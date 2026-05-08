"""T-2.8 §5 smoke tests: scene_ai_judge runner.

FakeProvider only — never hits real API (per task spec). Verifies:

  * pass1 lenient + pass2 strict are both invoked per success scene
  * AI_JUDGE_REPORT.{md,json} are written with the expected sections
  * weakest_dimensions surface the lowest-mean dimensions
  * BudgetExceeded mid-batch triggers stopped_early + partial flush

T-3.0 R3.0 additions:
  * dimensions schema now requires the 10 explicit S1..S10 keys so the
    OpenAPI sanitizer doesn't silently zero them out (baseline_007–011
    "(no dimensions returned)" finding); a 10-field response round-trips
    intact and a partial response logs a warning + records what it got.
"""
from __future__ import annotations

import json
import logging
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


# ---------------------------------------------------------------------------
# R3.0 — explicit S1..S10 dimensions schema (T-3.0)
# ---------------------------------------------------------------------------


def test_judge_response_schema_declares_explicit_s1_to_s10_dimensions():
    """The dimensions sub-schema must list every S1..S10 key as an
    integer 0/1/2. The OpenAPI sanitizer drops `additionalProperties`,
    so without explicit `properties` Gemini emits `dimensions: {}` —
    that's the baseline_007–011 "(no dimensions returned)" failure
    mode. Pin the list so a future refactor can't regress to the loose
    shape."""
    schema = scene_ai_judge._JUDGE_RESPONSE_SCHEMA
    dims_schema = schema["properties"]["dimensions"]

    assert set(dims_schema["required"]) == set(scene_ai_judge._SCENE_DIMENSION_KEYS)
    assert set(dims_schema["properties"].keys()) == set(
        scene_ai_judge._SCENE_DIMENSION_KEYS
    )
    for key in scene_ai_judge._SCENE_DIMENSION_KEYS:
        prop = dims_schema["properties"][key]
        assert prop["type"] == "integer"
        assert prop["minimum"] == 0
        assert prop["maximum"] == 2
    assert "additionalProperties" not in dims_schema, (
        "additionalProperties is stripped by providers/_schema_sanitizer.py "
        "before the schema reaches Gemini; rely on explicit `properties` "
        "instead so the sanitizer can't zero out the dimensions dict."
    )


def test_record_pass_round_trips_full_s1_to_s10_response(tmp_path):
    """The runner must accept a 10-field S1..S10 response unchanged.

    Retro check for the baseline_011 failure: rationales were populated,
    advisory was set, but `dimensions` came back empty. After R3.0 the
    schema asks Gemini for these 10 keys explicitly — feeding the
    runner a "good" response (what the prompt asks the model to emit)
    must land all 10 keys in the report, not silently drop them.
    """
    batch_dir = _seed_batch(tmp_path / "batch", [_envelope(0, "s_full")])
    template_path = _write_template(tmp_path)
    full_dims = {key: 2 for key in scene_ai_judge._SCENE_DIMENSION_KEYS}
    full_dims["S4_decision"] = 1  # at least one borderline so weakest != []
    script = [
        _make_response({
            "scene_id": "s_full",
            "dimensions": dict(full_dims),
            "advisory": "accept",
            "rationale": "lenient: all good",
        }),
        _make_response({
            "scene_id": "s_full",
            "dimensions": dict(full_dims),
            "advisory": "accept",
            "rationale": "strict: all good",
        }),
    ]
    provider = _ScriptedJudgeProvider(script)

    report = scene_ai_judge.run_scene_ai_judge(
        batch_dir=batch_dir,
        provider=provider,
        prompt_template_path=template_path,
        progress=False,
    )
    assert set(report.pass2_strict_scores["s_full"].keys()) == set(
        scene_ai_judge._SCENE_DIMENSION_KEYS
    )
    # Total = 9*2 + 1 (S4) = 19, which advisory rule maps to "accept".
    assert sum(report.pass2_strict_scores["s_full"].values()) == 19
    assert report.advisory_recommendation["s_full"] == "accept"


def test_record_pass_logs_warning_on_partial_dimensions(tmp_path, caplog):
    """If the model returns fewer than 10 dimensions (provider regression
    or prompt drift), the runner must log a warning instead of silently
    storing whatever scraps came back. Caplog asserts the WARNING fires
    with the missing key list — that's the diagnostic that turns a
    silent-zero failure mode into something a future debugger can find.
    """
    batch_dir = _seed_batch(tmp_path / "batch", [_envelope(0, "s_partial")])
    template_path = _write_template(tmp_path)
    # Two of the ten keys present; the rest missing.
    script = [
        _make_response({
            "scene_id": "s_partial",
            "dimensions": {"S1_topology": 2, "S2_pacing": 1},
            "advisory": "marginal",
            "rationale": "partial dim regression",
        }),
        _make_response({
            "scene_id": "s_partial",
            "dimensions": {"S1_topology": 2, "S2_pacing": 1},
            "advisory": "marginal",
            "rationale": "partial dim regression",
        }),
    ]
    provider = _ScriptedJudgeProvider(script)

    with caplog.at_level(logging.WARNING, logger="generator.scene_ai_judge"):
        scene_ai_judge.run_scene_ai_judge(
            batch_dir=batch_dir,
            provider=provider,
            prompt_template_path=template_path,
            progress=False,
        )
    # The warning fires once per pass per scene = 2 records.
    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "missing" in r.getMessage()
    ]
    assert len(warning_records) == 2
    sample = warning_records[0].getMessage()
    assert "s_partial" in sample
    assert "S10_naming" in sample  # one of the 8 missing keys


def test_render_user_prompt_substitutes_judge_context(tmp_path):
    """B-review 4.1 (T-3.0 C): the rendered prompt must carry the
    envelope's ``judge_context`` JSON so the model can ground S7-S9
    against the ontology snapshot. Pin both the placeholder name and
    the JSON shape so a refactor can't quietly drop the field."""
    env = _envelope(0, "s_ctx")
    env["judge_context"] = {
        "character_cards": [
            {
                "id": "char_vellin",
                "display_name": "Vellin",
                "dramatic_triggers": [{"trait": "stoic", "when": "X", "how": "Y"}],
            }
        ],
        "location_card": {"id": "scene_x", "display_name": "Iron Oath"},
        "active_clocks": [{"id": "pressure", "ticks_filled": 4, "ticks_total": 6}],
        "system_time": {"scene_count": 3, "long_rest_count": 1},
    }
    template = (
        "scene: {{SCENE_ID}}\npass: {{PASS_MODE}}\n\n"
        "context:\n{{JUDGE_CONTEXT}}\n"
    )
    rendered = scene_ai_judge._render_user_prompt(
        template, scene_id="s_ctx", pass_mode="strict", env=env
    )
    # Placeholder consumed.
    assert "{{JUDGE_CONTEXT}}" not in rendered
    # Character / location / clocks / system_time all present in payload.
    assert "char_vellin" in rendered
    assert "Iron Oath" in rendered
    assert "ticks_filled" in rendered
    assert '"scene_count": 3' in rendered


def test_render_user_prompt_judge_context_falls_back_to_empty_object(tmp_path):
    """Legacy envelopes (pre-judge_context) — substitution must still
    fire with ``{}`` so the prompt template doesn't end up with a
    literal ``{{JUDGE_CONTEXT}}`` token reaching the LLM."""
    env = _envelope(0, "s_legacy")
    # No judge_context key at all — older baseline_NNN envelopes.
    assert "judge_context" not in env
    template = "ctx: {{JUDGE_CONTEXT}}"
    rendered = scene_ai_judge._render_user_prompt(
        template, scene_id="s_legacy", pass_mode="strict", env=env
    )
    assert "{{JUDGE_CONTEXT}}" not in rendered
    assert "ctx: {}" in rendered


def test_judge_scene_envelope_returns_parsed_content_and_cost(tmp_path):
    """The new public wrapper for one-shot judging is what
    `judge_calibration` uses to score a hand-picked scene set without
    replaying the whole batch loop. Pin the (content, cost) shape so
    R3.3 and any future caller has a stable contract.
    """
    template_path = _write_template(tmp_path)
    template_text = template_path.read_text(encoding="utf-8")
    env = _envelope(0, "s_solo")
    script = [
        _make_response({
            "scene_id": "s_solo",
            "dimensions": {key: 2 for key in scene_ai_judge._SCENE_DIMENSION_KEYS},
            "advisory": "accept",
            "rationale": "single-shot judge",
        }),
    ]
    provider = _ScriptedJudgeProvider(script)
    content, cost = scene_ai_judge.judge_scene_envelope(
        env,
        pass_mode="strict",
        provider=provider,
        template_text=template_text,
    )
    assert content["scene_id"] == "s_solo"
    assert content["advisory"] == "accept"
    assert set(content["dimensions"].keys()) == set(
        scene_ai_judge._SCENE_DIMENSION_KEYS
    )
    assert cost > 0  # FakeProvider.estimate_cost = 0.005
