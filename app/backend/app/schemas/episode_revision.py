from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class EpisodeRevisionCreate(BaseModel):
    change_notes: Optional[str] = None


class EpisodeRevisionResponse(BaseModel):
    id: str
    episode_id: str
    revision_number: int
    title: Optional[str] = None
    summary: Optional[str] = None
    scene_breakdown: Optional[Dict[str, Any]] = None
    full_text: Optional[str] = None
    change_notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
