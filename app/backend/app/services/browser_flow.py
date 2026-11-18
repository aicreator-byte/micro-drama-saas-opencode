"""Browser login (email + password, no Google Cloud Console) + Google
Flow execution with automatic account switching.

This is the browser path Di ordered on 2026-11-17 22:22 WIB ("Hrsnya
login biasa. Dengan browser masing2"): a real Chromium (Playwright)
logs into Google with the account's email + password — the password is
decrypted from the existing ``GoogleAccount.password_encrypted`` column
with the existing encryption service, nothing about encryption changed
— and the login session lives in a persistent browser profile
(``user_data_dir``) per account, so cookies survive restarts.

No ``client_id``/``client_secret`` from Google Cloud Console is used
anywhere here. OAuth keeps existing untouched; this path does not need
it and does not touch it.

Environment facts (verified 2026-11-17 on this VM):
* Playwright 1.65.2 + Chromium are installed (``playwright install
  chromium`` works — the Playwright CDN is reachable from this VM).
* Chromium CANNOT talk directly to the VM egress proxy: every HTTPS
  navigation fails with ``net::ERR_TUNNEL_CONNECTION_FAILED`` while
  curl to the same proxy/target works. A minimal local CONNECT relay
  (``app.services.browser_proxy``) fixes it: Chromium -> relay ->
  egress proxy loads https://accounts.google.com (200, sign-in page).
  The relay is on by default (``FLOW_BROWSER_USE_RELAY=1``); without
  an upstream proxy in the environment it connects directly.
* The egress proxy MITMs TLS, so the browser runs with
  ``ignore_https_errors=True`` by default
  (``FLOW_BROWSER_IGNORE_HTTPS_ERRORS=1``). Security is deferred by
  Di's order; this is recorded here so it is not mistaken for a
  hardening decision.

What is NOT verified (honest limits):
* No real Google account/password was available for testing, so a real
  Google login and a real Flow generation have NEVER run through this
  code. The login steps and Flow selectors are written against
  Google's public sign-in page (verified loaded: 200 + email field)
  and Flow's known layout, but Google changes its DOM and may show
  bot-detection / captcha / 2FA challenges. Those cases are detected
  and reported as account failures (so fallback tries the next
  account) instead of being silently treated as success.
* Flow video generation takes minutes; ``run_flow`` waits up to
  ``FLOW_GENERATION_TIMEOUT_SECONDS`` (default 600s) and then returns
  ``submitted`` — the video may still be generating in Flow.

Fallback wiring: ``BrowserFlowService.make_task_executor`` returns an
``executor`` callable for ``execute_flow_task_with_fallback`` in
``app.services.google_account_fallback`` — the same ordered-retry loop
as the OAuth path, so a failed browser session/quota moves to the next
account and every attempt lands in ``FlowBridgeTask.fallback_history``.
"""
import ast
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import encryption_service
from app.models.flow_bridge import FlowBridgeTask
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.services.google_account_fallback import GoogleAccountFailure

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BrowserUnavailable(Exception):
    """Playwright / Chromium is not usable in this environment."""


class FlowDomError(Exception):
    """The Google Flow page structure was not recognised.

    This is NOT an account failure (it must not burn through the user's
    other accounts): the page changed, or Flow blocked automation in a
    way we do not recognise. Reported honestly, never faked as success.
    """


class FlowBlockedError(GoogleAccountFailure):
    """Flow refused this account (bot detection / captcha / challenge)."""


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class FlowResult:
    """Outcome of one Flow generation attempt."""
    status: str  # "completed" | "submitted"
    video_url: Optional[str] = None
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"flow_status": self.status, "video_url": self.video_url,
                "detail": self.detail}


@dataclass
class BrowserLoginResult:
    email: str
    session_valid: bool
    profile_dir: str
    method: str = "browser-password"
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Dict[str, Any]:
        return {"email": self.email, "session_valid": self.session_valid,
                "profile_dir": self.profile_dir, "method": self.method,
                "verified_at": self.verified_at.isoformat()}


# ---------------------------------------------------------------------------
# Prompt extraction (task.input_prompts is stored as str(...) — see note)
# ---------------------------------------------------------------------------

def extract_flow_prompt(task: FlowBridgeTask) -> str:
    """Pull the generation prompt out of a Flow task's stored input.

    ``input_prompts`` is stored as ``str(value)`` by the create
    endpoint, so it may be JSON, a Python repr, or plain text.
    Returns "" when the task carries no prompt at all.
    """
    raw = task.input_prompts
    if not raw:
        return ""
    value: Any = raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            try:
                value = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                value = raw
    if isinstance(value, dict):
        for key in ("prompt", "text", "description", "input_prompt"):
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key].strip()
        for item in value.values():
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                found = extract_flow_prompt(_FakeTask(str(item)))
                if found:
                    return found
        return ""
    if isinstance(value, str):
        return value.strip()
    return ""


class _FakeTask:
    """Minimal stand-in so extract_flow_prompt can recurse into dicts."""
    def __init__(self, input_prompts: str):
        self.input_prompts = input_prompts


def manual_flow_export(task: FlowBridgeTask,
                       account_email: Optional[str] = None) -> Dict[str, Any]:
    """Manual fallback: everything a human needs to run this task in
    Google Flow by hand when browser automation fails or is blocked."""
    return {
        "flow_url": settings.GOOGLE_FLOW_URL,
        "prompt": extract_flow_prompt(task),
        "task_id": task.id,
        "task_title": task.title,
        "account_email": account_email,
        "note": ("Browser automation failed or is unavailable — open the "
                 "Flow URL above, sign in with the account shown (or any "
                 "of your Google accounts), paste the prompt, generate."),
    }


# ---------------------------------------------------------------------------
# Playwright driver (real browser)
# ---------------------------------------------------------------------------

GOOGLE_SIGNIN_URL = "https://accounts.google.com/"
GOOGLE_ACCOUNT_URL = "https://myaccount.google.com/"

# Fragments (lowercase) of page text that mean the login did NOT succeed.
_LOGIN_FAILURE_MARKERS = {
    "wrong password": "wrong password",
    "couldn't find your google account": "account not found",
    "couldn’t find your google account": "account not found",
    "this account has been disabled": "account disabled",
    "account has been disabled": "account disabled",
    "2-step verification": "two-factor authentication required",
    "verify it's you": "identity verification challenge",
    "verify it’s you": "identity verification challenge",
    "unusual traffic": "bot detection: unusual traffic",
    "not a robot": "bot detection: captcha",
    "confirm you're not a robot": "bot detection: captcha",
    "confirm you’re not a robot": "bot detection: captcha",
    "try again later": "login rate limited, try again later",
}

# Fragments meaning this account's Flow quota/credits are exhausted.
_FLOW_QUOTA_MARKERS = (
    "reached your limit",
    "out of credits",
    "no credits left",
    "quota exceeded",
    "try again tomorrow",
    "try again next month",
    "upgrade to get more",
)


def _profile_dir_for(account_id: str) -> Path:
    base = Path(os.path.expanduser(settings.FLOW_BROWSER_PROFILE_DIR))
    return base / account_id


def _session_marker_path(account_id: str) -> Path:
    return _profile_dir_for(account_id) / "session.json"


class PlaywrightBrowserDriver:
    """Real Chromium driver. One persistent browser context per account.

    A persistent context keeps its own ``user_data_dir`` (cookies,
    localStorage), so a login done once survives process restarts and
    the next run only has to check the session is still valid.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._relay_url: Optional[str] = None

    # -- lifecycle ------------------------------------------------------
    def _ensure_playwright(self):
        if self._playwright is not None:
            return self._playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserUnavailable(
                "Playwright is not installed in this environment "
                "(pip install playwright + playwright install chromium)") from exc
        return async_playwright()

    def _proxy_config(self) -> Optional[Dict[str, Any]]:
        """Proxy for the browser: local CONNECT relay when enabled."""
        if not settings.FLOW_BROWSER_USE_RELAY:
            return None
        from app.services.browser_proxy import get_relay
        relay = get_relay()
        return {"server": relay.proxy_url}

    async def _start(self):
        if self._playwright is not None:
            return
        manager = self._ensure_playwright()
        self._playwright = await manager.start()
        try:
            self._browser = await self._playwright.chromium.launch(
                headless=settings.FLOW_BROWSER_HEADLESS,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        except Exception as exc:
            await self._playwright.stop()
            self._playwright = None
            raise BrowserUnavailable(
                "Chromium could not be launched: %s "
                "(if the binary is missing, run: playwright install chromium)"
                % exc) from exc

    async def close(self):
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:  # noqa: BLE001 - best-effort shutdown
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:  # noqa: BLE001 - best-effort shutdown
                pass
            self._playwright = None

    # -- sessions -------------------------------------------------------
    async def open_session(self, account_id: str, email: str):
        """Open (or re-open) the persistent context for one account."""
        await self._start()
        assert self._playwright is not None
        profile_dir = _profile_dir_for(account_id)
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=settings.FLOW_BROWSER_HEADLESS,
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=settings.FLOW_BROWSER_IGNORE_HTTPS_ERRORS,
            proxy=self._proxy_config(),
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
        )
        return context

    async def close_session(self, session) -> None:
        try:
            await session.close()
        except Exception:  # noqa: BLE001 - best-effort shutdown
            pass

    async def _page(self, session):
        pages = session.pages
        if pages:
            return pages[0]
        return await session.new_page()

    async def is_logged_in(self, session) -> bool:
        """True when the stored browser session is still signed in."""
        page = await self._page(session)
        try:
            # "commit" is enough: we only need the final URL to detect a
            # redirect back to sign-in. domcontentloaded on Google's
            # account page can exceed 30s through the VM proxy chain.
            await page.goto(GOOGLE_ACCOUNT_URL, wait_until="commit",
                            timeout=60000)
        except Exception as exc:
            raise FlowDomError(
                f"could not reach Google account page: {exc}") from exc
        if "accounts.google.com" in page.url:
            return False
        try:
            body = (await page.content()).lower()
        except Exception:  # noqa: BLE001 - fall back to URL check
            return "myaccount.google.com" in page.url
        return ("myaccount.google.com" in page.url
                and "sign in" not in body[:2000])

    async def login(self, session, email: str, password: str) -> None:
        """Sign in with email + password. Raises GoogleAccountFailure on
        wrong password / disabled account / 2FA / captcha / bot block."""
        page = await self._page(session)
        await page.goto(GOOGLE_SIGNIN_URL, wait_until="domcontentloaded",
                        timeout=60000)
        email_input = page.locator(
            "input[type='email'], #identifierId").first
        try:
            await email_input.wait_for(state="visible", timeout=15000)
        except Exception as exc:
            raise FlowDomError(
                "Google sign-in page did not show an email field — "
                "page structure changed or automation blocked") from exc
        await email_input.fill(email)
        await page.locator("#identifierNext").click()
        # After Next, Google shows one of: the password field, an error
        # ("Couldn't find your Google Account"), or a redirect to
        # /v3/signin/rejected (unknown account / automation rejected —
        # verified live 2026-11-17 for a nonexistent account). Poll for
        # all three instead of a single snapshot: the page re-renders
        # ("Loading") for several seconds before settling.
        await self._wait_for_password_or_rejection(page, timeout_ms=30000)

        password_input = page.locator(
            "input[type='password'], input[name='Passwd']").first
        if "signin/rejected" in page.url:
            raise GoogleAccountFailure(
                "Google rejected the sign-in for this account "
                "(account not found, or automation rejected)")
        try:
            await password_input.wait_for(state="visible", timeout=5000)
        except Exception as exc:
            await self._raise_if_login_failed(page)
            raise FlowDomError(
                "Google sign-in page did not show a password field — "
                "page structure changed or automation blocked "
                f"(url={page.url}, text={await self._page_snippet(page)})"
            ) from exc
        await password_input.fill(password)
        await page.locator("#passwordNext").click()
        await page.wait_for_timeout(3000)
        await self._raise_if_login_failed(page)
        # Success = we land on the account page (or anywhere that is not
        # the sign-in flow). Verify with a real check, not the click.
        if not await self.is_logged_in(session):
            await self._raise_if_login_failed(page)
            raise GoogleAccountFailure(
                "login did not complete: still on the sign-in page "
                "(Google may have shown an unrecognised challenge)")

    async def _wait_for_password_or_rejection(self, page,
                                              timeout_ms: int = 30000) -> None:
        """Poll after the email step until the password field is visible,
        the page is rejected, or an error message appears."""
        deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
        while True:
            if "signin/rejected" in page.url:
                return
            try:
                if await page.locator(
                        "input[type='password']").first.is_visible():
                    return
            except Exception:  # noqa: BLE001 - keep polling
                pass
            try:
                await self._raise_if_login_failed(page)
            except GoogleAccountFailure:
                raise
            if asyncio.get_running_loop().time() >= deadline:
                return
            await page.wait_for_timeout(1000)

    @staticmethod
    async def _page_snippet(page, limit: int = 200) -> str:
        try:
            text = await page.inner_text("body")
        except Exception:  # noqa: BLE001 - no text available
            return ""
        return " ".join(text.split())[:limit]

    async def _raise_if_login_failed(self, page) -> None:
        if "signin/rejected" in page.url:
            raise GoogleAccountFailure(
                "Google rejected the sign-in for this account "
                "(account not found, or automation rejected)")
        try:
            text = (await page.inner_text("body")).lower()
        except Exception:  # noqa: BLE001 - no text to inspect
            return
        for marker, reason in _LOGIN_FAILURE_MARKERS.items():
            if marker in text:
                raise GoogleAccountFailure(
                    f"Google login failed: {reason}")

    async def run_flow(self, session, prompt: str,
                       timeout_s: int) -> FlowResult:
        """Run one prompt in Google Flow. Returns completed/submitted.

        Raises GoogleAccountFailure on quota exhaustion / bot block,
        FlowDomError when the Flow page structure is not recognised.
        """
        if not prompt or not prompt.strip():
            raise ValueError("invalid prompt: empty")
        page = await self._page(session)
        try:
            await page.goto(settings.GOOGLE_FLOW_URL,
                            wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            raise FlowDomError(
                f"could not reach Google Flow ({settings.GOOGLE_FLOW_URL}): "
                f"{exc}") from exc
        if "accounts.google.com" in page.url:
            raise GoogleAccountFailure(
                "browser session expired: Flow redirected to sign-in")
        await self._raise_if_flow_quota(page)

        prompt_box = page.locator(
            "textarea[placeholder*='Describe'], "
            "textarea[aria-label*='prompt' i], "
            "textarea[placeholder*='prompt' i], "
            "[contenteditable='true'][data-placeholder*='prompt' i], "
            "textarea").first
        try:
            await prompt_box.wait_for(state="visible", timeout=20000)
        except Exception as exc:
            raise FlowDomError(
                "Google Flow page did not show a prompt box — page "
                "structure changed or automation blocked") from exc
        await prompt_box.fill(prompt)
        submit = page.locator(
            "button[aria-label*='Create' i], "
            "button[aria-label*='Generate' i], "
            "button:has-text('Create'), "
            "button[type='submit']").first
        try:
            await submit.wait_for(state="visible", timeout=10000)
            await submit.click()
        except Exception as exc:
            raise FlowDomError(
                "Google Flow page did not show a Create/Generate button — "
                "page structure changed or automation blocked") from exc

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        while True:
            await self._raise_if_flow_quota(page)
            video = page.locator("video[src], a[href$='.mp4']").first
            try:
                await video.wait_for(state="attached", timeout=5000)
                url = await video.get_attribute("src") or \
                    await video.get_attribute("href")
                if url:
                    return FlowResult(status="completed", video_url=url,
                                      detail="Flow returned a video")
            except Exception:  # noqa: BLE001 - not ready yet, keep polling
                pass
            if loop.time() >= deadline:
                return FlowResult(
                    status="submitted",
                    detail=("prompt submitted to Flow but no finished video "
                            "appeared within %ss — it may still be "
                            "generating; check Flow manually" % timeout_s))
            await page.wait_for_timeout(10000)

    async def _raise_if_flow_quota(self, page) -> None:
        try:
            text = (await page.inner_text("body")).lower()
        except Exception:  # noqa: BLE001 - no text to inspect
            return
        for marker in _FLOW_QUOTA_MARKERS:
            if marker in text:
                raise GoogleAccountFailure(
                    f"Flow quota exhausted for this account ({marker})")
        if "not a robot" in text or "unusual traffic" in text:
            raise FlowBlockedError(
                "Flow blocked automation for this account (bot detection)")

    async def smoke_launch(self) -> bool:
        """Launch Chromium and load a local page — proves the engine
        works without any Google credentials or network."""
        await self._start()
        assert self._browser is not None
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto("data:text/html,<title>ok</title><h1>hi</h1>")
            return await page.title() == "ok"
        finally:
            await context.close()


# ---------------------------------------------------------------------------
# Service: login + session reuse + Flow execution with fallback
# ---------------------------------------------------------------------------

class BrowserFlowService:
    """Orchestrates browser login / Flow runs over an injected driver.

    The driver is injectable so tests can use a fake browser (no real
    Google account exists for testing); production uses
    :class:`PlaywrightBrowserDriver`.
    """

    def __init__(self, driver=None,
                 profile_base: Optional[str] = None):
        self.driver = driver or PlaywrightBrowserDriver()
        self._profile_base = profile_base  # tests only; else settings

    # -- session markers (disk, no secrets) ------------------------------
    def _marker_path(self, account_id: str) -> Path:
        if self._profile_base:
            return Path(self._profile_base) / account_id / "session.json"
        return _session_marker_path(account_id)

    def read_session_marker(self, account_id: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(self._marker_path(account_id).read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def write_session_marker(self, account_id: str, email: str) -> None:
        path = self._marker_path(account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "email": email,
            "method": "browser-password",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }))

    # -- password (existing encryption, unchanged) -----------------------
    def decrypt_password(self, account: GoogleAccount) -> str:
        if not account.password_encrypted:
            raise GoogleAccountFailure(
                "no password stored for account — add the Google password "
                "in the account settings first")
        try:
            password = encryption_service.decrypt(account.password_encrypted)
        except Exception as exc:
            raise GoogleAccountFailure(
                "stored password cannot be decrypted") from exc
        if not password:
            raise GoogleAccountFailure("no password stored for account")
        return password

    # -- login / session --------------------------------------------------
    async def login_account(self, db: AsyncSession,
                            account: GoogleAccount) -> BrowserLoginResult:
        """Log in with the stored password and persist the session.

        Password is decrypted in memory only, typed into Google's form,
        and never written to disk or logs. The session lives in the
        account's persistent browser profile on disk.
        """
        password = self.decrypt_password(account)
        session = await self.driver.open_session(account.id, account.email)
        try:
            await self.driver.login(session, account.email, password)
        finally:
            await self.driver.close_session(session)
        self.write_session_marker(account.id, account.email)
        now = datetime.now(timezone.utc)
        account.status = GoogleAccountStatus.CONNECTED
        account.last_verified_at = now
        account.last_used_at = now
        account.error_message = None
        await db.commit()
        await db.refresh(account)
        return BrowserLoginResult(
            email=account.email, session_valid=True,
            profile_dir=str(_profile_dir_for(account.id)),
            verified_at=now)

    async def ensure_session(self, db: AsyncSession,
                             account: GoogleAccount):
        """Return a logged-in browser session for the account.

        Reuses the stored profile when it is still signed in, otherwise
        logs in again with the stored password. Raises
        GoogleAccountFailure when login fails (wrong password / 2FA /
        captcha / disabled) — the fallback loop then tries the next
        account.
        """
        session = await self.driver.open_session(account.id, account.email)
        try:
            if await self.driver.is_logged_in(session):
                self.write_session_marker(account.id, account.email)
                return session
        except (FlowDomError, GoogleAccountFailure):
            await self.driver.close_session(session)
            raise
        except Exception:  # noqa: BLE001 - treat as "not logged in"
            pass
        # Not logged in (or check inconclusive): log in with password.
        password = self.decrypt_password(account)
        await self.driver.login(session, account.email, password)
        self.write_session_marker(account.id, account.email)
        now = datetime.now(timezone.utc)
        account.status = GoogleAccountStatus.CONNECTED
        account.last_verified_at = now
        account.error_message = None
        await db.commit()
        return session

    # -- Flow execution ---------------------------------------------------
    async def run_flow_for_account(self, db: AsyncSession,
                                   task: FlowBridgeTask,
                                   account: GoogleAccount) -> Dict[str, Any]:
        """One Flow attempt for one account: session + prompt -> result."""
        prompt = extract_flow_prompt(task)
        if not prompt:
            raise ValueError("invalid prompt: task has no input prompt")
        session = await self.ensure_session(db, account)
        try:
            result = await self.driver.run_flow(
                session, prompt, settings.FLOW_GENERATION_TIMEOUT_SECONDS)
        finally:
            await self.driver.close_session(session)
        account.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return {**result.as_dict(), "email": account.email}

    def make_task_executor(
            self, db: AsyncSession, task: FlowBridgeTask
    ) -> Callable[[GoogleAccount], Awaitable[Dict[str, Any]]]:
        """Executor for ``execute_flow_task_with_fallback``: each account
        attempt logs in (or reuses its browser session) and runs the
        Flow prompt; account failures fall through to the next account."""
        async def _attempt(account: GoogleAccount) -> Dict[str, Any]:
            return await self.run_flow_for_account(db, task, account)
        return _attempt


# Global service instance (same pattern as automation_service).
_browser_flow_service: Optional[BrowserFlowService] = None


def get_browser_flow_service() -> BrowserFlowService:
    """Dependency injection for the browser Flow service."""
    global _browser_flow_service
    if _browser_flow_service is None:
        _browser_flow_service = BrowserFlowService()
    return _browser_flow_service


def automation_enabled() -> bool:
    """Real browser automation is opt-in (FLOW_AUTOMATION_ENABLED=1)."""
    return os.getenv("FLOW_AUTOMATION_ENABLED") == "1"


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False
