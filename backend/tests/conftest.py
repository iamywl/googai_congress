"""Test harness: exercise the real controllers/services/core against in-memory
repositories, so the full request path runs without a live database."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.models import Action, Forecast, Host, Metric, Recommendation
from app.services import AnalysisService, HostService, MetricService

_UTC = UTC


class FakeHostRepository:
    def __init__(self, store: dict[str, Host]) -> None:
        self.store = store

    async def create(self, host: Host) -> Host:
        host.created_at = datetime.now(_UTC)
        self.store[host.id] = host
        return host

    async def get(self, host_id: str) -> Host | None:
        return self.store.get(host_id)

    async def get_by_hostname(self, hostname: str) -> Host | None:
        return next((h for h in self.store.values() if h.hostname == hostname), None)

    async def list(self) -> list[Host]:
        return sorted(self.store.values(), key=lambda h: h.hostname)

    async def update(self, host: Host) -> Host:
        self.store[host.id] = host
        return host


class FakeMetricRepository:
    def __init__(self, store: list[Metric]) -> None:
        self.store = store

    async def bulk_insert(self, metrics: list[Metric]) -> int:
        self.store.extend(metrics)
        return len(metrics)

    async def list_by_host(self, host_id, start=None, end=None) -> list[Metric]:
        rows = [m for m in self.store if m.host_id == host_id]
        if start is not None:
            rows = [m for m in rows if m.ts >= start]
        if end is not None:
            rows = [m for m in rows if m.ts <= end]
        return sorted(rows, key=lambda m: m.ts)


class FakeAnalysisRepository:
    async def save_forecast(self, forecast: Forecast) -> Forecast:
        forecast.generated_at = datetime.now(_UTC)
        return forecast

    async def save_recommendation(self, rec: Recommendation) -> Recommendation:
        rec.generated_at = datetime.now(_UTC)
        return rec


class FakeActionRepository:
    def __init__(self, store: list[Action]) -> None:
        self.store = store

    async def add(self, action: Action) -> Action:
        action.ts = datetime.now(_UTC)
        self.store.append(action)
        return action

    async def list_by_host(self, host_id: str, limit: int = 50) -> list[Action]:
        rows = [a for a in self.store if a.host_id == host_id]
        return sorted(rows, key=lambda a: a.ts, reverse=True)[:limit]

    async def list_all(self, limit: int = 200) -> list[Action]:
        return sorted(self.store, key=lambda a: a.ts, reverse=True)[:limit]


@pytest.fixture
def client() -> Iterator[TestClient]:
    host_store: dict[str, Host] = {}
    metric_store: list[Metric] = []
    action_store: list[Action] = []
    host_repo = FakeHostRepository(host_store)
    metric_repo = FakeMetricRepository(metric_store)
    analysis_repo = FakeAnalysisRepository()
    action_repo = FakeActionRepository(action_store)

    app.dependency_overrides[deps.get_host_service] = lambda: HostService(
        host_repo, action_repo
    )
    app.dependency_overrides[deps.get_metric_service] = lambda: MetricService(
        host_repo, metric_repo
    )
    app.dependency_overrides[deps.get_analysis_service] = lambda: AnalysisService(
        host_repo, metric_repo, analysis_repo, action_repo
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def seeded_host(client: TestClient) -> dict:
    """Create a host and feed it two clean daily cycles of seasonal metrics."""
    resp = client.post(
        "/api/v1/hosts",
        json={
            "hostname": "web-prod-01",
            "environment": "PROD",
            "vcpu_count": 16,
            "memory_mb": 32768,
        },
    )
    assert resp.status_code == 201, resp.text
    host = resp.json()

    daily = [12, 10, 9, 8, 8, 9, 14, 25, 45, 58, 66, 72,
             78, 82, 85, 80, 70, 60, 48, 38, 30, 24, 18, 14]
    base = datetime(2024, 1, 1, tzinfo=_UTC)
    samples = []
    for i in range(48):
        cpu = daily[i % 24]
        samples.append(
            {
                "ts": (base + timedelta(hours=i)).isoformat(),
                "cpu_pct": cpu,
                "mem_pct": min(100, cpu * 0.7 + 20),
                "net_in_kbps": cpu * 120 + 50,
                "net_out_kbps": cpu * 80 + 30,
            }
        )
    ingest = client.post(f"/api/v1/hosts/{host['id']}/metrics", json=samples)
    assert ingest.status_code == 202, ingest.text
    return host
