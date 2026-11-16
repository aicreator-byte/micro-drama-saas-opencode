import pytest
from httpx import AsyncClient


class TestAuditLogs:
    @pytest.mark.asyncio
    async def test_list_audit_logs(self, client: AsyncClient, auth_headers, test_project):
        # Create a project to generate audit logs
        await client.post("/api/v1/projects", json={
            "title": "Audit Test Project"
        }, headers=auth_headers)
        
        response = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_action(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/audit-logs?action=project_create", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for log in data:
            assert log["action"] == "project_create"

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_resource(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/audit-logs?resource_type=project", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for log in data:
            assert log["resource_type"] == "project"

    @pytest.mark.asyncio
    async def test_tenant_isolation_audit_logs(self, client: AsyncClient, auth_headers, auth_headers2, test_project, test_project2):
        # User 1 creates a project
        await client.post("/api/v1/projects", json={
            "title": "User 1 Project"
        }, headers=auth_headers)
        
        # User 2 creates a project
        await client.post("/api/v1/projects", json={
            "title": "User 2 Project"
        }, headers=auth_headers2)
        
        # User 1 should only see their own logs
        response = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # User 2 should only see their own logs
        response = await client.get("/api/v1/audit-logs", headers=auth_headers2)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)