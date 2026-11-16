from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExportFormat(str, Enum):
    JSON = "json"
    TXT = "txt"
    CSV = "csv"
    PDF = "pdf"
    MARKDOWN = "markdown"


class ExportType(str, Enum):
    PROJECT = "project"
    EPISODE = "episode"
    PROMPTS = "prompts"
    SERIES_BIBLE = "series_bible"
    CHARACTERS = "characters"
    LOCATIONS = "locations"
    SCENES = "scenes"
    FULL_PROJECT = "full_project"


class ExportRequest(BaseModel):
    export_type: ExportType
    format: ExportFormat = ExportFormat.JSON
    project_id: Optional[str] = None
    episode_id: Optional[str] = None
    include_related: bool = True


class ExportResponse(BaseModel):
    export_id: str
    project_id: str
    export_type: ExportType
    format: ExportFormat
    status: str  # pending, processing, completed, failed
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ProjectExportData(BaseModel):
    project: Dict[str, Any]
    series_bible: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    locations: List[Dict[str, Any]] = []
    episodes: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    exported_at: datetime


class EpisodeExportData(BaseModel):
    episode: Dict[str, Any]
    scenes: List[Dict[str, Any]] = []
    shots: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    exported_at: datetime


class PromptsExportData(BaseModel):
    prompts: List[Dict[str, Any]] = []
    exported_at: datetime