from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.flow_bridge import FlowBridgeTask, FlowBridgeTaskStatus, FlowBridgeAsset, FlowBridgeAssetType
from app.models.audit_log import AuditAction
from app.schemas.flow_bridge import FlowBridgeTaskCreate, FlowBridgeTaskUpdate, FlowBridgeTaskResponse, FlowBridgeAssetCreate, FlowBridgeAssetResponse

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


# Task endpoints
@router.post("/{project_id}/tasks", response_model=FlowBridgeTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_flow_task(
    project_id: str,
    task_data: FlowBridgeTaskCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    # Verify episode/scene/shot belong to project
    if task_data.episode_id:
        from app.models.episode import Episode
        result = await db.execute(
            select(Episode).where(Episode.id == task_data.episode_id, Episode.project_id == project_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Episode not found in this project")
    
    if task_data.scene_id:
        from app.models.episode import Scene
        result = await db.execute(
            select(Scene).where(Scene.id == task_data.scene_id)
        )
        scene = result.scalar_one_or_none()
        if not scene or scene.episode_id != task_data.episode_id:
            raise HTTPException(status_code=400, detail="Scene not found in this episode")
    
    if task_data.shot_id:
        from app.models.episode import Shot
        result = await db.execute(
            select(Shot).where(Shot.id == task_data.shot_id)
        )
        shot = result.scalar_one_or_none()
        if not shot or shot.scene_id != task_data.scene_id:
            raise HTTPException(status_code=400, detail="Shot not found in this scene")
    
    if task_data.google_account_id:
        from app.models.google_account import GoogleAccount
        result = await db.execute(
            select(GoogleAccount).where(GoogleAccount.id == task_data.google_account_id, GoogleAccount.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Google account not found")
    
    task = FlowBridgeTask(
        project_id=project_id,
        episode_id=task_data.episode_id,
        scene_id=task_data.scene_id,
        shot_id=task_data.shot_id,
        google_account_id=task_data.google_account_id,
        title=task_data.title,
        description=task_data.description,
        task_type=task_data.task_type,
        input_prompts=str(task_data.input_prompts) if task_data.input_prompts else None,
        input_references=str(task_data.input_references) if task_data.input_references else None,
        input_parameters=str(task_data.input_parameters) if task_data.input_parameters else None,
        priority=task_data.priority
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_TASK_CREATE,
        resource_type="flow_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"title": task.title, "task_type": task.task_type}
    )
    await db.commit()
    
    return task


@router.get("/{project_id}/tasks", response_model=List[FlowBridgeTaskResponse])
async def list_flow_tasks(
    project_id: str,
    request: Request,
    status: Optional[FlowBridgeTaskStatus] = None,
    episode_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    query = select(FlowBridgeTask).where(FlowBridgeTask.project_id == project_id)
    
    if status:
        query = query.where(FlowBridgeTask.status == status)
    if episode_id:
        query = query.where(FlowBridgeTask.episode_id == episode_id)
    
    query = query.order_by(FlowBridgeTask.priority.desc(), FlowBridgeTask.created_at)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_TASK_CREATE,  # Using CREATE as generic read
        resource_type="flow_task", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return tasks


@router.get("/{project_id}/tasks/{task_id}", response_model=FlowBridgeTaskResponse)
async def get_flow_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == task_id, FlowBridgeTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow bridge task not found"
        )
    
    return task


@router.patch("/{project_id}/tasks/{task_id}", response_model=FlowBridgeTaskResponse)
async def update_flow_task(
    project_id: str,
    task_id: str,
    task_data: FlowBridgeTaskUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == task_id, FlowBridgeTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow bridge task not found"
        )
    
    old_values = {
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "status": task.status.value,
        "input_prompts": task.input_prompts,
        "input_references": task.input_references,
        "input_parameters": task.input_parameters,
        "output_assets": task.output_assets,
        "generation_log": task.generation_log,
        "error_message": task.error_message,
        "automation_data": task.automation_data,
        "manual_steps_completed": task.manual_steps_completed,
        "priority": task.priority,
        "google_account_id": task.google_account_id
    }
    
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["input_prompts", "input_references", "input_parameters", "output_assets", "generation_log", "automation_data", "manual_steps_completed"] and value is not None:
            value = str(value)
        setattr(task, field, value)
    
    # Auto-set timestamps
    from datetime import datetime
    if task_data.status == FlowBridgeTaskStatus.GENERATING and task.status != FlowBridgeTaskStatus.GENERATING:
        task.started_at = datetime.utcnow()
    elif task_data.status in [FlowBridgeTaskStatus.COMPLETED, FlowBridgeTaskStatus.FAILED] and task.status not in [FlowBridgeTaskStatus.COMPLETED, FlowBridgeTaskStatus.FAILED]:
        task.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    new_values = {
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "status": task.status.value,
        "input_prompts": task.input_prompts,
        "input_references": task.input_references,
        "input_parameters": task.input_parameters,
        "output_assets": task.output_assets,
        "generation_log": task.generation_log,
        "error_message": task.error_message,
        "automation_data": task.automation_data,
        "manual_steps_completed": task.manual_steps_completed,
        "priority": task.priority,
        "google_account_id": task.google_account_id
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_TASK_UPDATE,
        resource_type="flow_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return task


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == task_id, FlowBridgeTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow bridge task not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_TASK_CREATE,  # Using CREATE as generic delete
        resource_type="flow_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"title": task.title}
    )
    
    await db.delete(task)
    await db.commit()


# Asset endpoints
@router.post("/{project_id}/tasks/{task_id}/assets", response_model=FlowBridgeAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_flow_asset(
    project_id: str,
    task_id: str,
    asset_data: FlowBridgeAssetCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == task_id, FlowBridgeTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow bridge task not found"
        )
    
    asset = FlowBridgeAsset(
        task_id=task_id,
        project_id=project_id,
        asset_type=asset_data.asset_type,
        title=asset_data.title,
        description=asset_data.description,
        file_path=asset_data.file_path,
        file_url=asset_data.file_url,
        file_size=asset_data.file_size,
        mime_type=asset_data.mime_type,
        checksum=asset_data.checksum,
        source=asset_data.source,
        source_metadata=str(asset_data.source_metadata) if asset_data.source_metadata else None,
        episode_id=asset_data.episode_id,
        scene_id=asset_data.scene_id,
        shot_id=asset_data.shot_id,
        character_id=asset_data.character_id,
        location_id=asset_data.location_id
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_ASSET_UPLOAD,
        resource_type="flow_asset", resource_id=asset.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"asset_type": asset.asset_type.value, "title": asset.title}
    )
    await db.commit()
    
    return asset


@router.get("/{project_id}/tasks/{task_id}/assets", response_model=List[FlowBridgeAssetResponse])
async def list_flow_assets(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == task_id, FlowBridgeTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow bridge task not found"
        )
    
    result = await db.execute(
        select(FlowBridgeAsset).where(FlowBridgeAsset.task_id == task_id).order_by(FlowBridgeAsset.created_at)
    )
    assets = result.scalars().all()
    
    return assets


@router.get("/{project_id}/assets", response_model=List[FlowBridgeAssetResponse])
async def list_project_assets(
    project_id: str,
    request: Request,
    asset_type: Optional[FlowBridgeAssetType] = None,
    episode_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    query = select(FlowBridgeAsset).where(FlowBridgeAsset.project_id == project_id)
    
    if asset_type:
        query = query.where(FlowBridgeAsset.asset_type == asset_type)
    if episode_id:
        query = query.where(FlowBridgeAsset.episode_id == episode_id)
    
    query = query.order_by(FlowBridgeAsset.created_at.desc())
    result = await db.execute(query)
    assets = result.scalars().all()
    
    return assets