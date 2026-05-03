"""T-2.5 critique 4.9: NodeRequirement.allowed_targets behavior.

Targets the new `allowed_targets` field added to `NodeRequirement` and the
matching post-validation hook in `generate_node`. Three things are
specified by the spec and exercised here:

  1. Default (`allowed_targets = None`) preserves T-1.6 behavior — no
     constraint, no prompt change beyond what's already there.
  2. Non-None `allowed_targets` adds a hard constraint to the user
     prompt (so the LLM sees it) AND post-processes responses to flag
     out-of-set `target_node_id`s as schema_invalid.
  3. The retry loop re-feeds the violation to the LLM exactly the same
     way it re-feeds any other schema_invalid error.

The tests use the same `_ScriptedProvider` pattern as
`test_generate_node.py` so we exercise the real `generate_node` retry
plumbing (not a mocked subset).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from generator.context_assembler import (
    GraphContext,
    NodeRequirement,
    assemble_context_block,
)
from generator.generate_node import generate_node
from generator.llm_provider import StructuredResponse


# ---------------------------------------------------------------------------
# Fixtures (mirrored from test_generate_node.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


_SCENE = json.loads(
    (
        Path(__file__).resolve().parent.parent.parent
        / "content"
        / "test_scene_v0"
        / "scene.json"
    ).read_text(encoding="utf-8")
)


def _valid_dialogue_node() -> dict:
    return copy.deepcopy(_SCENE["nodes"]["arrival_waystation"])


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=100,
        output_tokens=200,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _ScriptedProvider:
    model_id = "fake-model"

    def __init__(self, script):
        self._script = list(script)
        self._idx = 0
        self.call_count = 0
        self.user_prompts: list[str] = []

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        self.user_prompts.append(user_prompt)
        if self._idx >= len(self._script):
            raise AssertionError(
                f"FakeProvider exhausted on call #{self.call_count}"
            )
        item = self._script[self._idx]
        self._idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.001


def _ctx() -> GraphContext:
    return GraphContext(
        scene_anchor="scene_waystation_of_iron_oath",
        location_candidates=[
            {"location_id": "scene_waystation_of_iron_oath", "name": "铁誓驿站"}
        ],
        primary_location_ref="scene_waystation_of_iron_oath",
        parent_chain=[],
        involved_characters=[
            {"character_id": "char_vellin"},
            {"character_id": "char_corvan"},
            {"character_id": "char_aelwin"},
        ],
        faction_clocks={},
    )


# ---------------------------------------------------------------------------
# allowed_targets = None: default backwards-compat
# ---------------------------------------------------------------------------


def test_allowed_targets_none_does_not_constrain_targets():
    """T-1.6 behavior preserved when allowed_targets is left default."""
    node = _valid_dialogue_node()
    # The valid node points at vellin_confession / patrol_arrives —
    # neither is in any "allowed set" because there is no allowed set.
    provider = _ScriptedProvider([_make_response(node)])
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        # allowed_targets defaults to None
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    assert result.attempts[0].validator_errors == []


def test_allowed_targets_none_is_not_mentioned_in_prompt():
    """The skeleton-first prompt block only appears when allowed_targets
    is non-None — keeps T-1.6 prompt hashes stable."""
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
    )
    rendered = assemble_context_block(_ctx(), req)
    assert "skeleton-first" not in rendered
    assert "target_node_id 硬约束" not in rendered


# ---------------------------------------------------------------------------
# allowed_targets = [...]: prompt injection + happy path
# ---------------------------------------------------------------------------


def test_allowed_targets_listed_in_prompt():
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=["vellin_confession", "patrol_arrives"],
    )
    rendered = assemble_context_block(_ctx(), req)
    assert "target_node_id 硬约束" in rendered
    assert "vellin_confession" in rendered
    assert "patrol_arrives" in rendered


def test_allowed_targets_satisfied_succeeds_first_attempt():
    """All option targets in allowed_targets → success on attempt 1."""
    node = _valid_dialogue_node()
    legal_targets = sorted({opt["target_node_id"] for opt in node["options"]})
    provider = _ScriptedProvider([_make_response(node)])
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    # Sanity: prompt did include the constraint
    assert "target_node_id 硬约束" in provider.user_prompts[0]


# ---------------------------------------------------------------------------
# allowed_targets = [...]: violation triggers schema_invalid retry
# ---------------------------------------------------------------------------


def test_out_of_set_target_first_then_valid_succeeds_on_retry():
    """LLM emits a target outside the set → flagged → retry → fixed."""
    bad = _valid_dialogue_node()
    bad["options"][0]["target_node_id"] = "ghost_node_not_in_skeleton"
    good = _valid_dialogue_node()  # all originals are in legal set

    legal_targets = sorted({opt["target_node_id"] for opt in good["options"]})
    provider = _ScriptedProvider(
        [_make_response(bad), _make_response(good)]
    )
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    assert len(result.attempts) == 2
    first_errors = result.attempts[0].validator_errors
    assert any("not in skeleton allowed_targets" in e for e in first_errors)
    # The retry prompt must have re-fed the violation
    assert any(
        "ghost_node_not_in_skeleton" in p for p in provider.user_prompts[1:]
    )


def test_out_of_set_target_three_times_yields_schema_invalid():
    """Three consecutive violations → failure_reason='schema_invalid'."""
    bad = _valid_dialogue_node()
    bad["options"][0]["target_node_id"] = "ghost_node_not_in_skeleton"
    legal_targets = ["vellin_confession", "patrol_arrives"]
    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(bad)),
            _make_response(copy.deepcopy(bad)),
            _make_response(copy.deepcopy(bad)),
        ]
    )
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is False
    assert result.failure_reason == "schema_invalid"
    assert len(result.attempts) == 3
    for att in result.attempts:
        assert any(
            "not in skeleton allowed_targets" in e for e in att.validator_errors
        )


# ---------------------------------------------------------------------------
# Empty allowed_targets (end-node defensive case)
# ---------------------------------------------------------------------------


def test_end_node_with_empty_allowed_targets_is_signalled_in_prompt():
    """Empty list communicates 'this is an end node' to the LLM."""
    req = NodeRequirement(
        node_type="end",
        expected_speaker_ref=None,
        narrative_intent="ending：共谋余韵",
        allowed_targets=[],
    )
    rendered = assemble_context_block(_ctx(), req)
    assert "target_node_id 硬约束" in rendered
    assert "end 节点" in rendered


# ---------------------------------------------------------------------------
# C-phase (review 4.1): type / speaker_ref invariants
# ---------------------------------------------------------------------------


def _valid_end_node() -> dict:
    return copy.deepcopy(_SCENE["nodes"]["end_silent_ally"])


def test_type_mismatch_rejected_when_skeleton_required_dialogue():
    """LLM returns a schema-valid `end` node when skeleton wanted
    `dialogue` → must be flagged as schema_invalid + retried.

    Without this guard, `options=[]` would silently bypass
    `_check_allowed_targets` (no options = no targets to check) and
    `success=True` would bubble up to `fill_skeleton` with the
    skeleton's planned out-edges erased.
    """
    end_node_when_dialogue_expected = _valid_end_node()
    good_dialogue = _valid_dialogue_node()
    legal_targets = sorted({opt["target_node_id"] for opt in good_dialogue["options"]})
    provider = _ScriptedProvider(
        [
            _make_response(end_node_when_dialogue_expected),
            _make_response(good_dialogue),
        ]
    )
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    assert len(result.attempts) == 2
    first_errors = result.attempts[0].validator_errors
    assert any(
        "/type:" in e and "expected 'dialogue'" in e for e in first_errors
    )


def test_type_mismatch_three_times_yields_schema_invalid():
    end_node_when_dialogue_expected = _valid_end_node()
    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(end_node_when_dialogue_expected)),
            _make_response(copy.deepcopy(end_node_when_dialogue_expected)),
            _make_response(copy.deepcopy(end_node_when_dialogue_expected)),
        ]
    )
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref=None,  # leave speaker free; isolating type check
        narrative_intent="建立场景张力",
        allowed_targets=["vellin_confession", "patrol_arrives"],
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is False
    assert result.failure_reason == "schema_invalid"


def test_speaker_mismatch_rejected_when_named_speaker_required():
    """When `expected_speaker_ref` is non-None the LLM must respect it."""
    bad = _valid_dialogue_node()
    bad["speaker_ref"] = "char_corvan"  # skeleton wanted char_vellin
    good = _valid_dialogue_node()  # speaker_ref already char_vellin
    legal_targets = sorted({opt["target_node_id"] for opt in good["options"]})
    provider = _ScriptedProvider(
        [_make_response(bad), _make_response(good)]
    )
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    assert len(result.attempts) == 2
    first_errors = result.attempts[0].validator_errors
    assert any(
        "/speaker_ref:" in e and "char_vellin" in e for e in first_errors
    )


def test_speaker_unconstrained_when_expected_speaker_is_none():
    """`expected_speaker_ref=None` (旁白 OK) should not flag any speaker."""
    node = _valid_dialogue_node()  # speaker_ref = char_vellin
    legal_targets = sorted({opt["target_node_id"] for opt in node["options"]})
    provider = _ScriptedProvider([_make_response(node)])
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref=None,  # caller doesn't pin the speaker
        narrative_intent="建立场景张力",
        allowed_targets=legal_targets,
    )
    result = generate_node(graph_context=_ctx(), node_requirement=req, provider=provider)
    assert result.success is True
    assert result.attempts[0].validator_errors == []
