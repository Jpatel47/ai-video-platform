import logging
from collections.abc import Mapping
from typing import Any

from app.application.ports.provider import AIProvider, UnsupportedCapabilityError
from app.domain.models.workflow import (
    StageResult,
    StageStatus,
    WorkflowPlan,
    WorkflowRunResult,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowExecutionError(RuntimeError):
    pass


class WorkflowExecutor:
    """Executes a planned workflow by dispatching each stage to its provider adapter.

    Stages run in dependency order. The textual output of completed upstream stages
    is forwarded to downstream stages as context, so the scene planner sees the story
    and the prompt enhancer sees the scenes.
    """

    def __init__(
        self,
        providers: Mapping[str, AIProvider],
        fallback_provider: AIProvider,
    ) -> None:
        self._providers = providers
        self._fallback_provider = fallback_provider

    async def execute(self, plan: WorkflowPlan) -> WorkflowRunResult:
        ordered_stages = self._resolve_order(plan)
        outputs: dict[str, Any] = {}
        failed_stages: set[str] = set()
        results: list[StageResult] = []

        for stage in ordered_stages:
            if stage.route is None:
                raise WorkflowExecutionError(f"Stage '{stage.key}' has no model route")

            if any(dependency in failed_stages for dependency in stage.depends_on):
                results.append(
                    StageResult(
                        stage_key=stage.key,
                        label=stage.label,
                        model_slug=stage.route.model.slug,
                        provider_slug=stage.route.model.provider_slug,
                        status=StageStatus.SKIPPED,
                        error="Skipped because an upstream stage failed",
                    )
                )
                failed_stages.add(stage.key)
                continue

            provider = self._providers.get(
                stage.route.model.provider_slug, self._fallback_provider
            )
            payload = self._build_payload(plan, stage.depends_on, outputs)

            try:
                try:
                    output = await provider.execute(
                        model_slug=stage.route.model.slug,
                        capability=stage.required_capability,
                        payload=payload,
                    )
                except UnsupportedCapabilityError:
                    logger.info(
                        "Provider for stage '%s' does not implement '%s'; using mock",
                        stage.key,
                        stage.required_capability.value,
                    )
                    output = await self._fallback_provider.execute(
                        model_slug=stage.route.model.slug,
                        capability=stage.required_capability,
                        payload=payload,
                    )
            except Exception as error:
                logger.exception("Stage '%s' failed", stage.key)
                failed_stages.add(stage.key)
                results.append(
                    StageResult(
                        stage_key=stage.key,
                        label=stage.label,
                        model_slug=stage.route.model.slug,
                        provider_slug=stage.route.model.provider_slug,
                        status=StageStatus.FAILED,
                        error=str(error),
                    )
                )
                continue

            outputs[stage.key] = output.get("output", output)
            results.append(
                StageResult(
                    stage_key=stage.key,
                    label=stage.label,
                    model_slug=stage.route.model.slug,
                    provider_slug=stage.route.model.provider_slug,
                    status=StageStatus.COMPLETED,
                    output=output,
                )
            )

        completed = sum(1 for item in results if item.status == StageStatus.COMPLETED)
        run_status = (
            WorkflowStatus.COMPLETED if completed == len(results) else WorkflowStatus.FAILED
        )
        summary = (
            f"Executed {completed}/{len(results)} stages successfully."
            if run_status == WorkflowStatus.COMPLETED
            else f"Run stopped with failures: {completed}/{len(results)} stages completed."
        )

        return WorkflowRunResult(
            plan_id=plan.id,
            status=run_status,
            stage_results=results,
            director_summary=summary,
        )

    @staticmethod
    def _build_payload(
        plan: WorkflowPlan,
        depends_on: list[str],
        outputs: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": plan.request.prompt,
            "target_duration_seconds": plan.request.target_duration_seconds,
            "language": plan.request.language,
        }
        if plan.request.target_audience:
            payload["target_audience"] = plan.request.target_audience

        context = {key: outputs[key] for key in depends_on if key in outputs}
        if context:
            payload["context"] = context
        return payload

    @staticmethod
    def _resolve_order(plan: WorkflowPlan) -> list[Any]:
        known_keys = {stage.key for stage in plan.stages}
        for stage in plan.stages:
            missing = [key for key in stage.depends_on if key not in known_keys]
            if missing:
                raise WorkflowExecutionError(
                    f"Stage '{stage.key}' depends on unknown stages: {missing}"
                )

        ordered: list[Any] = []
        placed: set[str] = set()
        remaining = list(plan.stages)
        while remaining:
            progressed = False
            for stage in list(remaining):
                if all(dependency in placed for dependency in stage.depends_on):
                    ordered.append(stage)
                    placed.add(stage.key)
                    remaining.remove(stage)
                    progressed = True
            if not progressed:
                cycle = [stage.key for stage in remaining]
                raise WorkflowExecutionError(f"Dependency cycle detected among stages: {cycle}")
        return ordered
