from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # AI Providers configuration (JSON array)
    # Each entry: {id, provider, model, key_env, enabled, priority}
    ai_providers = Column(JSON().with_variant(SQLiteJSON, "sqlite"), nullable=True)
    
    # Google OAuth credentials (encrypted)
    google_oauth_client_id_encrypted = Column(Text, nullable=True)
    google_oauth_client_secret_encrypted = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)