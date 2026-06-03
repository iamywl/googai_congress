"""Unit tests for the GCP machine-type catalogue and snapping helpers."""

from app.core import machine_types
from app.core.machine_types import CATALOG, MachineType


def test_catalog_is_non_empty_and_well_formed():
    assert len(CATALOG) > 0
    for mt in CATALOG:
        assert isinstance(mt, MachineType)
        assert mt.vcpu >= 1
        assert mt.memory_mb >= 1024
        assert mt.memory_gb == mt.memory_mb // 1024


def test_exact_match_found_and_missing():
    sample = CATALOG[0]
    assert machine_types.exact_match(sample.vcpu, sample.memory_mb) == sample
    # No predefined type has this odd shape.
    assert machine_types.exact_match(3, 5 * 1024) is None


def test_nearest_fit_covers_demand():
    fit = machine_types.nearest_fit(8, 16 * 1024)
    assert fit.vcpu >= 8
    assert fit.memory_mb >= 16 * 1024


def test_nearest_fit_picks_smallest_satisfying():
    # 4 vCPU / 16 GB should map to a 4-vCPU type, not an 8-vCPU one.
    fit = machine_types.nearest_fit(4, 16 * 1024)
    assert fit.vcpu == 4
    assert fit.memory_mb >= 16 * 1024


def test_nearest_fit_falls_back_to_largest_when_oversized():
    largest = max(CATALOG, key=lambda m: (m.vcpu, m.memory_mb))
    fit = machine_types.nearest_fit(10_000, 10_000 * 1024)
    assert fit == largest


def test_describe_prefers_exact_then_nearest():
    sample = CATALOG[0]
    assert machine_types.describe(sample.vcpu, sample.memory_mb) == sample
    # Odd shape -> nearest fit that still covers it.
    desc = machine_types.describe(3, 5 * 1024)
    assert desc.vcpu >= 3 and desc.memory_mb >= 5 * 1024
