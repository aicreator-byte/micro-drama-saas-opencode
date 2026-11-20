"""Video pipeline: rakit klip Flow yang sudah diupload jadi satu mp4.

TIDAK generate video — hanya FFmpeg concat. ffmpeg jalan di background
task (asyncio.create_task) agar POST langsung 202.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_user
from app.api.v1.story_engine import get_project_or_404
from app.core.config import settings
from app.core.database import async_session_maker, get_db
from app.models.asset import Asset
from app.models.episode import Episode
from app.models.user import User
from app.models.video_job import VideoJob
from app.schemas.video import AssembleRequest, VideoJobResponse
from app.services.storage import get_storage_backend, resolve_storage_root
from app.services.video_pipeline import assemble_video

logger = logging.getLogger(__name__)

router = APIRouter()

# Satu AsyncSession tes (in-memory sqlite, StaticPool) dipakai bersama oleh
# request handler + background task — akses DB di modul ini diserialisasi
# dengan lock ini supaya tidak tabrakan state transaksi. Di produksi tiap
# request/background pakai session sendiri, lock hanya menertibkan antar
# endpoint video.
#
# Lock dibuat MALAS per event loop (perbaikan FIX-ROUND2): asyncio.Lock
# module-level terikat ke loop yang pertama memakainya, dan pemakaian dari
# loop lain (mis. tiap tes pytest-asyncio punya loop sendiri) melempar
# "Lock is bound to a different event loop". Di produksi hanya ada satu
# loop sehingga perilakunya sama; di tes, lock dibuat ulang bila loop
# berganti.
_lock_holder: dict = {}


def _get_video_db_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _lock_holder.get("lock")
    if lock is None or _lock_holder.get("loop") is not loop:
        lock = asyncio.Lock()
        _lock_holder["lock"] = lock
        _lock_holder["loop"] = loop
    return lock


@asynccontextmanager
async def _job_session():
    """Session DB untuk background task.

    Di tes, get_db di-override ke session in-memory — pakai session itu
    (di bawah _get_video_db_lock(), jadi aman); di produksi pakai session
    maker biasa.
    """
    override = None
    try:
        from app.main import app as _app
        override = _app.dependency_overrides.get(get_db)
    except Exception:
        override = None
    if override is not None:
        agen = override()
        session = await agen.__anext__()
        try:
            yield session
        finally:
            try:
                await agen.aclose()
            except Exception:
                pass
    else:
        async with async_session_maker() as session:
            yield session


async def _update_job(job_id: str, **fields) -> bool:
    """Update status job dengan retry (transaksi sqlite in-memory di tes
    bisa tabrakan sesaat dengan request polling yang memakai koneksi sama)."""
    from sqlalchemy.exc import SQLAlchemyError

    for attempt in range(5):
        try:
            async with _get_video_db_lock():
                async with _job_session() as db:
                    job = (await db.execute(select(VideoJob).where(VideoJob.id == job_id))).scalar_one_or_none()
                    if not job:
                        return False
                    for key, value in fields.items():
                        setattr(job, key, value)
                    await db.commit()
            return True
        except (SQLAlchemyError, Exception):
            if attempt == 4:
                raise
            await asyncio.sleep(0.2 * (attempt + 1))
    return False


async def _get_job_or_404(project_id: str, job_id: str, db: AsyncSession) -> VideoJob:
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.project_id == project_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    return job


async def _resolve_key_to_local_path(key: str, job_id: str) -> Path:
    """Kunci aset -> path file lokal di dalam storage root.

    Backend lokal: langsung path-nya. Backend lain (s3): unduh dulu ke
    direktori temp di dalam storage root.
    """
    root = resolve_storage_root()
    if (settings.STORAGE_BACKEND or "local").lower() == "local":
        return (root / key).resolve()
    data = get_storage_backend().get(key)
    tmp_dir = root / "_tmp" / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / Path(key).name
    tmp_path.write_bytes(data)
    return tmp_path


async def _run_assemble(job_id: str, input_keys: list[str],
                        subtitle_key: str | None, audio_key: str | None,
                        resolution: str) -> None:
    tmp_dir: Path | None = None
    try:
        await _update_job(job_id, status="processing")
        root = resolve_storage_root()
        input_paths = [await _resolve_key_to_local_path(k, job_id) for k in input_keys]
        subtitle_path = await _resolve_key_to_local_path(subtitle_key, job_id) if subtitle_key else None
        audio_path = await _resolve_key_to_local_path(audio_key, job_id) if audio_key else None
        if (settings.STORAGE_BACKEND or "local").lower() != "local":
            tmp_dir = root / "_tmp" / job_id
        output_rel = f"video-outputs/{job_id}.mp4"
        duration = await asyncio.to_thread(
            assemble_video, input_paths, output_rel,
            subtitle_path, audio_path, resolution,
        )
        await _update_job(
            job_id, status="completed", output_path=output_rel,
            duration_seconds=duration, completed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        try:
            await _update_job(
                job_id, status="failed", error_message=str(e)[:2000],
                completed_at=datetime.now(timezone.utc),
            )
        except Exception:
            pass
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)


async def resume_stale_video_jobs(engine) -> list[str]:
    """Resume VideoJob yang ditinggal `pending`/`processing` oleh restart.

    Cerminan `resume_stale_jobs` untuk auto-generate (perbaikan P2-4
    ronde 2): sebelumnya tidak ada sweep startup untuk VideoJob, jadi
    restart saat assemble berjalan meninggalkan job `processing` selamanya
    (tidak gagal, tidak lanjut). Job dengan parameter lengkap di-reset ke
    `pending` lalu `_run_assemble` dijadwalkan ulang (perakitan ulang
    dari awal — output ditimpa, idempotent). Job yang input-nya tidak
    tersimpan (baris lama sebelum kolom P2-4) ditandai `failed`
    "interrupted by restart" supaya tidak menggantung. No-op bila tidak
    ada yang stale. Dipanggil sekali saat startup (lihat app/main.py).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker as _sessionmaker

    factory = _sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    to_resume: list[dict] = []
    try:
        async with factory() as session:
            result = await session.execute(
                select(VideoJob).where(
                    VideoJob.status.in_(["pending", "processing"])
                )
            )
            jobs = list(result.scalars().all())
            for job in jobs:
                try:
                    input_keys = json.loads(job.input_files or "[]")
                except (ValueError, TypeError):
                    input_keys = []
                if not input_keys:
                    job.status = "failed"
                    job.error_message = "interrupted by restart (missing input list)"
                    job.completed_at = datetime.now(timezone.utc)
                    logger.warning(
                        "resume_stale_video_jobs: job %s failed, no inputs stored",
                        job.id,
                    )
                    continue
                job.status = "pending"
                job.error_message = None
                to_resume.append({
                    "job_id": job.id,
                    "input_keys": input_keys,
                    "subtitle_key": job.subtitle_key,
                    "audio_key": job.audio_key,
                    "resolution": job.resolution or "1080x1920",
                })
                logger.info(
                    "resume_stale_video_jobs: resuming job %s", job.id
                )
            await session.commit()
    except Exception as exc:
        logger.warning(f"resume_stale_video_jobs failed: {exc}")
        return []
    resumed: list[str] = []
    for item in to_resume:
        try:
            asyncio.create_task(_run_assemble(
                item["job_id"], item["input_keys"], item["subtitle_key"],
                item["audio_key"], item["resolution"],
            ))
            resumed.append(item["job_id"])
        except Exception as exc:
            logger.warning(
                f"resume_stale_video_jobs: could not resume {item['job_id']}: {exc}"
            )
    return resumed


@router.post("/{project_id}/video/assemble", response_model=VideoJobResponse,
              status_code=status.HTTP_202_ACCEPTED)
async def assemble_video_endpoint(
    project_id: str,
    body: AssembleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with _get_video_db_lock():
        await get_project_or_404(project_id, current_user.id, db)
        if body.episode_id:
            ep = (await db.execute(
                select(Episode).where(Episode.id == body.episode_id, Episode.project_id == project_id)
            )).scalar_one_or_none()
            if not ep:
                raise HTTPException(status_code=404, detail="Episode not found")

        # Semua key harus merujuk ke aset yang sudah diupload.
        all_keys = list(body.input_keys)
        if body.subtitle_key:
            all_keys.append(body.subtitle_key)
        if body.audio_key:
            all_keys.append(body.audio_key)
        for key in all_keys:
            asset = (await db.execute(
                select(Asset).where(Asset.project_id == project_id, Asset.key == key)
            )).scalar_one_or_none()
            if not asset:
                raise HTTPException(status_code=404, detail=f"Asset not found: {key}")

        job = VideoJob(
            project_id=project_id,
            episode_id=body.episode_id,
            status="pending",
            input_files=json.dumps(body.input_keys),
            # P2-4: simpan SEMUA parameter perakitan — tanpa ini job yang
            # terpotong restart tidak bisa di-resume (hanya input_files
            # yang tersimpan sebelumnya).
            subtitle_key=body.subtitle_key,
            audio_key=body.audio_key,
            resolution=body.resolution,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
    asyncio.create_task(_run_assemble(
        job.id, body.input_keys, body.subtitle_key, body.audio_key, body.resolution,
    ))
    return job


@router.get("/{project_id}/video/jobs/{job_id}", response_model=VideoJobResponse)
async def get_video_job(
    project_id: str,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with _get_video_db_lock():
        await get_project_or_404(project_id, current_user.id, db)
        return await _get_job_or_404(project_id, job_id, db)


@router.get("/{project_id}/video/jobs", response_model=list[VideoJobResponse])
async def list_video_jobs(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with _get_video_db_lock():
        await get_project_or_404(project_id, current_user.id, db)
        result = await db.execute(
            select(VideoJob).where(VideoJob.project_id == project_id)
            .order_by(VideoJob.created_at.desc())
        )
        return result.scalars().all()
