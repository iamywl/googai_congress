"""FastAPI dependency providers.

Services are assembled from repositories bound to a request-scoped session.
Tests override these providers with in-memory fakes, so the controllers can be
exercised without a live database.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..repositories import (
    ActionRepository,
    AnalysisRepository,
    HostRepository,
    MetricRepository,
)
from ..services import AnalysisService, HostService, MetricService
from ..services_gcp import GcpSyncService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_host_service(session: SessionDep) -> HostService:
    return HostService(HostRepository(session), ActionRepository(session))


def get_metric_service(session: SessionDep) -> MetricService:
    return MetricService(HostRepository(session), MetricRepository(session))


def get_analysis_service(session: SessionDep) -> AnalysisService:
    return AnalysisService(
        HostRepository(session),
        MetricRepository(session),
        AnalysisRepository(session),
        ActionRepository(session),
    )


def get_gcp_sync_service(session: SessionDep) -> GcpSyncService:
    return GcpSyncService(
        HostRepository(session),
        MetricRepository(session),
        ActionRepository(session),
    )


HostServiceDep = Annotated[HostService, Depends(get_host_service)]
MetricServiceDep = Annotated[MetricService, Depends(get_metric_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
GcpSyncServiceDep = Annotated[GcpSyncService, Depends(get_gcp_sync_service)]
