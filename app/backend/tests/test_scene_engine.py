import pytest
from httpx import AsyncClient
from app.models.scene_engine import SceneEngineTaskType, SceneEngineTaskStatus


class TestSceneEngine:
    @pytest.mark.asyncio
    async def test_create_breakdown_task(self, client: AsyncClient, auth_headers, test_project, test_episode):
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
    async def test_execute_breakdown_task(self, client: AsyncClient, auth_headers, test_project, test_episode):
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
    async def test_create_shots_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene):
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
    async def test_create_dialogue_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene):
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
    async def test_create_action_task(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene):
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
    async def test_list_scene_tasks(self, client: AsyncClient, auth_headers, test_project, test_episode):
        await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode):
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
    async def test_refine_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode):
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
    async def test_tenant_isolation_scene_engine(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2, test_episode):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/scene-engine/tasks", json={
            "episode_id": test_episode.id,
            "task_type": "breakdown_episode"
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # User 2 should not access it
        response = await client.get(f"/api/v1/projects/{test_project.id}/scene-engine/tasks/{task_id}", headers=auth_headers2)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_scene_task(self, client: AsyncClient, auth_headers, test_project, test_episode):
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