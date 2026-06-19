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

    # OpenRouter — the LLM path (called directly; InsForge is not in this path).
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LLM request tuning. Low temperature for deterministic-leaning diagnoses.
    llm_timeout_seconds: float = 60.0
    llm_temperature: float = 0.1


settings = Settings()
