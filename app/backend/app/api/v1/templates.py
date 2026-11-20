"""Project templates per genre (no LLM).

- GET /templates: summary list (genre + title suggestion + short premise).
- GET /templates/{genre}: full detail; unknown genre -> 404.
- POST /projects/from-template: create a Project owned by the caller plus
  its SeriesBible, Characters and Locations straight from the template.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.character import Character
from app.models.location import Location
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.models.user import User
from app.schemas.project import ProjectResponse
from app.services import templates as template_service

router = APIRouter()


@router.get("/templates")
async def list_templates():
    return {"templates": template_service.list_templates()}


@router.get("/templates/{genre}")
async def get_template_detail(genre: str):
    template = template_service.get_template(genre)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Unknown template genre: {genre!r}")
    return template


@router.post("/projects/from-template", response_model=ProjectResponse, status_code=201)
async def create_project_from_template(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    genre = (payload or {}).get("genre")
    template = template_service.get_template(genre) if genre else None
    if template is None:
        raise HTTPException(status_code=404, detail=f"Unknown template genre: {genre!r}")

    title = (payload or {}).get("title") or template["title_suggestion"]
    project = Project(
        owner_id=current_user.id,
        title=title,
        description=template["premise"],
        genre=genre,
        total_episodes=20,
    )
    db.add(project)
    await db.flush()  # project.id needed for children below

    bible = SeriesBible(
        project_id=project.id,
        premise=template["premise"],
        main_plot=template["main_plot"],
        subplots=json.dumps(template["subplots"]),
        world_settings=template["world_settings"],
        tone_and_visual_style=template["tone_and_visual_style"],
        ending_direction=template["ending_direction"],
        episode_structure=template["episode_structure"],
    )
    db.add(bible)
    for index, char in enumerate(template["characters"]):
        db.add(Character(
            project_id=project.id,
            name=char["name"],
            role=char.get("role"),
            background=char.get("background"),
            order_index=index,
        ))
    for index, loc in enumerate(template["locations"]):
        db.add(Location(
            project_id=project.id,
            name=loc["name"],
            type=loc.get("type"),
            description=loc.get("description"),
            order_index=index,
        ))
    await db.commit()
    await db.refresh(project)
    return project
