"""
Analytica — Application Settings
Loads configuration from environment variables via pydantic-settings.
"""

import urllib.parse
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    db_type: str = "mysql"
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "brazilian_ecommerce_dw"
    db_user: str = ""
    db_password: str = ""

    # API
    api_title: str = "Analytica"
    api_version: str = "1.0.0"
    cors_origins: str = "http://localhost:3000,http://localhost:7860"

    # Security
    secret_key: str = ""
    admin_token: str = ""
    allow_credentials: bool = True

    @property
    def database_url(self) -> str:
        """Construct database connection string (MySQL or SQLite)."""
        if self.db_type == "sqlite":
            db_path = Path(__file__).resolve().parent.parent.parent / "analytica.db"
            return f"sqlite+aiosqlite:///{db_path}"
        password = urllib.parse.quote_plus(self.db_password)
        return (
            f"mysql+aiomysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync MySQL connection string (for migrations/scripts)."""
        password = urllib.parse.quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
