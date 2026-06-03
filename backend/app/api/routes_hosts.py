"""Host inventory controller."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..schemas import ActionOut, HostCreate, HostOut, ResizeRequest
from ..services import DuplicateHostError, HostNotFoundError
from .deps import HostServiceDep

router = APIRouter(prefix="/api/v1/hosts", tags=["Hosts"])


@router.post("", response_model=HostOut, status_code=status.HTTP_201_CREATED)
async def create_host(payload: HostCreate, service: HostServiceDep) -> HostOut:
    try:
        host = await service.create_host(payload)
    except DuplicateHostError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Host '{exc}' already exists.",
        ) from exc
    return HostOut.model_validate(host)


@router.get("", response_model=list[HostOut])
async def list_hosts(service: HostServiceDep) -> list[HostOut]:
    hosts = await service.list_hosts()
    return [HostOut.model_validate(h) for h in hosts]


@router.get("/{host_id}", response_model=HostOut)
async def get_host(host_id: str, service: HostServiceDep) -> HostOut:
    try:
        host = await service.get_host(host_id)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    return HostOut.model_validate(host)


@router.post("/{host_id}/resize", response_model=HostOut)
async def resize_host(
    host_id: str, payload: ResizeRequest, service: HostServiceDep
) -> HostOut:
    """Apply a real allocation change; the change is persisted and audit-logged."""
    try:
        host, _action = await service.resize_host(
            host_id, payload.vcpu_count, payload.memory_mb
        )
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    return HostOut.model_validate(host)


@router.get("/{host_id}/actions", response_model=list[ActionOut])
async def get_actions(host_id: str, service: HostServiceDep) -> list[ActionOut]:
    """Return the audit log (most recent first): forecasts run and resizes applied."""
    try:
        actions = await service.list_actions(host_id)
    except HostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        ) from exc
    return [ActionOut.model_validate(a) for a in actions]
