"""Append-only JSONL cost log for LLM API calls (ADR-012).

One line per call, fsynced on append so daily totals survive crashes.
The default file lives at /generator/cost_log.jsonl (gitignored). Tests
override the path via the FORGEWRIGHT_COST_LOG environment variable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "cost_log.jsonl"


def _log_path() -> Path:
    override = os.environ.get("FORGEWRIGHT_COST_LOG")
    if override:
        return Path(override)
    return DEFAULT_LOG_PATH


def _now() -> datetime:
    # Wall-clock UTC. Exposed at module scope so tests can monkeypatch it
    # to simulate day-boundary crossings.
    return datetime.now(timezone.utc)


def append(record: dict) -> None:
    """Append `record` as a single JSON line; flush + fsync for durability."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def read_today() -> list[dict]:
    """Return records whose `timestamp` falls on the current UTC date.

    Returns [] when the log file does not yet exist.
    """
    path = _log_path()
    if not path.exists():
        return []
    today = _now().astimezone(timezone.utc).date()
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            ts = rec.get("timestamp")
            if not ts:
                continue
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt.astimezone(timezone.utc).date() == today:
                out.append(rec)
    return out
