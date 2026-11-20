import pytest
from httpx import AsyncClient
from app.models.flow_bridge import FlowBridgeTaskStatus


class TestFlowBridge:
    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task",
            "task_type": "video_generation",
            "input_prompts": {"main": "Generate a video of a sunset"},
            "input_parameters": {"duration": 10, "resolution": "1920x1080"}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "video_generation"
        assert data["status"] == "pending"
        assert data["project_id"] == test_project.id

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task 2",
            "task_type": "image_generation",
            "input_prompts": {"main": "Test prompt"}
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task 3",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "video_generation"

    @pytest.mark.asyncio
    async def test_update_task_status(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task 4",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/tasks/{task_id}", json={
            "status": "generating"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"

    @pytest.mark.asyncio
    async def test_create_asset(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task 5",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/tasks/{task_id}/assets", json={
            "asset_type": "video_clip",
            "title": "Generated Video",
            "file_path": "/uploads/video.mp4",
            "file_size": 1024000,
            "mime_type": "video/mp4"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["asset_type"] == "video_clip"
        assert data["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_list_assets(self, client: AsyncClient, auth_headers, test_project):
        task_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task 6",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = task_response.json()["id"]
        
        await client.post(f"/api/v1/projects/{test_project.id}/tasks/{task_id}/assets", json={
            "asset_type": "video_clip",
            "title": "Video 1",
            "file_path": "/uploads/video1.mp4"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/tasks/{task_id}/assets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_tenant_isolation_flow_bridge(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "User 1 Task",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # User 2 should not access it
        response = await client.get(f"/api/v1/projects/{test_project.id}/tasks/{task_id}", headers=auth_headers2)
        assert response.status_code == 404
    @pytest.mark.asyncio
    async def test_list_project_flow_assets_moved_path(self, client: AsyncClient, auth_headers, test_project):
        """Round 2: the FlowBridge project-assets list moved from
        GET /projects/{id}/assets to /flow-assets, because /assets is
        now the generic Asset Management list (assets.py). Both must
        stay alive: FlowBridge list here, generic list empty (200)."""
        task_response = await client.post(f"/api/v1/projects/{test_project.id}/tasks", json={
            "title": "Test Task flow-assets",
            "task_type": "video_generation",
            "input_prompts": {"main": "Test"}
        }, headers=auth_headers)
        task_id = task_response.json()["id"]
        await client.post(f"/api/v1/projects/{test_project.id}/tasks/{task_id}/assets", json={
            "asset_type": "video_clip",
            "title": "Video flow-assets",
            "file_path": "/uploads/video-flow.mp4"
        }, headers=auth_headers)

        response = await client.get(f"/api/v1/projects/{test_project.id}/flow-assets", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) >= 1
        assert any(a["title"] == "Video flow-assets" for a in data)

        generic = await client.get(f"/api/v1/projects/{test_project.id}/assets", headers=auth_headers)
        assert generic.status_code == 200, generic.text
        assert generic.json() == []
