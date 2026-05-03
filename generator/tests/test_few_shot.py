"""T-2.0 R2 cleanup: composite-condition few-shot demos parse cleanly.

The two hand-written demos appended by `load_iron_oath_few_shot` exist to
make the StateCondition leaf-vs-composite split unambiguous. The contract
they need to honour:

  * The `expected_node` of each demo passes the auto-generated Pydantic
    `Node` model unchanged (i.e. it would pass `/schema/` validation if
    fed to `validator.schema_check`).
  * The composite-condition options round-trip through
    `StateCondition.model_validate` and surface the expected branch
    (`StateConditionAllOf`, `StateConditionAnyOf`) so we know the model
    parser is actually picking the composite shape.

Keeping these as schema-level checks (not deep semantic checks) since the
LLM prompts only need the *shape* to be unambiguous; semantics are the
generator's responsibility.
"""
from __future__ import annotations

import json
from pathlib import Path

from generator.models import (
    Node,
    Option,
    StateCondition,
    StateConditionAllOf,
    StateConditionAnyOf,
    StateConditionLeaf,
    StateConditionNot,
)
from generator.prompts import (
    FewShotPair,
    load_composite_condition_few_shot,
    load_iron_oath_few_shot,
)
from generator.prompts.few_shot import _FEW_SHOT_TEXT_OVERRIDES, _SCENE_PATH


def test_iron_oath_few_shot_now_appends_composite_demos():
    """The bundled few-shot is the 5 scene pairs + 2 composite demos."""
    pairs = load_iron_oath_few_shot()
    assert len(pairs) == 7
    composite_pairs = pairs[-2:]
    composite_node_ids = [p.expected_node["node_id"] for p in composite_pairs]
    assert composite_node_ids == ["demo_all_of_not", "demo_any_of"]


def test_composite_demos_each_have_one_composite_option():
    pairs = load_composite_condition_few_shot()
    assert len(pairs) == 2

    # Demo 1: all_of with a nested not.
    all_of_pair = pairs[0]
    assert isinstance(all_of_pair, FewShotPair)
    all_of_node = Node.model_validate(all_of_pair.expected_node)
    composite_options = [o for o in all_of_node.options if o.condition is not None]
    assert len(composite_options) == 1
    cond = composite_options[0].condition
    assert isinstance(cond, StateCondition)
    assert isinstance(cond.root, StateConditionAllOf)
    # The all_of has exactly two children: a leaf `has` and a `not`-wrapping leaf.
    assert len(cond.root.all_of) == 2
    child_kinds = [type(c.root) for c in cond.root.all_of]
    assert StateConditionLeaf in child_kinds
    assert StateConditionNot in child_kinds

    # Demo 2: any_of with two leaf children.
    any_of_pair = pairs[1]
    any_of_node = Node.model_validate(any_of_pair.expected_node)
    composite_options = [o for o in any_of_node.options if o.condition is not None]
    assert len(composite_options) == 1
    cond = composite_options[0].condition
    assert isinstance(cond.root, StateConditionAnyOf)
    assert len(cond.root.any_of) == 2
    assert all(isinstance(c.root, StateConditionLeaf) for c in cond.root.any_of)


def test_composite_demo_input_context_explains_state():
    """Each demo's input_context must spell out the precondition state so
    the model can see *why* the composite is satisfied — that's the whole
    point of the hand-built demo (the scene-derived ones don't have this)."""
    all_of_pair, any_of_pair = load_composite_condition_few_shot()

    assert "player.traits" in all_of_pair.input_context
    assert "observant" in all_of_pair.input_context
    assert "flag.composite_demo_used" in all_of_pair.input_context

    assert "relationship.demo_npc.trust" in any_of_pair.input_context
    assert "player.bonds" in any_of_pair.input_context
    # any_of demo must make it explicit that EITHER branch alone is enough.
    assert "任一" in any_of_pair.input_context or "其一" in any_of_pair.input_context


def test_all_seven_few_shot_options_respect_25_char_text_cap():
    """T-2.0 R3 cleanup (review 4.1): every Option.text in the entire
    `load_iron_oath_few_shot()` block — both the 5 scene-derived demos and
    the 2 hand-built composite demos — must obey the 25-字 cap. The
    scene-derived 5 originally had 3 long options; few_shot.py overrides
    them in the prompt copy without touching /content/.

    CJK characters count as 1 by Python `len`; ascii letters / digits count
    as one slot too — anything stricter would mis-handle bracketed action
    prefixes and short proper nouns ("Vellin", "Corvan") that the gold
    scene relies on. 25 is generous enough to cover both."""
    for pair in load_iron_oath_few_shot():
        for opt in pair.expected_node["options"]:
            text = opt["text"]
            assert len(text) <= 25, (
                f"{pair.expected_node['node_id']}/{opt['option_id']}: "
                f"text='{text}' length={len(text)} > 25"
            )


def test_few_shot_text_overrides_target_long_originals_only():
    """T-2.0 R3 cleanup (review 4.1): every entry in _FEW_SHOT_TEXT_OVERRIDES
    must (a) point at an option whose *original* text in /content/ exceeds
    the 25-字 cap (otherwise the override is dead weight), and (b) supply a
    replacement that fits under the cap. Keeps the override table from
    drifting into a generic "I don't like this wording" mechanism."""
    gold_scene = json.loads(Path(_SCENE_PATH).read_text(encoding="utf-8"))

    assert _FEW_SHOT_TEXT_OVERRIDES, "override table must not be empty"

    for (node_id, option_id), replacement in _FEW_SHOT_TEXT_OVERRIDES.items():
        gold_node = gold_scene["nodes"].get(node_id)
        assert gold_node is not None, f"override targets missing node: {node_id}"
        gold_options = {o["option_id"]: o for o in gold_node.get("options") or []}
        assert option_id in gold_options, (
            f"override targets missing option: {node_id}/{option_id}"
        )
        original_text = gold_options[option_id]["text"]
        assert len(original_text) > 25, (
            f"override is unnecessary — original {node_id}/{option_id} text "
            f"is already {len(original_text)} chars (≤ 25)"
        )
        assert len(replacement) <= 25, (
            f"override replacement for {node_id}/{option_id} is itself > 25 "
            f"chars: '{replacement}' (length {len(replacement)})"
        )


def test_few_shot_overrides_actually_applied_to_loaded_pairs():
    """The override table is plumbed through `load_iron_oath_few_shot`: each
    (node_id, option_id) override surfaces with the replacement text, not
    the gold-scene original."""
    pairs_by_node = {p.expected_node["node_id"]: p for p in load_iron_oath_few_shot()}
    for (node_id, option_id), replacement in _FEW_SHOT_TEXT_OVERRIDES.items():
        pair = pairs_by_node[node_id]
        opts = {o["option_id"]: o for o in pair.expected_node["options"]}
        assert opts[option_id]["text"] == replacement, (
            f"override for {node_id}/{option_id} not applied — saw "
            f"'{opts[option_id]['text']}'"
        )


def test_few_shot_overrides_do_not_mutate_gold_scene_on_disk():
    """Calling `load_iron_oath_few_shot` multiple times must not write the
    short replacements back into the cached or on-disk gold scene — the
    /content/ copy is the truth source and the overrides are display-only.

    Concretely: read the on-disk JSON twice (once before the loader fires,
    once after) and confirm the long originals are still present."""
    raw_before = json.loads(Path(_SCENE_PATH).read_text(encoding="utf-8"))
    before = {
        (n_id, o["option_id"]): o["text"]
        for n_id, n in raw_before["nodes"].items()
        for o in n.get("options") or []
    }

    # Trigger the loader twice — both calls must see the override applied
    # AND leave /content/ untouched.
    load_iron_oath_few_shot()
    load_iron_oath_few_shot()

    raw_after = json.loads(Path(_SCENE_PATH).read_text(encoding="utf-8"))
    after = {
        (n_id, o["option_id"]): o["text"]
        for n_id, n in raw_after["nodes"].items()
        for o in n.get("options") or []
    }
    assert before == after
    # And the override targets in /content/ are still the original (long) text.
    for key in _FEW_SHOT_TEXT_OVERRIDES:
        assert len(after[key]) > 25


def test_composite_demo_location_ref_in_candidates():
    """T-2.0 R4 cleanup: each demo's location_ref must be one of the
    location_id values it advertises in the input_context block."""
    for pair in load_composite_condition_few_shot():
        loc_ref = pair.expected_node["location_ref"]
        assert f'"location_id": "{loc_ref}"' in pair.input_context


def test_composite_demo_options_are_valid_pydantic_options():
    """Round-trip every option in both demos through the Option Pydantic
    model so we catch any subtle schema drift in the demos themselves."""
    for pair in load_composite_condition_few_shot():
        for opt in pair.expected_node["options"]:
            Option.model_validate(opt)
