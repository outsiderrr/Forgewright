"""T-2.8 smoke tests: scene_experiment + scene_review_cli + scene_metrics.

No real Gemini calls — `_ScriptedProvider` returns canned responses for
each (skeleton, fill) call generate_scene makes. The fixture rotation
+ JSONL envelope shape is the contract scene_review_cli + scene_metrics
depend on, so these tests pin both.
"""
from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from generator import scene_experiment, scene_metrics, scene_review_cli
from generator.llm_provider import StructuredResponse
from generator.scene_experiment import SceneFixture
from generator.scene_strategies import GraphSkeleton, SceneSetting, SkeletonNode


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")
    monkeypatch.setenv("SCENE_BUDGET_USD", "10")


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=200,
        output_tokens=400,
        model_id="fake-model",
        finish_reason="STOP",
    )


_VALID_SKELETON_JSON: dict = {
    "nodes": [
        {"node_id": "n_arrival", "type": "dialogue", "beat": "抵达驿站",
         "speaker_ref": "char_vellin", "expected_branch_count": 3},
        {"node_id": "n_confession", "type": "dialogue", "beat": "Vellin 承认",
         "speaker_ref": "char_vellin", "expected_branch_count": 2},
        {"node_id": "n_patrol", "type": "dialogue", "beat": "巡逻官登场",
         "speaker_ref": "char_corvan", "expected_branch_count": 3},
        {"node_id": "n_end_silent", "type": "end", "beat": "ending：共谋",
         "speaker_ref": None, "expected_branch_count": 0},
        {"node_id": "n_end_iron", "type": "end", "beat": "ending：告发",
         "speaker_ref": None, "expected_branch_count": 0},
    ],
    "edges": [
        ["n_arrival", "n_confession"], ["n_arrival", "n_patrol"],
        ["n_confession", "n_end_silent"], ["n_confession", "n_end_iron"],
        ["n_patrol", "n_end_silent"], ["n_patrol", "n_end_iron"],
    ],
    "entry_node_id": "n_arrival",
    "end_node_ids": ["n_end_silent", "n_end_iron"],
}


def _valid_filled_node(skel_node: SkeletonNode, allowed_targets: list[str]) -> dict:
    if skel_node.type == "end":
        return {
            "node_id": skel_node.node_id, "type": "end",
            "narration": f"（ending：{skel_node.beat}）",
            "speaker_ref": None,
            "location_ref": "scene_waystation_of_iron_oath",
            "on_enter_effects": [], "options": [],
        }
    targets = allowed_targets or ["unknown"]
    options = []
    for i in range(skel_node.expected_branch_count):
        options.append({
            "option_id": f"opt_{skel_node.node_id}_{i+1}",
            "text": f"选项 {i+1}",
            "target_node_id": targets[i % len(targets)],
            "condition": None, "effects": [],
            "unavailable_behavior": "hide",
        })
    return {
        "node_id": skel_node.node_id, "type": "dialogue",
        "narration": f"（节拍 {skel_node.beat} 的台词。）",
        "speaker_ref": skel_node.speaker_ref,
        "location_ref": "scene_waystation_of_iron_oath",
        "on_enter_effects": [], "options": options,
    }


def _one_scene_script() -> list[StructuredResponse]:
    """Skeleton + 5 fill responses, deterministic per call."""
    skel_nodes = [
        SkeletonNode(
            node_id=n["node_id"], type=n["type"], beat=n["beat"],
            speaker_ref=n.get("speaker_ref"),
            expected_branch_count=n["expected_branch_count"],
        )
        for n in _VALID_SKELETON_JSON["nodes"]
    ]
    skel = GraphSkeleton(
        nodes=skel_nodes,
        edges=[tuple(e) for e in _VALID_SKELETON_JSON["edges"]],
        entry_node_id=_VALID_SKELETON_JSON["entry_node_id"],
        end_node_ids=_VALID_SKELETON_JSON["end_node_ids"],
    )
    return [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + [
        _make_response(_valid_filled_node(n, skel.get_allowed_targets(n.node_id)))
        for n in skel_nodes
    ]


class _ScriptedProvider:
    model_id = "fake-model"

    def __init__(self, script):
        self._script = list(script)
        self._idx = 0
        self.call_count = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        if self._idx >= len(self._script):
            raise AssertionError(
                f"scripted provider exhausted at call {self.call_count}"
            )
        resp = self._script[self._idx]
        self._idx += 1
        return resp

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.005


def _tiny_ontology() -> dict:
    """Minimal ontology providing just the participating characters +
    location entries the strategy needs. Includes state_path_slug so the
    T-2.4 mechanical pre-check (BOND_ID_UNKNOWN) doesn't false-positive."""
    return {
        "system_time": {"scene_count": 0, "long_rest_count": 0},
        "clocks": [],
        "chapters": [],
        "entities": [
            {"id": "char_vellin", "type": "character", "display_name": "Vellin",
             "state_path_slug": "vellin", "character_features": [], "relations": []},
            {"id": "char_corvan", "type": "character", "display_name": "Corvan",
             "state_path_slug": "corvan", "character_features": [], "relations": []},
            {"id": "char_aelwin", "type": "character", "display_name": "Aelwin",
             "state_path_slug": "aelwin", "character_features": [], "relations": []},
            {"id": "scene_waystation_of_iron_oath", "type": "location",
             "display_name": "铁誓驿站", "location_type": "scene"},
        ],
    }


def _tiny_fixture() -> SceneFixture:
    return SceneFixture(
        fixture_id="iron_oath_smoke",
        scene_setting=SceneSetting(
            scene_anchor="scene_waystation_of_iron_oath",
            primary_location_ref="scene_waystation_of_iron_oath",
            chapter_ref=None,
            expected_node_count_min=5,
            expected_node_count_max=12,
        ),
        target_beats=("抵达", "承认", "结局"),
        participating_npcs=("char_vellin", "char_corvan"),
    )


# ---------------------------------------------------------------------------
# scene_experiment.run_scene_experiment
# ---------------------------------------------------------------------------


def test_run_scene_experiment_writes_results_and_views(tmp_path):
    """Two iterations of a single fixture: 2 × (1 skeleton + 5 fills) calls,
    two graph_views/<scene_id>/ directories, one summary."""
    provider = _ScriptedProvider(_one_scene_script() + _one_scene_script())
    batch_dir = scene_experiment.run_scene_experiment(
        batch_name="smoke",
        count=2,
        provider=provider,
        out_root=tmp_path,
        fixtures=[_tiny_fixture()],
        ontology=_tiny_ontology(),
        timestamp="20260504T000000Z",
        progress=False,
    )
    assert batch_dir == tmp_path / "20260504T000000Z_smoke"
    results = (batch_dir / "scene_results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(results) == 2

    rows = [json.loads(r) for r in results]
    for i, row in enumerate(rows):
        assert row["iter_id"] == i
        assert row["fixture_id"] == "iron_oath_smoke"
        assert row["result"]["success"] is True
        assert row["result"]["graph"] is not None
        # Validator summaries baked in at experiment time.
        v = row["validator_summaries"]
        assert v is not None
        assert {"mechanical", "topology", "sampling"} <= v.keys()
        assert v["mechanical"]["pass"] is True
        assert v["sampling"]["sample_count"] > 0

    # Summary file mentions the ADR-020 metrics.
    summary = (batch_dir / "scene_summary.txt").read_text(encoding="utf-8")
    for keyword in (
        "schema_pass_rate",
        "gross_pass_rate",
        "topology_pass_rate",
        "sampling_reach_rate",
    ):
        assert keyword in summary

    # Three views per success scene.
    views_root = batch_dir / "graph_views"
    scene_dirs = list(views_root.iterdir())
    assert scene_dirs, "expected at least one graph_views subdir"
    for d in scene_dirs:
        for fname in ("mermaid.mmd", "dot.gv", "ascii.txt"):
            assert (d / fname).exists(), f"missing {fname} in {d}"
            assert (d / fname).read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# scene_review_cli — scripted input + --help smoke
# ---------------------------------------------------------------------------


def _scripted_input(answers: list[str]):
    queue = list(answers)

    def _read(prompt: str) -> str:
        if not queue:
            raise EOFError("scripted input exhausted")
        return queue.pop(0)

    return _read


def _seed_review_batch(tmp_path: Path) -> Path:
    """Run a 2-iter experiment so we have a real scene_results.jsonl to review."""
    provider = _ScriptedProvider(_one_scene_script() + _one_scene_script())
    return scene_experiment.run_scene_experiment(
        batch_name="review_smoke",
        count=2,
        provider=provider,
        out_root=tmp_path,
        fixtures=[_tiny_fixture()],
        ontology=_tiny_ontology(),
        timestamp="20260504T010000Z",
        progress=False,
    )


def test_scene_review_cli_records_accept_reject(tmp_path):
    batch_dir = _seed_review_batch(tmp_path)
    answers = ["a", "r", "对白突兀"]  # iter 0 accept; iter 1 reject + reason
    out = io.StringIO()
    written = scene_review_cli.run_scene_review(
        batch_dir, input_fn=_scripted_input(answers), output=out
    )
    assert written == 2

    log_lines = (
        (batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").splitlines()
    )
    assert len(log_lines) == 2
    rec0, rec1 = (json.loads(l) for l in log_lines)
    assert rec0["accepted"] is True
    assert rec0["mechanical_pass"] is True
    assert rec0["topology_pass"] is True
    assert rec0["scene_id"]
    assert rec1["accepted"] is False
    assert rec1["reason"] == "对白突兀"


def test_scene_review_cli_help_smoke():
    """v1.0 §2.8: `scene_review_cli --help` must return 0 and list flags."""
    proc = subprocess.run(
        [sys.executable, "-m", "generator.scene_review_cli", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    assert proc.returncode == 0
    assert "--batch-dir" in proc.stdout
    assert "--web" in proc.stdout


# ---------------------------------------------------------------------------
# scene_metrics
# ---------------------------------------------------------------------------


def test_scene_metrics_computes_gross_and_topology_rates(tmp_path):
    batch_dir = _seed_review_batch(tmp_path)
    m = scene_metrics.compute_scene_metrics(batch_dir)
    assert m["total_attempts"] == 2
    assert m["schema_pass_rate"] == 1.0
    assert m["gross_pass_rate"] == 1.0  # mechanical pre-check is the gross gate
    assert m["mechanical_pass_rate"] == 1.0
    assert m["topology_pass_rate"] == 1.0
    assert m["sampling_reach_rate"] is not None
    assert m["sampling_reach_rate"] >= 0.0
    assert m["mean_cost_per_attempt"] > 0
    # No review log yet → review keys absent.
    assert "acceptance_rate" not in m


def test_scene_metrics_with_review_log(tmp_path):
    batch_dir = _seed_review_batch(tmp_path)
    log_path = batch_dir / "scene_review_log.jsonl"
    log_path.write_text(
        json.dumps({"iter_id": 0, "scene_id": "s0", "schema_pass": True,
                    "topology_pass": True, "sampling_pass": True,
                    "mechanical_pass": True, "accepted": True,
                    "reason": None, "reviewed_at": "2026-05-04T00:00:00+00:00"}) + "\n"
        + json.dumps({"iter_id": 1, "scene_id": "s1", "schema_pass": True,
                      "topology_pass": True, "sampling_pass": True,
                      "mechanical_pass": True, "accepted": False,
                      "reason": "节奏拖沓",
                      "reviewed_at": "2026-05-04T00:01:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    m = scene_metrics.compute_scene_metrics(batch_dir)
    assert m["reviewed_count"] == 2
    assert m["acceptance_rate"] == pytest.approx(0.5)
    assert ("节奏拖沓", 1) in m["reject_reason_top_5"]
