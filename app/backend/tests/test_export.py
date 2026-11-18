import pytest
from httpx import AsyncClient
from app.schemas.export import ExportFormat, ExportType


class TestExport:
    @pytest.mark.asyncio
    async def test_export_project(self, client: AsyncClient, auth_headers, test_project, test_series_bible, test_character, test_location, test_episode):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "project",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "project"
        assert data["format"] == "json"
        assert data["status"] == "completed"
        assert data["file_url"] is not None
        assert data["file_size"] > 0

    @pytest.mark.asyncio
    async def test_export_full_project(self, client: AsyncClient, auth_headers, test_project, test_series_bible, test_character, test_location, test_episode):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "full_project",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "full_project"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_episode(self, client: AsyncClient, auth_headers, test_project, test_episode):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "episode",
            "format": "json",
            "episode_id": test_episode.id
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "episode"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_prompts(self, client: AsyncClient, auth_headers, test_project, test_prompt):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "prompts",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "prompts"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_series_bible(self, client: AsyncClient, auth_headers, test_project, test_series_bible):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "series_bible",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "series_bible"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_characters(self, client: AsyncClient, auth_headers, test_project, test_character):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "characters",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "characters"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_locations(self, client: AsyncClient, auth_headers, test_project, test_location):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "locations",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "locations"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_scenes(self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "scenes",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["export_type"] == "scenes"
        assert data["format"] == "json"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_markdown_format(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "project",
            "format": "markdown"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "markdown"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_txt_format(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "project",
            "format": "txt"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "txt"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_exports(self, client: AsyncClient, auth_headers, test_project):
        # Create an export first
        await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "project",
            "format": "json"
        }, headers=auth_headers)
        
        response = await client.get(f"/api/v1/projects/{test_project.id}/export/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_quick_export_project(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get(f"/api/v1/projects/{test_project.id}/export/project?format=json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["export_type"] == "full_project"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_quick_export_episode(self, client: AsyncClient, auth_headers, test_project, test_episode):
        response = await client.get(f"/api/v1/projects/{test_project.id}/export/episode/{test_episode.id}?format=json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["export_type"] == "episode"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_quick_export_prompts(self, client: AsyncClient, auth_headers, test_project):
        response = await client.get(f"/api/v1/projects/{test_project.id}/export/prompts?format=json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["export_type"] == "prompts"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_tenant_isolation_export(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "project",
            "format": "json"
        }, headers=auth_headers)
        export_id = response.json()["export_id"]
        
        # User 2 should not access user 1's project at all (404)
        response = await client.get(f"/api/v1/projects/{test_project.id}/export/history", headers=auth_headers2)
        assert response.status_code == 404
        
        # User 2's own project history should not show user 1's exports
        response = await client.get(f"/api/v1/projects/{test_project2.id}/export/history", headers=auth_headers2)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_export_episode_not_found(self, client: AsyncClient, auth_headers, test_project):
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "episode",
            "format": "json",
            "episode_id": "00000000-0000-0000-0000-000000000000"
        }, headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_series_bible_not_found(self, client: AsyncClient, auth_headers, test_project):
        # Project without series bible
        response = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "series_bible",
            "format": "json"
        }, headers=auth_headers)
        assert response.status_code == 404

class TestExportDownload:
    """Audit F-15/F-16/P1-08: download was a 307 stub; history missed types."""

    @pytest.mark.asyncio
    async def test_download_export_returns_file(
        self, client: AsyncClient, auth_headers, test_project, test_character
    ):
        create = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "characters", "format": "json",
        }, headers=auth_headers)
        assert create.status_code == 201
        export_id = create.json()["export_id"]

        # History now includes all 8 export types (was: only 3).
        history = await client.get(
            f"/api/v1/projects/{test_project.id}/export/history", headers=auth_headers)
        assert history.status_code == 200
        assert any(e["export_id"] == export_id for e in history.json())

        download = await client.get(
            f"/api/v1/projects/{test_project.id}/export/{export_id}/download",
            headers=auth_headers)
        assert download.status_code == 200, download.text
        assert "attachment" in download.headers.get("content-disposition", "")
        import json as _json
        body = _json.loads(download.content)
        assert body["characters"][0]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_export_csv_is_real_csv(
        self, client: AsyncClient, auth_headers, test_project, test_character
    ):
        create = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "characters", "format": "csv",
        }, headers=auth_headers)
        assert create.status_code == 201
        file_url = create.json()["file_url"]
        assert file_url.startswith("data:text/csv;base64,")
        import base64, csv, io
        content = base64.b64decode(file_url.split(";base64,", 1)[1]).decode()
        rows = list(csv.DictReader(io.StringIO(content)))
        assert rows and rows[0]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_download_unknown_export_404(
        self, client: AsyncClient, auth_headers, test_project
    ):
        response = await client.get(
            f"/api/v1/projects/{test_project.id}/export/does-not-exist/download",
            headers=auth_headers)
        assert response.status_code == 404
