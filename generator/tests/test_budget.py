"""T-1.5: budget guard + cost_log behavior.

Covers per-call ceiling, daily ceiling, normal pass-through writes,
day-boundary reset, missing-file read, and concurrent-write atomicity.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import pytest

from generator import budget, cost_log
from generator.budget import BudgetExceeded


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    """Every test gets its own log file. Real cost_log.jsonl is never touched."""
    log_file = tmp_path / "cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(log_file))
    # Clear inherited budget overrides so default-budget tests are deterministic.
    monkeypatch.delenv("DAILY_BUDGET_USD", raising=False)
    monkeypatch.delenv("PER_CALL_BUDGET_USD", raising=False)
    return log_file


def _freeze(monkeypatch, dt: datetime) -> None:
    monkeypatch.setattr(cost_log, "_now", lambda: dt)


# ----- read_today on a missing file -----

def test_read_today_returns_empty_when_file_missing(isolated_log):
    assert not isolated_log.exists()
    assert cost_log.read_today() == []


# ----- normal pass-through writes a row -----

def test_check_and_charge_writes_one_row_on_success(isolated_log):
    record_id = budget.check_and_charge(
        0.123, model_id="gemini-3.1-pro-preview", input_tokens=100, output_tokens=50
    )
    assert isinstance(record_id, str) and record_id  # T-2.11: stable record_id
    lines = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["model_id"] == "gemini-3.1-pro-preview"
    assert rec["input_tokens"] == 100
    assert rec["output_tokens"] == 50
    assert rec["cost_usd"] == 0.123
    assert rec["record_id"] == record_id
    # timestamp parses as ISO-8601
    datetime.fromisoformat(rec["timestamp"])


def test_today_total_reflects_appended_rows(isolated_log):
    budget.check_and_charge(0.10, model_id="m", input_tokens=1, output_tokens=1)
    budget.check_and_charge(0.20, model_id="m", input_tokens=1, output_tokens=1)
    assert budget.today_total_usd() == pytest.approx(0.30)


# ----- per-call ceiling -----

def test_per_call_exceeded_raises_and_does_not_write(isolated_log):
    with pytest.raises(BudgetExceeded, match="per-call"):
        budget.check_and_charge(
            0.51, model_id="m", input_tokens=1, output_tokens=1  # default cap is 0.50
        )
    assert not isolated_log.exists()


def test_per_call_at_exact_ceiling_passes(isolated_log):
    # Spec: raise iff estimated_cost > PER_CALL_BUDGET; equal is fine.
    budget.check_and_charge(0.50, model_id="m", input_tokens=1, output_tokens=1)
    assert isolated_log.exists()


def test_per_call_ceiling_overridable_via_env(isolated_log, monkeypatch):
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.10")
    with pytest.raises(BudgetExceeded, match="per-call"):
        budget.check_and_charge(0.11, model_id="m", input_tokens=1, output_tokens=1)


# ----- daily ceiling -----

def test_daily_exceeded_raises_after_accumulating(isolated_log, monkeypatch):
    monkeypatch.setenv("DAILY_BUDGET_USD", "1.00")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.50")
    budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    # 0.80 + 0.40 = 1.20 > 1.00 → raise, no third row written
    with pytest.raises(BudgetExceeded, match="daily"):
        budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    rows = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2


# ----- day boundary reset -----

def test_today_total_resets_across_day_boundary(isolated_log, monkeypatch):
    day1 = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 4, 25, 0, 30, 0, tzinfo=timezone.utc)

    _freeze(monkeypatch, day1)
    budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    assert budget.today_total_usd() == pytest.approx(0.40)

    _freeze(monkeypatch, day2)
    # Yesterday's row is still on disk but no longer counts toward today's total.
    assert budget.today_total_usd() == pytest.approx(0.0)
    # And a fresh charge under the daily cap goes through.
    budget.check_and_charge(0.10, model_id="m", input_tokens=1, output_tokens=1)
    assert budget.today_total_usd() == pytest.approx(0.10)


# ----- concurrent writes preserve JSONL framing -----

def test_concurrent_appends_yield_valid_jsonl(isolated_log):
    n_writers = 16
    per_writer = 5

    def worker(wid: int) -> None:
        for i in range(per_writer):
            cost_log.append(
                {
                    "timestamp": "2026-04-25T12:00:00+00:00",
                    "model_id": f"w{wid}",
                    "input_tokens": i,
                    "output_tokens": i,
                    "cost_usd": 0.001,
                }
            )

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(n_writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    raw = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(raw) == n_writers * per_writer
    # Every line must parse cleanly — no torn writes interleaved.
    seen_ids: set[str] = set()
    for line in raw:
        rec = json.loads(line)
        assert set(rec.keys()) == {
            "timestamp",
            "model_id",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "record_id",
        }
        seen_ids.add(rec["record_id"])
    # T-2.11: every append gets a unique record_id even under contention.
    assert len(seen_ids) == n_writers * per_writer


# ===========================================================================
# T-2.11 R7: cost reconcile (record_id + tri-state refund)
# ===========================================================================


def _read_one(log_path) -> dict:
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"expected one row, got {len(lines)}"
    return json.loads(lines[0])


# ----- check_and_charge returns a stable, unique record_id -----


def test_check_and_charge_returns_unique_record_ids(isolated_log):
    ids = [
        budget.check_and_charge(0.001, model_id="m", input_tokens=1, output_tokens=1)
        for _ in range(50)
    ]
    assert len(set(ids)) == 50  # uniqueness across many calls
    rows = [json.loads(line) for line in isolated_log.read_text("utf-8").splitlines()]
    assert [r["record_id"] for r in rows] == ids  # same order on disk


def test_check_and_charge_returns_no_record_when_budget_fails(isolated_log, monkeypatch):
    """pre_call_budget_fail: no record is ever written, no record_id to refund."""
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.10")
    with pytest.raises(BudgetExceeded):
        budget.check_and_charge(0.50, model_id="m", input_tokens=1, output_tokens=1)
    assert not isolated_log.exists()


# ----- reconcile_after_call: estimate -> actual rewrite -----


def test_reconcile_after_call_overwrites_with_actuals(isolated_log):
    record_id = budget.check_and_charge(
        0.40, model_id="m", input_tokens=1000, output_tokens=200
    )
    # Simulate the provider returning smaller-than-estimated usage.
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=850,
        actual_output_tokens=150,
        actual_cost_usd=0.0033,
    )
    rec = _read_one(isolated_log)
    assert rec["record_id"] == record_id
    assert rec["input_tokens"] == 850
    assert rec["output_tokens"] == 150
    assert rec["cost_usd"] == 0.0033  # estimate dropped
    assert rec["reconciled"] is True
    assert "reconciled_at" in rec


def test_reconcile_brings_today_total_in_line_with_actual(isolated_log):
    record_id = budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    assert budget.today_total_usd() == pytest.approx(0.40)

    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=10,
        actual_output_tokens=5,
        actual_cost_usd=0.05,
    )
    # Daily total now reflects the actual, not the estimate.
    assert budget.today_total_usd() == pytest.approx(0.05)


# ----- refund_estimated: tri-state, request_not_sent path -----


def test_refund_estimated_zeroes_cost_and_marks_status(isolated_log):
    record_id = budget.check_and_charge(0.40, model_id="m", input_tokens=1, output_tokens=1)
    assert budget.today_total_usd() == pytest.approx(0.40)

    budget.refund_estimated(record_id, reason="request_not_sent")
    rec = _read_one(isolated_log)
    assert rec["cost_usd"] == 0.0
    assert rec["status"] == "refunded"
    assert rec["refund_reason"] == "request_not_sent"
    assert "refunded_at" in rec
    # Refunded rows drop out of the running total.
    assert budget.today_total_usd() == pytest.approx(0.0)


def test_request_sent_failure_keeps_estimated_charge(isolated_log):
    """request_sent_failure (third refund state): row stays charged, no refund called.

    There's no API call in this path — it's the ABSENCE of a refund. The
    test asserts that without `refund_estimated`, the row keeps its
    pre-call estimate and `status` is never set to refunded.
    """
    budget.check_and_charge(0.30, model_id="m", input_tokens=1, output_tokens=1)
    rec = _read_one(isolated_log)
    assert rec["cost_usd"] == 0.30
    assert "status" not in rec  # never marked refunded
    assert budget.today_total_usd() == pytest.approx(0.30)


# ----- update_record / mark_refunded error paths -----


def test_update_record_raises_when_id_unknown(isolated_log):
    budget.check_and_charge(0.10, model_id="m", input_tokens=1, output_tokens=1)
    with pytest.raises(cost_log.RecordNotFound):
        budget.reconcile_after_call(
            "deadbeef",
            actual_input_tokens=1,
            actual_output_tokens=1,
            actual_cost_usd=0.001,
        )


def test_mark_refunded_raises_when_id_unknown(isolated_log):
    budget.check_and_charge(0.10, model_id="m", input_tokens=1, output_tokens=1)
    with pytest.raises(cost_log.RecordNotFound):
        budget.refund_estimated("deadbeef", reason="request_not_sent")


def test_update_record_raises_when_log_missing(isolated_log):
    """Calling reconcile against an empty log surfaces a clean error."""
    assert not isolated_log.exists()
    with pytest.raises(cost_log.RecordNotFound):
        cost_log.update_record(
            "anything",
            actual_input_tokens=1,
            actual_output_tokens=1,
            actual_cost_usd=0.01,
        )


# ----- update_record preserves sibling rows -----


def test_update_record_only_touches_the_matching_row(isolated_log):
    rid_a = budget.check_and_charge(0.10, model_id="ma", input_tokens=1, output_tokens=1)
    rid_b = budget.check_and_charge(0.20, model_id="mb", input_tokens=1, output_tokens=1)
    rid_c = budget.check_and_charge(0.30, model_id="mc", input_tokens=1, output_tokens=1)

    budget.reconcile_after_call(
        rid_b, actual_input_tokens=99, actual_output_tokens=99, actual_cost_usd=0.05
    )

    rows = {
        json.loads(line)["record_id"]: json.loads(line)
        for line in isolated_log.read_text("utf-8").splitlines()
    }
    assert rows[rid_a]["cost_usd"] == 0.10 and "reconciled" not in rows[rid_a]
    assert rows[rid_c]["cost_usd"] == 0.30 and "reconciled" not in rows[rid_c]
    assert rows[rid_b]["cost_usd"] == 0.05 and rows[rid_b]["reconciled"] is True
