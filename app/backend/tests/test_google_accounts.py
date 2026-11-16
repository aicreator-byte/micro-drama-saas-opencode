import pytest
from httpx import AsyncClient
from app.models.google_account import GoogleAccountStatus


class TestGoogleAccounts:
    @pytest.mark.asyncio
    async def test_create_google_account(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/google-accounts", json={
            "email": "test@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@gmail.com"
        assert data["status"] == "connected"

    @pytest.mark.asyncio
    async def test_list_google_accounts(self, client: AsyncClient, auth_headers, test_project):
        await client.post("/api/v1/google-accounts", json={
            "email": "test1@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        
        response = await client.get("/api/v1/google-accounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_max_accounts_limit(self, client: AsyncClient, auth_headers):
        # Create 20 accounts (max allowed)
        for i in range(20):
            response = await client.post("/api/v1/google-accounts", json={
                "email": f"test{i}@gmail.com",
                "session_data": "test_session_data"
            }, headers=auth_headers)
            assert response.status_code == 201
        
        # 21st should fail
        response = await client.post("/api/v1/google-accounts", json={
            "email": "test20@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "Maximum of 20" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_google_account(self, client: AsyncClient, auth_headers):
        create_response = await client.post("/api/v1/google-accounts", json={
            "email": "get@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        account_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/google-accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "get@gmail.com"

    @pytest.mark.asyncio
    async def test_update_google_account(self, client: AsyncClient, auth_headers):
        create_response = await client.post("/api/v1/google-accounts", json={
            "email": "update@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        account_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/v1/google-accounts/{account_id}", json={
            "display_name": "Updated Name",
            "status": "disconnected"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
        assert data["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_delete_google_account(self, client: AsyncClient, auth_headers):
        create_response = await client.post("/api/v1/google-accounts", json={
            "email": "delete@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        account_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/google-accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_tenant_isolation_google_accounts(self, client: AsyncClient, auth_headers, auth_headers2):
        create_response = await client.post("/api/v1/google-accounts", json={
            "email": "user1@gmail.com",
            "session_data": "test_session_data"
        }, headers=auth_headers)
        account_id = create_response.json()["id"]
        
        # User 2 should not access
        response = await client.get(f"/api/v1/google-accounts/{account_id}", headers=auth_headers2)
        assert response.status_code == 404