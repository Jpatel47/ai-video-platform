from typing import Annotated

from fastapi import APIRouter, Depends

from app.domain.models.capability import CapabilityType
from app.domain.models.provider import ProviderDefinition
from app.domain.models.workflow import (
    WorkflowPlan,
    WorkflowRequest,
    WorkflowRunResult,
)
from app.infrastructure.registries.bootstrap import ApplicationContainer, get_container

api_router = APIRouter()

Container = Annotated[ApplicationContainer, Depends(get_container)]


@api_router.get("/registry/capabilities", tags=["registry"])
async def list_capabilities(container: Container) -> list[CapabilityType]:
    return container.capability_registry.list_capabilities()


@api_router.get("/registry/models", tags=["registry"])
async def list_models(container: Container) -> list[dict[str, object]]:
    return [model.model_dump(mode="json") for model in container.model_registry.list_models()]


@api_router.get("/registry/providers", tags=["registry"])
async def list_providers(container: Container) -> list[ProviderDefinition]:
    return container.provider_registry.list_providers()


@api_router.get("/providers/health", tags=["providers"])
async def provider_health(container: Container) -> dict[str, bool]:
    health: dict[str, bool] = {}
    for slug, adapter in container.provider_adapters.items():
        health[slug] = await adapter.health()
    return health


@api_router.post("/workflows/plan", response_model=WorkflowPlan, tags=["workflows"])
async def plan_workflow(request: WorkflowRequest, container: Container) -> WorkflowPlan:
    return container.workflow_engine.plan(request)


@api_router.post("/workflows/execute", response_model=WorkflowRunResult, tags=["workflows"])
async def execute_workflow(request: WorkflowRequest, container: Container) -> WorkflowRunResult:
    plan = container.workflow_engine.plan(request)
    return await container.workflow_executor.execute(plan)
