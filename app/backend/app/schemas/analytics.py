from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LlmUsageEventResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str] = None
    job_id: Optional[str] = None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CostByModelEntry(BaseModel):
    model: str
    events: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Optional[float] = None


class CostByJobEntry(BaseModel):
    job_id: Optional[str] = None
    events: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Optional[float] = None


class AnalyticsSummaryResponse(BaseModel):
    project_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: Optional[float] = None
    cost_by_model: List[CostByModelEntry] = []
    cost_by_job: List[CostByJobEntry] = []


class UsageListResponse(BaseModel):
    items: List[LlmUsageEventResponse] = []
    total: int
    limit: int
    offset: int
