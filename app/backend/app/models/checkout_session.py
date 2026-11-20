from sqlalchemy import Column, String, DateTime, ForeignKey
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class CheckoutSession(Base):
    """Pemetaan checkout Stripe -> user lokal (perbaikan P1-2 ronde 2).

    Dibuat saat POST /billing/checkout berhasil membuat sesi Stripe.
    Webhook `checkout.session.completed` memakai baris ini untuk mengaitkan
    event asli ke user BILA metadata event kosong (Stripe tidak menjamin
    metadata selalu ada) — tanpa ini pembayaran asli hilang diam-diam.
    Bukan sumber kebenaran langganan; itu tetap tabel `subscriptions`.
    """

    __tablename__ = "checkout_sessions"

    id = Column(String(255), primary_key=True)  # Stripe checkout session id (cs_...)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    plan = Column(String(50), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
