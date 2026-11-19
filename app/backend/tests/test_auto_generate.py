import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode
from app.models.prompt import Prompt, PromptType
from app.models.series_bible import SeriesBible


async def _create_job(client, project_id, headers, **overrides):
    body = {
        "title": "THE BILLIONAIRE CEO",
        "genre": "Romance",
        "total_episodes": 5,
        "premise": "A struggling young woman marries a cold billionaire CEO.",
    }
    body.update(overrides)
    return await client.post(
        f"/api/v1/projects/{project_id}/auto-generate", json=body, headers=headers
    )


class TestAutoGenerate:
    @pytest.mark.asyncio
    async def test_create_job_completes_all_steps(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock, db_session
    ):
        response = await _create_job(client, test_project.id, auth_headers)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "completed"
        assert data["title"] == "THE BILLIONAIRE CEO"
        assert len(data["steps"]) == 5
        assert [s["step"] for s in data["steps"]] == [
            "series_bible", "characters", "locations", "episodes", "prompts",
        ]
        assert all(s["status"] == "completed" for s in data["steps"])

        # Step 1 wrote the bible (mock provider).
        bible = (await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == test_project.id)
        )).scalar_one()
        assert bible.premise == "Mock premise for the series"

        # Step 2 wrote 5 characters, step 3 wrote 1 location (mock world).
        characters = (await db_session.execute(
            select(Character).where(Character.project_id == test_project.id)
        )).scalars().all()
        assert len(characters) == 5
        assert {c.name for c in characters} == {f"Mock Character {i}" for i in range(1, 6)}
        locations = (await db_session.execute(
            select(Location).where(Location.project_id == test_project.id)
        )).scalars().all()
        assert len(locations) == 1
        assert locations[0].name == "Location 1"

        # Step 4 wrote 5 OUTLINED episodes (mock outline returns 5).
        episodes = (await db_session.execute(
            select(Episode).where(Episode.project_id == test_project.id)
            .order_by(Episode.episode_number)
        )).scalars().all()
        assert len(episodes) == 5
        assert [e.episode_number for e in episodes] == [1, 2, 3, 4, 5]
        assert all(e.status.value == "outlined" for e in episodes)

        # Step 5 wrote 1 video prompt per episode.
        prompts = (await db_session.execute(
            select(Prompt).where(
                Prompt.project_id == test_project.id,
                Prompt.prompt_type == PromptType.VIDEO_GENERATION,
            )
        )).scalars().all()
        assert len(prompts) == 5
        assert {p.episode_id for p in prompts} == {e.id for e in episodes}
        assert all(p.prompt_text for p in prompts)

    @pytest.mark.asyncio
    async def test_get_job(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        created = await _create_job(client, test_project.id, auth_headers)
        job_id = created.json()["id"]
        response = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == job_id
        assert len(response.json()["steps"]) == 5

        missing = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/does-not-exist",
            headers=auth_headers,
        )
        assert missing.status_code == 404

    @pytest.mark.asyncio
    async def test_reuses_existing_bible(
        self, client: AsyncClient, auth_headers, test_project, test_series_bible,
        test_settings_with_mock, db_session
    ):
        response = await _create_job(client, test_project.id, auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        bible_step = next(s for s in data["steps"] if s["step"] == "series_bible")
        assert bible_step["result"]["reused_existing"] is True
        # The hand-filled bible was NOT overwritten by the LLM.
        bible = (await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == test_project.id)
        )).scalar_one()
        assert bible.premise == "A family drama about betrayal and redemption"

    @pytest.mark.asyncio
    async def test_rerun_is_idempotent(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock, db_session
    ):
        first = await _create_job(client, test_project.id, auth_headers)
        assert first.status_code == 201
        assert first.json()["status"] == "completed"

        second = await _create_job(client, test_project.id, auth_headers)
        assert second.status_code == 201
        assert second.json()["status"] == "completed"

        async def count(model):
            return len((await db_session.execute(
                select(model).where(model.project_id == test_project.id)
            )).scalars().all())

        assert await count(Character) == 5
        assert await count(Location) == 1
        assert await count(Episode) == 5
        prompts = (await db_session.execute(
            select(Prompt).where(
                Prompt.project_id == test_project.id,
                Prompt.prompt_type == PromptType.VIDEO_GENERATION,
            )
        )).scalars().all()
        assert len(prompts) == 5

    @pytest.mark.asyncio
    async def test_retry_failed_step_then_continues(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session, monkeypatch
    ):
        import app.api.v1.auto_generate as ag
        from fastapi import HTTPException

        async def boom(*args, **kwargs):
            raise HTTPException(status_code=502, detail="mock world-building down")

        monkeypatch.setattr(ag, "generate_world_building_llm", boom)
        failed = await _create_job(client, test_project.id, auth_headers)
        assert failed.status_code == 201
        data = failed.json()
        assert data["status"] == "failed"
        by_step = {s["step"]: s for s in data["steps"]}
        assert by_step["series_bible"]["status"] == "completed"
        assert by_step["characters"]["status"] == "completed"
        assert by_step["locations"]["status"] == "failed"
        assert "mock world-building down" in by_step["locations"]["error_message"]
        # Later steps never ran.
        assert by_step["episodes"]["status"] == "pending"
        assert by_step["prompts"]["status"] == "pending"

        # Retry of a completed step is rejected; unknown step is rejected.
        job_id = data["id"]
        assert (await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/retry/characters",
            headers=auth_headers,
        )).status_code == 400
        assert (await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/retry/nope",
            headers=auth_headers,
        )).status_code == 400

        monkeypatch.undo()
        retried = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/retry/locations",
            headers=auth_headers,
        )
        assert retried.status_code == 200, retried.text
        data = retried.json()
        assert data["status"] == "completed"
        assert all(s["status"] == "completed" for s in data["steps"])

        # Retry did not duplicate the earlier steps' rows.
        characters = (await db_session.execute(
            select(Character).where(Character.project_id == test_project.id)
        )).scalars().all()
        assert len(characters) == 5
        episodes = (await db_session.execute(
            select(Episode).where(Episode.project_id == test_project.id)
        )).scalars().all()
        assert len(episodes) == 5

    @pytest.mark.asyncio
    async def test_validates_input(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock
    ):
        assert (await _create_job(client, test_project.id, auth_headers, title="")).status_code == 422
        assert (await _create_job(
            client, test_project.id, auth_headers, total_episodes=0)).status_code == 422
        assert (await _create_job(
            client, test_project.id, auth_headers, total_episodes=61)).status_code == 422

    @pytest.mark.asyncio
    async def test_other_users_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2, test_settings_with_mock
    ):
        response = await _create_job(client, test_project2.id, auth_headers)
        assert response.status_code == 404
