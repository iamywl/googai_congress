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
from statistics import NormalDist

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


# --------------------------------------------------------------------------
# Publication-grade evaluation: aligned backtest arrays + academic statistics.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BacktestRun:
    """Aligned one-step backtest series for the model and the two baselines."""

    actual: list[float]
    model: list[float]
    naive: list[float]
    seasonal_naive: list[float]
    lower: list[float]
    upper: list[float]


def backtest_run(series: list[float], period: int, min_train: int | None = None) -> BacktestRun:
    """Expanding-window one-step backtest, returning every aligned prediction."""
    if min_train is None:
        min_train = max(period * 2, 10)
    actual, model, naive, snaive, lo, hi = [], [], [], [], [], []
    for t in range(min_train, len(series)):
        res = forecaster.forecast(series[:t], period=period, horizon=1)
        actual.append(series[t])
        model.append(res.predicted_value)
        lo.append(res.lower_bound)
        hi.append(res.upper_bound)
        naive.append(series[t - 1])
        snaive.append(series[t - period] if t - period >= 0 else series[t - 1])
    return BacktestRun(actual, model, naive, snaive, lo, hi)


def mase(actual: list[float], pred: list[float], period: int) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006), scaled by the
    seasonal-naive one-step error. < 1 means better than seasonal-naive."""
    n = len(actual)
    if n <= period:
        return float("nan")
    scale = sum(abs(actual[i] - actual[i - period]) for i in range(period, n)) / (n - period)
    if scale == 0:
        return float("nan")
    mae = sum(abs(a - p) for a, p in zip(actual, pred, strict=True)) / n
    return round(mae / scale, 3)


def smape(actual: list[float], pred: list[float]) -> float:
    """Symmetric MAPE (%) — bounded, robust to small denominators."""
    n = len(actual)
    total = 0.0
    for a, p in zip(actual, pred, strict=True):
        denom = (abs(a) + abs(p)) / 2.0
        total += abs(a - p) / denom if denom else 0.0
    return round(total / n * 100.0, 2)


def mpiw(lower: list[float], upper: list[float]) -> float:
    """Mean Prediction Interval Width — interval sharpness."""
    n = len(lower)
    return round(sum(u - lo for lo, u in zip(lower, upper, strict=True)) / n, 3) if n else 0.0


def diebold_mariano(
    actual: list[float], pred_a: list[float], pred_b: list[float]
) -> tuple[float, float]:
    """Diebold-Mariano test (1995) of equal predictive accuracy under squared
    loss. Returns (DM statistic, two-sided p-value). A negative statistic with a
    small p-value means forecast A is significantly more accurate than B."""
    d = []
    for a, pa, pb in zip(actual, pred_a, pred_b, strict=True):
        d.append((a - pa) ** 2 - (a - pb) ** 2)
    n = len(d)
    if n < 2:
        return 0.0, 1.0
    mean_d = sum(d) / n
    var_d = sum((x - mean_d) ** 2 for x in d) / n
    if var_d == 0:
        return 0.0, 1.0
    dm = mean_d / sqrt(var_d / n)
    p = 2.0 * (1.0 - NormalDist().cdf(abs(dm)))
    return round(dm, 3), round(p, 4)
