from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AssembleRequest(BaseModel):
    episode_id: Optional[str] = None
    input_keys: List[str] = Field(..., min_length=1)
    subtitle_key: Optional[str] = None
    audio_key: Optional[str] = None
    resolution: str = "1080x1920"


class VideoJobResponse(BaseModel):
    id: str
    project_id: str
    episode_id: Optional[str] = None
    status: str
    input_files: Optional[str] = None
    output_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
