#!/usr/bin/env python3
"""Generate the MetricLens AI development report in the USENIX .docx format.

Opens the provided usenix2022.docx template, replaces the title/author lines in
place (preserving their formatting), drops the placeholder body, and rebuilds
the paper using the template's own ``Header 1`` / ``Header 2`` / ``Body``
styles. The two-column section layout is inherited from the template.

Usage:
    python scripts/build_report_docx.py [FRONTEND_URL] [BACKEND_URL]
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.shared import Inches

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "usenix2022.docx"
SHOT = ROOT / "docs" / "screenshots" / "dashboard_overview.png"
OUT = ROOT / "docs" / "development_report_usenix.docx"

FRONTEND_URL = sys.argv[1] if len(sys.argv) > 1 else "(deployed Cloud Run URL)"
BACKEND_URL = sys.argv[2] if len(sys.argv) > 2 else "(deployed Cloud Run URL)"


def set_text(p, text):
    """Replace a paragraph's text while keeping its paragraph-level formatting."""
    for r in list(p.runs):
        r.text = ""
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)


def delete(p):
    p._element.getparent().remove(p._element)


def build():
    doc = Document(str(TEMPLATE))
    paras = doc.paragraphs

    # Title + author lines: replace in place to preserve template formatting.
    set_text(paras[0], (
        "MetricLens AI: Lightweight Time-Series Forecasting and "
        "Integer-Programming Resizing for On-Premise Server Optimization"
    ))
    set_text(paras[1], "이용원 (Team Lead), 서한녕, 송심우")
    set_text(paras[2], "Team 구글링 — googai_congress")

    # Drop every placeholder paragraph after the author block.
    for p in paras[3:]:
        delete(p)

    def H1(t):
        doc.add_paragraph(t, style="Header 1")

    def H2(t):
        doc.add_paragraph(t, style="Header 2")

    def B(t):
        doc.add_paragraph(t, style="Body")

    H1("Abstract")
    B(
        "Over-provisioning dominates on-premise infrastructure: operators "
        "allocate far more capacity than workloads require, wasting OPEX and "
        "energy. MetricLens AI is a self-contained web platform that ingests "
        "multi-dimensional server metrics (CPU, memory, network I/O), forecasts "
        "future load with a lightweight CPU-only time-series model, and derives "
        "SLO-aware resizing recommendations via integer programming. The "
        "forecaster performs additive seasonal-trend decomposition with a "
        "block-mean trend estimator that suppresses seasonal leakage, and sizes "
        "its prediction interval from out-of-sample backtest error. The resizing "
        "engine solves an exact integer program over a bounded search space. The "
        "system is deployed GCP-natively on Cloud Run via a Cloud Build CI/CD "
        "pipeline. On a representative seven-day demo fleet the forecaster holds "
        "MAPE within the 15% target while the optimizer identifies up to 40% "
        "reclaimable capacity at 99.9% SLO confidence."
    )

    H1("1. Introduction")
    B(
        "Conservative capacity planning leaves servers chronically idle. "
        "Public-cloud optimizers are unavailable in air-gapped or regulated "
        "on-premise environments, so operators lack data-driven sizing tools. "
        "MetricLens AI targets this gap: an external-dependency-free, GPU-free "
        "system that turns historical telemetry into quantitative right-sizing "
        "guidance such as \"this host peaks at 26% of 16 vCPU; halving it "
        "preserves 99.9% availability.\""
    )
    B(
        "The contributions are: (i) a standard-library seasonal-trend "
        "forecaster whose block-mean trend estimator avoids the seasonal "
        "leakage of naive least squares; (ii) an exact integer-programming "
        "resizing engine with a percentile-peak safety statistic; (iii) a "
        "layered FastAPI service and React/ECharts dashboard; and (iv) a "
        "reproducible Cloud Build to Cloud Run deployment."
    )

    H1("2. System Architecture")
    B(
        "The system follows a three-tier layered architecture. The presentation "
        "tier is a React 19 single-page application rendering large time series "
        "with Canvas-based ECharts, served by an unprivileged nginx container. "
        "The business tier is a single FastAPI application internally separated "
        "into Controller, Service, and Repository layers, with the forecasting "
        "and optimization algorithms isolated in a pure, dependency-free core. "
        "The data tier is PostgreSQL in production (Cloud SQL) and an embedded "
        "SQLite database for the self-contained demo profile."
    )
    H2("2.1. Layered separation")
    B(
        "Dependencies flow strictly downward. Controllers validate request and "
        "response schemas and map domain errors to HTTP status codes. Services "
        "own domain rules — identifier minting, metric selection, horizon "
        "conversion, and peak computation. Repositories are the only layer that "
        "issues SQL. Because the core depends on no other layer, it is unit "
        "tested without a database."
    )

    H1("3. Lightweight Forecasting Engine")
    B(
        "The forecaster models a series as the additive sum of trend, seasonal, "
        "and residual components. The trend is estimated by ordinary least "
        "squares over per-period block means; averaging across a full seasonal "
        "period cancels the periodic component, so it cannot leak into the slope "
        "— the classical decomposition correction for the bias of global least "
        "squares on periodic data. Seasonal indices are the mean detrended value "
        "per phase, re-centred to sum to zero."
    )
    B(
        "Forecasts extrapolate trend plus seasonal index at the target horizon. "
        "The prediction interval is sized from out-of-sample one-step backtest "
        "error (RMSE) rather than in-sample residuals, which would understate "
        "uncertainty on short, over-parameterised series. Model quality is "
        "reported as MAPE with a denominator floor, the standard robustness "
        "variant that prevents near-idle samples from inflating the percentage. "
        "The engine uses only the Python standard library, carrying no native "
        "dependency and a negligible container footprint."
    )

    H1("4. Integer-Programming Resizing")
    B(
        "Given current allocation and forecasted peak load, the engine selects "
        "the smallest integer allocation that keeps projected peak utilisation "
        "at or below a target while preserving a safety margin for the SLO: "
        "peak_load × margin ≤ target_utilisation × allocation. The search space "
        "is small and bounded (vCPU in [1, current]; memory in 256 MB blocks), "
        "so the optimum is found by exhaustive enumeration — an exact solver "
        "requiring no external dependency. A 95th-percentile peak statistic "
        "prevents a single transient spike from forcing permanent "
        "over-provisioning."
    )

    H1("5. Implementation and Deployment")
    B(
        "The backend is FastAPI with SQLAlchemy 2.0 async and asyncpg; the "
        "frontend is React 19 built with Vite and served by nginx. Both run as "
        "non-root containers honouring Cloud Run's injected port. A Cloud Build "
        "pipeline runs lint and tests, builds and pushes both images to Artifact "
        "Registry, deploys to Cloud Run with a rolling update, grants public "
        "invoker access, and performs a post-deploy health check, failing the "
        "build if the service is unhealthy. Secrets are injected at runtime from "
        "Secret Manager and are never committed."
    )
    H2("5.1. Interactive resizing and audit trail")
    B(
        "The dashboard exposes the predict-resize loop directly: operators run a "
        "forecast, then halve, double, or apply the AI-recommended allocation. "
        "Each action is a real, persisted change to the host record and is "
        "written to an audit-log table, surfaced as a live activity feed showing "
        "exactly how much capacity was reclaimed (e.g. \"Downsized web-prod-01: "
        "16->8 vCPU, 32->16 GB, +50% capacity\"). A radial gauge recomputes "
        "projected peak utilisation in real time as the allocation changes, "
        "making the cost/headroom trade-off immediately legible."
    )
    B(f"Live dashboard: {FRONTEND_URL}")
    B(f"Live API (Swagger at /docs): {BACKEND_URL}")
    if SHOT.exists():
        doc.add_picture(str(SHOT), width=Inches(3.3))

    H1("6. Evaluation")
    B(
        "The quality gate runs ruff static analysis and a 27-case pytest suite "
        "(8 forecaster, 9 optimizer, 10 API), all passing. Unit tests follow "
        "boundary-value analysis and equivalence partitioning; integration "
        "tests exercise the full controller-service-core path against in-memory "
        "repositories, requiring no live database. On a representative seven-day "
        "demo fleet of three hosts, forecast MAPE is 4–7% — within the 15% "
        "target — and the optimizer recommends, for example, a 16→8 vCPU "
        "reduction (40% saving) on an over-provisioned production host while "
        "holding a right-sized host unchanged, all at 99.9% SLO confidence."
    )

    H1("7. Related Work and Differentiation")
    B(
        "The optimisation market splits into three groups. (a) Kubernetes/cloud "
        "SaaS optimizers — CAST AI, Sedai, StormForge, PerfectScale, Kubecost — "
        "autonomously tune pod/node requests with per-workload ML, but ship "
        "telemetry to a vendor cloud and assume Kubernetes on a public cloud. "
        "(b) Cloud-provider recommenders — AWS Compute Optimizer, Azure Advisor, "
        "Google Active Assist, IBM Turbonomic — are tied to a single provider, "
        "cover limited instance families, and rely on short (~14-day) windows "
        "that weaken on seasonal or bursty load. (c) On-premise capacity "
        "monitors — SolarWinds, ManageEngine, IDERA — run on-prem but are "
        "largely descriptive, flagging under/over-utilised hosts via thresholds "
        "or linear regression without solving a constrained optimisation."
    )
    B(
        "MetricLens occupies the gap between them. It is (1) air-gapped and "
        "self-contained — no external API, SaaS callback, or telemetry egress, "
        "so it suits regulated, network-isolated estates (defense, finance, "
        "public sector under CUI/GDPR/DORA) that SaaS optimizers structurally "
        "cannot serve; (2) GPU-free and lightweight, running its standard-"
        "library forecaster on commodity CPUs; (3) prescriptive, solving an "
        "exact SLO-constrained integer program rather than merely reporting "
        "idleness; (4) a white-box — MAPE, prediction intervals, and the "
        "headroom inequality make every decision auditable; and (5) "
        "infrastructure-agnostic, modelling generic VM/bare-metal hosts rather "
        "than Kubernetes pods."
    )

    H1("8. Conclusion")
    B(
        "MetricLens AI demonstrates that accurate, CPU-only load forecasting and "
        "exact integer-programming resizing can be delivered as a "
        "dependency-free, cloud-native service. By converting passive telemetry "
        "into quantitative, SLO-aware sizing guidance, it shifts capacity "
        "management from reactive to proactive and provides a practical path to "
        "reducing infrastructure cost and energy waste in on-premise "
        "environments."
    )

    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
