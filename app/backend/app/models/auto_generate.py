from sqlalchemy import Column, String, Text, DateTime, Integer, Enum as SQLEnum, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.core.database import Base
import enum


class AutoGenerateJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AutoGenerateStepName(str, enum.Enum):
    SERIES_BIBLE = "series_bible"
    CHARACTERS = "characters"
    LOCATIONS = "locations"
    EPISODES = "episodes"
    PROMPTS = "prompts"


class AutoGenerateStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Fixed execution order (spec section 4). Retry re-runs the failed step and
# then continues with the later pending steps, in this order.
STEP_ORDER = [
    AutoGenerateStepName.SERIES_BIBLE,
    AutoGenerateStepName.CHARACTERS,
    AutoGenerateStepName.LOCATIONS,
    AutoGenerateStepName.EPISODES,
    AutoGenerateStepName.PROMPTS,
]


class AutoGenerateJob(Base):
    __tablename__ = "auto_generate_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    # Input the user gave (title/genre/episodes/premise). Title is required;
    # genre/premise are optional.
    title = Column(String(255), nullable=False)
    genre = Column(String(100), nullable=True)
    total_episodes = Column(Integer, default=30, nullable=False)
    premise = Column(Text, nullable=True)
    status = Column(SQLEnum(AutoGenerateJobStatus), default=AutoGenerateJobStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="auto_generate_jobs")
    steps = relationship(
        "AutoGenerateStep",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AutoGenerateStep.step_order",
    )

    __table_args__ = (
        Index("ix_auto_generate_jobs_project_status", "project_id", "status"),
    )


class AutoGenerateStep(Base):
    __tablename__ = "auto_generate_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("auto_generate_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step = Column(SQLEnum(AutoGenerateStepName), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(SQLEnum(AutoGenerateStepStatus), default=AutoGenerateStepStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    # Small summary of what the step produced, e.g. {"created_characters": [...]}.
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    job = relationship("AutoGenerateJob", back_populates="steps")

    __table_args__ = (
        Index("ix_auto_generate_steps_job_order", "job_id", "step_order"),
    )
