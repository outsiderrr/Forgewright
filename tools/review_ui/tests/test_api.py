"""FastAPI route tests via TestClient (no live socket)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools.review_ui.server import build_app


@pytest.fixture
def client(fixture_batch_dir: Path, fixture_scenes_dir: Path) -> TestClient:
    app = build_app(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["batch_dir"] is not None
    assert body["scenes_dir"] is not None


def test_list_scenes_returns_batch_plus_content(client: TestClient) -> None:
    r = client.get("/api/scenes")
    assert r.status_code == 200
    body = r.json()
    ids = {s["scene_id"] for s in body["scenes"]}
    assert {"s_alpha", "demo_scene"} <= ids


def test_get_scene_batch_includes_advisory(client: TestClient) -> None:
    r = client.get("/api/scene/s_alpha")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "batch"
    assert body["advisory"] == "accept"
    assert body["validator_summaries"]["topology"]["pass"] is True
    assert body["graph_views_available"] == ["mermaid", "dot", "ascii"]


def test_get_scene_unknown_404(client: TestClient) -> None:
    r = client.get("/api/scene/nope")
    assert r.status_code == 404


def test_graph_mermaid(client: TestClient) -> None:
    r = client.get("/api/graph/s_alpha?format=mermaid")
    assert r.status_code == 200
    assert "flowchart TD" in r.text
    assert r.headers["content-type"].startswith("text/plain")


def test_graph_dot(client: TestClient) -> None:
    r = client.get("/api/graph/s_alpha?format=dot")
    assert r.status_code == 200
    assert "digraph" in r.text


def test_graph_ascii(client: TestClient) -> None:
    r = client.get("/api/graph/s_alpha?format=ascii")
    assert r.status_code == 200
    assert "n_start" in r.text


def test_graph_unknown_format_422(client: TestClient) -> None:
    # FastAPI's pattern validation gives 422 for invalid query enum
    r = client.get("/api/graph/s_alpha?format=svg")
    assert r.status_code == 422


def test_graph_unknown_scene_404(client: TestClient) -> None:
    r = client.get("/api/graph/missing?format=mermaid")
    assert r.status_code == 404


def test_review_accept_writes_log(client: TestClient, fixture_batch_dir: Path) -> None:
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "accept", "reason": None},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["record"]["accepted"] is True
    log = (fixture_batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(log[-1])["scene_id"] == "s_alpha"


def test_review_reject_requires_reason(client: TestClient) -> None:
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "reject", "reason": ""},
    )
    assert r.status_code == 400


def test_review_reject_with_reason_persists(client: TestClient, fixture_batch_dir: Path) -> None:
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "reject", "reason": "weak ending"},
    )
    assert r.status_code == 200, r.text
    rec = json.loads((fixture_batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert rec["accepted"] is False
    assert rec["reason"] == "weak ending"


def test_review_unknown_decision_422(client: TestClient) -> None:
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "maybe", "reason": None},
    )
    assert r.status_code == 422


def test_index_serves_html(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Forgewright Review UI" in r.text
    assert "<script src=\"/static/app.js\"></script>" in r.text


def test_static_assets_served(client: TestClient) -> None:
    r = client.get("/static/styles.css")
    assert r.status_code == 200
    assert "--accent" in r.text
    r = client.get("/static/app.js")
    assert r.status_code == 200
    assert "ensureMermaid" in r.text


def test_static_vendor_bundle_present(client: TestClient) -> None:
    """RUI-MVP-5 / F17: vendor mermaid bundle must ship with the package."""
    r = client.get("/static/vendor/mermaid.min.js")
    assert r.status_code == 200
    # The bundle is large; we just sanity-check it's a real mermaid build
    # without inflating the test by reading 2 MB of JS.
    assert len(r.content) > 100_000
    head = r.text[:500]
    assert "mermaid" in head.lower()


def test_review_endpoint_when_batch_dir_missing(fixture_scenes_dir: Path) -> None:
    app = build_app(batch_dir=None, scenes_dir=fixture_scenes_dir)
    client = TestClient(app)
    r = client.post(
        "/api/review",
        json={"scene_id": "demo_scene", "iter_id": None, "decision": "accept", "reason": None},
    )
    assert r.status_code == 400
