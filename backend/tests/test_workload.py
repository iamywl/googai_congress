"""Statistical-representativeness tests for the synthetic workload generator.

These assert that the demo/seed data reproduces the published datacentre
characteristics it is calibrated to (see docs/09_workload_modeling.md), so the
dataset stays representative if the archetypes are ever tuned.
"""

from statistics import mean, pstdev

import pytest

from app.core import forecaster, optimizer, workload


def _series(key):
    arch = workload.ARCHETYPE_BY_KEY[key]
    return arch, [s.cpu_pct for s in workload.generate(arch, days=14, seed=key)]


def test_generation_is_deterministic():
    a = workload.ARCHETYPES[0]
    assert workload.generate(a, 14, "host-x") == workload.generate(a, 14, "host-x")


def test_length_matches_days():
    a = workload.ARCHETYPES[0]
    assert len(workload.generate(a, 14, "s")) == 14 * 24


def test_minimum_three_days_enforced():
    with pytest.raises(ValueError):
        workload.generate(workload.ARCHETYPES[0], days=2, seed="s")


def test_values_within_physical_bounds():
    for a in workload.ARCHETYPES:
        for s in workload.generate(a, 14, a.key):
            assert 1 <= s.cpu_pct <= 100
            assert 1 <= s.mem_pct <= 100
            assert s.net_in_kbps >= 0 and s.net_out_kbps >= 0


def test_interactive_workloads_show_diurnal_periodicity():
    # Azure trace: interactive VMs show more CPU during the day than at night.
    for key in ("interactive_web", "interactive_api"):
        samples = workload.generate(workload.ARCHETYPE_BY_KEY[key], 14, key)
        day = mean(s.cpu_pct for s in samples if 10 <= s.hour % 24 <= 16)
        night = mean(s.cpu_pct for s in samples if 0 <= s.hour % 24 <= 5)
        assert day > night * 1.5


def test_batch_workload_is_bursty():
    # Delay-insensitive batch: occasional spikes far above the mean.
    _, cpu = _series("batch_etl")
    assert optimizer.peak(cpu, 95.0) > 2 * mean(cpu)
    assert pstdev(cpu) > 15


def test_steady_cache_is_flat_and_memory_bound():
    arch = workload.ARCHETYPE_BY_KEY["steady_cache"]
    samples = workload.generate(arch, 14, "steady_cache")
    cpu = [s.cpu_pct for s in samples]
    mem = [s.mem_pct for s in samples]
    assert pstdev(cpu) < 5            # near-flat CPU
    assert mean(mem) > 60             # memory-bound


def test_over_provisioned_classes_are_low_utilisation():
    # Alibaba: service-class servers ~7% CPU; Azure: 60% of VMs avg < 20%.
    for key in ("service_lowutil", "devtest"):
        _, cpu = _series(key)
        assert mean(cpu) < 15


def test_interactive_hosts_are_forecastable_within_target():
    # The forecaster targets diurnal/interactive workloads; MAPE stays <= 15%.
    for key in ("interactive_web", "interactive_api"):
        _, cpu = _series(key)
        result = forecaster.forecast(cpu, period=24, horizon=1)
        assert result.mape is not None
        assert result.mape <= 15.0
