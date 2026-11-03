from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.models.capability import CapabilityType
from app.domain.models.model_definition import ExecutionMode, QualityTier
from app.domain.models.routing import ModelRoute


class WorkflowStatus(StrEnum):
    PLANNED = "planned"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    quality: QualityTier = QualityTier.STANDARD
    preferred_execution_mode: ExecutionMode | None = None
    target_duration_seconds: int = Field(default=60, ge=5, le=3600)
    target_audience: str | None = None
    language: str = "en"
    brand_profile_id: UUID | None = None


class WorkflowStage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str
    label: str
    required_capability: CapabilityType
    depends_on: list[str] = Field(default_factory=list)
    route: ModelRoute | None = None
    estimated_latency_seconds: int = 0
    estimated_cost_units: float = 0


class WorkflowPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: WorkflowStatus = WorkflowStatus.PLANNED
    request: WorkflowRequest
    stages: list[WorkflowStage]
    total_estimated_latency_seconds: int
    total_estimated_cost_units: float
    director_summary: str


class StageStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    stage_key: str
    label: str
    model_slug: str
    provider_slug: str
    status: StageStatus
    output: dict[str, object] = Field(default_factory=dict)
    error: str | None = None


class WorkflowRunResult(BaseModel):
    plan_id: UUID
    status: WorkflowStatus
    stage_results: list[StageResult]
    director_summary: str
