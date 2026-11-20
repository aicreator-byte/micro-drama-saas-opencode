import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient, MockTransport, Request, Response

from app.core.config import settings
from app.main import app
from app.models.subscription import Subscription
from app.services.stripe_client import (
    StripeClient,
    StripeLiveKeyForbiddenError,
    StripeNotConfiguredError,
)
from app.api.v1 import billing as billing_api


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
        if request.url.path == "/v1/subscriptions/sub_test_1" and request.method == "GET":
            return Response(200, json={
                "id": "sub_test_1", "object": "subscription", "status": "active",
            })
        if request.url.path == "/v1/subscriptions/sub_test_1" and request.method == "DELETE":
            return Response(200, json={
                "id": "sub_test_1", "object": "subscription", "status": "canceled",
            })
        return Response(404, json={"error": {"message": "not mocked"}})
    return handler


def _sign_event(secret: str, event: dict) -> tuple[bytes, dict]:
    """Bangun (raw body, headers) untuk event webhook bertanda tangan valid."""
    raw = json.dumps(event).encode()
    timestamp = "1700000000"
    signed = f"{timestamp}.".encode() + raw
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return raw, {"stripe-signature": f"t={timestamp},v1={v1}"}


class TestStripeClient:
    @pytest.mark.asyncio
    async def test_create_checkout_session_posts_with_bearer_auth(self):
        captured = []
        transport = MockTransport(_mock_stripe_handler(captured))
        async with AsyncClient(transport=transport) as http_client:
            client = StripeClient(secret_key="sk_test_abc", client=http_client)
            session = await client.create_checkout_session(
                "cus_test_123", "price_test_pro",
                "https://example.com/success", "https://example.com/cancel",
            )
        assert session["id"] == "cs_test_123"
        assert session["url"] == "https://checkout.stripe.com/pay/cs_test_123"
        req = [r for r in captured if r.url.path == "/v1/checkout/sessions"][0]
        assert req.method == "POST"
        assert str(req.url) == "https://api.stripe.com/v1/checkout/sessions"
        assert req.headers["Authorization"] == "Bearer sk_test_abc"

    @pytest.mark.asyncio
    async def test_create_customer_and_subscription_methods(self):
        captured = []
        transport = MockTransport(_mock_stripe_handler(captured))
        async with AsyncClient(transport=transport) as http_client:
            client = StripeClient(secret_key="sk_test_abc", client=http_client)
            customer = await client.create_customer("a@example.com", "Alice")
            assert customer["id"] == "cus_test_123"
            sub = await client.get_subscription("sub_test_1")
            assert sub["status"] == "active"
            cancelled = await client.cancel_subscription("sub_test_1")
            assert cancelled["status"] == "canceled"
        methods = {(r.method, r.url.path) for r in captured}
        assert ("POST", "/v1/customers") in methods
        assert ("GET", "/v1/subscriptions/sub_test_1") in methods
        assert ("DELETE", "/v1/subscriptions/sub_test_1") in methods

    def test_live_key_rejected(self):
        with pytest.raises(StripeLiveKeyForbiddenError):
            StripeClient(secret_key="sk_live_forbidden")

    def test_empty_key_rejected(self):
        with pytest.raises(StripeNotConfiguredError):
            StripeClient(secret_key="")


class TestBillingEndpoints:
    @pytest.mark.asyncio
    async def test_list_plans(self, client: AsyncClient):
        resp = await client.get("/api/v1/billing/plans")
        assert resp.status_code == 200
        plans = resp.json()["plans"]
        assert len(plans) == 3
        assert {p["id"] for p in plans} == {"starter", "pro", "studio"}
        assert all("configured" in p for p in plans)

    @pytest.mark.asyncio
    async def test_checkout_without_key_returns_503(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
        resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth_headers)
        assert resp.status_code == 503
        assert "Stripe not configured" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_checkout_with_live_key_returns_503(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_live_nope")
        resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth_headers)
        assert resp.status_code == 503
        assert "live keys are forbidden" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_checkout_unknown_plan_400(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_abc")
        resp = await client.post("/api/v1/billing/checkout", json={"plan": "nope"}, headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_checkout_unconfigured_price_503(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_abc")
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "")
        resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth_headers)
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_checkout_returns_checkout_url_with_mocked_stripe(
        self, client: AsyncClient, auth_headers, monkeypatch,
    ):
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_test_pro")
        captured = []
        transport = MockTransport(_mock_stripe_handler(captured))
        http_client = AsyncClient(transport=transport)
        mock_client = StripeClient(secret_key="sk_test_abc", client=http_client)
        app.dependency_overrides[billing_api.get_stripe_client] = lambda: mock_client
        try:
            resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth_headers)
        finally:
            app.dependency_overrides.pop(billing_api.get_stripe_client, None)
            await http_client.aclose()
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"
        assert data["mode"] == "test"

    @pytest.mark.asyncio
    async def test_subscription_empty_then_webhook_creates_it(
        self, client: AsyncClient, auth_headers, test_user, db_session, monkeypatch,
    ):
        # Perbaikan P1-1: webhook TANPA secret kini ditolak — event di sini
        # ditandatangani dengan secret tes (jalur yang benar).
        secret = "whsec_test_secret"
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)
        resp = await client.get("/api/v1/billing/subscription", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["has_subscription"] is False

        event = {
            "id": "evt_test_1",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {"object": {
                "id": "cs_test_123",
                "object": "checkout.session",
                "customer": "cus_test_123",
                "subscription": "sub_test_1",
                "metadata": {"user_id": test_user.id, "plan": "pro"},
            }},
        }
        raw, headers = _sign_event(secret, event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text

        from sqlalchemy import select
        user_id = test_user.id  # read before expire_all (expired attrs can't lazy-load)
        db_session.expire_all()
        result = await db_session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        sub = result.scalar_one()
        assert sub.plan == "pro"
        assert sub.stripe_customer_id == "cus_test_123"
        assert sub.stripe_subscription_id == "sub_test_1"
        assert sub.status == "active"

        resp = await client.get("/api/v1/billing/subscription", headers=auth_headers)
        assert resp.json()["has_subscription"] is True
        assert resp.json()["subscription"]["plan"] == "pro"

    @pytest.mark.asyncio
    async def test_webhook_without_secret_always_refused(
        self, client: AsyncClient, monkeypatch,
    ):
        """P1-1: tanpa STRIPE_WEBHOOK_SECRET, SEMUA event ditolak — dulu
        event livemode=false diterima apa adanya (klaim langganan gratis)."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        for livemode in (False, True):
            event = {
                "id": f"evt_nosecret_{livemode}", "type": "checkout.session.completed",
                "livemode": livemode,
                "data": {"object": {"id": "cs_x", "customer": "cus_x"}},
            }
            resp = await client.post("/api/v1/billing/webhook", json=event)
            assert resp.status_code == 400, f"livemode={livemode} must be refused"
            assert "not configured" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_subscription_updated(
        self, client: AsyncClient, test_user, db_session, monkeypatch,
    ):
        secret = "whsec_test_secret"
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)
        db_session.add(Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_1",
            plan="starter",
            status="active",
        ))
        await db_session.commit()

        event = {
            "id": "evt_test_2",
            "type": "customer.subscription.updated",
            "livemode": False,
            "data": {"object": {
                "id": "sub_test_1",
                "object": "subscription",
                "customer": "cus_test_123",
                "status": "past_due",
                "current_period_end": 1790000000,
                "metadata": {"plan": "pro"},
            }},
        }
        raw, headers = _sign_event(secret, event)
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text

        from sqlalchemy import select
        db_session.expire_all()
        result = await db_session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == "sub_test_1")
        )
        sub = result.scalar_one()
        assert sub.status == "past_due"
        assert sub.plan == "pro"
        assert sub.current_period_end is not None

    @pytest.mark.asyncio
    async def test_webhook_valid_signature_accepted(self, client: AsyncClient, test_user, monkeypatch):
        secret = "whsec_test_secret"
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)
        event = {
            "id": "evt_test_3",
            "type": "checkout.session.completed",
            "livemode": True,  # live event OK when the signature verifies
            "data": {"object": {
                "id": "cs_test_999",
                "object": "checkout.session",
                "customer": "cus_test_999",
                "subscription": "sub_test_999",
                "metadata": {"user_id": test_user.id, "plan": "studio"},
            }},
        }
        raw = json.dumps(event).encode()
        timestamp = "1700000000"
        signed = f"{timestamp}.".encode() + raw
        v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        headers = {"stripe-signature": f"t={timestamp},v1={v1}"}
        resp = await client.post("/api/v1/billing/webhook", content=raw, headers=headers)
        assert resp.status_code == 200, resp.text

        resp_bad = await client.post(
            "/api/v1/billing/webhook", content=raw,
            headers={"stripe-signature": f"t={timestamp},v1=deadbeef"},
        )
        assert resp_bad.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, client: AsyncClient, auth_headers, test_user, db_session, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_test_pro")
        db_session.add(Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_1",
            plan="pro",
            status="active",
        ))
        await db_session.commit()

        captured = []
        transport = MockTransport(_mock_stripe_handler(captured))
        http_client = AsyncClient(transport=transport)
        mock_client = StripeClient(secret_key="sk_test_abc", client=http_client)
        app.dependency_overrides[billing_api.get_stripe_client] = lambda: mock_client
        try:
            resp = await client.post("/api/v1/billing/cancel", headers=auth_headers)
        finally:
            app.dependency_overrides.pop(billing_api.get_stripe_client, None)
            await http_client.aclose()
        assert resp.status_code == 200, resp.text
        assert resp.json()["subscription"]["status"] == "canceled"
        assert any(r.method == "DELETE" for r in captured)

    @pytest.mark.asyncio
    async def test_cancel_without_subscription_404(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_abc")
        resp = await client.post("/api/v1/billing/cancel", headers=auth_headers)
        assert resp.status_code == 404
