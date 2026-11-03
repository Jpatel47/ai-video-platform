from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models.model_definition import ExecutionMode


class ProviderKind(StrEnum):
    LOCAL_INFERENCE = "local_inference"
    COMFYUI = "comfyui"
    OLLAMA = "ollama"
    CLOUD_API = "cloud_api"
    INTERNAL_RENDERER = "internal_renderer"


class ProviderHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProviderDefinition(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slug: str
    display_name: str
    kind: ProviderKind
    execution_mode: ExecutionMode
    enabled: bool = True
    base_url: HttpUrl | None = None
    health: ProviderHealth = ProviderHealth.HEALTHY
    metadata: dict[str, str] = Field(default_factory=dict)
