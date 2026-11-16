from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
import enum


class GoogleAccountStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"


class GoogleAccount(Base):
    __tablename__ = "google_accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Account identification
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    google_user_id = Column(String(100), nullable=True, unique=True)  # Google's internal ID
    
    # Encrypted session data (cookies, localStorage, etc.)
    encrypted_session_data = Column(Text, nullable=True)
    session_expires_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(SQLEnum(GoogleAccountStatus), default=GoogleAccountStatus.DISCONNECTED, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Usage tracking
    projects_assigned = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    connected_at = Column(DateTime, nullable=True)
    disconnected_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="google_accounts")
    projects = relationship("Project", back_populates="google_account")