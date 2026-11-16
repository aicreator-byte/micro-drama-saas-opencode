from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
import enum


class FlowBridgeTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY_FOR_GENERATION = "ready_for_generation"
    GENERATING = "generating"
    WAITING_FOR_IMPORT = "waiting_for_import"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowBridgeAssetType(str, enum.Enum):
    REFERENCE_IMAGE = "reference_image"
    CHARACTER_IMAGE = "character_image"
    LOCATION_IMAGE = "location_image"
    STORYBOARD = "storyboard"
    VIDEO_CLIP = "video_clip"
    AUDIO_CLIP = "audio_clip"
    SUBTITLE_FILE = "subtitle_file"
    OTHER = "other"


class FlowBridgeTask(Base):
    __tablename__ = "flow_bridge_tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    shot_id = Column(String(36), ForeignKey("shots.id"), nullable=True, index=True)
    google_account_id = Column(String(36), ForeignKey("google_accounts.id"), nullable=True)
    
    # Task definition
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(100), nullable=True)  # image_gen, video_gen, etc.
    status = Column(SQLEnum(FlowBridgeTaskStatus), default=FlowBridgeTaskStatus.PENDING, nullable=False)
    
    # Input data
    input_prompts = Column(Text, nullable=True)  # JSON as text
    input_references = Column(Text, nullable=True)  # JSON array of asset IDs/URLs
    input_parameters = Column(Text, nullable=True)  # JSON as text
    
    # Output tracking
    output_assets = Column(Text, nullable=True)  # JSON array of generated asset IDs
    generation_log = Column(Text, nullable=True)  # JSON as text
    error_message = Column(Text, nullable=True)
    
    # Automation
    automation_data = Column(Text, nullable=True)  # JSON for browser automation state
    manual_steps_completed = Column(Text, nullable=True)  # JSON array
    
    # Metadata
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    project = relationship("Project")
    episode = relationship("Episode")
    scene = relationship("Scene")
    shot = relationship("Shot")
    google_account = relationship("GoogleAccount")
    assets = relationship("FlowBridgeAsset", back_populates="task", cascade="all, delete-orphan")


class FlowBridgeAsset(Base):
    __tablename__ = "flow_bridge_assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("flow_bridge_tasks.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    
    # Asset info
    asset_type = Column(SQLEnum(FlowBridgeAssetType), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # File info
    file_path = Column(String(500), nullable=True)  # Local path or S3 key
    file_url = Column(String(500), nullable=True)  # Public URL if available
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA256
    
    # Source tracking
    source = Column(String(100), nullable=True)  # flow, upload, generated, etc.
    source_metadata = Column(Text, nullable=True)  # JSON as text
    
    # Associations
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    shot_id = Column(String(36), ForeignKey("shots.id"), nullable=True, index=True)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=True, index=True)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    task = relationship("FlowBridgeTask", back_populates="assets")
    project = relationship("Project")
    episode = relationship("Episode")
    scene = relationship("Scene")
    shot = relationship("Shot")
    character = relationship("Character")
    location = relationship("Location")