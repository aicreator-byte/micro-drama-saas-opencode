import pytest
from httpx import AsyncClient
from app.models.project import ProjectStatus


class TestProjects:
    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/projects", json={
            "title": "New Project",
            "description": "Project description",
            "genre": "Thriller",
            "themes": ["mystery", "suspense"],
            "total_episodes": 15
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Project"
        assert data["genre"] == "Thriller"
        assert data["themes"] == ["mystery", "suspense"]
        assert data["total_episodes"] == 15
        assert data["status"] == "draft"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["projects"]) >= 1
        project = data["projects"][0]
        assert project["title"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get(f"/api/v1/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project.id
        assert data["title"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/projects/non-existent-id", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient, auth_headers, test_project):
        response = await client.patch(f"/api/v1/projects/{test_project.id}", json={
            "title": "Updated Title",
            "status": "in_progress",
            "genre": "Updated Genre"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "in_progress"
        assert data["genre"] == "Updated Genre"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient, auth_headers, test_project):
        response = await client.delete(f"/api/v1/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deleted
        response = await client.get(f"/api/v1/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_projects(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        # User 1 should not see User 2's project
        response = await client.get(f"/api/v1/projects/{test_project2.id}", headers=auth_headers)
        assert response.status_code == 404
        
        # User 2 should not see User 1's project
        response = await client.get(f"/api/v1/projects/{test_project.id}", headers=auth_headers2)
        assert response.status_code == 404
        
        # User 1 should only see their own projects
        response = await client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        project_ids = [p["id"] for p in data["projects"]]
        assert test_project.id in project_ids
        assert test_project2.id not in project_ids
        
        # User 2 should only see their own projects
        response = await client.get("/api/v1/projects", headers=auth_headers2)
        assert response.status_code == 200
        data = response.json()
        project_ids = [p["id"] for p in data["projects"]]
        assert test_project2.id in project_ids
        assert test_project.id not in project_ids

    @pytest.mark.asyncio
    async def test_project_filter_by_status(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get("/api/v1/projects?status=draft", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for project in data["projects"]:
            assert project["status"] == "draft"

    @pytest.mark.asyncio
    async def test_project_search(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get("/api/v1/projects?search=Test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) >= 1
        for project in data["projects"]:
            assert "test" in project["title"].lower() or "test" in (project["description"] or "").lower()