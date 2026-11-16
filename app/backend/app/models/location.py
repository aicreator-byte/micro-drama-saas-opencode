from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid


class Location(Base):
    __tablename__ = "locations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)  # interior, exterior, studio, etc.
    order_index = Column(Integer, default=0)
    
    # Environment description
    description = Column(Text, nullable=True)
    environment_details = Column(Text, nullable=True)  # JSON as text
    
    # Visual references
    reference_images = Column(Text, nullable=True)  # JSON array of URLs/paths
    visual_style_notes = Column(Text, nullable=True)
    
    # Lighting and atmosphere
    lighting = Column(Text, nullable=True)  # JSON as text (key_light, fill_light, mood, etc.)
    atmosphere = Column(Text, nullable=True)
    time_of_day = Column(String(50), nullable=True)
    weather = Column(String(100), nullable=True)
    
    # Consistency
    consistency_instructions = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="locations")