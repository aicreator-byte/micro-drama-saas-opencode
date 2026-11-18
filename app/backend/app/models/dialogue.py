from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class Dialogue(Base):
    __tablename__ = "dialogues"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
    line_number = Column(Integer, nullable=False)
    character_name = Column(String(255), nullable=False)
    dialogue_text = Column(Text, nullable=False)
    parenthetical = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    beat_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    scene = relationship("Scene", backref="dialogues")
    character = relationship("Character", backref="dialogues")

    __table_args__ = (
        Index("ix_dialogues_scene_line", "scene_id", "line_number", unique=True),
    )