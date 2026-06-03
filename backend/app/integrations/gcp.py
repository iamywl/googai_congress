"""Google Cloud integration: ingest real instance metrics and resize real VMs.

* Discovery + metrics: list Compute Engine instances carrying the configured
  label and pull their CPU utilisation from Cloud Monitoring.
* Resize: change a VM's machine type (stop → setMachineType → start), guarded by
  a hard monthly-cost ceiling and a protected-instance denylist.

The ``google-cloud-*`` clients are imported lazily so the app (and the unit
tests) run without the libraries or credentials present; callers get a clear
error only when a real GCP operation is actually attempted. On Cloud Run the
runtime service account supplies Application Default Credentials automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Approximate on-demand cost (USD/month, us-central1, 730h) and specs for the
# predefined machine types we create/resize within. Used for the cost guard and
# to map a machine type to (vcpu, memory_mb).
_MACHINE: dict[str, tuple[int, int, float]] = {
    # name: (vcpu, memory_mb, usd_per_month)
    "e2-micro": (2, 1024, 6.11),
    "e2-small": (2, 2048, 12.23),
    "e2-medium": (2, 4096, 24.46),
    "e2-standard-2": (2, 8192, 48.92),
    "e2-standard-4": (4, 16384, 97.83),
    "e2-standard-8": (8, 32768, 195.66),
    "n2-standard-2": (2, 8192, 70.18),
    "n2-standard-4": (4, 16384, 140.36),
}


@dataclass(frozen=True)
class GceInstance:
    name: str
    zone: str
    instance_id: str
    machine_type: str
    vcpu: int
    memory_mb: int


class GcpError(RuntimeError):
    """Raised when a real GCP operation cannot be completed."""


def machine_basename(machine_type_url: str) -> str:
    """Last path segment of a machineType URL/path (e.g. '.../e2-small' → 'e2-small')."""
    return machine_type_url.rstrip("/").rsplit("/", 1)[-1]


def specs_for(machine_type: str) -> tuple[int, int, float]:
    """(vcpu, memory_mb, usd_per_month) for a machine type; zeros if unknown."""
    return _MACHINE.get(machine_type, (0, 0, 0.0))


def monthly_cost_krw(machine_type: str, krw_per_usd: float) -> float:
    """Estimated monthly cost in KRW for a machine type (0 if unknown)."""
    return specs_for(machine_type)[2] * krw_per_usd


def within_budget(machine_type: str, budget_krw: float, krw_per_usd: float) -> bool:
    """True if the machine type's monthly cost is within the budget ceiling.

    An unknown machine type (cost 0) is treated as within budget=False to avoid
    silently resizing into an unpriced shape.
    """
    cost = monthly_cost_krw(machine_type, krw_per_usd)
    return 0 < cost <= budget_krw


def list_instances(project: str, label: str) -> list[GceInstance]:
    """List running instances carrying ``label=true`` across all zones."""
    try:
        from google.cloud import compute_v1
    except ImportError as exc:  # pragma: no cover - libs absent in unit tests
        raise GcpError("google-cloud-compute not installed") from exc

    client = compute_v1.InstancesClient()
    out: list[GceInstance] = []
    for zone, scoped in client.aggregated_list(project=project):
        for inst in scoped.instances or []:
            if (inst.labels or {}).get(label) != "true":
                continue
            mt = machine_basename(inst.machine_type)
            vcpu, mem, _ = specs_for(mt)
            out.append(GceInstance(
                name=inst.name,
                zone=zone.rsplit("/", 1)[-1],
                instance_id=str(inst.id),
                machine_type=mt,
                vcpu=vcpu or 1,
                memory_mb=mem or 1024,
            ))
    return out


def fetch_cpu_series(
    project: str, instance_id: str, hours: int, align_minutes: int = 60
) -> list[tuple[datetime, float]]:
    """Mean CPU utilisation (%) per ``align_minutes`` over the last ``hours``."""
    try:
        from google.cloud import monitoring_v3
    except ImportError as exc:  # pragma: no cover
        raise GcpError("google-cloud-monitoring not installed") from exc

    client = monitoring_v3.MetricServiceClient()
    now = datetime.now(UTC)
    interval = monitoring_v3.TimeInterval(
        end_time=now, start_time=now - timedelta(hours=hours)
    )
    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": align_minutes * 60},
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
    )
    flt = (
        'metric.type="compute.googleapis.com/instance/cpu/utilization" '
        f'AND resource.labels.instance_id="{instance_id}"'
    )
    series = client.list_time_series(
        request={
            "name": f"projects/{project}",
            "filter": flt,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": aggregation,
        }
    )
    points: list[tuple[datetime, float]] = []
    for ts in series:
        for p in ts.points:
            when = p.interval.end_time
            if not isinstance(when, datetime):
                when = when.replace(tzinfo=UTC) if hasattr(when, "replace") else now
            points.append((when, round(p.value.double_value * 100.0, 2)))
    points.sort(key=lambda x: x[0])
    return points


def resize_instance(project: str, zone: str, name: str, machine_type: str) -> None:
    """Change a VM's machine type: stop → setMachineType → start. Blocking."""
    try:
        from google.cloud import compute_v1
    except ImportError as exc:  # pragma: no cover
        raise GcpError("google-cloud-compute not installed") from exc

    client = compute_v1.InstancesClient()
    mt_path = f"zones/{zone}/machineTypes/{machine_type}"
    client.stop(project=project, zone=zone, instance=name).result()
    client.set_machine_type(
        project=project, zone=zone, instance=name,
        instances_set_machine_type_request_resource=compute_v1.InstancesSetMachineTypeRequest(
            machine_type=mt_path
        ),
    ).result()
    client.start(project=project, zone=zone, instance=name).result()
