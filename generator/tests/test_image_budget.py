"""T-1.5.5: image_budget check + log_charge behavior.

Covers per-call ceiling, daily ceiling, manual-mode pass-through (cost=0),
api-mode normal pass, and the day-boundary reset. The split between
`check()` and `log_charge()` is tested explicitly: `check()` never writes
to the log, and `log_charge()` writes regardless of cost.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from generator import image_budget, image_cost_log
from generator.image_budget import ImageBudgetExceeded


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    log_file = tmp_path / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(log_file))
    monkeypatch.delenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", raising=False)
    monkeypatch.delenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", raising=False)
    return log_file


def _freeze(monkeypatch, dt: datetime) -> None:
    monkeypatch.setattr(image_cost_log, "_now", lambda: dt)


def _log_api(monkeypatch, dt: datetime, cost_usd: float, stub: str = "char_x_v1") -> None:
    _freeze(monkeypatch, dt)
    image_budget.log_charge(
        timestamp=dt,
        mode="api",
        provider_id="openai_image_gpt-image-1",
        asset_kind="character_sheet",
        asset_id_stub=stub,
        n=1,
        size=(1024, 1536),
        cost_usd=cost_usd,
        input_tokens=200,
    )


# ----- defaults match ADR-014 numbers -----

def test_default_per_call_budget_is_one_dollar():
    assert image_budget.per_call_image_budget_usd() == pytest.approx(1.00)


def test_default_daily_budget_is_five_dollars():
    assert image_budget.daily_image_budget_usd() == pytest.approx(5.00)


# ----- check() does not write to the log -----

def test_check_does_not_write_log(isolated_log):
    image_budget.check(estimated_cost_usd=0.05, mode="api")
    assert not isolated_log.exists()


# ----- per-call ceiling -----

def test_per_call_exceeded_raises(isolated_log):
    with pytest.raises(ImageBudgetExceeded, match="per-call"):
        image_budget.check(estimated_cost_usd=1.01, mode="api")
    assert not isolated_log.exists()


def test_per_call_at_exact_ceiling_passes(isolated_log):
    # Spec: raise iff estimated_cost > PER_CALL; equal is fine.
    image_budget.check(estimated_cost_usd=1.00, mode="api")


def test_per_call_overridable_via_env(isolated_log, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "0.10")
    with pytest.raises(ImageBudgetExceeded, match="per-call"):
        image_budget.check(estimated_cost_usd=0.11, mode="api")


# ----- daily ceiling -----

def test_daily_exceeded_raises_after_accumulating(isolated_log, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.30")
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "0.50")
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _log_api(monkeypatch, today, 0.10, stub="a")
    _log_api(monkeypatch, today, 0.10, stub="b")
    # 0.20 + 0.15 = 0.35 > 0.30 → raise
    with pytest.raises(ImageBudgetExceeded, match="daily"):
        image_budget.check(estimated_cost_usd=0.15, mode="api")


def test_daily_at_exact_ceiling_passes(isolated_log, monkeypatch):
    # 0.10 + 0.10 == 0.20 exactly in IEEE-754 (avoid the 0.1+0.2≠0.3 trap).
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.20")
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _log_api(monkeypatch, today, 0.10, stub="a")
    image_budget.check(estimated_cost_usd=0.10, mode="api")  # 0.10 + 0.10 = 0.20, not > 0.20


# ----- manual mode bypasses both ceilings -----

def test_manual_mode_check_always_passes(isolated_log, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "0.01")
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.01")
    image_budget.check(estimated_cost_usd=0.0, mode="manual")


def test_manual_mode_log_charge_writes_zero_cost_row(isolated_log):
    timestamp = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    image_budget.log_charge(
        timestamp=timestamp,
        mode="manual",
        provider_id="manual_import",
        asset_kind="character_sheet",
        asset_id_stub="char_vellin_v1",
        n=1,
        size=(1024, 1536),
        cost_usd=0.0,
        input_tokens=None,
    )
    line = isolated_log.read_text(encoding="utf-8").splitlines()[0]
    rec = json.loads(line)
    assert rec["mode"] == "manual"
    assert rec["cost_usd"] == 0.0
    assert rec["input_tokens"] is None
    assert rec["asset_id_stub"] == "char_vellin_v1"
    assert rec["n"] == 1
    assert rec["size_w"] == 1024
    assert rec["size_h"] == 1536


def test_manual_rows_count_toward_zero_total(isolated_log, monkeypatch):
    """Manual rows have cost_usd=0 → today_total stays 0 even after many."""
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, today)
    for i in range(5):
        image_budget.log_charge(
            timestamp=today,
            mode="manual",
            provider_id="manual_import",
            asset_kind="character_sheet",
            asset_id_stub=f"char_{i}",
            n=1,
            size=(1024, 1536),
            cost_usd=0.0,
            input_tokens=None,
        )
    assert image_budget.today_total_usd() == pytest.approx(0.0)
    # And budget check still passes for an api call.
    image_budget.check(estimated_cost_usd=0.05, mode="api")


# ----- api mode happy path -----

def test_api_mode_log_charge_writes_full_row(isolated_log):
    timestamp = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    image_budget.log_charge(
        timestamp=timestamp,
        mode="api",
        provider_id="openai_image_gpt-image-1",
        asset_kind="scene_background",
        asset_id_stub="bg_waystation_dawn_v1",
        n=1,
        size=(1536, 1024),
        cost_usd=0.05,
        input_tokens=180,
    )
    line = isolated_log.read_text(encoding="utf-8").splitlines()[0]
    rec = json.loads(line)
    assert rec == {
        "timestamp": "2026-05-01T12:00:00+00:00",
        "mode": "api",
        "provider_id": "openai_image_gpt-image-1",
        "asset_kind": "scene_background",
        "asset_id_stub": "bg_waystation_dawn_v1",
        "batch_name": None,
        "n": 1,
        "size_w": 1536,
        "size_h": 1024,
        "input_tokens": 180,
        "cost_usd": 0.05,
    }


def test_log_charge_persists_batch_name_for_metrics(isolated_log):
    """T-1.5.8 visual_metrics groups image_cost_log rows by batch_name;
    the field must round-trip through log_charge() to disk.
    """
    timestamp = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    image_budget.log_charge(
        timestamp=timestamp,
        mode="api",
        provider_id="openai_image_gpt-image-1",
        asset_kind="character_sheet",
        asset_id_stub="char_vellin_v1",
        n=1,
        size=(1024, 1536),
        cost_usd=0.04,
        input_tokens=200,
        batch_name="vellin_probe",
    )
    rec = json.loads(isolated_log.read_text(encoding="utf-8").splitlines()[0])
    assert rec["batch_name"] == "vellin_probe"


def test_api_mode_normal_call_passes_check_and_logs(isolated_log, monkeypatch):
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, today)
    image_budget.check(estimated_cost_usd=0.05, mode="api")
    image_budget.log_charge(
        timestamp=today,
        mode="api",
        provider_id="openai_image_gpt-image-1",
        asset_kind="character_sheet",
        asset_id_stub="char_aelwin_v1",
        n=1,
        size=(1024, 1536),
        cost_usd=0.05,
        input_tokens=180,
    )
    assert image_budget.today_total_usd() == pytest.approx(0.05)


# ----- day boundary reset -----

def test_today_total_resets_across_day_boundary(isolated_log, monkeypatch):
    day1 = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 5, 1, 0, 30, 0, tzinfo=timezone.utc)

    _log_api(monkeypatch, day1, 0.40, stub="x")
    assert image_budget.today_total_usd() == pytest.approx(0.40)

    _freeze(monkeypatch, day2)
    assert image_budget.today_total_usd() == pytest.approx(0.0)
    image_budget.check(estimated_cost_usd=0.10, mode="api")  # passes — fresh day
    image_budget.log_charge(
        timestamp=day2,
        mode="api",
        provider_id="openai_image_gpt-image-1",
        asset_kind="character_sheet",
        asset_id_stub="char_y_v1",
        n=1,
        size=(1024, 1536),
        cost_usd=0.10,
        input_tokens=200,
    )
    assert image_budget.today_total_usd() == pytest.approx(0.10)
