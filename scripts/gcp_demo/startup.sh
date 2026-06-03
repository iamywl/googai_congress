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
"""Diurnal CPU load generator (stdlib only). One worker per vCPU duty-cycles to
hit a time-of-day target utilisation, so the instance's real CPU metric traces a
representative daily curve with a little noise."""
import datetime
import hashlib
import os
import time
from multiprocessing import Process

PHASE = os.environ.get("ML_PHASE", "web")

# Normalised diurnal shape (0..1) over a 24h UTC day.
CURVE = [
    0.12, 0.07, 0.04, 0.03, 0.04, 0.09, 0.22, 0.40, 0.60, 0.76, 0.88, 0.95,
    1.00, 0.98, 0.93, 0.85, 0.75, 0.63, 0.51, 0.41, 0.33, 0.25, 0.19, 0.14,
]
# (trough%, peak%) per phase.
BANDS = {"web": (10, 62), "api": (8, 46), "batch": (6, 88), "idle": (3, 16)}
SPIKE_HOURS = {1, 2, 3, 13, 14}


def _noise(minute):
    h = hashlib.md5(f"{PHASE}:{minute}".encode()).hexdigest()
    return (int(h[:6], 16) / 0xFFFFFF - 0.5) * 6.0  # +/- 3%


def target_fraction():
    now = datetime.datetime.utcnow()
    hour, minute = now.hour, now.hour * 60 + now.minute
    lo, hi = BANDS.get(PHASE, (8, 50))
    if PHASE == "batch":
        base = hi if hour in SPIKE_HOURS else lo
    else:
        base = lo + (hi - lo) * CURVE[hour]
    val = base + _noise(minute)
    return max(0.02, min(0.95, val / 100.0))


def worker():
    while True:
        frac = target_fraction()
        period = 0.5
        end = time.time() + period * frac
        while time.time() < end:
            pass
        time.sleep(max(0.0, period * (1.0 - frac)))


if __name__ == "__main__":
    for _ in range(os.cpu_count() or 1):
        Process(target=worker, daemon=True).start()
    while True:
        time.sleep(3600)
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
