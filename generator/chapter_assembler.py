"""Chapter/Act container assignment helper for generated scenes (T-3.9; F6 fix).

Per ROADMAP §阶段 3 重点工作 + STAGE_3_TASKS §6 Wave 3 + F6 修订:
batches scenes into the ontology's `chapters[].acts[].included_scenes`
tree. **F6 修订核心**: this task ships only the helper library; the
batch-scheduler hook lives in T-3.5's scope (the v0.1 plan had us
hooking `batch_scheduler.py` here, which would have caused dep_index
sidecars to be written with stale chapter_id values when the scheduler
imported chapter_assembler before the assignment finished). The agreed
write order is::

    write scene  →  assign chapter (this module)  →  write deps  →  record version

T-3.5 imports `assign_scene_to_chapter` and calls it after `scene.json`
lands but before the `<scene>.deps.json` sidecar is produced; that way
the dep_index can record the just-assigned `chapter_id`/`act_id` rather
than `None`/stale values.

What this module does NOT do (CA-5 + ADR-006 + F6 修订):
    * Modify the scene's `scene.json` — chapter membership is metadata
      *about* the scene's place in the world structure, not part of the
      scene's truth-source content (ADR-006).
    * Touch the chapter / act / dialogue_graph / scene `schema_version`
      consts. ADR-016 §schema 版本号策略 freezes those.
    * Hook `batch_scheduler.py` / `generate_scene.py` — those edits
      belong to T-3.5's scope (F6 拆分; CLAUDE.md 规则 2).
    * Auto-infer chapter / act from scene content. The task spec leaves
      a heuristic seam open but the default is the explicit fallback
      bucket — author or T-3.5 caller passes ids deliberately, and the
      author manually reassigns via the CLI in §审阅工坊.

CLI shape (CA-4 — author 审阅工坊期手动调整某场景归属)::

    python -m generator.chapter_assembler <scene_anchor> \\
        [--chapter <chapter_id>] [--act <act_id>] \\
        [--ontology <ontology.json>]

Public API:
    `assign_scene_to_chapter(scene_anchor, ontology_path, chapter_id=,
    act_id=, *, lock_factory=)` is imported by T-3.5 batch_scheduler in
    the `write scene → assign chapter → write deps → record version`
    chain (F6 修订). The `lock_factory` keyword keeps the lock
    injection seam open (CA-2 注脚): T-3.5 may pass a shared ontology
    lock so its dep_index_writer + chapter_assembler + version_recorder
    lineage doesn't fight on the same file.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import logging
import os
import re
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from generator._atomic_write import write_json_atomic

_LOG = logging.getLogger(__name__)

# Sentinel chapter / act ids for scenes the caller has not yet placed.
# Matching the chapter / act schema patterns (`^chap_...$` / `^act_...$`)
# so the auto-created unassigned containers themselves pass schema
# validation if the ontology is later schema-checked.
UNASSIGNED_CHAPTER_ID = "chap_unassigned"
UNASSIGNED_ACT_ID = "act_unassigned"
_UNASSIGNED_CHAPTER_DISPLAY_NAME = "Unassigned"
_UNASSIGNED_ACT_DISPLAY_NAME = "Unassigned"

_CHAPTER_ID_PATTERN = re.compile(r"^chap_[a-z0-9_]{1,64}$")
_ACT_ID_PATTERN = re.compile(r"^act_[a-z0-9_]{1,64}$")

DEFAULT_ONTOLOGY_PATH = Path("state/ontology/waystation.json")

# Match the existing waystation.json on-disk format (4-space indent +
# trailing newline) so this helper's writes don't reflow the entire
# file on first contact — keeps diffs reviewable.
_ONTOLOGY_INDENT = 4

LockFactory = Callable[[Path], AbstractContextManager[None]]
"""Lock factory injection seam for T-3.5 (F6 修订).

A callable that takes the ontology path and returns a context manager
guarding the read-modify-write critical section. Default factory does
per-process `threading.Lock` + sibling `fcntl.flock`; T-3.5 can swap in
a shared ontology lock so its dep_index_writer + chapter_assembler +
version_recorder lineage serialises against the same sentinel.
"""

ChapterAssignmentReason = Literal[
    "assigned",
    "fallback_unassigned",
    "idempotent_skip",
    "chapter_not_found",
    "act_not_found",
]


@dataclass(frozen=True)
class ChapterAssignment:
    """Outcome of `assign_scene_to_chapter`.

    `success=False` iff the caller named an explicit chapter / act id
    that was not present in the ontology — the helper does not invent
    user-named containers. `reason` distinguishes the success
    sub-states (idempotent skip vs. fallback bucket vs. clean assign)
    so T-3.5 callers can log / surface them separately without
    string-sniffing the message.
    """

    success: bool
    scene_anchor: str
    chapter_id: str
    act_id: str
    reason: ChapterAssignmentReason


# ---------------------------------------------------------------------------
# Default ontology lock (CA-2; F6 注脚 inject-lock 形态)
# ---------------------------------------------------------------------------
#
# Mirrors `version_recorder._sidecar_file_lock`: a per-process
# `threading.Lock` so threads inside one Python process serialise
# (fcntl.flock is process-level so it does NOT do this on its own) plus
# `fcntl.flock(LOCK_EX)` on a sibling `<ontology>.lock` sentinel so an
# overlapping CLI invocation can't race the batch scheduler. This
# default exists so the helper is self-contained when called outside
# T-3.5 (notably: the CA-4 manual reassign CLI). T-3.5 will inject its
# own factory once it lands.

_DEFAULT_PROCESS_LOCK = threading.Lock()


def _ontology_lock_path(ontology_path: Path) -> Path:
    return ontology_path.with_suffix(ontology_path.suffix + ".lock")


@contextlib.contextmanager
def _default_ontology_lock(ontology_path: Path) -> Iterator[None]:
    lock_path = _ontology_lock_path(ontology_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        with _DEFAULT_PROCESS_LOCK:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Core API (CA-1 + CA-2 + CA-3)
# ---------------------------------------------------------------------------


def assign_scene_to_chapter(
    scene_anchor: str,
    ontology_path: Path,
    chapter_id: str | None = None,
    act_id: str | None = None,
    *,
    lock_factory: LockFactory | None = None,
) -> ChapterAssignment:
    """Assign `scene_anchor` to `chapters[chapter_id].acts[act_id].included_scenes`.

    Behaviour
    ---------
    * **Both ids None** → fall back to (`UNASSIGNED_CHAPTER_ID`,
      `UNASSIGNED_ACT_ID`) and auto-create the bucket if absent.
    * **Only `chapter_id` given** (`act_id` None) → place under the
      author's named chapter but in its `act_unassigned` bucket;
      auto-create that bucket if absent.
    * **Both given** → both must exist in the ontology; missing →
      `ChapterAssignment(success=False, reason='chapter_not_found' /
      'act_not_found')` with no write. The helper does not invent user-
      named containers; chapter / act metadata (display_name, ordering)
      is L3 author-curated work outside this module's scope.
    * **`act_id` without `chapter_id`** → `ValueError` (act_id is only
      meaningful inside a chapter).
    * **`scene_anchor` already in target slot AND nowhere else** →
      `reason='idempotent_skip'`, no write (load-only fast path).
    * **`scene_anchor` in a different (chapter, act) slot** → removed
      from the old slot and appended to the new (the CA-4 CLI use case
      "审阅工坊期手动调整某场景归属"). `reason` reflects the new slot
      ('assigned' / 'fallback_unassigned'); the cleanup is logged at
      INFO. If the scene happened to be in target *and* elsewhere
      simultaneously (data corruption), the helper heals to a single
      reference at the target slot.

    Concurrency
    -----------
    * Default `lock_factory` holds a per-process `threading.Lock` plus
      `fcntl.flock` on `<ontology>.lock` for the whole load → modify →
      write critical section so concurrent invocations
      (T-3.5 N=3 worker pool, manual CLI overlap) don't lose an append
      or duplicate one.
    * T-3.5 may pass its own factory once its scheduler-level ontology
      lock lands (F6 修订; STAGE_3_TASKS §6 Wave 4 T-3.5 prompt).

    What is *not* changed
    ---------------------
    * `scene.json` content (CA-5 + ADR-006).
    * Chapter / Act / dialogue_graph / scene `schema_version` consts
      (ADR-016 §schema 版本号策略).
    """
    if not scene_anchor:
        raise ValueError("scene_anchor must be a non-empty string")
    if chapter_id is None and act_id is not None:
        raise ValueError(
            "act_id cannot be specified without chapter_id; "
            "either pass both or neither"
        )
    if chapter_id is not None and not _CHAPTER_ID_PATTERN.fullmatch(chapter_id):
        raise ValueError(
            f"chapter_id {chapter_id!r} does not match "
            f"chapter.schema.json pattern {_CHAPTER_ID_PATTERN.pattern}"
        )
    if act_id is not None and not _ACT_ID_PATTERN.fullmatch(act_id):
        raise ValueError(
            f"act_id {act_id!r} does not match "
            f"chapter.schema.json pattern {_ACT_ID_PATTERN.pattern}"
        )

    is_chapter_fallback = chapter_id is None
    target_chapter_id = chapter_id or UNASSIGNED_CHAPTER_ID
    target_act_id = act_id or UNASSIGNED_ACT_ID
    explicit_act_id = act_id is not None

    factory = lock_factory or _default_ontology_lock
    with factory(ontology_path):
        with ontology_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        chapters = _ensure_list(data, "chapters")
        target_chapter = _find_chapter(chapters, target_chapter_id)

        if target_chapter is None and not is_chapter_fallback:
            return ChapterAssignment(
                success=False,
                scene_anchor=scene_anchor,
                chapter_id=target_chapter_id,
                act_id=target_act_id,
                reason="chapter_not_found",
            )

        if target_chapter is None:
            target_chapter = {
                "schema_version": "0.3.0",
                "chapter_id": UNASSIGNED_CHAPTER_ID,
                "display_name": _UNASSIGNED_CHAPTER_DISPLAY_NAME,
                "acts": [],
            }
            chapters.append(target_chapter)

        acts = _ensure_list(target_chapter, "acts")
        target_act = _find_act(acts, target_act_id)

        if target_act is None and explicit_act_id:
            return ChapterAssignment(
                success=False,
                scene_anchor=scene_anchor,
                chapter_id=target_chapter_id,
                act_id=target_act_id,
                reason="act_not_found",
            )

        if target_act is None:
            display = (
                _UNASSIGNED_ACT_DISPLAY_NAME
                if target_act_id == UNASSIGNED_ACT_ID
                else target_act_id
            )
            target_act = {
                "act_id": target_act_id,
                "display_name": display,
                "included_scenes": [],
            }
            acts.append(target_act)

        included = _ensure_list(target_act, "included_scenes")
        already_in_target = scene_anchor in included
        was_elsewhere = _remove_scene_anchor_elsewhere(
            chapters,
            scene_anchor,
            except_chapter=target_chapter,
            except_act=target_act,
        )

        if already_in_target and not was_elsewhere:
            return ChapterAssignment(
                success=True,
                scene_anchor=scene_anchor,
                chapter_id=target_chapter_id,
                act_id=target_act_id,
                reason="idempotent_skip",
            )

        if not already_in_target:
            included.append(scene_anchor)

        write_json_atomic(ontology_path, data, indent=_ONTOLOGY_INDENT)

        if was_elsewhere:
            _LOG.info(
                "chapter_assembler: scene_anchor %r reassigned to "
                "(%s, %s); cleaned %s stale reference(s)",
                scene_anchor,
                target_chapter_id,
                target_act_id,
                "1+",
            )

        reason: ChapterAssignmentReason = (
            "fallback_unassigned" if is_chapter_fallback else "assigned"
        )
        return ChapterAssignment(
            success=True,
            scene_anchor=scene_anchor,
            chapter_id=target_chapter_id,
            act_id=target_act_id,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _ensure_list(container: dict, key: str) -> list:
    """Return `container[key]` as a list, creating an empty one if absent.

    A non-list existing value is treated as ontology corruption: raise
    rather than silently overwrite, so the operator notices.
    """
    value = container.get(key)
    if value is None:
        value = []
        container[key] = value
        return value
    if not isinstance(value, list):
        raise ValueError(
            f"ontology field {key!r} is not a list: got {type(value).__name__}"
        )
    return value


def _find_chapter(chapters: list[dict], chapter_id: str) -> dict | None:
    for c in chapters:
        if isinstance(c, dict) and c.get("chapter_id") == chapter_id:
            return c
    return None


def _find_act(acts: list[dict], act_id: str) -> dict | None:
    for a in acts:
        if isinstance(a, dict) and a.get("act_id") == act_id:
            return a
    return None


def _remove_scene_anchor_elsewhere(
    chapters: list[dict],
    scene_anchor: str,
    *,
    except_chapter: dict,
    except_act: dict,
) -> bool:
    """Drop `scene_anchor` from every (chapter, act).included_scenes
    except the target slot. Returns True iff at least one removal
    happened.

    The same-object identity check (`is`) is intentional: dict identity
    is well-defined here because both `except_chapter` and `except_act`
    are the dicts we just located inside `chapters`, not copies.
    """
    removed = False
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        for act in chapter.get("acts") or []:
            if not isinstance(act, dict):
                continue
            if chapter is except_chapter and act is except_act:
                continue
            included = act.get("included_scenes")
            if not isinstance(included, list):
                continue
            if scene_anchor in included:
                act["included_scenes"] = [
                    s for s in included if s != scene_anchor
                ]
                removed = True
    return removed


# ---------------------------------------------------------------------------
# CA-4: CLI entry point (manual reassign in 审阅工坊期)
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator.chapter_assembler",
        description=(
            "Assign or reassign a scene_anchor to a chapter/act in the "
            "ontology. Use during 审阅工坊期 to manually adjust a scene's "
            "chapter membership. Omit --chapter (and --act) to file the "
            "scene under the unassigned bucket; pass an explicit "
            "--chapter (and optionally --act) to place it in an "
            "author-curated container that already exists in the ontology."
        ),
    )
    parser.add_argument(
        "scene_anchor",
        help="The scene_anchor string (e.g. scene_alpha) to (re)assign.",
    )
    parser.add_argument(
        "--chapter",
        default=None,
        help=(
            "Target chapter_id (e.g. chap_arrival). Must already exist "
            "in the ontology. Omit to file under the unassigned bucket."
        ),
    )
    parser.add_argument(
        "--act",
        default=None,
        help=(
            "Target act_id within --chapter. Must already exist in that "
            "chapter when --chapter is given; ignored without --chapter."
        ),
    )
    parser.add_argument(
        "--ontology",
        type=Path,
        default=DEFAULT_ONTOLOGY_PATH,
        help=f"Ontology JSON path (default: {DEFAULT_ONTOLOGY_PATH}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    args = _build_arg_parser().parse_args(argv)
    ontology_path: Path = args.ontology
    if not ontology_path.exists():
        print(
            f"error: ontology not found: {ontology_path}", file=sys.stderr
        )
        return 2
    try:
        result = assign_scene_to_chapter(
            args.scene_anchor,
            ontology_path,
            chapter_id=args.chapter,
            act_id=args.act,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"chapter_assembler: scene_anchor={result.scene_anchor} "
        f"chapter={result.chapter_id} act={result.act_id} "
        f"reason={result.reason} success={result.success}"
    )
    return 0 if result.success else 1


__all__ = [
    "ChapterAssignment",
    "ChapterAssignmentReason",
    "DEFAULT_ONTOLOGY_PATH",
    "LockFactory",
    "UNASSIGNED_ACT_ID",
    "UNASSIGNED_CHAPTER_ID",
    "assign_scene_to_chapter",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
