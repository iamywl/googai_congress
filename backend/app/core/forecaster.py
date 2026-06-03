"""Lightweight, CPU-only time-series forecaster.

The engine performs additive seasonal-trend decomposition followed by a
trend + seasonal extrapolation (a Holt-Winters-style additive projection).
It is implemented purely on the standard library so the inference path carries
no native dependency, no GPU requirement, and a negligible container footprint
-- matching the MetricLens design constraint of running on commodity CPUs.

Decomposition model:  y[t] = trend[t] + seasonal[t mod period] + residual[t]

* trend     : ordinary least-squares straight-line fit over the sample index.
* seasonal  : mean of the detrended series grouped by phase (t mod period),
              re-centred to sum to zero so it does not bias the trend.
* residual  : what remains; its dispersion sets the prediction interval.

Forecast at a future offset h (in samples) is::

    y_hat = trend(n - 1 + h) + seasonal[(n - 1 + h) mod period]

Model quality is reported as MAPE from a one-step in-sample backtest, the
metric the functional spec tracks against the 15% accuracy target.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, pstdev

# 95% prediction interval half-width multiplier for a normal residual model.
_Z_95 = 1.96


@dataclass(frozen=True)
class ForecastResult:
    """Outcome of a single-horizon forecast."""

    predicted_value: float
    lower_bound: float
    upper_bound: float
    mape: float | None
    model: str = "STL_HOLTWINTERS"


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) of the OLS line through the (x, y) pairs."""
    n = len(xs)
    mean_x = fmean(xs)
    mean_y = fmean(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:  # degenerate x-spread -> flat line through the mean
        return 0.0, mean_y
    numer = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    slope = numer / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _linear_trend(series: list[float], period: int = 1) -> tuple[float, float]:
    """Seasonality-robust trend (slope, intercept) in original-index space.

    When at least two full seasonal periods are present, the trend is fitted on
    per-period block means located at each block's centre. Averaging over a full
    period cancels the seasonal component, so it cannot leak into the slope --
    the classical decomposition fix. Otherwise it falls back to a plain OLS fit
    over every sample.
    """
    n = len(series)
    full_blocks = n // period if period > 0 else 0
    if full_blocks >= 2:
        centres = [k * period + (period - 1) / 2.0 for k in range(full_blocks)]
        block_means = [
            fmean(series[k * period : (k + 1) * period]) for k in range(full_blocks)
        ]
        return _ols(centres, block_means)
    return _ols([float(x) for x in range(n)], series)


def _seasonal_indices(detrended: list[float], period: int) -> list[float]:
    """Mean detrended value per phase, re-centred to sum to zero."""
    buckets: list[list[float]] = [[] for _ in range(period)]
    for idx, value in enumerate(detrended):
        buckets[idx % period].append(value)
    raw = [fmean(b) if b else 0.0 for b in buckets]
    offset = fmean(raw)
    return [r - offset for r in raw]


def forecast(series: list[float], period: int, horizon: int = 1) -> ForecastResult:
    """Forecast ``horizon`` samples ahead of ``series``.

    Args:
        series:  Chronologically ordered metric samples (oldest first).
        period:  Seasonal period in samples (e.g. 24 for hourly daily cycles).
        horizon: How many samples ahead to project (>= 1).

    Raises:
        ValueError: if the series is empty or horizon < 1.
    """
    if not series:
        raise ValueError("series must contain at least one sample")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    period = max(1, period)
    n = len(series)
    slope, intercept = _linear_trend(series, period)

    detrended = [series[x] - (slope * x + intercept) for x in range(n)]
    seasonal = _seasonal_indices(detrended, period)

    future_index = (n - 1) + horizon
    predicted = slope * future_index + intercept + seasonal[future_index % period]

    # Prediction interval is sized from out-of-sample (backtest) error, which
    # reflects true predictive uncertainty. With too little history we fall back
    # to the in-sample residual spread.
    mape, rmse = _backtest(series, period)
    if rmse is None:
        residuals = [detrended[x] - seasonal[x % period] for x in range(n)]
        rmse = pstdev(residuals) if n > 1 else 0.0

    half_width = _Z_95 * rmse
    return ForecastResult(
        predicted_value=round(predicted, 2),
        lower_bound=round(predicted - half_width, 2),
        upper_bound=round(predicted + half_width, 2),
        mape=mape,
    )


def _backtest(series: list[float], period: int) -> tuple[float | None, float | None]:
    """One-step expanding-window backtest over the back half of the series.

    Returns ``(mape_pct, rmse)``. MAPE uses a denominator floor (1% of the
    series scale, min 1.0) so near-idle samples do not inflate the percentage.
    RMSE of the signed errors sizes the prediction interval. Returns
    ``(None, None)`` when there is too little history to backtest.
    """
    n = len(series)
    start = max(period, n // 2, 2)
    if n - start < 1:
        return None, None

    scale = max((abs(v) for v in series), default=0.0)
    floor = max(1.0, 0.01 * scale)

    pct_errors: list[float] = []
    sq_errors: list[float] = []
    for t in range(start, n):
        window = series[:t]
        slope, intercept = _linear_trend(window, period)
        detrended = [window[x] - (slope * x + intercept) for x in range(len(window))]
        seasonal = _seasonal_indices(detrended, period)
        predicted = slope * t + intercept + seasonal[t % period]
        actual = series[t]
        pct_errors.append(abs(actual - predicted) / max(abs(actual), floor))
        sq_errors.append((actual - predicted) ** 2)

    mape = round(fmean(pct_errors) * 100.0, 2)
    rmse = fmean(sq_errors) ** 0.5
    return mape, rmse
