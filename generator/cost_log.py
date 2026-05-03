"""JSONL cost log for LLM API calls (ADR-012).

Stage 1 wrote one immutable line per call. Stage 2 (T-2.11, R7) extends
this so each record carries a stable `record_id` and supports two
mutation operations:

  * `update_record(...)` — overwrite estimate fields with the actual
    `usage_metadata` returned by the provider, marking the row reconciled.
  * `mark_refunded(...)` — zero a row's `cost_usd` and stamp a refund
    reason when an estimated charge needs to be released (e.g. the
    request never reached the provider).

Concurrency: a module-level `threading.Lock` serialises in-process
writers, and an `fcntl.flock(LOCK_EX)` on a sibling `.lock` sentinel
file extends that exclusion across processes. Both `append` and the
read-modify-write paths take both locks so updates never lose a
concurrent append (or vice versa). Atomic rewrites use `tempfile.mkstemp`
in the log's directory so two writers can't collide on the tmp filename.
POSIX-only (Stage 2 dev runners are macOS / Linux).

The default file lives at /generator/cost_log.jsonl (gitignored). Tests
override the path via the FORGEWRIGHT_COST_LOG environment variable.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "cost_log.jsonl"

# In-process exclusion. Cross-process exclusion is layered on top via
# `_file_lock` below; both locks are held together for every write.
_LOG_LOCK = threading.Lock()


@contextlib.contextmanager
def _file_lock(lock_path: Path):
    """fcntl.flock(LOCK_EX) on a sibling sentinel file."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _lock_path_for(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def _log_path() -> Path:
    override = os.environ.get("FORGEWRIGHT_COST_LOG")
    if override:
        return Path(override)
    return DEFAULT_LOG_PATH


def _now() -> datetime:
    # Wall-clock UTC. Exposed at module scope so tests can monkeypatch it
    # to simulate day-boundary crossings.
    return datetime.now(timezone.utc)


def _new_record_id() -> str:
    return uuid.uuid4().hex


def append(record: dict) -> str:
    """Append `record` as a single JSON line; returns a stable `record_id`.

    Injects a fresh `record_id` (uuid4 hex) into the record before writing
    so callers can later locate it via `update_record` / `mark_refunded`.
    """
    record_id = _new_record_id()
    record = dict(record)  # don't mutate caller's dict
    record["record_id"] = record_id

    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_LOCK, _file_lock(_lock_path_for(path)):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    return record_id


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


class RecordNotFound(KeyError):
    """Raised when update_record / mark_refunded can't locate the id."""


def update_record(
    record_id: str,
    *,
    actual_input_tokens: int,
    actual_output_tokens: int,
    actual_cost_usd: float,
) -> None:
    """Reconcile a record with provider-returned actual usage.

    Overwrites `input_tokens` / `output_tokens` / `cost_usd` and stamps
    `reconciled=true` + `reconciled_at`. Raises `RecordNotFound` if the
    id is missing (callers passing a fresh record_id from `append`
    should never see this).
    """
    def _mutate(rec: dict) -> None:
        rec["input_tokens"] = actual_input_tokens
        rec["output_tokens"] = actual_output_tokens
        rec["cost_usd"] = actual_cost_usd
        rec["reconciled"] = True
        rec["reconciled_at"] = _now().isoformat()

    _rewrite_one(record_id, _mutate)


def mark_refunded(record_id: str, *, reason: str) -> None:
    """Release an estimated charge by zeroing `cost_usd`.

    Stamps `status="refunded"` and `refund_reason=<reason>` for audit.
    Raises `RecordNotFound` if the id is missing.
    """
    def _mutate(rec: dict) -> None:
        rec["cost_usd"] = 0.0
        rec["status"] = "refunded"
        rec["refund_reason"] = reason
        rec["refunded_at"] = _now().isoformat()

    _rewrite_one(record_id, _mutate)


def _rewrite_one(record_id: str, mutate) -> None:
    """Read all lines, mutate the matching record, atomically rewrite.

    Holds both the in-process lock and the cross-process file lock so a
    concurrent `append` (or another rewrite) can't interleave between
    the read and the rename. The temp file uses `mkstemp` for a unique
    name, so two simultaneous rewrites never share a tmp path.
    """
    path = _log_path()
    with _LOG_LOCK, _file_lock(_lock_path_for(path)):
        if not path.exists():
            raise RecordNotFound(f"record_id={record_id} not found (log file missing)")

        raw_lines = path.read_text(encoding="utf-8").splitlines()
        out_lines: list[str] = []
        found = False
        for raw in raw_lines:
            if not raw.strip():
                continue
            rec = json.loads(raw)
            if not found and rec.get("record_id") == record_id:
                mutate(rec)
                found = True
            out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

        if not found:
            raise RecordNotFound(f"record_id={record_id} not found")

        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=path.name + ".",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(out_lines))
                if out_lines:
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            # Replace failed (or write threw); clean up the orphan tmp.
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_name)
            raise
