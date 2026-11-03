import logging
from typing import Any

import httpx

from app.application.ports.provider import UnsupportedCapabilityError
from app.domain.models.capability import CapabilityType

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS: dict[CapabilityType, str] = {
    CapabilityType.STORY_GENERATION: (
        "You are the story director for an animation studio. Write a short, warm, "
        "age-appropriate story from the user's brief. Return a title, a logline, and "
        "a narration script split into numbered beats. Keep the total narration within "
        "the requested duration."
    ),
    CapabilityType.SCENE_PLANNING: (
        "You are a scene planner for an animation pipeline. Break the provided story "
        "into scenes. For each scene return: scene number, setting, characters on "
        "screen, action summary, camera direction, and the narration lines it covers. "
        "Return the plan as a numbered list."
    ),
    CapabilityType.PROMPT_ENHANCEMENT: (
        "You are a prompt engineer for image and video generation models. For each "
        "scene provided, write one detailed visual generation prompt: subject, style, "
        "composition, lighting, color palette, and camera movement. Keep character "
        "descriptions identical across scenes for visual consistency."
    ),
}


class OllamaExecutionError(RuntimeError):
    pass


class OllamaProvider:
    """Adapter that executes director-LLM capabilities against a local Ollama server."""

    def __init__(
        self,
        base_url: str,
        model: str,
        request_timeout_seconds: float = 180.0,
        health_timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._request_timeout = request_timeout_seconds
        self._health_timeout = health_timeout_seconds

    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        system_prompt = SYSTEM_PROMPTS.get(capability)
        if system_prompt is None:
            raise UnsupportedCapabilityError(
                f"Ollama provider does not implement capability '{capability.value}'"
            )

        prompt = self._build_prompt(payload)
        request_body = {
            "model": self._model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            # Keep the model in memory between the sequential director stages so
            # only the first stage pays the load cost.
            "keep_alive": "15m",
        }

        try:
            async with httpx.AsyncClient(timeout=self._request_timeout) as client:
                response = await client.post(f"{self._base_url}/api/generate", json=request_body)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as error:
            detail = str(error) or error.__class__.__name__
            raise OllamaExecutionError(
                f"Ollama request for '{capability.value}' failed: {detail}"
            ) from error

        output_text = str(data.get("response", "")).strip()
        if not output_text:
            raise OllamaExecutionError(
                f"Ollama returned an empty response for '{capability.value}'"
            )

        return {
            "model_slug": model_slug,
            "capability": capability.value,
            "status": "completed",
            "output": output_text,
            "ollama_model": self._model,
            "eval_count": data.get("eval_count"),
            "total_duration_ms": (
                data["total_duration"] // 1_000_000 if data.get("total_duration") else None
            ),
        }

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._health_timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            logger.warning("Ollama health check failed at %s", self._base_url)
            return False

    @staticmethod
    def _build_prompt(payload: dict[str, Any]) -> str:
        sections: list[str] = []
        prompt = str(payload.get("prompt", "")).strip()
        if prompt:
            sections.append(f"Brief:\n{prompt}")

        duration = payload.get("target_duration_seconds")
        if duration:
            sections.append(f"Target duration: {duration} seconds.")

        audience = payload.get("target_audience")
        if audience:
            sections.append(f"Target audience: {audience}.")

        language = payload.get("language")
        if language:
            sections.append(f"Language: {language}.")

        context = payload.get("context")
        if isinstance(context, dict):
            for stage_key, stage_output in context.items():
                sections.append(f"Output from '{stage_key}' stage:\n{stage_output}")

        if not sections:
            raise UnsupportedCapabilityError("Payload contains no prompt or context to send")

        return "\n\n".join(sections)
