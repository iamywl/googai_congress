#!/bin/bash
# Startup script for MetricLens demo instances. Installs a dependency-free,
# diurnal CPU load generator as a systemd service so the instance produces a
# realistic, time-varying CPU signal that Cloud Monitoring records. The target
# load pattern is chosen by the `ml-phase` instance-metadata attribute
# (web | api | batch | idle).
set -e

PHASE=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/ml-phase || echo web)

cat >/opt/mlload.py <<'PY'
"""Diurnal CPU load generator (stdlib only). A SINGLE worker duty-cycles one
core so the reported utilisation of a shared-core e2 instance stays well below
saturation and instead traces a representative daily curve. (Running one busy
core on a 2-vCPU VM caps reported utilisation near ~50%, so we map a target
utilisation of X% to a duty cycle of ~2X% of one core.)"""
import datetime
import hashlib
import os
import time

PHASE = os.environ.get("ML_PHASE", "web")

# Normalised diurnal shape (0..1) over a 24h UTC day.
CURVE = [
    0.12, 0.07, 0.04, 0.03, 0.04, 0.09, 0.22, 0.40, 0.60, 0.76, 0.88, 0.95,
    1.00, 0.98, 0.93, 0.85, 0.75, 0.63, 0.51, 0.41, 0.33, 0.25, 0.19, 0.14,
]
# (trough%, peak%) per phase — kept under the shared-core saturation point.
BANDS = {"web": (8, 46), "api": (6, 34), "batch": (4, 62), "idle": (2, 12)}
SPIKE_HOURS = {1, 2, 3, 13, 14}


def _noise(minute):
    h = hashlib.md5(f"{PHASE}:{minute}".encode()).hexdigest()
    return (int(h[:6], 16) / 0xFFFFFF - 0.5) * 5.0  # +/- 2.5%


def target_utilisation():
    now = datetime.datetime.utcnow()
    hour, minute = now.hour, now.hour * 60 + now.minute
    lo, hi = BANDS.get(PHASE, (6, 40))
    if PHASE == "batch":
        base = hi if hour in SPIKE_HOURS else lo
    else:
        base = lo + (hi - lo) * CURVE[hour]
    return max(1.0, min(60.0, base + _noise(minute)))


def main():
    while True:
        # One busy core ~= 50% of a 2-vCPU VM, so duty = 2 * target%.
        duty = min(1.0, (2.0 * target_utilisation()) / 100.0)
        period = 0.5
        end = time.time() + period * duty
        while time.time() < end:
            pass
        time.sleep(max(0.0, period * (1.0 - duty)))


if __name__ == "__main__":
    main()
PY

cat >/etc/systemd/system/mlload.service <<UNIT
[Unit]
Description=MetricLens demo diurnal load generator
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/mlload.py
Environment=ML_PHASE=${PHASE}
Restart=always
Nice=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now mlload.service
