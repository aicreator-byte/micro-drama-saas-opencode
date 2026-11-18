from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.models.flow_bridge import FlowBridgeTask, FlowBridgeTaskStatus, FlowBridgeAsset, FlowBridgeAssetType
from app.models.audit_log import AuditAction
from app.services.flow_bridge_automation import (
    BrowserAutomationService, AutomationTaskType, AutomationStatus,
    get_automation_service
)

router = APIRouter()


def _require_real_automation(automation: BrowserAutomationService):
    """Fail closed while browser automation is mock-only (audit F-02).

    The automation service ships with mock_mode=True and no real Playwright
    run path; its fake results must never touch production data. All
    mutating automation endpoints return 503 until real automation is
    enabled via env (FLOW_AUTOMATION_ENABLED=1 + Playwright available).
    """
    if automation.mock_mode:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Browser automation is unavailable (mock mode): real Playwright automation is not enabled"
        )
from app.schemas.flow_bridge_automation import (
    LoginAutomationRequest, ImageGenerationRequest, AccountCheckRequest,
    SessionRefreshRequest, AutomationTaskResponse, AutomationTaskListResponse,
    AIService
)

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


async def get_google_account_or_404(account_id: str, user_id: str, db: AsyncSession) -> GoogleAccount:
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    return account


@router.post("/{project_id}/flow-bridge/automation/login", response_model=AutomationTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_login_automation(
    project_id: str,
    login_data: LoginAutomationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """Create and execute Google login automation."""
    project = await get_project_or_404(project_id, current_user.id, db)
    google_account = await get_google_account_or_404(login_data.google_account_id, current_user.id, db)
    _require_real_automation(automation)

    # Real-mode login goes through BrowserFlowService: per-account
    # persistent browser profile, password decrypted from the existing
    # encrypted column (never a literal placeholder — audit: the old
    # code passed "***", which real Playwright would have typed into
    # Google's login form). No Cloud Console credentials involved.
    # The AutomationTask below is only the record for the response;
    # the session lives in the account's browser profile on disk, NOT
    # in encrypted_session_data (the old code stored raw cookies there
    # unencrypted).
    from app.services.browser_flow import (
        BrowserUnavailable, FlowDomError, get_browser_flow_service)
    from app.services.google_account_fallback import GoogleAccountFailure

    task = automation.create_task(
        task_type=AutomationTaskType.LOGIN_GOOGLE,
        google_account_id=login_data.google_account_id,
        project_id=project_id,
        parameters={"email": google_account.email},
    )
    browser_flow = get_browser_flow_service()
    try:
        login_result = await browser_flow.login_account(db, google_account)
    except BrowserUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Browser automation is unavailable: {e}")
    except FlowDomError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Browser automation could not reach Google: {e}")
    except GoogleAccountFailure as e:
        task.status = AutomationStatus.FAILED
        task.error_message = e.reason
        task.completed_at = datetime.now(timezone.utc)
        result_task = task
    else:
        task.status = AutomationStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.result_data = login_result.as_dict()
        for step in task.steps:
            step.completed = True
        task.current_step = len(task.steps)
        result_task = task
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_VERIFY,
        resource_type="google_account", resource_id=login_data.google_account_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"automation_task_id": task.task_id, "status": result_task.status.value}
    )
    await db.commit()
    
    return AutomationTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        google_account_id=task.google_account_id,
        project_id=task.project_id,
        status=result_task.status.value,
        current_step=task.current_step,
        total_steps=len(task.steps),
        steps=[
            {
                "step_id": s.step_id,
                "action": s.action,
                "selector": s.selector,
                "description": s.description,
                "completed": s.completed,
                "result": s.result,
                "error": s.error
            }
            for s in task.steps
        ],
        result=result_task.result_data,
        error=result_task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@router.post("/{project_id}/flow-bridge/automation/generate-images", response_model=AutomationTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_image_generation_automation(
    project_id: str,
    gen_data: ImageGenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """Create and execute AI image generation automation."""
    project = await get_project_or_404(project_id, current_user.id, db)
    google_account = await get_google_account_or_404(gen_data.google_account_id, current_user.id, db)
    _require_real_automation(automation)
    
    ft_result = await db.execute(
        select(FlowBridgeTask).where(FlowBridgeTask.id == gen_data.flow_task_id, FlowBridgeTask.project_id == project_id)
    )
    flow_task = ft_result.scalar_one_or_none()
    if not flow_task:
        raise HTTPException(status_code=404, detail="Flow bridge task not found")
    
    parameters = {
        "service": gen_data.service.value,
        "prompt": gen_data.prompt,
        "count": gen_data.count,
        "session_data": google_account.encrypted_session_data
    }
    
    task = automation.create_task(
        task_type=AutomationTaskType.GENERATE_IMAGES,
        google_account_id=gen_data.google_account_id,
        project_id=project_id,
        flow_task_id=gen_data.flow_task_id,
        parameters=parameters
    )
    
    try:
        result_task = await automation.execute_task(task.task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation failed: {str(e)}")
    
    if result_task.status == AutomationStatus.COMPLETED and result_task.result_data and not automation.mock_mode:
        image_urls = result_task.result_data.get("image_urls", [])
        flow_task.output_assets = str(image_urls)
        flow_task.status = FlowBridgeTaskStatus.COMPLETED
        flow_task.completed_at = datetime.now(timezone.utc)
        
        for i, url in enumerate(image_urls):
            asset = FlowBridgeAsset(
                task_id=gen_data.flow_task_id,
                project_id=project_id,
                asset_type=FlowBridgeAssetType.CHARACTER_IMAGE,
                title=f"Generated Image {i+1}",
                file_url=url,
                source=f"ai_generation_{gen_data.service.value}",
                episode_id=flow_task.episode_id,
                scene_id=flow_task.scene_id
            )
            db.add(asset)
        
        await db.commit()
    
    create_audit_log(
        db, current_user.id, AuditAction.FLOW_TASK_EXECUTE,
        resource_type="flow_task", resource_id=gen_data.flow_task_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"automation_task_id": task.task_id, "status": result_task.status.value, "images_generated": len(result_task.result_data.get("image_urls", [])) if result_task.result_data else 0}
    )
    await db.commit()
    
    return AutomationTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        google_account_id=task.google_account_id,
        flow_task_id=task.flow_task_id,
        project_id=task.project_id,
        status=result_task.status.value,
        current_step=task.current_step,
        total_steps=len(task.steps),
        steps=[
            {
                "step_id": s.step_id,
                "action": s.action,
                "selector": s.selector,
                "description": s.description,
                "completed": s.completed,
                "result": s.result,
                "error": s.error
            }
            for s in task.steps
        ],
        result=result_task.result_data,
        error=result_task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@router.post("/{project_id}/flow-bridge/automation/check-account", response_model=AutomationTaskResponse, status_code=status.HTTP_201_CREATED)
async def check_google_account_status(
    project_id: str,
    check_data: AccountCheckRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """Check Google account login status via automation."""
    project = await get_project_or_404(project_id, current_user.id, db)
    google_account = await get_google_account_or_404(check_data.google_account_id, current_user.id, db)
    _require_real_automation(automation)
    
    parameters = {"session_data": google_account.encrypted_session_data}
    
    task = automation.create_task(
        task_type=AutomationTaskType.CHECK_ACCOUNT_STATUS,
        google_account_id=check_data.google_account_id,
        project_id=project_id,
        parameters=parameters
    )
    
    try:
        result_task = await automation.execute_task(task.task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation failed: {str(e)}")
    
    if result_task.status == AutomationStatus.COMPLETED and result_task.result_data and not automation.mock_mode:
        is_logged_in = result_task.result_data.get("loggedIn", False)
        google_account.status = GoogleAccountStatus.CONNECTED if is_logged_in else GoogleAccountStatus.ERROR
        google_account.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_VERIFY,
        resource_type="google_account", resource_id=check_data.google_account_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"automation_task_id": task.task_id, "status": result_task.status.value, "logged_in": result_task.result_data.get("loggedIn") if result_task.result_data else False}
    )
    await db.commit()
    
    return AutomationTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        google_account_id=task.google_account_id,
        project_id=task.project_id,
        status=result_task.status.value,
        current_step=task.current_step,
        total_steps=len(task.steps),
        steps=[
            {
                "step_id": s.step_id,
                "action": s.action,
                "selector": s.selector,
                "description": s.description,
                "completed": s.completed,
                "result": s.result,
                "error": s.error
            }
            for s in task.steps
        ],
        result=result_task.result_data,
        error=result_task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@router.post("/{project_id}/flow-bridge/automation/refresh-session", response_model=AutomationTaskResponse, status_code=status.HTTP_201_CREATED)
async def refresh_google_account_session(
    project_id: str,
    refresh_data: SessionRefreshRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """Refresh Google account session via automation."""
    project = await get_project_or_404(project_id, current_user.id, db)
    google_account = await get_google_account_or_404(refresh_data.google_account_id, current_user.id, db)
    _require_real_automation(automation)
    
    parameters = {"session_data": google_account.encrypted_session_data}
    
    task = automation.create_task(
        task_type=AutomationTaskType.REFRESH_SESSION,
        google_account_id=refresh_data.google_account_id,
        project_id=project_id,
        parameters=parameters
    )
    
    try:
        result_task = await automation.execute_task(task.task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation failed: {str(e)}")
    
    if result_task.status == AutomationStatus.COMPLETED and result_task.result_data and not automation.mock_mode:
        session_data = result_task.result_data
        if isinstance(session_data, dict):
            import json
            session_data = json.dumps(session_data)
        google_account.encrypted_session_data = session_data
        google_account.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_UPDATE,
        resource_type="google_account", resource_id=refresh_data.google_account_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"automation_task_id": task.task_id, "status": result_task.status.value}
    )
    await db.commit()
    
    return AutomationTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        google_account_id=task.google_account_id,
        project_id=task.project_id,
        status=result_task.status.value,
        current_step=task.current_step,
        total_steps=len(task.steps),
        steps=[
            {
                "step_id": s.step_id,
                "action": s.action,
                "selector": s.selector,
                "description": s.description,
                "completed": s.completed,
                "result": s.result,
                "error": s.error
            }
            for s in task.steps
        ],
        result=result_task.result_data,
        error=result_task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@router.get("/{project_id}/flow-bridge/automation/tasks", response_model=List[AutomationTaskListResponse])
async def list_automation_tasks(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """List all automation tasks for a project."""
    project = await get_project_or_404(project_id, current_user.id, db)
    
    tasks = automation.list_tasks(project_id)
    
    return [
        AutomationTaskListResponse(
            task_id=t.task_id,
            task_type=t.task_type,
            google_account_id=t.google_account_id,
            flow_task_id=t.flow_task_id,
            status=t.status.value,
            current_step=t.current_step,
            total_steps=len(t.steps),
            result=t.result_data,
            error=t.error_message,
            created_at=t.created_at.isoformat(),
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None
        )
        for t in tasks
    ]


@router.get("/{project_id}/flow-bridge/automation/tasks/{task_id}", response_model=AutomationTaskResponse)
async def get_automation_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    automation: BrowserAutomationService = Depends(get_automation_service)
):
    """Get automation task details."""
    project = await get_project_or_404(project_id, current_user.id, db)
    
    task = automation.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Automation task not found")
    
    return AutomationTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        google_account_id=task.google_account_id,
        flow_task_id=task.flow_task_id,
        project_id=task.project_id,
        status=task.status.value,
        current_step=task.current_step,
        total_steps=len(task.steps),
        steps=[
            {
                "step_id": s.step_id,
                "action": s.action,
                "selector": s.selector,
                "description": s.description,
                "completed": s.completed,
                "result": s.result,
                "error": s.error
            }
            for s in task.steps
        ],
        result=task.result_data,
        error=task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )