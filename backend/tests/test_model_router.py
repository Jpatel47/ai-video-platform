import pytest

from app.application.services.model_router import ModelRouter, NoModelRouteError
from app.domain.models.capability import CapabilityType
from app.domain.models.model_definition import (
    ExecutionMode,
    ModelCapability,
    ModelDefinition,
    QualityTier,
)
from app.domain.models.provider import ProviderDefinition, ProviderKind
from app.domain.models.routing import RoutingRequest
from app.infrastructure.registries.bootstrap import build_application_container
from app.infrastructure.registries.in_memory import (
    InMemoryModelRegistry,
    InMemoryProviderRegistry,
)


def _two_mode_router() -> ModelRouter:
    """Two image models: a local one that is worst on every score component and a cloud
    one that is best on every component, for the requested cinematic quality."""
    providers = [
        ProviderDefinition(
            slug="local-gpu",
            display_name="Local GPU",
            kind=ProviderKind.LOCAL_INFERENCE,
            execution_mode=ExecutionMode.LOCAL,
        ),
        ProviderDefinition(
            slug="cloud-api",
            display_name="Cloud API",
            kind=ProviderKind.CLOUD_API,
            execution_mode=ExecutionMode.CLOUD,
        ),
    ]
    models = [
        ModelDefinition(
            slug="slow-local",
            display_name="Slow Local",
            provider_slug="local-gpu",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.IMAGE_GENERATION,
                    quality_tier=QualityTier.DRAFT,
                    estimated_cost_units=20.0,
                    estimated_latency_seconds=600,
                )
            ],
        ),
        ModelDefinition(
            slug="fast-cloud",
            display_name="Fast Cloud",
            provider_slug="cloud-api",
            execution_mode=ExecutionMode.CLOUD,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.IMAGE_GENERATION,
                    quality_tier=QualityTier.CINEMATIC,
                    estimated_cost_units=0.0,
                    estimated_latency_seconds=0,
                )
            ],
        ),
    ]
    return ModelRouter(InMemoryModelRegistry(models), InMemoryProviderRegistry(providers))


def test_router_selects_model_by_capability() -> None:
    container = build_application_container()
    router = ModelRouter(container.model_registry, container.provider_registry)

    route = router.route(
        RoutingRequest(
            capability=CapabilityType.IMAGE_GENERATION,
            quality=QualityTier.HIGH,
        )
    )

    assert route.model.slug == "flux-image"
    assert route.capability == CapabilityType.IMAGE_GENERATION


def test_router_respects_execution_mode() -> None:
    container = build_application_container()
    router = ModelRouter(container.model_registry, container.provider_registry)

    route = router.route(
        RoutingRequest(
            capability=CapabilityType.IMAGE_TO_VIDEO,
            quality=QualityTier.HIGH,
            preferred_execution_mode=ExecutionMode.CLOUD,
        )
    )

    assert route.model.slug == "ltx-video"
    assert "Runs in the preferred cloud execution mode." in route.reason


@pytest.mark.parametrize(
    ("preferred", "expected_slug"),
    [
        (ExecutionMode.LOCAL, "slow-local"),
        (ExecutionMode.CLOUD, "fast-cloud"),
        (None, "fast-cloud"),
    ],
)
def test_router_prefers_model_in_preferred_execution_mode(
    preferred: ExecutionMode | None, expected_slug: str
) -> None:
    route = _two_mode_router().route(
        RoutingRequest(
            capability=CapabilityType.IMAGE_GENERATION,
            quality=QualityTier.CINEMATIC,
            preferred_execution_mode=preferred,
        )
    )

    assert route.model.slug == expected_slug


def test_router_falls_back_to_best_model_when_none_runs_in_preferred_mode() -> None:
    route = _two_mode_router().route(
        RoutingRequest(
            capability=CapabilityType.IMAGE_GENERATION,
            quality=QualityTier.CINEMATIC,
            preferred_execution_mode=ExecutionMode.HYBRID,
        )
    )

    assert route.model.slug == "fast-cloud"
    assert (
        "No eligible model runs in the preferred hybrid execution mode, "
        "so this cloud model is used instead." in route.reason
    )


def test_router_falls_back_when_registry_has_no_model_in_preferred_mode() -> None:
    container = build_application_container()
    router = ModelRouter(container.model_registry, container.provider_registry)

    route = router.route(
        RoutingRequest(
            capability=CapabilityType.IMAGE_TO_VIDEO,
            quality=QualityTier.HIGH,
            preferred_execution_mode=ExecutionMode.LOCAL,
        )
    )

    assert route.model.slug == "ltx-video"
    assert "No eligible model runs in the preferred local execution mode" in route.reason


def test_router_raises_when_no_model_satisfies_hard_constraints() -> None:
    container = build_application_container()
    router = ModelRouter(container.model_registry, container.provider_registry)

    with pytest.raises(NoModelRouteError):
        router.route(
            RoutingRequest(
                capability=CapabilityType.IMAGE_TO_VIDEO,
                quality=QualityTier.HIGH,
                max_cost_units=1.0,
            )
        )
