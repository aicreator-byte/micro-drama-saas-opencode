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


# --- Short-lived SSE stream tokens (perbaikan P2-2 ronde 2) ---
#
# EventSource tidak bisa mengirim header Authorization, jadi browser lama
# mengirim JWT penuh lewat ?token= — token berumur panjang itu tercatat di
# access log, history browser, dan bisa bocor via header Referer. Sebagai
# gantinya frontend meminta token stream khusus (endpoint
# POST .../auto-generate/{job_id}/stream-token, auth via header):
#   - umur 5 menit, sekali tujuan (purpose="sse"),
#   - terikat ke SATU job (job_id) — tidak bisa dipakai membuka stream
#     job lain atau memanggil endpoint lain,
#   - hanya memberi hak baca progres stream itu.
# Risiko sisa: token tetap lewat URL (sifat EventSource), tapi masa
# berlakunya pendek dan cakupannya sempit; JWT penuh via ?token= kini
# DITOLAK (401) — hanya header Authorization yang boleh membawa JWT penuh.
STREAM_TOKEN_EXPIRE_MINUTES = 5


def create_stream_token(user_id: str, job_id: str,
                       expires_minutes: int = STREAM_TOKEN_EXPIRE_MINUTES) -> str:
    """Token SSE berumur pendek untuk satu job auto-generate."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(
        {"sub": user_id, "purpose": "sse", "job_id": job_id, "exp": expire},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )


def decode_stream_token(token: str, job_id: str) -> Optional[str]:
    """Validasi token stream untuk job tertentu. Kembalikan user_id, atau
    None bila token bukan token stream, job-nya beda, atau kedaluwarsa."""
    payload = decode_access_token(token)
    if not payload:
        return None
    if payload.get("purpose") != "sse":
        return None
    if payload.get("job_id") != job_id:
        return None
    user_id = payload.get("sub")
    return user_id if isinstance(user_id, str) and user_id else None