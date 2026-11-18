from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from app.models.google_account import GoogleAccountStatus


class GoogleAccountBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=255)
    profile_picture: Optional[str] = Field(None, max_length=500)
    google_user_id: Optional[str] = Field(None, max_length=100)


class GoogleAccountCreate(GoogleAccountBase):
    pass


class GoogleAccountUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    profile_picture: Optional[str] = Field(None, max_length=500)
    status: Optional[GoogleAccountStatus] = None
    encrypted_session_data: Optional[str] = None
    session_expires_at: Optional[datetime] = None
    password: Optional[str] = Field(None, max_length=500)  # Plaintext password, will be encrypted on save


class GoogleAccountResponse(GoogleAccountBase):
    id: str
    user_id: str
    status: GoogleAccountStatus
    last_verified_at: Optional[datetime] = None
    error_message: Optional[str] = None
    projects_assigned: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GoogleAccountConnectRequest(BaseModel):
    email: EmailStr
    session_data: str  # Encrypted session data (cookies, localStorage)
    expires_at: Optional[datetime] = None


class GoogleAccountSessionUpdate(BaseModel):
    encrypted_session_data: str
    expires_at: Optional[datetime] = None


class GoogleOAuthAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class GoogleOAuthTokenResponse(BaseModel):
    status: str
    expires_at: Optional[str] = None