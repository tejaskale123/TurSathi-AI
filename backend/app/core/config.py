import os
from typing import Optional
from urllib.parse import quote_plus
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TurSathi AI Backend"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security & JWT Configuration
    SECRET_KEY: str = "default_unsafe_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Test & Diagnostic Endpoints (Disabled in production by default)
    ENABLE_TEST_ENDPOINTS: bool = False

    # CPU / RAM Tuning for PyTorch on 4-Core VPS
    TORCH_NUM_THREADS: int = 2

    # CORS Configuration
    FRONTEND_CORS_ORIGINS: str = "http://localhost:8081,http://127.0.0.1:8081,http://localhost:8000,http://127.0.0.1:8000"

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # PostgreSQL Database Configuration
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "tursathi_db"

    # Optional direct DATABASE_URL override
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Anthropic Claude Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"

    # Sarvam AI Indic Speech-to-Text Configuration
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_API_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_STT_MODEL: str = "saaras:v4"

    # ML Feature Flags (Phase 5D)
    ENABLE_ORGAN_VALIDATOR: bool = False

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
