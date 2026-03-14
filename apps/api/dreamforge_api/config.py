from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["development", "test", "production"] = Field(default="development", alias="DREAMFORGE_APP_ENV")
    use_mock_ai: bool = Field(default=True, alias="DREAMFORGE_USE_MOCK_AI")
    auto_migrate: bool = Field(default=True, alias="DREAMFORGE_AUTO_MIGRATE")
    database_url: str = Field(default="sqlite:///./dreamforge.db", alias="DATABASE_URL")
    digitalocean_api_token: str | None = Field(default=None, alias="DIGITALOCEAN_API_TOKEN")
    gradient_model_access_key: str | None = Field(default=None, alias="GRADIENT_MODEL_ACCESS_KEY")
    story_crew_run_url: str | None = Field(default=None, alias="STORY_CREW_RUN_URL")
    story_crew_model_id: str = Field(default="anthropic-claude-4.6-sonnet", alias="STORY_CREW_MODEL_ID")
    image_model_id: str = Field(default="fal-ai/fast-sdxl", alias="IMAGE_MODEL_ID")
    audio_model_id: str = Field(default="fal-ai/elevenlabs/tts/multilingual-v2", alias="AUDIO_MODEL_ID")
    inference_base_url: str = Field(default="https://inference.do-ai.run", alias="INFERENCE_BASE_URL")
    app_public_base_url: str = Field(default="http://localhost:8000", alias="APP_PUBLIC_BASE_URL")
    spaces_access_key_id: str | None = Field(default=None, alias="SPACES_ACCESS_KEY_ID")
    spaces_secret_access_key: str | None = Field(default=None, alias="SPACES_SECRET_ACCESS_KEY")
    spaces_bucket: str | None = Field(default=None, alias="SPACES_BUCKET")
    spaces_region: str = Field(default="nyc3", alias="SPACES_REGION")
    spaces_cdn_base_url: str | None = Field(default=None, alias="SPACES_CDN_BASE_URL")
    media_poll_interval_seconds: int = Field(default=5, alias="MEDIA_POLL_INTERVAL_SECONDS")
    worker_loop_interval_seconds: int = Field(default=2, alias="WORKER_LOOP_INTERVAL_SECONDS")
    session_retention_hours: int = Field(default=24 * 7, alias="SESSION_RETENTION_HOURS")

    @property
    def spaces_endpoint_url(self) -> str:
        return f"https://{self.spaces_region}.digitaloceanspaces.com"

    @property
    def spaces_public_base_url(self) -> str | None:
        if self.spaces_cdn_base_url:
            return self.spaces_cdn_base_url.rstrip("/")
        if self.spaces_bucket:
            return f"https://{self.spaces_bucket}.{self.spaces_region}.cdn.digitaloceanspaces.com"
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

