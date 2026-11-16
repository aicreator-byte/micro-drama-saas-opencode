import pytest
from httpx import AsyncClient


class TestSeriesBible:
    @pytest.mark.asyncio
    async def test_create_series_bible(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "A family drama about secrets and lies",
            "main_plot": "The main character discovers a dark family secret",
            "subplots": ["Romance subplot", "Business rivalry"],
            "character_relationships": "Complex family dynamics",
            "world_settings": "Modern day suburban town",
            "tone_and_visual_style": "Dark and moody",
            "ending_direction": "Bittersweet resolution",
            "episode_structure": "20 episodes, 3 acts"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["premise"] == "A family drama about secrets and lies"
        assert data["project_id"] == test_project.id

    @pytest.mark.asyncio
    async def test_create_duplicate_series_bible(self, client: AsyncClient, auth_headers, test_project):
        # Create first
        await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "First bible"
        }, headers=auth_headers)
        
        # Try to create second
        response = await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "Second bible"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_bible(self, client: AsyncClient, auth_headers, test_project):
        # Create first
        await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "Test premise"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/series-bible", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["premise"] == "Test premise"

    @pytest.mark.asyncio
    async def test_get_series_bible_not_found(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get(f"/api/v1/projects/{test_project.id}/series-bible", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_series_bible(self, client: AsyncClient, auth_headers, test_project):
        # Create first
        await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "Original premise"
        }, headers=auth_headers)
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "Updated premise",
            "main_plot": "New main plot"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["premise"] == "Updated premise"
        assert data["main_plot"] == "New main plot"

    @pytest.mark.asyncio
    async def test_delete_series_bible(self, client: AsyncClient, auth_headers, test_project):
        # Create first
        await client.post(f"/api/v1/projects/{test_project.id}/series-bible", json={
            "premise": "To be deleted"
        }, headers=auth_headers)
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/series-bible", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deleted
        response = await client.get(f"/api/v1/projects/{test_project.id}/series-bible", headers=auth_headers)
        assert response.status_code == 404