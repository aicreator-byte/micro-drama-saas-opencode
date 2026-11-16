from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class StoryEngineTaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryEngineTaskType(str, Enum):
    GENERATE_OUTLINE = "generate_outline"
    GENERATE_EPISODE = "generate_episode"
    GENERATE_CHARACTER_ARCS = "generate_character_arcs"
    GENERATE_WORLD_BUILDING = "generate_world_building"
    REFINE_STORY = "refine_story"


class StoryEngineRequest(BaseModel):
    task_type: StoryEngineTaskType
    series_bible_id: str
    parameters: Optional[Dict[str, Any]] = None
    context: Optional[str] = None


class StoryEngineResponse(BaseModel):
    id: str
    project_id: str
    series_bible_id: str
    task_type: StoryEngineTaskType
    status: StoryEngineTaskStatus
    input_parameters: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EpisodeOutline(BaseModel):
    episode_number: int
    title: str
    logline: str
    synopsis: str
    key_beats: List[str]
    character_focus: List[str]


class StoryOutlineResponse(BaseModel):
    series_bible_id: str
    total_episodes: int
    episodes: List[EpisodeOutline]
    generated_at: datetime


class CharacterArcResponse(BaseModel):
    character_id: str
    character_name: str
    arc_summary: str
    key_moments: List[Dict[str, Any]]
    emotional_journey: str
    generated_at: datetime


class WorldBuildingResponse(BaseModel):
    series_bible_id: str
    locations: List[Dict[str, Any]]
    factions: List[Dict[str, Any]]
    technology: List[Dict[str, Any]]
    culture: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    generated_at: datetime


class RefineStoryRequest(BaseModel):
    feedback: str
    refine_type: str = "general"


class RefineStoryResponse(BaseModel):
    task_id: str
    refined_output: Dict[str, Any]
    refined_at: datetime