"""Google account fallback for Flow Bridge tasks.

Covers the service loop (first account fails -> second succeeds; all
fail -> honest error; non-account errors never trigger fallback) and
the HTTP execute/retry endpoints (expired first account -> valid second
account; all expired -> 503 + task FAILED; manual retry after fixing an
account; auto-select of a usable account at task creation).
"""
import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.encryption import encryption_service
from app.models.flow_bridge import FlowBridgeTask, FlowBridgeTaskStatus
from app.models.google_account import GoogleAccount, GoogleAccountStatus
from app.services.google_account_fallback import (
    AllGoogleAccountsFailed,
    GoogleAccountFailure,
    classify_account_failure,
    execute_flow_task_with_fallback,
    is_account_failure_reason,
    run_with_fallback,
)


def _session_blob(email: str) -> str:
    return encryption_service.encrypt(json.dumps({
        "access_token": f"tok-{email}",
        "refresh_token": f"ref-{email}",
    }))


async def _make_account(db_session, user, email, expires_in_hours=1,
                        status=GoogleAccountStatus.CONNECTED,
                        error_message=None):
    account = GoogleAccount(
        user_id=user.id,
        email=email,
        display_name=email.split("@")[0],
        encrypted_session_data=_session_blob(email),
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        status=status,
        error_message=error_message,
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


async def _make_task(db_session, project, google_account_id=None):
    task = FlowBridgeTask(
        project_id=project.id,
        google_account_id=google_account_id,
        title="Fallback test task",
        task_type="video_gen",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def _create_task_via_api(client, auth_headers, project, google_account_id=None):
    payload = {"title": "API fallback task", "task_type": "video_gen"}
    if google_account_id:
        payload["google_account_id"] = google_account_id
    response = await client.post(
        f"/api/v1/projects/{project.id}/tasks", json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


class TestFallbackClassification:
    def test_quota_and_429_are_account_failures(self):
        assert is_account_failure_reason("Quota exceeded for this account")
        assert is_account_failure_reason("429 Too Many Requests")
        assert is_account_failure_reason("token expired, refresh failed")
        assert classify_account_failure(
            GoogleAccountFailure("quota exceeded", status_code=429)) is not None

    def test_bad_prompt_is_not_an_account_failure(self):
        assert not is_account_failure_reason("invalid prompt: empty")
        assert classify_account_failure(ValueError("invalid prompt")) is None


class TestRunWithFallback:
    @pytest.mark.asyncio
    async def test_first_account_quota_second_succeeds(
            self, db_session, test_user, test_project):
        a = await _make_account(db_session, test_user, "a@example.com")
        b = await _make_account(db_session, test_user, "b@example.com")
        task = await _make_task(db_session, test_project, a.id)
        tried = []

        async def executor(account):
            tried.append(account.email)
            if account.id == a.id:
                raise GoogleAccountFailure("quota exceeded", status_code=429)
            return {"generated": True}

        result, attempts, used = await execute_flow_task_with_fallback(
            db_session, task, test_user.id, executor=executor)
        assert result == {"generated": True}
        assert used.id == b.id
        assert tried == ["a@example.com", "b@example.com"]
        assert [x["outcome"] for x in attempts] == ["failed", "success"]
        assert "quota exceeded" in attempts[0]["reason"]
        assert task.status == FlowBridgeTaskStatus.READY_FOR_GENERATION
        assert task.google_account_id == b.id
        history = json.loads(task.fallback_history)
        assert len(history) == 2
        assert history[0]["email"] == "a@example.com"

    @pytest.mark.asyncio
    async def test_all_accounts_fail_is_honest_error(
            self, db_session, test_user, test_project):
        a = await _make_account(db_session, test_user, "a@example.com")
        b = await _make_account(db_session, test_user, "b@example.com")
        task = await _make_task(db_session, test_project, a.id)

        async def executor(account):
            raise GoogleAccountFailure("quota exceeded", status_code=429)

        with pytest.raises(AllGoogleAccountsFailed) as exc_info:
            await execute_flow_task_with_fallback(
                db_session, task, test_user.id, executor=executor)
        assert len(exc_info.value.attempts) == 2
        assert task.status == FlowBridgeTaskStatus.FAILED
        assert "a@example.com" in task.error_message
        assert "b@example.com" in task.error_message
        assert len(json.loads(task.fallback_history)) == 2

    @pytest.mark.asyncio
    async def test_non_account_error_does_not_fall_back(
            self, db_session, test_user, test_project):
        a = await _make_account(db_session, test_user, "a@example.com")
        b = await _make_account(db_session, test_user, "b@example.com")
        tried = []

        async def executor(account):
            tried.append(account.email)
            raise ValueError("invalid prompt: empty")

        with pytest.raises(ValueError, match="invalid prompt"):
            await run_with_fallback([a, b], executor)
        assert tried == ["a@example.com"]  # B never touched


class TestExecuteEndpoint:
    @pytest.mark.asyncio
    async def test_execute_falls_back_to_valid_account(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project):
        expired = await _make_account(
            db_session, test_user, "expired@example.com", expires_in_hours=-1)
        valid = await _make_account(
            db_session, test_user, "valid@example.com", expires_in_hours=2)
        task = await _create_task_via_api(
            client, auth_headers, test_project, expired.id)

        response = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}/execute",
            headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ready_for_generation"
        assert data["google_account_id"] == valid.id
        history = data["fallback_history"]
        assert len(history) == 2
        assert history[0]["email"] == "expired@example.com"
        assert history[0]["outcome"] == "failed"
        assert "expired" in history[0]["reason"]
        assert history[1]["email"] == "valid@example.com"
        assert history[1]["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_execute_all_fail_returns_503_and_marks_task_failed(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project):
        a = await _make_account(
            db_session, test_user, "a@example.com", expires_in_hours=-1)
        b = await _make_account(
            db_session, test_user, "b@example.com", expires_in_hours=-2)
        task = await _create_task_via_api(
            client, auth_headers, test_project, a.id)

        response = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}/execute",
            headers=auth_headers)
        assert response.status_code == 503, response.text
        assert len(response.json()["detail"]["attempts"]) == 2

        get_response = await client.get(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}",
            headers=auth_headers)
        assert get_response.json()["status"] == "failed"
        assert "a@example.com" in get_response.json()["error_message"]
        assert "b@example.com" in get_response.json()["error_message"]

    @pytest.mark.asyncio
    async def test_retry_after_fixing_account(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project):
        a = await _make_account(
            db_session, test_user, "a@example.com", expires_in_hours=-1)
        b = await _make_account(
            db_session, test_user, "b@example.com", expires_in_hours=-1)
        task = await _create_task_via_api(
            client, auth_headers, test_project, a.id)

        first = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}/execute",
            headers=auth_headers)
        assert first.status_code == 503

        # Fix B's session (e.g. quota reset / token refreshed by the user).
        b.session_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        await db_session.commit()

        retry = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}/retry",
            headers=auth_headers)
        assert retry.status_code == 200, retry.text
        assert retry.json()["status"] == "ready_for_generation"
        assert retry.json()["google_account_id"] == b.id

    @pytest.mark.asyncio
    async def test_retry_completed_task_rejected(
            self, client: AsyncClient, auth_headers, test_project):
        task = await _create_task_via_api(client, auth_headers, test_project)
        patched = await client.patch(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}",
            json={"status": "completed"}, headers=auth_headers)
        assert patched.status_code == 200
        retry = await client.post(
            f"/api/v1/projects/{test_project.id}/tasks/{task['id']}/retry",
            headers=auth_headers)
        assert retry.status_code == 400

    @pytest.mark.asyncio
    async def test_create_task_auto_selects_usable_account(
            self, client: AsyncClient, auth_headers, db_session,
            test_user, test_project):
        await _make_account(
            db_session, test_user, "expired@example.com", expires_in_hours=-1)
        valid = await _make_account(
            db_session, test_user, "valid@example.com", expires_in_hours=2)
        task = await _create_task_via_api(client, auth_headers, test_project)
        assert task["google_account_id"] == valid.id
