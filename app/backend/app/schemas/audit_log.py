from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime
from app.models.audit_log import AuditAction
import json


class AuditLogBase(BaseModel):
    action: AuditAction
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    old_values: Optional[Union[Dict[str, Any], str]] = None
    new_values: Optional[Union[Dict[str, Any], str]] = None
    success: bool = True
    error_message: Optional[str] = None

    @field_validator('old_values', 'new_values', mode='before')
    @classmethod
    def parse_json_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: str
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True