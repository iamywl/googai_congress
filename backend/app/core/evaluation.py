"""Forecast-model evaluation: baselines, error metrics, and interval coverage.

Provides the quantitative evidence that the forecasting model "actually works":
it is compared against the two standard naive baselines (last-value and
seasonal-naive) on an expanding-window one-step backtest, and the calibration of
its 95% prediction interval is measured by empirical coverage. All functions are
pure (stdlib only) and operate on a plain list of floats.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from . import forecaster


@dataclass(frozen=True)
class Metrics:
    mape: float
    rmse: float
    mae: float
    n: int


def _errors(actual: list[float], pred: list[float]) -> Metrics:
    n = len(actual)
    if n == 0:
        return Metrics(0.0, 0.0, 0.0, 0)
    ape, se, ae = 0.0, 0.0, 0.0
    for a, p in zip(actual, pred, strict=True):
        floor = max(1.0, 0.01 * abs(a))
        ape += abs(a - p) / max(abs(a), floor)
        se += (a - p) ** 2
        ae += abs(a - p)
    return Metrics(
        mape=round(ape / n * 100.0, 2),
        rmse=round(sqrt(se / n), 3),
        mae=round(ae / n, 3),
        n=n,
    )


def backtest_naive(series: list[float], min_train: int) -> Metrics:
    """Last-value baseline: predict x[t] = x[t-1]."""
    actual, pred = [], []
    for t in range(min_train, len(series)):
        actual.append(series[t])
        pred.append(series[t - 1])
    return _errors(actual, pred)


def backtest_seasonal_naive(series: list[float], period: int, min_train: int) -> Metrics:
    """Seasonal-naive baseline: predict x[t] = x[t-period]."""
    actual, pred = [], []
    start = max(min_train, period)
    for t in range(start, len(series)):
        actual.append(series[t])
        pred.append(series[t - period])
    return _errors(actual, pred)


def backtest_model(series: list[float], period: int, min_train: int) -> Metrics:
    """The STL forecaster on an expanding-window one-step backtest."""
    actual, pred = [], []
    for t in range(min_train, len(series)):
        result = forecaster.forecast(series[:t], period=period, horizon=1)
        actual.append(series[t])
        pred.append(result.predicted_value)
    return _errors(actual, pred)


def interval_coverage(series: list[float], period: int, min_train: int) -> float:
    """Empirical coverage of the model's 95% prediction interval.

    A well-calibrated 95% interval should contain ~0.95 of the realised next
    values. Returns the observed fraction in [0, 1].
    """
    inside, total = 0, 0
    for t in range(min_train, len(series)):
        result = forecaster.forecast(series[:t], period=period, horizon=1)
        if result.lower_bound <= series[t] <= result.upper_bound:
            inside += 1
        total += 1
    return round(inside / total, 3) if total else 0.0


@dataclass(frozen=True)
class Evaluation:
    model: Metrics
    naive: Metrics
    seasonal_naive: Metrics
    coverage: float

    @property
    def beats_seasonal_naive(self) -> bool:
        return self.model.rmse <= self.seasonal_naive.rmse

    @property
    def beats_naive(self) -> bool:
        return self.model.rmse <= self.naive.rmse


def evaluate(series: list[float], period: int, min_train: int | None = None) -> Evaluation:
    """Full evaluation: model vs both baselines, plus interval coverage."""
    if min_train is None:
        min_train = max(period * 2, 10)
    return Evaluation(
        model=backtest_model(series, period, min_train),
        naive=backtest_naive(series, min_train),
        seasonal_naive=backtest_seasonal_naive(series, period, min_train),
        coverage=interval_coverage(series, period, min_train),
    )
