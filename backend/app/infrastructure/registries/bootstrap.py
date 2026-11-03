from dataclasses import dataclass
from functools import lru_cache

from app.application.ports.provider import AIProvider
from app.application.services.model_router import ModelRouter
from app.application.services.workflow_engine import WorkflowEngine
from app.application.services.workflow_executor import WorkflowExecutor
from app.domain.models.capability import CapabilityDefinition, CapabilityType
from app.domain.models.model_definition import (
    ExecutionMode,
    ModelCapability,
    ModelDefinition,
    QualityTier,
)
from app.domain.models.provider import ProviderDefinition, ProviderKind
from app.domain.models.workflow import WorkflowStage
from app.infrastructure.config.settings import get_settings
from app.infrastructure.providers.comfyui_provider import ComfyUIProvider
from app.infrastructure.providers.mock_provider import MockAIProvider
from app.infrastructure.providers.ollama_provider import OllamaProvider
from app.infrastructure.registries.in_memory import (
    InMemoryCapabilityRegistry,
    InMemoryModelRegistry,
    InMemoryProviderRegistry,
    InMemoryWorkflowRegistry,
)


@dataclass(frozen=True)
class ApplicationContainer:
    capability_registry: InMemoryCapabilityRegistry
    provider_registry: InMemoryProviderRegistry
    model_registry: InMemoryModelRegistry
    workflow_registry: InMemoryWorkflowRegistry
    model_router: ModelRouter
    workflow_engine: WorkflowEngine
    workflow_executor: WorkflowExecutor
    provider_adapters: dict[str, AIProvider]


def build_application_container() -> ApplicationContainer:
    settings = get_settings()
    capability_registry = InMemoryCapabilityRegistry(_capabilities())
    provider_registry = InMemoryProviderRegistry(_providers())
    model_registry = InMemoryModelRegistry(_models())
    workflow_registry = InMemoryWorkflowRegistry(_workflow_templates())
    model_router = ModelRouter(model_registry=model_registry, provider_registry=provider_registry)
    workflow_engine = WorkflowEngine(model_router=model_router, workflow_registry=workflow_registry)

    provider_adapters: dict[str, AIProvider] = {
        "ollama-local": OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_director_model,
            request_timeout_seconds=settings.ollama_request_timeout_seconds,
            health_timeout_seconds=settings.provider_health_timeout_seconds,
        ),
        "comfyui-local": ComfyUIProvider(
            base_url=settings.comfyui_base_url,
            checkpoint=settings.comfyui_checkpoint,
            image_width=settings.comfyui_image_width,
            image_height=settings.comfyui_image_height,
            sampling_steps=settings.comfyui_sampling_steps,
            request_timeout_seconds=settings.comfyui_request_timeout_seconds,
            health_timeout_seconds=settings.provider_health_timeout_seconds,
        ),
    }
    workflow_executor = WorkflowExecutor(
        providers=provider_adapters,
        fallback_provider=MockAIProvider(),
    )

    return ApplicationContainer(
        capability_registry=capability_registry,
        provider_registry=provider_registry,
        model_registry=model_registry,
        workflow_registry=workflow_registry,
        model_router=model_router,
        workflow_engine=workflow_engine,
        workflow_executor=workflow_executor,
        provider_adapters=provider_adapters,
    )


@lru_cache
def get_container() -> ApplicationContainer:
    return build_application_container()


def _capabilities() -> list[CapabilityDefinition]:
    return [
        CapabilityDefinition(
            capability=capability,
            label=capability.value.replace("_", " ").title(),
            description=f"Executes {capability.value.replace('_', ' ')} tasks.",
        )
        for capability in CapabilityType
    ]


def _providers() -> list[ProviderDefinition]:
    return [
        ProviderDefinition(
            slug="ollama-local",
            display_name="Ollama Local",
            kind=ProviderKind.OLLAMA,
            execution_mode=ExecutionMode.LOCAL,
        ),
        ProviderDefinition(
            slug="comfyui-local",
            display_name="ComfyUI Local",
            kind=ProviderKind.COMFYUI,
            execution_mode=ExecutionMode.LOCAL,
        ),
        ProviderDefinition(
            slug="cloud-video",
            display_name="Cloud Video Provider",
            kind=ProviderKind.CLOUD_API,
            execution_mode=ExecutionMode.CLOUD,
        ),
        ProviderDefinition(
            slug="renderer",
            display_name="Internal Renderer",
            kind=ProviderKind.INTERNAL_RENDERER,
            execution_mode=ExecutionMode.HYBRID,
        ),
    ]


def _models() -> list[ModelDefinition]:
    return [
        ModelDefinition(
            slug="ollama-director",
            display_name="Local Director LLM",
            provider_slug="ollama-local",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.STORY_GENERATION,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=0.2,
                    estimated_latency_seconds=12,
                ),
                ModelCapability(
                    capability=CapabilityType.SCENE_PLANNING,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=0.2,
                    estimated_latency_seconds=10,
                ),
                ModelCapability(
                    capability=CapabilityType.PROMPT_ENHANCEMENT,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=0.15,
                    estimated_latency_seconds=8,
                ),
            ],
        ),
        ModelDefinition(
            slug="flux-image",
            display_name="FLUX Image Provider",
            provider_slug="comfyui-local",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.CHARACTER_GENERATION,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=1.5,
                    estimated_latency_seconds=45,
                    supports_character_reference=True,
                ),
                ModelCapability(
                    capability=CapabilityType.IMAGE_GENERATION,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=1.2,
                    estimated_latency_seconds=40,
                    supports_character_reference=True,
                ),
            ],
        ),
        ModelDefinition(
            slug="qwen-image-edit",
            display_name="Qwen Image Edit Provider",
            provider_slug="comfyui-local",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.IMAGE_EDITING,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=1.0,
                    estimated_latency_seconds=35,
                    supports_character_reference=True,
                ),
                ModelCapability(
                    capability=CapabilityType.CHARACTER_CONSISTENCY,
                    quality_tier=QualityTier.STANDARD,
                    estimated_cost_units=0.8,
                    estimated_latency_seconds=30,
                    supports_character_reference=True,
                ),
            ],
        ),
        ModelDefinition(
            slug="ltx-video",
            display_name="LTX Video Provider",
            provider_slug="cloud-video",
            execution_mode=ExecutionMode.CLOUD,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.IMAGE_TO_VIDEO,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=4.5,
                    estimated_latency_seconds=120,
                    max_duration_seconds=10,
                    supports_character_reference=True,
                ),
                ModelCapability(
                    capability=CapabilityType.VIDEO_TO_VIDEO,
                    quality_tier=QualityTier.STANDARD,
                    estimated_cost_units=5.5,
                    estimated_latency_seconds=180,
                ),
            ],
        ),
        ModelDefinition(
            slug="kokoro-voice",
            display_name="Kokoro Voice Provider",
            provider_slug="comfyui-local",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.VOICE_GENERATION,
                    quality_tier=QualityTier.HIGH,
                    estimated_cost_units=0.4,
                    estimated_latency_seconds=20,
                )
            ],
        ),
        ModelDefinition(
            slug="musicgen",
            display_name="MusicGen Provider",
            provider_slug="comfyui-local",
            execution_mode=ExecutionMode.LOCAL,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.MUSIC_GENERATION,
                    quality_tier=QualityTier.STANDARD,
                    estimated_cost_units=0.6,
                    estimated_latency_seconds=45,
                )
            ],
        ),
        ModelDefinition(
            slug="ffmpeg-composer",
            display_name="FFmpeg Composition Engine",
            provider_slug="renderer",
            execution_mode=ExecutionMode.HYBRID,
            capabilities=[
                ModelCapability(
                    capability=CapabilityType.VIDEO_COMPOSITION,
                    quality_tier=QualityTier.CINEMATIC,
                    estimated_cost_units=0.3,
                    estimated_latency_seconds=25,
                ),
                ModelCapability(
                    capability=CapabilityType.FINAL_RENDERING,
                    quality_tier=QualityTier.CINEMATIC,
                    estimated_cost_units=0.8,
                    estimated_latency_seconds=60,
                ),
            ],
        ),
    ]


def _workflow_templates() -> dict[str, list[WorkflowStage]]:
    return {
        "text_to_animated_video": [
            WorkflowStage(
                key="story_generation",
                label="Story Generation",
                required_capability=CapabilityType.STORY_GENERATION,
            ),
            WorkflowStage(
                key="scene_planning",
                label="Scene Planning",
                required_capability=CapabilityType.SCENE_PLANNING,
                depends_on=["story_generation"],
            ),
            WorkflowStage(
                key="prompt_enhancement",
                label="Prompt Enhancement",
                required_capability=CapabilityType.PROMPT_ENHANCEMENT,
                depends_on=["scene_planning"],
            ),
            WorkflowStage(
                key="character_generation",
                label="Character Generation",
                required_capability=CapabilityType.CHARACTER_GENERATION,
                depends_on=["prompt_enhancement"],
            ),
            WorkflowStage(
                key="image_generation",
                label="Image Generation",
                required_capability=CapabilityType.IMAGE_GENERATION,
                depends_on=["character_generation"],
            ),
            WorkflowStage(
                key="image_to_video",
                label="Image To Video",
                required_capability=CapabilityType.IMAGE_TO_VIDEO,
                depends_on=["image_generation"],
            ),
            WorkflowStage(
                key="voice_generation",
                label="Voice Generation",
                required_capability=CapabilityType.VOICE_GENERATION,
                depends_on=["story_generation"],
            ),
            WorkflowStage(
                key="music_generation",
                label="Music Generation",
                required_capability=CapabilityType.MUSIC_GENERATION,
                depends_on=["scene_planning"],
            ),
            WorkflowStage(
                key="video_composition",
                label="Video Composition",
                required_capability=CapabilityType.VIDEO_COMPOSITION,
                depends_on=["image_to_video", "voice_generation", "music_generation"],
            ),
            WorkflowStage(
                key="final_rendering",
                label="Final Rendering",
                required_capability=CapabilityType.FINAL_RENDERING,
                depends_on=["video_composition"],
            ),
        ]
    }
