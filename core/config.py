"""
Initializing settings with envaironment variables. such as database, smtp etc.
"""
import os
from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Settings class to maintain the configuration properties.
    """
    # Database Settings
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Email Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SMTP_USE_TLS: bool

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """
        This function return database url
        """
        return (f"postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
                f"/{self.POSTGRES_DB}")

    @property
    def email_settings(self) -> Dict:
        """
        This function return smtp credentials to setup the email integrations
        """
        return {
            "smtp_host": self.SMTP_HOST,
            "smtp_port": self.SMTP_PORT,
            "smtp_username": self.SMTP_USERNAME,
            "smtp_password": self.SMTP_PASSWORD,
            "smtp_from": self.SMTP_FROM,
            "smtp_use_tls": self.SMTP_USE_TLS,
        }

settings = Settings()
