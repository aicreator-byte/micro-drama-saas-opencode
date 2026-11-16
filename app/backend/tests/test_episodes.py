import pytest
from httpx import AsyncClient
from app.models.episode import EpisodeStatus, SceneStatus


class TestEpisodes:
    @pytest.mark.asyncio
    async def test_create_episode(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1,
            "title": "Pilot",
            "summary": "The beginning of the story"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["episode_number"] == 1
        assert data["title"] == "Pilot"
        assert data["status"] == "planned"

    @pytest.mark.asyncio
    async def test_create_duplicate_episode_number(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1,
            "title": "First"
        }, headers=auth_headers)
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1,
            "title": "Duplicate"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_episodes(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1,
            "title": "Ep 1"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/episodes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["episode_number"] == 1

    @pytest.mark.asyncio
    async def test_get_episode(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 2,
            "title": "Episode 2"
        }, headers=auth_headers)
        ep_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Episode 2"

    @pytest.mark.asyncio
    async def test_update_episode(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 3,
            "title": "Original Title"
        }, headers=auth_headers)
        ep_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}", json={
            "title": "Updated Title",
            "status": "in_production"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "in_production"

    @pytest.mark.asyncio
    async def test_delete_episode(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 4,
            "title": "To Delete"
        }, headers=auth_headers)
        ep_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}", headers=auth_headers)
        assert response.status_code == 204
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_scene(self, client: AsyncClient, auth_headers, test_project):
        # Create episode first
        ep_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1
        }, headers=auth_headers)
        ep_id = ep_response.json()["id"]
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes", json={
            "scene_number": 1,
            "title": "Opening Scene",
            "description": "The story begins"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["scene_number"] == 1
        assert data["title"] == "Opening Scene"

    @pytest.mark.asyncio
    async def test_list_scenes(self, client: AsyncClient, auth_headers, test_project):
        ep_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1
        }, headers=auth_headers)
        ep_id = ep_response.json()["id"]
        
        await client.post(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes", json={
            "scene_number": 1
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_update_scene(self, client: AsyncClient, auth_headers, test_project):
        ep_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1
        }, headers=auth_headers)
        ep_id = ep_response.json()["id"]
        
        scene_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes", json={
            "scene_number": 1,
            "title": "Original Scene"
        }, headers=auth_headers)
        scene_id = scene_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes/{scene_id}", json={
            "title": "Updated Scene",
            "status": "written"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Scene"
        assert data["status"] == "written"

    @pytest.mark.asyncio
    async def test_delete_scene(self, client: AsyncClient, auth_headers, test_project):
        ep_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1
        }, headers=auth_headers)
        ep_id = ep_response.json()["id"]
        
        scene_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes", json={
            "scene_number": 1
        }, headers=auth_headers)
        scene_id = scene_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}/scenes/{scene_id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_tenant_isolation_episodes(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        ep_response = await client.post(f"/api/v1/projects/{test_project.id}/episodes", json={
            "episode_number": 1
        }, headers=auth_headers)
        ep_id = ep_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/episodes/{ep_id}", headers=auth_headers2)
        assert response.status_code == 404