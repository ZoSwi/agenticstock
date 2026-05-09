from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"

    database_url: str
    redis_url: str
    backend_public_base_url: str = "http://localhost:8000"
    ml_service_url: str = "http://ml:8001"

    llm_provider: str = "auto"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"

    alphavantage_api_key: str | None = None
    news_api_key: str | None = None
    finnhub_api_key: str | None = None


settings = Settings()  # type: ignore[call-arg]
