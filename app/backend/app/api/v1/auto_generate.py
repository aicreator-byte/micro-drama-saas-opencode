"""Auto-Generate (spec AUTO-GENERATE-SPEC.md section 4-5, Fase 1 backend).

One POST creates a job with 5 sequential steps and runs them in order:
1 series_bible -> 2 characters -> 3 locations -> 4 episodes -> 5 prompts.
Each step writes its output straight into the project tables (no manual
Apply). A failed step stops the job; retry re-runs that step and then
continues with the later pending steps. Re-running a job/step never
duplicates rows: existing characters/locations (by name), episodes (by
number) and video prompts (by episode) are skipped.

Reuses the existing Story Engine LLM helpers where they fit:
- step 4 uses generate_story_outline_llm + apply_outline_episodes
- step 3 uses generate_world_building_llm (works with zero locations)
Steps 1, 2 and 5 need NEW LLM calls because the existing ones cannot
produce them from an empty project:
- generate_character_arcs_llm only writes arcs for characters that
  already exist, so step 2 invents the cast with its own call.
- there is no prompt-generation endpoint in this leg, so step 5 calls
  the LLM directly for one video prompt per episode.
No video is ever executed here (spec section 8): step 5 only writes
VIDEO_GENERATION prompt rows for manual use in Google Flow.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.models.auto_generate import (
    AutoGenerateJob, AutoGenerateStep, AutoGenerateJobStatus,
    AutoGenerateStepName, AutoGenerateStepStatus, STEP_ORDER,
)
from app.models.audit_log import AuditAction
from app.schemas.auto_generate import (
    AutoGenerateCreateRequest, AutoGenerateJobResponse, AutoGenerateStepResponse,
)
from app.api.v1.story_engine import (
    get_project_or_404,
    generate_story_outline_llm,
    generate_world_building_llm,
    apply_outline_episodes,
)
from app.services.ai_client import get_ai_client, AIClientError

router = APIRouter()

# Number of characters step 2 asks the LLM to invent (spec: default 4-6).
DEFAULT_CHARACTER_COUNT = 5


def job_to_response(job: AutoGenerateJob) -> AutoGenerateJobResponse:
    return AutoGenerateJobResponse(
        id=job.id,
        project_id=job.project_id,
        title=job.title,
        genre=job.genre,
        total_episodes=job.total_episodes,
        premise=job.premise,
        status=job.status,
        error_message=job.error_message,
        steps=[
            AutoGenerateStepResponse(
                id=s.id,
                job_id=s.job_id,
                step=s.step,
                step_order=s.step_order,
                status=s.status,
                error_message=s.error_message,
                result=s.result,
                created_at=s.created_at,
                updated_at=s.updated_at,
                completed_at=s.completed_at,
            )
            for s in sorted(job.steps, key=lambda x: x.step_order)
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _get_job_or_404(job_id: str, project_id: str, db: AsyncSession) -> AutoGenerateJob:
    result = await db.execute(
        select(AutoGenerateJob).where(
            AutoGenerateJob.id == job_id, AutoGenerateJob.project_id == project_id
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto-generate job not found")
    # Load steps (lazy load would fail outside the request session otherwise).
    await db.refresh(job, attribute_names=["steps"])
    return job


async def _get_bible_or_404(project_id: str, db: AsyncSession) -> SeriesBible:
    result = await db.execute(
        select(SeriesBible).where(SeriesBible.project_id == project_id)
    )
    bible = result.scalar_one_or_none()
    if not bible:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Series bible is missing; step 1 must complete first",
        )
    return bible


def _llm_json(response_content: str) -> Dict[str, Any]:
    try:
        output = json.loads(response_content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {e}")
    if not isinstance(output, dict):
        raise HTTPException(status_code=502, detail="Invalid JSON from AI: expected an object")
    return output


async def _chat_json(db: AsyncSession, prompt: str, max_tokens: int = 8000) -> Dict[str, Any]:
    """One chat_completion call that must return a JSON object."""
    ai_client = await get_ai_client(db)
    try:
        response = await ai_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional TV series writer. Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except AIClientError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e.errors}")
    return _llm_json(response.content)


def _as_text(value: Any) -> Optional[str]:
    """Store a plain string, or a list/dict as JSON text (bible text columns)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def build_series_bible_prompt(title: str, genre: Optional[str], total_episodes: int, premise: Optional[str]) -> str:
    genre_line = f"Genre: {genre}\n" if genre else ""
    premise_line = f"Premise hint from the user: {premise}\n" if premise else ""
    return f"""You are a professional TV series writer. Create a complete series bible for a micro-drama series.

Title: {title}
{genre_line}{premise_line}Total episodes planned: {total_episodes}

Write all content in the same language as the title above.

Generate a JSON response with this exact structure:
{{
  "premise": "One-paragraph hook: who the story is about and the central conflict",
  "main_plot": "2-3 paragraph main plot",
  "subplots": ["Subplot 1 title: one-sentence description", "Subplot 2 title: one-sentence description"],
  "character_relationships": "How the main characters relate to each other",
  "world_settings": "Where and when the story takes place, the social world",
  "tone_and_visual_style": "Tone and visual style, e.g. cinematic, glamorous, suspenseful",
  "ending_direction": "Where the series is heading in the finale",
  "episode_structure": "How episodes are structured, e.g. 30 episodes of 1-2 minutes, arcs per episode block"
}}

Include 3-5 subplots. Return ONLY valid JSON, no markdown formatting."""


def build_characters_prompt(bible: SeriesBible, count: int) -> str:
    return f"""You are a professional TV series writer. Create the main cast of {count} original characters for this micro-drama series.

SERIES BIBLE:
- Premise: {bible.premise or 'Not specified'}
- Main Plot: {bible.main_plot or 'Not specified'}
- Tone: {bible.tone_and_visual_style or 'Not specified'}

Write all content in the same language as the premise above. Give every
character a distinct name, a clear role (protagonist, antagonist, supporting),
and a background that fits the premise.

Generate a JSON response with this exact structure:
{{
  "characters": [
    {{
      "name": "Full name",
      "role": "protagonist/antagonist/supporting",
      "age": "28",
      "gender": "female/male",
      "ethnicity": "ethnicity",
      "background": "2-3 sentences: who they are, where they come from",
      "motivations": "What they want most",
      "fears": "What they are afraid of",
      "personality_traits": ["trait 1", "trait 2", "trait 3"]
    }}
  ]
}}

Return exactly {count} characters. Return ONLY valid JSON, no markdown formatting."""


def build_video_prompts_prompt(
    bible: SeriesBible,
    characters: List[Character],
    episodes: List[Episode],
) -> str:
    char_info = "\n".join([f"- {c.name} ({c.role or 'character'})" for c in characters]) or "No characters defined."
    ep_info = "\n".join([
        f"- Episode {e.episode_number}: {e.title or 'Untitled'} — {e.summary or 'No synopsis'}"
        for e in episodes
    ])
    return f"""You are a professional micro-drama video director. Write one video generation prompt for each episode below, for Google Flow / Veo.

SERIES:
- Tone and visual style: {bible.tone_and_visual_style or 'Not specified'}
- World: {bible.world_settings or 'Not specified'}

CHARACTERS:
{char_info}

EPISODES:
{ep_info}

Write all prompts in the same language as the episode titles above. Each
prompt must be a self-contained, cinematic, vertical-video (9:16) shot
description: setting, characters present, key action, camera, lighting and
mood, in 2-4 sentences. Keep visual continuity: same characters must look
the same across episodes (same age, outfit, features).

Generate a JSON response with this exact structure:
{{
  "prompts": [
    {{
      "episode_number": 1,
      "title": "Short title for this video prompt",
      "prompt_text": "The full video generation prompt",
      "negative_prompt": "blurry, low quality, distorted faces, inconsistent character"
    }}
  ]
}}

Write exactly one prompt per episode listed above. Return ONLY valid JSON, no markdown formatting."""


async def _run_step_series_bible(db: AsyncSession, job: AutoGenerateJob, project: Project, user: User) -> Dict[str, Any]:
    result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project.id))
    bible = result.scalar_one_or_none()
    if bible is not None and bible.premise:
        # Never overwrite a bible the user already filled in by hand
        # (re-run safety: step is idempotent).
        return {"series_bible_id": bible.id, "reused_existing": True}
    output = await _chat_json(
        db,
        build_series_bible_prompt(job.title, job.genre, job.total_episodes, job.premise),
    )
    fields = {
        "premise": output.get("premise"),
        "main_plot": output.get("main_plot"),
        "subplots": _as_text(output.get("subplots")),
        "character_relationships": _as_text(output.get("character_relationships")),
        "world_settings": _as_text(output.get("world_settings")),
        "tone_and_visual_style": _as_text(output.get("tone_and_visual_style")),
        "ending_direction": _as_text(output.get("ending_direction")),
        "episode_structure": _as_text(output.get("episode_structure")),
    }
    if not fields["premise"] and not fields["main_plot"]:
        raise HTTPException(status_code=502, detail="AI returned an empty series bible")
    if bible is None:
        bible = SeriesBible(project_id=project.id, **fields)
        db.add(bible)
    else:
        for key, value in fields.items():
            if value is not None:
                setattr(bible, key, value)
    await db.flush()
    return {"series_bible_id": bible.id, "reused_existing": False}


async def _run_step_characters(db: AsyncSession, job: AutoGenerateJob, project: Project, user: User) -> Dict[str, Any]:
    bible = await _get_bible_or_404(project.id, db)
    output = await _chat_json(db, build_characters_prompt(bible, DEFAULT_CHARACTER_COUNT))
    invented = output.get("characters") or []
    if not isinstance(invented, list) or not invented:
        raise HTTPException(status_code=502, detail="AI returned no characters")

    existing_result = await db.execute(select(Character.name).where(Character.project_id == project.id))
    existing_names = {str(row[0]).strip().lower() for row in existing_result.all()}
    created, skipped = [], []
    order = len(existing_names)
    for entry in invented[:6]:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            skipped.append({"episode": None, "reason": "missing name"})
            continue
        if name.lower() in existing_names:
            skipped.append({"name": name, "reason": "already exists"})
            continue
        traits = entry.get("personality_traits")
        character = Character(
            project_id=project.id,
            name=name[:255],
            role=str(entry.get("role") or "supporting")[:100],
            order_index=order,
            age=str(entry.get("age") or "")[:50] or None,
            gender=str(entry.get("gender") or "")[:50] or None,
            ethnicity=str(entry.get("ethnicity") or "")[:100] or None,
            background=_as_text(entry.get("background")),
            motivations=_as_text(entry.get("motivations")),
            fears=_as_text(entry.get("fears")),
            personality_traits=_as_text(traits),
        )
        db.add(character)
        existing_names.add(name.lower())
        created.append(name)
        order += 1
    if not created and not existing_names:
        raise HTTPException(status_code=502, detail="AI returned no usable characters")
    await db.flush()
    return {"created_characters": created, "skipped": skipped}


async def _run_step_locations(db: AsyncSession, job: AutoGenerateJob, project: Project, user: User) -> Dict[str, Any]:
    bible = await _get_bible_or_404(project.id, db)
    # Reuses the existing world-building generator (works with zero
    # locations); only the write path is new.
    output = await generate_world_building_llm(db, project.id, bible)
    invented = output.get("locations") or []
    existing_result = await db.execute(select(Location.name).where(Location.project_id == project.id))
    existing_names = {str(row[0]).strip().lower() for row in existing_result.all()}
    created, skipped = [], []
    order = len(existing_names)
    for entry in invented:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in existing_names:
            skipped.append({"name": name, "reason": "already exists"})
            continue
        location = Location(
            project_id=project.id,
            name=name[:255],
            type=str(entry.get("type") or "")[:100] or None,
            order_index=order,
            description=_as_text(entry.get("description")),
        )
        db.add(location)
        existing_names.add(name.lower())
        created.append(name)
        order += 1
    if not created and not existing_names:
        raise HTTPException(status_code=502, detail="AI returned no usable locations")
    await db.flush()
    return {"created_locations": created, "skipped": skipped}


async def _run_step_episodes(db: AsyncSession, job: AutoGenerateJob, project: Project, user: User) -> Dict[str, Any]:
    bible = await _get_bible_or_404(project.id, db)
    output = await generate_story_outline_llm(
        db, project.id, bible, {"total_episodes": job.total_episodes}
    )
    episodes_data = output.get("episodes") or []
    if not episodes_data:
        raise HTTPException(status_code=502, detail="AI returned no episode outline")
    # Same write path (and skip rules) as the story-engine apply endpoint.
    return await apply_outline_episodes(db, project.id, episodes_data)


async def _run_step_prompts(db: AsyncSession, job: AutoGenerateJob, project: Project, user: User) -> Dict[str, Any]:
    bible = await _get_bible_or_404(project.id, db)
    ep_result = await db.execute(
        select(Episode).where(Episode.project_id == project.id).order_by(Episode.episode_number)
    )
    episodes = list(ep_result.scalars().all())
    if not episodes:
        raise HTTPException(status_code=502, detail="No episodes to write prompts for")
    char_result = await db.execute(select(Character).where(Character.project_id == project.id))
    characters = list(char_result.scalars().all())

    output = await _chat_json(
        db, build_video_prompts_prompt(bible, characters, episodes), max_tokens=8000
    )
    invented = output.get("prompts") or []
    if not isinstance(invented, list) or not invented:
        raise HTTPException(status_code=502, detail="AI returned no video prompts")

    by_number = {e.episode_number: e for e in episodes}
    existing_result = await db.execute(
        select(Prompt.episode_id).where(
            Prompt.project_id == project.id,
            Prompt.prompt_type == PromptType.VIDEO_GENERATION,
        )
    )
    prompted_episode_ids = {row[0] for row in existing_result.all()}
    created, skipped = [], []
    for entry in invented:
        if not isinstance(entry, dict):
            continue
        try:
            number = int(entry.get("episode_number"))
        except (TypeError, ValueError):
            skipped.append({"episode": entry.get("title"), "reason": "missing episode_number"})
            continue
        episode = by_number.get(number)
        if episode is None:
            skipped.append({"episode_number": number, "reason": "episode not found"})
            continue
        if episode.id in prompted_episode_ids:
            skipped.append({"episode_number": number, "reason": "prompt already exists"})
            continue
        prompt_text = str(entry.get("prompt_text") or "").strip()
        if not prompt_text:
            skipped.append({"episode_number": number, "reason": "empty prompt_text"})
            continue
        prompt = Prompt(
            project_id=project.id,
            episode_id=episode.id,
            prompt_type=PromptType.VIDEO_GENERATION,
            title=(str(entry.get("title") or f"Video prompt episode {number}"))[:255],
            prompt_text=prompt_text,
            negative_prompt=_as_text(entry.get("negative_prompt")),
            status=PromptStatus.DRAFT,
            created_by=user.id,
        )
        db.add(prompt)
        prompted_episode_ids.add(episode.id)
        created.append({"episode_number": number, "title": prompt.title})
    if not created and not prompted_episode_ids:
        raise HTTPException(status_code=502, detail="AI returned no usable video prompts")
    await db.flush()
    return {"created_prompts": created, "skipped": skipped}


STEP_RUNNERS = {
    AutoGenerateStepName.SERIES_BIBLE: _run_step_series_bible,
    AutoGenerateStepName.CHARACTERS: _run_step_characters,
    AutoGenerateStepName.LOCATIONS: _run_step_locations,
    AutoGenerateStepName.EPISODES: _run_step_episodes,
    AutoGenerateStepName.PROMPTS: _run_step_prompts,
}


async def _execute_steps(
    db: AsyncSession,
    job: AutoGenerateJob,
    project: Project,
    user: User,
    from_step: Optional[AutoGenerateStepName] = None,
) -> AutoGenerateJob:
    """Run pending steps in order, starting at from_step (retry) or the start.

    A failed step stops the job immediately; later steps stay pending.
    Completed steps are never re-run.
    """
    job.status = AutoGenerateJobStatus.RUNNING
    job.error_message = None
    await db.commit()

    from_order = STEP_ORDER.index(from_step) if from_step else 0
    steps = sorted(job.steps, key=lambda s: s.step_order)
    for step in steps:
        if step.step_order < from_order:
            continue
        if step.status == AutoGenerateStepStatus.COMPLETED:
            continue
        step.status = AutoGenerateStepStatus.RUNNING
        step.error_message = None
        await db.commit()
        try:
            result = await STEP_RUNNERS[step.step](db, job, project, user)
            step.result = result
            step.status = AutoGenerateStepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, str) else str(e.detail)
            step.status = AutoGenerateStepStatus.FAILED
            step.error_message = detail
            step.completed_at = datetime.now(timezone.utc)
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = f"Step {step.step.value} failed: {detail}"
            await db.commit()
            return job
        except Exception as e:
            step.status = AutoGenerateStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = f"Step {step.step.value} failed: {e}"
            await db.commit()
            return job
        await db.commit()

    job.status = AutoGenerateJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return job


@router.post("/{project_id}/auto-generate", response_model=AutoGenerateJobResponse, status_code=status.HTTP_201_CREATED)
async def create_auto_generate_job(
    project_id: str,
    body: AutoGenerateCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an auto-generate job and run its 5 steps in order (sync, like
    the story-engine execute endpoint)."""
    project = await get_project_or_404(project_id, current_user.id, db)

    # The job input is the source of truth for the project header.
    project.title = body.title
    if body.genre is not None:
        project.genre = body.genre
    project.total_episodes = body.total_episodes

    job = AutoGenerateJob(
        project_id=project_id,
        title=body.title,
        genre=body.genre,
        total_episodes=body.total_episodes,
        premise=body.premise,
        status=AutoGenerateJobStatus.RUNNING,
    )
    db.add(job)
    await db.flush()
    for order, step_name in enumerate(STEP_ORDER):
        db.add(AutoGenerateStep(
            job_id=job.id,
            step=step_name,
            step_order=order,
            status=AutoGenerateStepStatus.PENDING,
        ))
    await db.commit()
    await db.refresh(job, attribute_names=["steps"])

    create_audit_log(
        db, current_user.id, AuditAction.AUTO_GENERATE_CREATE,
        resource_type="auto_generate_job", resource_id=job.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"title": body.title, "total_episodes": body.total_episodes},
    )
    await db.commit()

    await _execute_steps(db, job, project, current_user)

    create_audit_log(
        db, current_user.id, AuditAction.AUTO_GENERATE_RUN,
        resource_type="auto_generate_job", resource_id=job.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        success=job.status == AutoGenerateJobStatus.COMPLETED,
        error_message=job.error_message,
        new_values={"status": job.status.value},
    )
    await db.commit()
    await db.refresh(job, attribute_names=["steps"])
    return job_to_response(job)


@router.get("/{project_id}/auto-generate/{job_id}", response_model=AutoGenerateJobResponse)
async def get_auto_generate_job(
    project_id: str,
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_project_or_404(project_id, current_user.id, db)
    job = await _get_job_or_404(job_id, project_id, db)
    return job_to_response(job)


@router.post("/{project_id}/auto-generate/{job_id}/retry/{step}", response_model=AutoGenerateJobResponse)
async def retry_auto_generate_step(
    project_id: str,
    job_id: str,
    step: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry one failed step, then continue with the later pending steps."""
    project = await get_project_or_404(project_id, current_user.id, db)
    try:
        step_name = AutoGenerateStepName(step)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown step: {step}. Valid steps: {[s.value for s in STEP_ORDER]}",
        )
    job = await _get_job_or_404(job_id, project_id, db)
    target = next((s for s in job.steps if s.step == step_name), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found in this job")
    if target.status != AutoGenerateStepStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only a failed step can be retried (step {step} is {target.status.value})",
        )
    job.completed_at = None

    create_audit_log(
        db, current_user.id, AuditAction.AUTO_GENERATE_RETRY,
        resource_type="auto_generate_job", resource_id=job.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"step": step},
    )
    await db.commit()

    await _execute_steps(db, job, project, current_user, from_step=step_name)
    await db.refresh(job, attribute_names=["steps"])
    return job_to_response(job)
