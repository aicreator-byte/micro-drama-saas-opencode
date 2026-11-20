"""Tes Video Pipeline: assemble FFmpeg, validasi path, endpoint job."""
import asyncio
import shutil
import subprocess
import time

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.video_pipeline import assemble_video, get_duration_seconds

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not available")


def make_clip(path, color="red", duration=1):
    """Klip mp4 kecil dari testsrc (1 dtk, 320x240)."""
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi",
         "-i", f"testsrc=duration={duration}:size=320x240:rate=10",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        capture_output=True, check=True, timeout=60,
    )


class TestAssembleVideo:
    def test_assemble_two_clips(self, tmp_path):
        clip1, clip2 = tmp_path / "c1.mp4", tmp_path / "c2.mp4"
        make_clip(clip1, "red")
        make_clip(clip2, "blue")
        out = tmp_path / "out.mp4"
        duration = assemble_video([clip1, clip2], out, storage_root=tmp_path)
        assert out.is_file() and out.stat().st_size > 0
        assert out.read_bytes()[4:8] == b"ftyp"  # header mp4
        assert duration == pytest.approx(2.0, abs=0.5)

    def test_assemble_with_subtitle_and_audio(self, tmp_path):
        clip = tmp_path / "c1.mp4"
        make_clip(clip)
        srt = tmp_path / "sub.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHalo dunia\n", encoding="utf-8")
        out = tmp_path / "out_sub.mp4"
        duration = assemble_video([clip], out, subtitle_path=srt, storage_root=tmp_path)
        assert out.is_file() and out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.5)

    def test_path_traversal_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="escapes storage"):
            assemble_video(["../evil.mp4"], tmp_path / "o.mp4", storage_root=tmp_path)
        with pytest.raises(ValueError, match="escapes storage"):
            assemble_video(["/etc/passwd"], tmp_path / "o.mp4", storage_root=tmp_path)

    def test_missing_input_rejected(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            assemble_video(["nope.mp4"], tmp_path / "o.mp4", storage_root=tmp_path)

    def test_get_duration(self, tmp_path):
        clip = tmp_path / "c1.mp4"
        make_clip(clip)
        assert get_duration_seconds(clip) == pytest.approx(1.0, abs=0.3)


class TestVideoEndpoints:
    @pytest.mark.asyncio
    async def test_assemble_endpoint_end_to_end(self, client: AsyncClient, auth_headers,
                                                test_project, test_episode,
                                                tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "ASSET_STORAGE_DIR", str(tmp_path))
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        keys = []
        for name in ("c1.mp4", "c2.mp4"):
            clip = tmp_path / name
            make_clip(clip)
            upload = await client.post(
                f"/api/v1/projects/{test_project.id}/assets",
                files={"file": (name, clip.read_bytes(), "video/mp4")},
                headers=auth_headers)
            assert upload.status_code == 201, upload.text
            keys.append(upload.json()["key"])

        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/video/assemble",
            json={"episode_id": test_episode.id, "input_keys": keys},
            headers=auth_headers)
        assert resp.status_code == 202, resp.text
        job = resp.json()
        assert job["status"] in ("pending", "processing", "completed")
        job_id = job["id"]

        # Poll sampai selesai (ffmpeg 2x1 dtk, cepat). Abaikan 500 sesaat:
        # background task + polling berbagi satu koneksi sqlite in-memory.
        final = None
        for _ in range(60):
            got = await client.get(
                f"/api/v1/projects/{test_project.id}/video/jobs/{job_id}",
                headers=auth_headers)
            if got.status_code != 200:
                await asyncio.sleep(0.5)
                continue
            final = got.json()
            if final["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.5)
        assert final is not None
        assert final["status"] == "completed", final.get("error_message")
        assert final["duration_seconds"] == pytest.approx(2.0, abs=0.5)
        assert final["output_path"] == f"video-outputs/{job_id}.mp4"
        out_file = tmp_path / final["output_path"]
        assert out_file.is_file() and out_file.stat().st_size > 0

        listing = await client.get(
            f"/api/v1/projects/{test_project.id}/video/jobs", headers=auth_headers)
        assert listing.status_code == 200
        assert any(j["id"] == job_id for j in listing.json())

    @pytest.mark.asyncio
    async def test_assemble_unknown_asset_key_404(self, client: AsyncClient, auth_headers,
                                                  test_project, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "ASSET_STORAGE_DIR", str(tmp_path))
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/video/assemble",
            json={"input_keys": ["no/such-key.mp4"]},
            headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_job_404(self, client: AsyncClient, auth_headers, test_project):
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/video/jobs/00000000-0000-0000-0000-000000000000",
            headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_assemble_unknown_project_404(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/video/assemble",
            json={"input_keys": ["a/b.mp4"]},
            headers=auth_headers)
        assert resp.status_code == 404
