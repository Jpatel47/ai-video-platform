from app.domain.models.capability import CapabilityDefinition, CapabilityType
from app.domain.models.model_definition import ModelDefinition
from app.domain.models.provider import ProviderDefinition
from app.domain.models.workflow import WorkflowStage


class InMemoryCapabilityRegistry:
    def __init__(self, definitions: list[CapabilityDefinition]) -> None:
        self._definitions = {item.capability: item for item in definitions}

    def list_capabilities(self) -> list[CapabilityType]:
        return list(self._definitions.keys())

    def get_definition(self, capability: CapabilityType) -> CapabilityDefinition:
        return self._definitions[capability]


class InMemoryProviderRegistry:
    def __init__(self, providers: list[ProviderDefinition]) -> None:
        self._providers = {provider.slug: provider for provider in providers}

    def list_providers(self) -> list[ProviderDefinition]:
        return list(self._providers.values())

    def get_provider(self, slug: str) -> ProviderDefinition | None:
        return self._providers.get(slug)


class InMemoryModelRegistry:
    def __init__(self, models: list[ModelDefinition]) -> None:
        self._models = {model.slug: model for model in models}

    def list_models(self) -> list[ModelDefinition]:
        return list(self._models.values())

    def find_by_capability(self, capability: CapabilityType) -> list[ModelDefinition]:
        return [
            model
            for model in self._models.values()
            if any(item.capability == capability for item in model.capabilities)
        ]


class UnknownWorkflowTemplateError(KeyError):
    pass


class InMemoryWorkflowRegistry:
    def __init__(self, templates: dict[str, list[WorkflowStage]]) -> None:
        self._templates = templates

    def get_template(self, key: str) -> list[WorkflowStage]:
        if key not in self._templates:
            raise UnknownWorkflowTemplateError(f"Unknown workflow template '{key}'")
        return [stage.model_copy(deep=True) for stage in self._templates[key]]
