from app.application.services.model_router import ModelRouter
from app.domain.models.routing import RoutingRequest
from app.domain.models.workflow import WorkflowPlan, WorkflowRequest, WorkflowStage
from app.domain.repositories.registries import WorkflowRegistry


class WorkflowEngine:
    def __init__(self, model_router: ModelRouter, workflow_registry: WorkflowRegistry) -> None:
        self._model_router = model_router
        self._workflow_registry = workflow_registry

    def plan(self, request: WorkflowRequest) -> WorkflowPlan:
        stages: list[WorkflowStage] = []

        for stage_template in self._workflow_registry.get_template("text_to_animated_video"):
            route = self._model_router.route(
                RoutingRequest(
                    capability=stage_template.required_capability,
                    quality=request.quality,
                    preferred_execution_mode=request.preferred_execution_mode,
                    require_character_reference=stage_template.key
                    in {"image_generation", "image_to_video"},
                )
            )
            capability = next(
                capability
                for capability in route.model.capabilities
                if capability.capability == stage_template.required_capability
            )
            stages.append(
                stage_template.model_copy(
                    update={
                        "route": route,
                        "estimated_latency_seconds": capability.estimated_latency_seconds,
                        "estimated_cost_units": capability.estimated_cost_units,
                    }
                )
            )

        total_latency = sum(stage.estimated_latency_seconds for stage in stages)
        total_cost = sum(stage.estimated_cost_units for stage in stages)
        summary = (
            "Planned a text-to-animation workflow with replaceable stages for planning, "
            "visual generation, motion, audio, and final composition."
        )

        return WorkflowPlan(
            request=request,
            stages=stages,
            total_estimated_latency_seconds=total_latency,
            total_estimated_cost_units=round(total_cost, 2),
            director_summary=summary,
        )
