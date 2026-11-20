"""Tes regresi perbaikan audit ronde 2 (FIX-ROUND2).

P1-1: webhook tanpa secret / tanpa tanda tangan valid ditolak, tidak ada
  Subscription yang dibuat.
P1-2: checkout mengirim metadata ke Stripe; webhook event asli tanpa
  metadata tetap membuat Subscription via pemetaan CheckoutSession;
  event yang tidak bisa dikaitkan gagal keras (400).
P2-1: batas upload ditegakkan sebelum file dibaca penuh.
P2-2: token stream SSE (di test_auto_generate_stream.py).
P2-4: VideoJob processing ikut resume saat restart.
P2-5: usage event LLM tetap tercatat bila step gagal.
P2-6: REST patch kolaborasi.
P2-7: SSE timeout 120 dtk + reconnect (stream dibuka ulang).
"""
import asyncio
import hashlib
import hmac
import json
import shutil
import subprocess
from urllib.parse import parse_qs

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, MockTransport, Request, Response
from sqlalchemy import select

from app.api.v1 import auto_generate as ag_module
from app.api.v1 import billing as billing_api
from app.api.v1.auto_generate import _chat_json
from app.api.v1.video import resume_stale_video_jobs
from app.core.config import settings
from app.core.security import create_stream_token
from app.main import app
from app.models.auto_generate import (
    AutoGenerateJob, AutoGenerateStep, AutoGenerateJobStatus,
    AutoGenerateStepName, AutoGenerateStepStatus, STEP_ORDER,
)
from app.models.checkout_session import CheckoutSession
from app.models.llm_usage import LlmUsageEvent
from app.models.subscription import Subscription
from app.models.video_job import VideoJob
from app.services.llm_usage import make_buffered_usage_sink
from app.services.stripe_client import StripeClient

SECRET = "whsec_test_secret"


def _sign_event(event: dict, secret: str = SECRET) -> tuple[bytes, dict]:
    raw = json.dumps(event).encode()
    timestamp = "1700000000"
    signed = f"{timestamp}.".encode() + raw
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return raw, {"stripe-signature": f"t={timestamp},v1={v1}"}


def _checkout_event(*, session_id="cs_test_123", customer="cus_test_123",
                    subscription="sub_test_1", metadata=None, livemode=False):
    obj = {
        "id": session_id,
        "object": "checkout.session",
        "customer": customer,
        "subscription": subscription,
    }
    if metadata is not None:
        obj["metadata"] = metadata
    return {
        "id": "evt_test_1", "type": "checkout.session.completed",
        "livemode": livemode, "data": {"object": obj},
    }


async def _subscription_count(db_session) -> int:
    db_session.expire_all()
    rows = (await db_session.execute(select(Subscription))).scalars().all()
    return len(rows)


class TestP1WebhookRejected:
    @pytest.mark.asyncio
    async def test_forged_webhook_without_secret_rejected(
        self, client: AsyncClient, test_user, db_session, monkeypatch,
    ):
        """P1-1 (reproduksi audit): event palsu livemode=false tanpa secret
        dulu diterima dan membuat langganan Studio gratis — kini 400 dan
        tidak ada Subscription yang dibuat."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        event = _checkout_event(metadata={"user_id": test_user.id, "plan": "studio"})
        resp = await client.post("/api/v1/billing/webhook", json=event)
        assert resp.status_code == 400
        assert await _subscription_count(db_session) == 0

    @pytest.mark.asyncio
    async def test_forged_webhook_bad_signature_rejected(
        self, client: AsyncClient, test_user, db_session, monkeypatch,
    ):
        """P1-1: secret diset tapi tanda tangan hilang/salah -> 400."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        event = _checkout_event(metadata={"user_id": test_user.id, "plan": "studio"})
        resp = await client.post("/api/v1/billing/webhook", json=event)
        assert resp.status_code == 400
        assert await _subscription_count(db_session) == 0

        raw, headers = _sign_event(event, secret="whsec_wrong")
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 400
        assert await _subscription_count(db_session) == 0

    @pytest.mark.asyncio
    async def test_webhook_unknown_user_id_refused(
        self, client: AsyncClient, db_session, monkeypatch,
    ):
        """P1-1 pertahanan lapis dua: metadata user_id yang tidak ada di
        DB lokal tidak boleh membuat Subscription, walau tanda tangan valid."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        event = _checkout_event(metadata={"user_id": "no-such-user", "plan": "studio"})
        raw, headers = _sign_event(event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text  # event diproses, tapi...
        assert await _subscription_count(db_session) == 0


def _mock_stripe_handler(captured):
    async def handler(request: Request) -> Response:
        captured.append(request)
        if request.url.path == "/v1/customers" and request.method == "POST":
            return Response(200, json={"id": "cus_test_123", "object": "customer"})
        if request.url.path == "/v1/checkout/sessions" and request.method == "POST":
            return Response(200, json={
                "id": "cs_test_123",
                "object": "checkout.session",
                "url": "https://checkout.stripe.com/pay/cs_test_123",
            })
        return Response(404, json={"error": {"message": "not mocked"}})
    return handler


class TestP1RealPaymentFlow:
    @pytest.mark.asyncio
    async def test_checkout_sends_metadata_and_records_mapping(
        self, client: AsyncClient, auth_headers, test_user, db_session, monkeypatch,
    ):
        """P1-2: create_checkout_session mengirim metadata user_id/plan
        (sesi + subscription_data) dan endpoint mencatat CheckoutSession."""
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_test_pro")
        captured = []
        transport = MockTransport(_mock_stripe_handler(captured))
        http_client = AsyncClient(transport=transport)
        mock_client = StripeClient(secret_key="sk_test_abc", client=http_client)
        app.dependency_overrides[billing_api.get_stripe_client] = lambda: mock_client
        try:
            resp = await client.post(
                "/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth_headers
            )
        finally:
            app.dependency_overrides.pop(billing_api.get_stripe_client, None)
            await http_client.aclose()
        assert resp.status_code == 200, resp.text
        assert resp.json()["session_id"] == "cs_test_123"

        req = [r for r in captured if r.url.path == "/v1/checkout/sessions"][0]
        body = parse_qs(req.content.decode())
        assert body["metadata[user_id]"] == [test_user.id]
        assert body["metadata[plan]"] == ["pro"]
        assert body["subscription_data[metadata][user_id]"] == [test_user.id]
        assert body["subscription_data[metadata][plan]"] == ["pro"]

        user_id = test_user.id  # baca sebelum expire_all (expired attrs can't lazy-load)
        db_session.expire_all()
        row = (await db_session.execute(
            select(CheckoutSession).where(CheckoutSession.id == "cs_test_123")
        )).scalar_one_or_none()
        assert row is not None
        assert row.user_id == user_id
        assert row.plan == "pro"
        assert row.stripe_customer_id == "cus_test_123"

    @pytest.mark.asyncio
    async def test_real_webhook_without_metadata_creates_subscription(
        self, client: AsyncClient, test_user, db_session, monkeypatch,
    ):
        """P1-2 (reproduksi audit): event Stripe asli TANPA metadata dulu
        dijawab received:true tapi langganan tidak tercatat — kini
        pemetaan CheckoutSession mengaitkannya ke user + plan."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        db_session.add(CheckoutSession(
            id="cs_test_123", user_id=test_user.id, plan="pro",
            stripe_customer_id="cus_test_123",
        ))
        await db_session.commit()

        event = _checkout_event(metadata=None)  # persis seperti Stripe asli
        raw, headers = _sign_event(event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text

        user_id = test_user.id  # baca sebelum expire_all
        db_session.expire_all()
        sub = (await db_session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )).scalar_one_or_none()
        assert sub is not None
        assert sub.plan == "pro"
        assert sub.status == "active"
        assert sub.stripe_customer_id == "cus_test_123"
        assert sub.stripe_subscription_id == "sub_test_1"

    @pytest.mark.asyncio
    async def test_unattributable_webhook_fails_loudly(
        self, client: AsyncClient, db_session, monkeypatch,
    ):
        """P1-2: event yang tidak bisa dikaitkan ke user mana pun gagal
        keras (400), bukan diam-diam received:true."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        event = _checkout_event(
            session_id="cs_unknown", customer="cus_unknown",
            subscription="sub_unknown", metadata=None,
        )
        raw, headers = _sign_event(event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 400
        assert await _subscription_count(db_session) == 0

    @pytest.mark.asyncio
    async def test_subscription_updated_plan_from_price_id(
        self, client: AsyncClient, test_user, db_session, monkeypatch,
    ):
        """P1-2: plan diturunkan dari price id objek subscription asli —
        metadata plan (bila ada) kalah oleh harga yang ditagih Stripe."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_test_pro")
        db_session.add(Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_1",
            plan="starter", status="active",
        ))
        await db_session.commit()

        event = {
            "id": "evt_test_9", "type": "customer.subscription.updated",
            "livemode": False,
            "data": {"object": {
                "id": "sub_test_1",
                "object": "subscription",
                "customer": "cus_test_123",
                "status": "active",
                "current_period_end": 1790000000,
                "items": {"data": [{"price": {"id": "price_test_pro"}}]},
                "metadata": {"plan": "studio"},  # sengaja menyesatkan
            }},
        }
        raw, headers = _sign_event(event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text
        db_session.expire_all()
        sub = (await db_session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == "sub_test_1")
        )).scalar_one()
        assert sub.plan == "pro"


class TestP2UploadLimit:
    @pytest.mark.asyncio
    async def test_upload_over_small_limit_rejected(
        self, client: AsyncClient, auth_headers, test_project, monkeypatch,
    ):
        """P2-1: batas ditegakkan saat streaming (limit kecil di sini
        supaya tes tidak butuh file 100MB)."""
        monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10)
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/assets",
            files={"file": ("big.bin", b"x" * 20, "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 413

    @pytest.mark.asyncio
    async def test_upload_under_limit_ok(
        self, client: AsyncClient, auth_headers, test_project, monkeypatch,
    ):
        monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10)
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/assets",
            files={"file": ("small.bin", b"12345", "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text


FFMPEG = shutil.which("ffmpeg")
pytestmark_video = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not available")


def _make_clip(path, color="red", duration=1):
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi",
         "-i", f"testsrc=duration={duration}:size=320x240:rate=10",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        capture_output=True, check=True, timeout=60,
    )


async def _wait_for_video_job(client, project_id, job_id, headers, timeout=30.0):
    deadline = asyncio.get_event_loop().time() + timeout
    last = None
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/video/jobs/{job_id}", headers=headers
        )
        last = resp.json() if resp.status_code == 200 else None
        if last and last["status"] in ("completed", "failed"):
            return last
        await asyncio.sleep(0.25)
    raise AssertionError(f"video job {job_id} did not finish; last={last}")


class TestP2VideoResume:
    @pytest.mark.asyncio
    @pytestmark_video
    async def test_processing_video_job_resumes_to_completed(
        self, client: AsyncClient, auth_headers, test_project,
        db_session, db_engine, tmp_path, monkeypatch,
    ):
        """P2-4: job `processing` saat restart di-resume dan selesai
        (parameter lengkap tersimpan di baris job)."""
        monkeypatch.setattr(settings, "ASSET_STORAGE_DIR", str(tmp_path))
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        clip_dir = tmp_path / test_project.id
        clip_dir.mkdir(parents=True, exist_ok=True)
        _make_clip(clip_dir / "c1.mp4")
        key = f"{test_project.id}/c1.mp4"

        job = VideoJob(
            project_id=test_project.id, status="processing",
            input_files=json.dumps([key]),
            subtitle_key=None, audio_key=None, resolution="1080x1920",
        )
        db_session.add(job)
        await db_session.commit()

        resumed = await resume_stale_video_jobs(db_engine)
        assert resumed == [job.id]

        data = await _wait_for_video_job(
            client, test_project.id, job.id, auth_headers
        )
        assert data["status"] == "completed"
        assert data["output_path"] == f"video-outputs/{job.id}.mp4"

    @pytest.mark.asyncio
    async def test_video_job_without_inputs_fails_loudly(
        self, client: AsyncClient, auth_headers, test_project,
        db_session, db_engine,
    ):
        """P2-4: job lama tanpa input tersimpan tidak bisa di-resume —
        ditandai failed, bukan menggantung `processing` selamanya."""
        job = VideoJob(
            project_id=test_project.id, status="processing",
            input_files=None,
        )
        db_session.add(job)
        await db_session.commit()

        resumed = await resume_stale_video_jobs(db_engine)
        assert resumed == []

        job_id = job.id  # baca sebelum expire_all
        db_session.expire_all()
        row = (await db_session.execute(
            select(VideoJob).where(VideoJob.id == job_id)
        )).scalar_one()
        assert row.status == "failed"
        assert "interrupted by restart" in (row.error_message or "")

    @pytest.mark.asyncio
    async def test_video_resume_noop_when_no_stale_jobs(self, db_engine):
        assert await resume_stale_video_jobs(db_engine) == []


class TestP2UsageSurvivesFailure:
    @pytest.mark.asyncio
    async def test_buffered_sink_survives_session_rollback(
        self, db_session, db_engine, test_user, test_project,
    ):
        """P2-5 (unit): event yang masuk buffer tetap tersimpan walau sesi
        utama di-rollback sesudahnya."""
        from app.services.ai_client import AIResponse

        buffered = make_buffered_usage_sink(
            test_user.id, project_id=test_project.id, job_id="job-x"
        )
        await buffered.sink(AIResponse(
            content="{}", provider_id="mock", model="mock-model",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        ))
        # Simulasi rollback step yang gagal: tidak ada yang tersimpan di
        # sesi utama (buffer memang belum di-drain).
        await db_session.rollback()
        assert await buffered.drain(db_engine) == 1

        db_session.expire_all()
        events = (await db_session.execute(
            select(LlmUsageEvent).where(LlmUsageEvent.job_id == "job-x")
        )).scalars().all()
        assert len(events) == 1
        assert (events[0].prompt_tokens, events[0].completion_tokens) == (100, 200)

    @pytest.mark.asyncio
    async def test_failed_step_keeps_its_llm_usage(
        self, client: AsyncClient, auth_headers, test_project, test_user,
        test_settings_with_mock, db_session, monkeypatch,
    ):
        """P2-5 (integrasi): step 2 gagal SETELAH 1 call LLM — event
        call itu + event step 1 tetap tercatat (dulu ikut ter-rollback)."""
        async def failing_characters(db, job, project, user):
            await _chat_json(
                db,
                "You are a professional TV series writer. Create the main cast "
                "for a micro-drama series.",
            )
            raise HTTPException(status_code=502, detail="boom (simulated)")

        monkeypatch.setitem(
            ag_module.STEP_RUNNERS, AutoGenerateStepName.CHARACTERS,
            failing_characters,
        )
        created = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate",
            json={"title": "T", "genre": "Romance", "total_episodes": 5,
                  "premise": "A struggling young woman marries a cold billionaire CEO."},
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]

        last = None
        deadline = asyncio.get_event_loop().time() + 30.0
        while asyncio.get_event_loop().time() < deadline:
            resp = await client.get(
                f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}",
                headers=auth_headers,
            )
            last = resp.json()
            if last["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.25)
        assert last["status"] == "failed"
        assert last["steps"][1]["step"] == "characters"
        assert last["steps"][1]["status"] == "failed"

        db_session.expire_all()
        events = (await db_session.execute(
            select(LlmUsageEvent).where(LlmUsageEvent.job_id == job_id)
        )).scalars().all()
        # 1 call step bible (sukses) + 1 call step characters (gagal).
        assert len(events) == 2
        assert all(e.model == "mock-model" for e in events)


class TestP2CollabPatch:
    @pytest.mark.asyncio
    async def test_rest_patch_updates_bible(
        self, client: AsyncClient, auth_headers, test_project, db_session,
    ):
        """P2-6: PATCH bible via REST (fallback bila WS tidak tersedia)."""
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/collab/patch",
            json={"field": "premise", "value": "Premise baru dari REST"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["field"] == "premise"
        assert resp.json()["value"] == "Premise baru dari REST"

        from app.models.series_bible import SeriesBible
        project_id = test_project.id  # baca sebelum expire_all
        db_session.expire_all()
        bible = (await db_session.execute(
            select(SeriesBible).where(SeriesBible.project_id == project_id)
        )).scalar_one()
        assert bible.premise == "Premise baru dari REST"

    @pytest.mark.asyncio
    async def test_rest_patch_rejects_bad_field(
        self, client: AsyncClient, auth_headers, test_project,
    ):
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/collab/patch",
            json={"field": "id", "value": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rest_patch_other_users_project_is_404(
        self, client: AsyncClient, auth_headers2, test_project,
    ):
        resp = await client.post(
            f"/api/v1/projects/{test_project.id}/collab/patch",
            json={"field": "premise", "value": "x"},
            headers=auth_headers2,
        )
        assert resp.status_code == 404


async def _read_stream_events(client, url, headers, timeout=30.0):
    """Kumpulkan (event, data) sampai event `done` (salinan helper tes SSE)."""
    events = []
    deadline = asyncio.get_event_loop().time() + timeout
    async with client.stream("GET", url, headers=headers) as resp:
        assert resp.status_code == 200, resp.text
        current_event = None
        async for line in resp.aiter_lines():
            if asyncio.get_event_loop().time() > deadline:
                raise AssertionError(f"stream did not finish; got {events}")
            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
            elif line.startswith("data:") and current_event is not None:
                events.append((current_event, json.loads(line[len("data:"):].strip())))
                if current_event == "done":
                    break
                current_event = None
    return events


class TestP2SseTimeoutReconnect:
    @pytest.mark.asyncio
    async def test_stream_timeout_then_reopen_works(
        self, client: AsyncClient, auth_headers, test_project,
        db_session, monkeypatch,
    ):
        """P2-7: stream menutup dengan `done timeout` setelah batas waktu
        — dan stream yang dibuka ulang (reconnect) tetap jalan + memberi
        progress. Batas waktu dipendekkan di tes ini (0,6 dtk)."""
        job = AutoGenerateJob(
            project_id=test_project.id, title="T", genre="Romance",
            total_episodes=5, premise="x",
            status=AutoGenerateJobStatus.RUNNING,
        )
        db_session.add(job)
        await db_session.flush()
        for order, step_name in enumerate(STEP_ORDER):
            db_session.add(AutoGenerateStep(
                job_id=job.id, step=step_name, step_order=order,
                status=AutoGenerateStepStatus.PENDING,
            ))
        await db_session.commit()

        monkeypatch.setattr(ag_module, "SSE_TIMEOUT_SECONDS", 0.6)
        url = f"/api/v1/projects/{test_project.id}/auto-generate/{job.id}/stream"
        events = await _read_stream_events(client, url, auth_headers)
        kinds = [k for k, _ in events]
        assert "progress" in kinds
        assert kinds[-1] == "done"
        assert events[-1][1]["status"] == "timeout"

        # Reconnect: buka ulang stream yang sama — harus tetap 200 +
        # progress (job masih RUNNING, tidak ada background runner).
        events2 = await _read_stream_events(client, url, auth_headers)
        kinds2 = [k for k, _ in events2]
        assert "progress" in kinds2
        assert kinds2[-1] == "done"
        assert events2[-1][1]["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_expired_stream_token_is_401(
        self, client: AsyncClient, auth_headers, test_project,
        test_user, test_settings_with_mock,
    ):
        """P2-2: token stream kedaluwarsa ditolak."""
        created = await client.post(
            f"/api/v1/projects/{test_project.id}/auto-generate",
            json={"title": "T", "genre": "Romance", "total_episodes": 5,
                  "premise": "x"},
            headers=auth_headers,
        )
        job_id = created.json()["id"]
        expired = create_stream_token(test_user.id, job_id, expires_minutes=-1)
        resp = await client.get(
            f"/api/v1/projects/{test_project.id}/auto-generate/{job_id}/stream"
            f"?token={expired}",
            headers={},
        )
        assert resp.status_code == 401
