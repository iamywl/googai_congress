"""Google Compute Engine predefined machine-type catalogue.

A pure, dependency-free lookup table of the predefined GCE machine types the
dashboard can resize a host to. Each entry carries its vCPU count and memory so
the integer-programming recommendation can be *snapped* to a concrete, orderable
GCP instance rather than an abstract ``(vcpu, memory)`` pair.

The catalogue is intentionally a curated subset of the most common families
(E2 cost-optimised, N2 balanced, C2/C3 compute-optimised, plus highcpu/highmem
shapes); GCP also supports custom machine types, which the ``nearest_fit`` helper
approximates by selecting the smallest predefined type that satisfies a request.
"""

from __future__ import annotations

from dataclasses import dataclass

_GB = 1024  # MB per GB


@dataclass(frozen=True)
class MachineType:
    """A single predefined GCE machine type."""

    name: str
    series: str
    category: str
    vcpu: int
    memory_mb: int

    @property
    def memory_gb(self) -> int:
        return self.memory_mb // _GB


def _mt(name: str, series: str, category: str, vcpu: int, gb: int) -> MachineType:
    return MachineType(name, series, category, vcpu, gb * _GB)


# Curated catalogue, ordered from smallest to largest within each family.
CATALOG: tuple[MachineType, ...] = (
    # --- E2: cost-optimised general purpose ---
    _mt("e2-small", "E2", "General purpose (cost-optimised)", 2, 2),
    _mt("e2-medium", "E2", "General purpose (cost-optimised)", 2, 4),
    _mt("e2-standard-2", "E2", "General purpose (cost-optimised)", 2, 8),
    _mt("e2-standard-4", "E2", "General purpose (cost-optimised)", 4, 16),
    _mt("e2-standard-8", "E2", "General purpose (cost-optimised)", 8, 32),
    _mt("e2-standard-16", "E2", "General purpose (cost-optimised)", 16, 64),
    _mt("e2-standard-32", "E2", "General purpose (cost-optimised)", 32, 128),
    # --- N2: balanced general purpose ---
    _mt("n2-highcpu-8", "N2", "General purpose (high-CPU)", 8, 8),
    _mt("n2-highcpu-16", "N2", "General purpose (high-CPU)", 16, 16),
    _mt("n2-highcpu-32", "N2", "General purpose (high-CPU)", 32, 32),
    _mt("n2-standard-2", "N2", "General purpose (balanced)", 2, 8),
    _mt("n2-standard-4", "N2", "General purpose (balanced)", 4, 16),
    _mt("n2-standard-8", "N2", "General purpose (balanced)", 8, 32),
    _mt("n2-standard-16", "N2", "General purpose (balanced)", 16, 64),
    _mt("n2-standard-32", "N2", "General purpose (balanced)", 32, 128),
    _mt("n2-standard-48", "N2", "General purpose (balanced)", 48, 192),
    _mt("n2-standard-64", "N2", "General purpose (balanced)", 64, 256),
    _mt("n2-standard-80", "N2", "General purpose (balanced)", 80, 320),
    _mt("n2-highmem-8", "N2", "General purpose (high-memory)", 8, 64),
    _mt("n2-highmem-16", "N2", "General purpose (high-memory)", 16, 128),
    _mt("n2-highmem-32", "N2", "General purpose (high-memory)", 32, 256),
    # --- C2: compute-optimised ---
    _mt("c2-standard-4", "C2", "Compute-optimised", 4, 16),
    _mt("c2-standard-8", "C2", "Compute-optimised", 8, 32),
    _mt("c2-standard-16", "C2", "Compute-optimised", 16, 64),
    _mt("c2-standard-30", "C2", "Compute-optimised", 30, 120),
    _mt("c2-standard-60", "C2", "Compute-optimised", 60, 240),
    # --- C3: latest-generation compute-optimised ---
    _mt("c3-standard-4", "C3", "Compute-optimised (latest gen)", 4, 16),
    _mt("c3-standard-8", "C3", "Compute-optimised (latest gen)", 8, 32),
    _mt("c3-standard-22", "C3", "Compute-optimised (latest gen)", 22, 88),
    _mt("c3-standard-44", "C3", "Compute-optimised (latest gen)", 44, 176),
    _mt("c3-standard-88", "C3", "Compute-optimised (latest gen)", 88, 352),
)


def exact_match(vcpu: int, memory_mb: int) -> MachineType | None:
    """Return the predefined type whose specs match exactly, else ``None``."""
    for mt in CATALOG:
        if mt.vcpu == vcpu and mt.memory_mb == memory_mb:
            return mt
    return None


def nearest_fit(vcpu: int, memory_mb: int) -> MachineType:
    """Smallest predefined type that satisfies both vCPU and memory demand.

    "Smallest" minimises vCPU first, then memory — a proxy for the cheapest
    instance that still covers the requested capacity. If no predefined type is
    large enough, the largest in the catalogue is returned.
    """
    fits = [m for m in CATALOG if m.vcpu >= vcpu and m.memory_mb >= memory_mb]
    if fits:
        return min(fits, key=lambda m: (m.vcpu, m.memory_mb, m.name))
    return max(CATALOG, key=lambda m: (m.vcpu, m.memory_mb))


def describe(vcpu: int, memory_mb: int) -> MachineType:
    """Best label for an arbitrary allocation: exact match if any, else nearest fit."""
    return exact_match(vcpu, memory_mb) or nearest_fit(vcpu, memory_mb)
