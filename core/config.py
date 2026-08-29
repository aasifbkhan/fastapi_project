from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict

class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"                
                f"/{self.POSTGRES_DB}")

    @property
    def email_settings(self) -> Dict:
        return {
            "smtp_host": self.SMTP_HOST,
            "smtp_port": self.SMTP_PORT,
            "smtp_username": self.SMTP_USERNAME,
            "smtp_password": self.SMTP_PASSWORD,
            "smtp_from": self.SMTP_FROM
        }

settings = Settings()