import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode, EpisodeStatus
from app.models.project import Project
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


async def _wait_for_job(client, project_id, job_id, headers, timeout=30.0):
    """Poll GET until the job reaches a terminal status.

    Jobs run async in a background task; the POST only proves the job was
    created. Transient non-200s (the test engine shares one in-memory
    connection between the request session and the background session)
    are retried, not treated as failures.
    """
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


class TestAutoGenerate:
    @pytest.mark.asyncio
    async def test_create_job_completes_all_steps(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock, db_session
    ):
        response = await _create_job(client, test_project.id, auth_headers)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["title"] == "THE BILLIONAIRE CEO"
        assert len(data["steps"]) == 5
        assert [s["step"] for s in data["steps"]] == [
            "series_bible", "characters", "locations", "episodes", "prompts",
        ]

        # Async: POST only creates the job; the steps finish in the background.
        data = await _wait_for_job(client, test_project.id, data["id"], auth_headers)
        assert data["status"] == "completed"
        assert all(s["status"] == "completed" for s in data["steps"])

        # Step 1 wrote the bible (mock provider).
        bible = (await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == test_project.id)
        )).scalar_one()
        assert bible.premise == "Mock premise for the series"

        # Step 2 wrote 5 characters, step 3 wrote 3 locations (mock world).
        characters = (await db_session.execute(
            select(Character).where(Character.project_id == test_project.id)
        )).scalars().all()
        assert len(characters) == 5
        assert {c.name for c in characters} == {f"Mock Character {i}" for i in range(1, 6)}
        locations = (await db_session.execute(
            select(Location).where(Location.project_id == test_project.id)
        )).scalars().all()
        assert len(locations) == 3
        assert {loc.name for loc in locations} == {"Location 1", "Location 2", "Location 3"}

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
    async def test_post_returns_immediately_while_job_runs(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        monkeypatch
    ):
        """POST must not block on the 5 steps: with the first LLM call
        slowed to 1s, the response must already be back with status running."""
        import app.api.v1.auto_generate as ag

        orig = ag._chat_json

        async def slow_chat(db, prompt, max_tokens=8000):
            if "create a complete series bible" in prompt.lower():
                await asyncio.sleep(1.0)
            return await orig(db, prompt, max_tokens=max_tokens)

        monkeypatch.setattr(ag, "_chat_json", slow_chat)
        response = await _create_job(client, test_project.id, auth_headers)
        assert response.status_code == 201, response.text
        data = response.json()
        # The job cannot have finished: its first LLM call is still sleeping.
        assert data["status"] == "running"
        # ...but it does finish when polled.
        data = await _wait_for_job(client, test_project.id, data["id"], auth_headers)
        assert data["status"] == "completed"

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
        data = await _wait_for_job(client, test_project.id, response.json()["id"], auth_headers)
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
        data = await _wait_for_job(client, test_project.id, first.json()["id"], auth_headers)
        assert data["status"] == "completed"

        second = await _create_job(client, test_project.id, auth_headers)
        assert second.status_code == 201
        data = await _wait_for_job(client, test_project.id, second.json()["id"], auth_headers)
        assert data["status"] == "completed"

        async def count(model):
            return len((await db_session.execute(
                select(model).where(model.project_id == test_project.id)
            )).scalars().all())

        assert await count(Character) == 5
        assert await count(Location) == 3
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
        job_id = failed.json()["id"]
        data = await _wait_for_job(client, test_project.id, job_id, auth_headers)
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
        data = await _wait_for_job(client, test_project.id, job_id, auth_headers)
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
        # A title of only spaces is not a title (audit P2-OC-3).
        assert (await _create_job(client, test_project.id, auth_headers, title="   ")).status_code == 422
        assert (await _create_job(
            client, test_project.id, auth_headers, total_episodes=0)).status_code == 422
        assert (await _create_job(
            client, test_project.id, auth_headers, total_episodes=61)).status_code == 422

    @pytest.mark.asyncio
    async def test_request_schema_strips_title_and_blank_genre(self):
        from app.schemas.auto_generate import AutoGenerateCreateRequest

        req = AutoGenerateCreateRequest(title="  THE BILLIONAIRE CEO  ", genre="   ")
        assert req.title == "THE BILLIONAIRE CEO"
        assert req.genre is None

    @pytest.mark.asyncio
    async def test_job_does_not_overwrite_project_header(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session
    ):
        """Audit O7: the job input lives on the job, never on the project —
        a job (even a failed one) must not change the project header."""
        before = (await db_session.execute(
            select(Project).where(Project.id == test_project.id)
        )).scalar_one()
        assert (before.title, before.genre, before.total_episodes) == (
            "Test Project", "Drama", 20)

        created = await _create_job(
            client, test_project.id, auth_headers,
            title="A Totally Different Title", genre="Thriller", total_episodes=5)
        assert created.status_code == 201, created.text
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "completed"
        assert data["title"] == "A Totally Different Title"
        assert data["genre"] == "Thriller"

        after = (await db_session.execute(
            select(Project).where(Project.id == test_project.id)
        )).scalar_one()
        assert (after.title, after.genre, after.total_episodes) == (
            "Test Project", "Drama", 20)

    @pytest.mark.asyncio
    async def test_genre_inferred_from_title_when_missing(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session
    ):
        """No silent 'drama' default: with no genre given, step 1 asks the
        LLM to infer it from the title (mock returns 'Romance')."""
        body = {
            "title": "THE BILLIONAIRE CEO",
            "total_episodes": 5,
            "premise": "A struggling young woman marries a cold billionaire CEO.",
        }
        created = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate",
            json=body, headers=auth_headers)
        assert created.status_code == 201, created.text
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "completed"
        assert data["genre"] == "Romance"
        bible_step = next(s for s in data["steps"] if s["step"] == "series_bible")
        assert bible_step["result"]["genre_inferred"] is True
        assert bible_step["result"]["genre"] == "Romance"
        # The project header is untouched by the inference too.
        project = (await db_session.execute(
            select(Project).where(Project.id == test_project.id)
        )).scalar_one()
        assert project.genre == "Drama"

    @pytest.mark.asyncio
    async def test_characters_step_fails_below_minimum(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session, monkeypatch
    ):
        """Spec §9.1 (audit O5): 2 usable characters < minimum 4 → step
        FAILS, and the partial rows are rolled back, not left behind."""
        import app.api.v1.auto_generate as ag

        orig = ag._chat_json

        async def two_characters(db, prompt, max_tokens=8000):
            if "create the main cast" in prompt.lower():
                return {"characters": [
                    {"name": "Fake One", "role": "protagonist"},
                    {"name": "Fake Two", "role": "supporting"},
                ]}
            return await orig(db, prompt, max_tokens=max_tokens)

        monkeypatch.setattr(ag, "_chat_json", two_characters)
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "failed"
        by_step = {s["step"]: s for s in data["steps"]}
        assert by_step["characters"]["status"] == "failed"
        assert "minimum is 4" in by_step["characters"]["error_message"]
        assert by_step["locations"]["status"] == "pending"
        characters = (await db_session.execute(
            select(Character).where(Character.project_id == test_project.id)
        )).scalars().all()
        assert len(characters) == 0

    @pytest.mark.asyncio
    async def test_locations_step_fails_below_minimum(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session, monkeypatch
    ):
        """Spec §9.1 (audit O5): 2 usable locations < minimum 3 → step
        FAILS, and the partial rows are rolled back, not left behind."""
        import app.api.v1.auto_generate as ag

        async def two_locations(db, project_id, bible):
            return {"locations": [
                {"name": "Fake Place 1", "type": "urban", "description": "x"},
                {"name": "Fake Place 2", "type": "rural", "description": "x"},
            ]}

        monkeypatch.setattr(ag, "generate_world_building_llm", two_locations)
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "failed"
        by_step = {s["step"]: s for s in data["steps"]}
        assert by_step["locations"]["status"] == "failed"
        assert "minimum is 3" in by_step["locations"]["error_message"]
        assert by_step["episodes"]["status"] == "pending"
        locations = (await db_session.execute(
            select(Location).where(Location.project_id == test_project.id)
        )).scalars().all()
        assert len(locations) == 0

    @pytest.mark.asyncio
    async def test_prompts_step_fails_without_full_coverage(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session, monkeypatch
    ):
        """Audit O3: the prompts step FAILS when the LLM covers only 4 of 5
        episodes — no partial insert, retry the step."""
        import app.api.v1.auto_generate as ag

        orig = ag._chat_json

        async def drop_episode_five(db, prompt, max_tokens=8000):
            out = await orig(db, prompt, max_tokens=max_tokens)
            if "write one video generation prompt" in prompt.lower():
                out = dict(out)
                out["prompts"] = [
                    p for p in out.get("prompts", [])
                    if p.get("episode_number") != 5
                ]
            return out

        monkeypatch.setattr(ag, "_chat_json", drop_episode_five)
        created = await _create_job(client, test_project.id, auth_headers)
        assert created.status_code == 201
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "failed"
        by_step = {s["step"]: s for s in data["steps"]}
        assert by_step["prompts"]["status"] == "failed"
        assert "missing video prompts for episode(s): [5]" in by_step["prompts"]["error_message"]
        prompts = (await db_session.execute(
            select(Prompt).where(
                Prompt.project_id == test_project.id,
                Prompt.prompt_type == PromptType.VIDEO_GENERATION,
            )
        )).scalars().all()
        assert len(prompts) == 0

    @pytest.mark.asyncio
    async def test_prompts_are_chunked_per_five_episodes(
        self, client: AsyncClient, auth_headers, test_project, test_settings_with_mock,
        db_session, monkeypatch
    ):
        """Audit O4: 7 episodes must take 2 LLM calls (5 + 2), never one
        call for all of them — and all 7 prompts must be written."""
        import app.api.v1.auto_generate as ag

        for number in range(1, 8):
            db_session.add(Episode(
                project_id=test_project.id,
                episode_number=number,
                title=f"Episode {number}",
                summary=f"Summary {number}",
                status=EpisodeStatus.OUTLINED,
            ))
        await db_session.commit()

        orig = ag._chat_json
        calls = {"video_prompts": 0}

        async def counting_chat(db, prompt, max_tokens=8000):
            if "write one video generation prompt" in prompt.lower():
                calls["video_prompts"] += 1
            return await orig(db, prompt, max_tokens=max_tokens)

        monkeypatch.setattr(ag, "_chat_json", counting_chat)
        created = await _create_job(
            client, test_project.id, auth_headers, total_episodes=7)
        assert created.status_code == 201, created.text
        data = await _wait_for_job(client, test_project.id, created.json()["id"], auth_headers)
        assert data["status"] == "completed"
        assert calls["video_prompts"] == 2
        prompts = (await db_session.execute(
            select(Prompt).where(
                Prompt.project_id == test_project.id,
                Prompt.prompt_type == PromptType.VIDEO_GENERATION,
            )
        )).scalars().all()
        assert len(prompts) == 7

    @pytest.mark.asyncio
    async def test_other_users_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2, test_settings_with_mock
    ):
        response = await _create_job(client, test_project2.id, auth_headers)
        assert response.status_code == 404
