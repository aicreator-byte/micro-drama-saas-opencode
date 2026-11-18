from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from app.models.flow_bridge import FlowBridgeTaskStatus, FlowBridgeAssetType
import json


class FlowBridgeTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, max_length=100)
    input_prompts: Optional[Union[Dict[str, Any], str]] = None
    input_references: Optional[Union[List[str], str]] = None
    input_parameters: Optional[Union[Dict[str, Any], str]] = None
    priority: int = Field(default=0, ge=0)
    
    # Optional associations
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None
    google_account_id: Optional[str] = None

    @field_validator('input_prompts', 'input_parameters', mode='before')
    @classmethod
    def parse_json_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v

    @field_validator('input_references', mode='before')
    @classmethod
    def parse_list_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class FlowBridgeTaskCreate(FlowBridgeTaskBase):
    pass


class FlowBridgeTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, max_length=100)
    status: Optional[FlowBridgeTaskStatus] = None
    input_prompts: Optional[Union[Dict[str, Any], str]] = None
    input_references: Optional[Union[List[str], str]] = None
    input_parameters: Optional[Union[Dict[str, Any], str]] = None
    output_assets: Optional[Union[List[str], str]] = None
    generation_log: Optional[Union[Dict[str, Any], str]] = None
    error_message: Optional[str] = None
    automation_data: Optional[Union[Dict[str, Any], str]] = None
    manual_steps_completed: Optional[Union[List[str], str]] = None
    priority: Optional[int] = Field(None, ge=0)
    google_account_id: Optional[str] = None

    @field_validator('input_prompts', 'input_parameters', 'output_assets', 'generation_log', 'automation_data', 'manual_steps_completed', mode='before')
    @classmethod
    def parse_json_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v

    @field_validator('input_references', mode='before')
    @classmethod
    def parse_list_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class FlowBridgeTaskResponse(FlowBridgeTaskBase):
    id: str
    project_id: str
    status: FlowBridgeTaskStatus
    output_assets: Optional[Union[List[str], str]] = None
    generation_log: Optional[Union[Dict[str, Any], str]] = None
    error_message: Optional[str] = None
    automation_data: Optional[Union[Dict[str, Any], str]] = None
    manual_steps_completed: Optional[Union[List[str], str]] = None
    # Google account fallback history: JSON list of
    # {google_account_id, email, outcome, reason} attempts.
    fallback_history: Optional[Union[List[Dict[str, Any]], str]] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_validator('fallback_history', mode='before')
    @classmethod
    def parse_fallback_history_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v

    class Config:
        from_attributes = True


class FlowBridgeTaskExecuteRequest(BaseModel):
    """Optional preferred Google account for execute/retry; when omitted
    the task's current account is tried first, then the user's other
    connected accounts in least-recently-used order."""
    google_account_id: Optional[str] = None


class FlowBridgeAssetBase(BaseModel):
    asset_type: FlowBridgeAssetType
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    
    # Optional associations
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None
    character_id: Optional[str] = None
    location_id: Optional[str] = None


class FlowBridgeAssetCreate(FlowBridgeAssetBase):
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    source: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None


class FlowBridgeAssetUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    source: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None


class FlowBridgeAssetResponse(FlowBridgeAssetBase):
    id: str
    task_id: str
    project_id: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    source: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True