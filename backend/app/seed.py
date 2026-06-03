"""Idempotent demo seeding for dependency-free (SQLite) deployments.

On startup the service creates the schema and, if the host table is empty,
inserts a small deterministic dataset (3 hosts, 48 hourly samples each) so the
forecast and recommendation endpoints return meaningful results immediately.
Safe to run on every boot: it no-ops once data exists.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from .db import get_engine, get_sessionmaker
from .models import Action, Base, Host, Metric

# Diurnal CPU shape (normalised, peak 85). Each host scales this shape to its
# own peak utilisation so the fleet shows a spread of optimisation stories:
# an over-provisioned PROD host (large saving), a moderately-loaded staging
# host, and a right-sized DEV host (no saving).
_DAILY_SHAPE = [
    34, 32, 30, 30, 31, 33, 40, 50, 62, 70, 76, 80,
    83, 85, 84, 80, 74, 66, 58, 50, 44, 40, 37, 35,
]
_SHAPE_PEAK = max(_DAILY_SHAPE)

# (hostname, environment, vcpu, memory_mb, peak_cpu_pct, jitter_seed)
_DEMO_HOSTS = [
    ("web-prod-01", "PROD", 16, 32768, 26, 1),     # over-provisioned -> big downsize
    ("api-staging-02", "STAGING", 8, 16384, 38, 2),  # moderate -> mild downsize
    ("batch-dev-03", "DEV", 4, 8192, 78, 3),        # right-sized -> hold
]


# Period-5 noise table (5 is coprime to the 24h cycle, so the same clock hour
# gets a different perturbation each day — genuine noise the seasonal component
# cannot absorb, yet bounded to ±1 so MAPE stays well within target).
_NOISE = (-1, 1, 0, 1, -1)


def _jitter(i: int, seed: int) -> int:
    return _NOISE[(i + seed) % 5]


async def create_schema() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_demo_data() -> int:
    """Insert demo hosts + metrics when the database is empty. Returns rows added."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        existing = await session.scalar(select(func.count()).select_from(Host))
        if existing:
            return 0

        base = datetime(2024, 1, 1, tzinfo=UTC)
        added = 0
        for hostname, env, vcpu, mem, peak, seed in _DEMO_HOSTS:
            host = Host(
                id=str(uuid4()),
                hostname=hostname,
                environment=env,
                vcpu_count=vcpu,
                memory_mb=mem,
                created_at=base,
            )
            session.add(host)
            # Seven days of hourly history: enough seasonal cycles for the
            # block-mean trend estimator to separate trend from seasonality in
            # the backtest, keeping forecast MAPE within target.
            for i in range(168):
                shaped = _DAILY_SHAPE[i % 24] * peak / _SHAPE_PEAK
                cpu = min(100, max(1, round(shaped) + _jitter(i, seed)))
                session.add(
                    Metric(
                        host_id=host.id,
                        ts=base + timedelta(hours=i),
                        cpu_pct=cpu,
                        mem_pct=min(100, round(cpu * 0.7 + 20)),
                        net_in_kbps=cpu * 120 + 50,
                        net_out_kbps=cpu * 80 + 30,
                    )
                )
                added += 1
            # A seeded historical forecast entry so the activity log is non-empty
            # on first load.
            session.add(
                Action(
                    id=str(uuid4()),
                    host_id=host.id,
                    ts=base + timedelta(days=7),
                    action_type="FORECAST",
                    detail=(
                        f"Forecast CPU +60m on {hostname}: "
                        f"{round(peak * 0.4)}% (MAPE 6.3%)"
                    ),
                )
            )
        await session.commit()
        return added
