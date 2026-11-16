from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.models.audit_log import AuditAction
from app.schemas.series_bible import SeriesBibleCreate, SeriesBibleUpdate, SeriesBibleResponse

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


@router.post("/{project_id}/series-bible", response_model=SeriesBibleResponse, status_code=status.HTTP_201_CREATED)
async def create_series_bible(
    project_id: str,
    bible_data: SeriesBibleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    # Check if series bible already exists
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.project_id == project_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Series bible already exists for this project"
        )
    
    bible = SeriesBible(
        project_id=project_id,
        premise=bible_data.premise,
        main_plot=bible_data.main_plot,
        subplots=json.dumps(bible_data.subplots) if bible_data.subplots else None,
        character_relationships=bible_data.character_relationships,
        world_settings=bible_data.world_settings,
        tone_and_visual_style=bible_data.tone_and_visual_style,
        ending_direction=bible_data.ending_direction,
        episode_structure=bible_data.episode_structure
    )
    db.add(bible)
    await db.commit()
    await db.refresh(bible)
    
    create_audit_log(
        db, current_user.id, AuditAction.SERIES_BIBLE_CREATE,
        resource_type="series_bible", resource_id=bible.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"project_id": project_id}
    )
    await db.commit()
    
    return bible


@router.get("/{project_id}/series-bible", response_model=SeriesBibleResponse)
async def get_series_bible(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.project_id == project_id)
    )
    bible = result.scalar_one_or_none()
    
    if not bible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series bible not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SERIES_BIBLE_READ,
        resource_type="series_bible", resource_id=bible.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return bible


@router.patch("/{project_id}/series-bible", response_model=SeriesBibleResponse)
async def update_series_bible(
    project_id: str,
    bible_data: SeriesBibleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.project_id == project_id)
    )
    bible = result.scalar_one_or_none()
    
    if not bible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series bible not found"
        )
    
    old_values = {
        "premise": bible.premise,
        "main_plot": bible.main_plot,
        "subplots": bible.subplots,
        "character_relationships": bible.character_relationships,
        "world_settings": bible.world_settings,
        "tone_and_visual_style": bible.tone_and_visual_style,
        "ending_direction": bible.ending_direction,
        "episode_structure": bible.episode_structure
    }
    
    update_data = bible_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "subplots" and value is not None:
            value = json.dumps(value)
        setattr(bible, field, value)
    
    await db.commit()
    await db.refresh(bible)
    
    new_values = {
        "premise": bible.premise,
        "main_plot": bible.main_plot,
        "subplots": bible.subplots,
        "character_relationships": bible.character_relationships,
        "world_settings": bible.world_settings,
        "tone_and_visual_style": bible.tone_and_visual_style,
        "ending_direction": bible.ending_direction,
        "episode_structure": bible.episode_structure
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.SERIES_BIBLE_UPDATE,
        resource_type="series_bible", resource_id=bible.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return bible


@router.delete("/{project_id}/series-bible", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series_bible(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.project_id == project_id)
    )
    bible = result.scalar_one_or_none()
    
    if not bible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series bible not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SERIES_BIBLE_DELETE,
        resource_type="series_bible", resource_id=bible.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"project_id": project_id}
    )
    
    await db.delete(bible)
    await db.commit()