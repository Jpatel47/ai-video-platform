from app.domain.models.model_definition import (
    ExecutionMode,
    ModelCapability,
    ModelDefinition,
    QualityTier,
)
from app.domain.models.provider import ProviderHealth
from app.domain.models.routing import ModelRoute, RoutingRequest
from app.domain.repositories.registries import ModelRegistry, ProviderRegistry

QUALITY_WEIGHT: dict[QualityTier, int] = {
    QualityTier.DRAFT: 1,
    QualityTier.STANDARD: 2,
    QualityTier.HIGH: 3,
    QualityTier.CINEMATIC: 4,
}

# The quality, latency and cost parts of a score can differ by at most 24 + 30 + 25 = 79
# points between two candidates. A larger bonus means a model in the preferred execution
# mode always outranks one that is not, while the mode stays a preference: when no
# eligible model runs in that mode, the best-scoring model in another mode is used.
EXECUTION_MODE_BONUS = 100.0


class NoModelRouteError(RuntimeError):
    pass


class ModelRouter:
    def __init__(self, model_registry: ModelRegistry, provider_registry: ProviderRegistry) -> None:
        self._model_registry = model_registry
        self._provider_registry = provider_registry

    def route(self, request: RoutingRequest) -> ModelRoute:
        candidates: list[tuple[ModelDefinition, ModelCapability]] = []

        for model in self._model_registry.find_by_capability(request.capability):
            provider = self._provider_registry.get_provider(model.provider_slug)
            if not model.enabled or provider is None or not provider.enabled:
                continue
            if provider.health == ProviderHealth.UNAVAILABLE:
                continue

            capability = next(
                item for item in model.capabilities if item.capability == request.capability
            )
            if request.require_character_reference and not capability.supports_character_reference:
                continue
            if (
                request.max_cost_units is not None
                and capability.estimated_cost_units > request.max_cost_units
            ):
                continue
            candidates.append((model, capability))

        if not candidates:
            raise NoModelRouteError(f"No registered model can satisfy {request.capability}")

        scored = [
            (self._score(request, model, capability), model, capability)
            for model, capability in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        score, model, capability = scored[0]

        reason = (
            f"Selected {model.display_name} for {request.capability.value}: "
            f"{capability.quality_tier.value} quality, "
            f"{capability.estimated_latency_seconds}s estimated latency, "
            f"{capability.estimated_cost_units:.2f} cost units."
        )
        mode_note = self._execution_mode_note(request.preferred_execution_mode, model)
        if mode_note:
            reason = f"{reason} {mode_note}"
        return ModelRoute(capability=request.capability, model=model, score=score, reason=reason)

    @staticmethod
    def _execution_mode_note(preferred: ExecutionMode | None, model: ModelDefinition) -> str:
        if preferred is None:
            return ""
        if model.execution_mode == preferred:
            return f"Runs in the preferred {preferred.value} execution mode."
        # EXECUTION_MODE_BONUS guarantees this only happens when no candidate matched.
        return (
            f"No eligible model runs in the preferred {preferred.value} execution mode, "
            f"so this {model.execution_mode.value} model is used instead."
        )

    def _score(
        self,
        request: RoutingRequest,
        model: ModelDefinition,
        capability: ModelCapability,
    ) -> float:
        requested_quality = QUALITY_WEIGHT[request.quality]
        candidate_quality = QUALITY_WEIGHT[capability.quality_tier]
        quality_score = 40 - abs(candidate_quality - requested_quality) * 8

        latency_score = max(0, 30 - capability.estimated_latency_seconds / 10)
        cost_score = max(0, 25 - capability.estimated_cost_units * 2)
        execution_bonus = (
            EXECUTION_MODE_BONUS
            if request.preferred_execution_mode is not None
            and model.execution_mode == request.preferred_execution_mode
            else 0.0
        )
        provider_bonus = 2

        return quality_score + latency_score + cost_score + execution_bonus + provider_bonus
