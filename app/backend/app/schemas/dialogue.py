from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DialogueCreate(BaseModel):
    character_id: Optional[str] = None
    line_number: int = Field(..., ge=1)
    character_name: str = Field(..., min_length=1, max_length=255)
    dialogue_text: str = Field(..., min_length=1)
    parenthetical: Optional[str] = None
    action: Optional[str] = None
    beat_number: Optional[int] = None


class DialogueResponse(BaseModel):
    id: str
    scene_id: str
    character_id: Optional[str] = None
    line_number: int
    character_name: str
    dialogue_text: str
    parenthetical: Optional[str] = None
    action: Optional[str] = None
    beat_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
