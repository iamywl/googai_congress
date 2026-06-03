"""Business-logic layer (Service pattern).

Services orchestrate repositories and the pure ``core`` algorithms. They own
domain rules (identifier minting, metric selection, horizon conversion) and are
the only layer the API controllers call into.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .config import settings
from .core import evaluation, forecaster, optimizer
from .models import Action, Forecast, Host, Metric, Recommendation
from .repositories import (
    ActionRepository,
    AnalysisRepository,
    HostRepository,
    MetricRepository,
)
from .schemas import HostCreate, MetricIn, MetricKind

# Map a forecast metric class to its physical metric column.
_METRIC_COLUMN: dict[MetricKind, str] = {
    MetricKind.CPU: "cpu_pct",
    MetricKind.MEM: "mem_pct",
    MetricKind.NET_IN: "net_in_kbps",
    MetricKind.NET_OUT: "net_out_kbps",
}


class HostNotFoundError(Exception):
    """Raised when an operation targets a host id that does not exist."""


class DuplicateHostError(Exception):
    """Raised when creating a host whose hostname already exists."""


class InsufficientDataError(Exception):
    """Raised when there are too few samples to analyse a host."""


class HostService:
    def __init__(self, hosts: HostRepository, actions: ActionRepository) -> None:
        self.hosts = hosts
        self.actions = actions

    async def create_host(self, data: HostCreate) -> Host:
        if await self.hosts.get_by_hostname(data.hostname) is not None:
            raise DuplicateHostError(data.hostname)
        host = Host(
            id=str(uuid4()),
            hostname=data.hostname,
            environment=data.environment.value,
            vcpu_count=data.vcpu_count,
            memory_mb=data.memory_mb,
        )
        return await self.hosts.create(host)

    async def get_host(self, host_id: str) -> Host:
        host = await self.hosts.get(host_id)
        if host is None:
            raise HostNotFoundError(host_id)
        return host

    async def list_hosts(self) -> list[Host]:
        return await self.hosts.list()

    async def resize_host(
        self, host_id: str, vcpu_count: int, memory_mb: int
    ) -> tuple[Host, Action]:
        """Apply a real resize, persist it, and write an audit-log entry."""
        host = await self.get_host(host_id)
        before_vcpu, before_mem = host.vcpu_count, host.memory_mb

        vcpu_change = (before_vcpu - vcpu_count) / before_vcpu
        mem_change = (before_mem - memory_mb) / before_mem
        saving = round((vcpu_change + mem_change) / 2.0 * 100.0, 2)

        host.vcpu_count = vcpu_count
        host.memory_mb = memory_mb
        host = await self.hosts.update(host)

        verb = "Downsized" if saving > 0 else ("Upsized" if saving < 0 else "Kept")
        detail = (
            f"{verb} {host.hostname}: {before_vcpu}->{vcpu_count} vCPU, "
            f"{before_mem // 1024}->{memory_mb // 1024} GB "
            f"({saving:+.0f}% capacity)"
        )
        action = await self.actions.add(
            Action(
                id=str(uuid4()),
                host_id=host_id,
                action_type="RESIZE",
                detail=detail,
                before_vcpu=before_vcpu,
                after_vcpu=vcpu_count,
                before_memory_mb=before_mem,
                after_memory_mb=memory_mb,
                saving_pct=saving,
            )
        )
        return host, action

    async def list_actions(self, host_id: str) -> list[Action]:
        await self.get_host(host_id)
        return await self.actions.list_by_host(host_id)

    async def list_all_actions(self, limit: int = 200) -> list[Action]:
        """Fleet-wide audit log (most recent first) for the history view."""
        return await self.actions.list_all(limit)


class MetricService:
    def __init__(self, hosts: HostRepository, metrics: MetricRepository) -> None:
        self.hosts = hosts
        self.metrics = metrics

    async def ingest(self, host_id: str, samples: list[MetricIn]) -> int:
        await self._require_host(host_id)
        rows = [
            Metric(
                host_id=host_id,
                ts=s.ts,
                cpu_pct=s.cpu_pct,
                mem_pct=s.mem_pct,
                net_in_kbps=s.net_in_kbps,
                net_out_kbps=s.net_out_kbps,
            )
            for s in samples
        ]
        return await self.metrics.bulk_insert(rows)

    async def history(
        self, host_id: str, start: datetime | None, end: datetime | None
    ) -> list[Metric]:
        await self._require_host(host_id)
        return await self.metrics.list_by_host(host_id, start, end)

    async def _require_host(self, host_id: str) -> Host:
        host = await self.hosts.get(host_id)
        if host is None:
            raise HostNotFoundError(host_id)
        return host


class AnalysisService:
    def __init__(
        self,
        hosts: HostRepository,
        metrics: MetricRepository,
        analysis: AnalysisRepository,
        actions: ActionRepository,
    ) -> None:
        self.hosts = hosts
        self.metrics = metrics
        self.analysis = analysis
        self.actions = actions

    async def forecast(
        self,
        host_id: str,
        metric: MetricKind,
        horizon_minutes: int,
        log: bool = True,
    ) -> Forecast:
        host = await self._require_host(host_id)
        samples = await self.metrics.list_by_host(host_id)
        column = _METRIC_COLUMN[metric]
        series = [float(getattr(m, column)) for m in samples]
        if len(series) < 2:
            raise InsufficientDataError(host.id)

        horizon_steps = max(
            1, round(horizon_minutes / settings.sample_interval_minutes)
        )
        result = forecaster.forecast(
            series, period=settings.seasonal_period, horizon=horizon_steps
        )
        record = Forecast(
            id=str(uuid4()),
            host_id=host_id,
            metric=metric.value,
            horizon_minutes=horizon_minutes,
            model=result.model,
            predicted_value=result.predicted_value,
            lower_bound=result.lower_bound,
            upper_bound=result.upper_bound,
            mape=result.mape,
        )
        saved = await self.analysis.save_forecast(record)
        if log:
            mape_txt = "n/a" if result.mape is None else f"{result.mape:.1f}%"
            await self.actions.add(
                Action(
                    id=str(uuid4()),
                    host_id=host_id,
                    action_type="FORECAST",
                    detail=(
                        f"Forecast {metric.value} +{horizon_minutes}m on "
                        f"{host.hostname}: {result.predicted_value:.0f}% "
                        f"(MAPE {mape_txt})"
                    ),
                )
            )
        return saved

    async def recommend(self, host_id: str) -> Recommendation:
        host = await self._require_host(host_id)
        samples = await self.metrics.list_by_host(host_id)
        if not samples:
            raise InsufficientDataError(host.id)

        peak_cpu = optimizer.peak(
            [float(m.cpu_pct) for m in samples], settings.peak_percentile
        )
        peak_mem = optimizer.peak(
            [float(m.mem_pct) for m in samples], settings.peak_percentile
        )
        proposal = optimizer.recommend_resize(
            current_vcpu=host.vcpu_count,
            current_memory_mb=host.memory_mb,
            predicted_peak_cpu_pct=peak_cpu,
            predicted_peak_mem_pct=peak_mem,
            target_utilisation=settings.target_utilisation,
            safety_margin=settings.safety_margin,
            slo_confidence=settings.slo_confidence,
        )
        record = Recommendation(
            id=str(uuid4()),
            host_id=host_id,
            current_vcpu=proposal.current_vcpu,
            recommended_vcpu=proposal.recommended_vcpu,
            current_memory_mb=proposal.current_memory_mb,
            recommended_memory_mb=proposal.recommended_memory_mb,
            est_cost_saving_pct=proposal.est_cost_saving_pct,
            slo_confidence=proposal.slo_confidence,
        )
        return await self.analysis.save_recommendation(record)

    async def evaluate(self, host_id: str) -> evaluation.Evaluation:
        """Backtest the model against naive baselines + measure PI coverage."""
        host = await self._require_host(host_id)
        samples = await self.metrics.list_by_host(host_id)
        series = [float(m.cpu_pct) for m in samples]
        if len(series) < settings.seasonal_period * 2 + 2:
            raise InsufficientDataError(host.id)
        return evaluation.evaluate(series, period=settings.seasonal_period)

    async def _require_host(self, host_id: str) -> Host:
        host = await self.hosts.get(host_id)
        if host is None:
            raise HostNotFoundError(host_id)
        return host
