"""Dialogue + EpisodeRevision CRUD completion (Phase 2 gap).

The models existed but the API only had list/create/delete for dialogues
and list/create for revisions. These tests cover the missing pieces:
dialogue GET one + PATCH, revision GET one + DELETE, plus 404s and
cross-user ownership (project of another user is invisible).
"""
import pytest
from httpx import AsyncClient


def _dialogue_url(project_id, episode_id, scene_id, dialogue_id=""):
    base = (
        f"/api/v1/projects/{project_id}/episodes/{episode_id}"
        f"/scenes/{scene_id}/dialogues"
    )
    return f"{base}/{dialogue_id}" if dialogue_id else base


def _revision_url(project_id, episode_id, revision_id=""):
    base = f"/api/v1/projects/{project_id}/episodes/{episode_id}/revisions"
    return f"{base}/{revision_id}" if revision_id else base


class TestDialogueCrudCompletion:
    @pytest.mark.asyncio
    async def test_get_one_and_patch(
        self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene
    ):
        create = await client.post(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id),
            json={"line_number": 1, "character_name": "Nadia",
                  "dialogue_text": "Aku tidak akan menyerah.",
                  "parenthetical": "(tenang)", "beat_number": 1},
            headers=auth_headers)
        assert create.status_code == 201, create.text
        dialogue_id = create.json()["id"]

        got = await client.get(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id, dialogue_id),
            headers=auth_headers)
        assert got.status_code == 200
        assert got.json()["dialogue_text"] == "Aku tidak akan menyerah."
        assert got.json()["parenthetical"] == "(tenang)"

        patched = await client.patch(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id, dialogue_id),
            json={"dialogue_text": "Aku akan bangkit.", "beat_number": 2},
            headers=auth_headers)
        assert patched.status_code == 200, patched.text
        assert patched.json()["dialogue_text"] == "Aku akan bangkit."
        assert patched.json()["beat_number"] == 2
        # Fields not sent are untouched.
        assert patched.json()["character_name"] == "Nadia"
        assert patched.json()["parenthetical"] == "(tenang)"

        missing = await client.get(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id, "does-not-exist"),
            headers=auth_headers)
        assert missing.status_code == 404

        bad_patch = await client.patch(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id, "does-not-exist"),
            json={"dialogue_text": "x"}, headers=auth_headers)
        assert bad_patch.status_code == 404

        # Validation: empty text and line_number < 1 are rejected.
        bad = await client.patch(
            _dialogue_url(test_project.id, test_episode.id, test_scene.id, dialogue_id),
            json={"dialogue_text": ""}, headers=auth_headers)
        assert bad.status_code == 422

    @pytest.mark.asyncio
    async def test_other_users_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2, test_episode, test_scene
    ):
        # test_episode/test_scene belong to test_project, not test_project2.
        resp = await client.get(
            _dialogue_url(test_project2.id, test_episode.id, test_scene.id),
            headers=auth_headers)
        assert resp.status_code == 404


class TestEpisodeRevisionCrudCompletion:
    @pytest.mark.asyncio
    async def test_get_one_and_delete(
        self, client: AsyncClient, auth_headers, test_project, test_episode, test_scene
    ):
        first = await client.post(
            _revision_url(test_project.id, test_episode.id),
            json={"change_notes": "Snapshot before regenerate"},
            headers=auth_headers)
        assert first.status_code == 201, first.text
        assert first.json()["revision_number"] == 1
        revision_id = first.json()["id"]

        second = await client.post(
            _revision_url(test_project.id, test_episode.id),
            json={}, headers=auth_headers)
        assert second.json()["revision_number"] == 2
        second_id = second.json()["id"]

        got = await client.get(
            _revision_url(test_project.id, test_episode.id, revision_id),
            headers=auth_headers)
        assert got.status_code == 200
        assert got.json()["revision_number"] == 1
        assert got.json()["title"] == "The Return"
        assert got.json()["change_notes"] == "Snapshot before regenerate"

        missing = await client.get(
            _revision_url(test_project.id, test_episode.id, "does-not-exist"),
            headers=auth_headers)
        assert missing.status_code == 404

        deleted = await client.delete(
            _revision_url(test_project.id, test_episode.id, revision_id),
            headers=auth_headers)
        assert deleted.status_code == 204

        gone = await client.get(
            _revision_url(test_project.id, test_episode.id, revision_id),
            headers=auth_headers)
        assert gone.status_code == 404

        # The other revision is untouched; the episode itself still exists.
        rows = await client.get(
            _revision_url(test_project.id, test_episode.id), headers=auth_headers)
        assert [r["id"] for r in rows.json()] == [second_id]
        episode = await client.get(
            f"/api/v1/projects/{test_project.id}/episodes/{test_episode.id}",
            headers=auth_headers)
        assert episode.status_code == 200

        missing_delete = await client.delete(
            _revision_url(test_project.id, test_episode.id, "does-not-exist"),
            headers=auth_headers)
        assert missing_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_other_users_project_is_404(
        self, client: AsyncClient, auth_headers, test_project2, test_episode
    ):
        resp = await client.get(
            _revision_url(test_project2.id, test_episode.id), headers=auth_headers)
        assert resp.status_code == 404
