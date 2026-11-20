from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.core.database import Base


class LlmUsageEvent(Base):
    """One recorded LLM call: token usage + estimated cost.

    Written by the usage_sink attached to AIClient.chat_completion (see
    app/services/llm_usage.py). The event is added to the caller's session
    and flushed there, so it commits together with the step/task that made
    the call — a step that fails and rolls back loses its usage rows too.
    estimated_cost_usd is None when the model has no known price: an
    honest blank, never a guessed number.
    """

    __tablename__ = "llm_usage_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(String(36), ForeignKey("auto_generate_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(100), nullable=False)
    model = Column(String(255), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_llm_usage_project_created", "project_id", "created_at"),
        Index("ix_llm_usage_job_created", "job_id", "created_at"),
    )
