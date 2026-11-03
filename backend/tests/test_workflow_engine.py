from app.application.services.workflow_engine import WorkflowEngine
from app.domain.models.workflow import WorkflowRequest, WorkflowStatus
from app.infrastructure.registries.bootstrap import build_application_container


def test_workflow_engine_plans_text_to_video_workflow() -> None:
    container = build_application_container()
    engine = WorkflowEngine(container.model_router, container.workflow_registry)

    plan = engine.plan(
        WorkflowRequest(
            prompt="Create a magical children's story about a rabbit learning addition.",
            quality="high",
        )
    )

    assert plan.status == WorkflowStatus.PLANNED
    assert len(plan.stages) == 10
    assert plan.total_estimated_latency_seconds > 0
    assert all(stage.route is not None for stage in plan.stages)
