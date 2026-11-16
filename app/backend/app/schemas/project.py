from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.project import ProjectStatus
import json


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    themes: Optional[List[str]] = None
    total_episodes: int = Field(default=20, ge=1, le=100)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    themes: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None
    total_episodes: Optional[int] = Field(None, ge=1, le=100)
    google_account_id: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    owner_id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    google_account_id: Optional[str] = None
    
    @field_validator('themes', mode='before')
    @classmethod
    def parse_themes(cls, v):
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


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int