from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=True)  # protagonist, antagonist, supporting, etc.
    order_index = Column(Integer, default=0)  # for ordering characters
    
    # Physical appearance
    age = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    ethnicity = Column(String(100), nullable=True)
    height = Column(String(50), nullable=True)
    build = Column(String(50), nullable=True)
    hair_color = Column(String(50), nullable=True)
    hair_style = Column(String(100), nullable=True)
    eye_color = Column(String(50), nullable=True)
    skin_tone = Column(String(50), nullable=True)
    distinguishing_features = Column(Text, nullable=True)
    
    # Personality & background
    personality_traits = Column(Text, nullable=True)  # JSON array as text
    background = Column(Text, nullable=True)
    motivations = Column(Text, nullable=True)
    fears = Column(Text, nullable=True)
    quirks = Column(Text, nullable=True)
    # Voice & physicality (used by Scene Engine dialogue/action prompts)
    voice_pattern = Column(Text, nullable=True)
    physical_traits = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)  # JSON array as text
    
    # Costume
    costume_style = Column(Text, nullable=True)
    signature_items = Column(Text, nullable=True)  # JSON array as text
    color_palette = Column(Text, nullable=True)  # JSON array as text
    
    # Reference images & consistency
    reference_images = Column(Text, nullable=True)  # JSON array of URLs/paths
    consistency_instructions = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = relationship("Project", back_populates="characters")