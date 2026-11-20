"""Real-time collaboration: presence + bible patch broadcast.

Single-worker in-memory registry: rooms live only in this process.
Multi-worker deployments need Redis (NOT implemented here) — presence
and broadcasts do not cross processes/workers.
"""
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker
from app.models.series_bible import SeriesBible

PRESENCE_TIMEOUT_SECONDS = 60

# Fields of SeriesBible a collab client may patch (whitelist).
PATCHABLE_BIBLE_FIELDS = frozenset({
    "premise",
    "main_plot",
    "tone_and_visual_style",
    "world_settings",
    "ending_direction",
    "episode_structure",
})

# project_id -> {user_id: {"user_id", "full_name", "section", "cursor", "last_seen"}}
_rooms: dict[str, dict[str, dict[str, Any]]] = {}
# project_id -> {conn_id: (user_id, WebSocket)}; one user may hold several
# connections (two tabs/devices), so connections are keyed per-connection,
# while presence is keyed per-user (with a refcount below).
_connections: dict[str, dict[str, tuple[str, Any]]] = {}
# project_id -> {user_id: {conn_id, ...}} (presence leaves only when the
# user's last connection drops)
_user_conns: dict[str, dict[str, set[str]]] = {}

# Session factory used for bible patches (a fresh session per patch, so a
# long-lived websocket never holds a request transaction open). Tests may
# monkeypatch this to a sessionmaker bound to the test engine.
session_factory: async_sessionmaker[AsyncSession] = async_session_maker


def join(project_id: str, user_id: str, full_name: str | None) -> dict[str, Any]:
    entry = {
        "user_id": user_id,
        "full_name": full_name,
        "section": None,
        "cursor": None,
        "last_seen": time.time(),
    }
    _rooms.setdefault(project_id, {})[user_id] = entry
    return entry


def leave(project_id: str, user_id: str) -> None:
    room = _rooms.get(project_id)
    if room:
        room.pop(user_id, None)
        if not room:
            _rooms.pop(project_id, None)


def update_presence(
    project_id: str,
    user_id: str,
    section: Any = None,
    cursor: Any = None,
) -> dict[str, Any] | None:
    room = _rooms.get(project_id, {})
    entry = room.get(user_id)
    if entry is None:
        return None
    if section is not None:
        entry["section"] = section
    if cursor is not None:
        entry["cursor"] = cursor
    entry["last_seen"] = time.time()
    return entry


def heartbeat(project_id: str, user_id: str) -> None:
    room = _rooms.get(project_id, {})
    entry = room.get(user_id)
    if entry is not None:
        entry["last_seen"] = time.time()


def prune(project_id: str | None = None, now: float | None = None) -> None:
    """Drop presence entries not seen for >60s (and empty rooms)."""
    now = time.time() if now is None else now
    targets = [project_id] if project_id else list(_rooms.keys())
    for pid in targets:
        room = _rooms.get(pid)
        if not room:
            continue
        stale = [
            uid for uid, e in room.items()
            if now - float(e.get("last_seen", 0)) > PRESENCE_TIMEOUT_SECONDS
        ]
        for uid in stale:
            room.pop(uid, None)
        if not room:
            _rooms.pop(pid, None)


def get_presence(project_id: str) -> list[dict[str, Any]]:
    prune(project_id)
    room = _rooms.get(project_id, {})
    return [dict(e) for e in sorted(room.values(), key=lambda x: str(x.get("full_name") or ""))]


def presence_payload(project_id: str) -> dict[str, Any]:
    return {"type": "presence", "project_id": project_id, "users": get_presence(project_id)}


def register_connection(project_id: str, user_id: str, websocket: Any) -> str:
    """Register a websocket; returns the per-connection id."""
    import uuid
    conn_id = str(uuid.uuid4())
    _connections.setdefault(project_id, {})[conn_id] = (user_id, websocket)
    _user_conns.setdefault(project_id, {}).setdefault(user_id, set()).add(conn_id)
    return conn_id


def unregister_connection(project_id: str, conn_id: str, user_id: str) -> bool:
    """Drop a connection. Returns True if the user has no connections left."""
    conns = _connections.get(project_id)
    if conns:
        conns.pop(conn_id, None)
        if not conns:
            _connections.pop(project_id, None)
    user_conns = _user_conns.get(project_id, {}).get(user_id)
    if user_conns is not None:
        user_conns.discard(conn_id)
        if not user_conns:
            _user_conns.get(project_id, {}).pop(user_id, None)
            if not _user_conns.get(project_id):
                _user_conns.pop(project_id, None)
            return True
    return False


async def broadcast(
    project_id: str,
    message: dict[str, Any],
    exclude_conn_id: str | None = None,
) -> None:
    """Send a JSON message to every connected member of a room."""
    for conn_id, (uid, ws) in list(_connections.get(project_id, {}).items()):
        if exclude_conn_id is not None and conn_id == exclude_conn_id:
            continue
        try:
            await ws.send_json(message)
        except Exception:
            unregister_connection(project_id, conn_id, uid)


async def apply_bible_patch(
    project_id: str,
    field: str,
    value: str,
    session: AsyncSession | None = None,
) -> SeriesBible | None:
    """Apply one whitelisted bible patch.

    With `session` given, the patch runs on that session (the websocket
    connection's own session — one session per connection, never the HTTP
    request's). Without it, a fresh session is opened from
    `session_factory` and closed afterwards. Returns the updated (or newly
    created) SeriesBible, or None if the field is not whitelisted / value
    is not a string.
    """
    if field not in PATCHABLE_BIBLE_FIELDS or not isinstance(value, str):
        return None
    if session is not None:
        result = await session.execute(
            select(SeriesBible).where(SeriesBible.project_id == project_id)
        )
        bible = result.scalar_one_or_none()
        if bible is None:
            bible = SeriesBible(project_id=project_id)
            session.add(bible)
        setattr(bible, field, value)
        await session.commit()
        await session.refresh(bible)
        return bible
    async with session_factory() as fresh:
        return await apply_bible_patch(project_id, field, value, session=fresh)


def reset_state() -> None:
    """Test helper: clear all rooms and connections."""
    _rooms.clear()
    _connections.clear()
    _user_conns.clear()
