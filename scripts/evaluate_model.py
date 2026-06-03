#!/usr/bin/env python3
"""Evaluate the MetricLens forecaster against naive baselines on every archetype.

Runs an expanding-window one-step backtest of the STL+AR forecaster versus the
last-value (naive) and seasonal-naive baselines, and measures the empirical
coverage of the 95% prediction interval. Prints a table that constitutes the
quantitative "the model works" evidence.

Usage:  python scripts/evaluate_model.py      (run from repo root)
"""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core import evaluation, workload  # noqa: E402

PERIOD = 24


def main() -> None:
    print(f"{'archetype':16s} {'mean':>5} {'CV':>5} | "
          f"{'model':>6} {'snaive':>7} {'naive':>6} {'cover':>6}  verdict")
    print("-" * 72)
    wins = 0
    for arch in workload.ARCHETYPES:
        cpu = [s.cpu_pct for s in workload.generate(arch, 14, arch.key)]
        cv = pstdev(cpu) / mean(cpu)
        ev = evaluation.evaluate(cpu, period=PERIOD)
        verdict = ("beats both" if ev.beats_seasonal_naive and ev.beats_naive
                   else "beats s-naive" if ev.beats_seasonal_naive else "—")
        wins += ev.beats_seasonal_naive
        print(f"{arch.key:16s} {mean(cpu):5.1f} {cv:5.2f} | "
              f"{ev.model.mape:6.1f} {ev.seasonal_naive.mape:7.1f} "
              f"{ev.naive.mape:6.1f} {ev.coverage:6.2f}  {verdict}")
    print("-" * 72)
    print(f"Model beats seasonal-naive (RMSE) on {wins}/{len(workload.ARCHETYPES)} "
          f"archetypes. MAPE in %, coverage target ~0.95.")


if __name__ == "__main__":
    main()
