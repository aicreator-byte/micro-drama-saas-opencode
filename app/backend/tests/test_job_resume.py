"""Resume of stale (RUNNING) auto-generate jobs on startup."""
import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1.auto_generate import resume_stale_jobs
from app.models.auto_generate import (
    AutoGenerateJob, AutoGenerateStep, AutoGenerateJobStatus,
    AutoGenerateStepName, AutoGenerateStepStatus, STEP_ORDER,
)
from app.models.series_bible import SeriesBible


async def _wait_for_job(client, project_id, job_id, headers, timeout=30.0):
    last = None
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/auto-generate/{job_id}",
            headers=headers,
        )
        last = resp
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                return data
        await asyncio.sleep(0.25)
    raise AssertionError(
        f"job {job_id} did not finish in {timeout}s; last response: "
        f"{last.status_code if last is not None else None} "
        f"{last.text if last is not None else ''}"
    )


async def _make_stale_job(db_session, test_project):
    """A job as a restart would leave it: step 1 COMPLETED (with its
    result), step 2 RUNNING (cut off mid-flight), the rest PENDING."""
    bible = SeriesBible(
        project_id=test_project.id,
        premise="A family drama about betrayal and redemption",
        main_plot="Mock main plot",
    )
    db_session.add(bible)
    await db_session.flush()

    job = AutoGenerateJob(
        project_id=test_project.id,
        title="THE BILLIONAIRE CEO",
        genre="Romance",
        total_episodes=5,
        premise="A struggling young woman marries a cold billionaire CEO.",
        status=AutoGenerateJobStatus.RUNNING,
    )
    db_session.add(job)
    await db_session.flush()
    statuses = {
        AutoGenerateStepName.SERIES_BIBLE: AutoGenerateStepStatus.COMPLETED,
        AutoGenerateStepName.CHARACTERS: AutoGenerateStepStatus.RUNNING,
        AutoGenerateStepName.LOCATIONS: AutoGenerateStepStatus.PENDING,
        AutoGenerateStepName.EPISODES: AutoGenerateStepStatus.PENDING,
        AutoGenerateStepName.PROMPTS: AutoGenerateStepStatus.PENDING,
    }
    for order, step_name in enumerate(STEP_ORDER):
        db_session.add(AutoGenerateStep(
            job_id=job.id,
            step=step_name,
            step_order=order,
            status=statuses[step_name],
            result=(
                {"series_bible_id": bible.id, "reused_existing": True}
                if step_name == AutoGenerateStepName.SERIES_BIBLE else None
            ),
        ))
    await db_session.commit()
    return job, bible


class TestJobResume:
    @pytest.mark.asyncio
    async def test_resume_stale_job_completes_from_step_two(
        self, client: AsyncClient, auth_headers, test_project,
        test_settings_with_mock, db_session, db_engine,
    ):
        job, bible = await _make_stale_job(db_session, test_project)

        resumed = await resume_stale_jobs(db_engine)
        assert resumed == [job.id]

        data = await _wait_for_job(client, test_project.id, job.id, auth_headers)
        assert data["status"] == "completed"
        by_step = {s["step"]: s for s in data["steps"]}
        # Step 1 was NOT re-run: its result is intact.
        assert by_step["series_bible"]["status"] == "completed"
        assert by_step["series_bible"]["result"]["series_bible_id"] == bible.id
        assert by_step["series_bible"]["result"]["reused_existing"] is True
        # Step 2 was NOT skipped: it ran (from PENDING, after resume reset
        # its RUNNING state) and completed with the mock cast.
        assert by_step["characters"]["status"] == "completed"
        assert len(by_step["characters"]["result"]["created_characters"]) == 5
        assert by_step["locations"]["status"] == "completed"
        assert by_step["episodes"]["status"] == "completed"
        assert by_step["prompts"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_noop_when_no_stale_jobs(
        self, db_engine, test_project, test_settings_with_mock,
    ):
        assert await resume_stale_jobs(db_engine) == []

    @pytest.mark.asyncio
    async def test_resume_all_steps_done_marks_job_completed(
        self, client: AsyncClient, auth_headers, test_project,
        test_settings_with_mock, db_session, db_engine,
    ):
        """Edge case: every step COMPLETED but the job still RUNNING
        (crashed between the last step and the status flip)."""
        job, _bible = await _make_stale_job(db_session, test_project)
        for step in (await db_session.execute(
            select(AutoGenerateStep).where(AutoGenerateStep.job_id == job.id)
        )).scalars().all():
            step.status = AutoGenerateStepStatus.COMPLETED
        await db_session.commit()

        resumed = await resume_stale_jobs(db_engine)
        assert resumed == [job.id]
        data = await _wait_for_job(client, test_project.id, job.id, auth_headers)
        assert data["status"] == "completed"
