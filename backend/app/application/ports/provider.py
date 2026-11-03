from typing import Any, Protocol

from app.domain.models.capability import CapabilityType


class UnsupportedCapabilityError(ValueError):
    """Raised when a provider adapter is asked for a capability it does not implement."""


class AIProvider(Protocol):
    async def execute(
        self,
        *,
        model_slug: str,
        capability: CapabilityType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def health(self) -> bool:
        raise NotImplementedError
