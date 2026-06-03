"""MetricLens AI — FastAPI application entrypoint.

A single ASGI app exposes the layered API. Liveness (`/health`) never touches
the database so Cloud Run startup/health probes stay fast and dependency-free;
readiness (`/health/db`) verifies the persistence backend on demand.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api import (
    routes_analysis,
    routes_catalog,
    routes_gcp,
    routes_history,
    routes_hosts,
    routes_metrics,
)
from .config import settings
from .db import get_session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # For the dependency-free (SQLite) profile, create the schema and seed a
    # deterministic demo dataset so the API is usable immediately. Skipped when
    # a managed database (Postgres) is configured, where schema.sql owns DDL.
    if settings.auto_seed and settings.database_url.startswith("sqlite"):
        from .seed import create_schema, seed_demo_data

        await create_schema()
        await seed_demo_data()
    yield


app = FastAPI(
    title="MetricLens AI API",
    description=(
        "Time-series server-load forecasting and integer-programming based "
        "resource-resizing recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# The browser dashboard is served from a different Cloud Run origin, so the API
# must advertise CORS. This is a public, read-only demo API; credentials are not
# used, so a permissive policy is acceptable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_hosts.router)
app.include_router(routes_metrics.router)
app.include_router(routes_analysis.router)
app.include_router(routes_catalog.router)
app.include_router(routes_history.router)
app.include_router(routes_gcp.router)


@app.get("/", tags=["Meta"])
async def root() -> dict[str, str]:
    return {"service": "metriclens-ai", "status": "running"}


@app.get("/health", tags=["Meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["Meta"])
async def health_db() -> dict[str, str]:
    async for session in get_session():
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
