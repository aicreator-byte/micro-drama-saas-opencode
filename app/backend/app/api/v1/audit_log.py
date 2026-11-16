from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.audit_log import AuditLogResponse
from app.api.deps import get_current_active_user, get_current_superuser

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    success: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_superuser),  # Only superusers can view audit logs
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).where(AuditLog.user_id == current_user.id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if success is not None:
        query = query.where(AuditLog.success == (1 if success else 0))
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    return logs


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_id, AuditLog.user_id == current_user.id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log