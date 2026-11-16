from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SceneEngineTaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SceneEngineTaskType(str, Enum):
    BREAKDOWN_EPISODE = "breakdown_episode"
    GENERATE_SCENES = "generate_scenes"
    GENERATE_SHOTS = "generate_shots"
    GENERATE_DIALOGUE = "generate_dialogue"
    GENERATE_ACTION = "generate_action"
    REFINE_SCENES = "refine_scenes"


class SceneEngineRequest(BaseModel):
    task_type: SceneEngineTaskType
    episode_id: str
    scene_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    context: Optional[str] = None


class SceneEngineResponse(BaseModel):
    id: str
    project_id: str
    episode_id: str
    scene_id: Optional[str] = None
    task_type: SceneEngineTaskType
    status: SceneEngineTaskStatus
    input_parameters: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SceneBreakdown(BaseModel):
    scene_number: int
    title: str
    description: str
    location: Optional[str] = None
    characters: List[str] = []
    estimated_duration: str = "2-3 minutes"
    beat_type: str = "dramatic"
    key_dialogue_hint: Optional[str] = None
    action_summary: Optional[str] = None


class EpisodeBreakdownResponse(BaseModel):
    episode_id: str
    total_scenes: int
    scenes: List[SceneBreakdown]
    generated_at: datetime


class ShotBreakdown(BaseModel):
    shot_number: int
    scene_id: str
    shot_type: str  # wide, medium, closeup, extreme_closeup, etc.
    camera_angle: str  # eye_level, high_angle, low_angle, dutch_angle, etc.
    camera_movement: str  # static, pan, tilt, dolly, crane, handheld, etc.
    description: str
    characters_in_shot: List[str] = []
    estimated_duration: str = "3-5 seconds"
    visual_notes: Optional[str] = None
    audio_cues: Optional[str] = None


class SceneShotsResponse(BaseModel):
    scene_id: str
    total_shots: int
    shots: List[ShotBreakdown]
    generated_at: datetime


class DialogueResponse(BaseModel):
    scene_id: str
    dialogue_blocks: List[Dict[str, Any]]  # character, line, parenthetical, action
    generated_at: datetime


class ActionResponse(BaseModel):
    scene_id: str
    action_beats: List[Dict[str, Any]]  # beat_number, description, characters, props, choreography
    generated_at: datetime


class RefineSceneRequest(BaseModel):
    feedback: str
    refine_type: str = "general"


class RefineSceneResponse(BaseModel):
    task_id: str
    refined_output: Dict[str, Any]
    refined_at: datetime