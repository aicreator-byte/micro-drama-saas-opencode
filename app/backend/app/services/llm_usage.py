"""Usage sink: record one LlmUsageEvent per successful LLM call.

AIClient.chat_completion cannot write to the DB itself (it has no
session), so callers pass a sink built here. The sink adds the event to
the caller's own session and flushes it — it commits together with the
step/task that made the call, and it never raises: a recording failure
must not fail the job (chat_completion logs it as a warning instead).

The sink travels via an explicit argument AND a ContextVar:
- explicit `usage_sink=` on chat_completion / generate_*_llm (used by the
  story/scene execute endpoints);
- `usage_sink_scope(...)` around a whole auto-generate run, so the step
  runners and _chat_json pick it up without changing their call shapes
  (existing callers/mocks that call _chat_json(db, prompt, max_tokens)
  keep working untouched).

Two sink flavours:
- `make_usage_sink(db, ...)` — writes into the caller's own session
  (flush, commit bersama step). Dipakai endpoint story/scene (satu call
  per request; request commit di akhir).
- `BufferedUsageSink` / `make_buffered_usage_sink(...)` — kumpulkan event
  di memori, `drain(engine)` menulisnya di transaksi terpisah setelah
  run selesai. Dipakai auto-generate (perbaikan P2-5 ronde 2): rollback
  step yang gagal tidak boleh menghapus event call LLM-nya.
"""
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from app.models.llm_usage import LlmUsageEvent
from app.services.ai_client import AIResponse
from app.services.llm_pricing import estimated_cost_usd

logger = logging.getLogger(__name__)

# Sink active for the current task (an auto-generate run sets it once;
# see app/api/v1/auto_generate._execute_steps).
current_usage_sink: ContextVar = ContextVar("current_usage_sink", default=None)


@contextmanager
def usage_sink_scope(sink):
    """Run a block with `sink` as the ambient usage sink for this task."""
    token = current_usage_sink.set(sink)
    try:
        yield
    finally:
        current_usage_sink.reset(token)


def resolve_usage_sink(explicit=None):
    """Explicit sink wins; otherwise the ambient one from usage_sink_scope."""
    return explicit if explicit is not None else current_usage_sink.get()


def make_usage_sink(db, user_id: str, project_id: Optional[str] = None,
                    job_id: Optional[str] = None):
    """Build an async sink(response) for AIClient.chat_completion."""

    async def sink(response: AIResponse) -> None:
        usage = response.usage or {}
        try:
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
        except (TypeError, ValueError):
            prompt_tokens, completion_tokens = 0, 0
        total = prompt_tokens + completion_tokens
        if not usage.get("total_tokens"):
            pass
        else:
            try:
                total = int(usage["total_tokens"])
            except (TypeError, ValueError):
                pass
        event = LlmUsageEvent(
            user_id=user_id,
            project_id=project_id,
            job_id=job_id,
            provider=response.provider_id,
            model=response.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=estimated_cost_usd(
                response.model, prompt_tokens, completion_tokens
            ),
        )
        db.add(event)
        await db.flush()

    return sink


def _event_fields(response: AIResponse, user_id: str,
                  project_id: Optional[str], job_id: Optional[str]) -> dict:
    """Normalisasi AIResponse -> field LlmUsageEvent (tanpa session)."""
    usage = response.usage or {}
    try:
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        prompt_tokens, completion_tokens = 0, 0
    total = prompt_tokens + completion_tokens
    if usage.get("total_tokens"):
        try:
            total = int(usage["total_tokens"])
        except (TypeError, ValueError):
            pass
    return {
        "user_id": user_id,
        "project_id": project_id,
        "job_id": job_id,
        "provider": response.provider_id,
        "model": response.model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "estimated_cost_usd": estimated_cost_usd(
            response.model, prompt_tokens, completion_tokens
        ),
    }


class BufferedUsageSink:
    """Sink usage yang tahan rollback step (perbaikan P2-5 ronde 2).

    Event LLM dikumpulkan di memori selama run, lalu `drain()` menulis
    semuanya dalam SATU transaksi terpisah SETELAH run selesai — sukses
    atau gagal. Sebelumnya sink menulis di sesi step yang sama, sehingga
    `db.rollback()` di jalur gagal ikut menghapus event call LLM yang
    biayanya tetap terjadi (Analytics meremehkan biaya job bermasalah).
    Drain tidak pernah melempar: gagal tulis hanya dicatat di log.
    """

    def __init__(self, user_id: str, project_id: Optional[str] = None,
                 job_id: Optional[str] = None):
        self.user_id = user_id
        self.project_id = project_id
        self.job_id = job_id
        self.events: list[dict] = []

    async def sink(self, response: AIResponse) -> None:
        self.events.append(_event_fields(
            response, self.user_id, self.project_id, self.job_id
        ))

    async def drain(self, engine) -> int:
        """Tulis semua event yang terkumpul; kembalikan jumlah yang ditulis."""
        if not self.events:
            return 0
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        events, self.events = self.events, []
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            for fields in events:
                session.add(LlmUsageEvent(**fields))
            await session.commit()
        return len(events)


def make_buffered_usage_sink(user_id: str, project_id: Optional[str] = None,
                            job_id: Optional[str] = None) -> BufferedUsageSink:
    """Bangun BufferedUsageSink untuk satu run auto-generate."""
    return BufferedUsageSink(user_id, project_id=project_id, job_id=job_id)
