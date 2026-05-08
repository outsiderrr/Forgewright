"""Crash-safe atomic file writes for /generator/ sidecar producers.

Extracted in T-3.8a C 阶段 per PR #37 review F4.3 — `version_recorder`,
`manifest`, future `dep_index_writer` and `chapter_assembler` all need
the same tempfile + fsync + os.replace + parent-dir fsync sequence.
This module is the single source of truth for that recipe; new sidecar
writers should import from here rather than copy-pasting.

POSIX-only (Stage 2/3 dev runners are macOS / Linux). Parent-dir fsync
is best-effort: platforms that can't open a directory fall through
without erroring.

The helpers are intentionally minimal — no schema validation, no JSON
canonicalisation knobs beyond a fixed `indent`. Callers serialise their
own payload structure; this module just lands the bytes safely.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _fsync_parent(directory: Path) -> None:
    """Best-effort fsync on a directory so the rename itself is durable.

    Some platforms (notably Windows) can't open a directory; on those we
    skip silently rather than failing the write — the file content is
    already durable thanks to the file-level fsync, only the rename
    durability is at stake.
    """
    try:
        dir_fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def write_text_atomic(path: Path, text: str) -> None:
    """Atomically write `text` to `path` via tempfile + fsync + os.replace.

    Crash semantics:
      - mid-write crash leaves the prior `path` intact (rename is the
        atomic moment; before it, only the sibling tempfile is dirty)
      - on the failure path the tempfile is best-effort cleaned up so
        repeated crashes don't accumulate `<name>.<rand>.tmp` siblings
      - parent dir is fsynced after the rename so the new dirent is
        durable across power loss
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _fsync_parent(path.parent)


def write_json_atomic(
    path: Path, payload: Any, *, indent: int = 2
) -> None:
    """Atomically write `payload` as UTF-8 JSON with a trailing newline.

    Convention shared with `generator.manifest` / cost_log / ontology
    files: `ensure_ascii=False`, `indent=2`, single trailing `\\n`.
    """
    text = json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"
    write_text_atomic(path, text)


__all__ = ["write_json_atomic", "write_text_atomic"]
