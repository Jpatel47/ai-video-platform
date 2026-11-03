from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Video Platform"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    database_url: str = "postgresql+psycopg://ai_video:ai_video@localhost:5432/ai_video"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket_name: str = "ai-video-assets"

    ollama_base_url: str = "http://localhost:11434"
    ollama_director_model: str = "llama3.2"
    ollama_request_timeout_seconds: float = Field(default=600.0, gt=0)
    provider_health_timeout_seconds: float = Field(default=5.0, gt=0)

    comfyui_base_url: str = "http://localhost:8188"
    comfyui_checkpoint: str | None = None
    comfyui_image_width: int = Field(default=768, ge=64)
    comfyui_image_height: int = Field(default=768, ge=64)
    comfyui_sampling_steps: int = Field(default=20, ge=1)
    comfyui_request_timeout_seconds: float = Field(default=600.0, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AI_VIDEO_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
