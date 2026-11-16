from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    APP_NAME: str = "Micro Drama SaaS"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./micro_drama.db"
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    GOOGLE_ACCOUNTS_MAX_PER_USER: int = 20
    
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()