"""Service layer for the real GCP fleet: Cloud Monitoring sync and real resize."""

from __future__ import annotations

from uuid import uuid4

from .config import settings
from .integrations import gcp
from .models import Action, Host, Metric
from .repositories import ActionRepository, HostRepository, MetricRepository
from .services import HostNotFoundError


class BudgetExceededError(Exception):
    """Raised when a real resize would exceed the monthly cost ceiling."""


class NotARealHostError(Exception):
    """Raised when a real-VM operation targets a demo (synthetic) host."""


def _protected() -> set[str]:
    return {n.strip() for n in settings.gcp_protected_instances.split(",") if n.strip()}


class GcpSyncService:
    def __init__(
        self,
        hosts: HostRepository,
        metrics: MetricRepository,
        actions: ActionRepository,
    ) -> None:
        self.hosts = hosts
        self.metrics = metrics
        self.actions = actions

    async def list_instances(self) -> list[gcp.GceInstance]:
        return gcp.list_instances(settings.gcp_project, settings.gcp_label)

    async def sync(self) -> list[Host]:
        """Discover labelled instances and ingest their recent CPU into the DB."""
        instances = gcp.list_instances(settings.gcp_project, settings.gcp_label)
        synced: list[Host] = []
        for inst in instances:
            host = await self.hosts.get_by_hostname(inst.name)
            if host is None:
                host = Host(
                    id=str(uuid4()), hostname=inst.name, environment="GCE",
                    vcpu_count=inst.vcpu, memory_mb=inst.memory_mb,
                    provider="gce", zone=inst.zone, machine_type=inst.machine_type,
                )
                await self.hosts.create(host)
            else:
                host.vcpu_count = inst.vcpu
                host.memory_mb = inst.memory_mb
                host.provider = "gce"
                host.zone = inst.zone
                host.machine_type = inst.machine_type
                await self.hosts.update(host)

            series = gcp.fetch_cpu_series(
                settings.gcp_project, inst.instance_id, settings.gcp_sync_hours
            )
            existing = {m.ts for m in await self.metrics.list_by_host(host.id)}
            rows = []
            for ts, cpu in series:
                naive = ts.replace(tzinfo=None)
                if naive in existing:
                    continue
                # Shared-core (e2) instances can momentarily report utilisation
                # above 100% during a burst; clamp to the metric's valid range.
                cpu = max(0.0, min(100.0, cpu))
                # Memory is unmonitored without the Ops Agent; store a CPU-linked
                # proxy so recommendations stay sensible (documented limitation).
                mem = max(0.0, min(95.0, round(cpu * 0.6 + 20.0, 2)))
                rows.append(Metric(
                    host_id=host.id, ts=naive, cpu_pct=cpu, mem_pct=mem,
                    net_in_kbps=0, net_out_kbps=0,
                ))
            if rows:
                await self.metrics.bulk_insert(rows)
            synced.append(host)
        return synced

    async def real_resize(self, host_id: str, machine_type: str) -> tuple[Host, Action]:
        """Resize the underlying GCE VM, guarded by budget + denylist."""
        host = await self.hosts.get(host_id)
        if host is None:
            raise HostNotFoundError(host_id)
        if host.provider != "gce" or not host.zone:
            raise NotARealHostError(host.hostname)
        if host.hostname in _protected():
            raise NotARealHostError(f"{host.hostname} is protected")
        if not gcp.within_budget(
            machine_type, settings.monthly_budget_krw, settings.krw_per_usd
        ):
            raise BudgetExceededError(machine_type)

        before_vcpu, before_mem = host.vcpu_count, host.memory_mb
        gcp.resize_instance(settings.gcp_project, host.zone, host.hostname, machine_type)

        vcpu, mem, _ = gcp.specs_for(machine_type)
        host.vcpu_count, host.memory_mb, host.machine_type = vcpu, mem, machine_type
        await self.hosts.update(host)

        saving = round(
            ((before_vcpu - vcpu) / before_vcpu + (before_mem - mem) / before_mem)
            / 2.0 * 100.0, 2
        )
        verb = "Downsized" if saving > 0 else ("Upsized" if saving < 0 else "Kept")
        action = await self.actions.add(Action(
            id=str(uuid4()), host_id=host_id, action_type="RESIZE",
            detail=(f"[REAL] {verb} {host.hostname} → {machine_type} "
                    f"({before_vcpu}->{vcpu} vCPU, {before_mem // 1024}->{mem // 1024} GB)"),
            before_vcpu=before_vcpu, after_vcpu=vcpu,
            before_memory_mb=before_mem, after_memory_mb=mem, saving_pct=saving,
        ))
        return host, action
