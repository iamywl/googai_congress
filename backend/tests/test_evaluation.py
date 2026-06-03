"""Tests for the forecast-model evaluation (baselines + interval coverage)."""

from app.core import evaluation, workload


def _cpu(key, days=14):
    return [s.cpu_pct for s in workload.generate(workload.ARCHETYPE_BY_KEY[key], days, key)]


def test_metrics_are_non_negative_and_counted():
    cpu = _cpu("interactive_api")
    ev = evaluation.evaluate(cpu, period=24)
    for m in (ev.model, ev.naive, ev.seasonal_naive):
        assert m.mape >= 0 and m.rmse >= 0 and m.mae >= 0 and m.n > 0


def test_interval_coverage_is_well_calibrated():
    # A 95% prediction interval should cover roughly 95% of realised values.
    cpu = _cpu("interactive_api")
    ev = evaluation.evaluate(cpu, period=24)
    assert 0.85 <= ev.coverage <= 1.0


def test_model_beats_seasonal_naive_on_interactive():
    # The forecaster must improve on the seasonal-naive baseline (RMSE) for the
    # diurnal interactive workloads it targets.
    for key in ("interactive_web", "interactive_api", "service_lowutil"):
        ev = evaluation.evaluate(_cpu(key), period=24)
        assert ev.beats_seasonal_naive, key


def test_seasonal_naive_uses_one_period_lag():
    # Deterministic check: on a pure repeating season, seasonal-naive is exact.
    series = [float(i % 24) for i in range(24 * 6)]
    m = evaluation.backtest_seasonal_naive(series, period=24, min_train=24)
    assert m.rmse == 0.0


def test_naive_uses_last_value():
    series = [float(i) for i in range(50)]  # +1 each step
    m = evaluation.backtest_naive(series, min_train=10)
    # last-value predictor is always off by exactly 1 on a unit ramp.
    assert abs(m.mae - 1.0) < 1e-9
