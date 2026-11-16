from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import json


class SeriesBibleBase(BaseModel):
    premise: Optional[str] = None
    main_plot: Optional[str] = None
    subplots: Optional[List[str]] = None
    character_relationships: Optional[str] = None
    world_settings: Optional[str] = None
    tone_and_visual_style: Optional[str] = None
    ending_direction: Optional[str] = None
    episode_structure: Optional[str] = None


class SeriesBibleCreate(SeriesBibleBase):
    pass


class SeriesBibleUpdate(SeriesBibleBase):
    pass


class SeriesBibleResponse(SeriesBibleBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    
    @field_validator('subplots', mode='before')
    @classmethod
    def parse_subplots(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v
    
    class Config:
        from_attributes = True