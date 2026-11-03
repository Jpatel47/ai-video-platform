from typing import Any

from app.domain.models.capability import CapabilityType


class MockAIProvider:
    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "model_slug": model_slug,
            "capability": capability.value,
            "payload": payload,
            "status": "completed",
            "artifact_uri": f"mock://artifacts/{model_slug}/{capability.value}",
        }

    async def health(self) -> bool:
        return True
