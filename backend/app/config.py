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

    smtp_enabled: bool = Field(default=False, alias="SMTP_ENABLED")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")

    webhook_signing_secret: str = Field(default="", alias="WEBHOOK_SIGNING_SECRET")

    auth_jwt_secret: str = Field(default="change-me", alias="AUTH_JWT_SECRET")
    auth_jwt_exp_hours: int = Field(default=72, alias="AUTH_JWT_EXP_HOURS")
    auth_cookie_name: str = Field(default="miniats_session", alias="AUTH_COOKIE_NAME")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://localhost:8000/api/auth/google/callback", alias="GOOGLE_REDIRECT_URI")
    google_allowed_domain: str = Field(default="", alias="GOOGLE_ALLOWED_DOMAIN")
    auth_allow_dev_headers: bool = Field(default=False, alias="AUTH_ALLOW_DEV_HEADERS")
    auth_bootstrap_admin_email: str = Field(default="", alias="AUTH_BOOTSTRAP_ADMIN_EMAIL")

    matching_enable_embeddings: bool = Field(default=False, alias="MATCHING_ENABLE_EMBEDDINGS")
    matching_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="MATCHING_EMBEDDING_MODEL")


settings = Settings()
