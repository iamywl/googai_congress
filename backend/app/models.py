"""SQLAlchemy ORM models mirroring ./scripts/schema.sql.

ENUM-valued columns are stored as portable ``VARCHAR`` (validated by the
Pydantic layer) so the same models run against both PostgreSQL in production and
SQLite in the test harness. The canonical production DDL remains schema.sql.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False, default="PROD")
    vcpu_count: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=func.now())
    # Real-instance provenance: "demo" (synthetic seed) or "gce" (a live GCE VM
    # synced from Cloud Monitoring). zone/machine_type are set for "gce" hosts so
    # a real resize can target the actual instance.
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="demo")
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    machine_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("vcpu_count BETWEEN 1 AND 256", name="ck_hosts_vcpu"),
        CheckConstraint("memory_mb BETWEEN 256 AND 4194304", name="ck_hosts_mem"),
    )


class Metric(Base):
    __tablename__ = "metrics"

    # BIGINT on Postgres; INTEGER on SQLite so it aliases rowid and
    # auto-increments (SQLite only auto-generates for INTEGER PRIMARY KEY).
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(nullable=False)
    cpu_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    mem_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    net_in_kbps: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    net_out_kbps: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("host_id", "ts", name="uq_metrics_host_ts"),
        Index("ix_metrics_host_ts", "host_id", "ts"),
        CheckConstraint("cpu_pct BETWEEN 0 AND 100", name="ck_metrics_cpu"),
        CheckConstraint("mem_pct BETWEEN 0 AND 100", name="ck_metrics_mem"),
    )


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=func.now())
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="STL_HOLTWINTERS")
    predicted_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    upper_bound: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mape: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    __table_args__ = (Index("ix_forecasts_host", "host_id", "generated_at"),)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=func.now())
    current_vcpu: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_vcpu: Mapped[int] = mapped_column(Integer, nullable=False)
    current_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    est_cost_saving_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    slo_confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    __table_args__ = (Index("ix_recommendations_host", "host_id", "generated_at"),)


class Action(Base):
    """Audit log of operator/system actions: forecasts run and resizes applied."""

    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(nullable=False, default=func.now())
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)  # FORECAST | RESIZE
    detail: Mapped[str] = mapped_column(String(500), nullable=False)
    before_vcpu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_vcpu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saving_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    __table_args__ = (Index("ix_actions_host", "host_id", "ts"),)
