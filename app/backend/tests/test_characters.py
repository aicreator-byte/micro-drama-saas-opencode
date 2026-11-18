import pytest
from httpx import AsyncClient


class TestCharacters:
    @pytest.mark.asyncio
    async def test_create_character(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "John Doe",
            "role": "protagonist",
            "age": "30",
            "gender": "Male",
            "hair_color": "Brown",
            "eye_color": "Blue",
            "personality_traits": ["brave", "loyal", "determined"],
            "background": "Former detective",
            "motivations": "Justice for his family"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["role"] == "protagonist"
        assert data["project_id"] == test_project.id

    @pytest.mark.asyncio
    async def test_create_more_than_six_characters(self, client: AsyncClient, auth_headers, test_project):
        # Create 7 characters (no limit enforced)
        for i in range(7):
            response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
                "name": f"Character {i+1}",
                "role": "supporting"
            }, headers=auth_headers)
            assert response.status_code == 201
        
        # All 7 should succeed
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7

    @pytest.mark.asyncio
    async def test_list_characters(self, client: AsyncClient, auth_headers, test_project):
        # Create a character first
        await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "Test Character"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test Character"

    @pytest.mark.asyncio
    async def test_get_character(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "Get Character"
        }, headers=auth_headers)
        char_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters/{char_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Character"

    @pytest.mark.asyncio
    async def test_update_character(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "Original Name"
        }, headers=auth_headers)
        char_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/characters/{char_id}", json={
            "name": "Updated Name",
            "age": "35"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["age"] == "35"

    @pytest.mark.asyncio
    async def test_delete_character(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "To Delete"
        }, headers=auth_headers)
        char_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/characters/{char_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deleted
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters/{char_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_characters(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        # Create character in project 1
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "User 1 Character"
        }, headers=auth_headers)
        char_id = create_response.json()["id"]
        
        # User 2 should not access it
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters/{char_id}", headers=auth_headers2)
        assert response.status_code == 404
        
        # User 2 should not see it in list
        response = await client.get(f"/api/v1/projects/{test_project.id}/characters", headers=auth_headers2)
        assert response.status_code == 404

class TestCharacterNewFields:
    """Audit F-03: voice_pattern / physical_traits / skills must exist."""

    @pytest.mark.asyncio
    async def test_create_character_with_voice_and_physical_traits(
        self, client: AsyncClient, auth_headers, test_project
    ):
        response = await client.post(f"/api/v1/projects/{test_project.id}/characters", json={
            "name": "Nadia", "role": "protagonist",
            "voice_pattern": "Soft, measured, warm",
            "physical_traits": "Tall, graceful, dark hair",
            "skills": ["martial arts", "negotiation"],
        }, headers=auth_headers)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["voice_pattern"] == "Soft, measured, warm"
        assert data["physical_traits"] == "Tall, graceful, dark hair"

        # Round-trip via GET
        get_response = await client.get(
            f"/api/v1/projects/{test_project.id}/characters/{data['id']}",
            headers=auth_headers)
        assert get_response.json()["voice_pattern"] == "Soft, measured, warm"

        # PATCH the new fields
        patch = await client.patch(
            f"/api/v1/projects/{test_project.id}/characters/{data['id']}", json={
                "voice_pattern": "Cold, clipped, confident",
                "skills": ["driving"],
            }, headers=auth_headers)
        assert patch.status_code == 200, patch.text
        assert patch.json()["voice_pattern"] == "Cold, clipped, confident"
