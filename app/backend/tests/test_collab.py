import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.series_bible import SeriesBible
from app.services import collab as collab_service


@pytest.fixture(autouse=True)
def _reset_collab():
    collab_service.reset_state()
    yield
    collab_service.reset_state()


def _token(auth_headers):
    return auth_headers["Authorization"].split(" ", 1)[1]


class TestCollabWebsocket:
    @pytest.mark.asyncio
    async def test_patch_broadcast_between_two_clients(
        self, client: AsyncClient, auth_headers, test_project,
        test_series_bible, db_session,
    ):
        token = _token(auth_headers)
        tc = TestClient(app)
        url = f"/api/v1/ws/projects/{test_project.id}/collab?token={token}"
        with tc.websocket_connect(url) as ws_a, tc.websocket_connect(url) as ws_b:
            # Each connect broadcasts presence; drain both queues.
            # A sees its own join + B's join; B sees only its own join.
            ws_a.receive_json()
            ws_a.receive_json()
            ws_b.receive_json()
            # A sends a presence update; B must see the presence list.
            ws_a.send_json({"type": "presence", "section": "bible", "cursor": {"line": 3}})
            msg_b = ws_b.receive_json()
            assert msg_b["type"] == "presence"
            assert len(msg_b["users"]) >= 1
            assert msg_b["users"][0]["section"] == "bible"
            # Drain A's own presence echo.
            ws_a.receive_json()

            # A patches the bible premise; B must receive the broadcast.
            ws_a.send_json({"type": "patch", "field": "premise", "value": "New premise from collab"})
            patch = ws_b.receive_json()
            assert patch["type"] == "patch"
            assert patch["field"] == "premise"
            assert patch["value"] == "New premise from collab"

            # REST presence shows the user while connected.
            resp = tc.get(
                f"/api/v1/projects/{test_project.id}/collab/presence",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert any(u["full_name"] == "Test User" for u in resp.json()["users"])

        # After the patch, the DB bible actually changed.
        result = await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == test_project.id)
        )
        bible = result.scalar_one()
        assert bible.premise == "New premise from collab"

    @pytest.mark.asyncio
    async def test_ping_pong_and_unknown_message(
        self, client: AsyncClient, auth_headers, test_project,
    ):
        token = _token(auth_headers)
        tc = TestClient(app)
        url = f"/api/v1/ws/projects/{test_project.id}/collab?token={token}"
        with tc.websocket_connect(url) as ws:
            ws.receive_json()  # presence broadcast on join
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}
            ws.send_json({"type": "nonsense"})
            err = ws.receive_json()
            assert err["type"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(
        self, client: AsyncClient, auth_headers, test_project,
    ):
        tc = TestClient(app)
        url = f"/api/v1/ws/projects/{test_project.id}/collab?token=not-a-real-token"
        with pytest.raises(WebSocketDisconnect):
            with tc.websocket_connect(url):
                pass

    @pytest.mark.asyncio
    async def test_missing_token_rejected(
        self, client: AsyncClient, auth_headers, test_project,
    ):
        tc = TestClient(app)
        url = f"/api/v1/ws/projects/{test_project.id}/collab"
        with pytest.raises(WebSocketDisconnect):
            with tc.websocket_connect(url):
                pass

    @pytest.mark.asyncio
    async def test_patch_invalid_field_rejected_bible_unchanged(
        self, client: AsyncClient, auth_headers, test_project,
        test_series_bible, db_session,
    ):
        token = _token(auth_headers)
        tc = TestClient(app)
        url = f"/api/v1/ws/projects/{test_project.id}/collab?token={token}"
        with tc.websocket_connect(url) as ws:
            ws.receive_json()  # presence broadcast on join
            ws.send_json({"type": "patch", "field": "id", "value": "hacked"})
            err = ws.receive_json()
            assert err["type"] == "error"
            ws.send_json({"type": "patch", "field": "premise", "value": 123})
            err2 = ws.receive_json()
            assert err2["type"] == "error"

        result = await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == test_project.id)
        )
        bible = result.scalar_one()
        assert bible.premise == "A family drama about betrayal and redemption"
        assert bible.id != "hacked"

    @pytest.mark.asyncio
    async def test_presence_requires_project_owner(
        self, client: AsyncClient, auth_headers2, test_project,
    ):
        # User 2 does not own test_project -> presence REST is 404.
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/collab/presence",
            headers=auth_headers2,
        )
        assert resp.status_code == 404


class TestCollabService:
    def test_prune_drops_stale_entries(self):
        import time
        collab_service.join("p1", "u1", "Alice")
        collab_service.join("p1", "u2", "Bob")
        # Fake u2 as last seen 120s ago.
        collab_service._rooms["p1"]["u2"]["last_seen"] = time.time() - 120
        collab_service.prune("p1")
        users = collab_service.get_presence("p1")
        assert [u["user_id"] for u in users] == ["u1"]

    def test_join_leave_heartbeat(self):
        collab_service.join("p1", "u1", "Alice")
        collab_service.update_presence("p1", "u1", section="characters", cursor={"line": 1})
        users = collab_service.get_presence("p1")
        assert users[0]["section"] == "characters"
        assert users[0]["cursor"] == {"line": 1}
        collab_service.heartbeat("p1", "u1")
        collab_service.leave("p1", "u1")
        assert collab_service.get_presence("p1") == []
