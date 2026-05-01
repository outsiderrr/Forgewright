"""T-1.5.5: image_cost_log JSONL behavior.

Covers append + fsync, read_today on a missing file, multi-line JSONL
parsing, and the day-boundary filter. Each test gets its own log path
via FORGEWRIGHT_IMAGE_COST_LOG so the real
/generator/image_cost_log.jsonl is never touched.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import pytest

from generator import image_cost_log


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    log_file = tmp_path / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(log_file))
    return log_file


def _freeze(monkeypatch, dt: datetime) -> None:
    monkeypatch.setattr(image_cost_log, "_now", lambda: dt)


def _record(timestamp: str, **overrides: object) -> dict:
    base = {
        "timestamp": timestamp,
        "mode": "api",
        "provider_id": "openai_image_gpt-image-1",
        "asset_kind": "character_sheet",
        "asset_id_stub": "char_vellin_v1",
        "n": 1,
        "size_w": 1024,
        "size_h": 1536,
        "input_tokens": 200,
        "cost_usd": 0.04,
    }
    base.update(overrides)
    return base


def test_read_today_returns_empty_when_file_missing(isolated_log):
    assert not isolated_log.exists()
    assert image_cost_log.read_today() == []


def test_append_writes_one_line_per_call(isolated_log):
    image_cost_log.append(_record("2026-05-01T12:00:00+00:00"))
    image_cost_log.append(_record("2026-05-01T12:01:00+00:00", asset_id_stub="char_corvan_v1"))
    lines = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec0 = json.loads(lines[0])
    rec1 = json.loads(lines[1])
    assert rec0["asset_id_stub"] == "char_vellin_v1"
    assert rec1["asset_id_stub"] == "char_corvan_v1"


def test_read_today_parses_multiple_jsonl_lines(isolated_log, monkeypatch):
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, today)
    image_cost_log.append(_record("2026-05-01T08:00:00+00:00"))
    image_cost_log.append(_record("2026-05-01T16:00:00+00:00", cost_usd=0.17))
    rows = image_cost_log.read_today()
    assert len(rows) == 2
    assert {r["cost_usd"] for r in rows} == {0.04, 0.17}


def test_read_today_filters_other_days(isolated_log, monkeypatch):
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, today)
    image_cost_log.append(_record("2026-04-30T23:59:00+00:00", cost_usd=0.50))
    image_cost_log.append(_record("2026-05-01T00:30:00+00:00", cost_usd=0.10))
    image_cost_log.append(_record("2026-05-02T00:01:00+00:00", cost_usd=0.99))
    rows = image_cost_log.read_today()
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 0.10


def test_read_today_skips_blank_lines(isolated_log, monkeypatch):
    today = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, today)
    image_cost_log.append(_record("2026-05-01T12:00:00+00:00"))
    with open(isolated_log, "a", encoding="utf-8") as f:
        f.write("\n\n")
    image_cost_log.append(_record("2026-05-01T12:30:00+00:00"))
    rows = image_cost_log.read_today()
    assert len(rows) == 2


def test_manual_row_is_written_with_zero_cost(isolated_log):
    rec = _record(
        "2026-05-01T12:00:00+00:00",
        mode="manual",
        provider_id="manual_import",
        cost_usd=0.0,
        input_tokens=None,
    )
    image_cost_log.append(rec)
    line = isolated_log.read_text(encoding="utf-8").splitlines()[0]
    parsed = json.loads(line)
    assert parsed["mode"] == "manual"
    assert parsed["cost_usd"] == 0.0
    assert parsed["input_tokens"] is None


def test_concurrent_appends_yield_valid_jsonl(isolated_log):
    """Mirrors test_budget.test_concurrent_appends_yield_valid_jsonl;
    locks down the same write-atomicity guarantee for the image log so
    parallel batch experiments cannot tear lines.
    """
    n_writers = 16
    per_writer = 5

    def worker(wid: int) -> None:
        for i in range(per_writer):
            image_cost_log.append(
                _record(
                    "2026-05-01T12:00:00+00:00",
                    asset_id_stub=f"w{wid}_{i}",
                )
            )

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(n_writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    raw = isolated_log.read_text(encoding="utf-8").splitlines()
    assert len(raw) == n_writers * per_writer
    for line in raw:
        rec = json.loads(line)
        assert rec["asset_id_stub"].startswith("w")
