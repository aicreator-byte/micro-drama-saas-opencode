from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
import enum


class AuditAction(str, enum.Enum):
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    
    # Project
    PROJECT_CREATE = "project_create"
    PROJECT_READ = "project_read"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"
    
    # Series Bible
    SERIES_BIBLE_CREATE = "series_bible_create"
    SERIES_BIBLE_READ = "series_bible_read"
    SERIES_BIBLE_UPDATE = "series_bible_update"
    SERIES_BIBLE_DELETE = "series_bible_delete"
    
    # Character
    CHARACTER_CREATE = "character_create"
    CHARACTER_READ = "character_read"
    CHARACTER_UPDATE = "character_update"
    CHARACTER_DELETE = "character_delete"
    
    # Location
    LOCATION_CREATE = "location_create"
    LOCATION_READ = "location_read"
    LOCATION_UPDATE = "location_update"
    LOCATION_DELETE = "location_delete"
    
    # Episode
    EPISODE_CREATE = "episode_create"
    EPISODE_READ = "episode_read"
    EPISODE_UPDATE = "episode_update"
    EPISODE_DELETE = "episode_delete"
    
    # Scene
    SCENE_CREATE = "scene_create"
    SCENE_READ = "scene_read"
    SCENE_UPDATE = "scene_update"
    SCENE_DELETE = "scene_delete"
    
    # Shot
    SHOT_CREATE = "shot_create"
    SHOT_READ = "shot_read"
    SHOT_UPDATE = "shot_update"
    SHOT_DELETE = "shot_delete"
    
    # Prompt
    PROMPT_CREATE = "prompt_create"
    PROMPT_READ = "prompt_read"
    PROMPT_UPDATE = "prompt_update"
    PROMPT_DELETE = "prompt_delete"
    PROMPT_EXPORT = "prompt_export"
    
    # Google Account
    GOOGLE_ACCOUNT_CONNECT = "google_account_connect"
    GOOGLE_ACCOUNT_DISCONNECT = "google_account_disconnect"
    GOOGLE_ACCOUNT_UPDATE = "google_account_update"
    GOOGLE_ACCOUNT_VERIFY = "google_account_verify"
    
    # Flow Bridge
    FLOW_TASK_CREATE = "flow_task_create"
    FLOW_TASK_UPDATE = "flow_task_update"
    FLOW_TASK_EXECUTE = "flow_task_execute"
    FLOW_ASSET_UPLOAD = "flow_asset_upload"
    FLOW_ASSET_DOWNLOAD = "flow_asset_download"
    
    # Export
    EXPORT_PROJECT = "export_project"
    EXPORT_EPISODE = "export_episode"
    EXPORT_PROMPTS = "export_prompts"
    
    # Story Engine
    STORY_ENGINE_TASK_CREATE = "story_engine_task_create"
    STORY_ENGINE_TASK_READ = "story_engine_task_read"
    STORY_ENGINE_TASK_UPDATE = "story_engine_task_update"
    STORY_ENGINE_TASK_EXECUTE = "story_engine_task_execute"
    
    # Scene Engine
    SCENE_ENGINE_TASK_CREATE = "scene_engine_task_create"
    SCENE_ENGINE_TASK_READ = "scene_engine_task_read"
    SCENE_ENGINE_TASK_UPDATE = "scene_engine_task_update"
    SCENE_ENGINE_TASK_EXECUTE = "scene_engine_task_execute"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)  # project, character, etc.
    resource_id = Column(String(36), nullable=True, index=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    
    # Changes (for update actions)
    old_values = Column(Text, nullable=True)  # JSON as text
    new_values = Column(Text, nullable=True)  # JSON as text
    
    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="audit_logs")