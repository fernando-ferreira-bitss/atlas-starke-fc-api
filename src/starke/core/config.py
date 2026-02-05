"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Mega API
    mega_api_url: str = "https://rest.megaerp.online"
    mega_api_tenant_id: str
    mega_api_username: str
    mega_api_password: str
    mega_api_timeout: int = 30
    mega_api_max_retries: int = 3
    mega_max_workers: int = 4  # Parallel workers for contract/parcela sync

    # UAU API (Globaltec/Senior)
    uau_api_url: str = "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0"
    uau_integration_token: str = ""  # Token fixo de integração
    uau_username: str = ""
    uau_password: str = ""
    uau_timeout: int = 120
    uau_max_retries: int = 3
    uau_max_workers: int = 2  # Parallel workers for batch operations

    # Database
    database_url: str = "sqlite:///./data/starke.db"

    # Email
    email_backend: Literal["smtp", "gmail_api"] = "smtp"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    gmail_credentials_file: str = "./secrets/gmail-credentials.json"

    email_from_name: str = "Relatórios Starke"
    email_from_address: str

    # Authentication & Security
    jwt_secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT token generation. MUST be changed in production!",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480  # 8 hours

    # Report
    report_timezone: str = "America/Sao_Paulo"
    execution_time: str = "08:00"
    date_format: str = "%Y-%m-%d"

    # Alerting
    alert_email_recipients: str = ""

    # Testing
    test_mode: bool = False
    test_email_recipient: str = ""

    @field_validator("alert_email_recipients")
    @classmethod
    def parse_email_list(cls, v: str) -> list[str]:
        """Parse comma-separated email list."""
        if not v:
            return []
        return [email.strip() for email in v.split(",") if email.strip()]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
