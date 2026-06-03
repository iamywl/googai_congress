"""Forecast and resizing-recommendation controller."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..schemas import ForecastOut, MetricKind, RecommendationOut
from ..services import HostNotFoundError, InsufficientDataError
from .deps import AnalysisServiceDep

router = APIRouter(prefix="/api/v1/hosts/{host_id}", tags=["Analysis"])


@router.post("/forecast", response_model=ForecastOut)
async def create_forecast(
    host_id: str,
    service: AnalysisServiceDep,
    metric: MetricKind = Query(default=MetricKind.CPU),
    horizon_minutes: int = Query(default=60, ge=1, le=10080),
    log: bool = Query(default=True),
) -> ForecastOut:
    try:
        forecast = await service.forecast(host_id, metric, horizon_minutes, log=log)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough metric history to forecast.",
        ) from exc
    return ForecastOut.model_validate(forecast)


@router.post("/recommendation", response_model=RecommendationOut)
async def create_recommendation(
    host_id: str, service: AnalysisServiceDep
) -> RecommendationOut:
    try:
        rec = await service.recommend(host_id)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough metric history to recommend a resize.",
        ) from exc
    return RecommendationOut.model_validate(rec)
