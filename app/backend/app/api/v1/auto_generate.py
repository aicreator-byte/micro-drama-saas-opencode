"""Auto-Generate (spec AUTO-GENERATE-SPEC.md section 4-5, Fase 1 backend).

One POST creates a job with 5 sequential steps and runs them in order:
1 series_bible -> 2 characters -> 3 locations -> 4 episodes -> 5 prompts.
Each step writes its output straight into the project tables (no manual
Apply). A failed step stops the job; retry re-runs that step and then
continues with the later pending steps. Re-running a job/step never
duplicates rows: existing characters/locations (by name), episodes (by
number) and video prompts (by episode) are skipped.

Steps run ASYNC: POST creates the job and returns 201 immediately with
status RUNNING; the steps run in a background task on the same engine and
GET polls the per-step status (live progress, audit O1) — or the client
can follow GET .../stream (SSE) instead of polling. A job left RUNNING
when the server restarts IS resumed automatically: resume_stale_jobs
(runs at startup) re-queues it from the first step that is not COMPLETED,
after resetting any step left RUNNING mid-flight back to PENDING (every
step runner is idempotent, so re-running a half-finished step is safe).

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
import asyncio
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_user_optional, create_audit_log
from app.core.security import (
    create_stream_token,
    decode_stream_token,
    STREAM_TOKEN_EXPIRE_MINUTES,
)
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
from app.services.ai_client import get_ai_client, AIClientError, AIResponse
from app.services.llm_usage import (
    make_buffered_usage_sink,
    usage_sink_scope,
    resolve_usage_sink,
)

logger = logging.getLogger(__name__)

# SSE: give up after this long without the job reaching a terminal state.
SSE_TIMEOUT_SECONDS = 120.0
SSE_POLL_SECONDS = 0.5

router = APIRouter()

# Number of characters step 2 asks the LLM to invent (spec: default 4-6).
DEFAULT_CHARACTER_COUNT = 5

# Spec §9.1 minimums (audit O5): a step FAILS when its usable output is
# below the minimum — not only when it is zero.
MIN_CHARACTERS = 4
MIN_LOCATIONS = 3

# One LLM call per chunk of episodes, never a single call for all of them
# (audit O4: one call for 30 episodes risks truncation).
PROMPTS_CHUNK_SIZE = 5


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
        # populate_existing: a long-lived session (tests share one) may
        # already hold this job with a stale status from before the
        # background runner committed; force the row's values in.
        select(AutoGenerateJob).where(
            AutoGenerateJob.id == job_id, AutoGenerateJob.project_id == project_id
        ).execution_options(populate_existing=True)
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


async def _chat_json(
    db: AsyncSession,
    prompt: str,
    max_tokens: int = 8000,
    usage_sink: Optional[Callable[[AIResponse], Union[None, Awaitable[None]]]] = None,
) -> Dict[str, Any]:
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
            usage_sink=resolve_usage_sink(usage_sink),
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
    genre_ask = (
        'Use the genre given above for "genre".'
        if genre else
        'Infer the genre from the title and put one or two words in "genre" '
        '(e.g. Romance, Thriller, Revenge) — never leave it blank, never guess "drama" by default.'
    )
    premise_line = f"Premise hint from the user: {premise}\n" if premise else ""
    return f"""You are a professional TV series writer. Create a complete series bible for a micro-drama series.

Title: {title}
{genre_line}{premise_line}Total episodes planned: {total_episodes}

Write all content in the same language as the title above. {genre_ask}

Generate a JSON response with this exact structure:
{{
  "genre": "One or two words: the genre of this series",
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
    # Genre inference (no silent default): when the user gave no genre,
    # take the LLM's inferred genre for the job. When the LLM gives none,
    # job.genre stays None — an honest blank, never a guessed "drama".
    inferred_genre = None
    if job.genre is None:
        raw_genre = str(output.get("genre") or "").strip()
        if raw_genre:
            inferred_genre = raw_genre[:100]
            job.genre = inferred_genre
    if bible is None:
        bible = SeriesBible(project_id=project.id, **fields)
        db.add(bible)
    else:
        for key, value in fields.items():
            if value is not None:
                setattr(bible, key, value)
    await db.flush()
    return {
        "series_bible_id": bible.id,
        "reused_existing": False,
        "genre": job.genre,
        "genre_inferred": inferred_genre is not None,
    }


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
    # Spec §9.1 (audit O5): the step FAILS when the usable cast is below
    # the minimum — not only when it is zero. existing_names holds the
    # pre-existing cast plus everything created above.
    total_characters = len(existing_names)
    if total_characters < MIN_CHARACTERS:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Only {total_characters} usable character(s), "
                f"minimum is {MIN_CHARACTERS} (spec §9.1) — retry the step"
            ),
        )
    await db.flush()
    return {"created_characters": created, "skipped": skipped, "total_characters": total_characters}


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
    # Spec §9.1 (audit O5): the step FAILS when the usable locations are
    # below the minimum — not only when there are zero.
    total_locations = len(existing_names)
    if total_locations < MIN_LOCATIONS:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Only {total_locations} usable location(s), "
                f"minimum is {MIN_LOCATIONS} (spec §9.1) — retry the step"
            ),
        )
    await db.flush()
    return {"created_locations": created, "skipped": skipped, "total_locations": total_locations}


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

    by_number = {e.episode_number: e for e in episodes}
    existing_result = await db.execute(
        select(Prompt.episode_id).where(
            Prompt.project_id == project.id,
            Prompt.prompt_type == PromptType.VIDEO_GENERATION,
        )
    )
    prompted_episode_ids = {row[0] for row in existing_result.all()}
    # Only episodes without a prompt are sent to the LLM (idempotent retry
    # skips the ones already covered).
    missing_episodes = [e for e in episodes if e.id not in prompted_episode_ids]
    if not missing_episodes:
        return {"created_prompts": [], "skipped": [], "already_covered": len(episodes)}

    # Chunked LLM calls (audit O4): one call per chunk of episodes, never
    # one call for all of them — a single call for 30 episodes risks
    # truncation. Nothing is written to the DB until every chunk is in.
    collected: Dict[int, Dict[str, Any]] = {}
    skipped = []
    for start in range(0, len(missing_episodes), PROMPTS_CHUNK_SIZE):
        chunk = missing_episodes[start:start + PROMPTS_CHUNK_SIZE]
        output = await _chat_json(
            db, build_video_prompts_prompt(bible, characters, chunk), max_tokens=8000
        )
        invented = output.get("prompts") or []
        if not isinstance(invented, list):
            raise HTTPException(status_code=502, detail="AI returned no video prompts")
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
            if number in collected:
                skipped.append({"episode_number": number, "reason": "duplicate in AI output"})
                continue
            prompt_text = str(entry.get("prompt_text") or "").strip()
            if not prompt_text:
                skipped.append({"episode_number": number, "reason": "empty prompt_text"})
                continue
            collected[number] = entry

    # Full coverage (audit O3, like Hermes): the step FAILS when any
    # episode is left without a prompt — no partial insert, retry the step.
    still_missing = [
        e.episode_number for e in missing_episodes if e.episode_number not in collected
    ]
    if still_missing:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI did not cover all episodes; missing video prompts for "
                f"episode(s): {still_missing} — no prompts were written, retry the step"
            ),
        )

    created = []
    for number, entry in collected.items():
        episode = by_number[number]
        prompt = Prompt(
            project_id=project.id,
            episode_id=episode.id,
            prompt_type=PromptType.VIDEO_GENERATION,
            title=(str(entry.get("title") or f"Video prompt episode {number}"))[:255],
            prompt_text=str(entry.get("prompt_text")).strip(),
            negative_prompt=_as_text(entry.get("negative_prompt")),
            status=PromptStatus.DRAFT,
            created_by=user.id,
        )
        db.add(prompt)
        prompted_episode_ids.add(episode.id)
        created.append({"episode_number": number, "title": prompt.title})
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
    The run's LLM usage sink is set once here (ambient ContextVar), so
    every LLM call inside the steps records one LlmUsageEvent without
    changing any step's call shape.

    Perbaikan P2-5 ronde 2: usage event dikumpulkan di sink buffer lalu
    ditulis di transaksi TERPISAH SEBELUM status terminal (completed/
    failed) di-commit — sebelumnya sink menulis di sesi yang sama dengan
    step, sehingga rollback step yang gagal ikut menghapus event call
    LLM-nya (biaya call yang gagal tetap terjadi tapi tidak tercatat).
    Drain sebelum commit terminal juga menutup window race: penonton yang
    melihat status terminal tidak bisa kembali saat drain masih jalan.
    """
    job.status = AutoGenerateJobStatus.RUNNING
    job.error_message = None
    await db.commit()

    buffered_sink = make_buffered_usage_sink(
        user.id, project_id=project.id, job_id=job.id
    )
    try:
        with usage_sink_scope(buffered_sink.sink):
            return await _execute_steps_inner(
                db, job, project, user, from_step,
                buffered_sink=buffered_sink,
            )
    finally:
        # Jaring pengaman: drain sisa event bila inner keluar lewat jalur
        # tak terduga (exception di luar step). Jalur normal sudah drain
        # SEBELUM commit terminal di inner — drain di sini biasanya 0.
        try:
            await buffered_sink.drain(db.bind)
        except Exception as exc:
            logger.warning(f"usage drain failed for job {job.id}: {exc}")


async def _drain_usage_before_terminal_commit(db, buffered_sink, job) -> None:
    """Tulis event LLM yang terkumpul SEBELUM status terminal di-commit.

    Penonton (polling/SSE) melihat status terminal sebagai "run selesai";
    bila drain masih berjalan sesudahnya, teardown tes bisa menutup loop
    di tengah drain (greenlet commit menggantung ke tes berikutnya).
    Drain di sini tidak pernah menggagalkan job.
    """
    if buffered_sink is None:
        return
    try:
        await buffered_sink.drain(db.bind)
    except Exception as exc:
        logger.warning(f"usage drain failed for job {job.id}: {exc}")


async def _execute_steps_inner(
    db: AsyncSession,
    job: AutoGenerateJob,
    project: Project,
    user: User,
    from_step: Optional[AutoGenerateStepName] = None,
    buffered_sink=None,
) -> AutoGenerateJob:
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
        # Capture the label before the runner below: a rollback in the
        # failure path expires the row, and reading step.step afterwards
        # would refresh (and wipe) the FAILED marking we just set.
        step_label = step.step.value
        try:
            result = await STEP_RUNNERS[step.step](db, job, project, user)
            step.result = result
            step.status = AutoGenerateStepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, str) else str(e.detail)
            # Discard the failed step's partial writes first (audit O6:
            # a failed step must not leave half its rows behind), then mark
            # the step/job FAILED in a clean state and commit only that.
            await db.rollback()
            # Drain SEBELUM commit FAILED: event call LLM step yang gagal
            # tetap tercatat (P2-5), dan tidak ada kerja sesudah status
            # terminal terlihat.
            await _drain_usage_before_terminal_commit(db, buffered_sink, job)
            step.status = AutoGenerateStepStatus.FAILED
            step.error_message = detail
            step.completed_at = datetime.now(timezone.utc)
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = f"Step {step_label} failed: {detail}"
            await db.commit()
            return job
        except Exception as e:
            await db.rollback()
            await _drain_usage_before_terminal_commit(db, buffered_sink, job)
            step.status = AutoGenerateStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = f"Step {step_label} failed: {e}"
            await db.commit()
            return job
        await db.commit()

    await _drain_usage_before_terminal_commit(db, buffered_sink, job)
    job.status = AutoGenerateJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return job


async def _run_job_in_background(
    engine,
    job_id: str,
    project_id: str,
    user_id: str,
    from_step: Optional[AutoGenerateStepName] = None,
) -> None:
    """Run a job's pending steps outside the request (live progress via GET).

    Own session on the SAME engine the request used, so tests (in-memory
    engine) and production (file/postgres engine) both see the same rows.
    The RUN audit is written here, at completion, with no request context.
    Never raises: an unexpected failure marks the job FAILED instead of
    leaving it stuck RUNNING.
    """
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            job = await _get_job_or_404(job_id, project_id, session)
            project_result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if project is None or user is None:
                return
            await _execute_steps(session, job, project, user, from_step=from_step)
            create_audit_log(
                session, user_id, AuditAction.AUTO_GENERATE_RUN,
                resource_type="auto_generate_job", resource_id=job.id,
                success=job.status == AutoGenerateJobStatus.COMPLETED,
                error_message=job.error_message,
                new_values={"status": job.status.value},
            )
            await session.commit()
    except Exception as exc:
        # Never leave a job stuck RUNNING because the runner itself died.
        try:
            async with factory() as session:
                job = await _get_job_or_404(job_id, project_id, session)
                if job.status == AutoGenerateJobStatus.RUNNING:
                    job.status = AutoGenerateJobStatus.FAILED
                    job.error_message = f"Background runner failed: {exc}"
                    await session.commit()
        except Exception:
            pass


async def resume_stale_jobs(engine) -> List[str]:
    """Resume auto-generate jobs left RUNNING by a server restart.

    For every RUNNING job: reset any step left RUNNING mid-flight back to
    PENDING (every step runner is idempotent, so re-running it is safe),
    then re-queue the job in the background from the first step that is
    not COMPLETED. The job has no user_id of its own — the project's
    owner_id is the user. Returns the ids of the jobs actually re-queued;
    a job whose project is gone is skipped, never raised. No-op when
    nothing is stale. Called once at startup (see app/main.py lifespan)
    via create_task so it never blocks startup.
    """
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    to_resume: List[Dict[str, Any]] = []
    try:
        async with factory() as session:
            result = await session.execute(
                select(AutoGenerateJob).where(
                    AutoGenerateJob.status == AutoGenerateJobStatus.RUNNING
                )
            )
            jobs = list(result.scalars().all())
            for job in jobs:
                await session.refresh(job, attribute_names=["steps"])
                # A step interrupted mid-flight goes back to PENDING.
                for step in job.steps:
                    if step.status == AutoGenerateStepStatus.RUNNING:
                        step.status = AutoGenerateStepStatus.PENDING
                        step.error_message = None
                # First step that still needs work (None = all done; the
                # runner then just marks the job COMPLETED).
                pending = next(
                    (s for s in sorted(job.steps, key=lambda x: x.step_order)
                     if s.status != AutoGenerateStepStatus.COMPLETED),
                    None,
                )
                project_result = await session.execute(
                    select(Project).where(Project.id == job.project_id)
                )
                project = project_result.scalar_one_or_none()
                if project is None:
                    logger.warning(
                        f"resume_stale_jobs: skipping job {job.id}, project gone"
                    )
                    continue
                to_resume.append({
                    "job_id": job.id,
                    "project_id": job.project_id,
                    "owner_id": project.owner_id,
                    "from_step": pending.step if pending is not None else None,
                })
                logger.info(
                    "resume_stale_jobs: resuming job %s from step %s",
                    job.id,
                    pending.step.value if pending is not None else "none (all done)",
                )
            await session.commit()
    except Exception as exc:
        logger.warning(f"resume_stale_jobs failed: {exc}")
        return []
    # Schedule outside the session above: the runner opens its own.
    scheduled: List[str] = []
    for item in to_resume:
        try:
            asyncio.create_task(
                _run_job_in_background(
                    engine, item["job_id"], item["project_id"],
                    item["owner_id"], from_step=item["from_step"],
                )
            )
            scheduled.append(item["job_id"])
        except Exception as exc:
            logger.warning(
                f"resume_stale_jobs: could not resume {item['job_id']}: {exc}"
            )
    return scheduled


@router.post("/{project_id}/auto-generate", response_model=AutoGenerateJobResponse, status_code=status.HTTP_201_CREATED)
async def create_auto_generate_job(
    project_id: str,
    body: AutoGenerateCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an auto-generate job and start its 5 steps in the background.

    Returns 201 immediately with status RUNNING; poll GET for the live
    per-step progress. The job input is stored on the job itself and never
    rewrites the project header (audit O7): a failed job used to leave the
    project title/genre/total_episodes changed.
    """
    project = await get_project_or_404(project_id, current_user.id, db)

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

    # Async (audit O1): run the steps in the background on the same engine
    # the request used; GET polls the live per-step status.
    asyncio.create_task(
        _run_job_in_background(db.bind, job.id, project.id, current_user.id)
    )
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


async def _resolve_stream_user(
    request: Request, token: Optional[str], db: AsyncSession, job_id: str
) -> User:
    """Auth for the SSE stream.

    Dua jalur (perbaikan P2-2 ronde 2):
    - Header Authorization: JWT penuh seperti biasa (get_current_user).
    - Query ?token=: HANYA token stream berumur pendek (purpose="sse",
      terikat ke job ini, dibuat via POST .../stream-token). JWT penuh
      lewat query DITOLAK — token berumur panjang tidak boleh lewat URL
      (tercatat di access log / history browser / Referer).
    """
    user = await get_current_user_optional(request, db)
    if user is not None:
        return user
    if token:
        user_id = decode_stream_token(token, job_id)
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is not None and user.is_active:
                return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/{project_id}/auto-generate/{job_id}/stream-token")
async def create_stream_token_endpoint(
    project_id: str,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Terbitkan token stream SSE berumur pendek untuk satu job.

    Frontend memanggil ini (auth via header) sebelum membuka EventSource,
    lalu membuka stream dengan ?token=<stream token>. Token berlaku 5
    menit, hanya untuk job ini, hanya untuk membaca progres stream.
    """
    await get_project_or_404(project_id, current_user.id, db)
    await _get_job_or_404(job_id, project_id, db)
    token = create_stream_token(current_user.id, job_id)
    return {
        "stream_token": token,
        "expires_in_seconds": STREAM_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/{project_id}/auto-generate/{job_id}/stream")
async def stream_auto_generate_job(
    project_id: str,
    job_id: str,
    request: Request,
    token: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Live progress as Server-Sent Events (replaces 2s GET polling).

    Auth + project ownership are checked BEFORE the stream starts, so an
    unknown job is a plain 404 and a missing token a plain 401. Every
    ~0.5s a `progress` event carries the same JSON shape as
    AutoGenerateJobResponse; when the job reaches a terminal state
    (completed/failed) a `done` event is sent and the stream closes.
    The stream also closes after 120s without a terminal state — the
    client re-opens it (same job id, new stream token) or falls back to
    GET polling (perbaikan P2-7 ronde 2: sebelumnya event `done`
    timeout membuat UI berhenti total tanpa reconnect).

    Token: ?token= hanya menerima token stream berumur pendek (POST
    .../stream-token); JWT penuh hanya via header Authorization.
    """
    current_user = await _resolve_stream_user(request, token, db, job_id)
    await get_project_or_404(project_id, current_user.id, db)
    await _get_job_or_404(job_id, project_id, db)

    async def event_generator():
        # Poll through the REQUEST session (like GET polling does), not a
        # fresh session per poll: with a single-connection test engine a
        # second session's transaction can roll back / hide the runner's
        # uncommitted work. _get_job_or_404 uses populate_existing, so
        # these reads stay fresh even on a long-lived session.
        deadline = time.monotonic() + SSE_TIMEOUT_SECONDS
        while True:
            try:
                job = await _get_job_or_404(job_id, project_id, db)
                payload = job_to_response(job).model_dump(mode="json")
            except HTTPException:
                yield 'event: done\ndata: {"status": "not_found"}\n\n'
                return
            except Exception as exc:  # transient read error: keep streaming
                logger.warning(f"SSE poll failed for job {job_id}: {exc}")
                payload = None
            if payload is not None:
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                if payload["status"] in ("completed", "failed"):
                    yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                    return
            if time.monotonic() >= deadline:
                yield 'event: done\ndata: {"status": "timeout"}\n\n'
                return
            await asyncio.sleep(SSE_POLL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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

    # Reset the failed step and continue in the background, so the modal
    # can poll the live per-step progress instead of waiting on one call.
    target.status = AutoGenerateStepStatus.PENDING
    target.error_message = None
    job.status = AutoGenerateJobStatus.RUNNING
    job.error_message = None
    await db.commit()

    asyncio.create_task(
        _run_job_in_background(
            db.bind, job.id, project.id, current_user.id, from_step=step_name
        )
    )
    await db.refresh(job, attribute_names=["steps"])
    return job_to_response(job)
