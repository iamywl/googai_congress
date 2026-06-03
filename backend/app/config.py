"""Application configuration sourced from environment variables.

Secrets (notably ``DATABASE_URL``) are injected at runtime via Cloud Run
environment variables backed by Secret Manager -- never hard-coded. The
defaults below target a local Postgres for development only.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="METRICLENS_", extra="ignore"
    )

    # Database DSN. Defaults to a self-contained SQLite file so the service runs
    # with zero external dependencies (demo / Cloud Run without Cloud SQL).
    # Production overrides this with an asyncpg DSN via Secret Manager, e.g.
    #   postgresql+asyncpg://user:pass@/metriclens?host=/cloudsql/PROJECT:REGION:INSTANCE
    database_url: str = "sqlite+aiosqlite:////tmp/metriclens.db"

    # When true (default for SQLite), create tables and seed demo data on boot.
    auto_seed: bool = True

    # Forecasting / optimisation knobs.
    seasonal_period: int = 24            # samples per seasonal cycle (hourly -> daily)
    sample_interval_minutes: int = 60    # cadence of incoming metric samples
    target_utilisation: float = 0.65     # steady-state utilisation ceiling
    safety_margin: float = 1.2           # forecast-error buffer
    slo_confidence: float = 99.9         # SLO availability the margin protects
    peak_percentile: float = 95.0        # robust peak statistic for sizing


settings = Settings()
