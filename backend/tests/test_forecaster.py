"""Unit tests for the lightweight forecaster (docs/07: BVA + EP)."""

import math

import pytest

from app.core.forecaster import ForecastResult, forecast


def test_rejects_empty_series():
    with pytest.raises(ValueError):
        forecast([], period=24)


def test_rejects_non_positive_horizon():
    with pytest.raises(ValueError):
        forecast([1.0, 2.0, 3.0], period=2, horizon=0)


def test_single_sample_predicts_that_value():
    result = forecast([42.0], period=24, horizon=1)
    assert isinstance(result, ForecastResult)
    assert result.predicted_value == 42.0
    # No history to estimate dispersion -> zero-width band, no backtest.
    assert result.lower_bound == result.upper_bound == 42.0
    assert result.mape is None


def test_constant_series_is_flat_with_zero_error():
    result = forecast([50.0] * 48, period=24, horizon=5)
    assert result.predicted_value == pytest.approx(50.0, abs=1e-6)
    assert result.mape == pytest.approx(0.0, abs=1e-6)


def test_pure_linear_trend_is_extrapolated():
    series = [float(x) for x in range(1, 25)]  # y = x, no seasonality
    result = forecast(series, period=24, horizon=1)
    # Next value after 24 samples (1..24) is 25.
    assert result.predicted_value == pytest.approx(25.0, abs=1e-6)


def test_seasonal_pattern_is_recovered():
    # Two clean periods of a square-ish seasonal wave, no trend.
    base = [10.0, 20.0, 30.0, 20.0]
    series = base * 4
    result = forecast(series, period=4, horizon=1)
    # Index 16 mod 4 == 0 -> should land near the phase-0 level (10).
    assert result.predicted_value == pytest.approx(10.0, abs=1.0)


def test_prediction_interval_brackets_point_estimate():
    series = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0, 15.0]
    result = forecast(series, period=4, horizon=1)
    assert result.lower_bound <= result.predicted_value <= result.upper_bound


def test_mape_is_non_negative_when_reported():
    series = [float(20 + (x % 6)) for x in range(40)]
    result = forecast(series, period=6, horizon=1)
    assert result.mape is not None
    assert result.mape >= 0.0
    assert math.isfinite(result.mape)
