from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.models.audit_log import AuditAction
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse

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


def prompt_to_response(prompt: Prompt) -> PromptResponse:
    """Convert Prompt model to PromptResponse with parsed parameters."""
    return PromptResponse(
        id=prompt.id,
        project_id=prompt.project_id,
        episode_id=prompt.episode_id,
        scene_id=prompt.scene_id,
        shot_id=prompt.shot_id,
        character_id=prompt.character_id,
        location_id=prompt.location_id,
        prompt_type=prompt.prompt_type,
        title=prompt.title,
        prompt_text=prompt.prompt_text,
        negative_prompt=prompt.negative_prompt,
        parameters=prompt.parameters_dict,
        status=prompt.status,
        version=prompt.version,
        parent_prompt_id=prompt.parent_prompt_id,
        times_used=prompt.times_used,
        last_used_at=prompt.last_used_at,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        created_by=prompt.created_by
    )


@router.post("/{project_id}/prompts", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    project_id: str,
    prompt_data: PromptCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    import json
    prompt = Prompt(
        project_id=project_id,
        episode_id=prompt_data.episode_id,
        scene_id=prompt_data.scene_id,
        shot_id=prompt_data.shot_id,
        character_id=prompt_data.character_id,
        location_id=prompt_data.location_id,
        prompt_type=prompt_data.prompt_type,
        title=prompt_data.title,
        prompt_text=prompt_data.prompt_text,
        negative_prompt=prompt_data.negative_prompt,
        parameters=json.dumps(prompt_data.parameters) if prompt_data.parameters else None,
        created_by=current_user.id
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_CREATE,
        resource_type="prompt", resource_id=prompt.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"prompt_type": prompt.prompt_type.value, "title": prompt.title}
    )
    await db.commit()
    
    return prompt_to_response(prompt)


@router.get("/{project_id}/prompts", response_model=List[PromptResponse])
async def list_prompts(
    project_id: str,
    request: Request,
    prompt_type: Optional[PromptType] = None,
    episode_id: Optional[str] = None,
    scene_id: Optional[str] = None,
    shot_id: Optional[str] = None,
    character_id: Optional[str] = None,
    location_id: Optional[str] = None,
    status: Optional[PromptStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    query = select(Prompt).where(Prompt.project_id == project_id)
    
    if prompt_type:
        query = query.where(Prompt.prompt_type == prompt_type)
    if episode_id:
        query = query.where(Prompt.episode_id == episode_id)
    if scene_id:
        query = query.where(Prompt.scene_id == scene_id)
    if shot_id:
        query = query.where(Prompt.shot_id == shot_id)
    if character_id:
        query = query.where(Prompt.character_id == character_id)
    if location_id:
        query = query.where(Prompt.location_id == location_id)
    if status:
        query = query.where(Prompt.status == status)
    
    query = query.order_by(Prompt.created_at.desc())
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_READ,
        resource_type="prompt", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return [prompt_to_response(p) for p in prompts]


@router.get("/{project_id}/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    project_id: str,
    prompt_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.project_id == project_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_READ,
        resource_type="prompt", resource_id=prompt.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return prompt_to_response(prompt)


@router.patch("/{project_id}/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    project_id: str,
    prompt_id: str,
    prompt_data: PromptUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.project_id == project_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    old_values = {
        "title": prompt.title,
        "prompt_text": prompt.prompt_text,
        "negative_prompt": prompt.negative_prompt,
        "parameters": prompt.parameters,
        "status": prompt.status.value,
        "version": prompt.version
    }
    
    update_data = prompt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "parameters" and value is not None:
            value = json.dumps(value)
        setattr(prompt, field, value)
    
    # Increment version if prompt_text changed
    if "prompt_text" in update_data:
        prompt.version += 1
    
    await db.commit()
    await db.refresh(prompt)
    
    new_values = {
        "title": prompt.title,
        "prompt_text": prompt.prompt_text,
        "negative_prompt": prompt.negative_prompt,
        "parameters": prompt.parameters,
        "status": prompt.status.value,
        "version": prompt.version
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_UPDATE,
        resource_type="prompt", resource_id=prompt.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return prompt_to_response(prompt)


@router.delete("/{project_id}/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    project_id: str,
    prompt_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.project_id == project_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_DELETE,
        resource_type="prompt", resource_id=prompt.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"prompt_type": prompt.prompt_type.value, "title": prompt.title}
    )
    
    await db.delete(prompt)
    await db.commit()


@router.post("/{project_id}/prompts/{prompt_id}/use", response_model=PromptResponse)
async def use_prompt(
    project_id: str,
    prompt_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.project_id == project_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    from datetime import datetime, timezone
    prompt.times_used += 1
    prompt.last_used_at = datetime.now(timezone.utc)
    prompt.status = PromptStatus.USED
    
    await db.commit()
    await db.refresh(prompt)
    
    create_audit_log(
        db, current_user.id, AuditAction.PROMPT_EXPORT,
        resource_type="prompt", resource_id=prompt.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"times_used": prompt.times_used}
    )
    await db.commit()
    
    return prompt_to_response(prompt)