from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class Asset(Base):
    """File aset proyek (klip video Flow, gambar, audio, subtitle, ...).

    `key` adalah kunci logis di backend storage (bukan path absolut);
    file fisiknya diselesaikan oleh app.services.storage.
    """

    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    backend = Column(String(20), nullable=False, default="local")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
