from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.episode import Episode, Scene, Shot
from app.models.character import Character
from app.models.location import Location
from app.models.scene_engine import SceneEngineTask, SceneEngineTaskStatus, SceneEngineTaskType
from app.models.audit_log import AuditAction
from app.schemas.scene_engine import (
    SceneEngineRequest, SceneEngineResponse, SceneBreakdown,
    EpisodeBreakdownResponse, ShotBreakdown, SceneShotsResponse,
    DialogueResponse, ActionResponse, RefineSceneRequest, RefineSceneResponse
)

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


async def get_episode_or_404(episode_id: str, project_id: str, db: AsyncSession) -> Episode:
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    return episode


async def get_scene_or_404(scene_id: str, episode_id: str, db: AsyncSession) -> Scene:
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found"
        )
    return scene


def task_to_response(task: SceneEngineTask) -> SceneEngineResponse:
    return SceneEngineResponse(
        id=task.id,
        project_id=task.project_id,
        episode_id=task.episode_id,
        scene_id=task.scene_id,
        task_type=task.task_type,
        status=task.status,
        input_parameters=task.input_parameters,
        output=task.output,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at
    )


async def generate_episode_breakdown(db: AsyncSession, project_id: str, episode: Episode, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI episode breakdown into scenes."""
    total_scenes = parameters.get("total_scenes", 8) if parameters else 8
    
    # Get characters and locations for this project
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
    locations = loc_result.scalars().all()
    
    scenes = []
    beat_types = ["setup", "inciting_incident", "rising_action", "complication", "midpoint", "climax", "falling_action", "resolution"]
    
    for i in range(1, total_scenes + 1):
        beat_type = beat_types[min(i-1, len(beat_types)-1)]
        scenes.append({
            "scene_number": i,
            "title": f"Scene {i}: {beat_type.replace('_', ' ').title()}",
            "description": f"Scene {i} advances the {beat_type} beat of episode {episode.episode_number}. Key story moments unfold.",
            "location": locations[i % len(locations)].name if locations else f"Location {i}",
            "characters": [c.name for c in characters[:3]] if characters else ["Protagonist", "Supporting"],
            "estimated_duration": "2-3 minutes",
            "beat_type": beat_type,
            "key_dialogue_hint": f"Key dialogue moment for {beat_type}",
            "action_summary": f"Action sequence supporting {beat_type} beat"
        })
    
    return {
        "episode_id": str(episode.id),
        "total_scenes": total_scenes,
        "scenes": scenes,
        "generated_at": datetime.utcnow().isoformat()
    }


async def generate_scene_shots(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI shot list generation for a scene."""
    total_shots = parameters.get("total_shots", 12) if parameters else 12
    
    # Get characters for this project
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    shot_types = ["wide", "medium", "closeup", "extreme_closeup", "over_the_shoulder", "two_shot", "dutch_angle", "point_of_view"]
    camera_angles = ["eye_level", "high_angle", "low_angle", "dutch_angle", "birdseye", "wormseye"]
    camera_movements = ["static", "pan", "tilt", "dolly", "crane", "handheld", "steadicam", "drone"]
    
    shots = []
    for i in range(1, total_shots + 1):
        shots.append({
            "shot_number": i,
            "scene_id": str(scene.id),
            "shot_type": shot_types[i % len(shot_types)],
            "camera_angle": camera_angles[i % len(camera_angles)],
            "camera_movement": camera_movements[i % len(camera_movements)],
            "description": f"Shot {i} of scene {scene.scene_number}: {shot_types[i % len(shot_types)]} {camera_angles[i % len(camera_angles)]} shot with {camera_movements[i % len(camera_movements)]} movement.",
            "characters_in_shot": [c.name for c in characters[:2]] if characters else ["Protagonist"],
            "estimated_duration": "3-5 seconds",
            "visual_notes": f"Lighting: {['natural', 'dramatic', 'soft', 'harsh'][i % 4]}; Color palette: {['warm', 'cool', 'neutral', 'contrast'][i % 4]}",
            "audio_cues": f"Ambient: {['silence', 'room_tone', 'music_swell', 'sound_effect'][i % 4]}"
        })
    
    return {
        "scene_id": str(scene.id),
        "total_shots": total_shots,
        "shots": shots,
        "generated_at": datetime.utcnow().isoformat()
    }


async def generate_dialogue(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI dialogue generation for a scene."""
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    char_names = [c.name for c in characters] if characters else ["Protagonist", "Antagonist", "Supporting"]
    
    dialogue_blocks = []
    for i in range(6):
        speaker = char_names[i % len(char_names)]
        dialogue_blocks.append({
            "character": speaker,
            "line": f"This is {speaker}'s line {i+1} in scene {scene.scene_number}.",
            "parenthetical": f"({['calm', 'angry', 'whispered', 'shouted', 'sarcastic', 'earnest'][i % 6]})" if i % 3 == 0 else None,
            "action": f"{speaker} {['looks around', 'paces', 'sits down', 'stands up', 'gestures', 'freezes'][i % 6]}." if i % 2 == 0 else None,
            "beat_number": i + 1
        })
    
    return {
        "scene_id": str(scene.id),
        "dialogue_blocks": dialogue_blocks,
        "generated_at": datetime.utcnow().isoformat()
    }


async def generate_action(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI action/choreography generation for a scene."""
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    char_names = [c.name for c in characters] if characters else ["Protagonist", "Antagonist", "Supporting"]
    
    action_beats = []
    for i in range(5):
        action_beats.append({
            "beat_number": i + 1,
            "description": f"Action beat {i+1}: {['Chase sequence', 'Fight choreography', 'Emotional confrontation', 'Discovery moment', 'Escape sequence'][i % 5]} in scene {scene.scene_number}.",
            "characters": char_names[:3],
            "props": [f"Prop {j}" for j in range(1, 4)],
            "choreography_notes": f"Blocking: {['wide to tight', 'circular', 'linear', 'static with movement', 'dynamic'][i % 5]}; Timing: {['slow build', 'fast pace', 'rhythmic', 'explosive', 'measured'][i % 5]}"
        })
    
    return {
        "scene_id": str(scene.id),
        "action_beats": action_beats,
        "generated_at": datetime.utcnow().isoformat()
    }


async def refine_scene_output(task: SceneEngineTask, feedback: str, refine_type: str) -> Dict[str, Any]:
    """Mock AI scene refinement."""
    return {
        "refined_output": task.output,
        "refinement_notes": f"Applied {refine_type} refinement based on: {feedback}",
        "refined_at": datetime.utcnow().isoformat()
    }


@router.post("/{project_id}/scene-engine/tasks", response_model=SceneEngineResponse, status_code=status.HTTP_201_CREATED)
async def create_scene_task(
    project_id: str,
    task_data: SceneEngineRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    episode = await get_episode_or_404(task_data.episode_id, project_id, db)
    
    scene = None
    if task_data.scene_id:
        scene = await get_scene_or_404(task_data.scene_id, task_data.episode_id, db)
    
    task = SceneEngineTask(
        project_id=project_id,
        episode_id=task_data.episode_id,
        scene_id=task_data.scene_id,
        task_type=task_data.task_type,
        input_parameters=task_data.parameters,
        context=task_data.context,
        status=SceneEngineTaskStatus.PENDING
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_CREATE,
        resource_type="scene_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"task_type": task.task_type.value, "episode_id": str(task.episode_id)}
    )
    await db.commit()
    
    return task_to_response(task)


@router.post("/{project_id}/scene-engine/tasks/{task_id}/execute", response_model=SceneEngineResponse)
async def execute_scene_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SceneEngineTask).where(
            SceneEngineTask.id == task_id, 
            SceneEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene engine task not found")
    
    if task.status == SceneEngineTaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Task already processing")
    
    # Get episode/scene for generation
    episode = await get_episode_or_404(task.episode_id, project_id, db)
    scene = None
    if task.scene_id:
        scene = await get_scene_or_404(task.scene_id, task.episode_id, db)
    
    # Update status to processing
    task.status = SceneEngineTaskStatus.PROCESSING
    await db.commit()
    
    try:
        # Execute based on task type
        if task.task_type == SceneEngineTaskType.BREAKDOWN_EPISODE:
            output = await generate_episode_breakdown(db, project_id, episode, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_SHOTS:
            if not scene:
                raise ValueError("Scene ID required for shot generation")
            output = await generate_scene_shots(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_DIALOGUE:
            if not scene:
                raise ValueError("Scene ID required for dialogue generation")
            output = await generate_dialogue(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_ACTION:
            if not scene:
                raise ValueError("Scene ID required for action generation")
            output = await generate_action(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.REFINE_SCENES:
            output = await refine_scene_output(task, task.context or "", "general")
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
        
        task.output = output
        task.status = SceneEngineTaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        create_audit_log(
            db, current_user.id, AuditAction.SCENE_ENGINE_TASK_EXECUTE,
            resource_type="scene_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_values={"status": "completed", "output_keys": list(output.keys()) if output else []}
        )
        
    except Exception as e:
        task.status = SceneEngineTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        
        create_audit_log(
            db, current_user.id, AuditAction.SCENE_ENGINE_TASK_EXECUTE,
            resource_type="scene_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=False,
            error_message=str(e)
        )
    
    await db.commit()
    await db.refresh(task)
    
    return task_to_response(task)


@router.get("/{project_id}/scene-engine/tasks", response_model=List[SceneEngineResponse])
async def list_scene_tasks(
    project_id: str,
    request: Request,
    episode_id: Optional[str] = None,
    scene_id: Optional[str] = None,
    task_type: Optional[SceneEngineTaskType] = None,
    status_filter: Optional[SceneEngineTaskStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    query = select(SceneEngineTask).where(SceneEngineTask.project_id == project_id)
    
    if episode_id:
        query = query.where(SceneEngineTask.episode_id == episode_id)
    if scene_id:
        query = query.where(SceneEngineTask.scene_id == scene_id)
    if task_type:
        query = query.where(SceneEngineTask.task_type == task_type)
    if status_filter:
        query = query.where(SceneEngineTask.status == status_filter)
    
    query = query.order_by(SceneEngineTask.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_READ,
        resource_type="scene_engine_task", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return [task_to_response(t) for t in tasks]


@router.get("/{project_id}/scene-engine/tasks/{task_id}", response_model=SceneEngineResponse)
async def get_scene_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SceneEngineTask).where(
            SceneEngineTask.id == task_id, 
            SceneEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene engine task not found")
    
    return task_to_response(task)


@router.post("/{project_id}/scene-engine/tasks/{task_id}/refine", response_model=RefineSceneResponse)
async def refine_scene_task(
    project_id: str,
    task_id: str,
    refine_data: RefineSceneRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SceneEngineTask).where(
            SceneEngineTask.id == task_id, 
            SceneEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene engine task not found")
    
    if task.status != SceneEngineTaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only refine completed tasks")
    
    refined = await refine_scene_output(task, refine_data.feedback, refine_data.refine_type)
    
    # Create new task for refinement
    new_task = SceneEngineTask(
        project_id=project_id,
        episode_id=task.episode_id,
        scene_id=task.scene_id,
        task_type=SceneEngineTaskType.REFINE_SCENES,
        input_parameters={"original_task_id": str(task.id), "feedback": refine_data.feedback},
        context=refine_data.feedback,
        output=refined,
        status=SceneEngineTaskStatus.COMPLETED,
        completed_at=datetime.utcnow()
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_UPDATE,
        resource_type="scene_engine_task", resource_id=new_task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"refined_from": str(task.id), "feedback": refine_data.feedback}
    )
    await db.commit()
    
    return RefineSceneResponse(
        task_id=new_task.id,
        refined_output=refined,
        refined_at=new_task.completed_at
    )


@router.delete("/{project_id}/scene-engine/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(SceneEngineTask).where(
            SceneEngineTask.id == task_id, 
            SceneEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene engine task not found")
    
    create_audit_log(
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_CREATE,
        resource_type="scene_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"task_type": task.task_type.value}
    )
    
    await db.delete(task)
    await db.commit()