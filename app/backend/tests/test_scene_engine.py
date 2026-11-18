import pytest
from httpx import AsyncClient
from app.models.scene_engine import SceneEngineTaskType, SceneEngineTaskStatus


class TestSceneEngine:
    @pytest.mark.asyncio
    async def test_create_breakdown_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode",
            "parameters": {"total_scenes": 8}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "breakdown_episode"
        assert data["status"] == "pending"
        assert data["project_id"] == test_project.id
        assert data["episode_id"] == test_episode.id

    @pytest.mark.asyncio
    async def test_execute_breakdown_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode",
            "parameters": {"total_scenes": 5}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["output"] is not None
        assert "scenes" in data["output"]
        assert len(data["output"]["scenes"]) == 5

    @pytest.mark.asyncio
    async def test_create_shots_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene, test_settings_with_mock):
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "scene_id": test_scene.id,
            "task_type": "generate_shots",
            "parameters": {"total_shots": 10}
        }, headers=auth_headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        execute_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert execute_response.status_code == 200
        data = execute_response.json()
        assert data["status"] == "completed"
        assert "shots" in data["output"]
        assert len(data["output"]["shots"]) == 10

    @pytest.mark.asyncio
    async def test_create_dialogue_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene, test_settings_with_mock):
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "scene_id": test_scene.id,
            "task_type": "generate_dialogue"
        }, headers=auth_headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        execute_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert execute_response.status_code == 200
        data = execute_response.json()
        assert data["status"] == "completed"
        assert "dialogue_blocks" in data["output"]

    @pytest.mark.asyncio
    async def test_create_action_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene, test_settings_with_mock):
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "scene_id": test_scene.id,
            "task_type": "generate_action"
        }, headers=auth_headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        execute_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert execute_response.status_code == 200
        data = execute_response.json()
        assert data["status"] == "completed"
        assert "action_beats" in data["output"]

    @pytest.mark.asyncio
    async def test_list_scene_tasks(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "breakdown_episode"

    @pytest.mark.asyncio
    async def test_refine_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode",
            "parameters": {"total_scenes": 3}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # Execute first
        await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute", headers=auth_headers)
        
        # Now refine
        response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/refine", json={
            "feedback": "Add more conflict",
            "refine_type": "conflict"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "refined_output" in data

    @pytest.mark.asyncio
    async def test_tenant_isolation_scene_engine(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2, test_episode, test_settings_with_mock):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # User 2 should not access it
        response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}", headers=auth_headers2)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_settings_with_mock):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 404

class TestSceneEngineWithCharacter:
    """Audit F-03: dialogue/action generation crashed (AttributeError
    voice_pattern / physical_traits) whenever the project had characters."""

    @pytest.mark.asyncio
    async def test_execute_dialogue_with_character(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        test_scene, test_settings_with_mock
    ):
        create = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "Nadia", "role": "protagonist",
            "voice_pattern": "Soft, measured, warm",
            "physical_traits": "Tall, graceful, dark hair",
            "skills": ["martial arts", "negotiation"],
        }, headers=auth_headers)
        assert create.status_code == 201, create.text
        assert create.json()["voice_pattern"] == "Soft, measured, warm"
        assert create.json()["physical_traits"] == "Tall, graceful, dark hair"

        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "scene_id": test_scene.id,
            "task_type": "generate_dialogue",
        }, headers=auth_headers)
        task_id = task.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"
        assert "dialogue_blocks" in response.json()["output"]

    @pytest.mark.asyncio
    async def test_execute_action_with_character(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        test_scene, test_character, test_settings_with_mock
    ):
        # test_character fixture has no voice/physical fields (None) — the
        # prompt must still work via the 'Not specified' fallback.
        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "scene_id": test_scene.id,
            "task_type": "generate_action",
        }, headers=auth_headers)
        task_id = task.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"
        assert "action_beats" in response.json()["output"]

    @pytest.mark.asyncio
    async def test_generate_scenes_task_type(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        test_settings_with_mock
    ):
        """GENERATE_SCENES had no execute branch (same class of bug as F-18)."""
        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "task_type": "generate_scenes",
            "parameters": {"total_scenes": 3},
        }, headers=auth_headers)
        task_id = task.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"
        assert "scenes" in response.json()["output"]


class TestSceneEngineFailure:
    """Audit F-08: a failed execute left the task PROCESSING forever."""

    @pytest.mark.asyncio
    async def test_failed_execute_marks_failed_and_is_retryable(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        db_session
    ):
        # Settings with a real (nvidia) provider whose key env var does not
        # exist -> LLM fails deterministically with 502, no network involved.
        from app.models.settings import AppSettings
        db_session.add(AppSettings(ai_providers=[{
            "id": "nvidia-test", "provider": "nvidia",
            "model": "nvidia/nemotron-3-ultra-550b-a55b",
            "key_env": "DEFINITELY_MISSING_KEY_XYZ",
            "enabled": True, "priority": 1,
        }]))
        await db_session.commit()

        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "task_type": "breakdown_episode",
        }, headers=auth_headers)
        task_id = task.json()["id"]

        first = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert first.status_code == 502, first.text

        after = await client.get(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}",
            headers=auth_headers)
        assert after.json()["status"] == "failed"
        assert after.json()["error_message"]
        assert after.json()["completed_at"] is not None

        # Retry must be possible: NOT 400 "Task already processing".
        second = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert second.status_code == 502
        again = await client.get(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}",
            headers=auth_headers)
        assert again.json()["status"] == "failed"


class TestSceneEngineApply:
    """Audit F-19: generated output must materialize into rows."""

    @pytest.mark.asyncio
    async def test_apply_breakdown_creates_scenes(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        test_settings_with_mock
    ):
        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "task_type": "breakdown_episode",
            "parameters": {"total_scenes": 5},
        }, headers=auth_headers)
        task_id = task.json()["id"]
        executed = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        assert executed.json()["status"] == "completed"

        applied = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/apply",
            headers=auth_headers)
        assert applied.status_code == 200, applied.text
        assert len(applied.json()["created"]["scenes"]) == 5

        scenes = await client.get(
            f"/api/v1/projects/{test_project.id}/episodes/{test_episode.id}/scenes",
            headers=auth_headers)
        assert len(scenes.json()) == 5

        # Second apply skips existing scenes, never duplicates.
        again = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/apply",
            headers=auth_headers)
        assert again.json()["created"]["scenes"] == []
        assert len(again.json()["skipped"]) == 5

    @pytest.mark.asyncio
    async def test_apply_dialogue_creates_dialogue_rows(
        self, client: AsyncClient, auth_headers, test_project, test_episode,
        test_scene, test_settings_with_mock
    ):
        task = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id, "scene_id": test_scene.id,
            "task_type": "generate_dialogue",
        }, headers=auth_headers)
        task_id = task.json()["id"]
        await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/execute",
            headers=auth_headers)
        applied = await client.post(
            f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}/apply",
            headers=auth_headers)
        assert applied.status_code == 200, applied.text
        assert len(applied.json()["created"]["dialogues"]) == 2

        rows = await client.get(
            f"/api/v1/projects/{test_project.id}/episodes/{test_episode.id}/scenes/{test_scene.id}/dialogues",
            headers=auth_headers)
        assert rows.status_code == 200
        assert len(rows.json()) == 2
        assert rows.json()[0]["dialogue_text"] == "Line 1"
