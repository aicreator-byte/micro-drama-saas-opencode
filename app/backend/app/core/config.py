from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import logging
import secrets

logger = logging.getLogger(__name__)

# .env is resolved from the CODE location, never from the process CWD
# (audit SH-1: running the server from the wrong directory silently lost
# the key, because Settings only read "./.env"). The leg root (opencode/)
# holds .env; app/backend/ may hold one too. pydantic-settings reads the
# list in order and later files win: backend/.env > leg-root/.env > CWD.
_BACKEND_DIR = Path(__file__).resolve().parents[2]  # app/backend
_LEG_ROOT = _BACKEND_DIR.parent.parent  # opencode/
_ENV_FILES = (".env", str(_LEG_ROOT / ".env"), str(_BACKEND_DIR / ".env"))


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

    # --- Asset storage (S3-compatible abstraction, default local) ---
    ASSET_STORAGE_DIR: str = "./uploads/assets"
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_CDN_BASE_URL: str = ""
    
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

    # Fase 3 smoke live: ai_client baca NVIDIA_API_KEY via os.getenv;
    # field harus dideklarasi agar Settings tidak menolaknya (extra_forbidden).
    NVIDIA_API_KEY: str = ""
    # Ada di .env root (untuk frontend/docker-compose); dideklarasi juga
    # agar Settings tidak menolaknya (extra_forbidden).
    NEXT_PUBLIC_API_URL: str = ""

    # --- Billing (Stripe, TEST MODE SAJA) ---
    # Live key (sk_live_...) DITOLAK keras oleh StripeClient — Di tidak
    # punya kartu kredit, jadi build ini tidak boleh menyentuh live mode.
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_STUDIO: str = ""

    class Config:
        env_file = _ENV_FILES
        case_sensitive = True


settings = Settings()


def _ensure_usable_database_url() -> None:
    """Guard: the leg .env ships a postgresql+asyncpg DATABASE_URL, but
    this venv has no asyncpg driver and no Postgres server — creating the
    engine would crash at import. If the configured driver is unavailable,
    fall back to the local sqlite file under the leg root (loud warning,
    not silent). An explicitly exported DATABASE_URL (start script, tests)
    is honoured as-is."""
    url = settings.DATABASE_URL
    scheme = url.split("://", 1)[0].lower()
    if scheme in ("postgresql+asyncpg", "postgresql", "postgres"):
        try:
            import asyncpg  # noqa: F401
        except ImportError:
            fallback = f"sqlite+aiosqlite:///{_LEG_ROOT / 'micro_drama.db'}"
            logger.warning(
                "DATABASE_URL from .env uses %s but asyncpg is not installed; "
                "falling back to %s",
                scheme, fallback,
            )
            settings.DATABASE_URL = fallback


_ensure_usable_database_url()