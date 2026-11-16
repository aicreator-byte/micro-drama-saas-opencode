from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class AutomationTaskType(str, Enum):
    LOGIN_GOOGLE = "login_google"
    GENERATE_IMAGES = "generate_images"
    UPLOAD_ASSETS = "upload_assets"
    DOWNLOAD_ASSETS = "download_assets"
    CHECK_ACCOUNT_STATUS = "check_account_status"
    REFRESH_SESSION = "refresh_session"


class AIService(str, Enum):
    MIDJOURNEY = "midjourney"
    DALLE = "dalle"
    STABLE_DIFFUSION = "stable_diffusion"


class LoginAutomationRequest(BaseModel):
    google_account_id: str


class ImageGenerationRequest(BaseModel):
    google_account_id: str
    flow_task_id: str
    prompt: str
    service: AIService = AIService.MIDJOURNEY
    count: int = Field(default=4, ge=1, le=10)


class AccountCheckRequest(BaseModel):
    google_account_id: str


class SessionRefreshRequest(BaseModel):
    google_account_id: str


class AutomationTaskResponse(BaseModel):
    task_id: str
    task_type: AutomationTaskType
    google_account_id: str
    flow_task_id: Optional[str] = None
    project_id: str
    status: str
    current_step: int
    total_steps: int
    steps: Optional[list] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AutomationTaskListResponse(BaseModel):
    task_id: str
    task_type: AutomationTaskType
    google_account_id: str
    flow_task_id: Optional[str] = None
    status: str
    current_step: int
    total_steps: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None