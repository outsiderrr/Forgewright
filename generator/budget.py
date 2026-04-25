"""Cost guard for LLM API calls (ADR-012).

Two ceilings, both in USD:
  * PER_CALL_BUDGET_USD (default 0.50) — a single call may not exceed this.
  * DAILY_BUDGET_USD    (default 10.0) — running total of today's calls
    plus the new call may not exceed this.

Override via environment variables. The day's running total is rebuilt
lazily on each check by scanning today's lines in the cost log; there is
no in-memory counter, so totals survive process restarts.
"""
from __future__ import annotations

import os

from generator import cost_log


class BudgetExceeded(Exception):
    """Raised when a call would exceed the per-call or daily ceiling."""


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def per_call_budget_usd() -> float:
    return _float_env("PER_CALL_BUDGET_USD", 0.50)


def daily_budget_usd() -> float:
    return _float_env("DAILY_BUDGET_USD", 10.0)


def today_total_usd() -> float:
    return sum(float(rec.get("cost_usd", 0.0)) for rec in cost_log.read_today())


def check_and_charge(
    estimated_cost_usd: float,
    *,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Validate against budgets, then record the charge to the cost log.

    Raises BudgetExceeded — without writing to the log — if the call
    alone exceeds PER_CALL_BUDGET_USD, or if it would push today's
    running total past DAILY_BUDGET_USD.
    """
    per_call = per_call_budget_usd()
    daily = daily_budget_usd()

    if estimated_cost_usd > per_call:
        raise BudgetExceeded(
            f"per-call budget exceeded: ${estimated_cost_usd:.4f} > ${per_call:.4f}"
        )

    today = today_total_usd()
    if today + estimated_cost_usd > daily:
        raise BudgetExceeded(
            f"daily budget exceeded: today=${today:.4f} + "
            f"${estimated_cost_usd:.4f} > ${daily:.4f}"
        )

    cost_log.append(
        {
            "timestamp": cost_log._now().isoformat(),
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": estimated_cost_usd,
        }
    )
