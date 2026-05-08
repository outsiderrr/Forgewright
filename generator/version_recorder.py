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
import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast, get_args

_LOG = logging.getLogger(__name__)

GenerationMethod = Literal[
    "batch_scheduler",
    "manual_edit",
    "regenerate",
    "playtest_fix",
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


def _run_git(*args: str) -> str | None:
    """Return stripped stdout for `git <args>` or None if git is unavailable.

    Falls through quietly on:
      - FileNotFoundError (git binary missing from PATH)
      - CalledProcessError (e.g. cwd is not inside a repo, detached
        worktrees with no HEAD, etc.)
      - Empty stdout
    """
    try:
        out = subprocess.run(
            ["git", *args],
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
            "git %s exited %d; recording None for git fields. stderr=%s",
            " ".join(args),
            exc.returncode,
            (exc.stderr or "").strip(),
        )
        return None
    return out or None


def _git_head_commit() -> str | None:
    return _run_git("rev-parse", "HEAD")


def _git_head_branch() -> str | None:
    return _run_git("rev-parse", "--abbrev-ref", "HEAD")


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
    """Atomic write: tempfile + fsync + os.replace + parent fsync.

    Mirrors `generator.manifest` so a mid-write crash leaves the prior
    sidecar intact rather than half-written.
    """
    payload = asdict(meta)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    sidecar.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=sidecar.name + ".", suffix=".tmp", dir=str(sidecar.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, sidecar)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    try:
        dir_fd = os.open(str(sidecar.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


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
    - Writes `<scene>.version.json` atomically (tempfile + fsync + replace).
    - Reads `git rev-parse HEAD` + `--abbrev-ref HEAD` via subprocess; if
      git is unavailable the relevant fields are recorded as `None` and
      a warning is logged. Never invokes git commit / add / push.
    """
    if generation_method not in _ALLOWED_METHODS:
        raise ValueError(
            f"generation_method {generation_method!r} not allowed; "
            f"expected one of {sorted(_ALLOWED_METHODS)}."
        )

    sidecar = sidecar_path_for(scene_path)
    now = _now_iso()
    git_commit = _git_head_commit()
    git_branch = _git_head_branch()
    cf = list(changed_fields or [])
    method = cast(GenerationMethod, generation_method)

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
