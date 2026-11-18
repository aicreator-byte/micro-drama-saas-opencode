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

    # --- Browser login + Google Flow (no Cloud Console) ---
    # Google Flow (Veo) web app. Env-overridable; the default is the
    # public Labs URL — no client_id/secret is used anywhere on this path.
    GOOGLE_FLOW_URL: str = "https://labs.google/fx/tools/flow"
    # Persistent browser profile per Google account (cookies survive
    # restarts). One subdirectory per account id is created under here.
    FLOW_BROWSER_PROFILE_DIR: str = "~/.cache/micro-drama-saas/browser-profiles"
    # Chromium cannot CONNECT directly to this VM's egress proxy
    # (ERR_TUNNEL_CONNECTION_FAILED); the stdlib CONNECT relay in
    # app.services.browser_proxy fixes it. Without an upstream proxy in
    # the environment the relay connects directly, so leaving this on
    # is harmless elsewhere.
    FLOW_BROWSER_USE_RELAY: bool = True
    # The VM egress proxy MITMs TLS with a custom CA Chromium does not
    # trust; the browser must ignore HTTPS errors to reach Google from
    # here. Security deferred by Di's order — not a hardening choice.
    FLOW_BROWSER_IGNORE_HTTPS_ERRORS: bool = True
    FLOW_BROWSER_HEADLESS: bool = True
    # Flow video generation takes minutes; after this the run returns
    # "submitted" (video may still be generating in Flow).
    FLOW_GENERATION_TIMEOUT_SECONDS: int = 600
    
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()