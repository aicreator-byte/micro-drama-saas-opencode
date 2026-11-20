"""Per-model LLM price table — ESTIMASI, not official vendor pricing.

All values are USD per 1,000,000 tokens (prompt + completion charged at
the same blended rate here, because the callers only need one honest
order-of-magnitude estimate). Override any model at runtime with an env
var named LLM_PRICE_<MODEL>, where <MODEL> is the model id uppercased
with every non-alphanumeric character replaced by "_", e.g.:

    LLM_PRICE_NVIDIA_NEMOTRON_3_ULTRA_550B_A55B=0.80

A model with no entry here (and no env override) has no known price, so
estimated_cost_usd is None — an honest blank, never a guessed number.
"""
import os
import re
from typing import Optional

# ESTIMASI — placeholder rates, NOT official NVIDIA/vendor pricing.
# Update from the vendor's price list (or via the env override above)
# before quoting costs to anyone.
PRICE_PER_1M_USD = {
    "nvidia/nemotron-3-ultra-550b-a55b": 0.50,
    "nvidia/nemotron-3-super-120b-a12b": 0.20,
    "nvidia/nemotron-3.5-super-vl-120b-a12b": 0.20,
    "nvidia/nemotron-3.5-bolt-e4b": 0.05,
    "mock-model": 0.0,
}


def _env_var_name(model: str) -> str:
    return "LLM_PRICE_" + re.sub(r"[^A-Z0-9]", "_", model.upper())


def price_per_1m_usd(model: Optional[str]) -> Optional[float]:
    """USD per 1M tokens for a model, or None when unknown."""
    if not model:
        return None
    env_value = os.getenv(_env_var_name(model))
    if env_value is not None:
        try:
            return float(env_value)
        except ValueError:
            return None
    return PRICE_PER_1M_USD.get(model)


def estimated_cost_usd(
    model: Optional[str], prompt_tokens: int, completion_tokens: int
) -> Optional[float]:
    """Blended estimate: (prompt + completion) / 1e6 * price, or None."""
    price = price_per_1m_usd(model)
    if price is None:
        return None
    return (int(prompt_tokens or 0) + int(completion_tokens or 0)) / 1_000_000 * price
