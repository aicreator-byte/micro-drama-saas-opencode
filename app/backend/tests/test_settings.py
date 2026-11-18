"""Tests for Settings API + superuser bootstrap + change-password.

Covers audit findings:
- F-07 / O-P0-06: no way to become superuser on a fresh install.
- Hermes P0-11: PATCH /settings with ai_providers always 500
  (AttributeError: 'dict' object has no attribute 'model_dump').
- F-20: mock provider must not be activatable via Settings PATCH.
- F-24: change-password endpoint missing.
"""
import pytest
from httpx import AsyncClient


async def _register(client, email, password="password123"):
    response = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Test",
    })
    assert response.status_code == 201, response.text
    return response.json()


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", data={
        "username": email, "password": password,
    })
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestSuperuserBootstrap:
    @pytest.mark.asyncio
    async def test_first_registered_user_is_superuser(self, client: AsyncClient):
        user = await _register(client, "first@example.com")
        assert user["is_superuser"] is True

    @pytest.mark.asyncio
    async def test_second_registered_user_is_not_superuser(self, client: AsyncClient):
        first = await _register(client, "first@example.com")
        second = await _register(client, "second@example.com")
        assert first["is_superuser"] is True
        assert second["is_superuser"] is False

    @pytest.mark.asyncio
    async def test_first_user_can_reach_settings(self, client: AsyncClient):
        await _register(client, "admin@example.com")
        headers = await _login(client, "admin@example.com")
        response = await client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["ai_providers"]
        assert data["ai_providers"][0]["provider"] == "nvidia"


class TestSettingsApi:
    @pytest.mark.asyncio
    async def test_get_settings_forbidden_for_non_superuser(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.get("/api/v1/settings", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_patch_settings_forbidden_for_non_superuser(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.patch("/api/v1/settings", json={
            "ai_providers": [{
                "id": "x", "provider": "nvidia", "model": "m",
                "key_env": "NVIDIA_API_KEY", "enabled": True, "priority": 1,
            }]
        }, headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_patch_ai_providers_roundtrip(self, client: AsyncClient):
        """PATCH with ai_providers used to 500 (dict has no model_dump)."""
        await _register(client, "admin@example.com")
        headers = await _login(client, "admin@example.com")
        response = await client.patch("/api/v1/settings", json={
            "ai_providers": [{
                "id": "nvidia-nemotron-550b", "provider": "nvidia",
                "model": "nvidia/nemotron-3-ultra-550b-a55b",
                "key_env": "NVIDIA_API_KEY", "enabled": True, "priority": 1,
            }]
        }, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["ai_providers"]) == 1
        assert data["ai_providers"][0]["model"] == "nvidia/nemotron-3-ultra-550b-a55b"

        # GET reflects the PATCH
        get_response = await client.get("/api/v1/settings", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["ai_providers"][0]["id"] == "nvidia-nemotron-550b"

    @pytest.mark.asyncio
    async def test_patch_ai_providers_rejects_mock(self, client: AsyncClient):
        await _register(client, "admin@example.com")
        headers = await _login(client, "admin@example.com")
        response = await client.patch("/api/v1/settings", json={
            "ai_providers": [{
                "id": "mock-provider", "provider": "mock", "model": "mock-model",
                "key_env": "MOCK_API_KEY", "enabled": True, "priority": 1,
            }]
        }, headers=headers)
        assert response.status_code == 400
        assert "mock" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_patch_oauth_credentials_sets_configured_flags(
        self, client: AsyncClient
    ):
        await _register(client, "admin@example.com")
        headers = await _login(client, "admin@example.com")
        response = await client.patch("/api/v1/settings", json={
            "google_oauth_client_id": "fake-id.apps.googleusercontent.com",
            "google_oauth_client_secret": "fake-secret",
        }, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["google_oauth_client_id_configured"] is True
        assert data["google_oauth_client_secret_configured"] is True
        # GET must not leak the values
        get_response = await client.get("/api/v1/settings", headers=headers)
        body = get_response.text
        assert "fake-secret" not in body
        assert "fake-id.apps" not in body


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
        }, headers=auth_headers)
        assert response.status_code == 400

        response = await client.post("/api/v1/auth/change-password", json={
            "current_password": "testpassword123",
            "new_password": "newpassword123",
        }, headers=auth_headers)
        assert response.status_code == 200, response.text

        # New password works, old one does not
        login_new = await client.post("/api/v1/auth/login", data={
            "username": "test@example.com", "password": "newpassword123",
        })
        assert login_new.status_code == 200
        login_old = await client.post("/api/v1/auth/login", data={
            "username": "test@example.com", "password": "testpassword123",
        })
        assert login_old.status_code == 401
