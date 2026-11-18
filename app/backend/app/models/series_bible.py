from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class SeriesBible(Base):
    __tablename__ = "series_bibles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, unique=True, index=True)
    
    # Core story elements
    premise = Column(Text, nullable=True)
    main_plot = Column(Text, nullable=True)
    subplots = Column(Text, nullable=True)  # JSON array as text
    character_relationships = Column(Text, nullable=True)  # JSON as text
    world_settings = Column(Text, nullable=True)
    tone_and_visual_style = Column(Text, nullable=True)
    ending_direction = Column(Text, nullable=True)
    episode_structure = Column(Text, nullable=True)  # JSON as text
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = relationship("Project", back_populates="series_bible")