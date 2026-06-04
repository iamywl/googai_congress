"""Live scale-out test orchestration for the dashboard demo.

A single in-memory session (one demo user on a scale-to-zero instance) drives a
deterministic, compressed timeline. As the timeline crosses milestones the
service persists real rows -- a clearly test-named Host, its Metric trace, and
FORECAST/RESIZE Action audit entries -- so the demo also shows up in the fleet
list and the History view, not just the live chart.

Two modes:
- ``sim``  : everything is simulated locally (instant, free, repeatable).
- ``real`` : actually create / resize a labelled GCE test node via the existing
             GcpSyncService, while the same timeline drives the visualisation.

The test node is NEVER auto-removed; teardown is an explicit action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .core import livetest
from .models import Action, Host, Metric
from .repositories import ActionRepository, HostRepository, MetricRepository

SIM_HOSTNAME = "loadtest-sim-01"        # name makes the test purpose obvious
REAL_HOSTNAME = "ml-testnode"           # matches the GcpSyncService test node


@dataclass
class _Session:
    mode: str
    t0: datetime
    host_id: str
    hostname: str
    scaled_done: bool = False
    metrics_done: bool = False


# Module-level singleton session (demo is single-user).
_SESSION: _Session | None = None


class LiveTestService:
    def __init__(
        self,
        hosts: HostRepository,
        metrics: MetricRepository,
        actions: ActionRepository,
    ) -> None:
        self.hosts = hosts
        self.metrics = metrics
        self.actions = actions

    # ---- lifecycle ---------------------------------------------------------
    async def start(self, mode: str = "sim") -> dict:
        global _SESSION
        mode = "real" if mode == "real" else "sim"
        hostname = REAL_HOSTNAME if mode == "real" else SIM_HOSTNAME

        host = await self.hosts.get_by_hostname(hostname)
        if host is None:
            host = await self.hosts.create(Host(
                id=str(uuid4()), hostname=hostname, environment="TEST",
                vcpu_count=livetest.PRE["vcpu"], memory_mb=livetest.PRE["memory_mb"],
                provider="sim" if mode == "sim" else "gce",
                machine_type=livetest.PRE["machine_type"],
            ))
        else:
            # re-arm: clear the prior run's trace and reset to the pre-scale spec
            await self.metrics.delete_by_host(host.id)
            await self.actions.delete_by_host(host.id)
            host.environment = "TEST"
            host.vcpu_count = livetest.PRE["vcpu"]
            host.memory_mb = livetest.PRE["memory_mb"]
            host.machine_type = livetest.PRE["machine_type"]
            host = await self.hosts.update(host)

        if mode == "real":
            self._real_launch()

        _SESSION = _Session(mode=mode, t0=datetime.now(UTC), host_id=host.id, hostname=hostname)
        return await self.state()

    async def state(self) -> dict:
        if _SESSION is None:
            return {"active": False}
        elapsed = (datetime.now(UTC) - _SESSION.t0).total_seconds()
        st = livetest.simulate(elapsed)

        # milestone persistence: forecast + scale-up
        if st.scaled and not _SESSION.scaled_done:
            await self._persist_scaleup()
            _SESSION.scaled_done = True
        # final persistence: write the whole metric trace once, at the end
        if st.done and not _SESSION.metrics_done:
            await self._persist_metrics(st)
            _SESSION.metrics_done = True

        out = st.to_dict()
        out.update({
            "active": True, "mode": _SESSION.mode,
            "node": {"hostname": _SESSION.hostname, "host_id": _SESSION.host_id,
                     "status": st.node_status, **st.spec},
        })
        if _SESSION.mode == "real":
            out["node"]["status"] = self._real_status() or st.node_status
        return out

    async def stop(self) -> dict:
        """End the run but keep the node and its data (explicit teardown only)."""
        global _SESSION
        _SESSION = None
        return {"active": False}

    async def teardown(self) -> dict:
        """Explicitly remove the test node and all of its demo data."""
        global _SESSION
        mode = _SESSION.mode if _SESSION else "sim"
        hostname = REAL_HOSTNAME if mode == "real" else SIM_HOSTNAME
        host = await self.hosts.get_by_hostname(hostname)
        removed = False
        if host is not None:
            await self.metrics.delete_by_host(host.id)
            await self.actions.delete_by_host(host.id)
            await self.hosts.delete(host.id)
            removed = True
        if mode == "real":
            self._real_delete()
        _SESSION = None
        return {"active": False, "removed": removed, "hostname": hostname}

    # ---- persistence of milestones ----------------------------------------
    async def _persist_scaleup(self) -> None:
        host = await self.hosts.get(_SESSION.host_id)
        if host is None:
            return
        pre, post = livetest.PRE, livetest.POST
        await self.actions.add(Action(
            id=str(uuid4()), host_id=host.id, action_type="FORECAST",
            detail=(f"Forecast: CPU peak ~108% predicted on {host.hostname} "
                    f"(ceiling {int(livetest.THRESHOLD)}%) -> scale-up recommended"),
        ))
        host.vcpu_count = post["vcpu"]
        host.memory_mb = post["memory_mb"]
        host.machine_type = post["machine_type"]
        await self.hosts.update(host)
        saving = round(((pre["vcpu"] - post["vcpu"]) / pre["vcpu"]
                        + (pre["memory_mb"] - post["memory_mb"]) / pre["memory_mb"]) / 2 * 100, 2)
        await self.actions.add(Action(
            id=str(uuid4()), host_id=host.id, action_type="RESIZE",
            detail=(f"Scaled up {host.hostname}: {pre['machine_type']} -> {post['machine_type']} "
                    f"({pre['vcpu']}->{post['vcpu']} vCPU, "
                    f"{pre['memory_mb'] // 1024}->{post['memory_mb'] // 1024} GB)"),
            before_vcpu=pre["vcpu"], after_vcpu=post["vcpu"],
            before_memory_mb=pre["memory_mb"], after_memory_mb=post["memory_mb"],
            saving_pct=saving,
        ))
        if _SESSION.mode == "real":
            self._real_resize()

    async def _persist_metrics(self, st: livetest.State) -> None:
        """Write the simulated trace as 1-minute samples ending now."""
        pts = st.series
        if not pts:
            return
        now = datetime.now(UTC)
        rows: list[Metric] = []
        n = len(pts)
        for i, (_minute, cpu) in enumerate(pts):
            ts = now - timedelta(minutes=(n - 1 - i))
            rows.append(Metric(
                host_id=_SESSION.host_id, ts=ts, cpu_pct=cpu,
                mem_pct=round(min(95.0, cpu * 0.6 + 18.0), 1),
                net_in_kbps=round(120.0 + cpu * 9.0, 1),
                net_out_kbps=round(90.0 + cpu * 6.0, 1),
            ))
        await self.metrics.bulk_insert(rows)

    # ---- real GCP mode (best-effort; reuses existing integration) ----------
    def _gcp(self):
        from .integrations import gcp
        return gcp

    def _real_launch(self) -> None:
        from .config import settings
        try:
            gcp = self._gcp()
            if gcp.within_budget(livetest.PRE["machine_type"],
                                 settings.monthly_budget_krw, settings.krw_per_usd):
                gcp.create_instance(settings.gcp_project, settings.gcp_zone,
                                    REAL_HOSTNAME, livetest.PRE["machine_type"], settings.gcp_label)
        except Exception:  # noqa: BLE001 - real GCP is optional; sim view still works
            pass

    def _real_status(self) -> str | None:
        from .config import settings
        try:
            return self._gcp().instance_status(
                settings.gcp_project, settings.gcp_zone, REAL_HOSTNAME)
        except Exception:  # noqa: BLE001
            return None

    def _real_resize(self) -> None:
        from .config import settings
        try:
            self._gcp().resize_instance(settings.gcp_project, settings.gcp_zone,
                                        REAL_HOSTNAME, livetest.POST["machine_type"])
        except Exception:  # noqa: BLE001
            pass

    def _real_delete(self) -> None:
        from .config import settings
        try:
            self._gcp().delete_instance(settings.gcp_project, settings.gcp_zone, REAL_HOSTNAME)
        except Exception:  # noqa: BLE001
            pass
