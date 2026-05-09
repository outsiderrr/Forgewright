"""Read-only data layer for the T-3.6a review UI MVP.

Loads scenes from two sources:

  * ``batch_dir`` — a ``/generator/experiments/<batch>/`` directory
    produced by ``scene_experiment``.  Provides full envelopes (graph +
    validator summaries + cost), the ``graph_views/<scene_id>/`` triple
    (mermaid / dot / ascii), the AI judge advisory report, and the
    ``scene_review_log.jsonl`` decision log.
  * ``scenes_dir`` — typically ``/content/``.  Each subdir contains a
    ``scene.json`` (final accepted scene) and may carry a sibling
    ``<scene_id>.deps.json`` sidecar (ContentDependencyIndex).

Writes only happen against ``scene_review_log.jsonl`` inside ``batch_dir``
— matching the schema produced by ``generator/scene_review_cli.py`` so
the two clients can interleave on the same batch.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GRAPH_FORMATS: dict[str, tuple[str, str]] = {
    "mermaid": ("mermaid.mmd", "text/plain; charset=utf-8"),
    "dot": ("dot.gv", "text/plain; charset=utf-8"),
    "ascii": ("ascii.txt", "text/plain; charset=utf-8"),
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _read_json_or_none(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# data loader
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SceneSummary:
    """Lightweight per-scene row returned by ``GET /api/scenes``.

    T-3.6b extension: ``scene_anchor`` is added so the chapter-grouping
    UI can match scenes to ``chapters[].acts[].included_scenes`` without
    a second round-trip per scene. Field is additive — MVP clients that
    don't read it stay unaffected.
    """

    scene_id: str
    iter_id: int | None
    fixture_id: str | None
    source: str  # "batch" | "content"
    success: bool | None
    failure_reason: str | None
    review_status: str  # "unreviewed" | "accepted" | "rejected" | "skipped"
    review_reason: str | None
    advisory: str | None
    schema_pass: bool | None
    mechanical_pass: bool | None
    topology_pass: bool | None
    sampling_pass: bool | None
    cost_usd: float | None
    node_count: int | None
    has_deps_sidecar: bool
    reviewable: bool = False
    not_reviewable_reason: str | None = None
    graph_views_available: list[str] = field(default_factory=list)
    scene_anchor: str | None = None


def _envelope_scene_id(env: dict[str, Any]) -> str:
    graph = (env.get("result") or {}).get("graph") or {}
    sid = graph.get("graph_id")
    if sid:
        return str(sid)
    return f"iter_{env.get('iter_id')}"


def _validator_passes(env: dict[str, Any]) -> dict[str, bool | None]:
    summaries = env.get("validator_summaries") or {}
    if not summaries:
        return {
            "schema_pass": None,
            "mechanical_pass": None,
            "topology_pass": None,
            "sampling_pass": None,
        }
    mech = summaries.get("mechanical") or {}
    topo = summaries.get("topology") or {}
    samp = summaries.get("sampling") or {}
    sample_count = int(samp.get("sample_count", 0) or 0)
    reached = int(samp.get("reached_end_count", 0) or 0)
    deadlocks = int(samp.get("deadlock_count", 0) or 0)
    sampling_strict = (
        sample_count > 0 and reached == sample_count and deadlocks == 0
    )
    return {
        "schema_pass": True if (env.get("result") or {}).get("success") else None,
        "mechanical_pass": mech.get("pass"),
        "topology_pass": topo.get("pass"),
        "sampling_pass": sampling_strict if summaries.get("sampling") else None,
    }


class ReviewDataLoader:
    """Loads scenes + serves graph file contents + persists review decisions.

    All paths are resolved at construction time; subsequent reads happen
    fresh on each call so the operator can rerun ``scene_experiment``
    while the server is up without restarting.

    A single ``threading.Lock`` guards appends to ``scene_review_log.jsonl``
    — the file is JSONL so concurrent appends would interleave bytes.
    The lock is per-loader instance; in the MVP only one loader exists
    per process.
    """

    def __init__(
        self,
        *,
        batch_dir: Path | None,
        scenes_dir: Path | None,
        visuals_dir: Path | None = None,
        ontology_path: Path | None = None,
        playtest_root: Path | None = None,
    ) -> None:
        self.batch_dir = batch_dir.resolve() if batch_dir else None
        self.scenes_dir = scenes_dir.resolve() if scenes_dir else None
        # T-3.6b integrations: paths default to the conventional layout
        # (visuals next to scenes; ontology at repo's state/ontology;
        # playtest dirs nested under batch_dir per the prompt's literal
        # ``batch_dir/playtest_NNN/`` contract — operator can copy or
        # symlink playtest output into batch_dir).
        self.visuals_dir = (
            visuals_dir.resolve()
            if visuals_dir
            else (self.scenes_dir / "visuals" if self.scenes_dir else None)
        )
        self.ontology_path = ontology_path.resolve() if ontology_path else None
        self.playtest_root = (
            playtest_root.resolve() if playtest_root else self.batch_dir
        )
        self._review_lock = threading.Lock()

    # -- discovery --------------------------------------------------------

    def list_scenes(self) -> list[SceneSummary]:
        rows: list[SceneSummary] = []
        seen_ids: set[str] = set()
        for env in self._batch_envelopes():
            summary = self._envelope_to_summary(env)
            seen_ids.add(summary.scene_id)
            rows.append(summary)
        for content_summary in self._content_summaries():
            if content_summary.scene_id in seen_ids:
                continue
            rows.append(content_summary)
        rows.sort(key=lambda s: (s.source, s.iter_id if s.iter_id is not None else 1_000_000, s.scene_id))
        return rows

    def get_scene_detail(self, scene_id: str) -> dict[str, Any] | None:
        for env in self._batch_envelopes():
            if _envelope_scene_id(env) == scene_id:
                return self._envelope_to_detail(env)
        for path in self._content_scene_paths():
            data = _read_json_or_none(path)
            if not data or data.get("graph_id") != scene_id:
                continue
            deps_path = path.parent / f"{scene_id}.deps.json"
            return {
                "scene_id": scene_id,
                "source": "content",
                "iter_id": None,
                "fixture_id": None,
                "fixture": None,
                "graph": data,
                "validator_summaries": None,
                "advisory": None,
                "advisory_rationale": None,
                "review": None,
                "deps": _read_json_or_none(deps_path),
                "cost_usd": None,
                "reviewable": False,
                "not_reviewable_reason": (
                    "content/ scene already accepted; edits live in JSON + git, "
                    "not in scene_review_log.jsonl (ADR-025)"
                ),
                "graph_views_available": [],
                "scene_path": str(path),
            }
        return None

    # -- graph view file ---------------------------------------------------

    def _graph_views_root(self) -> Path | None:
        if not self.batch_dir:
            return None
        return (self.batch_dir / "graph_views").resolve()

    def _safe_view_dir(self, scene_id: str) -> Path | None:
        """Resolve ``graph_views/<scene_id>/`` and reject path traversal.

        Without the ``is_relative_to`` guard, a URL-encoded ``..`` in
        ``scene_id`` could escape the graph_views root and read arbitrary
        files under ``batch_dir``.  ``review C-4.2`` tightens this even
        though ``cli.py`` defaults to ``--host 127.0.0.1`` — the CLI lets
        the operator override it, so we don't trust the network boundary.
        """
        root = self._graph_views_root()
        if root is None:
            return None
        view_dir = (root / scene_id).resolve()
        try:
            view_dir.relative_to(root)
        except ValueError:
            return None
        return view_dir

    def get_graph_file(self, scene_id: str, fmt: str) -> tuple[str, str] | None:
        if fmt not in GRAPH_FORMATS:
            return None
        view_dir = self._safe_view_dir(scene_id)
        if view_dir is None or not view_dir.is_dir():
            return None
        filename, content_type = GRAPH_FORMATS[fmt]
        path = view_dir / filename
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8"), content_type

    def graph_views_available(self, scene_id: str) -> list[str]:
        view_dir = self._safe_view_dir(scene_id)
        if view_dir is None or not view_dir.is_dir():
            return []
        out: list[str] = []
        for fmt, (filename, _) in GRAPH_FORMATS.items():
            if (view_dir / filename).is_file():
                out.append(fmt)
        return out

    # -- review log --------------------------------------------------------

    def review_log_path(self) -> Path | None:
        if not self.batch_dir:
            return None
        return self.batch_dir / "scene_review_log.jsonl"

    def is_reviewable(self, scene_id: str, iter_id: int | None) -> tuple[bool, str | None]:
        """Return (reviewable?, blocking_reason).

        Acceptance-truth-source guard (review C-3.1): only batch envelopes
        that succeeded AND passed mechanical pre-check can carry an A/R/S
        decision.  ``content/`` scenes are already accepted and live under
        author-managed git, not the review log.  Failed-batch rows must
        be rerun, not annotated.
        """
        env = self._lookup_envelope(scene_id, iter_id)
        if env is None:
            return False, f"scene_id not found in batch_dir: {scene_id!r}"
        result = env.get("result") or {}
        if result.get("success") is not True:
            return False, (
                f"failed batch row (failure_reason={result.get('failure_reason')!r}); "
                "rerun rather than annotate"
            )
        passes = _validator_passes(env)
        if passes["mechanical_pass"] is not True:
            return False, "scene failed mechanical pre-check (T-2.4); not reviewable"
        return True, None

    def append_review(
        self,
        *,
        scene_id: str,
        iter_id: int | None,
        decision: str,
        reason: str | None,
    ) -> dict[str, Any]:
        if decision not in ("accept", "reject", "skip"):
            raise ValueError(
                f"decision must be 'accept', 'reject', or 'skip', got {decision!r}"
            )
        if decision in ("reject", "skip") and not (reason or "").strip():
            raise ValueError(f"{decision!r} requires a non-empty reason")
        log_path = self.review_log_path()
        if log_path is None:
            raise RuntimeError("batch_dir is required for review submissions")
        ok, why = self.is_reviewable(scene_id, iter_id)
        if not ok:
            raise ValueError(f"scene not reviewable: {why}")
        env = self._lookup_envelope(scene_id, iter_id)
        assert env is not None  # is_reviewable just confirmed
        passes = _validator_passes(env)
        topo = (env.get("validator_summaries") or {}).get("topology") or {}
        if decision == "accept":
            accepted: bool | None = True
        elif decision == "reject":
            accepted = False
        else:
            accepted = None  # skip
        record = {
            "iter_id": iter_id if iter_id is not None else env.get("iter_id"),
            "scene_id": scene_id,
            "schema_pass": passes["schema_pass"] is True,
            "topology_pass": topo.get("pass"),
            "pure_topology_pass": topo.get("pure_topology_pass"),
            "condition_form_pass": topo.get("condition_form_pass"),
            "sampling_pass": passes["sampling_pass"],
            "mechanical_pass": passes["mechanical_pass"],
            "accepted": accepted,
            "reason": reason.strip() if decision in ("reject", "skip") else None,
            "reviewed_at": _now_iso(),
        }
        with self._review_lock:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return record

    # -- internals --------------------------------------------------------

    def _envelope_to_summary(self, env: dict[str, Any]) -> SceneSummary:
        scene_id = _envelope_scene_id(env)
        result = env.get("result") or {}
        graph = result.get("graph") or {}
        passes = _validator_passes(env)
        review = self._review_index().get((env.get("iter_id"), scene_id))
        if review is None:
            status, review_reason = "unreviewed", None
        elif review.get("accepted") is True:
            status, review_reason = "accepted", review.get("reason")
        elif review.get("accepted") is False:
            status, review_reason = "rejected", review.get("reason")
        else:  # accepted is None → review C-3.2 [S] skip persisted
            status, review_reason = "skipped", review.get("reason")
        deps_path = (
            self.batch_dir / "deps" / f"{scene_id}.deps.json"
            if self.batch_dir
            else None
        )
        reviewable, not_reviewable_reason = self.is_reviewable(
            scene_id, env.get("iter_id")
        )
        return SceneSummary(
            scene_id=scene_id,
            iter_id=env.get("iter_id"),
            fixture_id=env.get("fixture_id"),
            source="batch",
            success=result.get("success"),
            failure_reason=result.get("failure_reason"),
            review_status=status,
            review_reason=review_reason,
            advisory=self._advisory_index().get(scene_id),
            schema_pass=passes["schema_pass"],
            mechanical_pass=passes["mechanical_pass"],
            topology_pass=passes["topology_pass"],
            sampling_pass=passes["sampling_pass"],
            cost_usd=result.get("total_cost_usd"),
            node_count=len(graph.get("nodes") or {}),
            has_deps_sidecar=bool(deps_path and deps_path.exists()),
            reviewable=reviewable,
            not_reviewable_reason=not_reviewable_reason,
            graph_views_available=self.graph_views_available(scene_id),
            scene_anchor=graph.get("scene_anchor"),
        )

    def _envelope_to_detail(self, env: dict[str, Any]) -> dict[str, Any]:
        scene_id = _envelope_scene_id(env)
        result = env.get("result") or {}
        graph = result.get("graph") or {}
        review = self._review_index().get((env.get("iter_id"), scene_id))
        deps = None
        if self.batch_dir:
            deps_path = self.batch_dir / "deps" / f"{scene_id}.deps.json"
            deps = _read_json_or_none(deps_path)
        reviewable, not_reviewable_reason = self.is_reviewable(
            scene_id, env.get("iter_id")
        )
        return {
            "scene_id": scene_id,
            "source": "batch",
            "iter_id": env.get("iter_id"),
            "fixture_id": env.get("fixture_id"),
            "fixture": env.get("fixture"),
            "graph": graph,
            "validator_summaries": env.get("validator_summaries"),
            "advisory": self._advisory_index().get(scene_id),
            "advisory_rationale": self._advisory_rationales().get(scene_id),
            "review": review,
            "deps": deps,
            "cost_usd": result.get("total_cost_usd"),
            "inner_attempt_count": result.get("inner_attempt_count"),
            "failure_reason": result.get("failure_reason"),
            "failure_node_id": result.get("failure_node_id"),
            "reviewable": reviewable,
            "not_reviewable_reason": not_reviewable_reason,
            "graph_views_available": self.graph_views_available(scene_id),
        }

    def _content_summaries(self) -> Iterable[SceneSummary]:
        for path in self._content_scene_paths():
            data = _read_json_or_none(path)
            if not isinstance(data, dict):
                continue
            scene_id = data.get("graph_id")
            if not scene_id:
                continue
            deps_path = path.parent / f"{scene_id}.deps.json"
            yield SceneSummary(
                scene_id=str(scene_id),
                iter_id=None,
                fixture_id=None,
                source="content",
                success=None,
                failure_reason=None,
                review_status="unreviewed",
                review_reason=None,
                advisory=None,
                schema_pass=None,
                mechanical_pass=None,
                reviewable=False,
                not_reviewable_reason=(
                    "content/ scene already accepted; edits live in JSON + git, "
                    "not in scene_review_log.jsonl (ADR-025)"
                ),
                topology_pass=None,
                sampling_pass=None,
                cost_usd=None,
                node_count=len(data.get("nodes") or {}),
                has_deps_sidecar=deps_path.exists(),
                graph_views_available=[],
                scene_anchor=data.get("scene_anchor"),
            )

    def _content_scene_paths(self) -> list[Path]:
        if not self.scenes_dir or not self.scenes_dir.is_dir():
            return []
        out: list[Path] = []
        for child in sorted(self.scenes_dir.iterdir()):
            scene_path = child / "scene.json"
            if scene_path.is_file():
                out.append(scene_path)
        return out

    def _batch_envelopes(self) -> list[dict[str, Any]]:
        if not self.batch_dir:
            return []
        return _read_jsonl(self.batch_dir / "scene_results.jsonl")

    def _review_index(self) -> dict[tuple[int | None, str], dict[str, Any]]:
        log_path = self.review_log_path()
        if log_path is None:
            return {}
        out: dict[tuple[int | None, str], dict[str, Any]] = {}
        for rec in _read_jsonl(log_path):
            key = (rec.get("iter_id"), rec.get("scene_id") or "")
            out[key] = rec
        return out

    def _advisory_report(self) -> dict[str, Any]:
        if not self.batch_dir:
            return {}
        return _read_json_or_none(self.batch_dir / "AI_JUDGE_REPORT.json") or {}

    def _advisory_index(self) -> dict[str, str]:
        return self._advisory_report().get("advisory_recommendation") or {}

    def _advisory_rationales(self) -> dict[str, dict[str, str]]:
        return self._advisory_report().get("rationales") or {}

    def _lookup_envelope(
        self, scene_id: str, iter_id: int | None
    ) -> dict[str, Any] | None:
        for env in self._batch_envelopes():
            if iter_id is not None and env.get("iter_id") != iter_id:
                continue
            if _envelope_scene_id(env) == scene_id:
                return env
        return None

    # =====================================================================
    # T-3.6b integrations (RUI-INT-1..4) — additive helpers; MVP methods
    # above stay byte-identical to the T-3.6a contract.
    # =====================================================================

    # ---- shared scene-graph resolver -----------------------------------

    def _resolve_scene_graph(self, scene_id: str) -> dict[str, Any] | None:
        """Return the dialogue-graph dict for ``scene_id`` from either the
        batch envelope or the content/ scene.json. Used by visuals and
        chapter-membership lookup; MVP detail loaders do their own thing."""
        for env in self._batch_envelopes():
            if _envelope_scene_id(env) == scene_id:
                graph = (env.get("result") or {}).get("graph") or None
                if graph:
                    return graph
        for path in self._content_scene_paths():
            data = _read_json_or_none(path)
            if isinstance(data, dict) and data.get("graph_id") == scene_id:
                return data
        return None

    # ---- RUI-INT-1: visual asset thumbnails -----------------------------

    def _load_visuals_manifest(self) -> dict[str, Any] | None:
        if not self.visuals_dir:
            return None
        manifest_path = self.visuals_dir / "manifest.json"
        data = _read_json_or_none(manifest_path)
        return data if isinstance(data, dict) else None

    def _visuals_file_root(self) -> Path | None:
        """Resolution base for relative ``file_path`` entries in manifest.json.

        Manifest stores paths like ``content/visuals/vellin/img.png`` —
        relative to the repo root. ``scenes_dir`` defaults to ``content/``
        so its parent is the repo root.  When the operator overrides
        ``scenes_dir`` to something else, fall back to cwd; the path
        traversal guard below still pins resolution to a known root.
        """
        if self.scenes_dir is not None:
            return self.scenes_dir.parent
        return Path.cwd().resolve()

    def get_visual_assets(self, scene_id: str) -> dict[str, Any] | None:
        graph = self._resolve_scene_graph(scene_id)
        if graph is None:
            return None
        character_refs = list(graph.get("character_refs") or [])
        scene_anchor = graph.get("scene_anchor")
        manifest = self._load_visuals_manifest()
        manifest_path = (
            str(self.visuals_dir / "manifest.json") if self.visuals_dir else None
        )
        if manifest is None:
            return {
                "scene_id": scene_id,
                "scene_anchor": scene_anchor,
                "character_refs": character_refs,
                "manifest_loaded": False,
                "manifest_path": manifest_path,
                "characters": [],
                "locations": [],
            }
        characters: list[dict[str, Any]] = []
        locations: list[dict[str, Any]] = []
        assets = manifest.get("assets") or {}
        if not isinstance(assets, dict):
            assets = {}
        for asset_id, asset in assets.items():
            if not isinstance(asset, dict):
                continue
            target_type = asset.get("target_type")
            target_ref = asset.get("target_ref")
            character_ref = asset.get("character_ref")
            location_ref = asset.get("location_ref")
            normalized = _project_visual_asset(str(asset_id), asset)
            if target_type == "character" and (
                target_ref in character_refs or character_ref in character_refs
            ):
                characters.append(normalized)
            elif target_type == "location" and scene_anchor and (
                target_ref == scene_anchor or location_ref == scene_anchor
            ):
                locations.append(normalized)
        characters.sort(key=lambda a: (a.get("character_ref") or "", a.get("asset_id") or ""))
        locations.sort(key=lambda a: (a.get("location_ref") or "", a.get("asset_id") or ""))
        return {
            "scene_id": scene_id,
            "scene_anchor": scene_anchor,
            "character_refs": character_refs,
            "manifest_loaded": True,
            "manifest_path": manifest_path,
            "characters": characters,
            "locations": locations,
        }

    def get_visual_file(self, asset_id: str) -> tuple[Path, str] | None:
        """Resolve an asset to ``(disk_path, content_type)`` or None.

        Path traversal guard mirrors :meth:`_safe_view_dir` — the
        manifest's ``file_path`` is data, not trusted input, but we
        still pin resolution to ``_visuals_file_root`` so a manifest
        edited offline can't escape it.
        """
        manifest = self._load_visuals_manifest()
        if manifest is None:
            return None
        assets = manifest.get("assets") or {}
        asset = assets.get(asset_id) if isinstance(assets, dict) else None
        if not isinstance(asset, dict):
            return None
        rel = asset.get("file_path")
        if not isinstance(rel, str) or not rel:
            return None
        base = self._visuals_file_root()
        if base is None:
            return None
        candidate = (base / rel).resolve()
        base_resolved = base.resolve()
        try:
            candidate.relative_to(base_resolved)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        fmt = str(asset.get("format") or "").lower()
        content_type = _IMG_CONTENT_TYPE.get(fmt, "application/octet-stream")
        return candidate, content_type

    # ---- RUI-INT-2: playtest worst paths/scenes (F13 degrade) -----------

    def get_playtest(self, scene_id: str) -> dict[str, Any]:
        """Search ``playtest_root/playtest_*/`` for runs covering ``scene_id``.

        F13 degrade: never raises, never 404s on missing data. When no
        run covers this scene the response carries ``playtest_run=null``
        + a human-readable ``reason`` so the UI keeps rendering the
        panel (with the run-the-CLI hint) instead of hiding it.
        """
        scanned = 0
        if self.playtest_root is not None and self.playtest_root.is_dir():
            runs = [
                c
                for c in sorted(self.playtest_root.iterdir(), key=lambda p: p.name)
                if c.is_dir() and c.name.startswith("playtest_")
            ]
            scanned = len(runs)
            matches: list[tuple[Path, dict[str, Any]]] = []
            for run_dir in runs:
                manifest = _read_json_or_none(run_dir / "run_manifest.json")
                if not isinstance(manifest, dict):
                    continue
                scenes_played = manifest.get("scenes_played") or []
                if isinstance(scenes_played, list) and scene_id in scenes_played:
                    matches.append((run_dir, manifest))
            if matches:
                run_dir, manifest = matches[-1]
                worst_paths_rows: list[dict[str, Any]] = []
                paths_path = run_dir / "worst_paths.jsonl"
                if paths_path.is_file():
                    for row in _read_jsonl(paths_path):
                        if row.get("scene_id") == scene_id:
                            worst_paths_rows.append(_compact_path_row(row))
                scene_summary = None
                rubric_version = None
                scenes_payload = _read_json_or_none(run_dir / "worst_scenes.json")
                if isinstance(scenes_payload, dict):
                    rubric_version = scenes_payload.get("rubric_version")
                    for s in scenes_payload.get("scenes") or []:
                        if isinstance(s, dict) and s.get("scene_id") == scene_id:
                            scene_summary = s
                            break
                return {
                    "scene_id": scene_id,
                    "playtest_run": run_dir.name,
                    "playtest_id": manifest.get("playtest_id"),
                    "started_at": manifest.get("started_at"),
                    "completed_at": manifest.get("completed_at"),
                    "model_id": manifest.get("model_id"),
                    "rubric_version": rubric_version,
                    "scene_summary": scene_summary,
                    "worst_paths": worst_paths_rows,
                    "all_runs_scanned": scanned,
                    "playtest_root": str(self.playtest_root),
                }
        # F13 degrade — no run covers this scene
        if self.playtest_root is None:
            reason = "no playtest_root configured (batch_dir not set)"
        elif not self.playtest_root.is_dir():
            reason = f"playtest_root does not exist: {self.playtest_root}"
        elif scanned == 0:
            reason = (
                f"no playtest_*/ subdirs under {self.playtest_root.name}/ "
                f"— run `python -m generator.playtest <scene_path>` then "
                f"copy/symlink the output dir into batch_dir"
            )
        else:
            reason = (
                f"no playtest run for this scene (scanned {scanned} run(s) "
                f"under {self.playtest_root.name}/)"
            )
        return {
            "scene_id": scene_id,
            "playtest_run": None,
            "reason": reason,
            "all_runs_scanned": scanned,
            "playtest_root": (
                str(self.playtest_root) if self.playtest_root is not None else None
            ),
        }

    # ---- RUI-INT-3: stale list (lazy dep_propagate call) ----------------

    def _effective_ontology_path(self) -> Path:
        return self.ontology_path or Path("state/ontology/waystation.json")

    def _effective_ontology_root(self) -> Path:
        path = self._effective_ontology_path()
        # dep_propagate.find_stale_scenes accepts a directory; if the
        # operator passed a single-file ontology, hand it the parent.
        if path.is_file() or path.suffix == ".json":
            return path.parent
        return path

    def get_stale(
        self,
        *,
        since: str | None = None,
        changed_ontology_ids: list[str] | None = None,
        changed_state_paths: list[str] | None = None,
        changed_visual_assets: list[str] | None = None,
        changed_clocks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run T-3.7 reverse-propagate against the configured content/ontology
        roots and return the JSON report verbatim (schema_version pinned by
        ``tools.dep_propagate.REPORT_SCHEMA_VERSION``).

        Lazy import keeps the review UI startup free of dep_propagate's
        git subprocess / regex compile cost when the operator never opens
        the stale view.
        """
        from tools.dep_propagate import (  # noqa: WPS433 — lazy by design
            REPORT_SCHEMA_VERSION,
            diff_ontology,
            find_stale_scenes,
            render_json_report,
        )

        content_root = self.scenes_dir or Path("content")
        ontology_root = self._effective_ontology_root()

        explicit_ids = list(changed_ontology_ids or [])
        explicit_paths = list(changed_state_paths or [])
        explicit_visuals = list(changed_visual_assets or [])
        explicit_clocks = list(changed_clocks or [])
        diff_error: str | None = None
        if since:
            try:
                diff = diff_ontology(ontology_root, since)
                explicit_ids = sorted(set(explicit_ids) | set(diff.changed_ontology_ids))
                explicit_paths = sorted(set(explicit_paths) | set(diff.changed_state_paths))
            except RuntimeError as exc:
                diff_error = str(exc)

        stale = find_stale_scenes(
            changed_ontology_ids=explicit_ids,
            changed_state_paths=explicit_paths,
            changed_visual_assets=explicit_visuals,
            changed_clocks=explicit_clocks,
            content_root=content_root,
            ontology_root=ontology_root,
        )
        inputs_meta = {
            "since_commit": since,
            "changed_ontology_ids": explicit_ids,
            "changed_state_paths": explicit_paths,
            "changed_visual_assets": explicit_visuals,
            "changed_clocks": explicit_clocks,
        }
        payload = render_json_report(stale, inputs_meta, content_root)
        # attach errors / metadata that dep_propagate's report doesn't
        # carry on its own — the UI shows these inline so the operator
        # knows when --since failed without surfacing a 500.
        payload["diff_error"] = diff_error
        payload["report_schema_version"] = REPORT_SCHEMA_VERSION
        return payload

    # ---- RUI-INT-4: chapter grouping ------------------------------------

    def _load_ontology(self) -> dict[str, Any] | None:
        path = self._effective_ontology_path()
        data = _read_json_or_none(path)
        return data if isinstance(data, dict) else None

    def get_chapters(self) -> dict[str, Any]:
        ontology = self._load_ontology()
        path = self._effective_ontology_path()
        if ontology is None:
            return {
                "ontology_path": str(path),
                "ontology_loaded": False,
                "chapters": [],
            }
        chapters: list[dict[str, Any]] = []
        for chap in ontology.get("chapters") or []:
            if not isinstance(chap, dict):
                continue
            chapters.append(
                {
                    "chapter_id": chap.get("chapter_id"),
                    "display_name": chap.get("display_name"),
                    "acts": [
                        {
                            "act_id": act.get("act_id"),
                            "display_name": act.get("display_name"),
                            "included_scenes": list(act.get("included_scenes") or []),
                        }
                        for act in (chap.get("acts") or [])
                        if isinstance(act, dict)
                    ],
                }
            )
        return {
            "ontology_path": str(path),
            "ontology_loaded": True,
            "chapters": chapters,
        }


# ---------------------------------------------------------------------------
# T-3.6b integrations: helpers shared across endpoints
# ---------------------------------------------------------------------------


_IMG_CONTENT_TYPE = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _project_visual_asset(asset_id: str, asset: dict[str, Any]) -> dict[str, Any]:
    """Trim an ``ImageAsset`` row to the fields the UI thumbnail card uses.

    Stripping bulky fields (prompt_hash, generation_metadata, reference_ids)
    keeps the JSON payload small for batches with hundreds of assets.
    """
    return {
        "asset_id": asset_id,
        "asset_kind": asset.get("asset_kind"),
        "asset_role": asset.get("asset_role"),
        "target_type": asset.get("target_type"),
        "target_ref": asset.get("target_ref"),
        "character_ref": asset.get("character_ref"),
        "location_ref": asset.get("location_ref"),
        "format": asset.get("format"),
        "width": asset.get("width"),
        "height": asset.get("height"),
        "has_alpha": asset.get("has_alpha"),
        "file_path": asset.get("file_path"),
        "file_url": f"/api/visual/{asset_id}",
    }


def _compact_path_row(row: dict[str, Any]) -> dict[str, Any]:
    """Drop the verbose ``steps[]`` snapshot from a worst_paths.jsonl row.

    The full step trace is hundreds of KB per path; the review UI only
    needs the summary metrics (judge_score, severity counts) plus a
    pointer back to ``worst_paths.jsonl`` for the operator to grep.
    """
    return {
        "path_id": row.get("path_id"),
        "persona_id": row.get("persona_id"),
        "scene_id": row.get("scene_id"),
        "reached_end": row.get("reached_end"),
        "end_node_id": row.get("end_node_id"),
        "failure_reason": row.get("failure_reason"),
        "judge_score": row.get("judge_score"),
        "judge_dimensions": row.get("judge_dimensions"),
        "judge_rationale": row.get("judge_rationale"),
        "severity_findings": row.get("severity_findings") or [],
        "critical_count": row.get("critical_count"),
        "major_count": row.get("major_count"),
        "minor_count": row.get("minor_count"),
        "step_count": len(row.get("steps") or []),
    }
