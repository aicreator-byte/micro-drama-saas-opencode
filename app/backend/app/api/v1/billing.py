"""Billing endpoints (Stripe subscription, TEST MODE ONLY).

- GET /billing/plans: public list of plans + whether each price is configured.
- POST /billing/checkout: create/reuse Stripe customer, return checkout_url.
  Stripe not configured -> 503 (never 500); live key -> 503.
- GET /billing/subscription: current user's latest subscription.
- POST /billing/cancel: cancel at Stripe, then mark canceled in DB.
- POST /billing/webhook: Stripe events. Signature (HMAC SHA256,
  STRIPE_WEBHOOK_SECRET) is REQUIRED: without a configured secret every
  event is refused (400) — an unverified event must never create or
  change a Subscription (perbaikan P1-1 ronde 2: sebelumnya event
  livemode=false tanpa secret diterima apa adanya, sehingga siapa pun
  bisa mengklaim paket Studio gratis). Atribusi user tidak lagi hanya
  mengandalkan metadata event: urutan metadata -> baris CheckoutSession
  lokal (dicatat saat checkout) -> Subscription yang sudah ada via
  customer id; event yang tidak bisa dikaitkan ke user mana pun gagal
  keras (400), bukan diam-diam `{"received": true}` (perbaikan P1-2).
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.checkout_session import CheckoutSession
from app.models.subscription import Subscription
from app.models.user import User
from app.services import billing_plans
from app.services.stripe_client import (
    StripeClient,
    StripeError,
    StripeLiveKeyForbiddenError,
    StripeNotConfiguredError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_stripe_client() -> StripeClient:
    """Dependency (overridable in tests). Config errors become 503."""
    try:
        return StripeClient()
    except StripeNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except StripeLiveKeyForbiddenError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _subscription_to_dict(sub: Subscription | None) -> dict | None:
    if sub is None:
        return None
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "stripe_customer_id": sub.stripe_customer_id,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "plan": sub.plan,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


def _unix_to_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


@router.get("/plans")
async def list_plans():
    return {"plans": billing_plans.get_plans()}


@router.post("/checkout")
async def create_checkout(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe: StripeClient = Depends(get_stripe_client),
):
    plan_id = (payload or {}).get("plan")
    plan = billing_plans.get_plan(plan_id) if plan_id else None
    if plan is None:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id!r}")
    price_id = billing_plans.get_price_id(plan_id)
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe price for plan {plan_id!r} is not configured",
        )

    # Reuse the user's existing Stripe customer when we have one.
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    customer_id = existing.stripe_customer_id if existing else None
    if not customer_id:
        try:
            customer = await stripe.create_customer(
                current_user.email, current_user.full_name,
                # P1-2: metadata user_id supaya customer Stripe bisa
                # dikaitkan kembali ke user lokal dari webhook.
                metadata={"user_id": current_user.id},
            )
        except StripeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        customer_id = customer.get("id")
        if not customer_id:
            raise HTTPException(status_code=502, detail="Stripe did not return a customer id")

    base = str(request.base_url).rstrip("/")
    success_url = (payload or {}).get("success_url") or f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = (payload or {}).get("cancel_url") or f"{base}/billing/cancelled"
    try:
        session = await stripe.create_checkout_session(
            customer_id, price_id, success_url, cancel_url,
            # P1-2: metadata user_id + plan — tanpa ini webhook event
            # Stripe asli bermetadata kosong dan langganan tidak tercatat.
            metadata={"user_id": current_user.id, "plan": plan_id},
        )
    except StripeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Catat pemetaan sesi -> user/plan untuk webhook (P1-2): bila event
    # datang tanpa metadata, webhook tetap bisa mengaitkan via session id.
    # Best-effort: kegagalan catat tidak membatalkan checkout (metadata
    # adalah jalur utama); dicatat di log supaya terlihat.
    if session.get("id"):
        try:
            db.add(CheckoutSession(
                id=session["id"],
                user_id=current_user.id,
                plan=plan_id,
                stripe_customer_id=customer_id,
            ))
            await db.commit()
        except Exception as exc:
            logger.warning(f"Could not record checkout session mapping: {exc}")
            await db.rollback()

    return {
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
        "plan": plan_id,
        "mode": "test",
    }


@router.get("/subscription")
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()
    return {"subscription": _subscription_to_dict(sub), "has_subscription": sub is not None}


@router.post("/cancel")
async def cancel_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe: StripeClient = Depends(get_stripe_client),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription found")
    if sub.stripe_subscription_id:
        try:
            await stripe.cancel_subscription(sub.stripe_subscription_id)
        except StripeError as e:
            raise HTTPException(status_code=502, detail=str(e))
    sub.status = "canceled"
    await db.commit()
    await db.refresh(sub)
    return {"subscription": _subscription_to_dict(sub)}


def _verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify a Stripe-Signature header (t=...,v1=...) with HMAC SHA256."""
    if not signature:
        return False
    try:
        parts = dict(
            item.split("=", 1) for item in signature.split(",") if "=" in item
        )
        timestamp = parts.get("t")
        v1_list = [v for k, v in (item.split("=", 1) for item in signature.split(",") if "=" in item) if k == "v1"]
    except ValueError:
        return False
    if not timestamp or not v1_list:
        return False
    signed_payload = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in v1_list)


async def _upsert_subscription(
    db: AsyncSession,
    *,
    user_id: str | None,
    customer_id: str | None,
    stripe_sub_id: str | None,
    plan: str | None,
    status: str | None,
    period_end: datetime | None,
) -> Subscription | None:
    """Upsert by stripe subscription id, else by customer id, else create
    (creation requires user_id, e.g. from checkout metadata).

    Pertahanan P1-1: user_id dari metadata event TIDAK dipercaya buta —
    baris baru hanya dibuat bila user itu benar-benar ada di DB lokal.
    """
    sub = None
    if stripe_sub_id:
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        sub = result.scalar_one_or_none()
    if sub is None and customer_id:
        result = await db.execute(
            select(Subscription)
            .where(Subscription.stripe_customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
    if sub is None:
        if not user_id:
            return None
        user_exists = (await db.execute(
            select(User.id).where(User.id == user_id)
        )).scalar_one_or_none()
        if user_exists is None:
            logger.warning(
                "Webhook upsert refused: user_id %s from event not found", user_id
            )
            return None
        sub = Subscription(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=stripe_sub_id,
            plan=plan or "starter",
            status=status or "incomplete",
            current_period_end=period_end,
        )
        db.add(sub)
    else:
        if customer_id:
            sub.stripe_customer_id = customer_id
        if stripe_sub_id:
            sub.stripe_subscription_id = stripe_sub_id
        if plan:
            sub.plan = plan
        if status:
            sub.status = status
        if period_end:
            sub.current_period_end = period_end
    await db.commit()
    await db.refresh(sub)
    return sub


def _plan_from_subscription_object(obj: dict) -> str | None:
    """Turunkan plan dari price id di objek subscription Stripe asli.

    Lebih bisa dipercaya daripada metadata: price id datang dari objek
    yang ditagih Stripe sendiri. None bila items/price tidak ada.
    """
    try:
        items = ((obj.get("items") or {}).get("data") or [])
        for item in items:
            price_id = ((item or {}).get("price") or {}).get("id")
            plan = billing_plans.get_plan_by_price_id(price_id)
            if plan:
                return plan
    except (AttributeError, TypeError):
        pass
    return None


async def _resolve_webhook_user(
    db: AsyncSession, event_obj: dict, session_id: str | None
) -> tuple[str | None, str | None]:
    """Kaitkan event webhook ke (user_id, plan) lokal.

    Urutan (P1-2): metadata event -> baris CheckoutSession (session id)
    -> Subscription yang sudah ada via customer id. Metadata saja tidak
    cukup: event Stripe asli bisa datang tanpa metadata, dan metadata
    dalam event yang tidak terverifikasi tidak boleh dipercaya — tapi
    handler ini hanya dipanggil SETELAH tanda tangan terverifikasi (atau
    secret tidak diset -> event sudah ditolak), jadi metadata di sini
    autentik dari Stripe.
    """
    metadata = event_obj.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan = metadata.get("plan")
    if user_id:
        return user_id, plan
    if session_id:
        row = (await db.execute(
            select(CheckoutSession).where(CheckoutSession.id == session_id)
        )).scalar_one_or_none()
        if row is not None:
            return row.user_id, row.plan
    customer_id = event_obj.get("customer")
    if customer_id:
        existing = (await db.execute(
            select(Subscription)
            .where(Subscription.stripe_customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if existing is not None:
            return existing.user_id, existing.plan
    return None, None


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    secret = settings.STRIPE_WEBHOOK_SECRET or ""
    if not secret:
        # P1-1: tanpa secret, TIDAK ADA event yang diproses — terverifikasi
        # atau tidak, event yang tidak bisa diverifikasi tidak boleh
        # membuat/mengubah Subscription. Sebelumnya event livemode=false
        # diterima apa adanya (langganan gratis bisa diklaim).
        logger.warning("Stripe webhook refused: STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=400,
            detail="Stripe webhook secret is not configured; refusing unverified event",
        )
    if not _verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        # ID sesi ada di objek event (obj["id"] = cs_...); metadata bisa
        # kosong pada event asli -> diselesaikan via CheckoutSession.
        user_id, plan = await _resolve_webhook_user(db, obj, obj.get("id"))
        if user_id is None:
            logger.error(
                "checkout.session.completed %s cannot be attributed to a user",
                obj.get("id"),
            )
            raise HTTPException(
                status_code=400,
                detail="Cannot attribute checkout event to a user",
            )
        await _upsert_subscription(
            db,
            user_id=user_id,
            customer_id=obj.get("customer"),
            stripe_sub_id=obj.get("subscription"),
            plan=plan or "starter",
            status="active" if obj.get("subscription") else "incomplete",
            period_end=None,
        )
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        # Plan dari price id objek asli lebih utama daripada metadata.
        plan = _plan_from_subscription_object(obj)
        user_id, mapped_plan = await _resolve_webhook_user(db, obj, None)
        if plan is None:
            # Metadata event dulu, baru plan baris lama (fallback terakhir —
            # plan lama tidak boleh menutupi plan yang dibawa event).
            plan = (obj.get("metadata") or {}).get("plan") or mapped_plan
        # Bila tidak ada baris lokal DAN tidak ada user yang bisa
        # dikaitkan, event tidak bisa diproses — gagal keras, bukan
        # diam-diam received:true.
        existing = None
        if obj.get("id"):
            existing = (await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == obj.get("id")
                )
            )).scalar_one_or_none()
        if existing is None and user_id is None:
            logger.error(
                "subscription event %s cannot be attributed to a user",
                obj.get("id"),
            )
            raise HTTPException(
                status_code=400,
                detail="Cannot attribute subscription event to a user",
            )
        await _upsert_subscription(
            db,
            user_id=user_id,
            customer_id=obj.get("customer"),
            stripe_sub_id=obj.get("id"),
            plan=plan,
            status=obj.get("status"),
            period_end=_unix_to_dt(obj.get("current_period_end")),
        )
    else:
        logger.info("Ignoring Stripe webhook event type: %s", event_type)

    return {"received": True}
