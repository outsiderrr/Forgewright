"""Judge tests (T-3.4 / ADR-022 P-5 + P-6)."""
from __future__ import annotations

import json

import pytest

from generator.llm_provider import ProviderError, StructuredResponse
from generator.playtest import judge as judge_mod
from generator.playtest.judge import (
    JUDGE_RESPONSE_SCHEMA,
    JUDGE_RUBRIC_VERSION,
    SceneAggregate,
    aggregate_scene_summary,
    build_judge_user_prompt,
    judge_path,
    rank_paths_worst_first,
    render_worst_scenes_json,
    render_worst_scenes_markdown,
)
from generator.playtest.personas import load_persona
from generator.playtest.runner import PathStep, PlaytestPath


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _structured(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=300,
        output_tokens=200,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _CannedJudgeProvider:
    model_id = "fake-judge"
    temperature = 0.4

    def __init__(self, response_or_exc):
        self._response_or_exc = response_or_exc
        self.calls = 0

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.calls += 1
        if isinstance(self._response_or_exc, BaseException):
            raise self._response_or_exc
        return _structured(self._response_or_exc)

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.002


def _example_path(*, persona_id="cautious", path_id="p1", reach=True) -> PlaytestPath:
    return PlaytestPath(
        path_id=path_id,
        persona_id=persona_id,
        scene_id="test_scene",
        steps=[
            PathStep(
                node_id="n_start",
                option_id=None,
                state_after={},
                valid_option_ids=[],
            ),
            PathStep(
                node_id="n_end_a",
                option_id="go_a",
                state_after={"flag": {"went_east": True}},
                valid_option_ids=["go_a", "go_b"],
                reasoning="I take the cautious option.",
            ),
        ],
        reached_end=reach,
        end_node_id="n_end_a" if reach else None,
        failure_reason=None,
        llm_calls=1,
        cost_usd=0.001,
        duration_seconds=1.0,
    )


# ---------------------------------------------------------------------------
# Schema + prompt
# ---------------------------------------------------------------------------


def test_judge_schema_locks_in_severity_enum():
    severity_enum = (
        JUDGE_RESPONSE_SCHEMA["properties"]["severity_findings"]["items"]
        ["properties"]["severity"]["enum"]
    )
    assert severity_enum == ["critical", "major", "minor"]


def test_judge_schema_locks_in_dimensions():
    dim_props = JUDGE_RESPONSE_SCHEMA["properties"]["dimensions"]["properties"]
    assert set(dim_props.keys()) == {
        "narrative_coherence",
        "persona_experience",
        "pacing",
        "ending_plausibility",
    }
    for spec in dim_props.values():
        assert spec == {"type": "integer", "minimum": 0, "maximum": 25}


def test_build_judge_user_prompt_embeds_severity_definitions():
    persona = load_persona("cautious")
    path = _example_path()
    scene = {
        "graph_id": "test_scene",
        "entry_node_id": "n_start",
        "nodes": {"n_start": {}, "n_end_a": {}},
    }
    prompt = build_judge_user_prompt(scene=scene, persona=persona, path=path)
    # Severity definitions baked into prompt verbatim (F10)
    assert "critical" in prompt
    assert "major" in prompt
    assert "minor" in prompt
    assert "validator-missed illegal path" in prompt
    assert "narrative_coherence" in prompt
    assert "persona_experience" in prompt
    # Persona surface info shows up too
    assert "cautious" in prompt
    assert persona.display_name in prompt
    # Outcome
    assert "reached_end" in prompt


def test_rubric_version_is_v1():
    assert JUDGE_RUBRIC_VERSION == "v1"


# ---------------------------------------------------------------------------
# judge_path
# ---------------------------------------------------------------------------


def test_judge_path_writes_score_and_severities_to_path():
    persona = load_persona("cautious")
    path = _example_path()
    provider = _CannedJudgeProvider({
        "path_score": 80,
        "dimensions": {
            "narrative_coherence": 22,
            "persona_experience": 21,
            "pacing": 20,
            "ending_plausibility": 17,
        },
        "severity_findings": [
            {"severity": "minor", "description": "phrasing tweak"},
            {"severity": "major", "description": "pacing dip mid-scene"},
        ],
        "rationale": "Mostly good with one pacing dip.",
    })
    scene = {
        "graph_id": "test_scene",
        "entry_node_id": "n_start",
        "nodes": {"n_start": {}, "n_end_a": {}},
    }
    out_path, cost = judge_path(path, scene=scene, persona=persona, provider=provider)
    assert out_path is path
    assert path.judge_score == 80
    assert path.judge_dimensions == {
        "narrative_coherence": 22,
        "persona_experience": 21,
        "pacing": 20,
        "ending_plausibility": 17,
    }
    assert path.severity_findings == [
        {"severity": "minor", "description": "phrasing tweak"},
        {"severity": "major", "description": "pacing dip mid-scene"},
    ]
    assert path.minor_count == 1
    assert path.major_count == 1
    assert path.critical_count == 0
    assert cost > 0
    assert path.judge_rationale.startswith("Mostly")


def test_judge_path_observer_invoked():
    persona = load_persona("cautious")
    path = _example_path()
    provider = _CannedJudgeProvider({
        "path_score": 50,
        "dimensions": {
            "narrative_coherence": 12,
            "persona_experience": 13,
            "pacing": 13,
            "ending_plausibility": 12,
        },
        "severity_findings": [],
    })
    seen: list[tuple[float, int, int]] = []
    judge_path(
        path,
        scene={"graph_id": "test_scene", "nodes": {}},
        persona=persona,
        provider=provider,
        observer=lambda c, i, o: seen.append((c, i, o)),
    )
    assert len(seen) == 1
    assert seen[0][1] == 300
    assert seen[0][2] == 200


def test_judge_path_provider_error_propagates():
    persona = load_persona("cautious")
    path = _example_path()
    provider = _CannedJudgeProvider(ProviderError("decode boom"))
    with pytest.raises(ProviderError):
        judge_path(
            path,
            scene={"graph_id": "test_scene", "nodes": {}},
            persona=persona,
            provider=provider,
        )
    # Path stays unscored
    assert path.judge_score is None
    assert path.severity_findings == []


def test_judge_path_filters_unknown_severity_value():
    persona = load_persona("cautious")
    path = _example_path()
    provider = _CannedJudgeProvider({
        "path_score": 60,
        "dimensions": {
            "narrative_coherence": 15,
            "persona_experience": 15,
            "pacing": 15,
            "ending_plausibility": 15,
        },
        "severity_findings": [
            {"severity": "blocker", "description": "unknown severity"},
            {"severity": "critical", "description": "real one"},
        ],
    })
    judge_path(
        path,
        scene={"graph_id": "test_scene", "nodes": {}},
        persona=persona,
        provider=provider,
    )
    # 'blocker' must be filtered out, 'critical' kept
    sevs = {f["severity"] for f in path.severity_findings}
    assert sevs == {"critical"}
    assert path.critical_count == 1


# ---------------------------------------------------------------------------
# Aggregation + ranking
# ---------------------------------------------------------------------------


def _judged(path_id: str, score: float | None, criticals: int = 0) -> PlaytestPath:
    p = _example_path(path_id=path_id)
    p.judge_score = score
    p.critical_count = criticals
    return p


def test_rank_paths_worst_first_orders_by_score_then_severity():
    high = _judged("high", 90.0, 0)
    mid = _judged("mid", 50.0, 0)
    low = _judged("low", 10.0, 0)
    crit = _judged("crit", 50.0, 5)  # same score as mid but with criticals
    failed = _judged("failed", None)
    failed.error = "ProviderError @ n_x: boom"

    ranked = rank_paths_worst_first([high, mid, low, crit, failed])
    # error paths come first (worst); then by ascending score; criticals
    # break ties.
    assert [p.path_id for p in ranked][0] == "failed"
    # remaining order: low (10), crit (50 with criticals), mid (50), high (90)
    rest = [p.path_id for p in ranked][1:]
    assert rest == ["low", "crit", "mid", "high"]


def test_aggregate_scene_summary_basic_math():
    paths = [
        _judged("a", 80, 0),
        _judged("b", 60, 1),  # 1 critical
        _judged("c", 100, 0),
    ]
    agg = aggregate_scene_summary("scene_x", paths)
    assert isinstance(agg, SceneAggregate)
    assert agg.scene_id == "scene_x"
    assert agg.n_paths == 3
    assert agg.n_paths_judged == 3
    assert agg.mean_path_score == pytest.approx(80.0)
    assert agg.min_path_score == 60
    assert agg.max_path_score == 100
    assert agg.critical_count == 1
    # composite = mean - 5*crit + 0.3*(min - mean) = 80 - 5 - 0.3*20 = 69
    assert agg.scene_quality_score == pytest.approx(69.0)


def test_aggregate_scene_summary_handles_unjudged_paths():
    p = _example_path()
    p.judge_score = None
    p.error = "judge crashed"
    agg = aggregate_scene_summary("scene_no_score", [p])
    assert agg.n_paths == 1
    assert agg.n_paths_judged == 0
    assert agg.mean_path_score is None
    assert agg.scene_quality_score is None


def test_aggregate_scene_summary_collects_critical_findings():
    p1 = _judged("a", 50, 1)
    p1.severity_findings = [
        {"severity": "critical", "description": "state contradiction at n_x"}
    ]
    p2 = _judged("b", 80, 0)
    agg = aggregate_scene_summary("scene_y", [p1, p2])
    assert agg.critical_count == 1
    assert len(agg.critical_findings) == 1
    assert agg.critical_findings[0]["path_id"] == "a"
    assert "state contradiction" in agg.critical_findings[0]["description"]


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def test_render_worst_scenes_markdown_orders_worst_first_and_has_critical_block():
    paths_clean = [_judged("a", 90, 0), _judged("b", 95, 0)]
    paths_bad = [_judged("c", 30, 2), _judged("d", 35, 1)]
    paths_bad[0].severity_findings = [
        {"severity": "critical", "description": "missed validator gap"},
        {"severity": "critical", "description": "ontology clash"},
    ]
    paths_bad[1].severity_findings = [
        {"severity": "critical", "description": "another missed gap"}
    ]
    aggs = [
        aggregate_scene_summary("good_scene", paths_clean),
        aggregate_scene_summary("bad_scene", paths_bad),
    ]
    md = render_worst_scenes_markdown(aggs, playtest_id="playtest_001")
    # Bad scene appears first in the table because lower quality.
    bad_pos = md.find("`bad_scene`")
    good_pos = md.find("`good_scene`")
    assert bad_pos < good_pos
    # Critical block contains the descriptions
    assert "missed validator gap" in md
    assert "ontology clash" in md
    assert "Critical findings" in md


def test_render_worst_scenes_json_has_metadata_and_scenes():
    aggs = [aggregate_scene_summary("only", [_judged("p", 80, 0)])]
    payload = render_worst_scenes_json(aggs, playtest_id="playtest_007")
    assert payload["playtest_id"] == "playtest_007"
    assert payload["rubric_version"] == JUDGE_RUBRIC_VERSION
    assert isinstance(payload["scenes"], list)
    assert payload["scenes"][0]["scene_id"] == "only"
