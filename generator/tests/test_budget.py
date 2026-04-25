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
    budget.check_and_charge(
        0.123, model_id="gemini-3.1-pro-preview", input_tokens=100, output_tokens=50
    )
    lines = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["model_id"] == "gemini-3.1-pro-preview"
    assert rec["input_tokens"] == 100
    assert rec["output_tokens"] == 50
    assert rec["cost_usd"] == 0.123
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
    for line in raw:
        rec = json.loads(line)
        assert set(rec.keys()) == {
            "timestamp",
            "model_id",
            "input_tokens",
            "output_tokens",
            "cost_usd",
        }
