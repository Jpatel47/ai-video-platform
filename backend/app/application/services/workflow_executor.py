import logging
from collections.abc import Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ForwardedOutput:
    """The parts of a stage result that downstream stages receive."""

    text: str | None
    artifact_uris: tuple[str, ...]

    @classmethod
    def from_result(cls, result: Mapping[str, Any]) -> "ForwardedOutput":
        """Keep the text output and artifact URIs; drop provider bookkeeping fields."""
        text = result.get("output")
        uris: list[str] = []
        listed = result.get("artifact_uris")
        if isinstance(listed, list):
            uris.extend(uri for uri in listed if isinstance(uri, str))
        single = result.get("artifact_uri")
        if isinstance(single, str):
            uris.append(single)
        return cls(
            text=text if isinstance(text, str) and text.strip() else None,
            artifact_uris=tuple(uris),
        )


class WorkflowExecutor:
    """Executes a planned workflow by dispatching each stage to its provider adapter.

    Stages run in dependency order. Only meaningful output of completed upstream
    stages is forwarded downstream: text goes into ``payload["context"]`` and artifact
    URIs into ``payload["artifacts"]``, both keyed by upstream stage. The scene planner
    sees the story, the prompt enhancer sees the scenes, and an image stage that
    follows another image stage receives that stage's image URIs instead of the raw
    provider response. No adapter consumes ``payload["artifacts"]`` yet.

    A stage whose provider has no adapter, or whose adapter does not implement the
    stage's capability, runs on the fallback (mock) provider and is reported as
    ``SIMULATED`` rather than ``COMPLETED``, because its output is a placeholder.
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
        outputs: dict[str, ForwardedOutput] = {}
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

            provider = self._providers.get(stage.route.model.provider_slug, self._fallback_provider)
            simulated = provider is self._fallback_provider
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
                    simulated = True
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

            outputs[stage.key] = ForwardedOutput.from_result(output)
            results.append(
                StageResult(
                    stage_key=stage.key,
                    label=stage.label,
                    model_slug=stage.route.model.slug,
                    provider_slug=stage.route.model.provider_slug,
                    status=StageStatus.SIMULATED if simulated else StageStatus.COMPLETED,
                    output=output,
                )
            )

        total = len(results)
        completed = sum(1 for item in results if item.status == StageStatus.COMPLETED)
        simulated_stages = [
            item.stage_key for item in results if item.status == StageStatus.SIMULATED
        ]
        run_status = (
            WorkflowStatus.COMPLETED
            if completed + len(simulated_stages) == total
            else WorkflowStatus.FAILED
        )
        if run_status == WorkflowStatus.FAILED:
            summary = f"Run stopped with failures: {completed}/{total} stages completed."
        elif simulated_stages:
            summary = f"Executed {total}/{total} stages, but only {completed} on real providers."
        else:
            summary = f"Executed {total}/{total} stages successfully."
        if simulated_stages:
            summary += (
                " Simulated by the mock provider, with no media produced: "
                f"{', '.join(simulated_stages)}."
            )

        return WorkflowRunResult(
            plan_id=plan.id,
            status=run_status,
            stage_results=results,
            simulated_stages=simulated_stages,
            director_summary=summary,
        )

    @staticmethod
    def _build_payload(
        plan: WorkflowPlan,
        depends_on: list[str],
        outputs: Mapping[str, ForwardedOutput],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": plan.request.prompt,
            "target_duration_seconds": plan.request.target_duration_seconds,
            "language": plan.request.language,
        }
        if plan.request.target_audience:
            payload["target_audience"] = plan.request.target_audience

        context: dict[str, str] = {}
        artifacts: dict[str, list[str]] = {}
        for key in depends_on:
            upstream = outputs.get(key)
            if upstream is None:
                continue
            if upstream.text is not None:
                context[key] = upstream.text
            if upstream.artifact_uris:
                artifacts[key] = list(upstream.artifact_uris)
        if context:
            payload["context"] = context
        if artifacts:
            payload["artifacts"] = artifacts
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
