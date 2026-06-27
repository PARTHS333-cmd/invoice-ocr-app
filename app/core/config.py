"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Invoice OCR Processor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    SECRET_KEY: str = "change-me-in-production-min-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    
    UPLOAD_DIR: str = "uploads/documents"
    
    OCR_LANG: str = "en"
    max_upload_size: int = 104857600

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Module-level instance for direct import compatibility
settings = get_settings()