"""Fleet-wide history controller — the audit log across every host."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas import ActionOut
from .deps import HostServiceDep

router = APIRouter(prefix="/api/v1", tags=["History"])


@router.get("/actions", response_model=list[ActionOut])
async def list_all_actions(
    service: HostServiceDep,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[ActionOut]:
    """Every host's forecasts and resizes, most recent first."""
    actions = await service.list_all_actions(limit)
    return [ActionOut.model_validate(a) for a in actions]
