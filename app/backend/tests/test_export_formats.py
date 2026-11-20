"""Tes Export format baru: Fountain (.fountain) dan Final Draft (.fdx)."""
import base64
import json
import xml.etree.ElementTree as ET

import pytest
from httpx import AsyncClient

from app.api.v1.export import format_fountain, format_final_draft


def _decode_file_url(file_url: str) -> str:
    assert ";base64," in file_url
    return base64.b64decode(file_url.split(";base64,", 1)[1]).decode("utf-8")


class TestFountainExport:
    @pytest.mark.asyncio
    async def test_full_project_fountain(self, client: AsyncClient, auth_headers,
                                         test_project, test_episode, test_scene):
        resp = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "full_project",
            "format": "fountain",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["format"] == "fountain"
        content = _decode_file_url(body["file_url"])
        assert "Title:" in content
        assert "Test Project" in content
        assert "INT." in content
        assert "FUNERAL SCENE" in content  # slugline dari scene fixture
        assert "CUT TO:" not in content  # hanya 1 scene -> tanpa transisi

    @pytest.mark.asyncio
    async def test_episode_fountain_with_dialogue(self, client: AsyncClient, auth_headers,
                                                  test_project, test_episode,
                                                  db_session, test_location):
        from app.models.episode import Scene
        scene = Scene(
            episode_id=test_episode.id,
            scene_number=2,
            title="Ruang Tamu",
            description="Nadia menatap Raka.",
            time_of_day="Night",
            dialogue=json.dumps([
                {"character": "Nadia", "text": "Aku tidak takut."},
                {"character": "Raka", "text": "Kita hadapi bersama.",
                 "parenthetical": "tenang"},
            ]),
        )
        db_session.add(scene)
        await db_session.commit()
        resp = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "episode",
            "format": "fountain",
            "episode_id": test_episode.id,
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        content = _decode_file_url(resp.json()["file_url"])
        assert "INT. RUANG TAMU - NIGHT" in content
        assert "NADIA" in content
        assert "Aku tidak takut." in content
        assert "(tenang)" in content

    def test_fountain_empty_data_still_has_title_page(self):
        content = format_fountain({})
        assert "Title:" in content
        assert "Untitled" in content


class TestFinalDraftExport:
    @pytest.mark.asyncio
    async def test_full_project_fdx(self, client: AsyncClient, auth_headers,
                                    test_project, test_episode, test_scene):
        resp = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "full_project",
            "format": "fdx",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["format"] == "fdx"
        content = _decode_file_url(body["file_url"])
        root = ET.fromstring(content)
        assert root.tag == "FinalDraft"
        assert root.attrib.get("DocumentType") == "Script"
        assert root.find("Content") is not None
        types = [p.attrib.get("Type") for p in root.find("Content").iter("Paragraph")]
        assert "Scene Heading" in types
        texts = [t.text for t in root.iter("Text") if t.text]
        assert any("FUNERAL SCENE" in t for t in texts)

    def test_fdx_empty_data_is_valid_xml(self):
        content = format_final_draft({})
        root = ET.fromstring(content)
        assert root.tag == "FinalDraft"
        assert root.find("Content") is not None

    @pytest.mark.asyncio
    async def test_unknown_format_422(self, client: AsyncClient, auth_headers, test_project):
        resp = await client.post(f"/api/v1/projects/{test_project.id}/export", json={
            "export_type": "full_project",
            "format": "docx",
        }, headers=auth_headers)
        assert resp.status_code == 422
