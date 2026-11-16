from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.episode import EpisodeStatus, SceneStatus, ShotStatus


# Episode schemas
class EpisodeBase(BaseModel):
    episode_number: int = Field(..., ge=1, le=100)
    title: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None


class EpisodeCreate(EpisodeBase):
    pass


class EpisodeUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None
    status: Optional[EpisodeStatus] = None
    estimated_cost: Optional[int] = Field(None, ge=0)
    actual_cost: Optional[int] = Field(None, ge=0)
    production_notes: Optional[str] = None


class EpisodeResponse(EpisodeBase):
    id: str
    project_id: str
    status: EpisodeStatus
    estimated_cost: int
    actual_cost: int
    production_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Scene schemas
class SceneBase(BaseModel):
    scene_number: int = Field(..., ge=1)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    location_id: Optional[str] = None
    time_of_day: Optional[str] = Field(None, max_length=50)
    duration_estimate: Optional[int] = Field(None, ge=0)
    action: Optional[str] = None
    dialogue: Optional[str] = None  # JSON string
    characters_present: Optional[List[str]] = None


class SceneCreate(SceneBase):
    pass


class SceneUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    location_id: Optional[str] = None
    time_of_day: Optional[str] = Field(None, max_length=50)
    duration_estimate: Optional[int] = Field(None, ge=0)
    status: Optional[SceneStatus] = None
    action: Optional[str] = None
    dialogue: Optional[str] = None
    characters_present: Optional[List[str]] = None
    production_notes: Optional[str] = None


class SceneResponse(SceneBase):
    id: str
    episode_id: str
    status: SceneStatus
    production_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Shot schemas
class ShotBase(BaseModel):
    shot_number: int = Field(..., ge=1)
    shot_type: Optional[str] = Field(None, max_length=50)
    camera_angle: Optional[str] = Field(None, max_length=50)
    camera_movement: Optional[str] = Field(None, max_length=100)
    duration: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    characters_in_shot: Optional[List[str]] = None


class ShotCreate(ShotBase):
    pass


class ShotUpdate(BaseModel):
    shot_type: Optional[str] = Field(None, max_length=50)
    camera_angle: Optional[str] = Field(None, max_length=50)
    camera_movement: Optional[str] = Field(None, max_length=100)
    duration: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    characters_in_shot: Optional[List[str]] = None
    status: Optional[ShotStatus] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    generated_image_url: Optional[str] = None
    generated_video_url: Optional[str] = None


class ShotResponse(ShotBase):
    id: str
    scene_id: str
    status: ShotStatus
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    generated_image_url: Optional[str] = None
    generated_video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True