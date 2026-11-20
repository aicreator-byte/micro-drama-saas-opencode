"""SSE live-progress stream for auto-generate jobs."""
import asyncio
import json

import pytest
from httpx import AsyncClient


async def _create_job(client, project_id, headers):
    return await client.post(
        f"/api/v1/projects/{project_id}/auto-generate",
        json={
            "title": "THE BILLIONAIRE CEO",
            "genre": "Romance",
            "total_episodes": 5,
            "premise": "A struggling young woman marries a cold billionaire CEO.",
        },
        headers=headers,
    )


async def _read_events(client, url, headers, timeout=30.0):
    """Collect (event, data-dict) pairs until the `done` event."""
    events = []
    deadline = asyncio.get_event_loop().time() + timeout
    async with client.stream("GET", url, headers=headers) as resp:
        assert resp.status_code == 200, resp.text
        assert "text/event-stream" in resp.headers.get("content-type", "")
        current_event = None
        async for line in resp.aiter_lines():
            if asyncio.get_event_loop().time() > deadline:
                raise AssertionError(f"stream did not finish in {timeout}s; got {events}")
            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
            elif line.startswith("data:") and current_event is not None:
                events.append((current_event, json.loads(line[len("data:"):].strip())))
                if current_event == "done":
                    break
                current_event = None
    return events


class TestAutoGenerateStream:
    @pytest.mark.asyncio
    async def test_stream_emits_progress_then_done(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]

        events = await _read_events(
            client,
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream",
            auth_headers,
        )
        kinds = [kind for kind, _ in events]
        assert "progress" in kinds
        assert kinds[-1] == "done"
        # Payloads have the same shape as AutoGenerateJobResponse.
        last_progress = [data for kind, data in events if kind == "progress"][-1]
        assert last_progress["id"] == job_id
        assert len(last_progress["steps"]) == 5
        assert [s["step"] for s in last_progress["steps"]] == [
            "series_bible", "characters", "locations", "episodes", "prompts",
        ]
        done_payload = events[-1][1]
        assert done_payload["status"] == "completed"
        assert all(s["status"] == "completed" for s in done_payload["steps"])

    @pytest.mark.asyncio
    async def test_stream_unknown_job_is_404(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/does-not-exist/stream",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_without_token_is_401(
        self, client: AsyncClient, test_project, test_settings_with_mock
    ):
        created = None
        # Need a real job id for the 401 path — but without a token we
        # cannot create one; use a dummy id: auth runs before the 404.
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/does-not-exist/stream",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_other_users_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2, test_settings_with_mock
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project2.id}/auto-generate/does-not-exist/stream",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_accepts_stream_token_query_param(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        """EventSource cannot send an Authorization header, so the browser
        passes a SHORT-LIVED stream token as ?token= (POST .../stream-token
        first). Perbaikan P2-2 ronde 2: token stream terikat satu job +
        5 menit — JWT penuh via ?token= kini ditolak (lihat tes berikut)."""
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]
        token_resp = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream-token",
            headers=auth_headers,
        )
        assert token_resp.status_code == 200, token_resp.text
        stream_token = token_resp.json()["stream_token"]
        assert token_resp.json()["expires_in_seconds"] == 300

        events = await _read_events(
            client,
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream"
            f"?token={stream_token}",
            headers={},  # no Authorization header on purpose
        )
        kinds = [kind for kind, _ in events]
        assert kinds[-1] == "done"
        assert events[-1][1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_stream_rejects_full_jwt_in_query_param(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        """P2-2: JWT penuh (umur panjang) tidak boleh lewat URL lagi."""
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]
        raw_token = auth_headers["Authorization"].split(" ", 1)[1]
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream"
            f"?token={raw_token}",
            headers={},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_token_wrong_job_is_401(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        """Token stream terikat satu job — tidak bisa dipakai job lain."""
        created = await _create_job(client, test_project.id, auth_headers)
        job_id = created.json()["id"]
        created2 = await _create_job(client, test_project.id, auth_headers)
        job_id2 = created2.json()["id"]
        token_resp = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream-token",
            headers=auth_headers,
        )
        stream_token = token_resp.json()["stream_token"]
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id2}/stream"
            f"?token={stream_token}",
            headers={},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_token_endpoint_requires_auth_and_job(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        created = await _create_job(client, test_project.id, auth_headers)
        job_id = created.json()["id"]
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream-token",
        )
        assert resp.status_code == 401
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/does-not-exist/stream-token",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_bad_query_token_is_401(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        created = await _create_job(client, test_project.id, auth_headers)
        job_id = created.json()["id"]
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream"
            "?token=not-a-real-token",
        )
        assert resp.status_code == 401
