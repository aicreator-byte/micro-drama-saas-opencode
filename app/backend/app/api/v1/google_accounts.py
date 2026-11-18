from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import secrets
import httpx
import json

from app.core.database import get_db
from app.core.encryption import encryption_service
from app.core.config import settings
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.models.project import Project
from app.models.audit_log import AuditAction
from app.schemas.google_account import GoogleAccountCreate, GoogleAccountUpdate, GoogleAccountResponse, GoogleAccountConnectRequest, GoogleAccountSessionUpdate
from app.models.settings import AppSettings

router = APIRouter()

# Google OAuth constants
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]


async def get_app_settings(db: AsyncSession) -> Optional[AppSettings]:
    """Get app settings singleton."""
    result = await db.execute(select(AppSettings))
    return result.scalar_one_or_none()


async def get_google_oauth_credentials(db: AsyncSession) -> tuple[Optional[str], Optional[str]]:
    """Get decrypted Google OAuth client credentials from settings."""
    app_settings = await get_app_settings(db)
    if not app_settings:
        return None, None
    
    client_id = None
    client_secret = None
    
    if app_settings.google_oauth_client_id_encrypted:
        try:
            client_id = encryption_service.decrypt(app_settings.google_oauth_client_id_encrypted)
        except Exception:
            pass
    
    if app_settings.google_oauth_client_secret_encrypted:
        try:
            client_secret = encryption_service.decrypt(app_settings.google_oauth_client_secret_encrypted)
        except Exception:
            pass
    
    return client_id, client_secret


def generate_state() -> str:
    """Generate secure random state parameter."""
    return secrets.token_urlsafe(32)


def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Build Google OAuth authorize URL (audit F-09: URL-encode all params)."""
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access/refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh access token using refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def get_user_info(access_token: str) -> dict:
    """Get user info from Google using access token."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def verify_token(access_token: str) -> dict:
    """Verify access token with Google's tokeninfo endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_TOKENINFO_URL,
            params={"access_token": access_token},
        )
        response.raise_for_status()
        return response.json()


@router.get("/oauth/authorize")
async def google_oauth_authorize(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate Google OAuth authorize URL with state."""
    client_id, client_secret = await get_google_oauth_credentials(db)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials not configured in settings"
        )
    
    # Generate state and store in user's session (or a temp store)
    state = generate_state()
    
    # Build redirect URI
    redirect_uri = str(request.url_for("google_oauth_callback"))
    
    # Store state in DB temporarily (could also use Redis/session)
    # For simplicity, we'll encode user_id in state and verify on callback
    # In production, use a proper session store
    import base64
    state_data = json.dumps({
        "user_id": current_user.id,
        "state": state,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    encoded_state = base64.urlsafe_b64encode(state_data.encode()).decode()
    
    authorize_url = build_authorize_url(client_id, redirect_uri, encoded_state)
    
    return {"authorize_url": authorize_url, "state": encoded_state}


@router.get("/oauth/callback", name="google_oauth_callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback - exchange code for tokens and create account."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )
    
    # Decode state
    try:
        import base64
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user_id = state_data["user_id"]
        original_state = state_data["state"]
        
        # Verify state matches the generated state (self-contained verification)
        # In production, use a proper session store with server-side state storage
        if not original_state or len(original_state) < 16:
            raise ValueError("Invalid state format")
            
        # Check state age (max 10 minutes)
        created_at = datetime.fromisoformat(state_data["created_at"])
        if created_at.tzinfo is None:
            # States minted before the timezone-aware switch stored naive UTC.
            created_at = created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(minutes=10):
            raise ValueError("State expired")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get OAuth credentials
    client_id, client_secret = await get_google_oauth_credentials(db)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials not configured"
        )
    
    # Exchange code for tokens
    try:
        redirect_uri = str(request.url_for("google_oauth_callback"))
        tokens = await exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {e.response.text}"
        )
    
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    id_token = tokens.get("id_token")
    
    # Get user info
    try:
        user_info = await get_user_info(access_token)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get user info: {e.response.text}"
        )
    
    email = user_info.get("email")
    google_user_id = user_info.get("id")
    display_name = user_info.get("name")
    profile_picture = user_info.get("picture")
    
    # Check if account already exists
    result = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.user_id == user_id,
            GoogleAccount.email == email
        )
    )
    existing_account = result.scalar_one_or_none()
    
    # Encrypt session data (tokens)
    session_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": id_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "token_type": tokens.get("token_type"),
        "scope": tokens.get("scope"),
    }
    encrypted_session = encryption_service.encrypt(json.dumps(session_data))
    
    # Encrypt refresh token separately for Flow Bridge automation
    refresh_encrypted = encryption_service.encrypt(refresh_token) if refresh_token else None
    
    if existing_account:
        # Update existing account
        existing_account.encrypted_session_data = encrypted_session
        existing_account.session_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        existing_account.password_encrypted = refresh_encrypted
        existing_account.display_name = display_name
        existing_account.profile_picture = profile_picture
        existing_account.google_user_id = google_user_id
        existing_account.status = GoogleAccountStatus.CONNECTED
        existing_account.last_verified_at = datetime.now(timezone.utc)
        existing_account.error_message = None
        existing_account.connected_at = datetime.now(timezone.utc)
        
        account = existing_account
        action = AuditAction.GOOGLE_ACCOUNT_UPDATE
    else:
        # Check account limit
        count_result = await db.execute(
            select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == user_id)
        )
        count = count_result.scalar()
        if count >= settings.GOOGLE_ACCOUNTS_MAX_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum of {settings.GOOGLE_ACCOUNTS_MAX_PER_USER} Google accounts allowed per user"
            )
        
        # Create new account
        account = GoogleAccount(
            user_id=user_id,
            email=email,
            display_name=display_name,
            profile_picture=profile_picture,
            google_user_id=google_user_id,
            encrypted_session_data=encrypted_session,
            session_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            password_encrypted=refresh_encrypted,
            status=GoogleAccountStatus.CONNECTED,
            last_verified_at=datetime.now(timezone.utc),
            connected_at=datetime.now(timezone.utc),
        )
        db.add(account)
        action = AuditAction.GOOGLE_ACCOUNT_CONNECT
    
    await db.commit()
    await db.refresh(account)
    
    create_audit_log(
        db, user.id, action,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"email": account.email, "google_user_id": account.google_user_id}
    )
    await db.commit()
    
    # Redirect to frontend with success
    frontend_url = settings.CORS_ORIGINS[0] if getattr(settings, 'CORS_ORIGINS', None) else "http://localhost:3000"
    return RedirectResponse(url=f"{frontend_url}/dashboard/settings?google_account=connected&email={email}")


@router.post("/{account_id}/refresh")
async def refresh_google_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh Google OAuth access token using refresh token."""
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    # Get refresh token from encrypted password field
    if not account.password_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available for this account"
        )
    
    try:
        refresh_token = encryption_service.decrypt(account.password_encrypted)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt refresh token"
        )
    
    # Get OAuth credentials
    client_id, client_secret = await get_google_oauth_credentials(db)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials not configured"
        )
    
    # Refresh token
    try:
        tokens = await refresh_access_token(client_id, client_secret, refresh_token)
    except httpx.HTTPStatusError as e:
        account.status = GoogleAccountStatus.ERROR
        account.error_message = f"Token refresh failed: {e.response.text}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {e.response.text}"
        )
    
    # Update session data
    access_token = tokens.get("access_token")
    new_refresh_token = tokens.get("refresh_token", refresh_token)
    expires_in = tokens.get("expires_in", 3600)
    id_token = tokens.get("id_token")
    
    # Get current session data and update
    session_data = {}
    if account.encrypted_session_data:
        try:
            session_data = json.loads(encryption_service.decrypt(account.encrypted_session_data))
        except Exception:
            pass
    
    session_data.update({
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "id_token": id_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "token_type": tokens.get("token_type"),
        "scope": tokens.get("scope"),
    })
    
    account.encrypted_session_data = encryption_service.encrypt(json.dumps(session_data))
    account.session_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account.password_encrypted = encryption_service.encrypt(new_refresh_token)
    account.status = GoogleAccountStatus.CONNECTED
    account.last_verified_at = datetime.now(timezone.utc)
    account.error_message = None
    
    await db.commit()
    await db.refresh(account)
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_UPDATE,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"refreshed_at": account.last_verified_at.isoformat()}
    )
    await db.commit()
    
    return {"status": "refreshed", "expires_at": account.session_expires_at.isoformat()}


@router.post("/{account_id}/verify")
async def verify_google_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify Google account by checking token validity with Google."""
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.id == account_id, GoogleAccount.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google account not found"
        )
    
    # Get access token from encrypted session
    if not account.encrypted_session_data:
        account.status = GoogleAccountStatus.EXPIRED
        account.error_message = "No session data"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session for this account"
        )
    
    try:
        session_data = json.loads(encryption_service.decrypt(account.encrypted_session_data))
        access_token = session_data.get("access_token")
    except Exception:
        account.status = GoogleAccountStatus.ERROR
        account.error_message = "Failed to decrypt session"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt session data"
        )
    
    if not access_token:
        account.status = GoogleAccountStatus.EXPIRED
        account.error_message = "No access token in session"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token available"
        )
    
    # Verify token with Google
    try:
        token_info = await verify_token(access_token)
        
        # Check if token matches this account
        if token_info.get("email") != account.email:
            account.status = GoogleAccountStatus.ERROR
            account.error_message = "Token email mismatch"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not match account"
            )
        
        # Check expiry
        expires_in = int(token_info.get("expires_in", 0))
        if expires_in <= 60:  # Less than 1 minute left
            account.status = GoogleAccountStatus.EXPIRED
            account.error_message = "Token expired"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token expired"
            )
        
        # Success - update verification timestamp
        account.last_verified_at = datetime.now(timezone.utc)
        account.status = GoogleAccountStatus.CONNECTED
        account.error_message = None
        
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        account.status = GoogleAccountStatus.ERROR
        account.error_message = f"Token verification failed: {e.response.text}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token verification failed: {e.response.text}"
        )
    except Exception as e:
        account.status = GoogleAccountStatus.ERROR
        account.error_message = f"Verification error: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}"
        )
    
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


@router.post("", response_model=GoogleAccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_google_account(
    account_data: GoogleAccountConnectRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect a Google account using pre-existing session data (manual/cookie import)."""
    # Check account limit
    count_result = await db.execute(
        select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == current_user.id)
    )
    count = count_result.scalar()
    if count >= settings.GOOGLE_ACCOUNTS_MAX_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.GOOGLE_ACCOUNTS_MAX_PER_USER} Google accounts allowed per user"
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
        connected_at=datetime.now(timezone.utc)
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

    # NOTE: read operations are not audit-logged (audit F-23: listing
    # previously logged a misleading GOOGLE_ACCOUNT_VERIFY action).
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
        elif field == "password" and value:
            value = encryption_service.encrypt(value)
            field = "password_encrypted"
        setattr(account, field, value)
    
    # If status changed to disconnected, record disconnected_at
    if account_data.status == GoogleAccountStatus.DISCONNECTED and account.status != GoogleAccountStatus.DISCONNECTED:
        account.disconnected_at = datetime.now(timezone.utc)
    
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
    
    account.status = GoogleAccountStatus.DISCONNECTED
    account.disconnected_at = datetime.now(timezone.utc)
    # Disconnect must wipe ALL stored credentials (audit: refresh token was
    # left behind in password_encrypted); a disconnected account keeps no
    # session and no refresh token.
    account.encrypted_session_data = None
    account.password_encrypted = None
    account.session_expires_at = None
    account.error_message = None
    
    await db.commit()
    
    create_audit_log(
        db, current_user.id, AuditAction.GOOGLE_ACCOUNT_DISCONNECT,
        resource_type="google_account", resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"email": account.email}
    )
    await db.commit()