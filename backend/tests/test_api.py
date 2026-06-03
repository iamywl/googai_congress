"""End-to-end API tests over the real controller/service/core stack."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_is_db_free(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_fetch_host(client: TestClient):
    resp = client.post(
        "/api/v1/hosts",
        json={
            "hostname": "db-staging-02",
            "environment": "STAGING",
            "vcpu_count": 8,
            "memory_mb": 16384,
        },
    )
    assert resp.status_code == 201
    host = resp.json()
    assert host["hostname"] == "db-staging-02"
    assert host["id"]

    fetched = client.get(f"/api/v1/hosts/{host['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["environment"] == "STAGING"


def test_duplicate_hostname_conflicts(client: TestClient):
    body = {"hostname": "dup", "vcpu_count": 1, "memory_mb": 256}
    assert client.post("/api/v1/hosts", json=body).status_code == 201
    assert client.post("/api/v1/hosts", json=body).status_code == 409


def test_host_validation_boundary(client: TestClient):
    # vcpu_count below the documented minimum (1) must be rejected.
    resp = client.post(
        "/api/v1/hosts",
        json={"hostname": "bad", "vcpu_count": 0, "memory_mb": 256},
    )
    assert resp.status_code == 422


def test_unknown_host_returns_404(client: TestClient):
    assert client.get("/api/v1/hosts/does-not-exist").status_code == 404


def test_metric_ingest_and_query(client: TestClient, seeded_host: dict):
    rows = client.get(f"/api/v1/hosts/{seeded_host['id']}/metrics")
    assert rows.status_code == 200
    assert len(rows.json()) == 48


def test_ingest_to_unknown_host_404(client: TestClient):
    resp = client.post(
        "/api/v1/hosts/ghost/metrics",
        json=[{
            "ts": "2024-01-01T00:00:00Z",
            "cpu_pct": 10, "mem_pct": 10,
            "net_in_kbps": 1, "net_out_kbps": 1,
        }],
    )
    assert resp.status_code == 404


def test_forecast_endpoint(client: TestClient, seeded_host: dict):
    resp = client.post(
        f"/api/v1/hosts/{seeded_host['id']}/forecast",
        params={"metric": "CPU", "horizon_minutes": 60},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["metric"] == "CPU"
    assert body["lower_bound"] <= body["predicted_value"] <= body["upper_bound"]
    assert body["mape"] is not None and body["mape"] >= 0


def test_forecast_without_data_is_422(client: TestClient):
    host = client.post(
        "/api/v1/hosts",
        json={"hostname": "empty", "vcpu_count": 2, "memory_mb": 4096},
    ).json()
    resp = client.post(f"/api/v1/hosts/{host['id']}/forecast")
    assert resp.status_code == 422


def test_recommendation_proposes_downsize(client: TestClient, seeded_host: dict):
    resp = client.post(f"/api/v1/hosts/{seeded_host['id']}/recommendation")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Peak CPU in the seed tops out at 85% of 16 vCPU -> headroom exists.
    assert body["recommended_vcpu"] <= body["current_vcpu"]
    assert body["slo_confidence"] == 99.9


def test_resize_persists_and_logs(client: TestClient, seeded_host: dict):
    hid = seeded_host["id"]
    resp = client.post(
        f"/api/v1/hosts/{hid}/resize",
        json={"vcpu_count": 8, "memory_mb": 16384},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["vcpu_count"] == 8

    # The change is persisted on the host record.
    assert client.get(f"/api/v1/hosts/{hid}").json()["vcpu_count"] == 8

    # ...and an audit-log RESIZE entry was recorded.
    actions = client.get(f"/api/v1/hosts/{hid}/actions").json()
    resize = [a for a in actions if a["action_type"] == "RESIZE"]
    assert resize, actions
    assert resize[0]["before_vcpu"] == 16
    assert resize[0]["after_vcpu"] == 8
    assert resize[0]["saving_pct"] > 0


def test_forecast_is_logged(client: TestClient, seeded_host: dict):
    hid = seeded_host["id"]
    client.post(f"/api/v1/hosts/{hid}/forecast")
    actions = client.get(f"/api/v1/hosts/{hid}/actions").json()
    assert any(a["action_type"] == "FORECAST" for a in actions)


def test_resize_validation(client: TestClient, seeded_host: dict):
    resp = client.post(
        f"/api/v1/hosts/{seeded_host['id']}/resize",
        json={"vcpu_count": 0, "memory_mb": 16384},
    )
    assert resp.status_code == 422


def test_fleet_wide_actions_feed(client: TestClient, seeded_host: dict):
    hid = seeded_host["id"]
    # Generate one action of each kind, then read the global feed.
    client.post(f"/api/v1/hosts/{hid}/forecast")
    client.post(f"/api/v1/hosts/{hid}/resize", json={"vcpu_count": 8, "memory_mb": 8192})
    resp = client.get("/api/v1/actions")
    assert resp.status_code == 200
    feed = resp.json()
    assert len(feed) >= 2
    kinds = {a["action_type"] for a in feed}
    assert {"FORECAST", "RESIZE"} <= kinds
    # limit is honoured
    assert len(client.get("/api/v1/actions?limit=1").json()) == 1
