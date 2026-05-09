"""FastAPI route table for the T-3.6a review UI MVP (ADR-025) +
T-3.6b integrations layer.

# T-3.6a MVP endpoints (unchanged contract)

  * ``GET  /api/scenes``            scene-list payload (left nav)
  * ``GET  /api/scene/{scene_id}``  full scene detail (graph, validators, deps, advisory, review)
  * ``GET  /api/graph/{scene_id}``  raw mermaid / dot / ascii text (?format=...)
  * ``POST /api/review``            append an A/R decision to ``scene_review_log.jsonl``
  * ``GET  /api/health``            simple liveness probe (used by browser smoke)

# T-3.6b integrations endpoints (new; never touch ``data.ReviewDataLoader``)

  * ``GET  /api/scene/{scene_id}/visuals``  thumbnails for character + location assets
  * ``GET  /api/visual/{asset_id}``         streams the asset PNG/JPG bytes
  * ``GET  /api/playtest/{scene_id}``       worst_paths/scenes for the scene (F13 degrade)
  * ``GET  /api/stale``                     dep_propagate stale list (lazy)
  * ``GET  /api/chapters``                  ontology chapters[] + per-scene placement map

# Module boundary (PR #48 review §3.2)

The integrations layer keeps the MVP ``ReviewDataLoader`` contract
byte-equivalent.  All four T-3.6b readers (visuals / playtest / stale /
chapter) live as module-level helpers below, reading from disk
directly and exposing them through new endpoints.  Path overrides for
production / tests live on ``request.app.state.t36b_*`` attrs so the
``server.build_app`` factory doesn't need to learn new wiring.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .data import GRAPH_FORMATS, ReviewDataLoader


# =============================================================================
# MVP wiring (unchanged from T-3.6a — review C-3.x contract)
# =============================================================================


def get_loader(request: Request) -> ReviewDataLoader:
    loader: ReviewDataLoader | None = getattr(request.app.state, "loader", None)
    if loader is None:  # pragma: no cover — wiring bug
        raise HTTPException(500, "review_ui loader not configured")
    return loader


class ReviewRequest(BaseModel):
    scene_id: str = Field(..., min_length=1)
    iter_id: int | None = None
    decision: Literal["accept", "reject", "skip"]
    reason: str | None = None


# =============================================================================
# T-3.6b integrations layer — module-level helpers (PR #48 review §3.2)
#
# These read from disk directly and never mutate ``ReviewDataLoader``.
# Path overrides come from ``request.app.state.t36b_*`` attrs so we
# don't need to thread new constructor kwargs through ``server.py`` /
# ``cli.py`` (both off-limits per the T-3.6b prompt §模块边界).
# =============================================================================


_IMG_CONTENT_TYPE = {
    "png": "image/png",
    "webp": "image/webp",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

_ALLOWED_VISUAL_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg"}


def _state_attr(request: Request, name: str, default: Any = None) -> Any:
    return getattr(request.app.state, name, default)


def _repo_root(loader: ReviewDataLoader) -> Path:
    """Path that joins with manifest's repo-root-relative ``file_path``.

    Convention: ``scenes_dir`` defaults to ``content/`` so its parent is
    the repo root.  When the operator overrides ``scenes_dir`` to
    something else, we fall back to cwd; the visuals-dir guard inside
    ``_resolve_visual_file`` re-pins resolution to a known root anyway.
    """
    if loader.scenes_dir is not None:
        return loader.scenes_dir.parent
    return Path.cwd().resolve()


def _visuals_dir(loader: ReviewDataLoader, request: Request) -> Path | None:
    override = _state_attr(request, "t36b_visuals_dir")
    if override is not None:
        return Path(override).resolve()
    if loader.scenes_dir is not None:
        return (loader.scenes_dir / "visuals").resolve()
    return None


def _load_visuals_manifest(
    loader: ReviewDataLoader, request: Request
) -> tuple[dict[str, Any] | None, Path | None]:
    visuals_dir = _visuals_dir(loader, request)
    if visuals_dir is None:
        return None, None
    manifest_path = visuals_dir / "manifest.json"
    if not manifest_path.is_file():
        return None, manifest_path
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, manifest_path
    return (data if isinstance(data, dict) else None), manifest_path


def _scene_detail(loader: ReviewDataLoader, scene_id: str) -> dict[str, Any] | None:
    """MVP-public path to a scene's full detail (graph + sidecar + ...)."""
    return loader.get_scene_detail(scene_id)


def _project_visual_asset(asset_id: str, asset: dict[str, Any]) -> dict[str, Any]:
    """Trim an ``ImageAsset`` row to the fields the UI thumbnail card uses."""
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


def _resolve_visual_assets(
    loader: ReviewDataLoader,
    request: Request,
    scene_id: str,
) -> dict[str, Any] | None:
    """RUI-INT-1 + finding 4.1: prefer dep_index sidecar's
    ``visual_asset_ids_referenced``; fall back to scene graph's
    ``character_refs`` + ``scene_anchor`` when the sidecar is absent
    or doesn't carry the field.

    The fallback path is what the T-3.6b prompt literally describes
    (and what content/ scenes hit before T-3.5 backfilled their
    sidecars), so we keep it as the degrade leg rather than dropping
    it entirely.
    """
    detail = _scene_detail(loader, scene_id)
    if detail is None:
        return None
    graph = detail.get("graph") or {}
    sidecar = detail.get("deps") or {}
    scene_anchor = graph.get("scene_anchor")
    character_refs = list(graph.get("character_refs") or [])

    manifest, manifest_path = _load_visuals_manifest(loader, request)
    payload: dict[str, Any] = {
        "scene_id": scene_id,
        "scene_anchor": scene_anchor,
        "character_refs": character_refs,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "manifest_loaded": manifest is not None,
        "characters": [],
        "locations": [],
    }
    if manifest is None:
        return payload

    assets = manifest.get("assets") or {}
    if not isinstance(assets, dict):
        assets = {}

    sidecar_ids: list[str] | None = None
    if isinstance(sidecar, dict):
        raw_ids = sidecar.get("visual_asset_ids_referenced")
        if isinstance(raw_ids, list) and all(isinstance(x, str) for x in raw_ids):
            sidecar_ids = raw_ids
    payload["source"] = "sidecar" if sidecar_ids is not None else "graph_fallback"

    characters: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []

    if sidecar_ids is not None:
        # Authoritative path — only show assets the dep_index actually
        # records as referenced.  Sidecar may list ids that are no
        # longer in the manifest (re-import); skip those silently.
        for asset_id in sidecar_ids:
            asset = assets.get(asset_id)
            if not isinstance(asset, dict):
                continue
            normalized = _project_visual_asset(asset_id, asset)
            if asset.get("target_type") == "character":
                characters.append(normalized)
            elif asset.get("target_type") == "location":
                locations.append(normalized)
            else:  # unknown target_type → bucket by character_ref / location_ref
                if asset.get("character_ref"):
                    characters.append(normalized)
                else:
                    locations.append(normalized)
    else:
        # Graph-fallback: filter manifest by scene's character_refs +
        # scene_anchor.  This was the original prompt behavior and is
        # what content/ scenes use until their sidecars are written.
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
    payload["characters"] = characters
    payload["locations"] = locations
    return payload


def _resolve_visual_file(
    loader: ReviewDataLoader,
    request: Request,
    asset_id: str,
) -> tuple[Path, str] | None:
    """Resolve an asset to ``(disk_path, content_type)`` or None.

    Finding 3.1 hardening:

      * the candidate must resolve **inside** ``visuals_dir`` (not
        merely under the repo root) — pinning to the visuals tree
        prevents a malicious manifest from pointing ``file_path`` at
        ``../../.env`` or ``content/secrets/...``.
      * the candidate's suffix must be in
        :data:`_ALLOWED_VISUAL_SUFFIXES` so even a path inside
        visuals_dir can't smuggle out a ``.txt``/``.json``/``.py``.

    The repo-root path is still used as the *join base* because the
    manifest stores repo-relative paths like ``content/visuals/.../foo.png``;
    after joining we pin against ``visuals_dir.resolve()``.
    """
    manifest, _ = _load_visuals_manifest(loader, request)
    if manifest is None:
        return None
    assets = manifest.get("assets") or {}
    asset = assets.get(asset_id) if isinstance(assets, dict) else None
    if not isinstance(asset, dict):
        return None
    rel = asset.get("file_path")
    if not isinstance(rel, str) or not rel:
        return None
    repo_root = _repo_root(loader)
    visuals_dir = _visuals_dir(loader, request)
    if visuals_dir is None:
        return None
    candidate = (repo_root / rel).resolve()
    visuals_dir_resolved = visuals_dir.resolve()
    try:
        candidate.relative_to(visuals_dir_resolved)
    except ValueError:
        return None
    if candidate.suffix.lower() not in _ALLOWED_VISUAL_SUFFIXES:
        return None
    if not candidate.is_file():
        return None
    fmt = candidate.suffix.lower().lstrip(".")
    content_type = _IMG_CONTENT_TYPE.get(fmt, "application/octet-stream")
    return candidate, content_type


def _playtest_root(loader: ReviewDataLoader, request: Request) -> Path | None:
    """Finding 4.2: T-3.4 CLI writes runs to ``generator/experiments/playtest_NNN/``,
    not inside any specific scene batch directory.  Heuristic:

      * explicit override via ``app.state.t36b_playtest_root`` → use it
      * batch_dir.parent looks like ``generator/experiments`` → use the parent
      * else fall back to batch_dir (the prompt's literal contract)
    """
    override = _state_attr(request, "t36b_playtest_root")
    if override is not None:
        return Path(override).resolve()
    if loader.batch_dir is None:
        return None
    if loader.batch_dir.parent.name == "experiments":
        return loader.batch_dir.parent
    return loader.batch_dir


def _compact_path_row(row: dict[str, Any]) -> dict[str, Any]:
    """Drop the verbose ``steps[]`` snapshot from a worst_paths.jsonl row."""
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


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_playtest(
    loader: ReviewDataLoader,
    request: Request,
    scene_id: str,
) -> dict[str, Any]:
    """F13 degrade contract — never raises, always 200.  When no run
    covers ``scene_id``, returns ``playtest_run=null`` plus a
    human-readable ``reason`` so the panel can render the run-the-CLI
    hint instead of disappearing."""
    root = _playtest_root(loader, request)
    scanned = 0
    if root is not None and root.is_dir():
        runs = sorted(
            (c for c in root.iterdir() if c.is_dir() and c.name.startswith("playtest_")),
            key=lambda p: p.name,
        )
        scanned = len(runs)
        matches: list[tuple[Path, dict[str, Any]]] = []
        for run_dir in runs:
            manifest = _read_json(run_dir / "run_manifest.json")
            if not isinstance(manifest, dict):
                continue
            scenes_played = manifest.get("scenes_played") or []
            if isinstance(scenes_played, list) and scene_id in scenes_played:
                matches.append((run_dir, manifest))
        if matches:
            run_dir, manifest = matches[-1]
            worst_paths_rows: list[dict[str, Any]] = []
            for row in _read_jsonl(run_dir / "worst_paths.jsonl"):
                if row.get("scene_id") == scene_id:
                    worst_paths_rows.append(_compact_path_row(row))
            scenes_payload = _read_json(run_dir / "worst_scenes.json")
            scene_summary = None
            rubric_version = None
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
                "playtest_root": str(root),
            }
    if root is None:
        reason = "no playtest_root resolved (batch_dir not set)"
    elif not root.is_dir():
        reason = f"playtest_root does not exist: {root}"
    elif scanned == 0:
        reason = (
            f"no playtest_*/ subdirs under {root.name}/ "
            f"— run `python -m generator.playtest <scene_path>` then "
            f"refresh"
        )
    else:
        reason = f"no playtest run for this scene (scanned {scanned} run(s))"
    return {
        "scene_id": scene_id,
        "playtest_run": None,
        "reason": reason,
        "all_runs_scanned": scanned,
        "playtest_root": str(root) if root is not None else None,
    }


def _ontology_path(request: Request) -> Path:
    override = _state_attr(request, "t36b_ontology_path")
    if override is not None:
        return Path(override)
    return Path("state/ontology/waystation.json")


def _ontology_root(request: Request) -> Path:
    """``find_stale_scenes`` wants a directory; pass the ontology
    file's parent when the override is a file, else treat as root."""
    p = _ontology_path(request)
    if p.suffix == ".json" or (p.exists() and p.is_file()):
        return p.parent
    return p


def _load_ontology(request: Request) -> dict[str, Any] | None:
    data = _read_json(_ontology_path(request))
    return data if isinstance(data, dict) else None


def _collect_scene_placements(
    loader: ReviewDataLoader,
    request: Request,
    ontology: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """RUI-INT-4 + finding 4.3: build a ``{scene_id: placement}`` map
    where ``placement.source`` is one of:

      * ``"sidecar"`` — sidecar carries both ``chapter_id`` and ``act_id``
      * ``"ontology_anchor_lookup"`` — sidecar lacked the fields, but the
        scene's ``scene_anchor`` matches an ontology
        ``chapters[].acts[].included_scenes`` entry
      * ``"unplaced"`` — neither path resolved

    The frontend gates the chapter tree on at least one ``sidecar`` or
    ``ontology_anchor_lookup`` placement to avoid the "未归入" pseudo-
    state the reviewer flagged.
    """
    placements: dict[str, dict[str, Any]] = {}

    # Index ontology's included_scenes for the fallback path
    anchor_to_act: dict[str, tuple[str, str]] = {}
    if ontology:
        for chap in ontology.get("chapters") or []:
            if not isinstance(chap, dict):
                continue
            chap_id = chap.get("chapter_id")
            for act in chap.get("acts") or []:
                if not isinstance(act, dict):
                    continue
                act_id = act.get("act_id")
                for anchor in act.get("included_scenes") or []:
                    if isinstance(anchor, str) and chap_id and act_id:
                        anchor_to_act[anchor] = (chap_id, act_id)

    for summary in loader.list_scenes():
        scene_id = summary.scene_id
        detail = loader.get_scene_detail(scene_id) or {}
        sidecar = detail.get("deps") if isinstance(detail.get("deps"), dict) else {}
        graph = detail.get("graph") if isinstance(detail.get("graph"), dict) else {}
        scene_anchor = (graph or {}).get("scene_anchor")

        sidecar_chapter = None
        sidecar_act = None
        if isinstance(sidecar, dict):
            cid = sidecar.get("chapter_id")
            aid = sidecar.get("act_id")
            if isinstance(cid, str) and isinstance(aid, str):
                sidecar_chapter, sidecar_act = cid, aid

        if sidecar_chapter and sidecar_act:
            placements[scene_id] = {
                "chapter_id": sidecar_chapter,
                "act_id": sidecar_act,
                "scene_anchor": scene_anchor,
                "source": "sidecar",
            }
            continue

        if scene_anchor and scene_anchor in anchor_to_act:
            chap_id, act_id = anchor_to_act[scene_anchor]
            placements[scene_id] = {
                "chapter_id": chap_id,
                "act_id": act_id,
                "scene_anchor": scene_anchor,
                "source": "ontology_anchor_lookup",
            }
            continue

        placements[scene_id] = {
            "chapter_id": None,
            "act_id": None,
            "scene_anchor": scene_anchor,
            "source": "unplaced",
        }

    return placements


def _resolve_chapters(loader: ReviewDataLoader, request: Request) -> dict[str, Any]:
    ontology = _load_ontology(request)
    path = _ontology_path(request)
    chapters_out: list[dict[str, Any]] = []
    if ontology:
        for chap in ontology.get("chapters") or []:
            if not isinstance(chap, dict):
                continue
            chapters_out.append(
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
    placements = _collect_scene_placements(loader, request, ontology)
    placed_count = sum(
        1
        for p in placements.values()
        if p.get("source") in ("sidecar", "ontology_anchor_lookup")
    )
    return {
        "ontology_path": str(path),
        "ontology_loaded": ontology is not None,
        "chapters": chapters_out,
        "scene_placements": placements,
        "placement_summary": {
            "total": len(placements),
            "placed": placed_count,
            "from_sidecar": sum(1 for p in placements.values() if p.get("source") == "sidecar"),
            "from_ontology_anchor": sum(
                1 for p in placements.values() if p.get("source") == "ontology_anchor_lookup"
            ),
            "unplaced": sum(1 for p in placements.values() if p.get("source") == "unplaced"),
        },
    }


def _resolve_stale(
    loader: ReviewDataLoader,
    request: Request,
    *,
    since: str | None,
    changed_ontology_ids: list[str],
    changed_state_paths: list[str],
    changed_visual_assets: list[str],
    changed_clocks: list[str],
) -> dict[str, Any]:
    from tools.dep_propagate import (  # noqa: WPS433 — lazy by design
        REPORT_SCHEMA_VERSION,
        diff_ontology,
        find_stale_scenes,
        render_json_report,
    )

    content_root = loader.scenes_dir or Path("content")
    ontology_root = _ontology_root(request)

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
    payload["diff_error"] = diff_error
    payload["report_schema_version"] = REPORT_SCHEMA_VERSION
    return payload


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [piece.strip() for piece in value.split(",") if piece.strip()]


# =============================================================================
# Router (MVP routes preserved + T-3.6b additions)
# =============================================================================


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health(loader: ReviewDataLoader = Depends(get_loader)) -> dict:
        return {
            "status": "ok",
            "batch_dir": str(loader.batch_dir) if loader.batch_dir else None,
            "scenes_dir": str(loader.scenes_dir) if loader.scenes_dir else None,
        }

    @router.get("/scenes")
    def list_scenes(loader: ReviewDataLoader = Depends(get_loader)) -> dict:
        rows = [asdict(s) for s in loader.list_scenes()]
        return {
            "batch_dir": str(loader.batch_dir) if loader.batch_dir else None,
            "scenes_dir": str(loader.scenes_dir) if loader.scenes_dir else None,
            "scenes": rows,
        }

    @router.get("/scene/{scene_id}")
    def get_scene(
        scene_id: str,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        detail = loader.get_scene_detail(scene_id)
        if detail is None:
            raise HTTPException(404, f"scene not found: {scene_id}")
        return detail

    @router.get("/graph/{scene_id}", response_class=PlainTextResponse)
    def get_graph(
        scene_id: str,
        format: str = Query("mermaid", pattern=r"^(mermaid|dot|ascii)$"),
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> PlainTextResponse:
        if format not in GRAPH_FORMATS:
            raise HTTPException(400, f"unknown format: {format}")
        result = loader.get_graph_file(scene_id, format)
        if result is None:
            raise HTTPException(
                404, f"graph view not found: {scene_id}/{format}"
            )
        text, content_type = result
        return PlainTextResponse(text, media_type=content_type)

    @router.post("/review")
    def post_review(
        body: ReviewRequest,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        if body.decision in ("reject", "skip") and not (body.reason or "").strip():
            raise HTTPException(400, f"{body.decision} requires a reason")
        try:
            record = loader.append_review(
                scene_id=body.scene_id,
                iter_id=body.iter_id,
                decision=body.decision,
                reason=(body.reason or None),
            )
        except RuntimeError as exc:
            raise HTTPException(400, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "record": record}

    # ---- T-3.6b integrations endpoints --------------------------------

    @router.get("/scene/{scene_id}/visuals")
    def get_scene_visuals(
        scene_id: str,
        request: Request,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        payload = _resolve_visual_assets(loader, request, scene_id)
        if payload is None:
            raise HTTPException(404, f"scene not found: {scene_id}")
        return payload

    @router.get("/visual/{asset_id}")
    def get_visual_file(
        asset_id: str,
        request: Request,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> FileResponse:
        result = _resolve_visual_file(loader, request, asset_id)
        if result is None:
            raise HTTPException(404, f"visual asset not found: {asset_id}")
        path, content_type = result
        return FileResponse(path, media_type=content_type)

    @router.get("/playtest/{scene_id}")
    def get_playtest(
        scene_id: str,
        request: Request,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        return _resolve_playtest(loader, request, scene_id)

    @router.get("/stale")
    def get_stale(
        request: Request,
        since: str | None = Query(None, description="git revision; merges into changed sets"),
        changed_ontology_ids: str | None = Query(None),
        changed_state_paths: str | None = Query(None),
        changed_visual_assets: str | None = Query(None),
        changed_clocks: str | None = Query(None),
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        return _resolve_stale(
            loader,
            request,
            since=since,
            changed_ontology_ids=_split_csv(changed_ontology_ids),
            changed_state_paths=_split_csv(changed_state_paths),
            changed_visual_assets=_split_csv(changed_visual_assets),
            changed_clocks=_split_csv(changed_clocks),
        )

    @router.get("/chapters")
    def get_chapters(
        request: Request,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        return _resolve_chapters(loader, request)

    return router
