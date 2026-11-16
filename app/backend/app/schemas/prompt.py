from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.prompt import PromptType, PromptStatus


class PromptBase(BaseModel):
    prompt_type: PromptType
    title: Optional[str] = Field(None, max_length=255)
    prompt_text: str
    negative_prompt: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Optional associations
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None
    character_id: Optional[str] = None
    location_id: Optional[str] = None


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    prompt_text: Optional[str] = None
    negative_prompt: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[PromptStatus] = None
    version: Optional[int] = Field(None, ge=1)


class PromptResponse(PromptBase):
    id: str
    project_id: str
    status: PromptStatus
    version: int
    parent_prompt_id: Optional[str] = None
    times_used: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class PromptExport(BaseModel):
    prompts: List[PromptResponse]
    format: str = "json"  # json, txt, csv