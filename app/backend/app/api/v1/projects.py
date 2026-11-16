from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from uuid import UUID
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.audit_log import AuditAction
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        owner_id=current_user.id,
        title=project_data.title,
        description=project_data.description,
        genre=project_data.genre,
        themes=json.dumps(project_data.themes) if project_data.themes else None,
        total_episodes=project_data.total_episodes
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    create_audit_log(
        db, current_user.id, AuditAction.PROJECT_CREATE,
        resource_type="project", resource_id=project.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"title": project.title, "genre": project.genre}
    )
    await db.commit()
    
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Project).where(Project.owner_id == current_user.id)
    
    if status:
        query = query.where(Project.status == status)
    
    if search:
        query = query.where(
            or_(
                Project.title.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
                Project.genre.ilike(f"%{search}%")
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        projects=projects,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.PROJECT_READ,
        resource_type="project", resource_id=project.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    old_values = {
        "title": project.title,
        "description": project.description,
        "genre": project.genre,
        "themes": project.themes,
        "status": project.status.value,
        "total_episodes": project.total_episodes,
        "google_account_id": project.google_account_id
    }
    
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "themes" and value is not None:
            value = json.dumps(value)
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    new_values = {
        "title": project.title,
        "description": project.description,
        "genre": project.genre,
        "themes": project.themes,
        "status": project.status.value,
        "total_episodes": project.total_episodes,
        "google_account_id": project.google_account_id
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.PROJECT_UPDATE,
        resource_type="project", resource_id=project.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.PROJECT_DELETE,
        resource_type="project", resource_id=project.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"title": project.title}
    )
    
    await db.delete(project)
    await db.commit()