"""Pure, DB-free simulation of a live scale-out test (dashboard demo).

Given the elapsed wall-clock seconds since a test started, this returns the full
visual state the dashboard animates: which phase we are in, the test node's status
and machine spec (before/after the scale-up), the CPU trace so far, the target
threshold, the forecast that predicts a breach, and the resize recommendation.

The story it tells, compressed into ~24 seconds:
    provision node -> apply load -> CPU climbs past the SLO ceiling ->
    forecaster predicts a breach -> scale up / provision more capacity ->
    CPU settles back under the ceiling.

The service layer turns the milestones into persisted Host / Metric / Action rows
so the same demo also lands in the fleet list and the audit log.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

# --- timeline (real seconds since start); the whole run is ~24s ---------------
T_RUNNING = 3.0      # node finishes provisioning, becomes RUNNING
T_LOAD = 5.0         # load injected, CPU starts to ramp
T_FORECAST = 11.0    # forecaster predicts the ceiling will be breached
T_SCALE = 13.0       # scale-up / provisioning applied
T_RESIZING = 1.6     # how long the RESIZING status is shown after T_SCALE
T_DONE = 24.0        # CPU has settled; run complete

SEC_PER_MIN = 0.5    # 1 simulated minute per 0.5s -> ~48 "minutes" over the run

# machine spec before and after the scale-up (cost is irrelevant in sim mode)
PRE = {"machine_type": "e2-small", "vcpu": 2, "memory_mb": 2048}
POST = {"machine_type": "e2-standard-4", "vcpu": 4, "memory_mb": 16384}

THRESHOLD = 65.0     # target-utilisation ceiling (%) drawn on the chart
BASE_CPU = 12.0      # idle baseline
PEAK_CPU = 93.0      # peak under load on the small node
POST_CPU = 44.0      # steady CPU after capacity is doubled


def _noise(t: float) -> float:
    return 2.2 * math.sin(t * 1.7) + 1.3 * math.sin(t * 0.7 + 1.0)


def _cpu(e: float) -> float:
    """CPU% at elapsed second ``e`` (only meaningful once the node is RUNNING)."""
    if e < T_LOAD:
        v = BASE_CPU + _noise(e)
    elif e < T_SCALE:
        frac = (e - T_LOAD) / (T_SCALE - T_LOAD)
        v = BASE_CPU + (PEAK_CPU - BASE_CPU) * frac + _noise(e)
    else:  # capacity doubled -> utilisation decays toward POST_CPU
        v = POST_CPU + (PEAK_CPU - POST_CPU) * math.exp(-(e - T_SCALE) / 3.0) + _noise(e)
    return round(max(0.0, min(100.0, v)), 1)


def phase(e: float) -> str:
    if e < T_RUNNING:
        return "provisioning"
    if e < T_LOAD:
        return "running"
    if e < T_FORECAST:
        return "load"
    if e < T_SCALE:
        return "forecast"
    if e < T_DONE:
        return "scaling"
    return "done"


def node_status(e: float) -> str:
    if e < T_RUNNING:
        return "PROVISIONING"
    if T_SCALE <= e < T_SCALE + T_RESIZING:
        return "RESIZING"
    return "RUNNING"


@dataclass
class State:
    phase: str
    node_status: str
    elapsed: float
    scaled: bool
    done: bool
    threshold: float
    spec: dict
    pre: dict
    post: dict
    cpu_now: float | None
    series: list[list[float]]                 # [[minute, cpu], ...]
    events: list[dict] = field(default_factory=list)
    forecast: dict | None = None
    recommendation: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def simulate(elapsed: float) -> State:
    """Build the full visual state at ``elapsed`` seconds since start."""
    e = max(0.0, elapsed)
    scaled = e >= T_SCALE
    done = e >= T_DONE
    spec = dict(POST if scaled else PRE)

    # CPU trace, sampled every 0.5s from when the node is RUNNING to now.
    series: list[list[float]] = []
    if e >= T_RUNNING:
        t = T_RUNNING
        end = min(e, T_DONE)
        while t <= end + 1e-9:
            series.append([round(t / SEC_PER_MIN, 1), _cpu(t)])
            t += 0.5
    cpu_now = series[-1][1] if series else None

    def _ev(t: float, kind: str, key: str) -> dict:
        return {"minute": round(t / SEC_PER_MIN, 1), "kind": kind, "key": key}

    events: list[dict] = []
    if e >= T_RUNNING:
        events.append(_ev(T_RUNNING, "node", "ev_running"))
    if e >= T_LOAD:
        events.append(_ev(T_LOAD, "load", "ev_load"))
    if e >= T_FORECAST:
        events.append(_ev(T_FORECAST, "forecast", "ev_forecast"))
    if e >= T_SCALE:
        events.append(_ev(T_SCALE, "scale", "ev_scale"))

    forecast = None
    if e >= T_FORECAST:
        # the ramp, extrapolated, breaches the ceiling -> triggers the scale-up
        forecast = {"predicted": 108.0, "lower": 95.0, "upper": 121.0, "mape": 6.4}

    recommendation = None
    if e >= T_FORECAST:
        recommendation = {
            "current_vcpu": PRE["vcpu"], "recommended_vcpu": POST["vcpu"],
            "current_memory_mb": PRE["memory_mb"],
            "recommended_memory_mb": POST["memory_mb"],
            "current_machine_type": PRE["machine_type"],
            "recommended_machine_type": POST["machine_type"],
        }

    return State(
        phase=phase(e), node_status=node_status(e), elapsed=round(e, 2),
        scaled=scaled, done=done, threshold=THRESHOLD, spec=spec,
        pre=dict(PRE), post=dict(POST), cpu_now=cpu_now, series=series,
        events=events, forecast=forecast, recommendation=recommendation,
    )
