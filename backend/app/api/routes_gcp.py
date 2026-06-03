"""Real GCP fleet controller: Cloud Monitoring sync and real-VM resize."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ..config import settings
from ..integrations import gcp
from ..schemas import HostOut
from ..services import HostNotFoundError
from ..services_gcp import BudgetExceededError, NotARealHostError
from .deps import GcpSyncServiceDep

router = APIRouter(prefix="/api/v1/gcp", tags=["GCP"])


class InstanceOut(BaseModel):
    name: str
    zone: str
    machine_type: str
    vcpu: int
    memory_mb: int
    monthly_cost_krw: float


@router.get("/instances", response_model=list[InstanceOut])
async def list_instances(service: GcpSyncServiceDep) -> list[InstanceOut]:
    """Preview the labelled GCE instances and their estimated monthly cost."""
    try:
        instances = await service.list_instances()
    except gcp.GcpError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return [
        InstanceOut(
            name=i.name, zone=i.zone, machine_type=i.machine_type,
            vcpu=i.vcpu, memory_mb=i.memory_mb,
            monthly_cost_krw=round(
                gcp.monthly_cost_krw(i.machine_type, settings.krw_per_usd)
            ),
        )
        for i in instances
    ]


@router.post("/sync", response_model=list[HostOut])
async def sync(service: GcpSyncServiceDep) -> list[HostOut]:
    """Ingest labelled instances' CPU metrics from Cloud Monitoring."""
    try:
        hosts = await service.sync()
    except gcp.GcpError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return [HostOut.model_validate(h) for h in hosts]


@router.post("/hosts/{host_id}/resize", response_model=HostOut)
async def real_resize(
    host_id: str,
    service: GcpSyncServiceDep,
    machine_type: str = Query(..., description="Target GCP machine type"),
) -> HostOut:
    """Resize the real GCE VM (stop→setMachineType→start), budget-guarded."""
    try:
        host, _ = await service.real_resize(host_id, machine_type)
    except HostNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Host not found.") from exc
    except NotARealHostError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except BudgetExceededError as exc:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"'{exc}' exceeds the monthly budget ceiling "
            f"({settings.monthly_budget_krw:,.0f} KRW).",
        ) from exc
    except gcp.GcpError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return HostOut.model_validate(host)
