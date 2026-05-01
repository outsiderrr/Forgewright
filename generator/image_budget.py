"""Cost guard for image generation API calls (ADR-014 / T-1.5.5).

Two ceilings, both in USD (sibling of `generator.budget` but with its own
log file and its own env-var namespace):

  * PER_CALL_IMAGE_BUDGET_USD (default 1.00) — single call ceiling
    (ADR-014 hard cap).
  * DAILY_IMAGE_BUDGET_USD    (default 5.00) — running daily total ceiling
    (ADR-014 API budget envelope).

Override via `FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD` and
`FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD`.

The check/log split (vs. the text-side `check_and_charge`) reflects that the
caller does not yet know the asset stub at check time — providers create
deterministic stubs only after the generation step. Recommended caller
sequence (T-1.5.6 generate_visual orchestration):

    image_budget.check(estimated_cost_usd=..., mode=...)
    result = provider.generate(...)
    image_budget.log_charge(asset_id_stub=result.asset_id_stub, ...)

Manual mode (cost = 0.0) always passes `check()` and still writes through
`log_charge()` — that is ADR-014's unified-interface contract: manual asset
volume is counted through the same channel as paid API usage.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from generator import image_cost_log


class ImageBudgetExceeded(Exception):
    """Raised when an image call would exceed the per-call or daily ceiling."""


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def per_call_image_budget_usd() -> float:
    return _float_env("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", 1.00)


def daily_image_budget_usd() -> float:
    return _float_env("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", 5.00)


def today_total_usd() -> float:
    return sum(float(rec.get("cost_usd", 0.0)) for rec in image_cost_log.read_today())


def check(
    *,
    estimated_cost_usd: float,
    mode: Literal["manual", "api"],
) -> None:
    """Validate an upcoming image call against per-call and daily ceilings.

    Does not write to the cost log — the caller invokes `log_charge()`
    after the provider returns a deterministic asset stub.

    Manual mode (estimated_cost_usd == 0.0 by ADR-014 convention) always
    passes; the function still accepts `mode` for symmetry and so the
    caller cannot accidentally pass an api-mode positive cost as manual.
    """
    if mode == "manual":
        return

    per_call = per_call_image_budget_usd()
    if estimated_cost_usd > per_call:
        raise ImageBudgetExceeded(
            f"per-call image budget exceeded: ${estimated_cost_usd:.4f} > ${per_call:.4f}"
        )

    daily = daily_image_budget_usd()
    today = today_total_usd()
    if today + estimated_cost_usd > daily:
        raise ImageBudgetExceeded(
            f"daily image budget exceeded: today=${today:.4f} + "
            f"${estimated_cost_usd:.4f} > ${daily:.4f}"
        )


def log_charge(
    *,
    timestamp: datetime,
    mode: Literal["manual", "api"],
    provider_id: str,
    asset_kind: str,
    asset_id_stub: str,
    n: int,
    size: tuple[int, int],
    cost_usd: float,
    input_tokens: int | None = None,
) -> None:
    """Write one row to image_cost_log.jsonl after a provider call returned.

    Manual rows (cost_usd=0.0) are written just like API rows.
    """
    width, height = size
    image_cost_log.append(
        {
            "timestamp": timestamp.isoformat(),
            "mode": mode,
            "provider_id": provider_id,
            "asset_kind": asset_kind,
            "asset_id_stub": asset_id_stub,
            "n": n,
            "size_w": width,
            "size_h": height,
            "input_tokens": input_tokens,
            "cost_usd": cost_usd,
        }
    )
