from enum import StrEnum

from pydantic import BaseModel, Field


class CapabilityType(StrEnum):
    STORY_GENERATION = "story_generation"
    SCENE_PLANNING = "scene_planning"
    PROMPT_ENHANCEMENT = "prompt_enhancement"
    CHARACTER_GENERATION = "character_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDITING = "image_editing"
    CHARACTER_CONSISTENCY = "character_consistency"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VOICE_GENERATION = "voice_generation"
    MUSIC_GENERATION = "music_generation"
    SOUND_EFFECTS = "sound_effects"
    LIP_SYNC = "lip_sync"
    SUBTITLE_GENERATION = "subtitle_generation"
    UPSCALING = "upscaling"
    FRAME_INTERPOLATION = "frame_interpolation"
    VIDEO_COMPOSITION = "video_composition"
    FINAL_RENDERING = "final_rendering"


class CapabilityDefinition(BaseModel):
    capability: CapabilityType
    label: str
    description: str
    input_contract: dict[str, str] = Field(default_factory=dict)
    output_contract: dict[str, str] = Field(default_factory=dict)
