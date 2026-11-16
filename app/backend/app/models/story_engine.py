from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class StoryEngineTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryEngineTaskType(str, enum.Enum):
    GENERATE_OUTLINE = "generate_outline"
    GENERATE_EPISODE = "generate_episode"
    GENERATE_CHARACTER_ARCS = "generate_character_arcs"
    GENERATE_WORLD_BUILDING = "generate_world_building"
    REFINE_STORY = "refine_story"


class StoryEngineTask(Base):
    __tablename__ = "story_engine_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    series_bible_id = Column(String(36), ForeignKey("series_bibles.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type = Column(SQLEnum(StoryEngineTaskType), nullable=False)
    status = Column(SQLEnum(StoryEngineTaskStatus), default=StoryEngineTaskStatus.PENDING, nullable=False)
    input_parameters = Column(JSON, nullable=True)
    context = Column(Text, nullable=True)
    output = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="story_engine_tasks")
    series_bible = relationship("SeriesBible", backref="story_engine_tasks")
    episode = relationship("Episode", backref="story_engine_tasks")

    __table_args__ = (
        Index("ix_story_engine_tasks_project_status", "project_id", "status"),
        Index("ix_story_engine_tasks_series_bible_type", "series_bible_id", "task_type"),
    )