"""Asset management: upload/list/download/delete via StorageBackend.

Default backend lokal (settings.ASSET_STORAGE_DIR); bila STORAGE_BACKEND=s3,
download me-redirect 302 ke URL S3/CDN.
"""
from __future__ import annotations

import re
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.story_engine import get_project_or_404
from app.core.config import settings
from app.core.database import get_db
from app.models.asset import Asset
from app.models.user import User
from app.schemas.asset import AssetResponse
from app.services.storage import get_storage_backend, sanitize_key

router = APIRouter()


def _safe_filename(filename: str) -> str:
    name = (filename or "file").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "file"
    return name[:200]


def _asset_url(asset: Asset) -> str:
    try:
        return get_storage_backend().url(asset.key)
    except Exception:
        return asset.key


@router.post("/{project_id}/assets", response_model=AssetResponse,
              status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_project_or_404(project_id, current_user.id, db)
    # P2-1: batas dicek SEBELUM file dibaca penuh ke memori. Sebelumnya
    # `await file.read()` membaca seluruh body dulu baru `len(data)` dicek
    # — upload raksasa menghabiskan memori sebelum 413 sempat keluar.
    # Baca streaming per chunk 1MB dan batalkan begitu melewati batas.
    # (Content-Length TIDAK dipakai sebagai pre-check: pada multipart
    # nilainya mencakup framing MIME, bukan ukuran file — file 5 byte
    # bisa ber-Content-Length 250 byte dan salah ditolak.)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 100MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    backend = get_storage_backend()
    key = sanitize_key(f"{project_id}/{uuid.uuid4()}-{_safe_filename(file.filename or 'file')}")
    backend.put(key, data, content_type=file.content_type or "application/octet-stream")
    asset = Asset(
        project_id=project_id,
        key=key,
        filename=_safe_filename(file.filename or "file"),
        content_type=file.content_type,
        size_bytes=len(data),
        backend=(settings.STORAGE_BACKEND or "local").lower(),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return AssetResponse.model_validate(asset, from_attributes=True).model_copy(
        update={"url": _asset_url(asset)}
    )


@router.get("/{project_id}/assets", response_model=List[AssetResponse])
async def list_assets(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_project_or_404(project_id, current_user.id, db)
    result = await db.execute(
        select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    return [
        AssetResponse.model_validate(a, from_attributes=True).model_copy(
            update={"url": _asset_url(a)}
        )
        for a in assets
    ]


async def _get_asset_or_404(project_id: str, asset_id: str,
                            user_id: str, db: AsyncSession) -> Asset:
    await get_project_or_404(project_id, user_id, db)
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.project_id == project_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{project_id}/assets/{asset_id}/download")
async def download_asset(
    project_id: str,
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    asset = await _get_asset_or_404(project_id, asset_id, current_user.id, db)
    backend = get_storage_backend()
    if (settings.STORAGE_BACKEND or "local").lower() == "s3":
        return RedirectResponse(url=backend.url(asset.key), status_code=302)
    try:
        data = backend.get(asset.key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Asset file not found in storage")
    return StreamingResponse(
        iter([data]),
        media_type=asset.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{asset.filename}"'},
    )


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    project_id: str,
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    asset = await _get_asset_or_404(project_id, asset_id, current_user.id, db)
    try:
        get_storage_backend().delete(asset.key)
    except Exception:
        pass  # file hilang dari storage bukan alasan gagal hapus record
    await db.delete(asset)
    await db.commit()
    return None
