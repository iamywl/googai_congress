"""Live scale-out test controller (dashboard demo).

Start a run (sim or real), poll its state for the animated chart, stop it, or
explicitly tear down the test node. State is returned as a plain JSON object the
dashboard renders directly.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..repositories import ActionRepository, HostRepository, MetricRepository
from ..services_livetest import LiveTestService
from .deps import SessionDep

router = APIRouter(prefix="/api/v1/livetest", tags=["LiveTest"])


def get_livetest_service(session: SessionDep) -> LiveTestService:
    return LiveTestService(
        HostRepository(session), MetricRepository(session), ActionRepository(session)
    )


LiveTestServiceDep = Annotated[LiveTestService, Depends(get_livetest_service)]


@router.post("/start")
async def start(svc: LiveTestServiceDep, mode: str = Query("sim", pattern="^(sim|real)$")) -> dict:
    return await svc.start(mode)


@router.get("/state")
async def state(svc: LiveTestServiceDep) -> dict:
    return await svc.state()


@router.post("/stop")
async def stop(svc: LiveTestServiceDep) -> dict:
    return await svc.stop()


@router.post("/teardown")
async def teardown(svc: LiveTestServiceDep) -> dict:
    return await svc.teardown()
