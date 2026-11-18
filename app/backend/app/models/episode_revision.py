from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class EpisodeRevision(Base):
    __tablename__ = "episode_revisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    scene_breakdown = Column(JSON().with_variant(SQLiteJSON, "sqlite"), nullable=True)
    full_text = Column(Text, nullable=True)
    change_notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    episode = relationship("Episode", backref="revisions")
    creator = relationship("User", backref="episode_revisions")

    __table_args__ = (
        Index("ix_episode_revisions_episode_revision", "episode_id", "revision_number", unique=True),
    )