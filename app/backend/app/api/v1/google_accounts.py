from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.core.encryption import encryption_service
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.models.project import Project
from app.models.audit_log import AuditAction
from app.schemas.google_account import GoogleAccountCreate, GoogleAccountUpdate, GoogleAccountResponse, GoogleAccountConnectRequest, GoogleAccountSessionUpdate

router = APIRouter()


@router.post("", response_model=GoogleAccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_google_account(
    account_data: GoogleAccountConnectRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check account limit (max 20 per user)
    count_result = await db.execute(
        select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == current_user.id)
    )
    count = count_result.scalar()
    if count >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 20 Google accounts allowed per user"
        )
    
    # Check if email already connected
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.user_id == current_user.id, GoogleAccount.email == account_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Google account is already connected"
        )
    
    # Encrypt session data
    encrypted_session = encryption_service.encrypt(account_data.session_data)
    
    account = GoogleAccount(
        user_id=current_user.id,
        email=account_data.email,
        encrypted_session_data=encrypted_session,
        session_expires_at=account_data.expires_at,
        status=GoogleAccountStatus.CONNECTED,
        connected_at=__import__('datetime').datetime.utcnow()
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_CONNECT,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"email": account.email}
    )
    await db.commit()
    
    return account


@router.get("", response_model=List[GoogleAccountResponse])
async def list_google_accounts(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.user_id == current_user.id).order_by(GoogleAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_VERIFY,
        resource_type="google_account", resource_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return accounts


@router.get("/{account_id}", response_model=GoogleAccountResponse)
async def get_google_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    return account


@router.patch("/{account_id}", response_model=GoogleAccountResponse)
async def update_google_account(
    account_id: str,
    account_data: GoogleAccountUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    old_values = {
        "display_name": account.display_name,
        "profile_picture": account.profile_picture,
        "status": account.status.value,
        "encrypted_session_data": "***" if account.encrypted_session_data else None,
        "session_expires_at": account.session_expires_at.isoformat() if account.session_expires_at else None
    }
    
    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "encrypted_session_data" and value:
            value = encryption_service.encrypt(value)
        setattr(account, field, value)
    
    # If status changed to disconnected, record disconnected_at
    if account_data.status == GoogleAccountStatus.DISCONNECTED and account.status != GoogleAccountStatus.DISCONNECTED:
        from datetime import datetime
        account.disconnected_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(account)
    
    new_values = {
        "display_name": account.display_name,
        "profile_picture": account.profile_picture,
        "status": account.status.value,
        "encrypted_session_data": "***" if account.encrypted_session_data else None,
        "session_expires_at": account.session_expires_at.isoformat() if account.session_expires_at else None
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_UPDATE,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    # Check if account is assigned to any projects
    project_result = await db.execute(
        select(Project).where(Project.google_account_id == account_id)
    )
    if project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect account assigned to projects. Reassign projects first."
        )
    
    from datetime import datetime
    account.status = GoogleAccountStatus.DISCONNECTED
    account.disconnected_at = datetime.utcnow()
    account.encrypted_session_data = None
    
    await db.commit()
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_DISCONNECT,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"email": account.email}
    )
    await db.commit()


@router.post("/{account_id}/verify", response_model=GoogleAccountResponse)
async def verify_google_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    # TODO: Implement actual session verification with Google
    # For now, just update last_verified_at
    from datetime import datetime
    account.last_verified_at = datetime.utcnow()
    account.status = GoogleAccountStatus.CONNECTED
    account.error_message = None
    
    await db.commit()
    await db.refresh(account)
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_VERIFY,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"last_verified_at": account.last_verified_at.isoformat()}
    )
    await db.commit()
    
    return account