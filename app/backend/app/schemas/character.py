from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime
import json


class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    order_index: int = Field(default=0, ge=0)
    
    # Physical appearance
    age: Optional[str] = Field(None, max_length=50)
    gender: Optional[str] = Field(None, max_length=50)
    ethnicity: Optional[str] = Field(None, max_length=100)
    height: Optional[str] = Field(None, max_length=50)
    build: Optional[str] = Field(None, max_length=50)
    hair_color: Optional[str] = Field(None, max_length=50)
    hair_style: Optional[str] = Field(None, max_length=100)
    eye_color: Optional[str] = Field(None, max_length=50)
    skin_tone: Optional[str] = Field(None, max_length=50)
    distinguishing_features: Optional[str] = None
    
    # Personality & background
    personality_traits: Optional[Union[List[str], str]] = None
    background: Optional[str] = None
    motivations: Optional[str] = None
    fears: Optional[str] = None
    quirks: Optional[str] = None

    # Voice & physicality (used by Scene Engine dialogue/action prompts)
    voice_pattern: Optional[str] = None
    physical_traits: Optional[str] = None
    skills: Optional[Union[List[str], str]] = None
    
    # Costume
    costume_style: Optional[str] = None
    signature_items: Optional[Union[List[str], str]] = None
    color_palette: Optional[Union[List[str], str]] = None
    
    # Reference images & consistency
    reference_images: Optional[Union[List[str], str]] = None
    consistency_instructions: Optional[str] = None

    @field_validator('personality_traits', 'signature_items', 'color_palette', 'reference_images', 'skills', mode='before')
    @classmethod
    def parse_json_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    order_index: Optional[int] = Field(None, ge=0)
    age: Optional[str] = Field(None, max_length=50)
    gender: Optional[str] = Field(None, max_length=50)
    ethnicity: Optional[str] = Field(None, max_length=100)
    height: Optional[str] = Field(None, max_length=50)
    build: Optional[str] = Field(None, max_length=50)
    hair_color: Optional[str] = Field(None, max_length=50)
    hair_style: Optional[str] = Field(None, max_length=100)
    eye_color: Optional[str] = Field(None, max_length=50)
    skin_tone: Optional[str] = Field(None, max_length=50)
    distinguishing_features: Optional[str] = None
    personality_traits: Optional[List[str]] = None
    background: Optional[str] = None
    motivations: Optional[str] = None
    fears: Optional[str] = None
    quirks: Optional[str] = None
    voice_pattern: Optional[str] = None
    physical_traits: Optional[str] = None
    skills: Optional[List[str]] = None
    costume_style: Optional[str] = None
    signature_items: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    reference_images: Optional[List[str]] = None
    consistency_instructions: Optional[str] = None


class CharacterResponse(CharacterBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True