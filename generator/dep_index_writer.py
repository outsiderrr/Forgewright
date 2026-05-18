"""ContentDependencyIndex sidecar writer (T-3.5; ADR-023 + F5).

Per ADR-023 §F5: every scene that lands in `/content` is shadowed by a
`<scene>.deps.json` sidecar describing the ontology / state / visual /
clock / prompt-template fingerprints of the prompt that produced it.
The sidecar is **context-assembly trace**, not a scene-content
post-mortem — see `generator.context_assembler.GenerationDependencyTrace`
for the upstream accumulator.

Write-time responsibilities (kept narrow on purpose):

  1. Project the live `GenerationDependencyTrace` into the on-disk
     shape (sets → sorted lists; prompt-template files →
     `sha256:<hex>` digest).
  2. Fold the truncation-aware `TokenMetrics` snapshot from
     `SceneGraphContext` into the matching sidecar fields.
  3. Pull `scene_history_referenced` from the post-truncation prior
     summaries (ADR-024 hook for future RAG / memory-stream upgrades).
  4. Validate the assembled payload against
     `/schema/content_dependency_index.schema.json` before atomic
     write — bad data must fail the batch loudly, not silently land a
     malformed sidecar that breaks `dep_propagate` downstream.

What this module does NOT do (CLAUDE.md rule 2; T-3.5 prompt §模块边界):
  * Touch `/schema/`, `/state/`, `/engine/`, `/validator/` —
    consumers, not producers, of the schema file.
  * Drive chapter assignment or version recording — those are the
    siblings in the F6 write order
    (`write scene → assign chapter → write deps → record version`),
    each owned by its own module (T-3.9 / T-3.8a).
  * Compute or rewrite token metrics — those land on
    `SceneGraphContext.token_metrics` at context-build time (T-3.3 /
    PR #44 review §3.1) and are passed straight through here.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from jsonschema import Draft202012Validator

from generator._atomic_write import write_json_atomic
from generator.context_assembler import (
    GenerationDependencyTrace,
    PriorSceneSummary,
    TokenMetrics,
)

DEP_INDEX_SCHEMA_VERSION = "0.3.0"
SIDECAR_SUFFIX = ".deps.json"

# Read the schema at import time so a bad write fails fast at validate
# time rather than the next time someone runs the validator. The path
# walks up the package tree to `/schema/...`; the project layout (see
# ROADMAP / pyproject) keeps `schema/` and `generator/` siblings under
# the repo root.
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schema"
    / "content_dependency_index.schema.json"
)
_DEP_INDEX_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_DEP_INDEX_VALIDATOR = Draft202012Validator(_DEP_INDEX_SCHEMA)

# `scene_id` and `state path` patterns mirror the schema. We pre-compile
# them so the writer can apply the schema's rejection criteria *before*
# building the full payload — gives a clearer error trail than the
# generic "did not match pattern" jsonschema message buried under the
# full document validation report.
_SCENE_ID_RE = re.compile(r"^[a-z0-9_]+$")
_STATE_PATH_RE = re.compile(
    r"^("
    r"world\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    r"|faction\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    r"|relationship\.[a-z0-9_]+\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    r"|flag\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    r"|player\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    # Codex review PR #66 finding 4.3：ADR-016 v0.4 第 6 命名空间 knowledge.*
    # 加入；T-3Y 场景写入 knowledge.* state path 不应在 sidecar 落盘阶段被拒
    r"|knowledge\.[a-z0-9_]+(\.[a-z0-9_]+)*"
    r")$"
)


def sidecar_path_for(scene_path: Path) -> Path:
    """`scene.json` → `scene.deps.json` (sibling)."""
    return scene_path.with_suffix(SIDECAR_SUFFIX)


def _now_iso() -> str:
    """Module-level so tests can monkeypatch wall clock."""
    return datetime.now(timezone.utc).isoformat()


def _hash_template_files(template_files: Sequence[Path]) -> str:
    """`sha256:<hex>` digest of the concatenated template-file bytes.

    Order matters: the caller provides templates in render order so
    re-running with the same prompt set produces a stable hash. Empty
    list → digest of an empty byte string (still schema-conformant; the
    schema only requires the prefix + 64 hex chars).
    """
    digest = hashlib.sha256()
    for path in template_files:
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _scene_id_from_graph(scene: dict) -> str:
    """Pull `graph_id` from the scene dict and project it into the
    `scene_id` shape required by the dep_index schema.

    `dialogue_graph.graph_id` allows `[a-z0-9_-]` per its schema; the
    sidecar's `scene_id` allows only `[a-z0-9_]` (ADR-023 / F15: the
    sidecar shape is intentionally stricter — sidecar filenames don't
    encode `-` and IDs flowing into `dep_propagate` need a single
    canonical form). We replace `-` with `_` only — any other
    out-of-range character is a bug we want to surface, so the regex
    check below raises if the projection still doesn't match.
    """
    raw = scene.get("graph_id")
    if not isinstance(raw, str) or not raw:
        raise ValueError(
            "scene dict is missing string `graph_id`; cannot derive "
            "sidecar scene_id."
        )
    projected = raw.replace("-", "_")
    if not _SCENE_ID_RE.fullmatch(projected):
        raise ValueError(
            f"graph_id {raw!r} cannot be projected into dep_index "
            f"scene_id (pattern {_SCENE_ID_RE.pattern}); got {projected!r}."
        )
    return projected


def _scene_history_referenced(
    prior_scene_summaries: Sequence[PriorSceneSummary] | None,
) -> list[str]:
    """Collect `scene_id`s the LLM saw in `prior_scene_summaries`.

    Caller is expected to pass the **post-truncation** list (the same
    set whose hashes land in `summary_source_hashes`). Each id is
    pattern-checked here so a malformed prior id surfaces at write
    time rather than under jsonschema's terser report.
    """
    if not prior_scene_summaries:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for s in prior_scene_summaries:
        sid = getattr(s, "scene_id", None)
        if not isinstance(sid, str) or not sid:
            continue
        if not _SCENE_ID_RE.fullmatch(sid):
            raise ValueError(
                f"prior_scene_summaries entry has invalid scene_id {sid!r} "
                f"(must match {_SCENE_ID_RE.pattern})."
            )
        if sid in seen:
            continue
        seen.add(sid)
        out.append(sid)
    return out


def _validate_state_paths(paths: list[str], *, label: str) -> None:
    """Reject paths that fail the ADR-016 five-namespace shape early.

    The full schema validator catches these too, but its error report
    is verbose and per-instance. This pre-check produces a single
    targeted message naming the offending path, which is friendlier in
    `dep_index_writer` failure mode (operator sees "trace contains bare
    `world` namespace" instead of "Failed validating 'pattern' in
    schema['properties']['state_paths_written']…").
    """
    for p in paths:
        if not _STATE_PATH_RE.fullmatch(p):
            raise ValueError(
                f"{label} contains state path {p!r} that does not match "
                f"the ADR-016 five-namespace pattern (bare namespaces "
                f"like 'world' / 'flag' / 'relationship.<slug>' are "
                f"rejected; minimum two segments — relationship.* needs "
                f"at least slug + field)."
            )


def build_sidecar_payload(
    *,
    scene: dict,
    trace: GenerationDependencyTrace,
    prior_scene_summaries: Sequence[PriorSceneSummary] | None,
    token_metrics: TokenMetrics | None,
    chapter_id: str | None,
    act_id: str | None,
    generated_at: str | None = None,
) -> dict:
    """Project the live trace + token metrics + chapter/act assignment
    into the sidecar JSON payload.

    Optional fields (chapter_id, act_id, visual / clock / scene-history
    arrays, the four token-metrics fields) are emitted only when their
    values are non-empty / non-None. The schema declares them as
    `missing-only` (no `null` form), so we drop the keys entirely
    rather than emit `null`. This matches the F15 modification on the
    schema side.
    """
    scene_id = _scene_id_from_graph(scene)

    state_paths_read = sorted(trace.state_paths_read)
    state_paths_written = sorted(trace.state_paths_written)
    _validate_state_paths(state_paths_read, label="state_paths_read")
    _validate_state_paths(state_paths_written, label="state_paths_written")

    payload: dict = {
        "schema_version": DEP_INDEX_SCHEMA_VERSION,
        "scene_id": scene_id,
        "generated_at": generated_at or _now_iso(),
        "ontology_ids_read": sorted(trace.ontology_ids_read),
        "state_paths_read": state_paths_read,
        "state_paths_written": state_paths_written,
        "prompt_template_hash": _hash_template_files(
            trace.prompt_template_files
        ),
    }

    if trace.visual_asset_ids_referenced:
        payload["visual_asset_ids_referenced"] = sorted(
            trace.visual_asset_ids_referenced
        )
    if trace.clock_ids_referenced:
        payload["clock_ids_referenced"] = sorted(
            trace.clock_ids_referenced
        )

    if isinstance(chapter_id, str) and chapter_id:
        payload["chapter_id"] = chapter_id
    if isinstance(act_id, str) and act_id:
        payload["act_id"] = act_id

    history = _scene_history_referenced(prior_scene_summaries)
    if history:
        payload["scene_history_referenced"] = history

    if token_metrics is not None:
        # Token-metrics fields are schema-optional but writer-mandatory:
        # whenever token_metrics is supplied (i.e. for every scene that
        # went through `generate_scene` / batch_scheduler), the four
        # fields land verbatim. ADR-024 token-curve / acceptance-rate
        # regression analysis at end-of-Stage-3 needs every scene to
        # carry the full metrics tuple — silently omitting "default"
        # values (0 / "none") makes "scene with 0 summaries injected"
        # indistinguishable from "scene whose hook never ran", which
        # breaks the regression cohort.
        payload["prompt_token_estimate"] = token_metrics.prompt_token_estimate
        payload["summaries_injected_count"] = (
            token_metrics.summaries_injected_count
        )
        payload["summary_source_hashes"] = list(
            token_metrics.summary_source_hashes
        )
        payload["truncation_reason"] = token_metrics.truncation_reason or "none"

    return payload


def write_sidecar(
    scene_path: Path,
    scene: dict,
    trace: GenerationDependencyTrace,
    prior_scene_summaries: Sequence[PriorSceneSummary] | None,
    token_metrics: TokenMetrics | None,
    chapter_id: str | None,
    act_id: str | None,
    *,
    generated_at: str | None = None,
) -> Path:
    """Write `<scene>.deps.json` next to `scene_path` (atomic + schema-checked).

    Validates the assembled payload against the dep_index schema before
    landing the bytes; a violation raises `jsonschema.ValidationError`
    so the caller (T-3.5 batch worker) can record the failure with
    full diagnostic context rather than discovering a malformed
    sidecar later.

    Returns the sidecar path written.
    """
    payload = build_sidecar_payload(
        scene=scene,
        trace=trace,
        prior_scene_summaries=prior_scene_summaries,
        token_metrics=token_metrics,
        chapter_id=chapter_id,
        act_id=act_id,
        generated_at=generated_at,
    )
    _DEP_INDEX_VALIDATOR.validate(payload)
    sidecar = sidecar_path_for(scene_path)
    write_json_atomic(sidecar, payload)
    return sidecar


__all__ = [
    "DEP_INDEX_SCHEMA_VERSION",
    "SIDECAR_SUFFIX",
    "build_sidecar_payload",
    "sidecar_path_for",
    "write_sidecar",
]
