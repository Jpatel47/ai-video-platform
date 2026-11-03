import json
from typing import Any

import httpx
import pytest

from app.application.ports.provider import UnsupportedCapabilityError
from app.application.services.workflow_executor import WorkflowExecutor
from app.domain.models.capability import CapabilityType
from app.domain.models.workflow import StageStatus, WorkflowRequest, WorkflowStatus
from app.infrastructure.providers.comfyui_provider import IMAGE_CAPABILITIES, ComfyUIProvider
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


class FakeImageProvider:
    """Returns ComfyUI-shaped results for image capabilities and records each payload."""

    def __init__(self) -> None:
        self.payloads: dict[CapabilityType, dict[str, Any]] = {}

    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if capability not in IMAGE_CAPABILITIES:
            raise UnsupportedCapabilityError(capability.value)
        self.payloads[capability] = payload
        return {
            "model_slug": model_slug,
            "capability": capability.value,
            "status": "completed",
            "prompt_id": f"job-{capability.value}",
            "checkpoint": "test.safetensors",
            "images": [{"filename": f"{capability.value}.png", "type": "output"}],
            "artifact_uris": [f"http://comfy.test/view?filename={capability.value}.png"],
        }

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
    assert all(
        item.status in {StageStatus.COMPLETED, StageStatus.SIMULATED}
        for item in result.stage_results
    )

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
async def test_executor_forwards_only_text_and_artifact_uris_downstream() -> None:
    images = FakeImageProvider()
    executor = WorkflowExecutor(
        providers={"ollama-local": RecordingProvider(), "comfyui-local": images},
        fallback_provider=MockAIProvider(),
    )

    await executor.execute(_plan())

    character_payload = images.payloads[CapabilityType.CHARACTER_GENERATION]
    assert character_payload["context"] == {"prompt_enhancement": "prompt_enhancement output"}
    assert "artifacts" not in character_payload

    # The character stage produced images, not text: its image URIs are forwarded,
    # its raw provider response (model_slug, prompt_id, checkpoint, ...) is not.
    image_payload = images.payloads[CapabilityType.IMAGE_GENERATION]
    assert "context" not in image_payload
    assert image_payload["artifacts"] == {
        "character_generation": ["http://comfy.test/view?filename=character_generation.png"]
    }


@pytest.mark.asyncio
async def test_comfyui_receives_text_prompts_for_each_image_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_prompts: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            graph = json.loads(request.content)["prompt"]
            capability = graph["7"]["inputs"]["filename_prefix"].rsplit("/", 1)[-1]
            submitted_prompts[capability] = graph["2"]["inputs"]["text"]
            return httpx.Response(200, json={"prompt_id": capability})
        if request.url.path.startswith("/history/"):
            prompt_id = request.url.path.removeprefix("/history/")
            history = {
                "status": {"status_str": "success", "completed": True},
                "outputs": {"7": {"images": [{"filename": f"{prompt_id}.png"}]}},
            }
            return httpx.Response(200, json={prompt_id: history})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def patched_client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    plan = _plan()
    comfyui = ComfyUIProvider(
        base_url="http://comfy.test",
        checkpoint="test.safetensors",
        poll_interval_seconds=0.01,
    )
    executor = WorkflowExecutor(
        providers={"ollama-local": RecordingProvider(), "comfyui-local": comfyui},
        fallback_provider=MockAIProvider(),
    )

    await executor.execute(plan)

    # image_generation depends only on character_generation, which yields images and
    # no text, so its prompt falls back to the brief instead of a stringified dict.
    assert submitted_prompts == {
        "character_generation": "prompt_enhancement output",
        "image_generation": plan.request.prompt,
    }


@pytest.mark.asyncio
async def test_executor_marks_stages_run_by_the_mock_provider_as_simulated() -> None:
    executor = WorkflowExecutor(
        providers={"ollama-local": RecordingProvider(), "comfyui-local": FakeImageProvider()},
        fallback_provider=MockAIProvider(),
    )

    result = await executor.execute(_plan())

    # cloud-video and renderer have no adapter; the ComfyUI adapter does not implement
    # voice or music. Those stages ran on the mock and must not be reported as completed.
    statuses = {item.stage_key: item.status for item in result.stage_results}
    assert statuses == {
        "story_generation": "completed",
        "scene_planning": "completed",
        "prompt_enhancement": "completed",
        "character_generation": "completed",
        "image_generation": "completed",
        "image_to_video": "simulated",
        "voice_generation": "simulated",
        "music_generation": "simulated",
        "video_composition": "simulated",
        "final_rendering": "simulated",
    }
    assert result.status == WorkflowStatus.COMPLETED
    assert result.simulated_stages == [
        "image_to_video",
        "voice_generation",
        "music_generation",
        "video_composition",
        "final_rendering",
    ]
    assert result.director_summary == (
        "Executed 10/10 stages, but only 5 on real providers. Simulated by the mock "
        "provider, with no media produced: image_to_video, voice_generation, "
        "music_generation, video_composition, final_rendering."
    )


@pytest.mark.asyncio
async def test_executor_reports_no_simulated_stages_when_all_adapters_exist() -> None:
    recorder = RecordingProvider()
    executor = WorkflowExecutor(
        providers={
            slug: recorder for slug in ("ollama-local", "comfyui-local", "cloud-video", "renderer")
        },
        fallback_provider=MockAIProvider(),
    )

    result = await executor.execute(_plan())

    assert all(item.status == StageStatus.COMPLETED for item in result.stage_results)
    assert result.simulated_stages == []
    assert result.director_summary == "Executed 10/10 stages successfully."


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
