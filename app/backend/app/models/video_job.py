from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class VideoJob(Base):
    """Satu pekerjaan perakitan video (FFmpeg concat dari klip Flow).

    Video TIDAK di-generate di sini — hanya klip yang sudah ada yang
    dirakit jadi satu file mp4 vertikal.
    """

    __tablename__ = "video_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending/processing/completed/failed
    input_files = Column(Text, nullable=True)  # JSON list of relative paths / asset keys
    # Parameter perakitan (perbaikan P2-4 ronde 2): tanpa ini job yang
    # terpotong restart tidak bisa di-resume — hanya input_files yang
    # tersimpan, subtitle/audio/resolusi hilang.
    subtitle_key = Column(String(500), nullable=True)
    audio_key = Column(String(500), nullable=True)
    resolution = Column(String(20), nullable=True, default="1080x1920")
    output_path = Column(String(500), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
