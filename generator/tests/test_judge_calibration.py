"""T-3.0 R3.3 / F18: judge_calibration mini-calibration runner.

Mocks 3 scenes + scripted judge responses + author labels and walks the
runner end-to-end. Verifies the disagreement_report.md has the expected
buckets:

  * agree (judge ≡ author)
  * disagree_judge_lenient (judge accept, author reject)
  * disagree_judge_strict (judge reject, author accept)
  * marginal_vs_A / marginal_vs_R (judge waffles)
  * no_author_label (author hasn't reviewed yet)
  * scene_not_found (scene_id not in scene_results.jsonl)

FakeProvider only — no real API calls.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator import judge_calibration
from generator.llm_provider import StructuredResponse


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    """Identical to scene_ai_judge tests: keep budget log per-test."""
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=300,
        output_tokens=200,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _ScriptedJudgeProvider:
    """Cycles through canned judge responses (one per scene)."""

    model_id = "fake-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0
        self.call_count = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        if self._idx >= len(self._responses):
            raise AssertionError(
                f"scripted provider exhausted at call {self.call_count}"
            )
        item = self._responses[self._idx]
        self._idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.005


def _envelope(scene_id: str, *, iter_id: int = 0, success: bool = True) -> dict:
    """Minimum success envelope shaped like scene_experiment writes."""
    return {
        "iter_id": iter_id,
        "fixture_id": "iron_oath_smoke",
        "fixture": {
            "scene_setting": {
                "scene_anchor": "scene_waystation_of_iron_oath",
                "primary_location_ref": "scene_waystation_of_iron_oath",
                "chapter_ref": None,
                "expected_node_count_min": 5,
                "expected_node_count_max": 12,
            },
            "target_beats": ["抵达", "结局"],
            "participating_npcs": ["char_vellin"],
        },
        "result": {
            "success": success,
            "failure_reason": None,
            "graph": {
                "schema_version": "0.1.1",
                "graph_id": scene_id,
                "entry_node_id": "n_arrival",
                "scene_anchor": "scene_waystation_of_iron_oath",
                "character_refs": ["char_vellin"],
                "nodes": {
                    "n_arrival": {
                        "node_id": "n_arrival",
                        "type": "dialogue",
                        "narration": "...",
                        "speaker_ref": "char_vellin",
                        "options": [],
                    }
                },
            },
            "total_cost_usd": 0.05,
        },
        "validator_summaries": None,
        "generated_at": "2026-05-04T00:00:00+00:00",
    }


def _seed_baseline(
    batch_dir: Path,
    *,
    envelopes: list[dict],
    review_records: list[dict] | None = None,
) -> Path:
    """Hand-build scene_results.jsonl + (optional) scene_review_log.jsonl."""
    batch_dir.mkdir(parents=True, exist_ok=True)
    with open(batch_dir / "scene_results.jsonl", "w", encoding="utf-8") as fh:
        for env in envelopes:
            fh.write(json.dumps(env, ensure_ascii=False) + "\n")
    if review_records is not None:
        with open(
            batch_dir / "scene_review_log.jsonl", "w", encoding="utf-8"
        ) as fh:
            for rec in review_records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return batch_dir


def _judge_response(
    scene_id: str,
    *,
    advisory: str,
    dim_score: int = 2,
    rationale: str = "rationale stub",
) -> StructuredResponse:
    """Build a canonical 10-dim S1..S10 judge response."""
    dims = {
        "S1_topology": dim_score,
        "S2_pacing": dim_score,
        "S3_arc": dim_score,
        "S4_decision": dim_score,
        "S5_closure": dim_score,
        "S6_length": dim_score,
        "S7_context": dim_score,
        "S8_relations": dim_score,
        "S9_clocks": dim_score,
        "S10_naming": dim_score,
    }
    return _make_response({
        "scene_id": scene_id,
        "dimensions": dims,
        "advisory": advisory,
        "rationale": rationale,
    })


# Static template stub matching scene_ai_judge's substitution keys.
_TEMPLATE_TEXT = (
    "scene_id: {{SCENE_ID}}\n"
    "pass_mode: {{PASS_MODE}}\n"
    "scene_anchor: {{SCENE_ANCHOR}}\n"
    "scene_json: {{SCENE_JSON}}\n"
)


# ---------------------------------------------------------------------------
# Decision-mapping unit tests (cheap; no provider involved)
# ---------------------------------------------------------------------------


def test_classify_agreement_buckets_pin():
    """The bucket names are surfaced in the markdown report and tests
    assert against them — pin the mapping so a refactor can't quietly
    rename a category and break the report contract."""
    classify = judge_calibration._classify_agreement
    assert classify("A", "A") == "agree"
    assert classify("R", "R") == "agree"
    assert classify("A", "R") == "disagree_judge_strict"
    assert classify("R", "A") == "disagree_judge_lenient"
    assert classify("A", "M") == "marginal_vs_A"
    assert classify("R", "M") == "marginal_vs_R"
    assert classify("S", "A") == "no_author_label"
    assert classify("missing", "A") == "no_author_label"
    assert classify("A", "missing") == "no_ai_advisory"


def test_author_decision_maps_review_log_row():
    """`accepted=True/False/None` → `A/R/S`."""
    assert judge_calibration._author_decision(
        {"accepted": True, "reason": None}
    ) == ("A", None)
    assert judge_calibration._author_decision(
        {"accepted": False, "reason": "节奏拖沓"}
    ) == ("R", "节奏拖沓")
    assert judge_calibration._author_decision(
        {"accepted": None, "reason": None}
    ) == ("S", None)
    assert judge_calibration._author_decision(None) == ("missing", None)


def test_ai_decision_from_advisory_pins_mapping():
    f = judge_calibration._ai_decision_from_advisory
    assert f("accept") == "A"
    assert f("reject") == "R"
    assert f("marginal") == "M"
    assert f(None) == "missing"
    assert f("unknown_value") == "missing"


# ---------------------------------------------------------------------------
# End-to-end runner tests
# ---------------------------------------------------------------------------


def test_runner_produces_report_with_three_scene_buckets(tmp_path):
    """Three scenes covering three buckets: agree, disagree_lenient, marginal.

    Pins the markdown report contract — header, summary counts, table,
    and the "How to read" guide must all surface."""
    batch_dir = _seed_baseline(
        tmp_path / "20260506T000000Z_baseline_test",
        envelopes=[
            _envelope("scene_a", iter_id=0),  # author A, ai accept   → agree
            _envelope("scene_b", iter_id=1),  # author R, ai accept   → lenient
            _envelope("scene_c", iter_id=2),  # author A, ai marginal → marginal_vs_A
        ],
        review_records=[
            {
                "iter_id": 0,
                "scene_id": "scene_a",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-04T00:00:00+00:00",
            },
            {
                "iter_id": 1,
                "scene_id": "scene_b",
                "accepted": False,
                "reason": "节奏拖沓",
                "reviewed_at": "2026-05-04T00:01:00+00:00",
            },
            {
                "iter_id": 2,
                "scene_id": "scene_c",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-04T00:02:00+00:00",
            },
        ],
    )
    provider = _ScriptedJudgeProvider([
        _judge_response("scene_a", advisory="accept", dim_score=2),
        _judge_response("scene_b", advisory="accept", dim_score=2),
        _judge_response("scene_c", advisory="marginal", dim_score=1),
    ])
    report_path = batch_dir / "judge_calibration_report.md"

    md, rows = judge_calibration.run_judge_calibration(
        baseline_dir=batch_dir,
        scene_ids=["scene_a", "scene_b", "scene_c"],
        provider=provider,
        template_text=_TEMPLATE_TEXT,
        report_path=report_path,
        progress=False,
    )

    assert provider.call_count == 3
    assert report_path.exists()

    # Row-level assertions.
    assert [r.scene_id for r in rows] == ["scene_a", "scene_b", "scene_c"]
    assert rows[0].agreement == "agree"
    assert rows[0].author_decision == "A"
    assert rows[0].ai_advisory == "accept"
    assert rows[0].ai_total == 20.0  # 10 dims × 2

    assert rows[1].agreement == "disagree_judge_lenient"
    assert rows[1].author_decision == "R"
    assert rows[1].author_reason == "节奏拖沓"

    assert rows[2].agreement == "marginal_vs_A"
    assert rows[2].ai_advisory == "marginal"
    assert rows[2].ai_total == 10.0  # 10 dims × 1

    # Markdown contract — header, summary lines, table headers, guide.
    assert "# Judge calibration report" in md
    assert "T-3.0 R3.3 / F18" in md
    assert "scenes calibrated:               3" in md
    assert "agree (judge ≡ author):          1" in md
    assert "disagree (judge too lenient):    1" in md
    assert "judge marginal:                  1" in md
    # Table row sample.
    assert "scene_a" in md
    assert "scene_b" in md
    assert "scene_c" in md
    assert "节奏拖沓" in md  # author reason carried through
    # "How to read" guide.
    assert "disagree_judge_lenient" in md
    assert "disagree_judge_strict" in md


def test_runner_records_no_author_label_when_review_log_missing(tmp_path):
    """Author hasn't run scene_review_cli yet — runner should record
    every scene as ``no_author_label`` and not crash."""
    batch_dir = _seed_baseline(
        tmp_path / "20260506T010000Z_baseline_test",
        envelopes=[_envelope("scene_x")],
        review_records=None,  # no scene_review_log.jsonl
    )
    provider = _ScriptedJudgeProvider([
        _judge_response("scene_x", advisory="accept"),
    ])
    md, rows = judge_calibration.run_judge_calibration(
        baseline_dir=batch_dir,
        scene_ids=["scene_x"],
        provider=provider,
        template_text=_TEMPLATE_TEXT,
        report_path=batch_dir / "report.md",
        progress=False,
    )
    assert rows[0].agreement == "no_author_label"
    assert rows[0].author_decision == "missing"
    assert rows[0].ai_advisory == "accept"
    assert "no_author_label" in md


def test_runner_records_scene_not_found_for_unknown_scene_id(tmp_path):
    """If the author asks for a scene_id not in scene_results.jsonl, the
    runner records ``scene_not_found`` instead of crashing."""
    batch_dir = _seed_baseline(
        tmp_path / "20260506T020000Z_baseline_test",
        envelopes=[_envelope("scene_real")],
        review_records=[],
    )
    # No provider calls expected since the scene isn't in the batch.
    provider = _ScriptedJudgeProvider([])
    _, rows = judge_calibration.run_judge_calibration(
        baseline_dir=batch_dir,
        scene_ids=["scene_does_not_exist"],
        provider=provider,
        template_text=_TEMPLATE_TEXT,
        report_path=batch_dir / "report.md",
        progress=False,
    )
    assert provider.call_count == 0
    assert len(rows) == 1
    assert rows[0].agreement == "scene_not_found"
    assert rows[0].ai_advisory is None


def test_runner_continues_after_provider_error_on_one_scene(tmp_path):
    """A ProviderError on one scene must record ``provider_error`` and
    let the loop continue to the next scene — calibration is best-effort
    per-scene, not all-or-nothing."""
    from generator.llm_provider import ProviderError

    batch_dir = _seed_baseline(
        tmp_path / "20260506T030000Z_baseline_test",
        envelopes=[
            _envelope("scene_p", iter_id=0),
            _envelope("scene_q", iter_id=1),
        ],
        review_records=[
            {
                "iter_id": 0,
                "scene_id": "scene_p",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-04T00:00:00+00:00",
            },
            {
                "iter_id": 1,
                "scene_id": "scene_q",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-04T00:01:00+00:00",
            },
        ],
    )
    provider = _ScriptedJudgeProvider([
        ProviderError("upstream timeout"),
        _judge_response("scene_q", advisory="accept"),
    ])
    _, rows = judge_calibration.run_judge_calibration(
        baseline_dir=batch_dir,
        scene_ids=["scene_p", "scene_q"],
        provider=provider,
        template_text=_TEMPLATE_TEXT,
        report_path=batch_dir / "report.md",
        progress=False,
    )
    assert rows[0].agreement == "provider_error"
    assert rows[0].ai_advisory is None
    assert rows[1].agreement == "agree"
    assert rows[1].ai_advisory == "accept"


def test_runner_stops_on_budget_exceeded_mid_run(tmp_path, monkeypatch):
    """BudgetExceeded must short-circuit the loop and still flush the
    report with a ``stopped early`` marker — same convention as
    scene_ai_judge."""
    batch_dir = _seed_baseline(
        tmp_path / "20260506T040000Z_baseline_test",
        envelopes=[
            _envelope("scene_first", iter_id=0),
            _envelope("scene_second", iter_id=1),
        ],
        review_records=[],
    )
    # Drop per-call cap so the very first judge call trips BudgetExceeded.
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.0001")
    provider = _ScriptedJudgeProvider([])  # no calls expected
    md, rows = judge_calibration.run_judge_calibration(
        baseline_dir=batch_dir,
        scene_ids=["scene_first", "scene_second"],
        provider=provider,
        template_text=_TEMPLATE_TEXT,
        report_path=batch_dir / "report.md",
        progress=False,
    )
    assert provider.call_count == 0
    # Only the first scene gets a row (loop breaks on BudgetExceeded).
    assert len(rows) == 1
    assert rows[0].agreement == "budget_exceeded"
    assert "stopped early" in md.lower()


def test_runner_raises_when_scene_results_missing(tmp_path):
    """An empty baseline-dir is a setup error, not a per-scene one —
    surface ``FileNotFoundError`` so the CLI returns non-zero before
    any provider call."""
    empty_dir = tmp_path / "no_results_here"
    empty_dir.mkdir()
    provider = _ScriptedJudgeProvider([])
    with pytest.raises(FileNotFoundError):
        judge_calibration.run_judge_calibration(
            baseline_dir=empty_dir,
            scene_ids=["any"],
            provider=provider,
            template_text=_TEMPLATE_TEXT,
            report_path=empty_dir / "report.md",
            progress=False,
        )
