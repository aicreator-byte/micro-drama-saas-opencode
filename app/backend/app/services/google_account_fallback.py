"""
Google account fallback for Flow Bridge tasks.

Mirrors the LLM provider fallback pattern in ``app.services.ai_client``:
try candidates in order, move to the next one only on an account failure
(quota exhausted / 429 / token invalid / refresh failed), and fail loudly
when every account is exhausted instead of silently succeeding.

There is no automatic Flow execution in this leg yet (real browser
automation is gated behind FLOW_AUTOMATION_ENABLED=1 + Playwright, and
mock automation must never touch real session data). Fallback therefore
runs at the account-selection + task-retry level:

* ``check_account_usable`` validates a stored account locally (status,
  decryptable session, unexpired session, access token present). It makes
  no network call and never fabricates a session.
* ``run_with_fallback`` is the generic ordered-retry loop. Callers inject
  an ``attempt`` callable (e.g. the real Flow executor once it exists);
  the default Flow-task executor only validates account usability and
  marks the task ready for generation in Flow.
* ``execute_flow_task_with_fallback`` wires the loop to a FlowBridgeTask:
  it records every attempt (account + reason) in
  ``FlowBridgeTask.fallback_history``, moves ``google_account_id`` to the
  account that worked, and marks the task FAILED with an honest
  per-account error summary when all accounts are exhausted.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.google_account import GoogleAccount, GoogleAccountStatus

logger = logging.getLogger(__name__)

# Substrings (lowercase) that mark an error as an *account* failure worth
# falling back over. Anything else (bad prompt, invalid task data, ...) is
# not an account problem and must NOT trigger a switch to another account.
_ACCOUNT_FAILURE_MARKERS = (
    "quota",
    "quota_exceeded",
    "rate limit",
    "rate_limit",
    "too many requests",
    "token expired",
    "token invalid",
    "invalid_token",
    "invalid_grant",
    "refresh failed",
    "refresh_token",
    "session expired",
    "session invalid",
    "unauthorized",
    "authentication",
    "account suspended",
    "account disabled",
)

_ACCOUNT_FAILURE_STATUS_CODES = {401, 403, 429}


class GoogleAccountFailure(Exception):
    """One Google account failed in a way fallback may recover from."""

    def __init__(self, reason: str, status_code: Optional[int] = None,
                 account_id: Optional[str] = None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.account_id = account_id


class AllGoogleAccountsFailed(Exception):
    """Every candidate Google account failed; carries the per-account log."""

    def __init__(self, message: str, attempts: List[Dict[str, Any]]):
        super().__init__(message)
        self.attempts = attempts


@dataclass
class FallbackAttempt:
    google_account_id: Optional[str]
    email: Optional[str]
    outcome: str  # "success" | "failed" | "skipped"
    reason: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "google_account_id": self.google_account_id,
            "email": self.email,
            "outcome": self.outcome,
            "reason": self.reason,
        }


def is_account_failure_reason(reason: str) -> bool:
    """True when an error message describes an account-side failure."""
    text = (reason or "").lower()
    return any(marker in text for marker in _ACCOUNT_FAILURE_MARKERS)


def is_account_failure_status(status_code: Optional[int]) -> bool:
    return status_code in _ACCOUNT_FAILURE_STATUS_CODES


def classify_account_failure(exc: BaseException) -> Optional[str]:
    """Return a reason string if ``exc`` is an account failure, else None.

    Non-account errors return None so the caller re-raises them instead
    of burning through the user's other accounts.
    """
    if isinstance(exc, GoogleAccountFailure):
        return exc.reason
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and is_account_failure_status(status_code):
        return str(exc)
    if is_account_failure_reason(str(exc)):
        return str(exc)
    return None


def check_account_usable(account: GoogleAccount,
                         now: Optional[datetime] = None) -> Optional[str]:
    """Return None if the account looks usable, else the failure reason.

    Local-only check of stored state: status, decryptable session data,
    unexpired session, access token present. No network call, no token
    refresh, no fabricated session.
    """
    now = now or datetime.now(timezone.utc)
    if account.status != GoogleAccountStatus.CONNECTED:
        return f"account status is {account.status.value}"
    if not account.encrypted_session_data:
        return "no session data stored for account"
    if account.session_expires_at is not None:
        expires_at = account.session_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return "session expired"
    # A stored quota/rate-limit failure means this account is exhausted
    # until its quota resets; do not pick it first.
    if account.error_message and is_account_failure_reason(account.error_message):
        return f"account flagged unusable: {account.error_message}"
    try:
        from app.core.encryption import encryption_service
        session = json.loads(
            encryption_service.decrypt(account.encrypted_session_data))
    except Exception:
        return "session data cannot be decrypted (token invalid)"
    if not isinstance(session, dict) or not session.get("access_token"):
        return "no access token in session data"
    return None


def order_candidates(accounts: Sequence[GoogleAccount],
                     preferred_id: Optional[str] = None) -> List[GoogleAccount]:
    """Preferred account first, then least-recently-used first."""
    def _ts(value: Optional[datetime]) -> float:
        # SQLite returns naive datetimes; .timestamp() compares them
        # consistently without mixing naive/aware values.
        return value.timestamp() if value is not None else 0.0

    ordered = sorted(
        accounts,
        key=lambda a: (
            a.last_used_at is not None,
            _ts(a.last_used_at),
            _ts(a.created_at),
        ),
    )
    if preferred_id:
        ordered.sort(key=lambda a: a.id != preferred_id)
    return ordered


async def list_candidate_accounts(db: AsyncSession, user_id: str,
                                  preferred_id: Optional[str] = None
                                  ) -> List[GoogleAccount]:
    """All of the user's Google accounts, fallback order applied."""
    result = await db.execute(
        select(GoogleAccount).where(GoogleAccount.user_id == user_id))
    return order_candidates(result.scalars().all(), preferred_id)


async def run_with_fallback(
    candidates: Sequence[GoogleAccount],
    attempt: Callable[[GoogleAccount], Awaitable[Any]],
) -> tuple[Any, List[Dict[str, Any]], GoogleAccount]:
    """Try ``attempt`` on each candidate until one succeeds.

    Returns ``(result, attempts, used_account)``. Falls back only on
    account failures; any other exception is re-raised immediately.
    Raises ``AllGoogleAccountsFailed`` when no candidate succeeds.
    """
    attempts: List[Dict[str, Any]] = []
    if not candidates:
        raise AllGoogleAccountsFailed(
            "No Google accounts available for fallback", attempts)

    for account in candidates:
        try:
            result = await attempt(account)
        except Exception as exc:  # noqa: BLE001 - classified below
            reason = classify_account_failure(exc)
            if reason is None:
                raise
            attempts.append(FallbackAttempt(
                google_account_id=account.id, email=account.email,
                outcome="failed", reason=reason).as_dict())
            logger.warning(
                "Google account %s (%s) failed, trying next: %s",
                account.id, account.email, reason)
            continue
        attempts.append(FallbackAttempt(
            google_account_id=account.id, email=account.email,
            outcome="success", reason=None).as_dict())
        return result, attempts, account

    summary = "; ".join(
        f"{a['email']}: {a['reason']}" for a in attempts)
    raise AllGoogleAccountsFailed(
        f"All Google accounts failed for Flow task ({summary})", attempts)


async def _default_attempt(account: GoogleAccount) -> Dict[str, Any]:
    """Default Flow attempt: validate the stored account is usable.

    No real Flow generation happens here (no automatic executor exists
    in this leg yet); a usable account means the task is ready to be
    generated in Google Flow with that account.
    """
    reason = check_account_usable(account)
    if reason is not None:
        raise GoogleAccountFailure(reason, account_id=account.id)
    return {"account_usable": True, "email": account.email}


async def execute_flow_task_with_fallback(
    db: AsyncSession,
    task,
    user_id: str,
    executor: Optional[Callable[[GoogleAccount], Awaitable[Any]]] = None,
    preferred_account_id: Optional[str] = None,
    on_success: Optional[Callable[[Any, Any, GoogleAccount], None]] = None,
) -> tuple[Any, List[Dict[str, Any]], GoogleAccount]:
    """Run a Flow task's account fallback and persist the outcome on it.

    On success the task moves to READY_FOR_GENERATION with
    ``google_account_id`` set to the account that worked; on total
    failure the task is marked FAILED with a per-account error summary
    and ``AllGoogleAccountsFailed`` is raised. Every attempt is stored
    in ``task.fallback_history`` (JSON list) either way.

    ``on_success`` (optional) runs after a successful attempt, before
    the commit, and may adjust the task — e.g. the browser executor
    sets COMPLETED/GENERATING with the generated video URL instead of
    the default READY_FOR_GENERATION.
    """
    from app.models.flow_bridge import FlowBridgeTaskStatus

    preferred_id = preferred_account_id or task.google_account_id
    candidates = await list_candidate_accounts(db, user_id, preferred_id)
    attempt = executor or _default_attempt
    now = datetime.now(timezone.utc)

    try:
        result, attempts, used = await run_with_fallback(candidates, attempt)
    except AllGoogleAccountsFailed as exc:
        task.fallback_history = json.dumps(exc.attempts)
        task.status = FlowBridgeTaskStatus.FAILED
        task.error_message = str(exc)
        task.completed_at = now
        await db.commit()
        raise

    task.fallback_history = json.dumps(attempts)
    task.google_account_id = used.id
    task.status = FlowBridgeTaskStatus.READY_FOR_GENERATION
    task.started_at = now
    task.error_message = None
    if on_success is not None:
        on_success(task, result, used)
    used.last_used_at = now
    await db.commit()
    await db.refresh(task)
    return result, attempts, used
