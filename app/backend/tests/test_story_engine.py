import pytest
from httpx import AsyncClient
from app.models.story_engine import StoryEngineTaskType, StoryEngineTaskStatus


class TestStoryEngine:
    @pytest.mark.asyncio
    async def test_create_story_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline",
            "parameters": {"total_episodes": 20}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "generate_outline"
        assert data["status"] == "pending"
        assert data["project_id"] == test_project.id
        assert data["series_bible_id"] == test_series_bible.id

    @pytest.mark.asyncio
    async def test_execute_story_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline",
            "parameters": {"total_episodes": 5}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["output"] is not None
        assert "episodes" in data["output"]
        assert len(data["output"]["episodes"]) == 5

    @pytest.mark.asyncio
    async def test_create_character_arcs_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible, test_character):
        response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_character_arcs"
        }, headers=auth_headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        execute_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert execute_response.status_code == 200
        data = execute_response.json()
        assert data["status"] == "completed"
        assert "arcs" in data["output"]
        assert len(data["output"]["arcs"]) >= 1

    @pytest.mark.asyncio
    async def test_create_world_building_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible, test_location):
        response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_world_building"
        }, headers=auth_headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        execute_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}/execute", headers=auth_headers)
        assert execute_response.status_code == 200
        data = execute_response.json()
        assert data["status"] == "completed"
        assert "locations" in data["output"]
        assert "factions" in data["output"]

    @pytest.mark.asyncio
    async def test_list_story_tasks(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/story-engine/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_story_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "generate_outline"

    @pytest.mark.asyncio
    async def test_refine_story_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline",
            "parameters": {"total_episodes": 3}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # Execute first
        await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}/execute", headers=auth_headers)
        
        # Now refine
        response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}/refine", json={
            "feedback": "Make it darker",
            "refine_type": "tone"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "refined_output" in data

    @pytest.mark.asyncio
    async def test_tenant_isolation_story_engine(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2, test_series_bible):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # User 2 should not access it
        response = await client.get(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}", headers=auth_headers2)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_story_task(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/story-engine/tasks", json={
            "series_bible_id": test_series_bible.id,
            "task_type": "generate_outline"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/projects/{test_project.id}/story-engine/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 404