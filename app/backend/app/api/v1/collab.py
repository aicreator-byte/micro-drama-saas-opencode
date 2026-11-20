"""Collaboration endpoints: websocket room + presence REST.

WS: /api/v1/ws/projects/{project_id}/collab?token=<JWT>
Auth comes from the `token` query param (no Authorization header on a
websocket handshake): the JWT is verified with the same
decode_access_token() used by get_current_user. Invalid/missing token
-> close code 4401; project not owned by the user -> close code 4404.

REST: GET .../collab/presence (daftar user di room) dan POST
.../collab/patch (ubah satu field bible) — dipakai halaman kolaborasi
web saat WebSocket tidak tersedia.

BATAS YANG DIKETAHUI (perbaikan P2-6 ronde 2 — didokumentasikan, bukan
disembunyikan):
- Room HANYA pemilik proyek (owner-only): user lain tidak bisa masuk
  karena belum ada model sharing/anggota proyek. Kolaborasi 2 user
  berbeda butuh model keanggotaan + undangan (belum dibuat).
- Registry in-memory single-worker: presence + broadcast tidak lintas
  proses/worker; deployment multi-worker butuh Redis (belum dibuat).
  Satu proses melayani banyak tab/perangkat dari user yang sama.
- WS memakai JWT penuh via ?token= (handshake WebSocket juga tidak bisa
  kirim header) — risiko yang sama seperti SSE lama; pola token stream
  berumur pendek belum diterapkan ke WS.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.api.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.services import collab as collab_service

router = APIRouter()


async def _user_from_token(token: str | None, db: AsyncSession) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


@router.websocket("/ws/projects/{project_id}/collab")
async def collab_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user = await _user_from_token(token, db)
    if user is None:
        await websocket.close(code=4401)
        return

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    conn_id = collab_service.register_connection(project_id, user.id, websocket)
    collab_service.join(project_id, user.id, user.full_name)
    await collab_service.broadcast(project_id, collab_service.presence_payload(project_id))

    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type") if isinstance(msg, dict) else None
            if mtype == "presence":
                collab_service.update_presence(
                    project_id, user.id,
                    section=msg.get("section"), cursor=msg.get("cursor"),
                )
                await collab_service.broadcast(
                    project_id, collab_service.presence_payload(project_id)
                )
            elif mtype == "patch":
                field, value = msg.get("field"), msg.get("value")
                if field not in collab_service.PATCHABLE_BIBLE_FIELDS or not isinstance(value, str):
                    await websocket.send_json({
                        "type": "error",
                        "detail": f"Invalid patch field: {field!r}",
                    })
                    continue
                updated = await collab_service.apply_bible_patch(
                    project_id, field, value, session=db
                )
                if updated is None:
                    await websocket.send_json({"type": "error", "detail": "Patch failed"})
                    continue
                await collab_service.broadcast(
                    project_id,
                    {"type": "patch", "user_id": user.id, "field": field, "value": value},
                    exclude_conn_id=conn_id,
                )
            elif mtype == "ping":
                collab_service.heartbeat(project_id, user.id)
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown message type: {mtype!r}"})
    except WebSocketDisconnect:
        pass
    finally:
        no_conns_left = collab_service.unregister_connection(project_id, conn_id, user.id)
        if no_conns_left:
            collab_service.leave(project_id, user.id)
        await collab_service.broadcast(
            project_id, collab_service.presence_payload(project_id)
        )


@router.get("/projects/{project_id}/collab/presence")
async def get_collab_presence(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "users": collab_service.get_presence(project_id)}


@router.post("/projects/{project_id}/collab/patch")
async def patch_collab_bible(
    project_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ubah satu field bible via REST (fallback bila WebSocket tidak
    tersedia). Field harus masuk whitelist PATCHABLE_BIBLE_FIELDS;
    hanya pemilik proyek (404 bila bukan). Mengembalikan field + nilai
    baru. Perilaku sama dengan pesan WS `patch` (tanpa broadcast —
    klien REST memuat ulang presence/bible sendiri)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")
    field = (payload or {}).get("field")
    value = (payload or {}).get("value")
    if field not in collab_service.PATCHABLE_BIBLE_FIELDS or not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"Invalid patch field: {field!r}")
    updated = await collab_service.apply_bible_patch(
        project_id, field, value, session=db
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="Patch failed")
    return {"project_id": project_id, "field": field, "value": value}
