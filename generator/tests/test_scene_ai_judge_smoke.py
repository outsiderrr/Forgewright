"""T-2.8 §5 smoke tests: scene_ai_judge runner.

FakeProvider only — never hits real API (per task spec). Verifies:

  * pass1 lenient + pass2 strict are both invoked per success scene
  * AI_JUDGE_REPORT.{md,json} are written with the expected sections
  * weakest_dimensions surface the lowest-mean dimensions
  * BudgetExceeded mid-batch triggers stopped_early + partial flush
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator import scene_ai_judge
from generator.budget import BudgetExceeded
from generator.llm_provider import StructuredResponse


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _envelope(iter_id: int, scene_id: str = "s0") -> dict:
    """A minimum success envelope shaped like scene_experiment writes."""
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
            "success": True,
            "failure_reason": None,
            "graph": {
                "schema_version": "0.1.1",
                "graph_id": scene_id,
                "entry_node_id": "n_arrival",
                "scene_anchor": "scene_waystation_of_iron_oath",
                "character_refs": ["char_vellin"],
                "nodes": {
                    "n_arrival": {
                        "node_id": "n_arrival", "type": "dialogue",
                        "narration": "...", "speaker_ref": "char_vellin",
                        "options": [],
                    }
                },
            },
            "total_cost_usd": 0.05,
        },
        "validator_summaries": None,
        "generated_at": "2026-05-04T00:00:00+00:00",
    }


def _seed_batch(batch_dir: Path, envelopes: list[dict]) -> Path:
    batch_dir.mkdir(parents=True, exist_ok=True)
    with open(batch_dir / "scene_results.jsonl", "w", encoding="utf-8") as fh:
        for env in envelopes:
            fh.write(json.dumps(env, ensure_ascii=False) + "\n")
    return batch_dir


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content, raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=300, output_tokens=200,
        model_id="fake-model", finish_reason="STOP",
    )


class _ScriptedJudgeProvider:
    """Cycles through a fixed list of judge responses."""

    model_id = "fake-model"

    def __init__(self, script: list[StructuredResponse]):
        self._script = script
        self._idx = 0
        self.call_count = 0
        self.observed_pass_modes: list[str] = []

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        # Surface the pass_mode the runner injected via {{PASS_MODE}}
        # so tests can assert pass1 + pass2 both ran.
        if "lenient" in user_prompt:
            self.observed_pass_modes.append("lenient")
        elif "strict" in user_prompt:
            self.observed_pass_modes.append("strict")
        if self._idx >= len(self._script):
            raise AssertionError("scripted provider exhausted")
        resp = self._script[self._idx]
        self._idx += 1
        return resp

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.005


_TEMPLATE = """# AI judge prompt (test stub)

scene_id: {{SCENE_ID}}
pass_mode: {{PASS_MODE}}
target_beats: {{TARGET_BEATS}}
participating_npcs: {{PARTICIPATING_NPCS}}
scene_anchor: {{SCENE_ANCHOR}}

scene_json:
{{SCENE_JSON}}
"""


def _write_template(tmp_path: Path) -> Path:
    p = tmp_path / "judge_template.md"
    p.write_text(_TEMPLATE, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path: 1 scene → 2 calls → report contains both passes
# ---------------------------------------------------------------------------


def test_scene_ai_judge_runs_both_passes_and_writes_report(tmp_path):
    batch_dir = _seed_batch(tmp_path / "batch", [_envelope(0, "s_alpha")])
    template_path = _write_template(tmp_path)

    script = [
        _make_response({
            "scene_id": "s_alpha",
            "dimensions": {"D1": 2, "D2": 1, "D3": 2},
            "advisory": "accept",
            "rationale": "lenient says ok",
        }),
        _make_response({
            "scene_id": "s_alpha",
            "dimensions": {"D1": 1, "D2": 0, "D3": 2},
            "advisory": "marginal",
            "rationale": "strict drops D2",
        }),
    ]
    provider = _ScriptedJudgeProvider(script)

    report = scene_ai_judge.run_scene_ai_judge(
        batch_dir=batch_dir,
        provider=provider,
        prompt_template_path=template_path,
        progress=False,
    )

    assert provider.call_count == 2
    assert provider.observed_pass_modes == ["lenient", "strict"]

    assert report.pass1_lenient_scores == {"s_alpha": {"D1": 2.0, "D2": 1.0, "D3": 2.0}}
    assert report.pass2_strict_scores == {"s_alpha": {"D1": 1.0, "D2": 0.0, "D3": 2.0}}
    assert report.advisory_recommendation == {"s_alpha": "marginal"}
    # Strict-pass averages: D2=0.0, D1=1.0, D3=2.0 → weakest first.
    assert report.weakest_dimensions[0] == ("D2", 0.0)
    assert not report.stopped_early

    md_path = batch_dir / "AI_JUDGE_REPORT.md"
    json_path = batch_dir / "AI_JUDGE_REPORT.json"
    assert md_path.exists() and json_path.exists()

    md = md_path.read_text(encoding="utf-8")
    assert "AI Judge Report" in md
    assert "s_alpha" in md
    assert "Authority note (ADR-020 §6)" in md  # advisory ≠ acceptance
    assert "Weakest dimensions" in md

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["advisory_recommendation"]["s_alpha"] == "marginal"
    assert ("D2", 0.0) in [tuple(x) for x in payload["weakest_dimensions"]]
    # Review 4.3: machine-readable non-binding disclaimer must be on the
    # JSON so T-2.12 / future programmatic consumers can verify the
    # advisory authority without parsing the markdown narrative.
    metadata = payload.get("metadata") or {}
    assert metadata.get("advisory_authority") == "informational_only"
    assert metadata.get("acceptance_source") == "scene_review_cli_author_A_R"
    assert "ADR-020" in (metadata.get("adr") or "")


# ---------------------------------------------------------------------------
# BudgetExceeded mid-batch: stopped_early=True, report still flushed
# ---------------------------------------------------------------------------


def test_scene_ai_judge_handles_budget_exceeded_mid_batch(tmp_path, monkeypatch):
    batch_dir = _seed_batch(
        tmp_path / "batch",
        [_envelope(0, "s_first"), _envelope(1, "s_second")],
    )
    template_path = _write_template(tmp_path)

    # Drop the per-call cap below the FakeProvider's $0.005 estimate so
    # the very first judge call trips BudgetExceeded.
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.0001")

    provider = _ScriptedJudgeProvider([])  # no calls should land
    report = scene_ai_judge.run_scene_ai_judge(
        batch_dir=batch_dir,
        provider=provider,
        prompt_template_path=template_path,
        progress=False,
    )
    assert report.stopped_early is True
    # No successful pass recorded.
    assert report.pass1_lenient_scores == {}
    assert report.pass2_strict_scores == {}
    # Report still flushed for whatever was scored.
    assert (batch_dir / "AI_JUDGE_REPORT.md").exists()
    assert (batch_dir / "AI_JUDGE_REPORT.json").exists()


# ---------------------------------------------------------------------------
# Missing template → FileNotFoundError, no API calls made
# ---------------------------------------------------------------------------


def test_scene_ai_judge_missing_template_raises(tmp_path):
    batch_dir = _seed_batch(tmp_path / "batch", [_envelope(0)])
    provider = _ScriptedJudgeProvider([])
    with pytest.raises(FileNotFoundError):
        scene_ai_judge.run_scene_ai_judge(
            batch_dir=batch_dir,
            provider=provider,
            prompt_template_path=tmp_path / "missing_template.md",
            progress=False,
        )
    assert provider.call_count == 0
