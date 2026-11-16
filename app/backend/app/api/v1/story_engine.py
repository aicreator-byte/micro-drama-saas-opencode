from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode
from app.models.story_engine import StoryEngineTask, StoryEngineTaskStatus, StoryEngineTaskType
from app.models.audit_log import AuditAction
from app.schemas.story_engine import (
    StoryEngineRequest, StoryEngineResponse, EpisodeOutline, 
    StoryOutlineResponse, CharacterArcResponse, WorldBuildingResponse,
    RefineStoryRequest, RefineStoryResponse
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


async def generate_story_outline(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI story generation - replace with actual LLM call."""
    total_episodes = parameters.get("total_episodes", 20) if parameters else 20
    
    # Get characters for this project
    result = await db.execute(select(Character).where(Character.project_id == project_id).limit(5))
    characters = result.scalars().all()
    
    episodes = []
    for i in range(1, total_episodes + 1):
        episodes.append({
            "episode_number": i,
            "title": f"Episode {i}: {series_bible.premise[:30]} - Part {i}" if series_bible.premise else f"Episode {i}",
            "logline": f"In this episode, the protagonists face a new challenge related to {series_bible.main_plot[:40]}." if series_bible.main_plot else f"Episode {i} continues the story.",
            "synopsis": f"Episode {i} continues the story of {series_bible.premise}. The main conflict deepens as {series_bible.main_plot}. Key characters develop their arcs." if series_bible.premise else f"Episode {i} synopsis.",
            "key_beats": [
                f"Opening: Establish the stakes for episode {i}",
                f"Inciting incident: New complication arises",
                f"Rising action: Characters investigate/respond",
                f"Climax: Major confrontation or revelation",
                f"Resolution: Temporary resolution, setup for next episode"
            ],
            "character_focus": [c.name for c in characters[:3]] if characters else ["Protagonist", "Antagonist", "Supporting"]
        })
    
    return {
        "series_bible_id": str(series_bible.id),
        "total_episodes": total_episodes,
        "episodes": episodes,
        "generated_at": datetime.utcnow().isoformat()
    }


async def generate_character_arcs(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI character arc generation."""
    result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = result.scalars().all()
    
    arcs = []
    for char in characters:
        arcs.append({
            "character_id": str(char.id),
            "character_name": char.name,
            "arc_summary": f"{char.name} undergoes a transformation from {char.role} to a changed person through the series.",
            "key_moments": [
                {"episode": 1, "moment": "Introduction and establishment of core wound"},
                {"episode": 5, "moment": "First major test of character's beliefs"},
                {"episode": 10, "moment": "Midpoint reversal - character forced to change"},
                {"episode": 15, "moment": "Dark night of the soul"},
                {"episode": 20, "moment": "Final transformation and resolution"}
            ],
            "emotional_journey": "Fear -> Courage -> Doubt -> Determination -> Mastery",
            "generated_at": datetime.utcnow().isoformat()
        })
    
    return {"arcs": arcs}


async def generate_world_building(db: AsyncSession, project_id: str, series_bible: SeriesBible, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mock AI world building generation."""
    result = await db.execute(select(Location).where(Location.project_id == project_id))
    locations = result.scalars().all()
    
    return {
        "series_bible_id": str(series_bible.id),
        "locations": [
            {"name": loc.name, "type": loc.type, "description": f"Key location: {loc.name}"}
            for loc in locations
        ] if locations else [
            {"name": "Main City", "type": "urban", "description": "Primary setting"},
            {"name": "Secret Base", "type": "hidden", "description": "Protagonist's hideout"}
        ],
        "factions": [
            {"name": "The Authority", "type": "government", "description": "Ruling power"},
            {"name": "The Resistance", "type": "rebel", "description": "Opposition group"}
        ],
        "technology": [
            {"name": "Neural Link", "description": "Brain-computer interface"},
            {"name": "Hover Transport", "description": "Anti-gravity vehicles"}
        ],
        "culture": [
            {"name": "Festival of Lights", "description": "Annual celebration"},
            {"name": "Code of Silence", "description": "Cultural taboo"}
        ],
        "history": [
            {"event": "The Great Collapse", "year": "20XX", "description": "Societal breakdown"},
            {"event": "Rise of the Authority", "year": "20XX", "description": "New order established"}
        ],
        "generated_at": datetime.utcnow().isoformat()
    }


async def refine_story_output(task: StoryEngineTask, feedback: str, refine_type: str) -> Dict[str, Any]:
    """Mock AI story refinement."""
    return {
        "refined_output": task.output,
        "refinement_notes": f"Applied {refine_type} refinement based on: {feedback}",
        "refined_at": datetime.utcnow().isoformat()
    }


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
            output = await generate_story_outline(db, project_id, series_bible, task.input_parameters)
        elif task.task_type == StoryEngineTaskType.GENERATE_CHARACTER_ARCS:
            output = await generate_character_arcs(db, project_id, series_bible, task.input_parameters)
        elif task.task_type == StoryEngineTaskType.GENERATE_WORLD_BUILDING:
            output = await generate_world_building(db, project_id, series_bible, task.input_parameters)
        elif task.task_type == StoryEngineTaskType.REFINE_STORY:
            output = await refine_story_output(task, task.context or "", "general")
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
        
        task.output = output
        task.status = StoryEngineTaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        create_audit_log(
            db, current_user.id, AuditAction.STORY_ENGINE_TASK_EXECUTE,
            resource_type="story_engine_task", resource_id=task.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_values={"status": "completed", "output_keys": list(output.keys()) if output else []}
        )
        
    except Exception as e:
        task.status = StoryEngineTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        
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
    
    refined = await refine_story_output(task, refine_data.feedback, refine_data.refine_type)
    
    # Create new task for refinement
    new_task = StoryEngineTask(
        project_id=project_id,
        series_bible_id=task.series_bible_id,
        task_type=StoryEngineTaskType.REFINE_STORY,
        input_parameters={"original_task_id": str(task.id), "feedback": refine_data.feedback},
        context=refine_data.feedback,
        output=refined,
        status=StoryEngineTaskStatus.COMPLETED,
        completed_at=datetime.utcnow()
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
        db, current_user.id, AuditAction.STORY_ENGINE_TASK_CREATE,
        resource_type="story_engine_task", resource_id=task.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"task_type": task.task_type.value}
    )
    
    await db.delete(task)
    await db.commit()