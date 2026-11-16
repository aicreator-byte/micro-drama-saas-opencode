from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class SceneEngineTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SceneEngineTaskType(str, enum.Enum):
    BREAKDOWN_EPISODE = "breakdown_episode"
    GENERATE_SCENES = "generate_scenes"
    GENERATE_SHOTS = "generate_shots"
    GENERATE_DIALOGUE = "generate_dialogue"
    GENERATE_ACTION = "generate_action"
    REFINE_SCENES = "refine_scenes"


class SceneEngineTask(Base):
    __tablename__ = "scene_engine_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(String(36), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type = Column(SQLEnum(SceneEngineTaskType), nullable=False)
    status = Column(SQLEnum(SceneEngineTaskStatus), default=SceneEngineTaskStatus.PENDING, nullable=False)
    input_parameters = Column(JSON, nullable=True)
    context = Column(Text, nullable=True)
    output = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="scene_engine_tasks")
    episode = relationship("Episode", backref="scene_engine_tasks")
    scene = relationship("Scene", backref="scene_engine_tasks")

    __table_args__ = (
        Index("ix_scene_engine_tasks_project_status", "project_id", "status"),
        Index("ix_scene_engine_tasks_episode_type", "episode_id", "task_type"),
    )