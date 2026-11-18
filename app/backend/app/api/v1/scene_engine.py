from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.episode import Episode, Scene, Shot, EpisodeStatus
from app.models.character import Character
from app.models.location import Location
from app.models.scene_engine import SceneEngineTask, SceneEngineTaskStatus, SceneEngineTaskType
from app.models.audit_log import AuditAction
from app.schemas.scene_engine import (
    SceneEngineRequest, SceneEngineResponse, SceneBreakdown,
    EpisodeBreakdownResponse, ShotBreakdown, SceneShotsResponse,
    DialogueResponse, ActionResponse, RefineSceneRequest, RefineSceneResponse
)
from app.services.ai_client import get_ai_client, AIClientError

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


def build_episode_breakdown_prompt(episode: Episode, characters: List[Character], locations: List[Location], total_scenes: int) -> str:
    """Build prompt for episode breakdown into scenes."""
    # All characters are included (audit F-17/P1-07): previously capped at 6.
    char_info = "\n".join([
        f"- {c.name} ({c.role}): {c.personality_traits[:150] if c.personality_traits else 'No traits'}"
        for c in characters
    ]) if characters else "No characters defined."

    loc_info = "\n".join([
        f"- {loc.name} ({loc.type}): {loc.description[:150] if loc.description else 'No description'}"
        for loc in locations[:5]
    ]) if locations else "No locations defined."

    return f"""You are a professional TV series director. Break down this episode into {total_scenes} detailed scenes.

EPISODE:
- Episode Number: {episode.episode_number}
- Title: {episode.title or 'Untitled'}
- Logline: {episode.summary or 'Not specified'}
- Synopsis: {episode.summary or 'Not specified'}

CHARACTERS:
{char_info}

LOCATIONS:
{loc_info}

Generate a JSON response with this exact structure:
{{
  "episode_id": "{episode.id}",
  "total_scenes": {total_scenes},
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene title",
      "description": "2-3 sentence description of what happens",
      "location": "Location name",
      "characters": ["Character A", "Character B"],
      "estimated_duration": "2-3 minutes",
      "beat_type": "setup/inciting_incident/rising_action/complication/midpoint/climax/falling_action/resolution",
      "key_dialogue_hint": "Key dialogue moment hint",
      "action_summary": "Brief action summary"
    }}
  ],
  "generated_at": "ISO timestamp"
}}

Each scene should map to a dramatic beat type (use the 8 standard beats).
Distribute characters and locations naturally across scenes.
Return ONLY valid JSON, no markdown formatting."""


def build_scene_shots_prompt(scene: Scene, episode: Episode, characters: List[Character], total_shots: int) -> str:
    """Build prompt for shot list generation."""
    # All characters are included (audit F-17/P1-07): previously capped at 4.
    char_info = "\n".join([
        f"- {c.name}: {c.personality_traits[:100] if c.personality_traits else ''}"
        for c in characters
    ]) if characters else "No characters defined."

    location_info = ""
    if scene.location:
        location_info = f"- Location: {scene.location.name} ({scene.location.type}): {scene.location.description[:200] if scene.location.description else 'No description'}"

    return f"""You are a professional cinematographer. Create a detailed shot list for this scene.

SCENE:
- Scene Number: {scene.scene_number}
- Title: {scene.title or 'Untitled'}
- Description: {scene.description or 'Not specified'}
{location_info}

EPISODE CONTEXT:
- Episode {episode.episode_number}: {episode.title or 'Untitled'}
- Logline: {episode.summary or 'Not specified'}

CHARACTERS IN THIS EPISODE:
{char_info}

Generate a JSON response with this exact structure:
{{
  "scene_id": "{scene.id}",
  "total_shots": {total_shots},
  "shots": [
    {{
      "shot_number": 1,
      "scene_id": "{scene.id}",
      "shot_type": "wide/medium/closeup/extreme_closeup/over_the_shoulder/two_shot/dutch_angle/point_of_view",
      "camera_angle": "eye_level/high_angle/low_angle/dutch_angle/birdseye/wormseye",
      "camera_movement": "static/pan/tilt/dolly/crane/handheld/steadicam/drone",
      "description": "Detailed description of what the shot shows",
      "characters_in_shot": ["Character A", "Character B"],
      "estimated_duration": "3-5 seconds",
      "visual_notes": "Lighting and color palette notes",
      "audio_cues": "Audio/ambient/sound effect cues"
    }}
  ],
  "generated_at": "ISO timestamp"
}}

Use variety in shot types, angles, and movements. Match shot choices to dramatic moment.
Return ONLY valid JSON, no markdown formatting."""


def build_dialogue_prompt(scene: Scene, episode: Episode, characters: List[Character]) -> str:
    """Build prompt for dialogue generation."""
    char_info = "\n".join([
        f"- {c.name} ({c.role}): Voice: {c.voice_pattern[:100] if c.voice_pattern else 'Not specified'}. "
        f"Personality: {c.personality_traits[:150] if c.personality_traits else 'Not specified'}. "
        f"Background: {c.background[:150] if c.background else 'Not specified'}."
        for c in characters
    ]) if characters else "No characters defined."

    location_info = ""
    if scene.location:
        location_info = f"Location: {scene.location.name} - {scene.location.description[:200] if scene.location.description else ''}"

    return f"""You are a professional TV dialogue writer. Write natural, character-driven dialogue for this scene.

SCENE:
- Scene Number: {scene.scene_number}
- Title: {scene.title or 'Untitled'}
- Description: {scene.description or 'Not specified'}
{location_info}

EPISODE CONTEXT:
- Episode {episode.episode_number}: {episode.title or 'Untitled'}
- Logline: {episode.summary or 'Not specified'}

CHARACTERS:
{char_info}

Generate a JSON response with this exact structure:
{{
  "scene_id": "{scene.id}",
  "dialogue_blocks": [
    {{
      "character": "Character name",
      "line": "Dialogue line",
      "parenthetical": "(tone/direction)" or null,
      "action": "Action/beat description" or null,
      "beat_number": 1
    }}
  ],
  "generated_at": "ISO timestamp"
}}

Write 6-8 dialogue blocks with distinct character voices. Include parentheticals for tone/direction every 2-3 lines.
Include physical actions/beats for about half the lines.
Each character should sound unique based on their voice_pattern and personality.
Return ONLY valid JSON, no markdown formatting."""


def build_action_prompt(scene: Scene, episode: Episode, characters: List[Character]) -> str:
    """Build prompt for action/choreography generation."""
    # All characters are included (audit F-17/P1-07): previously capped at 5.
    char_info = "\n".join([
        f"- {c.name} ({c.role}): Physicality: {c.physical_traits[:150] if c.physical_traits else 'Not specified'}. "
        f"Skills: {c.skills[:150] if c.skills else 'Not specified'}."
        for c in characters
    ]) if characters else "No characters defined."

    location_info = ""
    if scene.location:
        location_info = f"Location: {scene.location.name} ({scene.location.type}): {scene.location.description[:200] if scene.location.description else 'No description'}"

    return f"""You are a professional action/stunt coordinator. Design physical action choreography for this scene.

SCENE:
- Scene Number: {scene.scene_number}
- Title: {scene.title or 'Untitled'}
- Description: {scene.description or 'Not specified'}
{location_info}

EPISODE CONTEXT:
- Episode {episode.episode_number}: {episode.title or 'Untitled'}
- Logline: {episode.summary or 'Not specified'}

CHARACTERS:
{char_info}

Generate a JSON response with this exact structure:
{{
  "scene_id": "{scene.id}",
  "action_beats": [
    {{
      "beat_number": 1,
      "description": "Detailed action description",
      "characters": ["Character A", "Character B"],
      "props": ["Prop 1", "Prop 2"],
      "choreography_notes": "Blocking and timing notes"
    }}
  ],
  "generated_at": "ISO timestamp"
}}

Create 5 action beats with escalating intensity. Include blocking, timing, and specific props.
Match action to character physicalities and skills.
Return ONLY valid JSON, no markdown formatting."""


def build_scene_refine_prompt(original_output: Dict[str, Any], feedback: str, refine_type: str) -> str:
    """Build prompt for scene refinement."""
    return f"""You are a professional TV director/writer. Refine the following scene content based on user feedback.

ORIGINAL OUTPUT:
{json.dumps(original_output, indent=2)}

FEEDBACK: {feedback}
REFINEMENT TYPE: {refine_type}

Generate a JSON response with this exact structure:
{{
  "refined_output": {{...}},  // The entire refined output with same structure as original
  "refinement_notes": "What was changed and why",
  "refined_at": "ISO timestamp"
}}

Return ONLY valid JSON, no markdown formatting."""


async def generate_episode_breakdown_llm(db: AsyncSession, project_id: str, episode: Episode, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate episode breakdown using real LLM."""
    total_scenes = parameters.get("total_scenes", 8) if parameters else 8
    
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
    locations = loc_result.scalars().all()
    
    ai_client = await get_ai_client(db)
    prompt = build_episode_breakdown_prompt(episode, list(characters), list(locations), total_scenes)
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV director. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        output = json.loads(response.content)
        output["generated_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")


async def generate_scene_shots_llm(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate shot list using real LLM."""
    total_shots = parameters.get("total_shots", 12) if parameters else 12
    
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    # Get episode for context
    ep_result = await db.execute(select(Episode).where(Episode.id == scene.episode_id))
    episode = ep_result.scalar_one()
    
    ai_client = await get_ai_client(db)
    prompt = build_scene_shots_prompt(scene, episode, list(characters), total_shots)
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional cinematographer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        output = json.loads(response.content)
        output["generated_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")


async def generate_dialogue_llm(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate dialogue using real LLM."""
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    # Get episode for context
    ep_result = await db.execute(select(Episode).where(Episode.id == scene.episode_id))
    episode = ep_result.scalar_one()
    
    ai_client = await get_ai_client(db)
    prompt = build_dialogue_prompt(scene, episode, list(characters))
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV dialogue writer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        output = json.loads(response.content)
        output["generated_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")


async def generate_action_llm(db: AsyncSession, project_id: str, scene: Scene, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate action/choreography using real LLM."""
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    # Get episode for context
    ep_result = await db.execute(select(Episode).where(Episode.id == scene.episode_id))
    episode = ep_result.scalar_one()
    
    ai_client = await get_ai_client(db)
    prompt = build_action_prompt(scene, episode, list(characters))
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional action coordinator. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        output = json.loads(response.content)
        output["generated_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")


async def refine_scene_output_llm(db: AsyncSession, task: SceneEngineTask, feedback: str, refine_type: str) -> Dict[str, Any]:
    """Refine scene output using real LLM."""
    ai_client = await get_ai_client(db)
    prompt = build_scene_refine_prompt(task.output or {}, feedback, refine_type)
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV director/writer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        output = json.loads(response.content)
        output["refined_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")


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
        if task.task_type in (SceneEngineTaskType.BREAKDOWN_EPISODE, SceneEngineTaskType.GENERATE_SCENES):
            output = await generate_episode_breakdown_llm(db, project_id, episode, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_SHOTS:
            if not scene:
                raise ValueError("Scene ID required for shot generation")
            output = await generate_scene_shots_llm(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_DIALOGUE:
            if not scene:
                raise ValueError("Scene ID required for dialogue generation")
            output = await generate_dialogue_llm(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.GENERATE_ACTION:
            if not scene:
                raise ValueError("Scene ID required for action generation")
            output = await generate_action_llm(db, project_id, scene, task.input_parameters)
        elif task.task_type == SceneEngineTaskType.REFINE_SCENES:
            output = await refine_scene_output_llm(db, task, task.context or "", "general")
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
        
        task.output = output
        task.status = SceneEngineTaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        
        create_audit_log(
            db, current_user.id, AuditAction.SCENE_ENGINE_TASK_EXECUTE,
            resource_type="scene_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_values={"status": "completed", "output_keys": list(output.keys()) if output else []}
        )
        
    except HTTPException as e:
        # Audit F-08: same fix as story engine — a failed execute used to
        # re-raise with the task left in PROCESSING forever. Mark FAILED
        # (persisted) first, then re-raise; FAILED tasks can be retried.
        task.status = SceneEngineTaskStatus.FAILED
        task.error_message = e.detail if isinstance(e.detail, str) else str(e.detail)
        task.completed_at = datetime.now(timezone.utc)
        create_audit_log(
            db, current_user.id, AuditAction.SCENE_ENGINE_TASK_EXECUTE,
            resource_type="scene_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=False,
            error_message=task.error_message
        )
        await db.commit()
        raise
    except Exception as e:
        task.status = SceneEngineTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        
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
    
    refined = await refine_scene_output_llm(db, task, refine_data.feedback, refine_data.refine_type)
    
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
        completed_at=datetime.now(timezone.utc)
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
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_DELETE,
        resource_type="scene_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"task_type": task.task_type.value}
    )
    
    await db.delete(task)
    await db.commit()


@router.post("/{project_id}/scene-engine/tasks/{task_id}/apply", response_model=Dict[str, Any])
async def apply_scene_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Materialize a completed task's output into Scene/Shot/Dialogue rows (audit F-19).

    - BREAKDOWN_EPISODE / GENERATE_SCENES -> Scene rows under the episode
      (existing scene_numbers are skipped, never overwritten).
    - GENERATE_SHOTS -> Shot rows under the task's scene.
    - GENERATE_DIALOGUE -> Dialogue rows under the task's scene
      (existing lines for that scene are replaced by the new generation).
    - GENERATE_ACTION -> stores the beats as the scene's action text.
    """
    from app.models.dialogue import Dialogue
    from app.models.episode import SceneStatus, ShotStatus

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
    if task.status != SceneEngineTaskStatus.COMPLETED or not task.output:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only apply completed tasks with output")

    episode = await get_episode_or_404(task.episode_id, project_id, db)

    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    char_by_name = {c.name.lower(): c for c in char_result.scalars().all()}
    loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
    loc_by_name = {loc.name.lower(): loc for loc in loc_result.scalars().all()}

    created: Dict[str, Any] = {}
    skipped: list = []

    if task.task_type in (SceneEngineTaskType.BREAKDOWN_EPISODE, SceneEngineTaskType.GENERATE_SCENES):
        scenes_data = task.output.get("scenes") or []
        existing_result = await db.execute(
            select(Scene.scene_number).where(Scene.episode_id == episode.id)
        )
        existing_numbers = {row[0] for row in existing_result.all()}
        made = []
        for s in scenes_data:
            try:
                number = int(s.get("scene_number"))
            except (TypeError, ValueError):
                skipped.append({"scene": s.get("title"), "reason": "missing scene_number"})
                continue
            if number in existing_numbers:
                skipped.append({"scene_number": number, "reason": "already exists"})
                continue
            location = loc_by_name.get(str(s.get("location") or "").lower())
            chars = s.get("characters") or []
            scene = Scene(
                episode_id=episode.id,
                scene_number=number,
                title=(s.get("title") or f"Scene {number}")[:255],
                description=s.get("description"),
                location_id=location.id if location else None,
                status=SceneStatus.WRITTEN,
                action=s.get("action_summary"),
                characters_present=json.dumps(chars),
            )
            db.add(scene)
            existing_numbers.add(number)
            made.append({"scene_number": number, "title": scene.title})
        created["scenes"] = made
        episode.status = EpisodeStatus.SCENES_WRITTEN

    elif task.task_type == SceneEngineTaskType.GENERATE_SHOTS:
        if not task.scene_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task has no scene to apply shots to")
        scene = await get_scene_or_404(task.scene_id, task.episode_id, db)
        shots_data = task.output.get("shots") or []
        existing_result = await db.execute(
            select(Shot.shot_number).where(Shot.scene_id == scene.id)
        )
        existing_numbers = {row[0] for row in existing_result.all()}
        made = []
        for sh in shots_data:
            try:
                number = int(sh.get("shot_number"))
            except (TypeError, ValueError):
                skipped.append({"shot": sh.get("description"), "reason": "missing shot_number"})
                continue
            if number in existing_numbers:
                skipped.append({"shot_number": number, "reason": "already exists"})
                continue
            shot = Shot(
                scene_id=scene.id,
                shot_number=number,
                shot_type=sh.get("shot_type"),
                camera_angle=sh.get("camera_angle"),
                camera_movement=sh.get("camera_movement"),
                description=sh.get("description"),
                characters_in_shot=json.dumps(sh.get("characters_in_shot") or []),
                status=ShotStatus.PROMPT_READY,
                image_prompt=sh.get("visual_notes"),
                video_prompt=sh.get("audio_cues"),
            )
            db.add(shot)
            existing_numbers.add(number)
            made.append({"shot_number": number, "shot_type": shot.shot_type})
        created["shots"] = made

    elif task.task_type == SceneEngineTaskType.GENERATE_DIALOGUE:
        if not task.scene_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task has no scene to apply dialogue to")
        scene = await get_scene_or_404(task.scene_id, task.episode_id, db)
        blocks = task.output.get("dialogue_blocks") or []
        # Replace previous generated dialogue for this scene.
        old_result = await db.execute(select(Dialogue).where(Dialogue.scene_id == scene.id))
        for old in old_result.scalars().all():
            await db.delete(old)
        made = []
        for i, b in enumerate(blocks):
            try:
                line_number = int(b.get("beat_number") or i + 1)
            except (TypeError, ValueError):
                line_number = i + 1
            char = char_by_name.get(str(b.get("character") or "").lower())
            dialogue = Dialogue(
                scene_id=scene.id,
                character_id=char.id if char else None,
                line_number=line_number,
                character_name=str(b.get("character") or "Unknown")[:255],
                dialogue_text=str(b.get("line") or ""),
                parenthetical=b.get("parenthetical"),
                action=b.get("action"),
                beat_number=line_number,
            )
            db.add(dialogue)
            made.append({"line_number": line_number, "character": dialogue.character_name})
        created["dialogues"] = made

    elif task.task_type == SceneEngineTaskType.GENERATE_ACTION:
        if not task.scene_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task has no scene to apply action to")
        scene = await get_scene_or_404(task.scene_id, task.episode_id, db)
        beats = task.output.get("action_beats") or []
        scene.action = "\n".join(
            f"{b.get('beat_number', i + 1)}. {b.get('description', '')}"
            for i, b in enumerate(beats)
        ) or scene.action
        created["action_beats"] = len(beats)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task type {task.task_type.value} has no rows to apply"
        )

    await db.commit()

    create_audit_log(
        db, current_user.id, AuditAction.SCENE_ENGINE_TASK_UPDATE,
        resource_type="scene_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"applied": created, "skipped": len(skipped)}
    )
    await db.commit()

    return {"created": created, "skipped": skipped}