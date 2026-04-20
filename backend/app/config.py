from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash-lite", alias="GEMINI_MODEL")

    storage_mode: str = Field(default="local", alias="STORAGE_MODE")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")


settings = Settings()
