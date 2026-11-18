from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AIProviderConfig(BaseModel):
    id: str
    provider: str
    model: str
    key_env: str
    enabled: bool = True
    priority: int = 999
    key_configured: Optional[bool] = None  # Only in GET response


class AppSettingsBase(BaseModel):
    ai_providers: List[AIProviderConfig] = []
    google_oauth_client_id_configured: bool = False
    google_oauth_client_secret_configured: bool = False


class AppSettingsResponse(AppSettingsBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppSettingsUpdate(BaseModel):
    ai_providers: Optional[List[AIProviderConfig]] = None
    google_oauth_client_id: Optional[str] = None  # Plaintext, will be encrypted
    google_oauth_client_secret: Optional[str] = None  # Plaintext, will be encrypted