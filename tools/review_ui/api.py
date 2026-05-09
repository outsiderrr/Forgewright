"""FastAPI route table for the T-3.6a review UI MVP (ADR-025).

Endpoints (all under ``/api`` except the static / index routes which
``server.build_app`` mounts on top of these):

  * ``GET  /api/scenes``            scene-list payload (left nav)
  * ``GET  /api/scene/{scene_id}``  full scene detail (graph, validators, deps, advisory, review)
  * ``GET  /api/graph/{scene_id}``  raw mermaid / dot / ascii text (?format=...)
  * ``POST /api/review``            append an A/R decision to ``scene_review_log.jsonl``
  * ``GET  /api/health``            simple liveness probe (used by browser smoke)

T-3.6b integrations layer (RUI-INT-1..4 — additive; MVP routes above
keep the same contract):

  * ``GET  /api/scene/{scene_id}/visuals``  thumbnails for character + location assets
  * ``GET  /api/visual/{asset_id}``         streams the asset PNG/JPG bytes
  * ``GET  /api/playtest/{scene_id}``       worst_paths/scenes for the scene (F13 degrade)
  * ``GET  /api/stale``                     dep_propagate stale list (lazy)
  * ``GET  /api/chapters``                  ontology chapters[].acts[].included_scenes

The router is intentionally a small surface — ``server.build_app`` is
the composition root that wires it to a ``ReviewDataLoader``, exposes
the static directory, and serves the index page.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .data import GRAPH_FORMATS, ReviewDataLoader


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

    # ---- T-3.6b integrations (RUI-INT-1..4) -----------------------------

    @router.get("/scene/{scene_id}/visuals")
    def get_scene_visuals(
        scene_id: str,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        payload = loader.get_visual_assets(scene_id)
        if payload is None:
            raise HTTPException(404, f"scene not found: {scene_id}")
        return payload

    @router.get("/visual/{asset_id}")
    def get_visual_file(
        asset_id: str,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> FileResponse:
        # Path traversal guard lives inside ``loader.get_visual_file``;
        # any escape attempt returns None and we 404 here.
        result = loader.get_visual_file(asset_id)
        if result is None:
            raise HTTPException(404, f"visual asset not found: {asset_id}")
        path, content_type = result
        return FileResponse(path, media_type=content_type)

    @router.get("/playtest/{scene_id}")
    def get_playtest(
        scene_id: str,
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        # F13 degrade: the loader handles "no data" by returning a payload
        # with ``playtest_run=null`` and a human reason. We never 404 — the
        # UI's playtest panel always renders, even pre-run.
        return loader.get_playtest(scene_id)

    @router.get("/stale")
    def get_stale(
        since: str | None = Query(None, description="git revision; merges into changed_ontology / state"),
        changed_ontology_ids: str | None = Query(
            None,
            description="comma-separated ontology entity ids that changed",
        ),
        changed_state_paths: str | None = Query(
            None,
            description="comma-separated ADR-016 state paths (e.g. faction.iron_oath.*)",
        ),
        changed_visual_assets: str | None = Query(
            None, description="comma-separated visual asset_ids that changed"
        ),
        changed_clocks: str | None = Query(
            None, description="comma-separated clock ids that changed"
        ),
        loader: ReviewDataLoader = Depends(get_loader),
    ) -> dict:
        def split(value: str | None) -> list[str]:
            if not value:
                return []
            return [piece.strip() for piece in value.split(",") if piece.strip()]

        return loader.get_stale(
            since=since,
            changed_ontology_ids=split(changed_ontology_ids),
            changed_state_paths=split(changed_state_paths),
            changed_visual_assets=split(changed_visual_assets),
            changed_clocks=split(changed_clocks),
        )

    @router.get("/chapters")
    def get_chapters(loader: ReviewDataLoader = Depends(get_loader)) -> dict:
        return loader.get_chapters()

    return router
