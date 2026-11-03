import json
from typing import Any

import httpx
import pytest

from app.application.ports.provider import UnsupportedCapabilityError
from app.domain.models.capability import CapabilityType
from app.infrastructure.providers.comfyui_provider import (
    ComfyUIExecutionError,
    ComfyUIProvider,
)


def _mock_transport(handler: Any) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_rejects_unsupported_capability() -> None:
    provider = ComfyUIProvider(base_url="http://comfy.test")
    with pytest.raises(UnsupportedCapabilityError):
        await provider.execute(
            model_slug="kokoro-voice",
            capability=CapabilityType.VOICE_GENERATION,
            payload={"prompt": "hello"},
        )


@pytest.mark.asyncio
async def test_executes_image_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    submitted: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/object_info/CheckpointLoaderSimple":
            return httpx.Response(
                200,
                json={
                    "CheckpointLoaderSimple": {
                        "input": {"required": {"ckpt_name": [["dreamshaper_8.safetensors"]]}}
                    }
                },
            )
        if request.url.path == "/prompt":
            submitted.update(json.loads(request.content))
            return httpx.Response(200, json={"prompt_id": "job-1"})
        if request.url.path == "/history/job-1":
            return httpx.Response(
                200,
                json={
                    "job-1": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {
                            "7": {
                                "images": [
                                    {
                                        "filename": "ai-video_00001_.png",
                                        "subfolder": "ai-video",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                },
            )
        return httpx.Response(404)

    transport = _mock_transport(handler)
    original_client = httpx.AsyncClient

    def patched_client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    provider = ComfyUIProvider(base_url="http://comfy.test", poll_interval_seconds=0.01)
    result = await provider.execute(
        model_slug="flux-image",
        capability=CapabilityType.IMAGE_GENERATION,
        payload={"prompt": "a rabbit teaching addition"},
    )

    assert result["status"] == "completed"
    assert result["checkpoint"] == "dreamshaper_8.safetensors"
    assert result["images"][0]["filename"] == "ai-video_00001_.png"
    assert "view?filename=ai-video_00001_.png" in result["artifact_uris"][0]

    graph = submitted["prompt"]
    assert graph["2"]["inputs"]["text"] == "a rabbit teaching addition"
    assert graph["1"]["inputs"]["ckpt_name"] == "dreamshaper_8.safetensors"


@pytest.mark.asyncio
async def test_uses_enhanced_prompt_from_context(monkeypatch: pytest.MonkeyPatch) -> None:
    submitted: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            submitted.update(json.loads(request.content))
            return httpx.Response(200, json={"prompt_id": "job-2"})
        if request.url.path == "/history/job-2":
            return httpx.Response(
                200,
                json={
                    "job-2": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {"7": {"images": [{"filename": "x.png"}]}},
                    }
                },
            )
        return httpx.Response(404)

    transport = _mock_transport(handler)
    original_client = httpx.AsyncClient

    def patched_client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    provider = ComfyUIProvider(
        base_url="http://comfy.test",
        checkpoint="sdxl.safetensors",
        poll_interval_seconds=0.01,
    )
    await provider.execute(
        model_slug="flux-image",
        capability=CapabilityType.IMAGE_GENERATION,
        payload={
            "prompt": "original brief",
            "context": {"prompt_enhancement": "cinematic rabbit, warm lighting"},
        },
    )

    assert submitted["prompt"]["2"]["inputs"]["text"] == "cinematic rabbit, warm lighting"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context",
    [
        {"character_generation": {"model_slug": "flux-image", "images": [{"filename": "a.png"}]}},
        {"prompt_enhancement": {"text": "not a plain string"}},
        {"prompt_enhancement": "   "},
    ],
    ids=["upstream-image-result", "non-text-enhancement", "blank-enhancement"],
)
async def test_falls_back_to_brief_when_context_has_no_usable_text(
    monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]
) -> None:
    submitted: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            submitted.update(json.loads(request.content))
            return httpx.Response(200, json={"prompt_id": "job-3"})
        if request.url.path == "/history/job-3":
            return httpx.Response(
                200,
                json={
                    "job-3": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {"7": {"images": [{"filename": "x.png"}]}},
                    }
                },
            )
        return httpx.Response(404)

    transport = _mock_transport(handler)
    original_client = httpx.AsyncClient

    def patched_client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    provider = ComfyUIProvider(
        base_url="http://comfy.test",
        checkpoint="sdxl.safetensors",
        poll_interval_seconds=0.01,
    )
    await provider.execute(
        model_slug="flux-image",
        capability=CapabilityType.IMAGE_GENERATION,
        payload={"prompt": "a rabbit teaching addition", "context": context},
    )

    assert submitted["prompt"]["2"]["inputs"]["text"] == "a rabbit teaching addition"


@pytest.mark.asyncio
async def test_raises_when_no_checkpoints_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/object_info/CheckpointLoaderSimple":
            return httpx.Response(
                200,
                json={"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [[]]}}}},
            )
        return httpx.Response(404)

    transport = _mock_transport(handler)
    original_client = httpx.AsyncClient

    def patched_client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    provider = ComfyUIProvider(base_url="http://comfy.test")
    with pytest.raises(ComfyUIExecutionError, match="No checkpoints installed"):
        await provider.execute(
            model_slug="flux-image",
            capability=CapabilityType.IMAGE_GENERATION,
            payload={"prompt": "a rabbit"},
        )
