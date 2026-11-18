"""Browser login (email + password, no Cloud Console) + Flow execution
with automatic account switching.

All browser interaction here runs against a FAKE driver — no real
Google account/password exists for testing, so a real Google login is
NOT verified by these tests (see BROWSER-LOGIN-REPORT.md). The fake
driver reproduces the exact outcomes the real driver reports
(login ok / wrong password / captcha / quota exhausted / session
expired), so the fallback loop, session persistence, and endpoint
wiring are tested for real. One test launches the REAL Chromium
against a local page (no network, no credentials) to prove the engine
itself works in this environment.
"""
import json
import socket
import threading
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.encryption import encryption_service
from app.main import app
from app.models.flow_bridge import FlowBridgeTask, FlowBridgeTaskStatus
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.services.browser_flow import (
    BrowserFlowService,
    FlowResult,
    GoogleAccountFailure,
    extract_flow_prompt,
    get_browser_flow_service,
    manual_flow_export,
)
from app.services.browser_proxy import ConnectRelay
from app.services.google_account_fallback import (
    AllGoogleAccountsFailed,
    execute_flow_task_with_fallback,
)


# ---------------------------------------------------------------------------
# Fake browser driver (same outcomes as the real Playwright driver)
# ---------------------------------------------------------------------------

class FakeSession:
    def __init__(self, account_id):
        self.account_id = account_id
        self.closed = False


class FakeBrowserDriver:
    """Behaviour keyed by account email substring:

    * "wrongpass" -> login raises wrong password
    * "captcha"   -> login raises bot detection
    * "nopass"    -> (no password stored; service raises before driver)
    * "quota"     -> run_flow raises quota exhausted
    * "expired"   -> is_logged_in False once, then login succeeds
    * otherwise   -> logged in, run_flow completes with a video URL
    """

    def __init__(self):
        self.logins = []        # emails login was attempted for
        self.runs = []          # (email, prompt) run_flow calls
        self.sessions_opened = []
        self._logged_in = {}    # account_id -> bool
        self._login_seen = set()

    async def open_session(self, account_id, email):
        self.sessions_opened.append(email)
        session = FakeSession(account_id)
        # Accounts whose stored session is dead: login must run (and fail
        # for wrongpass/captcha, succeed for expired).
        if "wrongpass" in email or "captcha" in email:
            self._logged_in[account_id] = False
        elif "expired" in email and account_id not in self._login_seen:
            self._logged_in[account_id] = False
        else:
            self._logged_in.setdefault(account_id, True)
        return session

    async def close_session(self, session):
        session.closed = True

    async def is_logged_in(self, session):
        return self._logged_in.get(session.account_id, False)

    async def login(self, session, email, password):
        self.logins.append(email)
        self._login_seen.add(session.account_id)
        if "wrongpass" in email:
            raise GoogleAccountFailure("Google login failed: wrong password")
        if "captcha" in email:
            raise GoogleAccountFailure(
                "Google login failed: bot detection: captcha")
        if password != f"pw-{email}":
            raise GoogleAccountFailure("Google login failed: wrong password")
        self._logged_in[session.account_id] = True

    async def run_flow(self, session, prompt, timeout_s):
        email = next(
            (e for e in self.sessions_opened if e), "unknown")
        # Recover the email from the logged-in map via account id.
        self.runs.append((session.account_id, prompt))
        account_email = getattr(session, "email", None) or ""
        if "quota" in account_email:
            raise GoogleAccountFailure(
                "Flow quota exhausted for this account (reached your limit)")
        return FlowResult(status="completed",
                          video_url="https://flow.example/v/abc123.mp4",
                          detail="Flow returned a video")

    async def smoke_launch(self):
        return True


def _fake_driver_with_emails():
    """Fake driver that knows each session's email (set by the service)."""
    driver = FakeBrowserDriver()
    orig_open = driver.open_session

    async def open_session(account_id, email):
        session = await orig_open(account_id, email)
        session.email = email
        return session
    driver.open_session = open_session

    orig_run = driver.run_flow

    async def run_flow(session, prompt, timeout_s):
        if "quota" in getattr(session, "email", ""):
            raise GoogleAccountFailure(
                "Flow quota exhausted for this account (reached your limit)")
        return await orig_run(session, prompt, timeout_s)
    driver.run_flow = run_flow
    return driver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_blob(email: str) -> str:
    return encryption_service.encrypt(json.dumps({
        "access_token": f"tok-{email}",
        "refresh_token": f"ref-{email}",
    }))


async def _make_account(db_session, user, email, with_password=True,
                        expires_in_hours=1,
                        status=GoogleAccountStatus.CONNECTED):
    account = GoogleAccount(
        user_id=user.id,
        email=email,
        display_name=email.split("@")[0],
        encrypted_session_data=_session_blob(email),
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        password_encrypted=encryption_service.encrypt(f"pw-{email}") if with_password else None,
        status=status,
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


async def _make_task(db_session, project, google_account_id=None,
                     prompt="A dramatic scene in a Jakarta office, rain"):
    task = FlowBridgeTask(
        project_id=project.id,
        google_account_id=google_account_id,
        title="Browser flow test task",
        task_type="video_gen",
        input_prompts=json.dumps({"prompt": prompt}),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.fixture
def fake_service(tmp_path):
    driver = _fake_driver_with_emails()
    service = BrowserFlowService(driver=driver,
                                 profile_base=str(tmp_path / "profiles"))
    return service, driver


# ---------------------------------------------------------------------------
# Prompt extraction
# ---------------------------------------------------------------------------

class TestPromptExtraction:
    def test_json_dict_prompt(self):
        task = FlowBridgeTask(input_prompts=json.dumps({"prompt": "hello world"}))
        assert extract_flow_prompt(task) == "hello world"

    def test_python_repr_prompt(self):
        # create endpoint stores str(dict) — single quotes, not JSON.
        task = FlowBridgeTask(input_prompts="{'prompt': 'repr prompt'}")
        assert extract_flow_prompt(task) == "repr prompt"

    def test_plain_text_prompt(self):
        task = FlowBridgeTask(input_prompts="just a prompt")
        assert extract_flow_prompt(task) == "just a prompt"

    def test_no_prompt(self):
        task = FlowBridgeTask(input_prompts=None)
        assert extract_flow_prompt(task) == ""


# ---------------------------------------------------------------------------
# Login + session persistence (fake browser)
# ---------------------------------------------------------------------------

class TestBrowserLogin:
    @pytest.mark.asyncio
    async def test_login_mock_session_saved(self, db_session, test_user,
                                            fake_service):
        service, driver = fake_service
        account = await _make_account(db_session, test_user, "a@example.com")
        result = await service.login_account(db_session, account)
        assert result.session_valid is True
        assert result.email == "a@example.com"
        marker = service.read_session_marker(account.id)
        assert marker is not None
        assert marker["email"] == "a@example.com"
        assert marker["method"] == "browser-password"
        assert "password" not in marker  # no secret stored in the marker
        assert "password_encrypted" not in marker
        assert account.status == GoogleAccountStatus.CONNECTED
        assert account.last_verified_at is not None
        assert driver.logins == ["a@example.com"]

    @pytest.mark.asyncio
    async def test_login_wrong_password_is_account_failure(
            self, db_session, test_user, fake_service):
        service, _driver = fake_service
        account = await _make_account(db_session, test_user,
                                      "wrongpass@example.com")
        with pytest.raises(GoogleAccountFailure, match="wrong password"):
            await service.login_account(db_session, account)
        assert service.read_session_marker(account.id) is None

    @pytest.mark.asyncio
    async def test_login_without_stored_password_fails_honestly(
            self, db_session, test_user, fake_service):
        service, driver = fake_service
        account = await _make_account(db_session, test_user, "nopass@example.com",
                                      with_password=False)
        with pytest.raises(GoogleAccountFailure, match="no password stored"):
            await service.login_account(db_session, account)
        assert driver.logins == []  # browser never touched

    @pytest.mark.asyncio
    async def test_expired_session_relogs_in(self, db_session, test_user,
                                             fake_service):
        service, driver = fake_service
        account = await _make_account(db_session, test_user,
                                      "expired@example.com")
        session = await service.ensure_session(db_session, account)
        assert session is not None
        assert "expired@example.com" in driver.logins  # re-login happened
        assert service.read_session_marker(account.id) is not None
        await service.driver.close_session(session)


# ---------------------------------------------------------------------------
# Flow execution with automatic account switching
# ---------------------------------------------------------------------------

class TestBrowserFlowFallback:
    @pytest.mark.asyncio
    async def test_session_fails_switches_account(
            self, db_session, test_user, test_project, fake_service):
        service, driver = fake_service
        bad = await _make_account(db_session, test_user, "wrongpass@example.com")
        good = await _make_account(db_session, test_user, "good@example.com")
        task = await _make_task(db_session, test_project, bad.id)
        result, attempts, used = await execute_flow_task_with_fallback(
            db_session, task, test_user.id,
            executor=service.make_task_executor(db_session, task))
        assert result["flow_status"] == "completed"
        assert result["video_url"] == "https://flow.example/v/abc123.mp4"
        assert used.id == good.id
        assert [a["outcome"] for a in attempts] == ["failed", "success"]
        assert "wrong password" in attempts[0]["reason"]
        assert task.status == FlowBridgeTaskStatus.READY_FOR_GENERATION
        assert task.google_account_id == good.id
        history = json.loads(task.fallback_history)
        assert history[0]["email"] == "wrongpass@example.com"
        assert history[1]["email"] == "good@example.com"

    @pytest.mark.asyncio
    async def test_quota_failure_switches_account(
            self, db_session, test_user, test_project, fake_service):
        service, _driver = fake_service
        quota = await _make_account(db_session, test_user, "quota@example.com")
        good = await _make_account(db_session, test_user, "good@example.com")
        task = await _make_task(db_session, test_project, quota.id)
        _result, attempts, used = await execute_flow_task_with_fallback(
            db_session, task, test_user.id,
            executor=service.make_task_executor(db_session, task))
        assert used.id == good.id
        assert "quota" in attempts[0]["reason"]

    @pytest.mark.asyncio
    async def test_all_accounts_fail_is_honest_error(
            self, db_session, test_user, test_project, fake_service):
        service, _driver = fake_service
        a = await _make_account(db_session, test_user, "wrongpass-a@example.com")
        b = await _make_account(db_session, test_user, "captcha-b@example.com")
        task = await _make_task(db_session, test_project, a.id)
        with pytest.raises(AllGoogleAccountsFailed) as exc_info:
            await execute_flow_task_with_fallback(
                db_session, task, test_user.id,
                executor=service.make_task_executor(db_session, task))
        assert len(exc_info.value.attempts) == 2
        assert task.status == FlowBridgeTaskStatus.FAILED
        assert "wrongpass-a@example.com" in task.error_message
        assert "captcha-b@example.com" in task.error_message
        assert len(json.loads(task.fallback_history)) == 2

    @pytest.mark.asyncio
    async def test_empty_prompt_does_not_fall_back(
            self, db_session, test_user, test_project, fake_service):
        service, driver = fake_service
        a = await _make_account(db_session, test_user, "a@example.com")
        b = await _make_account(db_session, test_user, "b@example.com")
        task = await _make_task(db_session, test_project, a.id, prompt="")
        task.input_prompts = None
        await db_session.commit()
        with pytest.raises(ValueError, match="no input prompt"):
            await execute_flow_task_with_fallback(
                db_session, task, test_user.id,
                executor=service.make_task_executor(db_session, task))
        assert driver.runs == []  # no browser run at all
        assert driver.sessions_opened == []  # B never touched


# ---------------------------------------------------------------------------
# Manual fallback export
# ---------------------------------------------------------------------------

class TestManualExport:
    def test_manual_export_carries_prompt_and_url(self):
        task = FlowBridgeTask(
            id="task-1", title="T",
            input_prompts=json.dumps({"prompt": "rainy Jakarta office"}))
        export = manual_flow_export(task, "a@example.com")
        assert export["prompt"] == "rainy Jakarta office"
        assert export["flow_url"].startswith("https://")
        assert export["account_email"] == "a@example.com"


# ---------------------------------------------------------------------------
# execute-browser endpoint (fake browser service injected)
# ---------------------------------------------------------------------------

class TestExecuteBrowserEndpoint:
    @pytest.mark.asyncio
    async def test_gate_without_env_flag(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project, monkeypatch):
        monkeypatch.delenv("FLOW_AUTOMATION_ENABLED", raising=False)
        task = await _make_task(db_session, test_project)
        response = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task.id}/execute-browser",
            headers=auth_headers)
        assert response.status_code == 503, response.text
        assert "FLOW_AUTOMATION_ENABLED" in response.text

    @pytest.mark.asyncio
    async def test_execute_browser_completes_with_video(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project, fake_service, monkeypatch):
        service, _driver = fake_service
        monkeypatch.setenv("FLOW_AUTOMATION_ENABLED", "1")
        app.dependency_overrides[get_browser_flow_service] = lambda: service
        try:
            account = await _make_account(db_session, test_user, "good@example.com")
            task = await _make_task(db_session, test_project, account.id)
            response = await client.post(
                f"/api/v1/projects/{test_project.id}/tasks/{task.id}/execute-browser",
                headers=auth_headers)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["status"] == "completed"
            assert data["google_account_id"] == account.id
            assert json.loads(data["output_assets"]) == ["https://flow.example/v/abc123.mp4"]
        finally:
            app.dependency_overrides.pop(get_browser_flow_service, None)

    @pytest.mark.asyncio
    async def test_execute_browser_falls_back_then_completes(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project, fake_service, monkeypatch):
        service, _driver = fake_service
        monkeypatch.setenv("FLOW_AUTOMATION_ENABLED", "1")
        app.dependency_overrides[get_browser_flow_service] = lambda: service
        try:
            bad = await _make_account(db_session, test_user, "wrongpass@example.com")
            good = await _make_account(db_session, test_user, "good@example.com")
            task = await _make_task(db_session, test_project, bad.id)
            response = await client.post(
                f"/api/v1/projects/{test_project.id}/tasks/{task.id}/execute-browser",
                headers=auth_headers)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["status"] == "completed"
            assert data["google_account_id"] == good.id
            history = data["fallback_history"]
            assert len(history) == 2
            assert history[0]["email"] == "wrongpass@example.com"
            assert history[0]["outcome"] == "failed"
            assert history[1]["outcome"] == "success"
        finally:
            app.dependency_overrides.pop(get_browser_flow_service, None)

    @pytest.mark.asyncio
    async def test_execute_browser_all_fail_503_with_manual_fallback(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project, fake_service, monkeypatch):
        service, _driver = fake_service
        monkeypatch.setenv("FLOW_AUTOMATION_ENABLED", "1")
        app.dependency_overrides[get_browser_flow_service] = lambda: service
        try:
            a = await _make_account(db_session, test_user, "wrongpass-a@example.com")
            b = await _make_account(db_session, test_user, "captcha-b@example.com")
            task = await _make_task(db_session, test_project, a.id)
            response = await client.post(
                f"/api/v1/projects/{test_project.id}/tasks/{task.id}/execute-browser",
                headers=auth_headers)
            assert response.status_code == 503, response.text
            detail = response.json()["detail"]
            assert len(detail["attempts"]) == 2
            manual = detail["manual_fallback"]
            assert manual["flow_url"].startswith("https://")
            assert "dramatic scene" in manual["prompt"]
            get_response = await client.get(
                f"/api/v1/projects/{test_project.id}/tasks/{task.id}",
                headers=auth_headers)
            assert get_response.json()["status"] == "failed"
        finally:
            app.dependency_overrides.pop(get_browser_flow_service, None)


# ---------------------------------------------------------------------------
# CONNECT relay (stdlib, no network)
# ---------------------------------------------------------------------------

class TestConnectRelay:
    def test_relay_forwards_connect_and_bytes(self):
        # Fake upstream: accepts CONNECT, answers 200, echoes bytes.
        received = {}

        def fake_upstream(port_holder):
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            conn, _ = srv.accept()
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            received["connect"] = data
            conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            payload = conn.recv(4096)
            conn.sendall(b"echo:" + payload)
            conn.close()
            srv.close()

        port_holder: list = []
        thread = threading.Thread(target=fake_upstream, args=(port_holder,),
                                  daemon=True)
        thread.start()
        while not port_holder:
            pass
        relay = ConnectRelay(upstream=("127.0.0.1", port_holder[0], None))
        port = relay.start()
        try:
            client = socket.create_connection(("127.0.0.1", port), timeout=10)
            client.sendall(b"CONNECT target.example:443 HTTP/1.1\r\n"
                           b"Host: target.example:443\r\n\r\n")
            resp = client.recv(4096)
            assert resp.startswith(b"HTTP/1.1 200")
            client.sendall(b"hello")
            assert client.recv(4096) == b"echo:hello"
            client.close()
        finally:
            relay.stop()
        thread.join(timeout=5)
        assert b"CONNECT target.example:443" in received["connect"]
        # Relay must not add a browser User-Agent to the upstream CONNECT.
        assert b"User-Agent" not in received["connect"]


# ---------------------------------------------------------------------------
# Real Chromium, local page only (no Google, no credentials, no network)
# ---------------------------------------------------------------------------

class TestRealBrowserSmoke:
    @pytest.mark.asyncio
    async def test_real_chromium_loads_local_page(self):
        from app.services.browser_flow import PlaywrightBrowserDriver
        driver = PlaywrightBrowserDriver()
        try:
            assert await driver.smoke_launch() is True
        except Exception as exc:
            pytest.skip(f"Chromium unavailable in this environment: {exc}")
        finally:
            await driver.close()
