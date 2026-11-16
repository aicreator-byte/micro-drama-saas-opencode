from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: Optional[str] = Field(None, max_length=100)
    order_index: int = Field(default=0, ge=0)
    
    # Environment description
    description: Optional[str] = None
    environment_details: Optional[Dict[str, Any]] = None
    
    # Visual references
    reference_images: Optional[List[str]] = None
    visual_style_notes: Optional[str] = None
    
    # Lighting and atmosphere
    lighting: Optional[Dict[str, Any]] = None
    atmosphere: Optional[str] = None
    time_of_day: Optional[str] = Field(None, max_length=50)
    weather: Optional[str] = Field(None, max_length=100)
    
    # Consistency
    consistency_instructions: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field(None, max_length=100)
    order_index: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    environment_details: Optional[Dict[str, Any]] = None
    reference_images: Optional[List[str]] = None
    visual_style_notes: Optional[str] = None
    lighting: Optional[Dict[str, Any]] = None
    atmosphere: Optional[str] = None
    time_of_day: Optional[str] = Field(None, max_length=50)
    weather: Optional[str] = Field(None, max_length=100)
    consistency_instructions: Optional[str] = None


class LocationResponse(LocationBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True