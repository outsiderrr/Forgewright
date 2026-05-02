"""Tests for generator.import_log (T-1.5.7).

Covers append → readback, batch filter, missing-file behavior, and the
FORGEWRIGHT_IMPORT_LOG env override (used by tests + T-1.5.8 fixtures
for tmp_path isolation).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator import import_log


@pytest.fixture
def isolated_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    log_path = tmp_path / "import_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMPORT_LOG", str(log_path))
    return log_path


def test_read_all_missing_returns_empty(isolated_log: Path) -> None:
    assert not isolated_log.exists()
    assert import_log.read_all() == []


def test_append_creates_file_and_writes_jsonl(isolated_log: Path) -> None:
    record = {"timestamp": "2026-05-01T00:00:00Z", "asset_id_stub": "img_a"}
    import_log.append(record)
    assert isolated_log.exists()
    text = isolated_log.read_text(encoding="utf-8")
    # Single line + trailing newline
    assert text.endswith("\n")
    assert text.count("\n") == 1
    parsed = json.loads(text.strip())
    assert parsed == record


def test_read_all_returns_appended_in_order(isolated_log: Path) -> None:
    rows = [
        {"asset_id_stub": "img_a", "batch_name": None},
        {"asset_id_stub": "img_b", "batch_name": "vellin_run1"},
        {"asset_id_stub": "img_c", "batch_name": "vellin_run1"},
    ]
    for r in rows:
        import_log.append(r)
    assert import_log.read_all() == rows


def test_read_all_filter_by_batch(isolated_log: Path) -> None:
    rows = [
        {"asset_id_stub": "img_a", "batch_name": None},
        {"asset_id_stub": "img_b", "batch_name": "vellin_run1"},
        {"asset_id_stub": "img_c", "batch_name": "vellin_run1"},
        {"asset_id_stub": "img_d", "batch_name": "corvan_run1"},
    ]
    for r in rows:
        import_log.append(r)
    out = import_log.read_all(batch_name="vellin_run1")
    assert [r["asset_id_stub"] for r in out] == ["img_b", "img_c"]


def test_append_skips_blank_lines_on_read(isolated_log: Path) -> None:
    """Defensive: a blank line should not crash read_all (e.g. someone
    edited the file). This is a thin sanity-check, not a recovery
    guarantee."""
    isolated_log.write_text(
        '{"asset_id_stub":"img_a"}\n\n{"asset_id_stub":"img_b"}\n',
        encoding="utf-8",
    )
    out = import_log.read_all()
    assert [r["asset_id_stub"] for r in out] == ["img_a", "img_b"]
