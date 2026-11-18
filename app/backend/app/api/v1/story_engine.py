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
from app.models.series_bible import SeriesBible
from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode, EpisodeStatus
from app.models.story_engine import StoryEngineTask, StoryEngineTaskStatus, StoryEngineTaskType
from app.models.audit_log import AuditAction
from app.schemas.story_engine import (
    StoryEngineRequest, StoryEngineResponse, EpisodeOutline, 
    StoryOutlineResponse, CharacterArcResponse, WorldBuildingResponse,
    RefineStoryRequest, RefineStoryResponse
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


async def get_series_bible_or_404(series_bible_id: str, project_id: str, db: AsyncSession) -> SeriesBible:
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.id == series_bible_id, SeriesBible.project_id == project_id)
    )
    sb = result.scalar_one_or_none()
    if not sb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series Bible not found"
        )
    return sb


def task_to_response(task: StoryEngineTask) -> StoryEngineResponse:
    return StoryEngineResponse(
        id=task.id,
        project_id=task.project_id,
        series_bible_id=task.series_bible_id,
        task_type=task.task_type,
        status=task.status,
        input_parameters=task.input_parameters,
        output=task.output,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at
    )


def build_story_outline_prompt(series_bible: SeriesBible, characters: List[Character], total_episodes: int, user_context: Optional[str] = None) -> str:
    """Build prompt for story outline generation."""
    # All characters are included (audit F-17/P1-07): previously only the
    # first 5 were used, silently dropping character 6+. Each entry is kept
    # short so long casts still fit the prompt.
    char_info = "\n".join([
        f"- {c.name} ({c.role}): {c.background[:200] if c.background else 'No background'}"
        for c in characters
    ]) if characters else "No characters defined yet."

    context_block = ""
    if user_context:
        context_block = f"\nUSER INSTRUCTIONS (follow these first):\n{user_context}\n"

    return f"""You are a professional TV series writer. Create a detailed episode-by-episode outline for a {total_episodes}-episode micro-drama series.

SERIES BIBLE:
- Premise: {series_bible.premise or 'Not specified'}
- Main Plot: {series_bible.main_plot or 'Not specified'}
- Subplots: {series_bible.subplots or 'Not specified'}
- Tone & Visual Style: {series_bible.tone_and_visual_style or 'Not specified'}
- Ending Direction: {series_bible.ending_direction or 'Not specified'}
{context_block}
CHARACTERS:
{char_info}

Generate a JSON response with this exact structure:
{{
  "series_bible_id": "{series_bible.id}",
  "total_episodes": {total_episodes},
  "episodes": [
    {{
      "episode_number": 1,
      "title": "Episode title",
      "logline": "One-sentence hook",
      "synopsis": "2-3 paragraph summary",
      "key_beats": ["beat 1", "beat 2", "beat 3", "beat 4", "beat 5"],
      "character_focus": ["Character A", "Character B"]
    }}
  ],
  "generated_at": "ISO timestamp"
}}

Each episode should have 5 key beats following dramatic structure: Setup, Inciting Incident, Rising Action, Climax, Resolution.
Character focus should list 2-3 main characters per episode.
Return ONLY valid JSON, no markdown formatting."""


def build_character_arcs_prompt(series_bible: SeriesBible, characters: List[Character]) -> str:
    """Build prompt for character arcs generation."""
    char_info = "\n".join([
        f"- {c.name} ({c.role}): Age {c.age or '?'}, {c.gender or '?'}, {c.ethnicity or '?'}. "
        f"Background: {c.background[:300] if c.background else 'Not specified'}. "
        f"Motivations: {c.motivations[:200] if c.motivations else 'Not specified'}. "
        f"Fears: {c.fears[:200] if c.fears else 'Not specified'}. "
        f"Personality: {c.personality_traits[:200] if c.personality_traits else 'Not specified'}."
        for c in characters
    ]) if characters else "No characters defined yet."

    return f"""You are a professional TV series writer. Create detailed character arcs for each character in this micro-drama series.

SERIES BIBLE:
- Premise: {series_bible.premise or 'Not specified'}
- Main Plot: {series_bible.main_plot or 'Not specified'}
- Tone: {series_bible.tone_and_visual_style or 'Not specified'}

CHARACTERS:
{char_info}

Generate a JSON response with this exact structure:
{{
  "arcs": [
    {{
      "character_id": "uuid",
      "character_name": "Name",
      "arc_summary": "Overall transformation summary",
      "key_moments": [
        {{"episode": 1, "moment": "Description"}},
        {{"episode": 5, "moment": "Description"}},
        {{"episode": 10, "moment": "Description"}},
        {{"episode": 15, "moment": "Description"}},
        {{"episode": 20, "moment": "Description"}}
      ],
      "emotional_journey": "Stage1 -> Stage2 -> Stage3 -> Stage4 -> Stage5"
    }}
  ]
}}

Each character should have 5 key moments across the series (episodes 1, 5, 10, 15, 20).
Emotional journey should show 5 emotional stages.
Return ONLY valid JSON, no markdown formatting."""


def build_world_building_prompt(series_bible: SeriesBible, locations: List[Location], characters: List[Character]) -> str:
    """Build prompt for world building generation."""
    loc_info = "\n".join([
        f"- {loc.name} ({loc.type}): {loc.description[:200] if loc.description else 'No description'}"
        for loc in locations
    ]) if locations else "No locations defined yet."

    return f"""You are a professional TV series writer. Create comprehensive world building for this micro-drama series.

SERIES BIBLE:
- Premise: {series_bible.premise or 'Not specified'}
- Main Plot: {series_bible.main_plot or 'Not specified'}
- World Settings: {series_bible.world_settings or 'Not specified'}

EXISTING LOCATIONS:
{loc_info}

Generate a JSON response with this exact structure:
{{
  "series_bible_id": "{series_bible.id}",
  "locations": [
    {{"name": "Location name", "type": "urban/rural/hidden/etc", "description": "Detailed description"}}
  ],
  "factions": [
    {{"name": "Faction name", "type": "government/rebel/corporate/etc", "description": "Description"}}
  ],
  "technology": [
    {{"name": "Tech name", "description": "Description"}}
  ],
  "culture": [
    {{"name": "Cultural element", "description": "Description"}}
  ],
  "history": [
    {{"event": "Historical event", "year": "Year", "description": "Description"}}
  ],
  "generated_at": "ISO timestamp"
}}

Include at least 3 locations (use existing + add new), 2-3 factions, 2-3 technologies, 2-3 cultural elements, and 2-3 historical events.
Return ONLY valid JSON, no markdown formatting."""


def build_refine_prompt(original_output: Dict[str, Any], feedback: str, refine_type: str) -> str:
    """Build prompt for story refinement."""
    return f"""You are a professional TV series writer. Refine the following story content based on user feedback.

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


def build_single_episode_prompt(series_bible: SeriesBible, characters: List[Character], episode_number: int, user_context: Optional[str] = None) -> str:
    """Build prompt for generating one episode (GENERATE_EPISODE)."""
    char_info = "\n".join([
        f"- {c.name} ({c.role}): {c.background[:200] if c.background else 'No background'}"
        for c in characters
    ]) if characters else "No characters defined yet."

    context_block = ""
    if user_context:
        context_block = f"\nUSER INSTRUCTIONS (follow these first):\n{user_context}\n"

    return f"""You are a professional TV series writer. Create a detailed outline for ONE episode (episode {episode_number}) of a micro-drama series.

SERIES BIBLE:
- Premise: {series_bible.premise or 'Not specified'}
- Main Plot: {series_bible.main_plot or 'Not specified'}
- Subplots: {series_bible.subplots or 'Not specified'}
- Tone & Visual Style: {series_bible.tone_and_visual_style or 'Not specified'}
- Ending Direction: {series_bible.ending_direction or 'Not specified'}
{context_block}
CHARACTERS:
{char_info}

Generate a JSON response with this exact structure:
{{
  "series_bible_id": "{series_bible.id}",
  "episode_number": {episode_number},
  "title": "Episode title",
  "logline": "One-sentence hook",
  "synopsis": "2-3 paragraph summary",
  "key_beats": ["beat 1", "beat 2", "beat 3", "beat 4", "beat 5"],
  "character_focus": ["Character A", "Character B"]
}}

The episode should have 5 key beats following dramatic structure: Setup, Inciting Incident, Rising Action, Climax, Resolution.
Character focus should list 2-3 main characters for this episode.
Return ONLY valid JSON, no markdown formatting."""


async def generate_story_outline_llm(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None, user_context: Optional[str] = None) -> Dict[str, Any]:
    """Generate story outline using real LLM."""
    total_episodes = parameters.get("total_episodes", 20) if parameters else 20

    result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = result.scalars().all()

    ai_client = await get_ai_client(db)
    prompt = build_story_outline_prompt(series_bible, list(characters), total_episodes, user_context)
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
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


async def generate_single_episode_llm(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None, user_context: Optional[str] = None) -> Dict[str, Any]:
    """Generate a single episode outline using real LLM (GENERATE_EPISODE)."""
    episode_number = 1
    if parameters:
        try:
            episode_number = int(parameters.get("episode_number", 1))
        except (TypeError, ValueError):
            episode_number = 1

    result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = result.scalars().all()

    ai_client = await get_ai_client(db)
    prompt = build_single_episode_prompt(series_bible, list(characters), episode_number, user_context)

    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
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


async def generate_character_arcs_llm(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate character arcs using real LLM."""
    result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = result.scalars().all()
    
    ai_client = await get_ai_client(db)
    prompt = build_character_arcs_prompt(series_bible, list(characters))
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
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


async def generate_world_building_llm(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate world building using real LLM."""
    result = await db.execute(select(Location).where(Location.project_id == project_id))
    locations = result.scalars().all()
    
    char_result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = char_result.scalars().all()
    
    ai_client = await get_ai_client(db)
    prompt = build_world_building_prompt(series_bible, list(locations), list(characters))
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
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


async def refine_story_output_llm(db: AsyncSession, task: StoryEngineTask, feedback: str, refine_type: str) -> Dict[str, Any]:
    """Refine story output using real LLM."""
    ai_client = await get_ai_client(db)
    prompt = build_refine_prompt(task.output or {}, feedback, refine_type)
    
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
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


@router.post("/{project_id}/story-engine/tasks", response_model=StoryEngineResponse, status_code=status.HTTP_201_CREATED)
async def create_story_task(
    project_id: str,
    task_data: StoryEngineRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    series_bible = await get_series_bible_or_404(task_data.series_bible_id, project_id, db)
    
    task = StoryEngineTask(
        project_id=project_id,
        series_bible_id=task_data.series_bible_id,
        task_type=task_data.task_type,
        input_parameters=task_data.parameters,
        context=task_data.context,
        status=StoryEngineTaskStatus.PENDING
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    create_audit_log(
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_CREATE,
        resource_type="story_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"task_type": task.task_type.value, "series_bible_id": str(task.series_bible_id)}
    )
    await db.commit()
    
    return task_to_response(task)


@router.post("/{project_id}/story-engine/tasks/{task_id}/execute", response_model=StoryEngineResponse)
async def execute_story_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(StoryEngineTask).where(
            StoryEngineTask.id == task_id, 
            StoryEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story engine task not found")
    
    if task.status == StoryEngineTaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Task already processing")
    
    # Get series bible for generation
    series_bible = await get_series_bible_or_404(task.series_bible_id, project_id, db)
    
    # Update status to processing
    task.status = StoryEngineTaskStatus.PROCESSING
    await db.commit()
    
    try:
        # Execute based on task type
        if task.task_type == StoryEngineTaskType.GENERATE_OUTLINE:
            output = await generate_story_outline_llm(db, project_id, series_bible, task.input_parameters, task.context)
        elif task.task_type == StoryEngineTaskType.GENERATE_EPISODE:
            output = await generate_single_episode_llm(db, project_id, series_bible, task.input_parameters, task.context)
        elif task.task_type == StoryEngineTaskType.GENERATE_CHARACTER_ARCS:
            output = await generate_character_arcs_llm(db, project_id, series_bible, task.input_parameters)
        elif task.task_type == StoryEngineTaskType.GENERATE_WORLD_BUILDING:
            output = await generate_world_building_llm(db, project_id, series_bible, task.input_parameters)
        elif task.task_type == StoryEngineTaskType.REFINE_STORY:
            output = await refine_story_output_llm(db, task, task.context or "", "general")
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
        
        task.output = output
        task.status = StoryEngineTaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        
        create_audit_log(
            db, current_user.id, AuditAction.STORY_ENGINE_TASK_EXECUTE,
            resource_type="story_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_values={"status": "completed", "output_keys": list(output.keys()) if output else []}
        )
        
    except HTTPException as e:
        # Audit F-08: a failed execute used to re-raise without touching the
        # row, leaving the task stuck in PROCESSING forever (retry -> 400).
        # Mark it FAILED first (persisted), then re-raise so the caller
        # still sees the original error status. FAILED tasks can be retried:
        # execute only refuses PROCESSING tasks.
        task.status = StoryEngineTaskStatus.FAILED
        task.error_message = e.detail if isinstance(e.detail, str) else str(e.detail)
        task.completed_at = datetime.now(timezone.utc)
        create_audit_log(
            db, current_user.id, AuditAction.STORY_ENGINE_TASK_EXECUTE,
            resource_type="story_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=False,
            error_message=task.error_message
        )
        await db.commit()
        raise
    except Exception as e:
        task.status = StoryEngineTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        
        create_audit_log(
            db, current_user.id, AuditAction.STORY_ENGINE_TASK_EXECUTE,
            resource_type="story_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=False,
            error_message=str(e)
        )
    
    await db.commit()
    await db.refresh(task)
    
    return task_to_response(task)


@router.get("/{project_id}/story-engine/tasks", response_model=List[StoryEngineResponse])
async def list_story_tasks(
    project_id: str,
    request: Request,
    series_bible_id: Optional[str] = None,
    task_type: Optional[StoryEngineTaskType] = None,
    status_filter: Optional[StoryEngineTaskStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    query = select(StoryEngineTask).where(StoryEngineTask.project_id == project_id)
    
    if series_bible_id:
        query = query.where(StoryEngineTask.series_bible_id == series_bible_id)
    if task_type:
        query = query.where(StoryEngineTask.task_type == task_type)
    if status_filter:
        query = query.where(StoryEngineTask.status == status_filter)
    
    query = query.order_by(StoryEngineTask.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_READ,
        resource_type="story_engine_task", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return [task_to_response(t) for t in tasks]


@router.get("/{project_id}/story-engine/tasks/{task_id}", response_model=StoryEngineResponse)
async def get_story_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(StoryEngineTask).where(
            StoryEngineTask.id == task_id, 
            StoryEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story engine task not found")
    
    return task_to_response(task)


@router.post("/{project_id}/story-engine/tasks/{task_id}/refine", response_model=RefineStoryResponse)
async def refine_story_task(
    project_id: str,
    task_id: str,
    refine_data: RefineStoryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(StoryEngineTask).where(
            StoryEngineTask.id == task_id, 
            StoryEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story engine task not found")
    
    if task.status != StoryEngineTaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only refine completed tasks")
    
    refined = await refine_story_output_llm(db, task, refine_data.feedback, refine_data.refine_type)
    
    # Create new task for refinement
    new_task = StoryEngineTask(
        project_id=project_id,
        series_bible_id=task.series_bible_id,
        task_type=StoryEngineTaskType.REFINE_STORY,
        input_parameters={"original_task_id": str(task.id), "feedback": refine_data.feedback},
        context=refine_data.feedback,
        output=refined,
        status=StoryEngineTaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc)
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    create_audit_log(
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_UPDATE,
        resource_type="story_engine_task", resource_id=new_task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"refined_from": str(task.id), "feedback": refine_data.feedback}
    )
    await db.commit()
    
    return RefineStoryResponse(
        task_id=new_task.id,
        refined_output=refined,
        refined_at=new_task.completed_at
    )


@router.delete("/{project_id}/story-engine/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(StoryEngineTask).where(
            StoryEngineTask.id == task_id, 
            StoryEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story engine task not found")
    
    create_audit_log(
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_DELETE,
        resource_type="story_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"task_type": task.task_type.value}
    )
    
    await db.delete(task)
    await db.commit()


@router.post("/{project_id}/story-engine/tasks/{task_id}/apply", response_model=Dict[str, Any])
async def apply_story_task(
    project_id: str,
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Materialize a completed task's output into Episode rows (audit F-19).

    Only GENERATE_OUTLINE / GENERATE_EPISODE outputs are applied: each
    episode entry becomes an Episode row (existing episode_numbers are
    skipped, never overwritten). Other task types return 400.
    """
    project = await get_project_or_404(project_id, current_user.id, db)

    result = await db.execute(
        select(StoryEngineTask).where(
            StoryEngineTask.id == task_id,
            StoryEngineTask.project_id == project_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story engine task not found")
    if task.status != StoryEngineTaskStatus.COMPLETED or not task.output:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only apply completed tasks with output")

    if task.task_type == StoryEngineTaskType.GENERATE_OUTLINE:
        episodes_data = task.output.get("episodes") or []
    elif task.task_type == StoryEngineTaskType.GENERATE_EPISODE:
        episodes_data = [task.output]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task type {task.task_type.value} has no episode rows to apply"
        )

    existing_result = await db.execute(
        select(Episode.episode_number).where(Episode.project_id == project_id)
    )
    existing_numbers = {row[0] for row in existing_result.all()}

    created, skipped = [], []
    for ep in episodes_data:
        try:
            number = int(ep.get("episode_number"))
        except (TypeError, ValueError):
            skipped.append({"episode": ep.get("title"), "reason": "missing episode_number"})
            continue
        if number in existing_numbers:
            skipped.append({"episode_number": number, "reason": "already exists"})
            continue
        episode = Episode(
            project_id=project_id,
            episode_number=number,
            title=(ep.get("title") or f"Episode {number}")[:255],
            summary=ep.get("synopsis") or ep.get("logline"),
            status=EpisodeStatus.OUTLINED,
        )
        db.add(episode)
        existing_numbers.add(number)
        created.append({"episode_number": number, "title": episode.title})

    await db.commit()

    create_audit_log(
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_UPDATE,
        resource_type="story_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"applied_episodes": len(created), "skipped": len(skipped)}
    )
    await db.commit()

    return {"created_episodes": created, "skipped": skipped}