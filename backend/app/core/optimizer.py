"""Integer-programming resizing engine.

Given a host's current allocation and the forecasted peak load, the engine
selects the smallest integer resource allocation that keeps the projected peak
utilisation at or below a target threshold while preserving a safety margin for
the service-level objective (SLO).

The search space is small and bounded (vCPU in [1, current], memory in 256 MB
increments up to the current ceiling), so the optimum is found by exhaustive
enumeration -- an exact solver for this integer program with no external
dependency. The objective is to minimise allocated capacity (a proxy for cost)
subject to the capacity-headroom constraint::

    projected_peak_load * safety_margin <= target_utilisation * allocation

vCPU is treated as a unit-granular integer resource; memory is quantised to a
256 MB block, the minimum allocation unit defined in the data dictionary.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

_MEMORY_BLOCK_MB = 256


@dataclass(frozen=True)
class ResizeRecommendation:
    """A resizing proposal for a single host."""

    current_vcpu: int
    recommended_vcpu: int
    current_memory_mb: int
    recommended_memory_mb: int
    est_cost_saving_pct: float
    slo_confidence: float


def _smallest_unit_allocation(
    load_units: float, current_units: int, target_utilisation: float
) -> int:
    """Smallest integer allocation >= 1 (and <= current) satisfying headroom.

    Falls back to the current allocation when even that cannot satisfy the
    constraint (i.e. the host is already under-provisioned for the forecast).
    """
    for units in range(1, current_units + 1):
        if load_units <= target_utilisation * units:
            return units
    return current_units


def recommend_resize(
    current_vcpu: int,
    current_memory_mb: int,
    predicted_peak_cpu_pct: float,
    predicted_peak_mem_pct: float,
    target_utilisation: float = 0.65,
    safety_margin: float = 1.2,
    slo_confidence: float = 99.9,
) -> ResizeRecommendation:
    """Compute an SLO-aware resizing recommendation.

    Args:
        current_vcpu:            Currently allocated vCPU count (>= 1).
        current_memory_mb:       Currently allocated memory in MB (>= 256).
        predicted_peak_cpu_pct:  Forecasted peak CPU utilisation [0, 100+].
        predicted_peak_mem_pct:  Forecasted peak memory utilisation [0, 100+].
        target_utilisation:      Desired steady-state utilisation ceiling.
        safety_margin:           Multiplicative buffer absorbing forecast error.
        slo_confidence:          SLO availability the margin is sized to hold.

    Raises:
        ValueError: on non-positive allocations or a non-(0,1) target.
    """
    if current_vcpu < 1:
        raise ValueError("current_vcpu must be >= 1")
    if current_memory_mb < _MEMORY_BLOCK_MB:
        raise ValueError(f"current_memory_mb must be >= {_MEMORY_BLOCK_MB}")
    if not 0 < target_utilisation < 1:
        raise ValueError("target_utilisation must be in the open interval (0, 1)")

    # Absolute forecasted load expressed in the resource's own units.
    cpu_load_vcpu = (predicted_peak_cpu_pct / 100.0) * current_vcpu * safety_margin
    rec_vcpu = _smallest_unit_allocation(cpu_load_vcpu, current_vcpu, target_utilisation)

    current_blocks = current_memory_mb // _MEMORY_BLOCK_MB
    mem_load_blocks = (
        (predicted_peak_mem_pct / 100.0) * current_blocks * safety_margin
    )
    rec_blocks = _smallest_unit_allocation(
        mem_load_blocks, current_blocks, target_utilisation
    )
    rec_memory_mb = max(_MEMORY_BLOCK_MB, rec_blocks * _MEMORY_BLOCK_MB)

    # Cost proxy: equal-weighted reduction across the two resources.
    vcpu_saving = (current_vcpu - rec_vcpu) / current_vcpu
    mem_saving = (current_memory_mb - rec_memory_mb) / current_memory_mb
    est_saving_pct = round((vcpu_saving + mem_saving) / 2.0 * 100.0, 2)

    return ResizeRecommendation(
        current_vcpu=current_vcpu,
        recommended_vcpu=rec_vcpu,
        current_memory_mb=current_memory_mb,
        recommended_memory_mb=rec_memory_mb,
        est_cost_saving_pct=est_saving_pct,
        slo_confidence=round(slo_confidence, 2),
    )


def peak(values: list[float], percentile: float = 95.0) -> float:
    """Return the percentile peak of ``values`` (nearest-rank), 0.0 if empty.

    A high percentile rather than the raw maximum is used so a single transient
    spike does not force permanent over-provisioning -- the standard robust
    sizing statistic.
    """
    if not values:
        return 0.0
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    ordered = sorted(values)
    rank = ceil(percentile / 100.0 * len(ordered))
    return ordered[min(rank, len(ordered)) - 1]
