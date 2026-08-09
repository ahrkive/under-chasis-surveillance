"""
Backend Configuration — Pydantic Settings
==========================================
Centralized configuration loaded from environment variables / .env file.
All backend settings are validated and typed at startup.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Authentication ───────────────────────────────────────────────────
    secret_key: str = "change-me-to-a-very-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── Edge Authentication ──────────────────────────────────────────────
    edge_api_key: str = "change-me-to-a-secure-key"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # ── Storage ──────────────────────────────────────────────────────────
    storage_provider: Literal["local", "s3", "gcs", "azure"] = "local"
    storage_local_path: str = "./data/images"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "undercarriage-inspections"

    # Google Cloud Storage
    gcs_bucket_name: str = "undercarriage-inspections"
    gcs_credentials_path: str = ""

    # Azure Blob
    azure_connection_string: str = ""
    azure_container_name: str = "undercarriage-inspections"

    # ── AI / Model ───────────────────────────────────────────────────────
    model_dir: str = "./models"
    active_model_version: int = 0  # 0 = no model loaded yet
    inference_device: str = "cpu"
    min_images_for_training: int = 50
    training_schedule_cron: str = "0 2 * * 0"  # Sunday 2:00 AM

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000,*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        Path(self.storage_local_path).mkdir(parents=True, exist_ok=True)
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        # Ensure SQLite directory exists
        if "sqlite" in self.database_url:
            db_path = self.database_url.split("///")[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# ── Singleton ────────────────────────────────────────────────────────────
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
