from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
import hashlib
import secrets
from app.core.config import settings

# For testing, use a simple hash. In production, use bcrypt.
# We check if we're in test mode by checking the database URL
def is_test_mode():
    return "sqlite" in settings.DATABASE_URL

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if is_test_mode():
        # Simple SHA256 for testing
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    if is_test_mode():
        # Simple SHA256 for testing
        return hashlib.sha256(password.encode()).hexdigest()
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
        return None