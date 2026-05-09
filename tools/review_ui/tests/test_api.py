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
    by_id = {s["scene_id"]: s for s in body["scenes"]}
    assert {"s_alpha", "s_gamma", "demo_scene"} <= by_id.keys()
    # Reviewable surfaces must be present (review C-3.1 UI gating depends on them).
    assert by_id["s_alpha"]["reviewable"] is True
    assert by_id["s_gamma"]["reviewable"] is False
    assert by_id["demo_scene"]["reviewable"] is False


def test_get_scene_batch_includes_advisory_and_reviewable(client: TestClient) -> None:
    r = client.get("/api/scene/s_alpha")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "batch"
    assert body["advisory"] == "accept"
    assert body["validator_summaries"]["topology"]["pass"] is True
    assert body["graph_views_available"] == ["mermaid", "dot", "ascii"]
    assert body["reviewable"] is True


def test_get_scene_failed_row_is_not_reviewable(client: TestClient) -> None:
    r = client.get("/api/scene/iter_1")
    assert r.status_code == 200
    body = r.json()
    assert body["reviewable"] is False
    assert body["not_reviewable_reason"] is not None


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
    r = client.get("/api/graph/s_alpha?format=svg")
    assert r.status_code == 422


def test_graph_unknown_scene_404(client: TestClient) -> None:
    r = client.get("/api/graph/missing?format=mermaid")
    assert r.status_code == 404


def test_graph_path_traversal_rejected(client: TestClient, fixture_batch_dir: Path) -> None:
    """Review C-4.2: encoded ../ in scene_id must not escape graph_views/."""
    (fixture_batch_dir / "secret.mmd").write_text("secret", encoding="utf-8")
    r = client.get("/api/graph/%2E%2E?format=mermaid")  # encoded ".."
    assert r.status_code == 404
    r = client.get("/api/graph/%2E%2E%2Fsecret?format=mermaid")  # encoded "../secret"
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


def test_review_skip_persists_with_accepted_null(
    client: TestClient, fixture_batch_dir: Path
) -> None:
    """Review C-3.2: [S] writes a row with accepted=null + reason."""
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "skip", "reason": "defer"},
    )
    assert r.status_code == 200, r.text
    rec = r.json()["record"]
    assert rec["accepted"] is None
    assert rec["reason"] == "defer"
    log_rows = [
        json.loads(line)
        for line in (fixture_batch_dir / "scene_review_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert log_rows[-1]["accepted"] is None
    # And the scene list now reports it as 'skipped', not 'rejected'.
    list_resp = client.get("/api/scenes").json()
    by_id = {s["scene_id"]: s for s in list_resp["scenes"]}
    assert by_id["s_alpha"]["review_status"] == "skipped"


def test_review_skip_requires_reason(client: TestClient) -> None:
    """Review C-3.2: skip without reason is rejected by the API."""
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "skip", "reason": ""},
    )
    assert r.status_code == 400


def test_review_unknown_decision_422(client: TestClient) -> None:
    r = client.post(
        "/api/review",
        json={"scene_id": "s_alpha", "iter_id": 0, "decision": "maybe", "reason": None},
    )
    assert r.status_code == 422


def test_review_unknown_scene_422(client: TestClient) -> None:
    """Review C-3.1: unreachable scene_id surfaces a 422 from the gate."""
    r = client.post(
        "/api/review",
        json={"scene_id": "nope", "iter_id": 999, "decision": "accept", "reason": None},
    )
    assert r.status_code == 422
    assert "not reviewable" in r.text


def test_review_failed_batch_row_422(client: TestClient) -> None:
    """Review C-3.1: failed batch row cannot be A/R/S annotated."""
    r = client.post(
        "/api/review",
        json={"scene_id": "iter_1", "iter_id": 1, "decision": "accept", "reason": None},
    )
    assert r.status_code == 422
    assert "failed batch row" in r.text


def test_review_mechanical_failure_422(client: TestClient) -> None:
    """Review C-3.1: success=True but mech-fail row cannot be reviewed."""
    r = client.post(
        "/api/review",
        json={"scene_id": "s_gamma", "iter_id": 2, "decision": "accept", "reason": None},
    )
    assert r.status_code == 422
    assert "mechanical pre-check" in r.text


def test_review_content_scene_unreviewable(client: TestClient) -> None:
    """Content scenes have no batch envelope → fall through the same gate."""
    r = client.post(
        "/api/review",
        json={"scene_id": "demo_scene", "iter_id": None, "decision": "accept", "reason": None},
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
