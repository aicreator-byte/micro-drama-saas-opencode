"""Analytics: LLM usage recording + summary/usage endpoints."""
import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1.auto_generate import _chat_json
from app.models.llm_usage import LlmUsageEvent
from app.services.llm_usage import make_usage_sink
from app.services.llm_pricing import estimated_cost_usd, price_per_1m_usd


async def _wait_for_job(client, project_id, job_id, headers, timeout=30.0):
    last = None
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/auto-generate/{job_id}",
            headers=headers,
        )
        last = resp
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                return data
        await asyncio.sleep(0.25)
    raise AssertionError(
        f"job {job_id} did not finish in {timeout}s; last response: "
        f"{last.status_code if last is not None else None} "
        f"{last.text if last is not None else ''}"
    )


class TestLlmUsageRecording:
    @pytest.mark.asyncio
    async def test_chat_json_with_sink_records_one_event(
        self, db_session, test_user, test_project, test_settings_with_mock
    ):
        sink = make_usage_sink(
            db_session, test_user.id, project_id=test_project.id, job_id=None
        )
        out = await _chat_json(
            db_session,
            "You are a professional TV series writer. Create a complete series bible for a micro-drama series.\nTitle: X",
            usage_sink=sink,
        )
        assert out["premise"] == "Mock premise for the series"

        events = (await db_session.execute(
            select(LlmUsageEvent).where(LlmUsageEvent.project_id == test_project.id)
        )).scalars().all()
        assert len(events) == 1
        event = events[0]
        assert event.user_id == test_user.id
        assert event.model == "mock-model"
        # Mock provider usage (see AIClient._call_mock).
        assert (event.prompt_tokens, event.completion_tokens, event.total_tokens) == (100, 200, 300)
        assert event.estimated_cost_usd == 0.0  # mock-model is priced 0.0

    @pytest.mark.asyncio
    async def test_failing_sink_does_not_fail_the_call(
        self, db_session, test_settings_with_mock
    ):
        async def boom(_response):
            raise RuntimeError("sink exploded")

        out = await _chat_json(
            db_session,
            "Create a complete series bible for a micro-drama series.\nTitle: X",
            usage_sink=boom,
        )
        assert out["premise"] == "Mock premise for the series"

    def test_pricing_unknown_model_is_none(self):
        assert price_per_1m_usd("some/unknown-model-xyz") is None
        assert estimated_cost_usd("some/unknown-model-xyz", 100, 100) is None

    def test_pricing_env_override(self, monkeypatch):
        monkeypatch.setenv(
            "LLM_PRICE_NVIDIA_NEMOTRON_3_ULTRA_550B_A55B", "0.80"
        )
        assert price_per_1m_usd("nvidia/nemotron-3-ultra-550b-a55b") == 0.80
        assert estimated_cost_usd(
            "nvidia/nemotron-3-ultra-550b-a55b", 1_000_000, 0
        ) == 0.80


class TestAnalyticsEndpoints:
    @pytest.mark.asyncio
    async def test_summary_sums_a_completed_job(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        created = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate",
            json={
                "title": "THE BILLIONAIRE CEO",
                "genre": "Romance",
                "total_episodes": 5,
                "premise": "A struggling young woman marries a cold billionaire CEO.",
            },
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]
        data = await _wait_for_job(client, test_project.id, job_id, auth_headers)
        assert data["status"] == "completed"

        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/analytics/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        summary = resp.json()
        assert summary["total_jobs"] == 1
        assert summary["completed_jobs"] == 1
        assert summary["failed_jobs"] == 0
        # 5 LLM calls (bible, characters, world, outline, prompts),
        # mock usage 100/200/300 each.
        assert summary["total_prompt_tokens"] == 500
        assert summary["total_completion_tokens"] == 1000
        assert summary["total_tokens"] == 1500
        assert summary["total_estimated_cost_usd"] == 0.0
        assert len(summary["cost_by_model"]) == 1
        assert summary["cost_by_model"][0]["model"] == "mock-model"
        assert summary["cost_by_model"][0]["events"] == 5
        assert summary["cost_by_model"][0]["total_tokens"] == 1500
        assert len(summary["cost_by_job"]) == 1
        assert summary["cost_by_job"][0]["job_id"] == job_id
        assert summary["cost_by_job"][0]["events"] == 5

        # Usage list: 5 events, paginated.
        page1 = await client.get(
            f"/api/v1/projects/{test_project.id}/analytics/usage?limit=2&offset=0",
            headers=auth_headers,
        )
        assert page1.status_code == 200, page1.text
        assert page1.json()["total"] == 5
        assert len(page1.json()["items"]) == 2
        page2 = await client.get(
            f"/api/v1/projects/{test_project.id}/analytics/usage?limit=2&offset=4",
            headers=auth_headers,
        )
        assert len(page2.json()["items"]) == 1
        assert page2.json()["items"][0]["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_summary_empty_project_is_zeros(
        self, client: AsyncClient, auth_headers, test_project
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/analytics/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["total_jobs"] == 0
        assert summary["total_tokens"] == 0
        assert summary["total_estimated_cost_usd"] is None
        assert summary["cost_by_model"] == []
        assert summary["cost_by_job"] == []

    @pytest.mark.asyncio
    async def test_cross_user_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2
    ):
        for path in ("analytics/summary", "analytics/usage"):
            resp = await client.get(
                f"/api/v1/projects/{test_project2.id}/{path}",
                headers=auth_headers,
            )
            assert resp.status_code == 404, (path, resp.text)

    @pytest.mark.asyncio
    async def test_analytics_without_token_is_401(
        self, client: AsyncClient, test_project
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/analytics/summary",
        )
        assert resp.status_code == 401
