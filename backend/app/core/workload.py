"""Empirically-grounded synthetic workload generator.

The demo/seed metrics are not arbitrary: their utilisation levels, shapes, and
workload mix are calibrated to published large-scale datacentre measurements so
the dataset is statistically *representative* of real fleets rather than a toy.

Grounding (see ``docs/09_workload_modeling.md`` for the full write-up):

* Microsoft Azure VM trace — *Resource Central* (Cortez et al., SOSP 2017):
  60% of VMs average < 20% CPU; 40% have a 95th-percentile CPU < 50%. VMs split
  into *interactive* (diurnal periodicity) and *delay-insensitive* (batch,
  dev/test) classes; periodicity is detectable for VMs running >= 3 days.
* Barroso & Hölzle, *The Datacenter as a Computer*: servers spend most time in
  the 10–50% utilisation band and are rarely saturated.
* Alibaba 2018 cluster trace: batch-only servers average 29.3% CPU,
  service-only servers 7.4%; the cluster sits at 10–30% CPU >80% of the time.

Generation is fully deterministic (hash-based noise), so the seed is idempotent
and unit tests can assert the statistical properties directly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Normalised diurnal shape in [0, 1] over a 24h day for interactive workloads:
# quiet overnight, morning ramp, midday/afternoon peak, evening decline. This is
# the canonical "network-bound interactive" diurnal curve from the Azure trace.
_DIURNAL = (
    0.12, 0.07, 0.04, 0.03, 0.04, 0.09,   # 00–05 overnight trough
    0.22, 0.40, 0.60, 0.76, 0.88, 0.95,   # 06–11 morning ramp
    1.00, 0.98, 0.93, 0.85, 0.75, 0.63,   # 12–17 afternoon peak → decline
    0.51, 0.41, 0.33, 0.25, 0.19, 0.14,   # 18–23 evening wind-down
)


@dataclass(frozen=True)
class Archetype:
    """A workload class with calibrated utilisation targets.

    ``workload_class`` is one of ``interactive`` (diurnal), ``batch``
    (delay-insensitive, bursty) or ``steady`` (flat, often memory-bound).
    """

    key: str
    label: str
    workload_class: str
    cpu_trough: float           # overnight / idle CPU %
    cpu_peak: float             # diurnal peak CPU % (interactive/steady)
    weekend_factor: float       # multiplier applied Sat/Sun (interactive)
    spike_hours: tuple[int, ...]  # cron windows for batch
    spike_peak: float           # CPU % reached during a batch spike
    mem_base: float             # baseline memory %
    mem_coef: float             # memory % added per CPU %
    net_in_coef: float
    net_out_coef: float
    noise_amp: float            # +/- bound of deterministic noise (CPU %)


# The demo fleet — six hosts spanning the documented workload classes, cloud
# environments, and CPU- vs memory-bound profiles, with a mix of
# over-provisioned and right-sized boxes so the optimiser shows a real spread.
ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        key="interactive_web", label="Interactive web frontend (over-provisioned)",
        workload_class="interactive", cpu_trough=6, cpu_peak=30,
        weekend_factor=0.86, spike_hours=(), spike_peak=0,
        mem_base=24, mem_coef=0.5, net_in_coef=120, net_out_coef=85,
        noise_amp=1.4,
    ),
    Archetype(
        key="interactive_api", label="Interactive microservice API",
        workload_class="interactive", cpu_trough=8, cpu_peak=52,
        weekend_factor=0.88, spike_hours=(), spike_peak=0,
        mem_base=28, mem_coef=0.40, net_in_coef=90, net_out_coef=70,
        noise_amp=1.8,
    ),
    Archetype(
        key="steady_cache", label="Steady in-memory cache",
        workload_class="steady", cpu_trough=9, cpu_peak=15,
        weekend_factor=1.0, spike_hours=(), spike_peak=0,
        mem_base=66, mem_coef=0.25, net_in_coef=60, net_out_coef=55,
        noise_amp=1.5,
    ),
    Archetype(
        key="batch_etl", label="Delay-insensitive batch / ETL",
        workload_class="batch", cpu_trough=9, cpu_peak=0,
        weekend_factor=1.0, spike_hours=(1, 2, 3, 4, 13, 14, 15), spike_peak=90,
        mem_base=30, mem_coef=0.55, net_in_coef=55, net_out_coef=45,
        noise_amp=2.0,
    ),
    Archetype(
        key="service_lowutil", label="Over-provisioned service",
        workload_class="interactive", cpu_trough=4, cpu_peak=18,
        weekend_factor=0.9, spike_hours=(), spike_peak=0,
        mem_base=22, mem_coef=0.35, net_in_coef=70, net_out_coef=55,
        noise_amp=1.5,
    ),
    Archetype(
        key="devtest", label="Sporadic dev / test",
        workload_class="interactive", cpu_trough=5, cpu_peak=20,
        weekend_factor=0.6, spike_hours=(), spike_peak=0,
        mem_base=18, mem_coef=0.30, net_in_coef=40, net_out_coef=30,
        noise_amp=2.0,
    ),
)

ARCHETYPE_BY_KEY: dict[str, Archetype] = {a.key: a for a in ARCHETYPES}


@dataclass(frozen=True)
class Sample:
    """One hourly metric reading, ``hour`` hours after the series start."""

    hour: int
    cpu_pct: float
    mem_pct: float
    net_in_kbps: float
    net_out_kbps: float


def _unit(seed: str, i: int) -> float:
    """Deterministic pseudo-uniform value in [0, 1) from a hash of (seed, i)."""
    digest = hashlib.md5(f"{seed}:{i}".encode()).hexdigest()
    return int(digest[:8], 16) / 0x1_0000_0000


def _noise(seed: str, i: int, amp: float) -> float:
    return (_unit(seed, i) - 0.5) * 2.0 * amp


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# Stochastic structure parameters, calibrated so the generated series exhibit
# the autocorrelation, day-to-day variability, and occasional anomalies that
# real datacentre CPU traces show (rather than a perfectly repeating curve):
#   * AR(1) autocorrelated noise — consecutive hours are correlated (Azure/
#     Alibaba traces are strongly autocorrelated, not i.i.d.).
#   * Day-to-day amplitude variation — each day's peak is scaled, so no two days
#     are identical.
#   * A slow linear trend over the window (capacity creep / decay).
#   * Heteroscedastic noise — variance grows with the load level.
#   * Rare anomaly spikes (incidents).
_AR_RHO = 0.55          # AR(1) coefficient
_DAY_AMP = 0.15         # +/- day-to-day peak amplitude variation
_TREND_MAX = 0.08       # +/- slow drift across the whole window
_ANOMALY_THRESH = 0.99   # ~1% of hours get an anomaly spike


def _base_level(arch: Archetype, day: int, hour: int, seed: str) -> float:
    """Deterministic mean CPU% (no noise) for a day/hour under the archetype."""
    if arch.workload_class == "batch":
        if hour in arch.spike_hours:
            return arch.spike_peak * (0.9 + 0.1 * _unit(seed, day * 24 + hour))
        return arch.cpu_trough
    base = arch.cpu_trough + (arch.cpu_peak - arch.cpu_trough) * _DIURNAL[hour]
    if arch.weekend_factor != 1.0 and (day % 7) in (5, 6):
        base *= arch.weekend_factor
    return base


def generate(arch: Archetype, days: int, seed: str) -> list[Sample]:
    """Generate ``days`` of hourly samples for an archetype, deterministically.

    The mean follows the archetype's diurnal/batch shape; on top of it sit an
    AR(1) heteroscedastic noise process, day-to-day amplitude variation, a slow
    trend, and rare anomalies — so the series is statistically representative of
    a real trace rather than a clean repeating curve. A minimum of three days is
    enforced (the Azure trace's periodicity-detection threshold).
    """
    if days < 3:
        raise ValueError("days must be >= 3 for a representative seasonal series")
    total = days * 24
    trend_dir = (_unit(seed + "t", 0) - 0.5) * 2.0 * _TREND_MAX
    samples: list[Sample] = []
    resid = 0.0
    for i in range(total):
        day, hour = divmod(i, 24)
        day_amp = 1.0 + (_unit(seed + "d", day) - 0.5) * 2.0 * _DAY_AMP
        trend = 1.0 + trend_dir * (i / total)
        level = _base_level(arch, day, hour, seed) * day_amp * trend

        white = _noise(seed + "w", i, arch.noise_amp)
        resid = _AR_RHO * resid + white               # AR(1) autocorrelation
        cpu = level + resid * (0.6 + level / 120.0)    # heteroscedastic

        if _unit(seed + "a", i) > _ANOMALY_THRESH:     # rare incident spike
            cpu += 12.0 + 22.0 * _unit(seed + "x", i)

        cpu = round(_clamp(cpu, 1, 100))
        mem = round(_clamp(
            arch.mem_base + arch.mem_coef * cpu + _noise(seed + "m", i, 2.0), 1, 100,
        ))
        samples.append(Sample(
            hour=i, cpu_pct=cpu, mem_pct=mem,
            net_in_kbps=round(cpu * arch.net_in_coef + 50),
            net_out_kbps=round(cpu * arch.net_out_coef + 30),
        ))
    return samples
