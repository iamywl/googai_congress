"""Data-access layer (Repository pattern).

Each repository wraps a single :class:`AsyncSession` and is the only place SQL
is issued. Services depend on these classes, never on the session directly,
keeping persistence concerns isolated from business logic.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Action, Forecast, Host, Metric, Recommendation


class HostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, host: Host) -> Host:
        self.session.add(host)
        await self.session.commit()
        await self.session.refresh(host)
        return host

    async def get(self, host_id: str) -> Host | None:
        return await self.session.get(Host, host_id)

    async def get_by_hostname(self, hostname: str) -> Host | None:
        result = await self.session.execute(
            select(Host).where(Host.hostname == hostname)
        )
        return result.scalar_one_or_none()

    async def list(self) -> list[Host]:
        result = await self.session.execute(select(Host).order_by(Host.hostname))
        return list(result.scalars().all())

    async def update(self, host: Host) -> Host:
        await self.session.commit()
        await self.session.refresh(host)
        return host

    async def delete(self, host_id: str) -> None:
        host = await self.session.get(Host, host_id)
        if host is not None:
            await self.session.delete(host)
            await self.session.commit()


class MetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_insert(self, metrics: list[Metric]) -> int:
        self.session.add_all(metrics)
        await self.session.commit()
        return len(metrics)

    async def delete_by_host(self, host_id: str) -> None:
        await self.session.execute(sql_delete(Metric).where(Metric.host_id == host_id))
        await self.session.commit()

    async def list_by_host(
        self,
        host_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Metric]:
        query = select(Metric).where(Metric.host_id == host_id)
        if start is not None:
            query = query.where(Metric.ts >= start)
        if end is not None:
            query = query.where(Metric.ts <= end)
        query = query.order_by(Metric.ts.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_forecast(self, forecast: Forecast) -> Forecast:
        self.session.add(forecast)
        await self.session.commit()
        await self.session.refresh(forecast)
        return forecast

    async def save_recommendation(self, rec: Recommendation) -> Recommendation:
        self.session.add(rec)
        await self.session.commit()
        await self.session.refresh(rec)
        return rec


class ActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, action: Action) -> Action:
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def delete_by_host(self, host_id: str) -> None:
        await self.session.execute(sql_delete(Action).where(Action.host_id == host_id))
        await self.session.commit()

    async def list_by_host(self, host_id: str, limit: int = 50) -> list[Action]:
        result = await self.session.execute(
            select(Action)
            .where(Action.host_id == host_id)
            .order_by(Action.ts.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 200) -> list[Action]:
        """Every host's actions, most recent first — for the history view."""
        result = await self.session.execute(
            select(Action).order_by(Action.ts.desc()).limit(limit)
        )
        return list(result.scalars().all())
