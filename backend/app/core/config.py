"""Application settings, loaded from environment / .env.

Secrets come from env only (see CLAUDE.md standing rules). Never hardcode them and
never log their values. The OpenRouter fields are placeholders this phase — no AI or
OpenRouter logic is wired until Phase 3.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service identity
    service_name: str = "ai-kubernetes-agent"

    # CORS: the frontend origin allowed to call this API.
    frontend_origin: str = "http://localhost:3000"

    # OpenRouter (placeholders — unused until Phase 3).
    openrouter_api_key: str = ""
    openrouter_model: str = ""


settings = Settings()
