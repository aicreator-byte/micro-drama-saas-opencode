"""Billing plans (Stripe subscription, TEST MODE only).

Price IDs come from env (STRIPE_PRICE_STARTER/PRO/STUDIO); empty means
the plan is not configured yet. Plans are built per call so tests can
monkeypatch settings and see the change immediately.
"""
from app.core.config import settings

_PLAN_DEFS = {
    "starter": {
        "name": "Starter",
        "price_monthly_usd": 9,
        "features": [
            "1 proyek aktif",
            "20 episode per proyek",
            "Auto-generate cerita (AI)",
            "Template genre dasar",
        ],
        "price_env": "STRIPE_PRICE_STARTER",
    },
    "pro": {
        "name": "Pro",
        "price_monthly_usd": 29,
        "features": [
            "5 proyek aktif",
            "30 episode per proyek",
            "Auto-generate cerita (AI)",
            "Semua template genre",
            "Kolaborasi real-time",
        ],
        "price_env": "STRIPE_PRICE_PRO",
    },
    "studio": {
        "name": "Studio",
        "price_monthly_usd": 79,
        "features": [
            "Proyek tanpa batas",
            "Episode tanpa batas",
            "Auto-generate cerita (AI)",
            "Semua template genre",
            "Kolaborasi real-time",
            "Dukungan prioritas",
        ],
        "price_env": "STRIPE_PRICE_STUDIO",
    },
}


def get_plans() -> list[dict]:
    plans = []
    for plan_id, definition in _PLAN_DEFS.items():
        price_id = getattr(settings, definition["price_env"], "") or ""
        plans.append({
            "id": plan_id,
            "name": definition["name"],
            "price_monthly_usd": definition["price_monthly_usd"],
            "features": list(definition["features"]),
            "configured": bool(price_id),
        })
    return plans


def get_plan(plan_id: str) -> dict | None:
    for plan in get_plans():
        if plan["id"] == plan_id:
            return plan
    return None


def get_price_id(plan_id: str) -> str:
    definition = _PLAN_DEFS.get(plan_id)
    if not definition:
        return ""
    return getattr(settings, definition["price_env"], "") or ""


def get_plan_by_price_id(price_id: str) -> str | None:
    """Balikkan price id Stripe -> plan id lokal (perbaikan P1-2).

    Dipakai webhook untuk menurunkan plan dari objek subscription asli
    (items.data[0].price.id) bila metadata event kosong — plan dari
    Stripe sendiri lebih bisa dipercaya daripada metadata suntikan.
    """
    if not price_id:
        return None
    for plan_id, definition in _PLAN_DEFS.items():
        if getattr(settings, definition["price_env"], "") == price_id:
            return plan_id
    return None
