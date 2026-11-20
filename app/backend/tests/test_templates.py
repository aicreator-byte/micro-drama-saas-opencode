import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.character import Character
from app.models.location import Location
from app.models.project import Project
from app.models.series_bible import SeriesBible


class TestTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_has_at_least_six_genres(self, client: AsyncClient):
        resp = await client.get("/api/v1/templates")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        assert len(templates) >= 6
        genres = {t["genre"] for t in templates}
        assert {"romance", "thriller", "revenge", "family", "ceo_billionaire", "fantasy"} <= genres
        for t in templates:
            assert t["title_suggestion"]
            assert t["premise"]

    @pytest.mark.asyncio
    async def test_template_detail_romance(self, client: AsyncClient):
        resp = await client.get("/api/v1/templates/romance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["genre"] == "romance"
        assert len(data["characters"]) >= 4
        assert len(data["locations"]) >= 3
        assert data["premise"]
        assert data["main_plot"]
        assert data["episode_structure"]
        assert all(c["name"] and c["role"] for c in data["characters"])
        assert all(loc["name"] and loc["type"] for loc in data["locations"])

    @pytest.mark.asyncio
    async def test_template_detail_unknown_genre_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/templates/not-a-genre")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_from_template_creates_project_bible_characters_locations(
        self, client: AsyncClient, auth_headers, test_user, db_session,
    ):
        resp = await client.post(
            "/api/v1/projects/from-template",
            json={"genre": "romance"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Cinta di Balik Hujan"
        assert data["genre"] == "romance"
        assert data["owner_id"] == test_user.id
        project_id = data["id"]

        result = await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == project_id)
        )
        bible = result.scalar_one_or_none()
        assert bible is not None
        assert "koki muda" in bible.premise

        result = await db_session.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = result.scalars().all()
        assert len(characters) >= 4

        result = await db_session.execute(
            select(Location).where(Location.project_id == project_id)
        )
        locations = result.scalars().all()
        assert len(locations) >= 3

    @pytest.mark.asyncio
    async def test_from_template_custom_title(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/projects/from-template",
            json={"genre": "thriller", "title": "Judulku Sendiri"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Judulku Sendiri"

    @pytest.mark.asyncio
    async def test_from_template_unknown_genre_404(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/projects/from-template",
            json={"genre": "nope"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_from_template_project_belongs_to_caller_only(
        self, client: AsyncClient, auth_headers, auth_headers2, test_user, test_user2,
    ):
        resp = await client.post(
            "/api/v1/projects/from-template",
            json={"genre": "fantasy"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]
        assert resp.json()["owner_id"] == test_user.id

        # The other user cannot see the project at all.
        resp2 = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers2)
        assert resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_from_template_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/projects/from-template", json={"genre": "romance"})
        assert resp.status_code == 401
