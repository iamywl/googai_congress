"""Machine-type catalogue controller.

Exposes the predefined GCP machine types the dashboard offers as resize targets.
The catalogue is static and dependency-free, so this route needs no database.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..core import machine_types
from ..schemas import MachineTypeOut

router = APIRouter(prefix="/api/v1", tags=["Catalog"])


@router.get("/machine-types", response_model=list[MachineTypeOut])
async def list_machine_types() -> list[MachineTypeOut]:
    """Return the predefined GCP machine types (vCPU / memory) for resizing."""
    return [MachineTypeOut.model_validate(m) for m in machine_types.CATALOG]
