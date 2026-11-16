import pytest
from httpx import AsyncClient


class TestLocations:
    @pytest.mark.asyncio
    async def test_create_location(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "Main House",
            "type": "interior",
            "description": "Family living room",
            "atmosphere": "Warm and cozy",
            "time_of_day": "Evening",
            "weather": "Clear"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Main House"
        assert data["type"] == "interior"
        assert data["project_id"] == test_project.id

    @pytest.mark.asyncio
    async def test_list_locations(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "Test Location"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/locations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test Location"

    @pytest.mark.asyncio
    async def test_get_location(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "Get Location"
        }, headers=auth_headers)
        loc_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/locations/{loc_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Location"

    @pytest.mark.asyncio
    async def test_update_location(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "Original Location"
        }, headers=auth_headers)
        loc_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/locations/{loc_id}", json={
            "name": "Updated Location",
            "atmosphere": "New atmosphere"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Location"
        assert data["atmosphere"] == "New atmosphere"

    @pytest.mark.asyncio
    async def test_delete_location(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "To Delete"
        }, headers=auth_headers)
        loc_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/locations/{loc_id}", headers=auth_headers)
        assert response.status_code == 204
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/locations/{loc_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_locations(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/locations", json={
            "name": "User 1 Location"
        }, headers=auth_headers)
        loc_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/locations/{loc_id}", headers=auth_headers2)
        assert response.status_code == 404