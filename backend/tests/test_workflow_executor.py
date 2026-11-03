from typing import Any

import pytest

from app.application.services.workflow_executor import WorkflowExecutor
from app.domain.models.capability import CapabilityType
from app.domain.models.workflow import StageStatus, WorkflowRequest, WorkflowStatus
from app.infrastructure.providers.mock_provider import MockAIProvider
from app.infrastructure.registries.bootstrap import build_application_container


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append({"capability": capability, "payload": payload})
        return {"status": "completed", "output": f"{capability.value} output"}

    async def health(self) -> bool:
        return True


class FailingProvider:
    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise RuntimeError("provider exploded")

    async def health(self) -> bool:
        return False


def _plan() -> Any:
    container = build_application_container()
    return container.workflow_engine.plan(
        WorkflowRequest(prompt="A rabbit learns addition.", quality="high")
    )


@pytest.mark.asyncio
async def test_executor_runs_all_stages_in_dependency_order() -> None:
    recorder = RecordingProvider()
    executor = WorkflowExecutor(
        providers={"ollama-local": recorder}, fallback_provider=MockAIProvider()
    )

    result = await executor.execute(_plan())

    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.stage_results) == 10
    assert all(item.status == StageStatus.COMPLETED for item in result.stage_results)

    llm_calls = [call["capability"] for call in recorder.calls]
    assert llm_calls == [
        CapabilityType.STORY_GENERATION,
        CapabilityType.SCENE_PLANNING,
        CapabilityType.PROMPT_ENHANCEMENT,
    ]


@pytest.mark.asyncio
async def test_executor_forwards_upstream_output_as_context() -> None:
    recorder = RecordingProvider()
    executor = WorkflowExecutor(
        providers={"ollama-local": recorder}, fallback_provider=MockAIProvider()
    )

    await executor.execute(_plan())

    scene_call = recorder.calls[1]
    assert scene_call["capability"] == CapabilityType.SCENE_PLANNING
    assert scene_call["payload"]["context"] == {"story_generation": "story_generation output"}


@pytest.mark.asyncio
async def test_executor_skips_downstream_stages_when_dependency_fails() -> None:
    executor = WorkflowExecutor(
        providers={"ollama-local": FailingProvider()}, fallback_provider=MockAIProvider()
    )

    result = await executor.execute(_plan())

    assert result.status == WorkflowStatus.FAILED
    by_key = {item.stage_key: item for item in result.stage_results}
    assert by_key["story_generation"].status == StageStatus.FAILED
    assert by_key["scene_planning"].status == StageStatus.SKIPPED
    assert by_key["image_to_video"].status == StageStatus.SKIPPED
