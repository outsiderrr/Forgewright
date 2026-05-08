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
        item = self._script[self._idx]
        self._idx += 1
        # R2.9 metadata test injects a ProviderError as a script item; the
        # earlier shape only ever returned StructuredResponse rows.
        if isinstance(item, Exception):
            raise item
        return item

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

    # R2.9: success rows must have failure_metadata == None (the column
    # is reserved for provider_error rows; all other states leave it
    # absent so a finder grepping the file gets a stable shape).
    for row in rows:
        assert row["result"]["failure_metadata"] is None


def test_run_scene_experiment_serialises_failure_metadata_on_provider_error(tmp_path):
    """A scripted ProviderError on the skeleton call must surface in the
    jsonl envelope as `result.failure_metadata = {exception_class,
    http_status, response_body_excerpt}`. This is the R2.9 contract that
    lets baseline_NNN diagnose 三类失败假说 from one row."""
    from generator.llm_provider import ProviderError

    class _Synth429(Exception):
        status_code = 429
        body = '{"error": "rate limit exceeded by upstream relay"}'

    err = ProviderError.from_exception(
        _Synth429("rate limited"),
        message="PoloAI API error: rate limited",
    )
    provider = _ScriptedProvider([err])
    batch_dir = scene_experiment.run_scene_experiment(
        batch_name="r29_metadata_smoke",
        count=1,
        provider=provider,
        out_root=tmp_path,
        fixtures=[_tiny_fixture()],
        ontology=_tiny_ontology(),
        timestamp="20260506T000000Z",
        progress=False,
    )
    rows = [
        json.loads(r)
        for r in (batch_dir / "scene_results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 1
    result = rows[0]["result"]
    assert result["success"] is False
    assert result["failure_reason"] == "provider_error"
    md = result["failure_metadata"]
    assert isinstance(md, dict)
    assert md["http_status"] == 429
    assert md["exception_class"].endswith("._Synth429")
    assert "rate limit" in md["response_body_excerpt"]


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
    # Review 4.2: dual-report fields land in the persisted log.
    assert rec0["pure_topology_pass"] is True
    assert rec0["condition_form_pass"] is True
    assert rec0["scene_id"]
    assert rec1["accepted"] is False
    assert rec1["reason"] == "对白突兀"


def _seed_synthetic_review_batch(
    tmp_path: Path,
    *,
    sampling: dict,
    topology: dict | None = None,
) -> Path:
    """Hand-build a scene_results.jsonl row so review_cli's record-derivation
    rules can be exercised without standing up a real generate_scene flow.
    """
    batch_dir = tmp_path / "synthetic"
    batch_dir.mkdir(parents=True, exist_ok=True)
    topo = topology or {
        "pass": True,
        "pure_topology_pass": True,
        "condition_form_pass": True,
        "condition_form_issue_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "error_codes": [],
        "unreachable_nodes": [],
        "deadlock_nodes": [],
    }
    env = {
        "iter_id": 0,
        "fixture_id": "synthetic",
        "fixture": {
            "scene_setting": {
                "scene_anchor": "scene_x", "primary_location_ref": "scene_x",
                "chapter_ref": None,
                "expected_node_count_min": 5, "expected_node_count_max": 12,
            },
            "target_beats": [], "participating_npcs": [],
        },
        "result": {
            "success": True, "failure_reason": None, "failure_node_id": None,
            "graph": {"graph_id": "synth", "entry_node_id": "n", "nodes": {}},
            "schema_issues": [], "mechanical_issues_count": 0,
            "total_cost_usd": 0.0, "inner_attempt_count": 1,
        },
        "validator_summaries": {
            "mechanical": {"pass": True, "error_node_count": 0,
                           "error_count": 0, "error_codes": []},
            "topology": topo,
            "sampling": sampling,
        },
        "generated_at": "2026-05-04T00:00:00+00:00",
    }
    (batch_dir / "scene_results.jsonl").write_text(
        json.dumps(env, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return batch_dir


def test_scene_review_cli_sampling_pass_rejects_partial_reach(tmp_path):
    """Review 4.1: a 1/100-reached / 99-deadlock scene must NOT log
    sampling_pass=True. ADR-021 2B口径是路径全通且无死锁。"""
    batch_dir = _seed_synthetic_review_batch(
        tmp_path,
        sampling={
            "sample_count": 100,
            "reached_end_count": 1,
            "deadlock_count": 99,
            "avg_path_length": 7.5,
            "reach_rate": 0.01,
            "end_distribution": {},
        },
    )
    out = io.StringIO()
    written = scene_review_cli.run_scene_review(
        batch_dir, input_fn=_scripted_input(["a"]), output=out
    )
    assert written == 1
    rec = json.loads(
        (batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").strip()
    )
    assert rec["sampling_pass"] is False, (
        "sampling_pass must require reached==sample_count AND 0 deadlocks "
        "(ADR-021 2B); got reached=1/100 with 99 deadlocks → must be False."
    )


def test_scene_review_cli_sampling_pass_accepts_clean_run(tmp_path):
    """A 100/100-reached / 0-deadlock scene must log sampling_pass=True."""
    batch_dir = _seed_synthetic_review_batch(
        tmp_path,
        sampling={
            "sample_count": 100,
            "reached_end_count": 100,
            "deadlock_count": 0,
            "avg_path_length": 5.0,
            "reach_rate": 1.0,
            "end_distribution": {"end": 100},
        },
    )
    out = io.StringIO()
    scene_review_cli.run_scene_review(
        batch_dir, input_fn=_scripted_input(["a"]), output=out
    )
    rec = json.loads(
        (batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").strip()
    )
    assert rec["sampling_pass"] is True


def test_scene_experiment_topology_summary_dual_reports(tmp_path):
    """Review 4.2: validator_summaries.topology must expose pure_topology_pass
    and condition_form_pass independently (ADR-021 双报)."""
    batch_dir = _seed_review_batch(tmp_path)
    rows = [
        json.loads(l)
        for l in (batch_dir / "scene_results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    for row in rows:
        topo = (row.get("validator_summaries") or {}).get("topology") or {}
        assert "pure_topology_pass" in topo
        assert "condition_form_pass" in topo
        assert "condition_form_issue_count" in topo


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


# ---------------------------------------------------------------------------
# R3.2 — pre-flight provider health probe (T-3.0)
# ---------------------------------------------------------------------------


class _ProbeOnlyProvider:
    """Returns a single canned response then raises if called again."""

    model_id = "fake-probe-model"

    def __init__(self, content: dict | None, *, raise_exc: Exception | None = None):
        self._content = content
        self._raise = raise_exc
        self.call_count = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        if self._raise is not None:
            raise self._raise
        return StructuredResponse(
            content=self._content or {},
            raw_text=json.dumps(self._content or {}, ensure_ascii=False),
            input_tokens=10,
            output_tokens=4,
            model_id=self.model_id,
            finish_reason="STOP",
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0005


def test_probe_provider_health_ok_on_well_formed_response(tmp_path, capsys):
    """Happy path: provider returns ``{"ok":"yes"}`` → probe OK,
    one call billed."""
    provider = _ProbeOnlyProvider({"ok": "yes"})
    ok, err = scene_experiment.probe_provider_health(provider)
    assert ok is True
    assert err is None
    assert provider.call_count == 1
    out = capsys.readouterr().out
    assert "[probe] OK" in out
    assert "fake-probe-model" in out


def test_probe_provider_health_fails_on_provider_error(tmp_path):
    """ProviderError surfaces as ``(False, "ProviderError: …")`` —
    baseline_008 mode: PoloAI quota gate raises a 403 wrapped as
    ProviderError before any tokens are spent."""
    from generator.llm_provider import ProviderError as PE

    provider = _ProbeOnlyProvider(
        None,
        raise_exc=PE("upstream_error: insufficient_user_quota"),
    )
    ok, err = scene_experiment.probe_provider_health(provider)
    assert ok is False
    assert err is not None
    assert "ProviderError" in err
    assert "insufficient_user_quota" in err


def test_probe_provider_health_fails_on_budget_exceeded(monkeypatch, tmp_path):
    """If the per-call budget is set lower than the probe's estimate,
    BudgetExceeded must surface as a non-fatal probe failure (not crash
    the harness)."""
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.00001")
    provider = _ProbeOnlyProvider({"ok": "yes"})
    ok, err = scene_experiment.probe_provider_health(provider)
    assert ok is False
    assert err is not None
    assert "BudgetExceeded" in err
    # Provider must NOT have been called — check_and_charge guards before
    # any token spend.
    assert provider.call_count == 0


def test_probe_provider_health_fails_on_missing_ok_field(tmp_path):
    """Sanitizer regression / prompt drift could return a JSON blob that
    technically parses but is missing the ``ok`` field — probe must
    treat that as a failure so the batch doesn't silently start with a
    misbehaving provider."""
    provider = _ProbeOnlyProvider({"unrelated": "value"})
    ok, err = scene_experiment.probe_provider_health(provider)
    assert ok is False
    assert err is not None
    assert "missing 'ok'" in err


def test_scene_experiment_main_skip_probe_flag_smoke():
    """``--skip-probe`` must be a recognised flag (CLI surface contract).

    Smoke check via ``--help`` so we don't have to stand up a provider
    just to exercise argparse — if the flag silently disappeared, we'd
    miss the regression at L2 review time."""
    proc = subprocess.run(
        [sys.executable, "-m", "generator.scene_experiment", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    assert proc.returncode == 0
    assert "--skip-probe" in proc.stdout
    assert "pre-flight" in proc.stdout.lower()


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
