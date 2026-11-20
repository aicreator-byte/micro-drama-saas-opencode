"""Stripe client (subscription, TEST MODE ONLY).

- Secret key from settings.STRIPE_SECRET_KEY.
- Empty key -> StripeNotConfiguredError ("Stripe not configured").
- Key starting with "sk_live_" -> StripeLiveKeyForbiddenError: live keys
  are forbidden in this build (Di has no credit card; test mode only).
- The httpx.AsyncClient is injectable so tests can use MockTransport and
  no test ever hits the real Stripe API.
"""
import httpx

from app.core.config import settings

BASE_URL = "https://api.stripe.com/v1"


class StripeError(Exception):
    pass


class StripeNotConfiguredError(StripeError):
    pass


class StripeLiveKeyForbiddenError(StripeError):
    pass


class StripeClient:
    def __init__(self, secret_key: str | None = None, client: httpx.AsyncClient | None = None):
        key = secret_key if secret_key is not None else settings.STRIPE_SECRET_KEY
        if not key:
            raise StripeNotConfiguredError(
                "Stripe not configured: set STRIPE_SECRET_KEY (test key, sk_test_...)"
            )
        if key.startswith("sk_live_"):
            raise StripeLiveKeyForbiddenError(
                "live keys are forbidden in this build: use a Stripe test key (sk_test_...)"
            )
        self._secret_key = key
        # trust_env=False: httpx parses NO_PROXY as URL patterns and
        # crashes (InvalidURL) on bracketed IPv6 entries like "[::1]"
        # present in this VM's environment. Stripe is called with an
        # explicit client anyway; no env proxy is consulted.
        self._client = client or httpx.AsyncClient(
            headers={"Authorization": f"Bearer {key}"}, trust_env=False
        )
        self._owns_client = client is None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._secret_key}"}

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        kwargs.setdefault("headers", self._headers())
        response = await self._client.request(method, f"{BASE_URL}{path}", **kwargs)
        if response.status_code >= 400:
            raise StripeError(
                f"Stripe API error {response.status_code}: {response.text[:500]}"
            )
        return response.json()

    async def create_customer(
        self, email: str, name: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        data: dict[str, str] = {"email": email}
        if name:
            data["name"] = name
        # Metadata user_id: supaya customer Stripe bisa dikaitkan kembali
        # ke user lokal bila webhook datang tanpa metadata (P1-2).
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)
        return await self._request("POST", "/customers", data=data)

    async def create_checkout_session(
        self, customer_id: str, price_id: str, success_url: str, cancel_url: str,
        metadata: dict | None = None,
    ) -> dict:
        data = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        # P1-2: metadata HARUS dikirim — webhook membaca user_id/plan
        # dari sini. Tanpa ini event Stripe asli selalu bermetadata kosong
        # dan langganan berbayar tidak pernah tercatat. Metadata dikirim
        # di dua tempat: sesi checkout (dibaca di
        # checkout.session.completed) DAN subscription_data (diwarisi
        # objek subscription, dibaca di customer.subscription.*).
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)
                data[f"subscription_data[metadata][{key}]"] = str(value)
        return await self._request("POST", "/checkout/sessions", data=data)

    async def get_subscription(self, subscription_id: str) -> dict:
        return await self._request("GET", f"/subscriptions/{subscription_id}")

    async def cancel_subscription(self, subscription_id: str) -> dict:
        return await self._request("DELETE", f"/subscriptions/{subscription_id}")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
