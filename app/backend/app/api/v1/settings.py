from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.encryption import encryption_service
from app.api.v1.auth import get_current_user, create_audit_log
from app.api.deps import get_current_superuser
from app.models.user import User
from app.models.settings import AppSettings
from app.models.audit_log import AuditAction
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdate, AIProviderConfig

router = APIRouter(prefix="/settings", tags=["Settings"])


async def get_or_create_settings(db: AsyncSession) -> AppSettings:
    """Get the single AppSettings row, create if not exists. Seed default provider if missing."""
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AppSettings(
            ai_providers=[
                {
                    "id": "nvidia-nemotron-550b",
                    "provider": "nvidia",
                    "model": "nvidia/nemotron-3-ultra-550b-a55b",
                    "key_env": "NVIDIA_API_KEY",
                    "enabled": True,
                    "priority": 1,
                }
            ]
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    elif not settings.ai_providers:
        settings.ai_providers = [
            {
                "id": "nvidia-nemotron-550b",
                "provider": "nvidia",
                "model": "nvidia/nemotron-3-ultra-550b-a55b",
                "key_env": "NVIDIA_API_KEY",
                "enabled": True,
                "priority": 1,
            }
        ]
        await db.commit()
        await db.refresh(settings)
    return settings


def settings_to_response(settings: AppSettings) -> AppSettingsResponse:
    """Convert AppSettings to response, checking key configuration without exposing values."""
    providers_response = []
    for p in settings.ai_providers or []:
        key_env = p.get("key_env", "")
        key_configured = bool(key_env and __import__('os').getenv(key_env))
        providers_response.append(AIProviderConfig(
            id=p.get("id", ""),
            provider=p.get("provider", ""),
            model=p.get("model", ""),
            key_env=key_env,
            enabled=p.get("enabled", True),
            priority=p.get("priority", 999),
            key_configured=key_configured,
        ))

    return AppSettingsResponse(
        id=settings.id,
        ai_providers=providers_response,
        google_oauth_client_id_configured=bool(settings.google_oauth_client_id_encrypted),
        google_oauth_client_secret_configured=bool(settings.google_oauth_client_secret_encrypted),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("", response_model=AppSettingsResponse)
async def get_settings(
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get application settings (superuser only). Never returns secret values."""
    settings = await get_or_create_settings(db)
    # NOTE: read operations are not audit-logged (audit F-23: GET previously
    # logged a misleading PROJECT_READ action).
    return settings_to_response(settings)


@router.patch("", response_model=AppSettingsResponse)
async def update_settings(
    update_data: AppSettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Update application settings (superuser only)."""
    settings = await get_or_create_settings(db)
    
    old_values = {
        "ai_providers": settings.ai_providers,
        "google_oauth_client_id_configured": bool(settings.google_oauth_client_id_encrypted),
        "google_oauth_client_secret_configured": bool(settings.google_oauth_client_secret_encrypted),
    }
    
    update_dict = update_data.model_dump(exclude_unset=True)

    if "ai_providers" in update_dict:
        # Validate and serialize providers. NOTE: model_dump() above already
        # converted nested AIProviderConfig models to plain dicts, so handle
        # both dicts and models (audit: 'dict' object has no attribute
        # 'model_dump' used to 500 every PATCH with ai_providers).
        # Allowlist (audit F-20): only real providers are accepted; the
        # deterministic "mock" provider is test-only and is rejected unless
        # the TESTING env flag is set (tests seed mock providers directly
        # in the DB, bypassing this endpoint).
        import os
        allowed_providers = {"nvidia"}
        if os.getenv("TESTING") == "true":
            allowed_providers.add("mock")
        providers = update_dict["ai_providers"]
        normalized = []
        for p in providers:
            p = p if isinstance(p, dict) else p.model_dump()
            if p.get("provider") not in allowed_providers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported AI provider: {p.get('provider')!r}. Allowed: {sorted(allowed_providers)}"
                )
            normalized.append(p)
        settings.ai_providers = normalized
    
    if "google_oauth_client_id" in update_dict:
        value = update_dict["google_oauth_client_id"]
        if value:
            settings.google_oauth_client_id_encrypted = encryption_service.encrypt(value)
        else:
            settings.google_oauth_client_id_encrypted = None
    
    if "google_oauth_client_secret" in update_dict:
        value = update_dict["google_oauth_client_secret"]
        if value:
            settings.google_oauth_client_secret_encrypted = encryption_service.encrypt(value)
        else:
            settings.google_oauth_client_secret_encrypted = None
    
    await db.commit()
    await db.refresh(settings)
    
    new_values = {
        "ai_providers": settings.ai_providers,
        "google_oauth_client_id_configured": bool(settings.google_oauth_client_id_encrypted),
        "google_oauth_client_secret_configured": bool(settings.google_oauth_client_secret_encrypted),
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.SETTINGS_UPDATE,
        resource_type="app_settings", resource_id=settings.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values,
    )
    await db.commit()
    
    return settings_to_response(settings)