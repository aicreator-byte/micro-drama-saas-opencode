"""Analytics: production metrics + LLM cost tracking per project.

Costs are ESTIMATES (see app/services/llm_pricing.py): a model with no
known price contributes None to estimated_cost_usd, never a guessed
number. Cross-project access is impossible — both endpoints first run
get_project_or_404 with the caller's id, so another user's project is
a 404, exactly like the other project-scoped endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.auto_generate import AutoGenerateJob, AutoGenerateJobStatus
from app.models.llm_usage import LlmUsageEvent
from app.api.v1.story_engine import get_project_or_404
from app.schemas.analytics import (
    AnalyticsSummaryResponse, CostByJobEntry, CostByModelEntry,
    LlmUsageEventResponse, UsageListResponse,
)

router = APIRouter()


def _sum_or_zero(value) -> int:
    return int(value or 0)


@router.get("/{project_id}/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_project_or_404(project_id, current_user.id, db)

    jobs_result = await db.execute(
        select(AutoGenerateJob.status, func.count(AutoGenerateJob.id))
        .where(AutoGenerateJob.project_id == project_id)
        .group_by(AutoGenerateJob.status)
    )
    by_status = {row[0]: row[1] for row in jobs_result.all()}

    totals = (await db.execute(
        select(
            func.count(LlmUsageEvent.id),
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
            func.sum(LlmUsageEvent.estimated_cost_usd),
        ).where(LlmUsageEvent.project_id == project_id)
    )).one()

    by_model_rows = (await db.execute(
        select(
            LlmUsageEvent.model,
            func.count(LlmUsageEvent.id),
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
            func.sum(LlmUsageEvent.estimated_cost_usd),
        ).where(LlmUsageEvent.project_id == project_id)
        .group_by(LlmUsageEvent.model)
        .order_by(func.sum(LlmUsageEvent.total_tokens).desc())
    )).all()

    by_job_rows = (await db.execute(
        select(
            LlmUsageEvent.job_id,
            func.count(LlmUsageEvent.id),
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
            func.sum(LlmUsageEvent.estimated_cost_usd),
        ).where(LlmUsageEvent.project_id == project_id)
        .group_by(LlmUsageEvent.job_id)
        .order_by(func.sum(LlmUsageEvent.total_tokens).desc())
    )).all()

    return AnalyticsSummaryResponse(
        project_id=project_id,
        total_jobs=sum(by_status.values()),
        completed_jobs=by_status.get(AutoGenerateJobStatus.COMPLETED, 0),
        failed_jobs=by_status.get(AutoGenerateJobStatus.FAILED, 0),
        running_jobs=by_status.get(AutoGenerateJobStatus.RUNNING, 0),
        total_prompt_tokens=_sum_or_zero(totals[1]),
        total_completion_tokens=_sum_or_zero(totals[2]),
        total_tokens=_sum_or_zero(totals[3]),
        total_estimated_cost_usd=(
            float(totals[4]) if totals[4] is not None else None
        ),
        cost_by_model=[
            CostByModelEntry(
                model=row[0], events=row[1],
                prompt_tokens=_sum_or_zero(row[2]),
                completion_tokens=_sum_or_zero(row[3]),
                total_tokens=_sum_or_zero(row[4]),
                estimated_cost_usd=float(row[5]) if row[5] is not None else None,
            )
            for row in by_model_rows
        ],
        cost_by_job=[
            CostByJobEntry(
                job_id=row[0], events=row[1],
                prompt_tokens=_sum_or_zero(row[2]),
                completion_tokens=_sum_or_zero(row[3]),
                total_tokens=_sum_or_zero(row[4]),
                estimated_cost_usd=float(row[5]) if row[5] is not None else None,
            )
            for row in by_job_rows
        ],
    )


@router.get("/{project_id}/analytics/usage", response_model=UsageListResponse)
async def list_llm_usage(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_project_or_404(project_id, current_user.id, db)

    total = (await db.execute(
        select(func.count(LlmUsageEvent.id))
        .where(LlmUsageEvent.project_id == project_id)
    )).scalar_one()
    rows = (await db.execute(
        select(LlmUsageEvent)
        .where(LlmUsageEvent.project_id == project_id)
        .order_by(LlmUsageEvent.created_at.desc(), LlmUsageEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )).scalars().all()
    return UsageListResponse(
        items=[LlmUsageEventResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
