from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
import uuid
import enum


class EpisodeStatus(str, enum.Enum):
    PLANNED = "planned"
    OUTLINED = "outlined"
    SCENES_WRITTEN = "scenes_written"
    PROMPTS_READY = "prompts_ready"
    IN_PRODUCTION = "in_production"
    POST_PRODUCTION = "post_production"
    COMPLETED = "completed"


class SceneStatus(str, enum.Enum):
    PLANNED = "planned"
    WRITTEN = "written"
    PROMPTS_READY = "prompts_ready"
    GENERATING = "generating"
    GENERATED = "generated"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class ShotStatus(str, enum.Enum):
    PLANNED = "planned"
    PROMPT_READY = "prompt_ready"
    GENERATING = "generating"
    GENERATED = "generated"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class Episode(Base):
    __tablename__ = "episodes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(SQLEnum(EpisodeStatus), default=EpisodeStatus.PLANNED, nullable=False)
    
    # Production tracking
    estimated_cost = Column(Integer, default=0)  # in cents
    actual_cost = Column(Integer, default=0)
    production_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = relationship("Project", back_populates="episodes")
    scenes = relationship("Scene", back_populates="episode", cascade="all, delete-orphan", order_by="Scene.scene_number")


class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=True)
    time_of_day = Column(String(50), nullable=True)
    duration_estimate = Column(Integer, nullable=True)  # in seconds
    status = Column(SQLEnum(SceneStatus), default=SceneStatus.PLANNED, nullable=False)
    
    # Content
    action = Column(Text, nullable=True)
    dialogue = Column(Text, nullable=True)  # JSON as text
    characters_present = Column(Text, nullable=True)  # JSON array of character IDs
    
    # Production
    production_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    episode = relationship("Episode", back_populates="scenes")
    location = relationship("Location")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan", order_by="Shot.shot_number")


class Shot(Base):
    __tablename__ = "shots"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=False, index=True)
    shot_number = Column(Integer, nullable=False)
    shot_type = Column(String(50), nullable=True)  # wide, medium, closeup, extreme_closeup, etc.
    camera_angle = Column(String(50), nullable=True)  # eye_level, high, low, dutch, etc.
    camera_movement = Column(String(100), nullable=True)  # static, pan, tilt, dolly, crane, handheld, etc.
    duration = Column(Integer, nullable=True)  # in seconds
    description = Column(Text, nullable=True)
    characters_in_shot = Column(Text, nullable=True)  # JSON array of character IDs
    status = Column(SQLEnum(ShotStatus), default=ShotStatus.PLANNED, nullable=False)
    
    # Prompts
    image_prompt = Column(Text, nullable=True)
    video_prompt = Column(Text, nullable=True)
    
    # Generated assets
    generated_image_url = Column(String(500), nullable=True)
    generated_video_url = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    scene = relationship("Scene", back_populates="shots")