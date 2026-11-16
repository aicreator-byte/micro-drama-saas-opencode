import pytest
from httpx import AsyncClient
from app.models.prompt import PromptType, PromptStatus


class TestPrompts:
    @pytest.mark.asyncio
    async def test_create_prompt(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "title": "Character Prompt",
            "prompt_text": "A portrait of a brave detective",
            "negative_prompt": "blurry, low quality"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["prompt_type"] == "character_image"
        assert data["title"] == "Character Prompt"
        assert data["prompt_text"] == "A portrait of a brave detective"

    @pytest.mark.asyncio
    async def test_list_prompts(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "scene_image",
            "prompt_text": "Test prompt"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/prompts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_prompt(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "video_generation",
            "prompt_text": "Template"
        }, headers=auth_headers)
        prompt_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/prompts/{prompt_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["prompt_type"] == "video_generation"

    @pytest.mark.asyncio
    async def test_update_prompt(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "title": "Original",
            "prompt_text": "Original template"
        }, headers=auth_headers)
        prompt_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/projects/{test_project.id}/prompts/{prompt_id}", json={
            "title": "Updated",
            "prompt_text": "Updated template"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["prompt_text"] == "Updated template"
        assert data["version"] == 2

    @pytest.mark.asyncio
    async def test_delete_prompt(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "prompt_text": "Template"
        }, headers=auth_headers)
        prompt_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/projects/{test_project.id}/prompts/{prompt_id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_use_prompt(self, client: AsyncClient, auth_headers, test_project):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "prompt_text": "Test prompt"
        }, headers=auth_headers)
        prompt_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/projects/{test_project.id}/prompts/{prompt_id}/use", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["times_used"] == 1
        assert data["status"] == "used"

    @pytest.mark.asyncio
    async def test_filter_prompts_by_type(self, client: AsyncClient, auth_headers, test_project):
        await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "prompt_text": "Character prompt"
        }, headers=auth_headers)
        await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "location_image",
            "prompt_text": "Location prompt"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/prompts?prompt_type=character_image", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for prompt in data:
            assert prompt["prompt_type"] == "character_image"

    @pytest.mark.asyncio
    async def test_tenant_isolation_prompts(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        create_response = await client.post(f"/api/v1/projects/{test_project.id}/prompts", json={
            "prompt_type": "character_image",
            "prompt_text": "User 1 prompt"
        }, headers=auth_headers)
        prompt_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/prompts/{prompt_id}", headers=auth_headers2)
        assert response.status_code == 404