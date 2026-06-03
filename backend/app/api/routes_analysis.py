"""Forecast and resizing-recommendation controller."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..core import machine_types
from ..schemas import (
    EvaluationOut,
    ForecastOut,
    MachineTypeOut,
    MetricKind,
    MetricsOut,
    RecommendationOut,
)
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
    out = RecommendationOut.model_validate(rec)
    # Snap the abstract (vcpu, memory) figures to concrete GCP instances.
    out.current_machine_type = MachineTypeOut.model_validate(
        machine_types.describe(rec.current_vcpu, rec.current_memory_mb)
    )
    out.recommended_machine_type = MachineTypeOut.model_validate(
        machine_types.nearest_fit(rec.recommended_vcpu, rec.recommended_memory_mb)
    )
    return out


@router.post("/evaluation", response_model=EvaluationOut)
async def evaluate_model(
    host_id: str, service: AnalysisServiceDep
) -> EvaluationOut:
    """Backtest the forecaster vs naive baselines and report interval coverage."""
    try:
        ev = await service.evaluate(host_id)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough metric history to evaluate the model.",
        ) from exc
    return EvaluationOut(
        host_id=host_id,
        model=MetricsOut(**ev.model.__dict__),
        naive=MetricsOut(**ev.naive.__dict__),
        seasonal_naive=MetricsOut(**ev.seasonal_naive.__dict__),
        coverage=ev.coverage,
        beats_naive=ev.beats_naive,
        beats_seasonal_naive=ev.beats_seasonal_naive,
    )
