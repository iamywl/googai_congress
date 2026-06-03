"""Unit tests for the integer-programming resizing engine (docs/07)."""

import pytest

from app.core.optimizer import ResizeRecommendation, peak, recommend_resize


def test_low_load_proposes_downsize():
    rec = recommend_resize(
        current_vcpu=16,
        current_memory_mb=32768,
        predicted_peak_cpu_pct=20.0,
        predicted_peak_mem_pct=25.0,
    )
    assert isinstance(rec, ResizeRecommendation)
    assert rec.recommended_vcpu < rec.current_vcpu
    assert rec.recommended_memory_mb < rec.current_memory_mb
    assert rec.est_cost_saving_pct > 0


def test_saturated_load_keeps_capacity():
    rec = recommend_resize(
        current_vcpu=4,
        current_memory_mb=8192,
        predicted_peak_cpu_pct=100.0,
        predicted_peak_mem_pct=100.0,
    )
    # With safety margin the host cannot shrink; stay put, no negative saving.
    assert rec.recommended_vcpu == rec.current_vcpu
    assert rec.est_cost_saving_pct == 0.0


def test_headroom_constraint_is_respected():
    rec = recommend_resize(
        current_vcpu=10,
        current_memory_mb=10240,
        predicted_peak_cpu_pct=50.0,
        predicted_peak_mem_pct=50.0,
        target_utilisation=0.65,
        safety_margin=1.2,
    )
    cpu_load_units = 0.50 * 10 * 1.2  # = 6.0 vCPU-equivalents
    assert cpu_load_units <= 0.65 * rec.recommended_vcpu


def test_minimum_allocation_floor():
    rec = recommend_resize(
        current_vcpu=1,
        current_memory_mb=256,
        predicted_peak_cpu_pct=5.0,
        predicted_peak_mem_pct=5.0,
    )
    assert rec.recommended_vcpu == 1
    assert rec.recommended_memory_mb == 256


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        recommend_resize(0, 256, 10.0, 10.0)
    with pytest.raises(ValueError):
        recommend_resize(1, 128, 10.0, 10.0)
    with pytest.raises(ValueError):
        recommend_resize(1, 256, 10.0, 10.0, target_utilisation=1.5)


def test_slo_confidence_passthrough():
    rec = recommend_resize(2, 4096, 30.0, 30.0, slo_confidence=99.9)
    assert rec.slo_confidence == 99.9


def test_peak_percentile_ignores_single_spike():
    values = [10.0] * 99 + [100.0]
    assert peak(values, percentile=95.0) == 10.0
    assert peak(values, percentile=100.0) == 100.0


def test_peak_empty_is_zero():
    assert peak([]) == 0.0


def test_peak_invalid_percentile():
    with pytest.raises(ValueError):
        peak([1.0], percentile=0)
