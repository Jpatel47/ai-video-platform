from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models.capability import CapabilityType


class ExecutionMode(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class QualityTier(StrEnum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    CINEMATIC = "cinematic"


class ModelCapability(BaseModel):
    capability: CapabilityType
    quality_tier: QualityTier
    estimated_cost_units: float = Field(ge=0)
    estimated_latency_seconds: int = Field(ge=0)
    max_duration_seconds: int | None = Field(default=None, ge=1)
    supports_character_reference: bool = False
    supports_negative_prompt: bool = True


class ModelDefinition(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slug: str
    display_name: str
    provider_slug: str
    execution_mode: ExecutionMode
    capabilities: list[ModelCapability]
    enabled: bool = True
    endpoint_url: HttpUrl | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
