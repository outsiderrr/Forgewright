"""T-2.5 scene_strategies skeleton-first scenarios.

Six scenarios cover the contract:

  1. valid skeleton + N valid fills            → success
  2. skeleton 3 invalid attempts               → success=False, "skeleton_invalid"
  3. fill node 3 invalid (schema-only)         → success=False, "fill_node_invalid"
  4. fill node 3 invalid (allowed_targets)     → success=False, "fill_target_out_of_skeleton"
  5. fill node first allowed_targets, then OK  → success
  6. prompt sanity (character_features /
     dramatic_triggers / active_clocks /
     system_time / narrative_weight /
     location_candidates all rendered)         → string assertions

No real Gemini API calls; FakeProvider is scripted per scenario.
"""
from __future__ import annotations

import copy
import json

import pytest

from generator.context_assembler import PriorSceneSummary
from generator.llm_provider import StructuredResponse
from generator.scene_strategies import (
    GraphSkeleton,
    SceneSetting,
    SkeletonNode,
    fill_skeleton,
    generate_scene_skeleton_first,
    generate_skeleton,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=200,
        output_tokens=400,
        model_id="fake-model",
        finish_reason="STOP",
    )


class _ScriptedProvider:
    """Scripted provider with prompt capture for sanity assertions.

    Phase 1 (skeleton) and phase 2 (fill) calls share the same
    `generate_structured` interface so the script is a single linear
    list — caller must order it [skeleton_responses..., fill_responses...].
    """

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
                f"FakeProvider exhausted on call #{self.call_count}; "
                f"script length = {len(self._script)}"
            )
        item = self._script[self._idx]
        self._idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.001


# A minimal but parser-valid skeleton response.
# 3 dialogue + 2 end nodes; each dialogue has 2 unique outgoing targets.
_VALID_SKELETON_JSON: dict = {
    "nodes": [
        {
            "node_id": "n_arrival",
            "type": "dialogue",
            "beat": "抵达驿站",
            "speaker_ref": "char_vellin",
            "expected_branch_count": 3,
        },
        {
            "node_id": "n_confession",
            "type": "dialogue",
            "beat": "秘密摊开",
            "speaker_ref": "char_vellin",
            "expected_branch_count": 2,
        },
        {
            "node_id": "n_patrol",
            "type": "dialogue",
            "beat": "巡逻官登场",
            "speaker_ref": "char_corvan",
            "expected_branch_count": 3,
        },
        {
            "node_id": "n_end_silent",
            "type": "end",
            "beat": "ending：共谋余韵",
            "speaker_ref": None,
            "expected_branch_count": 0,
        },
        {
            "node_id": "n_end_iron",
            "type": "end",
            "beat": "ending：告发代价",
            "speaker_ref": None,
            "expected_branch_count": 0,
        },
    ],
    "edges": [
        ["n_arrival", "n_confession"],
        ["n_arrival", "n_patrol"],
        ["n_confession", "n_end_silent"],
        ["n_confession", "n_end_iron"],
        ["n_patrol", "n_end_silent"],
        ["n_patrol", "n_end_iron"],
    ],
    "entry_node_id": "n_arrival",
    "end_node_ids": ["n_end_silent", "n_end_iron"],
}


def _scene_setting() -> SceneSetting:
    return SceneSetting(
        scene_anchor="scene_waystation_of_iron_oath",
        primary_location_ref="scene_waystation_of_iron_oath",
        chapter_ref="chap_glades",
        expected_node_count_min=5,
        expected_node_count_max=15,
    )


def _participating_npcs() -> list[dict]:
    return [
        {
            "id": "char_vellin",
            "display_name": "Vellin",
            "state_path_slug": "vellin",
            "character_features": ["stoic mercenary", "驿站老板娘"],
            "dramatic_triggers": [
                {
                    "trait": "stoic mercenary",
                    "when": "被质问过去",
                    "how": "沉默几秒后岔开话题",
                    "priority": 1,
                }
            ],
            "relations": [
                {
                    "target_character_ref": "char_corvan",
                    "relation_type": "former_brother_in_arms_now_adversary",
                    "narrative_weight": "core",
                }
            ],
        },
        {
            "id": "char_corvan",
            "display_name": "Corvan",
            "state_path_slug": "corvan",
            "character_features": ["铁誓巡逻官", "前兰岭战友"],
            "dramatic_triggers": [],
            "relations": [
                {
                    "target_character_ref": "char_vellin",
                    "relation_type": "former_brother_in_arms_now_adversary",
                    "narrative_weight": "core",
                }
            ],
        },
    ]


def _target_beats() -> list[str]:
    return [
        "抵达驿站",
        "秘密摊开",
        "巡逻官登场",
        "ending：共谋余韵",
        "ending：告发代价",
    ]


def _location_candidates() -> list[dict]:
    return [
        {
            "location_id": "scene_waystation_of_iron_oath",
            "display_name": "铁誓驿站",
        }
    ]


def _active_clocks() -> list[dict]:
    return [
        {
            "id": "clock_iron_oath_pursuit",
            "name": "Iron Oath Pursuit",
            "scope": "faction",
            "ticks_total": 6,
            "ticks_filled": 2,
            "advance_rule": {"type": "every_n_scenes", "params": {"n": 1}},
        }
    ]


def _system_time() -> dict:
    return {"scene_count": 7, "long_rest_count": 3}


def _valid_filled_node(skel_node: SkeletonNode, allowed_targets: list[str]) -> dict:
    """Build a schema-valid Node dict whose options point at allowed_targets."""
    if skel_node.type == "end":
        return {
            "node_id": skel_node.node_id,
            "type": "end",
            "narration": "（ending：节拍 " + skel_node.beat + "）",
            "speaker_ref": None,
            "location_ref": "scene_waystation_of_iron_oath",
            "on_enter_effects": [],
            "options": [],
        }
    options = []
    # Generate enough options to satisfy expected_branch_count, recycling
    # allowed_targets cyclically. Each option text stays under 25 漢字.
    if not allowed_targets:
        # shouldn't happen for dialogue nodes given valid skeleton
        allowed_targets = ["unknown_target"]
    for i in range(skel_node.expected_branch_count):
        options.append(
            {
                "option_id": f"opt_{skel_node.node_id}_{i+1}",
                "text": f"选项 {i+1}。",
                "target_node_id": allowed_targets[i % len(allowed_targets)],
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            }
        )
    return {
        "node_id": skel_node.node_id,
        "type": "dialogue",
        "narration": f"（节拍 {skel_node.beat} 的台词。）",
        "speaker_ref": skel_node.speaker_ref,
        "location_ref": "scene_waystation_of_iron_oath",
        "on_enter_effects": [],
        "options": options,
    }


def _build_fill_responses_for_valid_skeleton(
    skeleton_dict: dict,
) -> list[StructuredResponse]:
    """Construct one valid Node response per skeleton node (in skeleton order)."""
    skel_nodes = [
        SkeletonNode(
            node_id=n["node_id"],
            type=n["type"],
            beat=n["beat"],
            speaker_ref=n.get("speaker_ref"),
            expected_branch_count=n["expected_branch_count"],
        )
        for n in skeleton_dict["nodes"]
    ]
    edges = [tuple(e) for e in skeleton_dict["edges"]]
    skel = GraphSkeleton(
        nodes=skel_nodes,
        edges=edges,
        entry_node_id=skeleton_dict["entry_node_id"],
        end_node_ids=skeleton_dict["end_node_ids"],
    )
    responses: list[StructuredResponse] = []
    for node in skel_nodes:
        allowed = skel.get_allowed_targets(node.node_id)
        responses.append(
            _make_response(_valid_filled_node(node, allowed))
        )
    return responses


# ---------------------------------------------------------------------------
# Scenario 1: valid skeleton + N valid fills → success
# ---------------------------------------------------------------------------


def test_scenario_1_happy_path():
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        active_clocks=_active_clocks(),
        system_time=_system_time(),
        location_candidates=_location_candidates(),
    )
    assert result.success is True
    assert result.failure_reason is None
    assert result.skeleton is not None
    assert result.graph is not None
    assert result.graph["schema_version"] == "0.1.1"
    assert result.graph["entry_node_id"] == "n_arrival"
    assert set(result.graph["nodes"].keys()) == {
        "n_arrival",
        "n_confession",
        "n_patrol",
        "n_end_silent",
        "n_end_iron",
    }
    # 1 skeleton call + 5 fill calls = 6 total
    assert provider.call_count == 6
    assert result.total_cost_usd > 0


# ---------------------------------------------------------------------------
# Scenario 2: skeleton three failures → "skeleton_invalid"
# ---------------------------------------------------------------------------


def test_scenario_2_skeleton_three_failures():
    bad_skeleton = {
        "nodes": [],  # empty array → /nodes: must be a non-empty array
        "edges": [],
        "entry_node_id": "",
        "end_node_ids": [],
    }
    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(bad_skeleton)),
            _make_response(copy.deepcopy(bad_skeleton)),
            _make_response(copy.deepcopy(bad_skeleton)),
        ]
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "skeleton_invalid"
    assert len(result.skeleton_attempts) == 3
    assert result.fill_attempts == {}
    assert provider.call_count == 3


# ---------------------------------------------------------------------------
# Scenario 3: fill node 3 schema-only failures → "fill_node_invalid"
# ---------------------------------------------------------------------------


def test_scenario_3_fill_node_three_schema_failures():
    """First fill node (n_arrival) fails 3 times with a schema error
    unrelated to allowed_targets — drops the required `narration`."""
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    # Mutate the FIRST fill response (for n_arrival) into 3 schema-invalid
    # repeats. Use a node missing its required `narration` field.
    bad_node = copy.deepcopy(fill_responses_full[0].content)
    del bad_node["narration"]
    bad_response = _make_response(bad_node)

    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(_VALID_SKELETON_JSON)),
            bad_response,
            _make_response(copy.deepcopy(bad_node)),
            _make_response(copy.deepcopy(bad_node)),
        ]
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "fill_node_invalid"
    assert result.failure_node_id == "n_arrival"
    # Skeleton phase used 1 call; fill phase used 3 attempts on n_arrival.
    assert provider.call_count == 4
    # The dominant error must NOT be allowed_targets — it should be a
    # plain schema_invalid (missing narration), so the classification
    # routes to fill_node_invalid not fill_target_out_of_skeleton.
    n_arrival_attempts = result.fill_attempts["n_arrival"]
    assert len(n_arrival_attempts) == 3
    for att in n_arrival_attempts:
        assert not any(
            "not in skeleton allowed_targets" in e for e in att.validator_errors
        )


# ---------------------------------------------------------------------------
# Scenario 4: fill 3x allowed_targets violations → fill_target_out_of_skeleton
# ---------------------------------------------------------------------------


def test_scenario_4_fill_three_allowed_targets_violations():
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    # Mutate the first fill response (n_arrival) so its option targets
    # all point outside skeleton.allowed_targets.
    bad_node = copy.deepcopy(fill_responses_full[0].content)
    for opt in bad_node["options"]:
        opt["target_node_id"] = "ghost_node"
    bad_response = _make_response(bad_node)

    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(_VALID_SKELETON_JSON)),
            bad_response,
            _make_response(copy.deepcopy(bad_node)),
            _make_response(copy.deepcopy(bad_node)),
        ]
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "fill_target_out_of_skeleton"
    assert result.failure_node_id == "n_arrival"
    n_arrival_attempts = result.fill_attempts["n_arrival"]
    assert len(n_arrival_attempts) == 3
    for att in n_arrival_attempts:
        assert any(
            "not in skeleton allowed_targets" in e for e in att.validator_errors
        )


# ---------------------------------------------------------------------------
# Scenario 5: out-of-skeleton on first attempt, valid on second → success
# ---------------------------------------------------------------------------


def test_scenario_5_fill_first_violates_then_recovers():
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    bad_first = copy.deepcopy(fill_responses_full[0].content)
    bad_first["options"][0]["target_node_id"] = "ghost_node"
    bad_response = _make_response(bad_first)

    # n_arrival: 1 bad + 1 good = 2 attempts. Other 4 nodes: 1 attempt each.
    script: list = [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
    script.append(bad_response)
    script.append(fill_responses_full[0])  # the recovery: good n_arrival
    script.extend(fill_responses_full[1:])  # the rest of the nodes

    provider = _ScriptedProvider(script)
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    assert result.failure_reason is None
    assert len(result.fill_attempts["n_arrival"]) == 2
    # First attempt had violation; second succeeded.
    assert any(
        "not in skeleton allowed_targets" in e
        for e in result.fill_attempts["n_arrival"][0].validator_errors
    )
    assert result.fill_attempts["n_arrival"][1].validator_errors == []


# ---------------------------------------------------------------------------
# Scenario 6: prompt sanity — context fields all rendered
# ---------------------------------------------------------------------------


def test_scenario_6_prompt_includes_context_fields():
    """Phase-1 prompt must surface character_features /
    dramatic_triggers / active_clocks / system_time / narrative_weight /
    location_candidates so the LLM sees the same ontology shape T-2.6
    will pre-assemble in production."""
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
    )
    skel_res = generate_skeleton(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        active_clocks=_active_clocks(),
        system_time=_system_time(),
        location_candidates=_location_candidates(),
    )
    assert skel_res.success is True
    prompt = provider.user_prompts[0]
    # All six context elements must appear somewhere in the prompt.
    assert "character_features" in prompt
    assert "dramatic_triggers" in prompt
    assert "active_clocks" in prompt
    # system_time appears as world.scene_count / world.long_rest_count
    assert "world.scene_count" in prompt
    assert "world.long_rest_count" in prompt
    assert "narrative_weight" in prompt
    assert "location_candidates" in prompt
    # state_path_slug usage instruction (§2.6 / Q1)
    assert "state_path_slug" in prompt


def test_fill_phase_injects_allowed_targets_into_each_node_prompt():
    """Sanity: every fill call's prompt must list the skeleton's
    allowed_targets for that node (critique 4.9)."""
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses_full
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    # Skip the first prompt (skeleton); inspect the fill prompts.
    fill_prompts = provider.user_prompts[1:]
    assert len(fill_prompts) == 5
    # n_arrival's allowed_targets are n_confession + n_patrol
    assert "n_confession" in fill_prompts[0]
    assert "n_patrol" in fill_prompts[0]
    # End nodes get an "end 节点" reminder instead of a target list
    end_idx = next(
        i
        for i, n in enumerate(_VALID_SKELETON_JSON["nodes"])
        if n["type"] == "end"
    )
    assert "end 节点" in fill_prompts[end_idx]


# ---------------------------------------------------------------------------
# Skeleton parser: structural invariants surface as validator_errors
# ---------------------------------------------------------------------------


def test_skeleton_parser_catches_unknown_target_in_edges():
    """An edge to an undeclared node must trigger a validator_error
    (and therefore retry / failure on exhaustion)."""
    bad_skeleton = copy.deepcopy(_VALID_SKELETON_JSON)
    bad_skeleton["edges"].append(["n_arrival", "n_phantom"])
    provider = _ScriptedProvider(
        [
            _make_response(bad_skeleton),
            _make_response(bad_skeleton),
            _make_response(bad_skeleton),
        ]
    )
    result = generate_skeleton(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "skeleton_invalid"
    assert any(
        "n_phantom" in e
        for att in result.attempts
        for e in att.validator_errors
    )


def test_get_allowed_targets_dedupes_repeated_edges():
    """Multiple options pointing at the same target → single allowed target."""
    skel = GraphSkeleton(
        nodes=[
            SkeletonNode("n_a", "dialogue", "beat_a", "char_x", 3),
            SkeletonNode("n_b", "end", "beat_b", None, 0),
        ],
        edges=[("n_a", "n_b"), ("n_a", "n_b"), ("n_a", "n_b")],
        entry_node_id="n_a",
        end_node_ids=["n_b"],
    )
    assert skel.get_allowed_targets("n_a") == ["n_b"]
    assert skel.get_allowed_targets("n_b") == []


# ---------------------------------------------------------------------------
# fill_skeleton standalone (skeleton injected directly)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# C-phase (review 4.1): fill-phase rejects skeleton-mismatched type
# ---------------------------------------------------------------------------


def test_fill_phase_rejects_end_node_when_skeleton_wants_dialogue():
    """If LLM returns an end-shaped node where skeleton planned a dialogue
    node, fill_skeleton must surface fill_node_invalid (NOT silently
    accept it via the `options=[]` allowed_targets bypass)."""
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    # Mutate n_arrival's response into an end-shape: type="end",
    # options=[], speaker_ref=None. Schema-valid for an end node, but
    # n_arrival is a dialogue node in the skeleton.
    bad_arrival_as_end = copy.deepcopy(fill_responses_full[0].content)
    bad_arrival_as_end["type"] = "end"
    bad_arrival_as_end["options"] = []
    bad_arrival_as_end["speaker_ref"] = None
    bad_response = _make_response(bad_arrival_as_end)

    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(_VALID_SKELETON_JSON)),
            bad_response,
            _make_response(copy.deepcopy(bad_arrival_as_end)),
            _make_response(copy.deepcopy(bad_arrival_as_end)),
        ]
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    # Three failures with the type mismatch but no allowed_targets
    # violation → routes to fill_node_invalid (not
    # fill_target_out_of_skeleton).
    assert result.failure_reason == "fill_node_invalid"
    assert result.failure_node_id == "n_arrival"
    n_arrival_attempts = result.fill_attempts["n_arrival"]
    assert len(n_arrival_attempts) == 3
    for att in n_arrival_attempts:
        assert any(
            "/type:" in e and "expected 'dialogue'" in e
            for e in att.validator_errors
        )


def test_fill_phase_rejects_speaker_mismatch_when_skeleton_pins_speaker():
    """Skeleton names char_vellin as speaker; LLM returns char_corvan."""
    fill_responses_full = _build_fill_responses_for_valid_skeleton(
        _VALID_SKELETON_JSON
    )
    # n_arrival's skeleton speaker is char_vellin. Replace it.
    bad = copy.deepcopy(fill_responses_full[0].content)
    bad["speaker_ref"] = "char_corvan"
    good = copy.deepcopy(fill_responses_full[0].content)  # original has char_vellin

    script: list = [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
    script.append(_make_response(bad))
    script.append(_make_response(good))
    script.extend(fill_responses_full[1:])

    provider = _ScriptedProvider(script)
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
    provider=provider,
    )
    assert result.success is True
    assert len(result.fill_attempts["n_arrival"]) == 2
    assert any(
        "/speaker_ref:" in e and "char_vellin" in e
        for e in result.fill_attempts["n_arrival"][0].validator_errors
    )


# ---------------------------------------------------------------------------
# C-phase (review 4.2): fill-phase prompts must surface active_clocks +
# system_time (not just the skeleton phase)
# ---------------------------------------------------------------------------


def test_fill_phase_prompts_include_active_clocks_and_system_time():
    """Each fill prompt must list active_clocks + system_time so per-node
    text reflects current world state. A-phase regression: helper wrote
    `faction_clocks={}` and dropped system_time on the way to fill."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        active_clocks=_active_clocks(),
        system_time=_system_time(),
        location_candidates=_location_candidates(),
    )
    assert result.success is True
    fill_prompts = provider.user_prompts[1:]  # skip skeleton prompt
    assert len(fill_prompts) == 5
    for idx, fp in enumerate(fill_prompts):
        assert "active_clocks" in fp, f"fill prompt {idx} missing active_clocks header"
        assert "clock_iron_oath_pursuit" in fp, (
            f"fill prompt {idx} missing concrete clock id"
        )
        assert "world.scene_count" in fp, (
            f"fill prompt {idx} missing system_time scene_count"
        )
        assert "world.long_rest_count" in fp, (
            f"fill prompt {idx} missing system_time long_rest_count"
        )


def test_fill_phase_omits_clock_section_when_no_clocks_provided():
    """Don't pollute T-1.6 single-node callers with empty 活跃时钟 sections.
    When neither active_clocks nor system_time was provided, the rendered
    block must skip both sections silently."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        # active_clocks / system_time / location_candidates left as defaults
    )
    assert result.success is True
    fill_prompts = provider.user_prompts[1:]
    for fp in fill_prompts:
        assert "活跃时钟" not in fp
        assert "系统时间" not in fp


def test_fill_skeleton_directly_with_minimal_skeleton():
    """Fill phase should work in isolation — useful for T-2.6 wiring."""
    skel = GraphSkeleton(
        nodes=[
            SkeletonNode("n_a", "dialogue", "beat_a", "char_vellin", 1),
            SkeletonNode("n_b", "end", "beat_b", None, 0),
        ],
        edges=[("n_a", "n_b")],
        entry_node_id="n_a",
        end_node_ids=["n_b"],
    )
    fill_responses = [
        _make_response(_valid_filled_node(skel.nodes[0], skel.get_allowed_targets("n_a"))),
        _make_response(_valid_filled_node(skel.nodes[1], [])),
    ]
    provider = _ScriptedProvider(fill_responses)
    scene_context = {
        "scene_anchor": "scene_waystation_of_iron_oath",
        "location_candidates": _location_candidates(),
        "primary_location_ref": "scene_waystation_of_iron_oath",
        "involved_characters": [{"character_id": "char_vellin"}],
        "active_clocks": [],
        "character_refs": ["char_vellin"],
    }
    fill_res = fill_skeleton(
        skeleton=skel, scene_context=scene_context, provider=provider
    )
    assert fill_res.success is True
    assert fill_res.graph is not None
    assert set(fill_res.graph["nodes"].keys()) == {"n_a", "n_b"}
    assert fill_res.graph["entry_node_id"] == "n_a"


# ---------------------------------------------------------------------------
# R2.6 — fill prompt context tuning (previously_filled + beat_position +
# bleed-through guard) targeting T-2.12 baseline_005 v3 reject patterns
# ---------------------------------------------------------------------------


def test_r2_6_first_fill_prompt_omits_previously_filled_section():
    """First-node fill prompt must NOT render the empty summary header.

    R2.6 §3 — rendering an empty section would just be visual noise the
    LLM has to step over. Beat-position + bleed-through guard still
    appear (they don't depend on prior fills).
    """
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    first_fill_prompt = provider.user_prompts[1]
    assert "## 前面已生成节点的 narration 摘要" not in first_fill_prompt
    assert "## 当前节点位置" in first_fill_prompt
    assert "context bleed-through 防御" in first_fill_prompt


def test_r2_6_later_fill_prompts_include_previously_filled_summary():
    """Each fill prompt for index >= 1 must list earlier-filled node ids
    so the LLM can see what setting / characters have been described
    already and stop repeating them."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    fill_prompts = provider.user_prompts[1:]
    # Fill #2 (index 1): summary must reference n_arrival
    assert "## 前面已生成节点的 narration 摘要" in fill_prompts[1]
    assert "n_arrival" in fill_prompts[1]
    # Last fill (index 4): must reference all four prior node ids
    last = fill_prompts[-1]
    assert "## 前面已生成节点的 narration 摘要" in last
    for prior_id in (
        "n_arrival",
        "n_confession",
        "n_patrol",
        "n_end_silent",
    ):
        assert prior_id in last, f"last fill prompt missing prior node {prior_id}"


def test_r2_6_fill_prompts_carry_beat_position_with_correct_role():
    """Each fill prompt surfaces beat tag, index/total, and node role."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    fill_prompts = provider.user_prompts[1:]
    total = len(fill_prompts)
    expected_beats = [n["beat"] for n in _VALID_SKELETON_JSON["nodes"]]
    for idx, fp in enumerate(fill_prompts):
        assert "## 当前节点位置" in fp
        assert f"`{expected_beats[idx]}`" in fp
        assert f"第 {idx + 1}/{total} 个节点" in fp
    # Role markers
    assert "节点角色：开场" in fill_prompts[0]
    assert "节点角色：收束" in fill_prompts[-1]
    for fp in fill_prompts[1:-1]:
        assert "节点角色：中段" in fp


def test_r2_6_fill_prompts_render_extras_between_context_and_requirement():
    """R2.6 spec §1.2: new sections appear after the SceneGraphContext
    block (system_time tail) and before '## 本次生成要求'."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        active_clocks=_active_clocks(),
        system_time=_system_time(),
        location_candidates=_location_candidates(),
    )
    assert result.success is True
    # Pick a fill index >= 1 so summary section is present.
    second_fill = provider.user_prompts[2]
    # The few-shot block at the prompt head also renders a full
    # `## 本次生成要求` block per example, so anchor on the LAST occurrence
    # of each header (rfind) — that lands inside the live context block
    # under `## 当前任务`. The R2.6 headers appear only there so find/rfind
    # collapse for them, but symmetry keeps the assertion uniform.
    pos_system_time = second_fill.rfind("## 系统时间")
    pos_summary = second_fill.rfind("## 前面已生成节点的 narration 摘要")
    pos_beat = second_fill.rfind("## 当前节点位置")
    pos_requirement = second_fill.rfind("## 本次生成要求")
    assert pos_system_time != -1
    assert pos_summary != -1
    assert pos_beat != -1
    assert pos_requirement != -1
    assert pos_system_time < pos_summary < pos_beat < pos_requirement


def test_r2_6_fill_prompts_carry_bleed_through_guard_each_node():
    """Hard constraint section appears in every fill prompt (R2.6 §1.4)."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is True
    for idx, fp in enumerate(provider.user_prompts[1:]):
        assert "context bleed-through 防御" in fp, (
            f"fill prompt {idx} missing bleed-through guard"
        )
        assert "不要重复" in fp
        assert "≤ 2 句话" in fp


def test_r2_6_render_previously_filled_summary_truncates_to_recent_5_when_over_budget():
    """Direct unit test on the helper. Skeleton schema caps at 15 nodes
    so the truncation path won't trigger from a real skeleton, but the
    invariant matters: when filled_so_far is large enough that the joined
    body exceeds 2000 chars, fall back to the most recent 5 entries.
    """
    from generator.prompts.scene.fill import render_previously_filled_summary
    # 25 entries with 100-char narrations. Each rendered line is
    # "- n_node_XX: " (13) + 80-char narration preview + "..." (3) = 96 chars,
    # joined with "\n" → 25*96 + 24 ≈ 2424 chars body, well over 2000.
    long_narration = "X" * 100
    filled = [(f"n_node_{i:02d}", long_narration) for i in range(25)]
    summary = render_previously_filled_summary(filled)
    body = summary.split("\n\n", 1)[1]
    assert len(body) <= 2000
    # Recent 5 only: n_node_20 .. n_node_24 in, n_node_19 and n_node_00 out.
    assert "n_node_24" in body
    assert "n_node_20" in body
    assert "n_node_19" not in body
    assert "n_node_00" not in body


def test_r2_6_render_previously_filled_summary_empty_input_returns_empty_string():
    """First-node case: helper returns empty string, NOT a header-only stub."""
    from generator.prompts.scene.fill import render_previously_filled_summary
    assert render_previously_filled_summary([]) == ""


def test_r2_6_render_previously_filled_summary_caps_per_node_at_80_chars():
    """Each per-node line caps narration at 80 chars + literal '...'."""
    from generator.prompts.scene.fill import render_previously_filled_summary
    long_narr = "推开沉重的橡木门" * 20  # ~160 漢字
    summary = render_previously_filled_summary([("n_a", long_narr)])
    body = summary.split("\n\n", 1)[1]
    # Body is exactly one line: "- n_a: " + 80 chars + "..."
    assert body.startswith("- n_a: ")
    after_prefix = body[len("- n_a: "):]
    assert len(after_prefix) == 80 + 3  # 80-char preview + "..."
    assert after_prefix.endswith("...")


def test_r2_6_extra_user_context_is_none_for_t1_6_solo_callers():
    """Backwards compat: T-1.6 single-node generate_node callers don't
    pass extra_user_context, so NodeRequirement defaults it to None and
    assemble_context_block omits the inserted block entirely."""
    from generator.context_assembler import (
        GraphContext,
        NodeRequirement,
        assemble_context_block,
    )
    ctx = GraphContext(scene_anchor="scene_solo_test")
    req = NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_x",
        narrative_intent="test intent",
    )
    assert req.extra_user_context is None
    block = assemble_context_block(ctx, req)
    # None of the R2.6 section headers should appear when extra is None.
    assert "## 前面已生成节点的 narration 摘要" not in block
    assert "## 当前节点位置" not in block
    assert "context bleed-through 防御" not in block


# ---------------------------------------------------------------------------
# R2.9: ProviderError diagnostic metadata propagates through the result chain
# ---------------------------------------------------------------------------


def test_skeleton_phase_provider_error_propagates_failure_metadata():
    """Skeleton-phase ProviderError must carry exception_class +
    http_status into SceneGenerationResult.failure_metadata so the
    scene_experiment envelope can serialise it without reconstructing
    from inner attempts."""
    from generator.llm_provider import ProviderError

    class _FakeStatusError(Exception):
        status_code = 400
        body = "Invalid JSON: additionalProperties not supported"

    err = ProviderError.from_exception(
        _FakeStatusError("schema rejected"),
        message="Gemini API error: schema rejected",
    )
    provider = _ScriptedProvider([err])
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "provider_error"
    md = result.failure_metadata
    assert isinstance(md, dict)
    assert md["http_status"] == 400
    assert md["exception_class"].endswith("._FakeStatusError")
    assert "additionalProperties" in (md["response_body_excerpt"] or "")


def test_fill_phase_provider_error_propagates_failure_metadata():
    """Fill-phase ProviderError flows GenerationResult → FillResult →
    SceneGenerationResult with metadata intact. Mirrors the
    baseline_007 fill-stage failure shape (9/15 of those rows)."""
    from generator.llm_provider import ProviderError

    class _FakeTimeoutError(Exception):
        pass

    err = ProviderError.from_exception(
        _FakeTimeoutError("Read timeout: 120s"),
        message="Gemini call failed: Read timeout",
    )
    # Skeleton succeeds, first fill call raises.
    provider = _ScriptedProvider(
        [
            _make_response(copy.deepcopy(_VALID_SKELETON_JSON)),
            err,
        ]
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "provider_error"
    md = result.failure_metadata
    assert isinstance(md, dict)
    assert md["http_status"] is None  # timeouts have no HTTP status
    assert md["exception_class"].endswith("._FakeTimeoutError")


# ---------------------------------------------------------------------------
# T-3.3 (ADR-024) — long-conversation-consistency C-tier prompt wiring
# ---------------------------------------------------------------------------


def _three_prior_summaries() -> list[PriorSceneSummary]:
    """Three caller-supplied summaries; below the 5-entry cap so they
    all land in the rendered prompts unchanged."""
    return [
        PriorSceneSummary(
            scene_id="scene_history_a",
            summary="Vellin 与 Corvan 在兰岭分道",
            key_state_paths=["world.scene_count", "flag.glades_oath"],
        ),
        PriorSceneSummary(
            scene_id="scene_history_b",
            summary="驿站夜火被袭",
            key_state_paths=["faction.iron_oath.discipline"],
        ),
        PriorSceneSummary(
            scene_id="scene_history_c",
            summary="Vellin 接到铁誓巡逻官的传讯",
            key_state_paths=["relationship.vellin.trust"],
        ),
    ]


def test_t_3_3_skeleton_prompt_includes_prior_scene_summaries():
    """When `prior_scene_summaries` is supplied, the skeleton phase's
    user prompt must carry the rendered ## 前置场景概要 section
    immediately above ## 当前任务."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    summaries = _three_prior_summaries()
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        prior_scene_summaries=summaries,
    )
    assert result.success is True
    skeleton_prompt = provider.user_prompts[0]
    assert "前置场景概要" in skeleton_prompt
    for summary in summaries:
        assert f"[{summary.scene_id}]" in skeleton_prompt
        assert summary.summary in skeleton_prompt
    # Section must sit before "## 当前任务" so it reads as historical context.
    assert skeleton_prompt.index("前置场景概要") < skeleton_prompt.index("## 当前任务")


def test_t_3_3_fill_prompts_include_prior_scene_summaries():
    """Every fill prompt must carry the same `## 前置场景概要` block — the
    LLM should see the long-conversation context on every node call,
    not only the skeleton phase."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    summaries = _three_prior_summaries()
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        prior_scene_summaries=summaries,
    )
    assert result.success is True
    fill_prompts = provider.user_prompts[1:]
    assert len(fill_prompts) == 5
    for idx, prompt in enumerate(fill_prompts):
        assert "前置场景概要" in prompt, f"fill prompt {idx} missing summaries section"
        for summary in summaries:
            assert f"[{summary.scene_id}]" in prompt


def test_t_3_3_skeleton_and_fill_prompts_omit_section_without_summaries():
    """Empty `prior_scene_summaries` must leave skeleton + fill prompts
    byte-identical to pre-T-3.3 behaviour — no header, no empty stub."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        # prior_scene_summaries left as None
    )
    assert result.success is True
    for prompt in provider.user_prompts:
        assert "前置场景概要" not in prompt


def test_t_3_3_skeleton_prompt_caps_summaries_at_five():
    """Eight summaries → only 5 land in the prompt (recent + boundary
    heuristic). Verifies the strategy applies the same truncation
    logic that `compute_prior_summary_token_metrics` records."""
    fill_responses = _build_fill_responses_for_valid_skeleton(_VALID_SKELETON_JSON)
    provider = _ScriptedProvider(
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fill_responses
    )
    summaries = [
        PriorSceneSummary(
            scene_id=f"scene_h{i}",
            summary=f"history-{i}",
            key_state_paths=[],
        )
        for i in range(8)
    ]
    result = generate_scene_skeleton_first(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        provider=provider,
        prior_scene_summaries=summaries,
    )
    assert result.success is True
    skeleton_prompt = provider.user_prompts[0]
    # Recent 5 (h3..h7) must appear; oldest 3 (h0..h2) must not.
    for kept in ("scene_h3", "scene_h4", "scene_h5", "scene_h6", "scene_h7"):
        assert f"[{kept}]" in skeleton_prompt
    for dropped in ("scene_h0", "scene_h1", "scene_h2"):
        assert f"[{dropped}]" not in skeleton_prompt
