from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AssetResponse(BaseModel):
    id: str
    project_id: str
    key: str
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    backend: str
    url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
