"""T-1.7 smoke tests for the experiment harness, review CLI, and metrics.

No real Gemini calls — everything runs against a small FakeProvider that
hands back canned StructuredResponse objects. Together these tests cover:

  * experiment.run_experiment writes a well-formed results.jsonl + summary.txt
  * experiment.run_experiment honours BudgetExceeded by stopping early
  * review_cli.run_review reads results.jsonl, dispatches to a scripted
    input function, and writes a resumable review_log.jsonl
  * metrics.compute_metrics computes pass-rate / cost / failure histogram,
    plus acceptance_rate / reject_reason_top_5 once a review log exists
"""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import pytest

from generator import metrics, review_cli
from generator.experiment import Fixture, run_experiment
from generator.context_assembler import GraphContext, NodeRequirement
from generator.llm_provider import StructuredResponse

# ---------------------------------------------------------------------------
# Test fixtures: budget isolation + a known-good Node JSON
# ---------------------------------------------------------------------------

_SCENE = json.loads(
    (Path(__file__).resolve().parent.parent.parent
     / "content" / "test_scene_v0" / "scene.json").read_text(encoding="utf-8")
)


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _valid_dialogue_node() -> dict:
    return copy.deepcopy(_SCENE["nodes"]["arrival_waystation"])


def _valid_end_node() -> dict:
    return copy.deepcopy(_SCENE["nodes"]["end_silent_ally"])


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=1234,
        output_tokens=567,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _SuccessfulFakeProvider:
    """Returns a schema-valid node every call. Cost is a fixed nominal value."""

    model_id = "fake-model"

    def __init__(self) -> None:
        self.call_count = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        # Return end node for end-type calls so options-empty invariant holds.
        # We detect via the user_prompt having "type=`end`" in the requirement.
        if "`end`" in user_prompt:
            return _make_response(_valid_end_node())
        return _make_response(_valid_dialogue_node())

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.005


class _BudgetExceededFakeProvider:
    """First two calls succeed; the third call would push past PER_CALL cap."""

    model_id = "fake-model"

    def __init__(self) -> None:
        self.call_count = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        if "`end`" in user_prompt:
            return _make_response(_valid_end_node())
        return _make_response(_valid_dialogue_node())

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.005


# A small fixture set the experiment tests use (smaller than the real one
# so per-test runtime stays low). Exercises both dialogue and end shapes.
def _tiny_fixtures() -> list[Fixture]:
    base_ctx = GraphContext(
        scene_anchor="scene_waystation_of_iron_oath",
        location_card={
            "location_id": "scene_waystation_of_iron_oath",
            "name": "铁誓驿站",
        },
        parent_chain=[],
        involved_characters=[
            {"character_id": "char_vellin", "summary": "驿站管事"},
        ],
        faction_clocks={},
    )
    return [
        Fixture(
            fixture_id="dialogue_t",
            graph_context=base_ctx,
            node_requirement=NodeRequirement(
                node_type="dialogue",
                expected_speaker_ref="char_vellin",
                narrative_intent="入口对白",
            ),
        ),
        Fixture(
            fixture_id="end_t",
            graph_context=base_ctx,
            node_requirement=NodeRequirement(
                node_type="end",
                expected_speaker_ref=None,
                narrative_intent="收尾",
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# experiment.run_experiment — happy path
# ---------------------------------------------------------------------------


def test_run_experiment_writes_results_and_summary(tmp_path):
    provider = _SuccessfulFakeProvider()
    batch_dir = run_experiment(
        batch_name="smoke",
        count=4,
        provider=provider,
        out_root=tmp_path,
        fixtures=_tiny_fixtures(),
        timestamp="20260425T000000Z",
        progress=False,
    )

    assert batch_dir == tmp_path / "20260425T000000Z_smoke"
    results_path = batch_dir / "results.jsonl"
    summary_path = batch_dir / "summary.txt"
    assert results_path.exists()
    assert summary_path.exists()

    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 4
    for i, row in enumerate(rows):
        # Envelope shape contract used by review_cli + metrics.
        assert row["iter_id"] == i
        assert row["fixture_id"] in {"dialogue_t", "end_t"}
        assert "fixture" in row and "graph_context" in row["fixture"]
        assert "result" in row
        assert row["result"]["success"] is True
        assert row["result"]["node"] is not None
        assert isinstance(row["result"]["attempts"], list)
        assert row["result"]["total_cost_usd"] > 0
        assert "generated_at" in row

    # Round-robin sampling: with 4 iterations and 2 fixtures we expect 2 each.
    fixture_ids = [r["fixture_id"] for r in rows]
    assert fixture_ids.count("dialogue_t") == 2
    assert fixture_ids.count("end_t") == 2

    summary = summary_path.read_text(encoding="utf-8")
    assert "schema_pass_rate" in summary
    assert "100.0%" in summary
    assert "failure_reason_distribution" in summary


def test_run_experiment_stops_on_budget_exceeded(tmp_path, monkeypatch):
    # Drop the per-call cap below the FakeProvider's 0.005 estimate so the
    # very first iteration trips BudgetExceeded inside generate_node.
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.0001")

    provider = _BudgetExceededFakeProvider()
    batch_dir = run_experiment(
        batch_name="budget",
        count=10,
        provider=provider,
        out_root=tmp_path,
        fixtures=_tiny_fixtures(),
        timestamp="20260425T010000Z",
        progress=False,
    )

    rows = [
        json.loads(line)
        for line in (batch_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # We requested 10, but the first iteration's failure short-circuits.
    assert len(rows) == 1
    assert rows[0]["result"]["success"] is False
    assert rows[0]["result"]["failure_reason"] == "budget_exceeded"

    summary = (batch_dir / "summary.txt").read_text(encoding="utf-8")
    assert "stopped early" in summary
    assert "budget_exceeded" in summary


# ---------------------------------------------------------------------------
# review_cli — non-interactive via scripted input
# ---------------------------------------------------------------------------


def _seed_batch_with_results(batch_dir: Path, envelopes: list[dict]) -> None:
    batch_dir.mkdir(parents=True, exist_ok=True)
    with open(batch_dir / "results.jsonl", "w", encoding="utf-8") as fh:
        for env in envelopes:
            fh.write(json.dumps(env, ensure_ascii=False) + "\n")


def _envelope(iter_id: int, *, success: bool, fixture_id: str = "dialogue_t",
              failure_reason: str | None = None, node: dict | None = None,
              cost: float = 0.01) -> dict:
    return {
        "iter_id": iter_id,
        "fixture_id": fixture_id,
        "fixture": {
            "graph_context": {
                "scene_anchor": "scene_waystation_of_iron_oath",
                "location_card": {"name": "铁誓驿站"},
                "parent_chain": [],
                "involved_characters": [{"character_id": "char_vellin"}],
                "faction_clocks": {},
            },
            "node_requirement": {
                "node_type": "dialogue",
                "expected_speaker_ref": "char_vellin",
                "narrative_intent": "test",
            },
        },
        "result": {
            "success": success,
            "node": node if node is not None else (
                _valid_dialogue_node() if success else None
            ),
            "failure_reason": failure_reason,
            "attempts": [],
            "total_cost_usd": cost,
        },
        "generated_at": "2026-04-25T00:00:00+00:00",
    }


def _scripted_input(answers: list[str]):
    """Build an input function that returns answers in order; raises on overflow."""
    queue = list(answers)

    def _read(prompt: str) -> str:
        if not queue:
            raise EOFError("scripted input exhausted")
        return queue.pop(0)

    return _read


def test_review_cli_records_accept_reject_skip(tmp_path):
    batch_dir = tmp_path / "batch1"
    envelopes = [
        _envelope(0, success=True),
        _envelope(1, success=True),
        _envelope(2, success=False, failure_reason="schema_invalid"),  # filtered
        _envelope(3, success=True),
    ]
    _seed_batch_with_results(batch_dir, envelopes)

    # Three successful rows → three prompts. iter 0 accept, iter 1 reject
    # with a reason, iter 3 skip.
    answers = [
        "a",                     # iter 0: accept
        "r", "对白突兀",         # iter 1: reject + reason
        "s",                     # iter 3: skip (no log entry)
    ]
    out = io.StringIO()
    written = review_cli.run_review(
        batch_dir, input_fn=_scripted_input(answers), output=out
    )

    assert written == 2
    log_lines = (batch_dir / "review_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 2

    rec0 = json.loads(log_lines[0])
    assert rec0["iter_id"] == 0
    assert rec0["accepted"] is True
    assert rec0["reason"] is None
    assert rec0["schema_pass"] is True

    rec1 = json.loads(log_lines[1])
    assert rec1["iter_id"] == 1
    assert rec1["accepted"] is False
    assert rec1["reason"] == "对白突兀"


def test_review_cli_resumes_skipping_already_reviewed(tmp_path):
    batch_dir = tmp_path / "batch2"
    envelopes = [_envelope(i, success=True) for i in range(3)]
    _seed_batch_with_results(batch_dir, envelopes)

    # Pre-seed: iter 0 already accepted in a prior session.
    (batch_dir / "review_log.jsonl").write_text(
        json.dumps({
            "iter_id": 0,
            "node_id_or_idx": "arrival_waystation",
            "schema_pass": True,
            "accepted": True,
            "reason": None,
            "reviewed_at": "2026-04-24T00:00:00+00:00",
        }) + "\n",
        encoding="utf-8",
    )

    # Resume: only iter 1 and iter 2 should be prompted.
    answers = ["a", "a"]
    out = io.StringIO()
    written = review_cli.run_review(
        batch_dir, input_fn=_scripted_input(answers), output=out
    )

    assert written == 2  # iter 1 and iter 2
    log_lines = (batch_dir / "review_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 3  # 1 pre-existing + 2 new
    iter_ids = [json.loads(l)["iter_id"] for l in log_lines]
    assert iter_ids == [0, 1, 2]


def test_review_cli_invalid_input_re_prompts(tmp_path):
    batch_dir = tmp_path / "batch3"
    _seed_batch_with_results(batch_dir, [_envelope(0, success=True)])

    answers = ["x", "huh", "a"]  # two garbage answers, then accept
    out = io.StringIO()
    written = review_cli.run_review(
        batch_dir, input_fn=_scripted_input(answers), output=out
    )

    assert written == 1


# ---------------------------------------------------------------------------
# metrics.compute_metrics
# ---------------------------------------------------------------------------


def test_metrics_basic_pass_rate_and_cost(tmp_path):
    batch_dir = tmp_path / "metrics_basic"
    envelopes = [
        _envelope(0, success=True, cost=0.01),
        _envelope(1, success=True, cost=0.02),
        _envelope(2, success=False, failure_reason="schema_invalid", cost=0.03),
        _envelope(3, success=False, failure_reason="provider_error", cost=0.0),
    ]
    _seed_batch_with_results(batch_dir, envelopes)

    m = metrics.compute_metrics(batch_dir)

    assert m["total_iterations"] == 4
    assert m["total_attempts"] == 4
    assert m["schema_pass_rate"] == 0.5
    assert m["mean_cost_per_attempt"] == pytest.approx(0.015)
    assert m["total_cost_usd"] == pytest.approx(0.06)
    assert m["failure_reason_distribution"] == {
        "schema_invalid": 1,
        "provider_error": 1,
    }
    # No review log seeded → review keys absent.
    assert "acceptance_rate" not in m
    assert "reject_reason_top_5" not in m


def test_metrics_with_review_log(tmp_path):
    batch_dir = tmp_path / "metrics_review"
    envelopes = [_envelope(i, success=True) for i in range(5)]
    _seed_batch_with_results(batch_dir, envelopes)

    review_records = [
        {"iter_id": 0, "schema_pass": True, "accepted": True,  "reason": None,
         "reviewed_at": "2026-04-25T00:00:00+00:00"},
        {"iter_id": 1, "schema_pass": True, "accepted": False, "reason": "对白突兀",
         "reviewed_at": "2026-04-25T00:00:01+00:00"},
        {"iter_id": 2, "schema_pass": True, "accepted": False, "reason": "对白突兀",
         "reviewed_at": "2026-04-25T00:00:02+00:00"},
        {"iter_id": 3, "schema_pass": True, "accepted": True,  "reason": None,
         "reviewed_at": "2026-04-25T00:00:03+00:00"},
        {"iter_id": 4, "schema_pass": True, "accepted": False, "reason": "选项重复",
         "reviewed_at": "2026-04-25T00:00:04+00:00"},
    ]
    with open(batch_dir / "review_log.jsonl", "w", encoding="utf-8") as fh:
        for r in review_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    m = metrics.compute_metrics(batch_dir)
    assert m["reviewed_count"] == 5
    assert m["acceptance_rate"] == pytest.approx(2 / 5)
    # top-5 reject reasons, ordered by count desc.
    assert m["reject_reason_top_5"][0] == ("对白突兀", 2)
    reasons = dict(m["reject_reason_top_5"])
    assert reasons["选项重复"] == 1


def test_metrics_empty_batch_returns_none_rates(tmp_path):
    batch_dir = tmp_path / "metrics_empty"
    _seed_batch_with_results(batch_dir, [])

    m = metrics.compute_metrics(batch_dir)
    assert m["total_iterations"] == 0
    assert m["schema_pass_rate"] is None
    assert m["mean_cost_per_attempt"] is None
    assert m["failure_reason_distribution"] == {}
