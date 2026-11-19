from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.episode import Episode, EpisodeStatus, Scene, SceneStatus, Shot, ShotStatus
from app.models.audit_log import AuditAction
from app.schemas.episode import EpisodeCreate, EpisodeUpdate, EpisodeResponse, SceneCreate, SceneUpdate, SceneResponse, ShotCreate, ShotUpdate, ShotResponse

router = APIRouter()


async def get_project_or_404(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


# Episode endpoints
@router.post("/{project_id}/episodes", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    project_id: str,
    episode_data: EpisodeCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    # Check if episode number already exists
    result = await db.execute(
        select(Episode).where(Episode.project_id == project_id, Episode.episode_number == episode_data.episode_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Episode {episode_data.episode_number} already exists"
        )
    
    # Check total episodes limit
    count_result = await db.execute(
        select(func.count(Episode.id)).where(Episode.project_id == project_id)
    )
    count = count_result.scalar()
    if count >= project.total_episodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {project.total_episodes} episodes allowed"
        )
    
    episode = Episode(
        project_id=project_id,
        episode_number=episode_data.episode_number,
        title=episode_data.title,
        summary=episode_data.summary
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_CREATE,
        resource_type="episode", resource_id=episode.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"episode_number": episode.episode_number, "title": episode.title}
    )
    await db.commit()
    
    return episode


@router.get("/{project_id}/episodes", response_model=List[EpisodeResponse])
async def list_episodes(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.project_id == project_id).order_by(Episode.episode_number)
    )
    episodes = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_READ,
        resource_type="episode", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return episodes


@router.get("/{project_id}/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    project_id: str,
    episode_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_READ,
        resource_type="episode", resource_id=episode.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return episode


@router.patch("/{project_id}/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    project_id: str,
    episode_id: str,
    episode_data: EpisodeUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    old_values = {
        "title": episode.title,
        "summary": episode.summary,
        "status": episode.status.value,
        "estimated_cost": episode.estimated_cost,
        "actual_cost": episode.actual_cost,
        "production_notes": episode.production_notes
    }
    
    update_data = episode_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(episode, field, value)
    
    await db.commit()
    await db.refresh(episode)
    
    new_values = {
        "title": episode.title,
        "summary": episode.summary,
        "status": episode.status.value,
        "estimated_cost": episode.estimated_cost,
        "actual_cost": episode.actual_cost,
        "production_notes": episode.production_notes
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_UPDATE,
        resource_type="episode", resource_id=episode.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return episode


@router.delete("/{project_id}/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    project_id: str,
    episode_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_DELETE,
        resource_type="episode", resource_id=episode.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"episode_number": episode.episode_number, "title": episode.title}
    )
    
    await db.delete(episode)
    await db.commit()


# Scene endpoints
@router.post("/{project_id}/episodes/{episode_id}/scenes", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    project_id: str,
    episode_id: str,
    scene_data: SceneCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    # Check if scene number already exists
    result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id, Scene.scene_number == scene_data.scene_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scene {scene_data.scene_number} already exists in this episode"
        )
    
    scene = Scene(
        episode_id=episode_id,
        scene_number=scene_data.scene_number,
        title=scene_data.title,
        description=scene_data.description,
        location_id=scene_data.location_id,
        time_of_day=scene_data.time_of_day,
        duration_estimate=scene_data.duration_estimate,
        action=scene_data.action,
        dialogue=scene_data.dialogue,
        characters_present=json.dumps(scene_data.characters_present) if scene_data.characters_present else None
    )
    db.add(scene)
    await db.commit()
    await db.refresh(scene)
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_CREATE,
        resource_type="scene", resource_id=scene.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"scene_number": scene.scene_number, "title": scene.title}
    )
    await db.commit()
    
    return scene


@router.get("/{project_id}/episodes/{episode_id}/scenes", response_model=List[SceneResponse])
async def list_scenes(
    project_id: str,
    episode_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_number)
    )
    scenes = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_READ,
        resource_type="scene", resource_id=episode_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return scenes


@router.get("/{project_id}/episodes/{episode_id}/scenes/{scene_id}", response_model=SceneResponse)
async def get_scene(
    project_id: str,
    episode_id: str,
    scene_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_READ,
        resource_type="scene", resource_id=scene.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return scene


@router.patch("/{project_id}/episodes/{episode_id}/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    project_id: str,
    episode_id: str,
    scene_id: str,
    scene_data: SceneUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    
    old_values = {
        "title": scene.title,
        "description": scene.description,
        "location_id": scene.location_id,
        "time_of_day": scene.time_of_day,
        "duration_estimate": scene.duration_estimate,
        "status": scene.status.value,
        "action": scene.action,
        "dialogue": scene.dialogue,
        "characters_present": scene.characters_present,
        "production_notes": scene.production_notes
    }
    
    update_data = scene_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "characters_present" and value is not None:
            value = json.dumps(value)
        setattr(scene, field, value)
    
    await db.commit()
    await db.refresh(scene)
    
    new_values = {
        "title": scene.title,
        "description": scene.description,
        "location_id": scene.location_id,
        "time_of_day": scene.time_of_day,
        "duration_estimate": scene.duration_estimate,
        "status": scene.status.value,
        "action": scene.action,
        "dialogue": scene.dialogue,
        "characters_present": scene.characters_present,
        "production_notes": scene.production_notes
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_UPDATE,
        resource_type="scene", resource_id=scene.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return scene


@router.delete("/{project_id}/episodes/{episode_id}/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    project_id: str,
    episode_id: str,
    scene_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_DELETE,
        resource_type="scene", resource_id=scene.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"scene_number": scene.scene_number, "title": scene.title}
    )
    
    await db.delete(scene)
    await db.commit()


# Shot endpoints
@router.post("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/shots", response_model=ShotResponse, status_code=status.HTTP_201_CREATED)
async def create_shot(
    project_id: str,
    episode_id: str,
    scene_id: str,
    shot_data: ShotCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    
    # Check if shot number already exists
    result = await db.execute(
        select(Shot).where(Shot.scene_id == scene_id, Shot.shot_number == shot_data.shot_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shot {shot_data.shot_number} already exists in this scene"
        )
    
    shot = Shot(
        scene_id=scene_id,
        shot_number=shot_data.shot_number,
        shot_type=shot_data.shot_type,
        camera_angle=shot_data.camera_angle,
        camera_movement=shot_data.camera_movement,
        duration=shot_data.duration,
        description=shot_data.description,
        characters_in_shot=json.dumps(shot_data.characters_in_shot) if shot_data.characters_in_shot else None
    )
    db.add(shot)
    await db.commit()
    await db.refresh(shot)
    
    create_audit_log(
        db, current_user.id, AuditAction.SHOT_CREATE,
        resource_type="shot", resource_id=shot.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"shot_number": shot.shot_number, "shot_type": shot.shot_type}
    )
    await db.commit()
    
    return shot


@router.get("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/shots", response_model=List[ShotResponse])
async def list_shots(
    project_id: str,
    episode_id: str,
    scene_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    
    result = await db.execute(
        select(Shot).where(Shot.scene_id == scene_id).order_by(Shot.shot_number)
    )
    shots = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.SHOT_READ,
        resource_type="shot", resource_id=scene_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return shots


@router.get("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/shots/{shot_id}", response_model=ShotResponse)
async def get_shot(
    project_id: str,
    episode_id: str,
    scene_id: str,
    shot_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.scene_id == scene_id)
    )
    shot = result.scalar_one_or_none()
    
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SHOT_READ,
        resource_type="shot", resource_id=shot.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return shot


@router.patch("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/shots/{shot_id}", response_model=ShotResponse)
async def update_shot(
    project_id: str,
    episode_id: str,
    scene_id: str,
    shot_id: str,
    shot_data: ShotUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.scene_id == scene_id)
    )
    shot = result.scalar_one_or_none()
    
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found"
        )
    
    old_values = {
        "shot_type": shot.shot_type,
        "camera_angle": shot.camera_angle,
        "camera_movement": shot.camera_movement,
        "duration": shot.duration,
        "description": shot.description,
        "characters_in_shot": shot.characters_in_shot,
        "status": shot.status.value,
        "image_prompt": shot.image_prompt,
        "video_prompt": shot.video_prompt,
        "generated_image_url": shot.generated_image_url,
        "generated_video_url": shot.generated_video_url
    }
    
    update_data = shot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "characters_in_shot" and value is not None:
            value = json.dumps(value)
        setattr(shot, field, value)
    
    await db.commit()
    await db.refresh(shot)
    
    new_values = {
        "shot_type": shot.shot_type,
        "camera_angle": shot.camera_angle,
        "camera_movement": shot.camera_movement,
        "duration": shot.duration,
        "description": shot.description,
        "characters_in_shot": shot.characters_in_shot,
        "status": shot.status.value,
        "image_prompt": shot.image_prompt,
        "video_prompt": shot.video_prompt,
        "generated_image_url": shot.generated_image_url,
        "generated_video_url": shot.generated_video_url
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.SHOT_UPDATE,
        resource_type="shot", resource_id=shot.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return shot


@router.delete("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/shots/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(
    project_id: str,
    episode_id: str,
    scene_id: str,
    shot_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.scene_id == scene_id)
    )
    shot = result.scalar_one_or_none()
    
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.SHOT_DELETE,
        resource_type="shot", resource_id=shot.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"shot_number": shot.shot_number, "shot_type": shot.shot_type}
    )
    
    await db.delete(shot)
    await db.commit()

# ---------------------------------------------------------------------------
# Dialogues & episode revisions (audit F-25: models existed with no API, so
# generated dialogue could never be stored or read back as rows).
# ---------------------------------------------------------------------------
from app.models.dialogue import Dialogue
from app.models.episode_revision import EpisodeRevision
from app.schemas.dialogue import DialogueCreate, DialogueUpdate, DialogueResponse
from app.schemas.episode_revision import EpisodeRevisionCreate, EpisodeRevisionResponse


async def _get_episode_or_404(episode_id: str, project_id: str, db: AsyncSession) -> Episode:
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    return episode


async def _get_scene_or_404(scene_id: str, episode_id: str, db: AsyncSession) -> Scene:
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


@router.get("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/dialogues", response_model=List[DialogueResponse])
async def list_dialogues(
    project_id: str,
    episode_id: str,
    scene_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    await _get_scene_or_404(scene_id, episode_id, db)
    result = await db.execute(
        select(Dialogue).where(Dialogue.scene_id == scene_id).order_by(Dialogue.line_number)
    )
    return result.scalars().all()


@router.post("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/dialogues", response_model=DialogueResponse, status_code=status.HTTP_201_CREATED)
async def create_dialogue(
    project_id: str,
    episode_id: str,
    scene_id: str,
    dialogue_data: DialogueCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    await _get_scene_or_404(scene_id, episode_id, db)
    dialogue = Dialogue(
        scene_id=scene_id,
        character_id=dialogue_data.character_id,
        line_number=dialogue_data.line_number,
        character_name=dialogue_data.character_name,
        dialogue_text=dialogue_data.dialogue_text,
        parenthetical=dialogue_data.parenthetical,
        action=dialogue_data.action,
        beat_number=dialogue_data.beat_number,
    )
    db.add(dialogue)
    await db.commit()
    await db.refresh(dialogue)
    create_audit_log(
        db, current_user.id, AuditAction.DIALOGUE_CREATE,
        resource_type="dialogue", resource_id=dialogue.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"character_name": dialogue.character_name, "line_number": dialogue.line_number}
    )
    await db.commit()
    return dialogue


@router.get("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/dialogues/{dialogue_id}", response_model=DialogueResponse)
async def get_dialogue(
    project_id: str,
    episode_id: str,
    scene_id: str,
    dialogue_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    await _get_scene_or_404(scene_id, episode_id, db)
    result = await db.execute(
        select(Dialogue).where(Dialogue.id == dialogue_id, Dialogue.scene_id == scene_id)
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialogue not found")
    return dialogue


@router.patch("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/dialogues/{dialogue_id}", response_model=DialogueResponse)
async def update_dialogue(
    project_id: str,
    episode_id: str,
    scene_id: str,
    dialogue_id: str,
    dialogue_data: DialogueUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    await _get_scene_or_404(scene_id, episode_id, db)
    result = await db.execute(
        select(Dialogue).where(Dialogue.id == dialogue_id, Dialogue.scene_id == scene_id)
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialogue not found")
    for field, value in dialogue_data.model_dump(exclude_unset=True).items():
        setattr(dialogue, field, value)
    await db.commit()
    await db.refresh(dialogue)
    create_audit_log(
        db, current_user.id, AuditAction.DIALOGUE_UPDATE,
        resource_type="dialogue", resource_id=dialogue.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"character_name": dialogue.character_name, "line_number": dialogue.line_number}
    )
    await db.commit()
    return dialogue


@router.delete("/{project_id}/episodes/{episode_id}/scenes/{scene_id}/dialogues/{dialogue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dialogue(
    project_id: str,
    episode_id: str,
    scene_id: str,
    dialogue_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    await _get_scene_or_404(scene_id, episode_id, db)
    result = await db.execute(
        select(Dialogue).where(Dialogue.id == dialogue_id, Dialogue.scene_id == scene_id)
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialogue not found")
    create_audit_log(
        db, current_user.id, AuditAction.DIALOGUE_DELETE,
        resource_type="dialogue", resource_id=dialogue.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"character_name": dialogue.character_name, "line_number": dialogue.line_number}
    )
    await db.delete(dialogue)
    await db.commit()


@router.get("/{project_id}/episodes/{episode_id}/revisions", response_model=List[EpisodeRevisionResponse])
async def list_episode_revisions(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    result = await db.execute(
        select(EpisodeRevision).where(EpisodeRevision.episode_id == episode_id)
        .order_by(EpisodeRevision.revision_number.desc())
    )
    return result.scalars().all()


@router.post("/{project_id}/episodes/{episode_id}/revisions", response_model=EpisodeRevisionResponse, status_code=status.HTTP_201_CREATED)
async def create_episode_revision(
    project_id: str,
    episode_id: str,
    revision_data: EpisodeRevisionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Snapshot the episode's current title/summary/scenes as a revision."""
    await get_project_or_404(project_id, current_user.id, db)
    episode = await _get_episode_or_404(episode_id, project_id, db)
    result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_number)
    )
    scenes = result.scalars().all()
    max_result = await db.execute(
        select(func.max(EpisodeRevision.revision_number)).where(EpisodeRevision.episode_id == episode_id)
    )
    next_number = (max_result.scalar() or 0) + 1
    revision = EpisodeRevision(
        episode_id=episode_id,
        revision_number=next_number,
        title=episode.title,
        summary=episode.summary,
        scene_breakdown={"scenes": [
            {"scene_number": s.scene_number, "title": s.title, "description": s.description}
            for s in scenes
        ]},
        change_notes=revision_data.change_notes,
        created_by=current_user.id,
    )
    db.add(revision)
    await db.commit()
    await db.refresh(revision)
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_REVISION_CREATE,
        resource_type="episode_revision", resource_id=revision.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"episode_id": episode_id, "revision_number": next_number}
    )
    await db.commit()
    return revision


@router.get("/{project_id}/episodes/{episode_id}/revisions/{revision_id}", response_model=EpisodeRevisionResponse)
async def get_episode_revision(
    project_id: str,
    episode_id: str,
    revision_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    result = await db.execute(
        select(EpisodeRevision).where(
            EpisodeRevision.id == revision_id, EpisodeRevision.episode_id == episode_id
        )
    )
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode revision not found")
    return revision


@router.delete("/{project_id}/episodes/{episode_id}/revisions/{revision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode_revision(
    project_id: str,
    episode_id: str,
    revision_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Revisions are immutable snapshots: no update endpoint by design.
    # Delete only removes the snapshot row, never the episode itself.
    await get_project_or_404(project_id, current_user.id, db)
    await _get_episode_or_404(episode_id, project_id, db)
    result = await db.execute(
        select(EpisodeRevision).where(
            EpisodeRevision.id == revision_id, EpisodeRevision.episode_id == episode_id
        )
    )
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode revision not found")
    create_audit_log(
        db, current_user.id, AuditAction.EPISODE_REVISION_DELETE,
        resource_type="episode_revision", resource_id=revision.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"episode_id": episode_id, "revision_number": revision.revision_number}
    )
    await db.delete(revision)
    await db.commit()
