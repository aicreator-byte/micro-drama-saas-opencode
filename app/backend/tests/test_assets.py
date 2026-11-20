"""Tes Asset Management: LocalStorageBackend, endpoint CRUD, S3 signing (mock)."""
import pytest
from httpx import AsyncClient, MockTransport, Request, Response

from app.core.config import settings
from app.services.storage import (
    LocalStorageBackend,
    S3Backend,
    get_storage_backend,
    sanitize_key,
)


class TestLocalStorageBackend:
    def test_put_get_delete_exists(self, tmp_path):
        backend = LocalStorageBackend(root=tmp_path)
        url = backend.put("proj1/clip.mp4", b"fake-video-bytes", "video/mp4")
        assert url == "proj1/clip.mp4"
        assert backend.exists("proj1/clip.mp4")
        assert backend.get("proj1/clip.mp4") == b"fake-video-bytes"
        assert "proj1/clip.mp4" in backend.list("proj1")
        backend.delete("proj1/clip.mp4")
        assert not backend.exists("proj1/clip.mp4")
        with pytest.raises(FileNotFoundError):
            backend.get("proj1/clip.mp4")

    def test_sanitize_key_rejects_traversal(self, tmp_path):
        backend = LocalStorageBackend(root=tmp_path)
        for bad in ("../evil.mp4", "a/../../evil.mp4", "/abs/path.mp4", "a\\b.mp4", "", ".."):
            with pytest.raises(ValueError):
                sanitize_key(bad)
            with pytest.raises(ValueError):
                backend.put(bad, b"x")
        assert sanitize_key("a/./b.mp4") == "a/b.mp4"

    def test_list_prefix(self, tmp_path):
        backend = LocalStorageBackend(root=tmp_path)
        backend.put("p1/a.txt", b"1")
        backend.put("p1/b.txt", b"2")
        backend.put("p2/c.txt", b"3")
        assert sorted(backend.list("p1")) == ["p1/a.txt", "p1/b.txt"]
        assert len(backend.list()) == 3


class TestAssetEndpoints:
    @pytest.mark.asyncio
    async def test_upload_list_download_delete(self, client: AsyncClient, auth_headers,
                                              test_project, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "ASSET_STORAGE_DIR", str(tmp_path))
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")

        upload = await client.post(
            f"/api/v1/projects/{test_project.id}/assets",
            files={"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
            headers=auth_headers,
        )
        assert upload.status_code == 201, upload.text
        asset = upload.json()
        assert asset["filename"] == "clip.mp4"
        assert asset["size_bytes"] == len(b"fake-video-bytes")
        assert asset["key"].startswith(test_project.id + "/")

        listing = await client.get(f"/api/v1/projects/{test_project.id}/assets",
                                   headers=auth_headers)
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["id"] == asset["id"]

        download = await client.get(
            f"/api/v1/projects/{test_project.id}/assets/{asset['id']}/download",
            headers=auth_headers)
        assert download.status_code == 200
        assert download.content == b"fake-video-bytes"

        delete = await client.delete(
            f"/api/v1/projects/{test_project.id}/assets/{asset['id']}",
            headers=auth_headers)
        assert delete.status_code == 204
        listing = await client.get(f"/api/v1/projects/{test_project.id}/assets",
                                   headers=auth_headers)
        assert listing.json() == []

    @pytest.mark.asyncio
    async def test_upload_unknown_project_404(self, client: AsyncClient, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "ASSET_STORAGE_DIR", str(tmp_path))
        resp = await client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/assets",
            files={"file": ("x.txt", b"x", "text/plain")},
            headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_unknown_asset_404(self, client: AsyncClient, auth_headers, test_project):
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/assets/00000000-0000-0000-0000-000000000000/download",
            headers=auth_headers)
        assert resp.status_code == 404


class TestS3Backend:
    def test_url_signing_without_network(self):
        seen: dict = {}

        def handler(request: Request) -> Response:
            seen["headers"] = dict(request.headers)
            seen["url"] = str(request.url)
            return Response(200, content=b"ok")

        backend = S3Backend(
            endpoint="https://s3.example.test",
            bucket="my-bucket",
            access_key="AKIDEXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            cdn_base_url="https://cdn.example.test",
            transport=MockTransport(handler),
        )
        backend.put("proj/clip.mp4", b"data", "video/mp4")
        auth = seen["headers"].get("authorization", "")
        assert "AWS4-HMAC-SHA256" in auth
        assert "SignedHeaders=" in auth
        assert "Credential=AKIDEXAMPLE/" in auth
        assert "Signature=" in auth
        assert seen["url"] == "https://s3.example.test/my-bucket/proj/clip.mp4"
        # CDN base dipakai untuk URL publik, bukan untuk request S3.
        assert backend.url("proj/clip.mp4") == "https://cdn.example.test/proj/clip.mp4"

    def test_s3_backend_without_credentials_errors_on_use(self, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
        monkeypatch.setattr(settings, "S3_ENDPOINT", "")
        monkeypatch.setattr(settings, "S3_BUCKET", "")
        monkeypatch.setattr(settings, "S3_ACCESS_KEY", "")
        monkeypatch.setattr(settings, "S3_SECRET_KEY", "")
        backend = get_storage_backend()
        with pytest.raises(ValueError, match="S3_ENDPOINT"):
            backend.put("a/b.txt", b"x")

    def test_unknown_backend_errors(self, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "ftp")
        with pytest.raises(ValueError, match="unknown STORAGE_BACKEND"):
            get_storage_backend()
