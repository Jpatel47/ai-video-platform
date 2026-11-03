from pydantic import BaseModel, Field

from app.domain.models.capability import CapabilityType
from app.domain.models.model_definition import ExecutionMode, ModelDefinition, QualityTier


class RoutingRequest(BaseModel):
    capability: CapabilityType
    quality: QualityTier = QualityTier.STANDARD
    preferred_execution_mode: ExecutionMode | None = None
    max_cost_units: float | None = Field(default=None, ge=0)
    require_character_reference: bool = False


class ModelRoute(BaseModel):
    capability: CapabilityType
    model: ModelDefinition
    score: float
    reason: str
