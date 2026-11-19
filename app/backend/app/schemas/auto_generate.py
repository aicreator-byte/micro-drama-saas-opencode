from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.auto_generate import (
    AutoGenerateJobStatus,
    AutoGenerateStepName,
    AutoGenerateStepStatus,
)


class AutoGenerateCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    genre: Optional[str] = Field(default=None, max_length=100)
    total_episodes: int = Field(default=30, ge=1, le=60)
    premise: Optional[str] = None


class AutoGenerateStepResponse(BaseModel):
    id: str
    job_id: str
    step: AutoGenerateStepName
    step_order: int
    status: AutoGenerateStepStatus
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AutoGenerateJobResponse(BaseModel):
    id: str
    project_id: str
    title: str
    genre: Optional[str] = None
    total_episodes: int
    premise: Optional[str] = None
    status: AutoGenerateJobStatus
    error_message: Optional[str] = None
    steps: List[AutoGenerateStepResponse] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
