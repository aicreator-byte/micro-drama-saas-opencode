from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
import enum
import json


class PromptType(str, enum.Enum):
    CHARACTER_IMAGE = "character_image"
    LOCATION_IMAGE = "location_image"
    SCENE_IMAGE = "scene_image"
    VIDEO_GENERATION = "video_generation"
    CAMERA_MOVEMENT = "camera_movement"
    CHARACTER_ACTION = "character_action"
    DIALOGUE_AUDIO = "dialogue_audio"
    SOUND_EFFECT = "sound_effect"
    MUSIC = "music"


class PromptStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    USED = "used"
    ARCHIVED = "archived"


class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    shot_id = Column(String(36), ForeignKey("shots.id"), nullable=True, index=True)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=True, index=True)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=True, index=True)
    
    prompt_type = Column(SQLEnum(PromptType), nullable=False)
    title = Column(String(255), nullable=True)
    prompt_text = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    parameters = Column(Text, nullable=True)  # JSON as text (model, steps, cfg, seed, etc.)
    
    status = Column(SQLEnum(PromptStatus), default=PromptStatus.DRAFT, nullable=False)
    version = Column(Integer, default=1)
    parent_prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=True)
    
    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    project = relationship("Project")
    episode = relationship("Episode")
    scene = relationship("Scene")
    shot = relationship("Shot")
    character = relationship("Character")
    location = relationship("Location")
    creator = relationship("User")
    parent = relationship("Prompt", remote_side=[id], backref="versions")
    
    @property
    def parameters_dict(self) -> dict | None:
        """Parse parameters JSON string to dict."""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except (json.JSONDecodeError, TypeError):
                try:
                    import ast
                    return ast.literal_eval(self.parameters)
                except (ValueError, SyntaxError):
                    return None
        return None