"""Sidecar version-metadata recorder for /content scenes (T-3.8a).

Per ROADMAP §阶段 3 完成标志 / STAGE_3_TASKS §1 + §2.4 (F7 修订)：each
scene that lands in /content must have a sibling `<scene>.version.json`
capturing its current version + git audit trail. T-3.10 验收期审计每个
入库 scene 必须有 version sidecar；缺失 = 阶段 3 不达标。

Sidecar location:
    /content/<scene_dir>/scene.json
    /content/<scene_dir>/scene.version.json   <-- this module writes/updates

Why a sidecar (not a field on dialogue_graph):
    ADR-016 freezes dialogue_graph.schema_version at "0.1.1"; version
    metadata is audit data (not truth-source per ADR-006), so it lives
    next to the scene rather than inside it. The sidecar shape is
    intentionally not declared in /schema/ — it is generator-internal
    book-keeping.

What this module does NOT do (F7 修订；CLAUDE.md 安全约束):
    * Run `git commit`, `git add`, or `git push` — author handles git
      commits themselves; we only *read* HEAD state for the audit trail.
    * Touch the dialogue_graph schema or the scene file itself.
    * Write to ontology, validator, or runtime modules.

CLI shape (T-3.8a VR-3 — author追溯手动编辑)::

    python -m generator.version_recorder <scene_path> \\
        [--method manual_edit|regenerate|batch_scheduler|playtest_fix] \\
        [--changed-fields field1,field2]

Public API:
    `record_version(scene_path, generation_method, changed_fields=None)`
    is imported by T-3.5 batch_scheduler in the
    `write scene → assign chapter → write deps → record version` chain
    (T-3.8b 范围；F12)。
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast, get_args

from generator._atomic_write import write_json_atomic

_LOG = logging.getLogger(__name__)

GenerationMethod = Literal[
    "batch_scheduler",
    "manual_edit",
    "regenerate",
    "playtest_fix",
    # T-3P-0（ADR-039 写作提示词包转向）：编剧 BYOM 正文回流经 P-B 合并落地时用；
    # 该值被后续所有回流落地依赖（T-3P-3 只消费不再改）
    "writer_ingest",
]

# Snapshot of `Literal` members for argparse choices + runtime validation.
_ALLOWED_METHODS: frozenset[str] = frozenset(get_args(GenerationMethod))

SIDECAR_SUFFIX = ".version.json"


@dataclass
class PreviousVersion:
    """One archived version snapshot in the lineage chain.

    `changed_fields` describes the fields modified when transitioning
    *out of* this version — i.e., the `changed_fields` argument the
    caller passed to `record_version` at the moment this version got
    superseded. Empty list = caller did not declare specific fields
    (typical for batch_scheduler / regenerate paths).
    """

    version: int
    commit: str | None
    modified_at: str
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class VersionMetadata:
    """Current version + lineage for a single scene sidecar."""

    scene_id: str
    version: int
    first_generated_at: str
    last_modified_at: str
    git_commit_at_generation: str | None
    git_branch_at_generation: str | None
    generation_method: GenerationMethod
    previous_versions: list[PreviousVersion] = field(default_factory=list)


def sidecar_path_for(scene_path: Path) -> Path:
    """Return the sibling sidecar path for a `<scene>.json` file.

    `Path("scene.json").with_suffix(".version.json")` → `scene.version.json`.
    Mirrors the dep_index naming (`<scene>.deps.json`; STAGE_3_TASKS §2.4).
    """
    return scene_path.with_suffix(SIDECAR_SUFFIX)


def _now_iso() -> str:
    """Wall-clock UTC ISO-8601. Module-level so tests can monkeypatch it."""
    return datetime.now(timezone.utc).isoformat()


# Whitelist of git invocations this module is allowed to make. Anchors
# the audit trail to the scene's repo (via `-C`) and provably excludes
# any mutation command (commit / add / push) — see CLAUDE.md safety
# rules + T-3.8a F7 修订. PR #37 review §4.1 narrowed the original
# generic `_run_git(*args)` wrapper down to this whitelist.
_ALLOWED_READ_ONLY_GIT_ARGS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("rev-parse", "HEAD"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
    }
)


def _run_git_readonly(repo_hint: Path, args: tuple[str, ...]) -> str | None:
    """Read-only `git -C <repo_hint> <args>` — never mutates the repo.

    `args` must be a member of `_ALLOWED_READ_ONLY_GIT_ARGS`; passing
    anything else raises `ValueError` at the call site rather than
    silently shelling out. The `-C` flag anchors the invocation to the
    scene's directory so a CLI run from a non-repo cwd still records
    the scene's repo HEAD (review §4.1).

    Falls through to `None` on:
      - `FileNotFoundError` (git binary missing from PATH)
      - `subprocess.CalledProcessError` (e.g. repo_hint is not inside a
        git repo, detached worktree with no HEAD, etc.)
      - empty stdout

    Never invokes `git commit` / `git add` / `git push` (CLAUDE.md
    safety + F7 修订: this module records audit metadata only).
    """
    if args not in _ALLOWED_READ_ONLY_GIT_ARGS:
        raise ValueError(
            f"_run_git_readonly only accepts whitelisted read-only "
            f"invocations; got {args!r}. Add to _ALLOWED_READ_ONLY_GIT_ARGS "
            f"if a new audit field is genuinely needed."
        )
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_hint), *args],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except FileNotFoundError:
        _LOG.warning(
            "git binary not found on PATH; recording None for git fields."
        )
        return None
    except subprocess.CalledProcessError as exc:
        _LOG.warning(
            "git -C %s %s exited %d; recording None for git fields. stderr=%s",
            repo_hint,
            " ".join(args),
            exc.returncode,
            (exc.stderr or "").strip(),
        )
        return None
    return out or None


def _git_head_commit(scene_path: Path) -> str | None:
    return _run_git_readonly(scene_path.parent, ("rev-parse", "HEAD"))


def _git_head_branch(scene_path: Path) -> str | None:
    return _run_git_readonly(
        scene_path.parent, ("rev-parse", "--abbrev-ref", "HEAD")
    )


def _read_scene_id(scene_path: Path) -> str:
    """Pull the scene's `graph_id` from scene.json — used as `scene_id`."""
    with scene_path.open("r", encoding="utf-8") as f:
        scene = json.load(f)
    scene_id = scene.get("graph_id")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError(
            f"scene file {scene_path} is missing a string `graph_id`; "
            f"cannot derive scene_id for version sidecar."
        )
    return scene_id


def _previous_version_from_dict(data: dict) -> PreviousVersion:
    return PreviousVersion(
        version=int(data["version"]),
        commit=data.get("commit"),
        modified_at=str(data["modified_at"]),
        changed_fields=list(data.get("changed_fields") or []),
    )


def _load_sidecar(sidecar: Path) -> VersionMetadata:
    with sidecar.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return VersionMetadata(
        scene_id=str(raw["scene_id"]),
        version=int(raw["version"]),
        first_generated_at=str(raw["first_generated_at"]),
        last_modified_at=str(raw["last_modified_at"]),
        git_commit_at_generation=raw.get("git_commit_at_generation"),
        git_branch_at_generation=raw.get("git_branch_at_generation"),
        generation_method=cast(GenerationMethod, raw["generation_method"]),
        previous_versions=[
            _previous_version_from_dict(p)
            for p in raw.get("previous_versions") or []
        ],
    )


def _save_sidecar(sidecar: Path, meta: VersionMetadata) -> None:
    """Atomically write the sidecar via the shared `_atomic_write` helper.

    Wraps `write_json_atomic` so the tempfile + fsync + replace recipe
    stays a single source of truth (review §4.3); a mid-write crash
    leaves the prior sidecar intact rather than half-written.
    """
    write_json_atomic(sidecar, asdict(meta))


# ---------------------------------------------------------------------------
# Concurrency control (review §4.2)
# ---------------------------------------------------------------------------
#
# `record_version` is read-modify-write on the sidecar: load → bump →
# write. Without serialisation, two concurrent calls on the same scene
# (batch_scheduler + manual CLI rerun, two threads in T-3.5's N=3 pool,
# etc.) can both read v_n and both write v_{n+1}, losing one bump and
# its `changed_fields` audit. We layer two locks:
#
#   * a per-process `threading.Lock` so threads in the same Python
#     process serialise — fcntl.flock is process-level so it does NOT
#     do this on its own
#   * a sibling `<sidecar>.lock` file under `fcntl.flock(LOCK_EX)` so a
#     manual CLI invocation overlapping the batch scheduler also
#     serialises
#
# Locks are held across the whole load → bump → write critical section
# so the version + previous_versions chain stays gap-free.

_RECORD_LOCK = threading.Lock()


def _sidecar_lock_path(sidecar: Path) -> Path:
    """`<sidecar>.lock` — sibling sentinel for the cross-process lock."""
    return sidecar.with_suffix(sidecar.suffix + ".lock")


@contextlib.contextmanager
def _sidecar_file_lock(sidecar: Path) -> Iterator[None]:
    """fcntl.flock(LOCK_EX) on a sibling `.lock` sentinel. POSIX-only."""
    lock_path = _sidecar_lock_path(sidecar)
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


def record_version(
    scene_path: Path,
    generation_method: str,
    changed_fields: list[str] | None = None,
) -> VersionMetadata:
    """Record a new version for `scene_path` — create or bump the sidecar.

    Parameters
    ----------
    scene_path:
        Path to the scene's `scene.json`. Must exist on the *first* call
        so we can read `graph_id` for `scene_id`. On subsequent bumps the
        sidecar already carries `scene_id`, so the scene file does not
        have to exist (useful for forensics).
    generation_method:
        Which path produced this version. Must be one of `GenerationMethod`
        literals; otherwise `ValueError` is raised.
    changed_fields:
        Optional list of field paths the caller modified in this bump.
        Captured on the `PreviousVersion` entry that archives the version
        being superseded — i.e., describes what changed *out of* the
        prior version. Ignored on first creation (no prior to record on).

    Returns
    -------
    The new `VersionMetadata` written to disk.

    Side effects
    ------------
    - Writes `<scene>.version.json` atomically (review §4.3 shared helper).
    - Holds a per-process `threading.Lock` + a sibling `<sidecar>.lock`
      `fcntl.flock` for the load → bump → write critical section so
      concurrent calls (T-3.5 N=3 pool, manual CLI overlap) don't lose
      a bump (review §4.2).
    - Reads `git rev-parse HEAD` + `--abbrev-ref HEAD` anchored to
      `scene_path.parent` via `git -C` (review §4.1); if git is
      unavailable the relevant fields are recorded as `None` and a
      warning is logged. Never invokes git commit / add / push.
    """
    if generation_method not in _ALLOWED_METHODS:
        raise ValueError(
            f"generation_method {generation_method!r} not allowed; "
            f"expected one of {sorted(_ALLOWED_METHODS)}."
        )

    sidecar = sidecar_path_for(scene_path)
    cf = list(changed_fields or [])
    method = cast(GenerationMethod, generation_method)

    with _RECORD_LOCK, _sidecar_file_lock(sidecar):
        # Sample git + clock under the lock so the audit trail reflects
        # the actual write moment, not whatever was true seconds ago
        # while we waited on a contending writer.
        now = _now_iso()
        git_commit = _git_head_commit(scene_path)
        git_branch = _git_head_branch(scene_path)

        if sidecar.exists():
            old = _load_sidecar(sidecar)
            archived = PreviousVersion(
                version=old.version,
                commit=old.git_commit_at_generation,
                modified_at=old.last_modified_at,
                changed_fields=cf,
            )
            meta = VersionMetadata(
                scene_id=old.scene_id,
                version=old.version + 1,
                first_generated_at=old.first_generated_at,
                last_modified_at=now,
                git_commit_at_generation=git_commit,
                git_branch_at_generation=git_branch,
                generation_method=method,
                previous_versions=[*old.previous_versions, archived],
            )
        else:
            if not scene_path.exists():
                raise FileNotFoundError(
                    f"scene file {scene_path} does not exist; cannot create "
                    f"version sidecar for a missing scene."
                )
            scene_id = _read_scene_id(scene_path)
            meta = VersionMetadata(
                scene_id=scene_id,
                version=1,
                first_generated_at=now,
                last_modified_at=now,
                git_commit_at_generation=git_commit,
                git_branch_at_generation=git_branch,
                generation_method=method,
                previous_versions=[],
            )

        _save_sidecar(sidecar, meta)
        return meta


# ---------------------------------------------------------------------------
# CLI entry point (VR-3)
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator.version_recorder",
        description=(
            "Record / bump the version sidecar for a scene. Default "
            "--method is `manual_edit` (CLI use case = author追溯手动编辑); "
            "pass --method to override."
        ),
    )
    parser.add_argument(
        "scene_path",
        type=Path,
        help="Path to the scene's scene.json (sidecar is its sibling).",
    )
    parser.add_argument(
        "--method",
        choices=sorted(_ALLOWED_METHODS),
        default="manual_edit",
        help="generation_method literal (default: manual_edit).",
    )
    parser.add_argument(
        "--changed-fields",
        default=None,
        help=(
            "Comma-separated field paths the author modified (e.g. "
            "`nodes.opt_x.text,character_refs`). Empty / missing = []."
        ),
    )
    return parser


def _parse_changed_fields(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    fields = [s.strip() for s in raw.split(",") if s.strip()]
    return fields or None


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    args = _build_arg_parser().parse_args(argv)
    scene_path: Path = args.scene_path
    if not scene_path.exists():
        print(
            f"error: scene_path does not exist: {scene_path}", file=sys.stderr
        )
        return 2
    cf = _parse_changed_fields(args.changed_fields)
    try:
        meta = record_version(scene_path, args.method, cf)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sidecar = sidecar_path_for(scene_path)
    print(
        f"version_recorder: scene={meta.scene_id} version={meta.version} "
        f"method={meta.generation_method} sidecar={sidecar}"
    )
    return 0


__all__ = [
    "GenerationMethod",
    "PreviousVersion",
    "SIDECAR_SUFFIX",
    "VersionMetadata",
    "main",
    "record_version",
    "sidecar_path_for",
]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
