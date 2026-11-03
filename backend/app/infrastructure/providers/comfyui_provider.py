import asyncio
import logging
import uuid
from typing import Any

import httpx

from app.application.ports.provider import UnsupportedCapabilityError
from app.domain.models.capability import CapabilityType

logger = logging.getLogger(__name__)

IMAGE_CAPABILITIES = {
    CapabilityType.IMAGE_GENERATION,
    CapabilityType.CHARACTER_GENERATION,
}

DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, watermark, text, signature"


class ComfyUIExecutionError(RuntimeError):
    pass


class ComfyUIProvider:
    """Adapter that executes image capabilities against a local ComfyUI server.

    Submits a checkpoint-based text-to-image graph to POST /prompt, polls
    GET /history/{prompt_id} until the job finishes, and returns the output
    image reference. The checkpoint is auto-discovered from the server when
    not configured explicitly.
    """

    def __init__(
        self,
        base_url: str,
        checkpoint: str | None = None,
        image_width: int = 768,
        image_height: int = 768,
        sampling_steps: int = 20,
        request_timeout_seconds: float = 600.0,
        poll_interval_seconds: float = 2.0,
        health_timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._checkpoint = checkpoint
        self._image_width = image_width
        self._image_height = image_height
        self._sampling_steps = sampling_steps
        self._request_timeout = request_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._health_timeout = health_timeout_seconds

    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if capability not in IMAGE_CAPABILITIES:
            raise UnsupportedCapabilityError(
                f"ComfyUI provider does not implement capability '{capability.value}'"
            )

        positive_prompt = self._build_positive_prompt(payload)
        client_id = uuid.uuid4().hex

        try:
            async with httpx.AsyncClient(timeout=self._request_timeout) as client:
                checkpoint = self._checkpoint or await self._discover_checkpoint(client)
                graph = self._text_to_image_graph(
                    checkpoint=checkpoint,
                    positive_prompt=positive_prompt,
                    negative_prompt=str(payload.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)),
                    seed=int.from_bytes(uuid.uuid4().bytes[:4], "big"),
                    filename_prefix=f"ai-video/{capability.value}",
                )
                response = await client.post(
                    f"{self._base_url}/prompt",
                    json={"prompt": graph, "client_id": client_id},
                )
                response.raise_for_status()
                prompt_id = response.json().get("prompt_id")
                if not prompt_id:
                    raise ComfyUIExecutionError("ComfyUI did not return a prompt_id")

                images = await self._wait_for_images(client, prompt_id)
        except httpx.HTTPError as error:
            detail = str(error) or error.__class__.__name__
            raise ComfyUIExecutionError(
                f"ComfyUI request for '{capability.value}' failed: {detail}"
            ) from error

        return {
            "model_slug": model_slug,
            "capability": capability.value,
            "status": "completed",
            "prompt_id": prompt_id,
            "checkpoint": checkpoint,
            "images": images,
            "artifact_uris": [
                f"{self._base_url}/view?filename={image['filename']}"
                f"&subfolder={image.get('subfolder', '')}&type={image.get('type', 'output')}"
                for image in images
            ],
        }

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._health_timeout) as client:
                response = await client.get(f"{self._base_url}/system_stats")
                return response.status_code == 200
        except httpx.HTTPError:
            logger.warning("ComfyUI health check failed at %s", self._base_url)
            return False

    async def _discover_checkpoint(self, client: httpx.AsyncClient) -> str:
        response = await client.get(f"{self._base_url}/object_info/CheckpointLoaderSimple")
        response.raise_for_status()
        data = response.json()
        try:
            checkpoints = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except (KeyError, IndexError, TypeError):
            checkpoints = []
        if not checkpoints:
            raise ComfyUIExecutionError(
                "No checkpoints installed in ComfyUI. Download a model into "
                "ComfyUI/models/checkpoints (for example DreamShaper or SDXL-Turbo) "
                "or set AI_VIDEO_COMFYUI_CHECKPOINT."
            )
        return str(checkpoints[0])

    async def _wait_for_images(
        self, client: httpx.AsyncClient, prompt_id: str
    ) -> list[dict[str, Any]]:
        elapsed = 0.0
        while elapsed < self._request_timeout:
            response = await client.get(f"{self._base_url}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json().get(prompt_id)
            if history:
                status = history.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyUIExecutionError(
                        f"ComfyUI job {prompt_id} failed: {self._extract_error(history)}"
                    )
                images: list[dict[str, Any]] = []
                for node_output in history.get("outputs", {}).values():
                    images.extend(node_output.get("images", []))
                if images:
                    return images
                if status.get("completed"):
                    raise ComfyUIExecutionError(
                        f"ComfyUI job {prompt_id} completed without image outputs"
                    )
            await asyncio.sleep(self._poll_interval)
            elapsed += self._poll_interval
        raise ComfyUIExecutionError(
            f"Timed out after {self._request_timeout}s waiting for ComfyUI job {prompt_id}"
        )

    @staticmethod
    def _extract_error(history: dict[str, Any]) -> str:
        for message in history.get("status", {}).get("messages", []):
            if isinstance(message, list) and message and message[0] == "execution_error":
                detail = message[1] if len(message) > 1 else {}
                return str(detail.get("exception_message", detail))
        return "unknown error"

    @staticmethod
    def _build_positive_prompt(payload: dict[str, Any]) -> str:
        """Return the enhanced prompt text when one was forwarded, otherwise the brief.

        Only text is used. Other context values (such as another image stage's result)
        are ignored instead of being stringified into the prompt.
        """
        context = payload.get("context")
        if isinstance(context, dict):
            enhanced = context.get("prompt_enhancement")
            if isinstance(enhanced, str) and enhanced.strip():
                return enhanced.strip()

        prompt = payload.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            return prompt.strip()
        raise UnsupportedCapabilityError("Payload contains no prompt to render")

    def _text_to_image_graph(
        self,
        checkpoint: str,
        positive_prompt: str,
        negative_prompt: str,
        seed: int,
        filename_prefix: str,
    ) -> dict[str, Any]:
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive_prompt, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": self._image_width,
                    "height": self._image_height,
                    "batch_size": 1,
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed,
                    "steps": self._sampling_steps,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": filename_prefix},
            },
        }
