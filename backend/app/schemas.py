"""Pydantic request/response schemas — the API's validation boundary."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Environment(str, Enum):
    PROD = "PROD"
    STAGING = "STAGING"
    DEV = "DEV"


class MetricKind(str, Enum):
    CPU = "CPU"
    MEM = "MEM"
    NET_IN = "NET_IN"
    NET_OUT = "NET_OUT"


class HostCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    environment: Environment = Environment.PROD
    vcpu_count: int = Field(ge=1, le=256)
    memory_mb: int = Field(ge=256, le=4_194_304)


class HostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hostname: str
    environment: str
    vcpu_count: int
    memory_mb: int
    created_at: datetime


class MetricIn(BaseModel):
    ts: datetime
    cpu_pct: float = Field(ge=0, le=100)
    mem_pct: float = Field(ge=0, le=100)
    net_in_kbps: float = Field(ge=0)
    net_out_kbps: float = Field(ge=0)


class MetricOut(MetricIn):
    model_config = ConfigDict(from_attributes=True)

    host_id: str


class IngestResult(BaseModel):
    host_id: str
    ingested: int


class ForecastOut(BaseModel):
    # `model` is a legitimate domain field; opt out of Pydantic's model_ guard.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    host_id: str
    metric: str
    generated_at: datetime
    horizon_minutes: int
    model: str
    predicted_value: float
    lower_bound: float
    upper_bound: float
    mape: float | None


class ResizeRequest(BaseModel):
    vcpu_count: int = Field(ge=1, le=256)
    memory_mb: int = Field(ge=256, le=4_194_304)


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    host_id: str
    ts: datetime
    action_type: str
    detail: str
    before_vcpu: int | None
    after_vcpu: int | None
    before_memory_mb: int | None
    after_memory_mb: int | None
    saving_pct: float | None


class MachineTypeOut(BaseModel):
    """A predefined GCP machine type the UI can target for a resize."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    series: str
    category: str
    vcpu: int
    memory_mb: int


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    host_id: str
    generated_at: datetime
    current_vcpu: int
    recommended_vcpu: int
    current_memory_mb: int
    recommended_memory_mb: int
    est_cost_saving_pct: float
    slo_confidence: float
    # Nearest predefined GCP instances, attached by the controller (computed,
    # not persisted) so the dashboard can name the before/after machine type.
    current_machine_type: MachineTypeOut | None = None
    recommended_machine_type: MachineTypeOut | None = None
