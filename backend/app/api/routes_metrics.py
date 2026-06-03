"""Metric ingestion and time-range query controller."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from ..schemas import IngestResult, MetricIn, MetricOut
from ..services import HostNotFoundError
from .deps import MetricServiceDep

router = APIRouter(prefix="/api/v1/hosts/{host_id}/metrics", tags=["Metrics"])


@router.post("", response_model=IngestResult, status_code=status.HTTP_202_ACCEPTED)
async def ingest_metrics(
    host_id: str, samples: list[MetricIn], service: MetricServiceDep
) -> IngestResult:
    try:
        count = await service.ingest(host_id, samples)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    return IngestResult(host_id=host_id, ingested=count)


@router.get("", response_model=list[MetricOut])
async def get_metrics(
    host_id: str,
    service: MetricServiceDep,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[MetricOut]:
    try:
        rows = await service.history(host_id, start, end)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    return [MetricOut.model_validate(r) for r in rows]
