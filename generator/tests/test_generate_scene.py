"""T-2.6 scene-level generation contract tests.

Six scenarios required by STAGE_2_TASKS §T-2.6:

  1. skeleton + N fills all valid                                   → success
  2. skeleton fails first attempt, second attempt valid             → success
  3. one fill node fails 3 times                                    → failure_reason="fill_node_invalid"
  4. budget pre-flight rejects                                      → failure_reason="budget_exceeded"
  5. mechanical pre-check (T-2.4) rejects first attempt, second OK  → success
  6. SceneGraphContext field-presence smoke test (active_clocks /
     location_candidates / state_path_slug / relations_matrix /
     system_time / participating_characters all populated)          → string assertions

No real Gemini API calls — `_ScriptedProvider` is fed a per-scenario list of
canned responses. Budget isolation pins DAILY_BUDGET_USD / PER_CALL_BUDGET_USD
so tests stay deterministic regardless of `~/.cache` state.
"""
from __future__ import annotations

import copy
import json

import pytest

from generator.context_assembler import (
    SceneGraphContext,
    assemble_scene_context_block,
)
from generator.generate_scene import (
    SceneResult,
    build_scene_graph_context,
    estimate_scene_cost,
    generate_scene,
)
from generator.llm_provider import StructuredResponse
from generator.scene_strategies import (
    GraphSkeleton,
    SceneSetting,
    SkeletonNode,
)


# ---------------------------------------------------------------------------
# Fixtures: budget isolation + per-test ontology
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


class _ScriptedProvider:
    """Linear scripted provider — same shape as test_scene_strategies."""

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
        # Tiny per-token rate so estimate_scene_cost stays well under
        # SCENE_BUDGET_USD in the happy-path scenarios.
        return (input_tokens + output_tokens) * 1e-7


# ---------------------------------------------------------------------------
# Ontology + scene shape used across scenarios
# ---------------------------------------------------------------------------


def _ontology() -> dict:
    """Minimal but realistic ontology — character cards include the
    state_path_slug + relations + dramatic_triggers fields T-2.6
    contract requires the SceneGraphContext to surface."""
    return {
        "system_time": {"scene_count": 7, "long_rest_count": 3},
        "clocks": [
            {
                "id": "clock_iron_oath_pursuit",
                "name": "Iron Oath Pursuit",
                "scope": "faction",
                "ticks_total": 6,
                "ticks_filled": 2,
                "advance_rule": {"type": "every_n_scenes", "params": {"n": 1}},
            }
        ],
        "chapters": [],
        "entities": [
            {
                "id": "char_vellin",
                "type": "character",
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
                    },
                    {
                        "target_character_ref": "char_aelwin",
                        "relation_type": "context_anchor",
                        "narrative_weight": "context_only",
                    },
                ],
            },
            {
                "id": "char_corvan",
                "type": "character",
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
            {
                "id": "scene_waystation_of_iron_oath",
                "type": "location",
                "display_name": "铁誓驿站",
                "location_type": "scene",
                "parent_location_ref": None,
            },
        ],
    }


def _scene_setting() -> SceneSetting:
    return SceneSetting(
        scene_anchor="scene_waystation_of_iron_oath",
        primary_location_ref="scene_waystation_of_iron_oath",
        chapter_ref="chap_glades",
        expected_node_count_min=5,
        expected_node_count_max=15,
    )


def _participating_npcs() -> list[str]:
    return ["char_vellin", "char_corvan"]


def _target_beats() -> list[str]:
    return [
        "抵达驿站",
        "秘密摊开",
        "巡逻官登场",
        "ending：共谋余韵",
        "ending：告发代价",
    ]


# ---------------------------------------------------------------------------
# Skeleton / fill response builders (lifted from test_scene_strategies.py)
# ---------------------------------------------------------------------------


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


def _valid_filled_node(skel_node: SkeletonNode, allowed_targets: list[str]) -> dict:
    """Schema- and mechanically-valid Node dict.

    Option text is short; effects/condition use compliant state paths;
    unavailable_behavior is in the enum.  The returned node passes both
    `validator.schema_check` and `validator.dialogue_validator` clean.
    """
    if skel_node.type == "end":
        return {
            "node_id": skel_node.node_id,
            "type": "end",
            "narration": f"（ending：节拍 {skel_node.beat}）",
            "speaker_ref": None,
            "location_ref": "scene_waystation_of_iron_oath",
            "on_enter_effects": [],
            "options": [],
        }
    options = []
    targets = allowed_targets or ["unknown"]
    for i in range(skel_node.expected_branch_count):
        options.append(
            {
                "option_id": f"opt_{skel_node.node_id}_{i+1}",
                "text": f"选项 {i+1}",
                "target_node_id": targets[i % len(targets)],
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


def _build_fill_responses(skeleton_dict: dict) -> list[StructuredResponse]:
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
    return [
        _make_response(_valid_filled_node(n, skel.get_allowed_targets(n.node_id)))
        for n in skel_nodes
    ]


def _full_happy_script() -> list[StructuredResponse]:
    """Skeleton + 5 fill responses. Six provider calls in total."""
    return [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + _build_fill_responses(
        _VALID_SKELETON_JSON
    )


# ---------------------------------------------------------------------------
# Scenario 1: full happy path → success
# ---------------------------------------------------------------------------


def test_scenario_1_happy_path():
    provider = _ScriptedProvider(_full_happy_script())
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert isinstance(result, SceneResult)
    assert result.success is True
    assert result.failure_reason is None
    assert result.graph is not None
    assert result.graph["schema_version"] == "0.1.1"
    assert set(result.graph["nodes"].keys()) == {
        "n_arrival",
        "n_confession",
        "n_patrol",
        "n_end_silent",
        "n_end_iron",
    }
    # 1 skeleton call + 5 fill calls
    assert provider.call_count == 6
    assert len(result.inner_results) == 1
    assert result.total_cost_usd > 0
    # No issues at either gate.
    assert result.schema_issues == []
    assert result.mechanical_issues == {}


# ---------------------------------------------------------------------------
# Scenario 2: skeleton first call fails, second attempt is valid → success
# ---------------------------------------------------------------------------


def test_scenario_2_skeleton_first_invalid_then_valid():
    """The strategy's skeleton phase has a 3-attempt internal retry —
    we exercise that here. First skeleton response is structurally bad
    (empty nodes), retry succeeds, then fills land."""
    bad_skeleton = {
        "nodes": [],
        "edges": [],
        "entry_node_id": "",
        "end_node_ids": [],
    }
    script = (
        [_make_response(copy.deepcopy(bad_skeleton))]
        + [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
        + _build_fill_responses(_VALID_SKELETON_JSON)
    )
    provider = _ScriptedProvider(script)
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is True
    assert result.failure_reason is None
    assert result.graph is not None
    # Bad skeleton + valid skeleton + 5 fills = 7 calls.
    assert provider.call_count == 7
    # One outer attempt — strategy handled the retry internally.
    assert len(result.inner_results) == 1
    assert len(result.inner_results[0].skeleton_attempts) == 2


# ---------------------------------------------------------------------------
# Scenario 3: one fill node fails 3x → failure_reason="fill_node_invalid"
# ---------------------------------------------------------------------------


def test_scenario_3_fill_node_three_failures():
    fill_responses = _build_fill_responses(_VALID_SKELETON_JSON)
    # Drop required `narration` to force a schema error on n_arrival
    # three attempts in a row.
    bad_node = copy.deepcopy(fill_responses[0].content)
    del bad_node["narration"]
    bad_response = _make_response(bad_node)

    script = [
        _make_response(copy.deepcopy(_VALID_SKELETON_JSON)),
        bad_response,
        _make_response(copy.deepcopy(bad_node)),
        _make_response(copy.deepcopy(bad_node)),
    ]
    provider = _ScriptedProvider(script)

    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "fill_node_invalid"
    assert result.failure_node_id == "n_arrival"
    # 1 skeleton + 3 bad fills = 4 calls; outer loop must NOT retry the
    # whole strategy on a fill_node_invalid (those already exhausted).
    assert provider.call_count == 4
    assert len(result.inner_results) == 1


# ---------------------------------------------------------------------------
# Scenario 4: budget pre-flight rejects → failure_reason="budget_exceeded"
# ---------------------------------------------------------------------------


def test_scenario_4_budget_pre_flight_rejects(monkeypatch):
    """Cap SCENE_BUDGET_USD below the estimate — generate_scene must
    return success=False before issuing a single LLM call."""
    monkeypatch.setenv("SCENE_BUDGET_USD", "0.0001")
    provider = _ScriptedProvider([])  # empty script — must not be hit
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "budget_exceeded"
    assert provider.call_count == 0
    assert result.graph is None


def test_scenario_4b_daily_budget_pre_flight_rejects(monkeypatch):
    """Same gate, different ceiling: a tiny daily budget fires the
    `today + estimate > daily` branch."""
    monkeypatch.setenv("DAILY_BUDGET_USD", "0.0001")
    provider = _ScriptedProvider([])
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is False
    assert result.failure_reason == "budget_exceeded"
    assert provider.call_count == 0


# ---------------------------------------------------------------------------
# Scenario 5: mechanical pre-check rejects first attempt, retry succeeds
# ---------------------------------------------------------------------------


def _build_mechanically_bad_arrival(allowed_targets: list[str]) -> dict:
    """Returns an n_arrival node whose first option violates OPT_LEN_OVER.

    Schema-valid (option.text has no maxLength in the schema), but
    mechanical pre-check rejects 26+ Chinese chars.
    """
    skel = SkeletonNode(
        node_id="n_arrival",
        type="dialogue",
        beat="抵达驿站",
        speaker_ref="char_vellin",
        expected_branch_count=3,
    )
    node = _valid_filled_node(skel, allowed_targets)
    long_chinese = "字" * 30  # 30 漢字 → > 25 → OPT_LEN_OVER
    node["options"][0]["text"] = long_chinese
    return node


def test_scenario_5_mechanical_invalid_then_valid():
    """First strategy run produces a graph with an OPT_LEN_OVER error on
    n_arrival; outer loop retries and the second strategy run is clean.

    This is the v1.0 critique 3.4 integration test: validate_graph_mechanical
    must surface as a re-feedable failure, not a silent pass.
    """
    skel = GraphSkeleton(
        nodes=[
            SkeletonNode(n["node_id"], n["type"], n["beat"], n.get("speaker_ref"),
                         n["expected_branch_count"])
            for n in _VALID_SKELETON_JSON["nodes"]
        ],
        edges=[tuple(e) for e in _VALID_SKELETON_JSON["edges"]],
        entry_node_id=_VALID_SKELETON_JSON["entry_node_id"],
        end_node_ids=_VALID_SKELETON_JSON["end_node_ids"],
    )

    # Outer attempt 1: skeleton valid, n_arrival has OPT_LEN_OVER, rest fine.
    bad_arrival = _build_mechanically_bad_arrival(skel.get_allowed_targets("n_arrival"))
    attempt1_fills = [_make_response(bad_arrival)]
    for n in skel.nodes[1:]:
        attempt1_fills.append(
            _make_response(_valid_filled_node(n, skel.get_allowed_targets(n.node_id)))
        )

    # Outer attempt 2: skeleton + clean fills (mechanical passes).
    attempt2_fills = _build_fill_responses(_VALID_SKELETON_JSON)

    script = (
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
        + attempt1_fills
        + [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
        + attempt2_fills
    )
    provider = _ScriptedProvider(script)
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
        max_retries=2,
    )
    assert result.success is True
    assert result.failure_reason is None
    assert result.graph is not None
    # Two outer attempts — first failed mechanical, second succeeded.
    assert len(result.inner_results) == 2
    # 12 calls: 6 (attempt 1) + 6 (attempt 2).
    assert provider.call_count == 12
    # The terminal SceneResult clears earlier issues (we only carry them
    # through as last_* state in the failure path).
    assert result.mechanical_issues == {}


def test_scenario_5b_mechanical_invalid_exhausts_retries():
    """Every outer attempt produces the same OPT_LEN_OVER violation —
    after max_retries+1 = 3 attempts, generate_scene must report
    failure_reason='mechanical_invalid' and surface the issue list."""
    skel = GraphSkeleton(
        nodes=[
            SkeletonNode(n["node_id"], n["type"], n["beat"], n.get("speaker_ref"),
                         n["expected_branch_count"])
            for n in _VALID_SKELETON_JSON["nodes"]
        ],
        edges=[tuple(e) for e in _VALID_SKELETON_JSON["edges"]],
        entry_node_id=_VALID_SKELETON_JSON["entry_node_id"],
        end_node_ids=_VALID_SKELETON_JSON["end_node_ids"],
    )

    def attempt_script() -> list[StructuredResponse]:
        bad_arrival = _build_mechanically_bad_arrival(
            skel.get_allowed_targets("n_arrival")
        )
        fills = [_make_response(bad_arrival)]
        for n in skel.nodes[1:]:
            fills.append(
                _make_response(_valid_filled_node(n, skel.get_allowed_targets(n.node_id)))
            )
        return [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))] + fills

    script = attempt_script() + attempt_script() + attempt_script()
    provider = _ScriptedProvider(script)
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
        max_retries=2,
    )
    assert result.success is False
    assert result.failure_reason == "mechanical_invalid"
    assert provider.call_count == 18  # 3 attempts × 6 calls
    assert len(result.inner_results) == 3
    assert "n_arrival" in result.mechanical_issues
    issues = result.mechanical_issues["n_arrival"]
    assert any(i.code == "OPT_LEN_OVER" for i in issues)


# ---------------------------------------------------------------------------
# Scenario 6: SceneGraphContext field-presence smoke test
# ---------------------------------------------------------------------------


def test_scenario_6_scene_graph_context_fields_present():
    """Every contracted field of SceneGraphContext must be populated from
    the ontology — STAGE_2_TASKS §2.8 + T-2.6 §A-phase completion criteria."""
    scene_ctx = build_scene_graph_context(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
    )
    assert isinstance(scene_ctx, SceneGraphContext)

    # Required scene-level fields
    assert scene_ctx.scene_anchor == "scene_waystation_of_iron_oath"
    assert scene_ctx.chapter_ref == "chap_glades"
    assert scene_ctx.primary_location_ref == "scene_waystation_of_iron_oath"

    # location_candidates pulled from ontology entities[type=="location"]
    assert len(scene_ctx.location_candidates) == 1
    assert scene_ctx.location_candidates[0]["id"] == "scene_waystation_of_iron_oath"

    # participating_characters resolved by id, with state_path_slug present
    assert len(scene_ctx.participating_characters) == 2
    vellin = scene_ctx.participating_characters[0]
    assert vellin["id"] == "char_vellin"
    assert vellin["state_path_slug"] == "vellin"
    assert vellin["character_features"]
    assert vellin["dramatic_triggers"]

    # relations_matrix filtered to core/minor only — context_only dropped
    assert len(scene_ctx.relations_matrix) == 2  # vellin↔corvan from both sides
    assert all(r["narrative_weight"] in ("core", "minor") for r in scene_ctx.relations_matrix)
    assert all("from_character_ref" in r for r in scene_ctx.relations_matrix)
    assert not any(r.get("narrative_weight") == "context_only" for r in scene_ctx.relations_matrix)

    # active_clocks pulled from ontology["clocks"]
    assert len(scene_ctx.active_clocks) == 1
    assert scene_ctx.active_clocks[0]["id"] == "clock_iron_oath_pursuit"

    # system_time pulled from ontology["system_time"]
    assert scene_ctx.system_time == {"scene_count": 7, "long_rest_count": 3}

    # target_beats forwarded from caller
    assert scene_ctx.target_beats == _target_beats()

    # The renderer surfaces every field — sanity that the dataclass
    # isn't silently dropping any contracted section.
    rendered = assemble_scene_context_block(scene_ctx, _scene_setting())
    for keyword in (
        "scene_waystation_of_iron_oath",
        "chap_glades",
        "active_clocks",
        "location_candidates",
        "participating_characters",
        "relations_matrix",
        "system_time",
        "target_beats",
        "vellin",  # state_path_slug surfaces in the JSON dump of the card
        "world.scene_count",
        "world.long_rest_count",
    ):
        assert keyword in rendered, f"missing {keyword!r} in rendered scene context"


# ---------------------------------------------------------------------------
# Bonus: graceful degradation when ontology is sparse
# ---------------------------------------------------------------------------


def test_build_scene_graph_context_degrades_when_npc_missing():
    """An NPC id absent from the ontology returns a stub `{"id": ...}` —
    never a KeyError. The strategy can still render *something* even if
    an upstream type-o slipped through."""
    onto = _ontology()
    scene_ctx = build_scene_graph_context(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=["char_vellin", "char_does_not_exist"],
        ontology=onto,
    )
    assert len(scene_ctx.participating_characters) == 2
    assert scene_ctx.participating_characters[1] == {"id": "char_does_not_exist"}


def test_build_scene_graph_context_falls_back_when_system_time_missing():
    onto = _ontology()
    onto.pop("system_time")
    scene_ctx = build_scene_graph_context(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=onto,
    )
    assert scene_ctx.system_time == {"scene_count": 0, "long_rest_count": 0}


# ---------------------------------------------------------------------------
# estimate_scene_cost smoke test
# ---------------------------------------------------------------------------


def test_estimate_scene_cost_scales_with_node_count():
    """Doubling expected_node_count should ~double the cost (the
    skeleton call is amortised but the N fills dominate)."""

    class _CheapProvider:
        def estimate_cost(self, in_tokens, out_tokens):
            return (in_tokens + out_tokens) * 1e-7

    cheap = _CheapProvider()
    cost_5 = estimate_scene_cost(
        npc_count=2, beat_count=5, expected_node_count=5, provider=cheap
    )
    cost_10 = estimate_scene_cost(
        npc_count=2, beat_count=5, expected_node_count=10, provider=cheap
    )
    assert cost_5 > 0
    assert cost_10 > cost_5
    # At least 1.5× growth (skeleton is fixed; N fills double but
    # provider's linear cost means total ~doubles with a small offset).
    assert cost_10 > cost_5 * 1.5


# ---------------------------------------------------------------------------
# C-phase (review 3.1): never raise — wrap unexpected exceptions
# ---------------------------------------------------------------------------


class _ExplodingEstimateProvider(_ScriptedProvider):
    """estimate_cost raises — used to verify generate_scene catches
    unexpected exceptions in the cost-estimate phase."""

    def estimate_cost(self, input_tokens, output_tokens):
        raise RuntimeError("boom: provider failed to compute cost")


def test_review_3_1_estimate_cost_exception_returns_scene_result():
    provider = _ExplodingEstimateProvider([])
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert isinstance(result, SceneResult)
    assert result.success is False
    assert result.failure_reason == "provider_error"
    assert any("RuntimeError" in m for m in result.schema_issues)
    # No LLM calls before the exception.
    assert provider.call_count == 0


def test_review_3_1_strategy_exception_returns_scene_result():
    """If the strategy itself raises (e.g. a programmer error in a
    downstream module), generate_scene must wrap it into a SceneResult
    rather than propagating to the caller."""

    class _ExplodingStrategyProvider(_ScriptedProvider):
        def generate_structured(self, system_prompt, user_prompt, json_schema):
            self.call_count += 1
            self.user_prompts.append(user_prompt)
            raise RuntimeError("synthetic upstream programmer error")

    provider = _ExplodingStrategyProvider([])
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    # The strategy DOES catch the inner exception itself and surfaces it
    # as failure_reason="provider_error" via its own ProviderError
    # routing — so the graceful-degradation path here is the strategy's,
    # not generate_scene's outer try/except. Either way the contract
    # holds: no exception escapes to the caller.
    assert result.success is False
    assert result.failure_reason in ("provider_error", "skeleton_invalid")


def test_review_3_1_malformed_ontology_returns_scene_result():
    """Pass a non-dict ontology — build_scene_graph_context handles it
    gracefully, but if it didn't, the generate_scene wrapper must catch."""
    provider = _ScriptedProvider(_full_happy_script())
    # Non-dict ontology: build_scene_graph_context returns an empty-ish
    # context. The strategy then runs as-if no characters exist, which
    # the FakeProvider script accommodates.
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology="not a dict",  # type: ignore[arg-type]
        provider=provider,
    )
    # Either it succeeds (graceful degradation) or it fails with a
    # SceneResult — never raises.
    assert isinstance(result, SceneResult)


# ---------------------------------------------------------------------------
# C-phase (review 4.2): generation_trace.slot_assignments on every node
# ---------------------------------------------------------------------------


def test_review_4_2_success_attaches_generation_trace_with_slot_assignments():
    """ADR-019 + STAGE_2_TASKS: T-2.6 must write
    generation_trace.slot_assignments on every node of the success graph.
    """
    provider = _ScriptedProvider(_full_happy_script())
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is True
    assert result.graph is not None
    for node_id, node in result.graph["nodes"].items():
        assert "generation_trace" in node, f"missing trace on {node_id}"
        trace = node["generation_trace"]
        # Required by schema: source.
        assert trace["source"] == "llm"
        # Six legacy keys present (nullable) — needed for downstream
        # tooling that reads them unconditionally.
        for key in (
            "generated_at",
            "model_id",
            "prompt_hash",
            "reviewed_by",
            "reviewed_at",
        ):
            assert key in trace, f"{node_id} trace missing {key}"
        # ADR-019 / review 4.2: slot_assignments dict present (empty in
        # 阶段 2 — no abstract slots yet, but the field's *presence* is
        # the contract).
        assert "slot_assignments" in trace, f"{node_id} trace missing slot_assignments"
        assert isinstance(trace["slot_assignments"], dict)


def test_review_4_2_attached_trace_passes_dialogue_graph_schema():
    """Sanity: the post-attach graph still passes the dialogue_graph
    JSON Schema (generation_trace's seven allowed keys + nullable five
    must satisfy `additionalProperties: false`)."""
    from validator import schema_check as _sc

    provider = _ScriptedProvider(_full_happy_script())
    result = generate_scene(
        scene_setting=_scene_setting(),
        target_beats=_target_beats(),
        participating_npcs=_participating_npcs(),
        ontology=_ontology(),
        provider=provider,
    )
    assert result.success is True
    assert result.graph is not None
    issues = _sc.check(result.graph)
    assert issues == [], f"post-attach graph has schema issues: {issues}"


# ---------------------------------------------------------------------------
# C-phase (review 4.1): outer retry feedback rendered + logged
# ---------------------------------------------------------------------------


def test_review_4_1_outer_retry_logs_feedback_with_issue_codes(caplog):
    """When mechanical pre-check rejects attempt 1, the outer loop must
    log a feedback summary that includes the offending node id + issue
    code (so batch operators see the audit trail).

    Documents the current limit — the LLM doesn't see this string until
    scene_strategies exposes a feedback hook (follow-up). Tests assert
    the *render + log*, not the LLM behaviour.
    """
    import logging as _logging

    skel = GraphSkeleton(
        nodes=[
            SkeletonNode(n["node_id"], n["type"], n["beat"], n.get("speaker_ref"),
                         n["expected_branch_count"])
            for n in _VALID_SKELETON_JSON["nodes"]
        ],
        edges=[tuple(e) for e in _VALID_SKELETON_JSON["edges"]],
        entry_node_id=_VALID_SKELETON_JSON["entry_node_id"],
        end_node_ids=_VALID_SKELETON_JSON["end_node_ids"],
    )
    long_chinese = "字" * 30
    bad_arrival = _valid_filled_node(
        skel.nodes[0], skel.get_allowed_targets("n_arrival")
    )
    bad_arrival["options"][0]["text"] = long_chinese
    attempt1 = [_make_response(bad_arrival)] + [
        _make_response(_valid_filled_node(n, skel.get_allowed_targets(n.node_id)))
        for n in skel.nodes[1:]
    ]
    attempt2 = _build_fill_responses(_VALID_SKELETON_JSON)

    script = (
        [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
        + attempt1
        + [_make_response(copy.deepcopy(_VALID_SKELETON_JSON))]
        + attempt2
    )
    provider = _ScriptedProvider(script)

    with caplog.at_level(_logging.INFO, logger="generator.generate_scene"):
        result = generate_scene(
            scene_setting=_scene_setting(),
            target_beats=_target_beats(),
            participating_npcs=_participating_npcs(),
            ontology=_ontology(),
            provider=provider,
            max_retries=2,
        )
    assert result.success is True

    feedback_records = [
        r.getMessage() for r in caplog.records
        if "OUTER_RETRY_FEEDBACK" in r.getMessage()
    ]
    assert feedback_records, "no outer-retry feedback log line emitted"
    # The log line must mention the failing node + the OPT_LEN_OVER code
    # — that's what makes the audit trail useful.
    joined = "\n".join(feedback_records)
    assert "n_arrival" in joined
    assert "OPT_LEN_OVER" in joined
