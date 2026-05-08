"""Path simulator tests (T-3.4 / ADR-022 P-2)."""
from __future__ import annotations

import asyncio
import json
from typing import Iterable

import pytest

from generator.llm_provider import ProviderError, StructuredResponse
from generator.playtest.personas import Persona, load_persona
from generator.playtest.runner import (
    PathStep,
    PlaytestPath,
    path_to_jsonl_dict,
    run_path,
    run_paths,
)


# ---------------------------------------------------------------------------
# Test isolation — sibling pattern of scene_ai_judge tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


def _structured(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=200,
        output_tokens=80,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _ScriptedProvider:
    """Yields canned (option_id, reasoning) tuples in order."""

    model_id = "fake-model"
    temperature = 0.7

    def __init__(self, decisions: Iterable[tuple[str, str]]):
        self._items = list(decisions)
        self._idx = 0
        self.calls: list[dict] = []

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt, "schema": json_schema}
        )
        if self._idx >= len(self._items):
            raise AssertionError(
                f"_ScriptedProvider exhausted at call {len(self.calls)}"
            )
        item = self._items[self._idx]
        self._idx += 1
        if isinstance(item, BaseException):
            raise item
        opt_id, reasoning = item
        return _structured(
            {"chosen_option_id": opt_id, "reasoning": reasoning}
        )

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.001


# ---------------------------------------------------------------------------
# Test scene fixtures
# ---------------------------------------------------------------------------


def _two_branch_scene() -> dict:
    """Linear scene: entry → either end_a or end_b."""
    return {
        "schema_version": "0.1.1",
        "graph_id": "test_two_branch",
        "entry_node_id": "n_start",
        "scene_anchor": "test_anchor",
        "nodes": {
            "n_start": {
                "node_id": "n_start",
                "type": "dialogue",
                "narration": "You arrive at the crossroads.",
                "speaker_ref": None,
                "options": [
                    {
                        "option_id": "go_a",
                        "text": "Take the eastern road.",
                        "target_node_id": "n_end_a",
                        "condition": None,
                        "effects": [
                            {"op": "set", "path": "flag.went_east", "value": True}
                        ],
                        "unavailable_behavior": "hide",
                    },
                    {
                        "option_id": "go_b",
                        "text": "Take the western road.",
                        "target_node_id": "n_end_b",
                        "condition": None,
                        "effects": [
                            {"op": "set", "path": "flag.went_west", "value": True}
                        ],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "n_end_a": {
                "node_id": "n_end_a",
                "type": "end",
                "narration": "Eastern outcome.",
                "options": [],
            },
            "n_end_b": {
                "node_id": "n_end_b",
                "type": "end",
                "narration": "Western outcome.",
                "options": [],
            },
        },
    }


def _conditional_scene() -> dict:
    """Same as two_branch but go_b requires flag.has_torch."""
    scene = _two_branch_scene()
    scene["graph_id"] = "test_conditional"
    scene["nodes"]["n_start"]["options"][1]["condition"] = {
        "op": "eq",
        "path": "flag.has_torch",
        "value": True,
    }
    return scene


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_path_single_step_reaches_end():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_a", "I prefer the eastern road.")])
    scene = _two_branch_scene()

    result = run_path(scene, persona, provider=provider)

    assert isinstance(result, PlaytestPath)
    assert result.reached_end is True
    assert result.end_node_id == "n_end_a"
    assert result.failure_reason is None
    assert result.error is None
    assert result.llm_calls == 1
    assert result.cost_usd > 0
    assert result.duration_seconds >= 0
    assert len(result.steps) == 2  # entry + end
    # B-review 4.2: option_id belongs to the step the persona is
    # LEAVING, not the target node. End step's option_id is None.
    assert result.steps[0].node_id == "n_start"
    assert result.steps[0].option_id == "go_a"
    assert result.steps[0].reasoning == "I prefer the eastern road."
    assert result.steps[1].node_id == "n_end_a"
    assert result.steps[1].option_id is None
    # state_after on the second step should reflect the option's effect
    assert result.steps[1].state_after.get("flag", {}).get("went_east") is True


def test_run_path_step_records_option_set_and_raw_choice():
    """F20 replay metadata: option_set + raw_choice land on the step
    the persona left (B-review 4.1)."""
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_b", "western chosen")])
    result = run_path(_two_branch_scene(), persona, provider=provider)
    leaving_step = result.steps[0]
    # option_set spans every valid option the LLM saw
    ids = sorted(opt["option_id"] for opt in leaving_step.option_set)
    assert ids == ["go_a", "go_b"]
    for opt in leaving_step.option_set:
        # texts truncated to ≤ 240 chars but non-empty for the fixture
        assert isinstance(opt["text"], str)
        assert opt["text"]
        assert "target_node_id" in opt
    # raw_choice is the provider's raw_text (JSON-shaped)
    assert leaving_step.raw_choice
    assert "go_b" in leaving_step.raw_choice
    # End step has no option set or raw_choice — pure arrival snapshot
    end_step = result.steps[1]
    assert end_step.option_set == []
    assert end_step.raw_choice is None


def test_run_path_end_node_state_after_includes_on_enter_effects():
    """B-review 4.2 second concern: when the end node has
    ``on_enter_effects``, those land in the final step's
    ``state_after`` (not the prior step's snapshot)."""
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_a", "ok")])
    scene = _two_branch_scene()
    scene["nodes"]["n_end_a"]["on_enter_effects"] = [
        {"op": "set", "path": "flag.end_marker_seen", "value": True}
    ]
    result = run_path(scene, persona, provider=provider)
    assert result.reached_end is True
    final = result.steps[-1]
    assert final.node_id == "n_end_a"
    assert final.option_id is None
    assert final.state_after.get("flag", {}).get("end_marker_seen") is True
    # Entry step's snapshot should NOT carry the end's on_enter
    entry = result.steps[0]
    assert entry.state_after.get("flag", {}).get("end_marker_seen") is None


def test_run_path_records_persona_id_and_scene_id():
    persona = load_persona("aggressive")
    provider = _ScriptedProvider([("go_b", "Smash through the western road.")])
    scene = _two_branch_scene()
    result = run_path(scene, persona, provider=provider)
    assert result.persona_id == "aggressive"
    assert result.scene_id == "test_two_branch"


def test_run_path_on_provider_error_records_error_field():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([ProviderError("transient failure")])
    scene = _two_branch_scene()
    result = run_path(scene, persona, provider=provider)
    assert result.error and "ProviderError" in result.error
    assert result.failure_reason == "provider_error"
    assert result.reached_end is False


def test_run_path_deadlock_when_no_valid_option():
    """Conditional scene with no `flag.has_torch` and only one valid path
    works fine. But if we strip both targets, we deadlock."""
    persona = load_persona("cautious")
    provider = _ScriptedProvider([])  # no calls expected
    scene = _two_branch_scene()
    # Force every option's condition to evaluate False.
    scene["nodes"]["n_start"]["options"][0]["condition"] = {
        "op": "eq", "path": "flag.never", "value": True
    }
    scene["nodes"]["n_start"]["options"][1]["condition"] = {
        "op": "eq", "path": "flag.never_either", "value": True
    }
    result = run_path(scene, persona, provider=provider)
    assert result.reached_end is False
    assert result.failure_reason == "no valid option at non-end node (deadlock)"
    assert result.llm_calls == 0


def test_run_path_invalid_target_node_id():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("ghost", "I take the ghost road.")])
    scene = _two_branch_scene()
    scene["nodes"]["n_start"]["options"].append({
        "option_id": "ghost",
        "text": "Take the ghost road.",
        "target_node_id": "nonexistent",
        "condition": None,
        "effects": [],
        "unavailable_behavior": "hide",
    })
    result = run_path(scene, persona, provider=provider)
    assert result.reached_end is False
    assert "missing or invalid" in (result.failure_reason or "")


def test_run_path_invalid_entry_node_short_circuits():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([])
    scene = _two_branch_scene()
    scene["entry_node_id"] = "no_such_node"
    result = run_path(scene, persona, provider=provider)
    assert result.reached_end is False
    assert result.llm_calls == 0
    assert "entry_node_id" in (result.failure_reason or "")


def test_run_path_observer_called_per_call():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_a", "ok")])
    scene = _two_branch_scene()
    seen: list[tuple[float, int, int]] = []
    run_path(
        scene,
        persona,
        provider=provider,
        observer=lambda c, i, o: seen.append((c, i, o)),
    )
    assert len(seen) == 1
    cost, in_tok, out_tok = seen[0]
    assert cost > 0
    assert in_tok == 200
    assert out_tok == 80


def test_run_path_initial_state_seeds_world_state():
    """If we seed flag.has_torch=True, the conditional option becomes valid."""
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_b", "I have a torch.")])
    scene = _conditional_scene()
    # Without initial_state, go_b would be filtered. With it, the
    # provider's choice of go_b lands without surfacing as
    # "invalid_option_choice".
    result = run_path(
        scene, persona, provider=provider, initial_state={"flag.has_torch": True}
    )
    assert result.reached_end is True
    assert result.end_node_id == "n_end_b"


def test_run_paths_runs_n_paths_and_collects_results():
    persona = load_persona("cautious")
    provider = _ScriptedProvider(
        [
            ("go_a", "east 1"),
            ("go_b", "west 2"),
            ("go_a", "east 3"),
        ]
    )
    results = run_paths(_two_branch_scene(), persona, n_paths=3, provider=provider)
    assert len(results) == 3
    assert sum(p.reached_end for p in results) == 3
    assert all(p.persona_id == "cautious" for p in results)


def test_path_to_jsonl_dict_serialises_steps_and_findings():
    persona = load_persona("cautious")
    provider = _ScriptedProvider([("go_a", "reasoning text")])
    result = run_path(_two_branch_scene(), persona, provider=provider)
    # Manually attach a finding to make sure it round-trips.
    result.judge_score = 75.0
    result.severity_findings = [
        {"severity": "minor", "description": "phrasing"},
    ]
    result.minor_count = 1
    result.judge_dimensions = {"narrative_coherence": 20.0}
    out = path_to_jsonl_dict(result)
    assert out["path_id"] == result.path_id
    assert out["judge_score"] == 75.0
    assert out["severity_findings"] == [
        {"severity": "minor", "description": "phrasing"}
    ]
    assert out["minor_count"] == 1
    assert out["judge_dimensions"] == {"narrative_coherence": 20.0}
    # steps round-trip with state_after present
    assert len(out["steps"]) == 2
    assert out["steps"][1]["state_after"]["flag"]["went_east"] is True
