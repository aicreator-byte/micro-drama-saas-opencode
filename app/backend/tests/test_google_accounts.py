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

class TestAutomationMockDisabled:
    """Audit F-02: mock automation login overwrote the real encrypted
    session with plaintext fake cookies and marked the account CONNECTED."""

    @pytest.mark.asyncio
    async def test_automation_login_returns_503_and_keeps_session(
        self, client: AsyncClient, auth_headers, test_project, db_session
    ):
        from sqlalchemy import select
        from app.models.google_account import GoogleAccount
        from app.core.encryption import encryption_service

        create = await client.post("/api/v1/google-accounts", json={
            "email": "real@gmail.com", "session_data": "REAL_ENCRYPTED_SESSION_MARKER",
        }, headers=auth_headers)
        assert create.status_code == 201
        account_id = create.json()["id"]

        response = await client.post(
            f"/api/v1/projects/{test_project.id}/flow-bridge/automation/login",
            json={"google_account_id": account_id}, headers=auth_headers)
        assert response.status_code == 503, response.text

        result = await db_session.execute(
            select(GoogleAccount).where(GoogleAccount.id == account_id))
        account = result.scalar_one()
        assert encryption_service.decrypt(account.encrypted_session_data) == "REAL_ENCRYPTED_SESSION_MARKER"
        assert account.status.value == "connected"

    @pytest.mark.asyncio
    async def test_automation_check_account_returns_503(
        self, client: AsyncClient, auth_headers, test_project
    ):
        create = await client.post("/api/v1/google-accounts", json={
            "email": "real2@gmail.com", "session_data": "session-data",
        }, headers=auth_headers)
        account_id = create.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{test_project.id}/flow-bridge/automation/check-account",
            json={"google_account_id": account_id}, headers=auth_headers)
        assert response.status_code == 503


class TestGoogleAccountDisconnect:
    """Disconnect must wipe session AND refresh token (password_encrypted)."""

    @pytest.mark.asyncio
    async def test_disconnect_clears_all_credentials(
        self, client: AsyncClient, auth_headers, db_session
    ):
        from sqlalchemy import select
        from app.models.google_account import GoogleAccount

        create = await client.post("/api/v1/google-accounts", json={
            "email": "disc@gmail.com", "session_data": "session-data",
        }, headers=auth_headers)
        account_id = create.json()["id"]
        # Simulate a stored refresh token via PATCH password.
        patched = await client.patch(f"/api/v1/google-accounts/{account_id}",
            json={"password": "refresh-token-xyz"}, headers=auth_headers)
        assert patched.status_code == 200, patched.text

        delete = await client.delete(
            f"/api/v1/google-accounts/{account_id}", headers=auth_headers)
        assert delete.status_code == 204

        result = await db_session.execute(
            select(GoogleAccount).where(GoogleAccount.id == account_id))
        account = result.scalar_one()
        assert account.status.value == "disconnected"
        assert account.encrypted_session_data is None
        assert account.password_encrypted is None


class TestOAuthAuthorizeUrlEncoding:
    """Audit F-09: authorize URL had raw spaces / unencoded redirect_uri."""

    @pytest.mark.asyncio
    async def test_authorize_url_is_url_encoded(self, client: AsyncClient):
        # First registered user is superuser (bootstrap) and can PATCH settings.
        reg = await client.post("/api/v1/auth/register", json={
            "email": "oauth-admin@example.com", "password": "password123",
            "full_name": "OAuth Admin",
        })
        assert reg.status_code == 201
        login = await client.post("/api/v1/auth/login", data={
            "username": "oauth-admin@example.com", "password": "password123",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        patched = await client.patch("/api/v1/settings", json={
            "google_oauth_client_id": "fake-id.apps.googleusercontent.com",
            "google_oauth_client_secret": "fake-secret",
        }, headers=headers)
        assert patched.status_code == 200, patched.text

        response = await client.get(
            "/api/v1/google-accounts/oauth/authorize", headers=headers)
        assert response.status_code == 200, response.text
        url = response.json()["authorize_url"]
        assert " " not in url
        assert "scope=openid" in url
        assert "redirect_uri=http%3A%2F%2F" in url
