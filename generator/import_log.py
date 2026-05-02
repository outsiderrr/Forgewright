"""Append-only JSONL log for image_import CLI runs (T-1.5.7).

One row per CLI decision (`imported` / `rejected` / `dry_run`). T-1.5.8
visual_metrics and T-1.5.10 acceptance recompute mechanical-pass-rate /
per-batch tallies from this file rather than scanning _pending /
_rejected directories or relying on memory.

Mirrors `generator.image_cost_log`: one line per call, `os.fsync`'d on
append. Default path `/generator/import_log.jsonl`; tests / cron runs can
override via the `FORGEWRIGHT_IMPORT_LOG` env var.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "import_log.jsonl"


def _log_path() -> Path:
    override = os.environ.get("FORGEWRIGHT_IMPORT_LOG")
    if override:
        return Path(override)
    return DEFAULT_LOG_PATH


def append(record: dict) -> None:
    """Append `record` as a single JSON line; flush + fsync for durability."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def read_all(batch_name: str | None = None) -> list[dict]:
    """Return all rows; if `batch_name` given, filter by `batch_name` field.

    Returns [] if the log file does not yet exist.
    """
    path = _log_path()
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            if batch_name is not None and rec.get("batch_name") != batch_name:
                continue
            out.append(rec)
    return out


__all__ = ["DEFAULT_LOG_PATH", "append", "read_all"]
