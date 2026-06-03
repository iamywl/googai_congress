#!/usr/bin/env python3
"""Publication-grade evaluation of the MetricLens forecaster + figures.

Runs an expanding-window one-step backtest of the STL+AR forecaster against the
last-value (naive) and seasonal-naive baselines across every workload archetype,
computes academic accuracy statistics (RMSE, MAE, MAPE, sMAPE, MASE), prediction
-interval calibration (PICP coverage, MPIW), and the Diebold-Mariano test of
equal predictive accuracy, then renders clean figures for the report.

Outputs (docs/evaluation/):
    fig_forecast_overlay.png   actual vs forecast + 95% interval (2 archetypes)
    fig_error_rmse.png         RMSE: model vs baselines, per archetype
    fig_mase.png               MASE per archetype (1.0 = seasonal-naive)
    fig_coverage.png           95% interval coverage vs target, per archetype
    fig_residual_acf.png       residual autocorrelation (whiteness check)
    metrics.json               machine-readable results table

Usage:  python scripts/evaluate_model_paper.py     (from repo root)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import fmean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as _fm  # noqa: E402

# Register the bundled Korean font so figure labels render Hangul.
for _f in (Path.home() / ".local/share/fonts").glob("NanumGothic*.ttf"):
    try:
        _fm.fontManager.addfont(str(_f))
    except Exception:  # noqa: BLE001
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.core import evaluation, workload  # noqa: E402

PERIOD = 24
OUT = Path(__file__).resolve().parent.parent / "docs" / "evaluation"
OUT.mkdir(parents=True, exist_ok=True)

# Consistent, clean publication style.
plt.rcParams.update({
    "figure.dpi": 150,
    "font.family": "NanumGothic",
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.autolayout": True,
    "axes.unicode_minus": False,
})
C_MODEL, C_NAIVE, C_SNAIVE = "#1f77b4", "#999999", "#d62728"


def _acf(x, lags):
    n = len(x)
    m = fmean(x)
    denom = sum((v - m) ** 2 for v in x)
    out = []
    for k in range(lags + 1):
        num = sum((x[i] - m) * (x[i - k] - m) for i in range(k, n))
        out.append(num / denom if denom else 0.0)
    return out


def compute():
    rows = {}
    runs = {}
    for arch in workload.ARCHETYPES:
        cpu = [s.cpu_pct for s in workload.generate(arch, 14, arch.key)]
        run = evaluation.backtest_run(cpu, PERIOD)
        runs[arch.key] = (cpu, run)
        me = evaluation._errors(run.actual, run.model)
        ne = evaluation._errors(run.actual, run.naive)
        se = evaluation._errors(run.actual, run.seasonal_naive)
        cover = sum(lo <= a <= hi for a, lo, hi in
                    zip(run.actual, run.lower, run.upper, strict=True)) / len(run.actual)
        dm_s, dm_p = evaluation.diebold_mariano(run.actual, run.model, run.seasonal_naive)
        rows[arch.key] = {
            "mae_model": me.mae, "rmse_model": me.rmse, "mape_model": me.mape,
            "rmse_naive": ne.rmse, "rmse_snaive": se.rmse,
            "smape": evaluation.smape(run.actual, run.model),
            "mase": evaluation.mase(run.actual, run.model, PERIOD),
            "coverage": round(cover, 3),
            "mpiw": evaluation.mpiw(run.lower, run.upper),
            "dm_stat": dm_s, "dm_p": dm_p,
        }
    return rows, runs


def fig_forecast_overlay(runs):
    keys = ["interactive_web", "batch_etl"]
    fig, axes = plt.subplots(2, 1, figsize=(8, 6))
    for ax, key in zip(axes, keys, strict=True):
        _, run = runs[key]
        a, m, lo, hi = run.actual[-96:], run.model[-96:], run.lower[-96:], run.upper[-96:]
        x = range(len(a))
        ax.fill_between(x, lo, hi, color=C_MODEL, alpha=0.18, label="95% 구간")
        ax.plot(x, a, color="#111", lw=1.4, label="실측")
        ax.plot(x, m, color=C_MODEL, lw=1.4, ls="--", label="예측")
        ax.set_title(f"{key}: 1-스텝 예측 vs 실측 (최근 96h)")
        ax.set_ylabel("CPU %")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    axes[-1].set_xlabel("시간 (h)")
    fig.savefig(OUT / "fig_forecast_overlay.png")
    plt.close(fig)


def fig_error_rmse(rows):
    keys = list(rows)
    x = range(len(keys))
    w = 0.27
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - w for i in x], [rows[k]["rmse_model"] for k in keys], w, label="모델(model)", color=C_MODEL)
    ax.bar(list(x), [rows[k]["rmse_snaive"] for k in keys], w, label="seasonal-naive", color=C_SNAIVE)
    ax.bar([i + w for i in x], [rows[k]["rmse_naive"] for k in keys], w, label="naive", color=C_NAIVE)
    ax.set_xticks(list(x))
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("RMSE (CPU %)")
    ax.set_title("예측 오차(RMSE): 모델 vs 기준선 (낮을수록 우수)")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "fig_error_rmse.png")
    plt.close(fig)


def fig_mase(rows):
    keys = list(rows)
    vals = [rows[k]["mase"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [C_MODEL if v < 1 else C_NAIVE for v in vals]
    ax.bar(keys, vals, color=colors)
    ax.axhline(1.0, color=C_SNAIVE, ls="--", lw=1.2, label="seasonal-naive (MASE=1)")
    ax.set_ylabel("MASE")
    ax.set_title("MASE — 1 미만이면 seasonal-naive 능가")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.savefig(OUT / "fig_mase.png")
    plt.close(fig)


def fig_coverage(rows):
    keys = list(rows)
    vals = [rows[k]["coverage"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(keys, vals, color=C_MODEL)
    ax.axhline(0.95, color=C_SNAIVE, ls="--", lw=1.2, label="공칭 95%")
    ax.set_ylim(0.8, 1.0)
    ax.set_ylabel("실측 커버리지 (PICP)")
    ax.set_title("95% 예측구간 보정 (PICP)")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.savefig(OUT / "fig_coverage.png")
    plt.close(fig)


def fig_residual_acf(runs):
    _, run = runs["interactive_api"]
    resid = [a - m for a, m in zip(run.actual, run.model, strict=True)]
    acf = _acf(resid, 24)
    n = len(resid)
    ci = 1.96 / (n ** 0.5)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(range(len(acf)), acf, width=0.5, color=C_MODEL)
    ax.axhline(ci, color=C_SNAIVE, ls="--", lw=1.0)
    ax.axhline(-ci, color=C_SNAIVE, ls="--", lw=1.0, label="95% 백색잡음 대역")
    ax.set_xlabel("시차 (시간)")
    ax.set_ylabel("잔차 ACF")
    ax.set_title("잔차 자기상관(ACF, interactive_api) — 백색잡음에 가까우면 적합 양호")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "fig_residual_acf.png")
    plt.close(fig)


def main():
    rows, runs = compute()
    fig_forecast_overlay(runs)
    fig_error_rmse(rows)
    fig_mase(rows)
    fig_coverage(rows)
    fig_residual_acf(runs)
    (OUT / "metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"{'archetype':16s} {'RMSEm':>6} {'RMSEsn':>6} {'MASE':>5} "
          f"{'sMAPE':>6} {'cover':>6} {'MPIW':>6} {'DM':>6} {'p':>6}")
    for k, r in rows.items():
        print(f"{k:16s} {r['rmse_model']:6.2f} {r['rmse_snaive']:6.2f} {r['mase']:5.2f} "
              f"{r['smape']:6.1f} {r['coverage']:6.2f} {r['mpiw']:6.1f} "
              f"{r['dm_stat']:6.2f} {r['dm_p']:6.3f}")
    print(f"\nFigures + metrics.json written to {OUT}")


if __name__ == "__main__":
    main()
