#!/usr/bin/env python3
"""Publication-grade evaluation of the MetricLens forecaster + figures.

Runs an expanding-window one-step backtest of the STL+AR forecaster against the
last-value (naive) and seasonal-naive baselines across every workload archetype,
computes academic accuracy statistics (RMSE, MAE, MAPE, sMAPE, MASE), prediction
-interval calibration (PICP coverage, MPIW), and the Diebold-Mariano test, then
renders clean figures. English is primary (base filenames); Korean variants are
written with a ``_kr`` suffix.

Outputs (docs/evaluation/): fig_*.png (EN) and fig_*_kr.png (KR), metrics.json.
Usage:  python scripts/evaluate_model_paper.py
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

C_MODEL, C_NAIVE, C_SNAIVE = "#1f77b4", "#999999", "#d62728"

# Bilingual labels: English primary, Korean (_kr).
TR = {
    "en": {
        "font": "DejaVu Sans",
        "fc_title": "{k}: one-step forecast vs actual (last 96h)",
        "interval": "95% interval", "actual": "actual", "forecast": "forecast",
        "hour": "hour", "rmse_y": "RMSE (CPU %)",
        "rmse_title": "Forecast error (RMSE): model vs baselines (lower is better)",
        "model": "model",
        "mase_title": "MASE - below 1 beats seasonal-naive",
        "mase_ref": "seasonal-naive (MASE=1)",
        "cov_y": "empirical coverage (PICP)",
        "cov_title": "95% prediction-interval calibration (PICP)",
        "cov_nom": "nominal 95%",
        "acf_x": "lag (hours)", "acf_y": "residual ACF",
        "acf_title": "Residual autocorrelation (interactive_api) - near white = good fit",
        "acf_band": "95% white-noise band",
    },
    "kr": {
        "font": "NanumGothic",
        "fc_title": "{k}: 1-스텝 예측 vs 실측 (최근 96h)",
        "interval": "95% 구간", "actual": "실측", "forecast": "예측",
        "hour": "시간 (h)", "rmse_y": "RMSE (CPU %)",
        "rmse_title": "예측 오차(RMSE): 모델 vs 기준선 (낮을수록 우수)",
        "model": "모델(model)",
        "mase_title": "MASE - 1 미만이면 seasonal-naive 능가",
        "mase_ref": "seasonal-naive (MASE=1)",
        "cov_y": "실측 커버리지 (PICP)",
        "cov_title": "95% 예측구간 보정 (PICP)",
        "cov_nom": "공칭 95%",
        "acf_x": "시차 (시간)", "acf_y": "잔차 ACF",
        "acf_title": "잔차 자기상관(ACF, interactive_api) - 백색잡음에 가까우면 적합 양호",
        "acf_band": "95% 백색잡음 대역",
    },
}


def _acf(x, lags):
    n = len(x)
    m = fmean(x)
    denom = sum((v - m) ** 2 for v in x)
    return [(sum((x[i] - m) * (x[i - k] - m) for i in range(k, n)) / denom if denom else 0.0)
            for k in range(lags + 1)]


def compute():
    rows, runs = {}, {}
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
            "rmse_model": me.rmse, "mae_model": me.mae, "mape_model": me.mape,
            "rmse_naive": ne.rmse, "rmse_snaive": se.rmse,
            "smape": evaluation.smape(run.actual, run.model),
            "mase": evaluation.mase(run.actual, run.model, PERIOD),
            "coverage": round(cover, 3), "mpiw": evaluation.mpiw(run.lower, run.upper),
            "dm_stat": dm_s, "dm_p": dm_p,
        }
    return rows, runs


def render(rows, runs, T, suf):
    plt.rcParams.update({
        "figure.dpi": 150, "font.family": T["font"], "font.size": 10,
        "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
        "axes.spines.right": False, "figure.autolayout": True, "axes.unicode_minus": False,
    })
    keys = list(rows)

    fig, axes = plt.subplots(2, 1, figsize=(8, 6))
    for ax, key in zip(axes, ["interactive_web", "batch_etl"], strict=True):
        _, run = runs[key]
        a, m, lo, hi = run.actual[-96:], run.model[-96:], run.lower[-96:], run.upper[-96:]
        x = range(len(a))
        ax.fill_between(x, lo, hi, color=C_MODEL, alpha=0.18, label=T["interval"])
        ax.plot(x, a, color="#111", lw=1.4, label=T["actual"])
        ax.plot(x, m, color=C_MODEL, lw=1.4, ls="--", label=T["forecast"])
        ax.set_title(T["fc_title"].format(k=key))
        ax.set_ylabel("CPU %")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    axes[-1].set_xlabel(T["hour"])
    fig.savefig(OUT / f"fig_forecast_overlay{suf}.png"); plt.close(fig)

    x = range(len(keys)); w = 0.27
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - w for i in x], [rows[k]["rmse_model"] for k in keys], w, label=T["model"], color=C_MODEL)
    ax.bar(list(x), [rows[k]["rmse_snaive"] for k in keys], w, label="seasonal-naive", color=C_SNAIVE)
    ax.bar([i + w for i in x], [rows[k]["rmse_naive"] for k in keys], w, label="naive", color=C_NAIVE)
    ax.set_xticks(list(x)); ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel(T["rmse_y"]); ax.set_title(T["rmse_title"]); ax.legend(fontsize=8)
    fig.savefig(OUT / f"fig_error_rmse{suf}.png"); plt.close(fig)

    vals = [rows[k]["mase"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(keys, vals, color=[C_MODEL if v < 1 else C_NAIVE for v in vals])
    ax.axhline(1.0, color=C_SNAIVE, ls="--", lw=1.2, label=T["mase_ref"])
    ax.set_ylabel("MASE"); ax.set_title(T["mase_title"])
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.legend(fontsize=8); fig.savefig(OUT / f"fig_mase{suf}.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(keys, [rows[k]["coverage"] for k in keys], color=C_MODEL)
    ax.axhline(0.95, color=C_SNAIVE, ls="--", lw=1.2, label=T["cov_nom"])
    ax.set_ylim(0.8, 1.0); ax.set_ylabel(T["cov_y"]); ax.set_title(T["cov_title"])
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(keys, rotation=20, ha="right", fontsize=8)
    ax.legend(fontsize=8); fig.savefig(OUT / f"fig_coverage{suf}.png"); plt.close(fig)

    _, run = runs["interactive_api"]
    resid = [a - m for a, m in zip(run.actual, run.model, strict=True)]
    acf = _acf(resid, 24); ci = 1.96 / (len(resid) ** 0.5)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(range(len(acf)), acf, width=0.5, color=C_MODEL)
    ax.axhline(ci, color=C_SNAIVE, ls="--", lw=1.0)
    ax.axhline(-ci, color=C_SNAIVE, ls="--", lw=1.0, label=T["acf_band"])
    ax.set_xlabel(T["acf_x"]); ax.set_ylabel(T["acf_y"]); ax.set_title(T["acf_title"])
    ax.legend(fontsize=8); fig.savefig(OUT / f"fig_residual_acf{suf}.png"); plt.close(fig)


def main():
    rows, runs = compute()
    render(rows, runs, TR["en"], "")        # English primary
    render(rows, runs, TR["kr"], "_kr")     # Korean variant
    (OUT / "metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{'archetype':16s} {'RMSEm':>6} {'RMSEsn':>6} {'MASE':>5} {'cover':>6} {'DM':>6} {'p':>6}")
    for k, r in rows.items():
        print(f"{k:16s} {r['rmse_model']:6.2f} {r['rmse_snaive']:6.2f} {r['mase']:5.2f} "
              f"{r['coverage']:6.2f} {r['dm_stat']:6.2f} {r['dm_p']:6.3f}")
    print(f"Figures (EN + _kr) + metrics.json -> {OUT}")


if __name__ == "__main__":
    main()
