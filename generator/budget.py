"""Cost guard for LLM API calls (ADR-012, T-2.11 R7 reconcile).

Two ceilings, both in USD:
  * PER_CALL_BUDGET_USD (default 0.50) — a single call may not exceed this.
  * DAILY_BUDGET_USD    (default 10.0) — running total of today's calls
    plus the new call may not exceed this.

Override via environment variables. The day's running total is rebuilt
lazily on each check by scanning today's lines in the cost log; there is
no in-memory counter, so totals survive process restarts. After a call
returns, callers reconcile the estimated row with the provider's actual
`usage_metadata` via `reconcile_after_call`, or release the estimated
charge via `refund_estimated` when the request never reached the
provider. Either way the running total self-corrects on the next read.
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
) -> str:
    """Validate against budgets, then write a pre-call charge to the log.

    Returns the new row's `record_id`, which callers must keep so they
    can later call `reconcile_after_call(record_id, ...)` (success path)
    or `refund_estimated(record_id, ...)` (request never sent).

    Raises `BudgetExceeded` — without writing to the log — if the call
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

    return cost_log.append(
        {
            "timestamp": cost_log._now().isoformat(),
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": estimated_cost_usd,
        }
    )


def reconcile_after_call(
    record_id: str,
    *,
    actual_input_tokens: int,
    actual_output_tokens: int,
    actual_cost_usd: float,
) -> None:
    """Overwrite a row's estimate with the provider's actual usage.

    Thin wrapper over `cost_log.update_record` so callers don't have to
    know which log module owns the bookkeeping.
    """
    cost_log.update_record(
        record_id,
        actual_input_tokens=actual_input_tokens,
        actual_output_tokens=actual_output_tokens,
        actual_cost_usd=actual_cost_usd,
    )


def refund_estimated(record_id: str, *, reason: str) -> None:
    """Release the estimated charge for a row that never billed.

    Used when a request never made it to the provider (connect failure,
    pre-flight rejection). Sets the row's `cost_usd` to 0; the daily
    total drops on the next read since `today_total_usd` re-reads.
    """
    cost_log.mark_refunded(record_id, reason=reason)
