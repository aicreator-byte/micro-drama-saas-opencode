from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.location import Location
from app.models.audit_log import AuditAction
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse

router = APIRouter()


async def get_project_or_404(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.post("/{project_id}/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    project_id: str,
    location_data: LocationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    location = Location(
        project_id=project_id,
        name=location_data.name,
        type=location_data.type,
        order_index=location_data.order_index,
        description=location_data.description,
        environment_details=str(location_data.environment_details) if location_data.environment_details else None,
        reference_images=str(location_data.reference_images) if location_data.reference_images else None,
        visual_style_notes=location_data.visual_style_notes,
        lighting=str(location_data.lighting) if location_data.lighting else None,
        atmosphere=location_data.atmosphere,
        time_of_day=location_data.time_of_day,
        weather=location_data.weather,
        consistency_instructions=location_data.consistency_instructions
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    create_audit_log(
        db, current_user.id, AuditAction.LOCATION_CREATE,
        resource_type="location", resource_id=location.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"name": location.name, "type": location.type, "project_id": project_id}
    )
    await db.commit()
    
    return location


@router.get("/{project_id}/locations", response_model=list[LocationResponse])
async def list_locations(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Location).where(Location.project_id == project_id).order_by(Location.order_index, Location.created_at)
    )
    locations = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.LOCATION_READ,
        resource_type="location", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return locations


@router.get("/{project_id}/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    project_id: str,
    location_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.project_id == project_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.LOCATION_READ,
        resource_type="location", resource_id=location.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return location


@router.patch("/{project_id}/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    project_id: str,
    location_id: str,
    location_data: LocationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.project_id == project_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    old_values = {
        "name": location.name,
        "type": location.type,
        "order_index": location.order_index,
        "description": location.description,
        "environment_details": location.environment_details,
        "reference_images": location.reference_images,
        "visual_style_notes": location.visual_style_notes,
        "lighting": location.lighting,
        "atmosphere": location.atmosphere,
        "time_of_day": location.time_of_day,
        "weather": location.weather,
        "consistency_instructions": location.consistency_instructions
    }
    
    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["environment_details", "reference_images", "lighting"] and value is not None:
            value = str(value)
        setattr(location, field, value)
    
    await db.commit()
    await db.refresh(location)
    
    new_values = {
        "name": location.name,
        "type": location.type,
        "order_index": location.order_index,
        "description": location.description,
        "environment_details": location.environment_details,
        "reference_images": location.reference_images,
        "visual_style_notes": location.visual_style_notes,
        "lighting": location.lighting,
        "atmosphere": location.atmosphere,
        "time_of_day": location.time_of_day,
        "weather": location.weather,
        "consistency_instructions": location.consistency_instructions
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.LOCATION_UPDATE,
        resource_type="location", resource_id=location.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return location


@router.delete("/{project_id}/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    project_id: str,
    location_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.project_id == project_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.LOCATION_DELETE,
        resource_type="location", resource_id=location.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"name": location.name, "type": location.type, "project_id": project_id}
    )
    
    await db.delete(location)
    await db.commit()