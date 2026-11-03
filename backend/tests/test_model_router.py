import pytest

from app.application.services.model_router import ModelRouter, NoModelRouteError
from app.domain.models.capability import CapabilityType
from app.domain.models.model_definition import ExecutionMode, QualityTier
from app.domain.models.routing import RoutingRequest
from app.infrastructure.registries.bootstrap import build_application_container


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


def test_router_raises_when_execution_mode_cannot_satisfy_capability() -> None:
    container = build_application_container()
    router = ModelRouter(container.model_registry, container.provider_registry)

    with pytest.raises(NoModelRouteError):
        router.route(
            RoutingRequest(
                capability=CapabilityType.IMAGE_TO_VIDEO,
                quality=QualityTier.HIGH,
                preferred_execution_mode=ExecutionMode.LOCAL,
            )
        )
