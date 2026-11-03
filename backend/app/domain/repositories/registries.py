from typing import Protocol

from app.domain.models.capability import CapabilityDefinition, CapabilityType
from app.domain.models.model_definition import ModelDefinition
from app.domain.models.provider import ProviderDefinition
from app.domain.models.workflow import WorkflowStage


class CapabilityRegistry(Protocol):
    def list_capabilities(self) -> list[CapabilityType]:
        raise NotImplementedError

    def get_definition(self, capability: CapabilityType) -> CapabilityDefinition:
        raise NotImplementedError


class ProviderRegistry(Protocol):
    def list_providers(self) -> list[ProviderDefinition]:
        raise NotImplementedError

    def get_provider(self, slug: str) -> ProviderDefinition | None:
        raise NotImplementedError


class ModelRegistry(Protocol):
    def list_models(self) -> list[ModelDefinition]:
        raise NotImplementedError

    def find_by_capability(self, capability: CapabilityType) -> list[ModelDefinition]:
        raise NotImplementedError


class WorkflowRegistry(Protocol):
    def get_template(self, key: str) -> list[WorkflowStage]:
        raise NotImplementedError
