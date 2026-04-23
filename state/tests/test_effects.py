"""T-0.7：apply_effect 对 5 种 op 的正负样本 + schema 违反。"""
from __future__ import annotations

import pytest

from state.effects import apply_effect
from state.world_state import WorldState


# ----- set -----

def test_set_writes_value() -> None:
    s = WorldState()
    apply_effect(s, {"op": "set", "path": "flag.read_the_room_used", "value": True})
    assert s.get("flag.read_the_room_used") is True


def test_set_overwrites_previous_value() -> None:
    s = WorldState()
    s.set("flag.x", "old")
    apply_effect(s, {"op": "set", "path": "flag.x", "value": "new"})
    assert s.get("flag.x") == "new"


# ----- inc -----

def test_inc_from_zero_default() -> None:
    s = WorldState()
    apply_effect(s, {"op": "inc", "path": "relationship.vellin.trust", "value": 2})
    assert s.get("relationship.vellin.trust") == 2


def test_inc_adds_to_existing_numeric() -> None:
    s = WorldState()
    s.set("relationship.vellin.trust", 3)
    apply_effect(s, {"op": "inc", "path": "relationship.vellin.trust", "value": 1})
    assert s.get("relationship.vellin.trust") == 4


def test_inc_on_non_numeric_raises_type_error() -> None:
    s = WorldState()
    s.set("flag.x", "not-a-number")
    with pytest.raises(TypeError):
        apply_effect(s, {"op": "inc", "path": "flag.x", "value": 1})


# ----- dec -----

def test_dec_from_zero_default() -> None:
    s = WorldState()
    apply_effect(s, {"op": "dec", "path": "relationship.corvan.trust", "value": 2})
    assert s.get("relationship.corvan.trust") == -2


def test_dec_subtracts_from_existing() -> None:
    s = WorldState()
    s.set("faction.iron_oath.reputation", 5)
    apply_effect(s, {"op": "dec", "path": "faction.iron_oath.reputation", "value": 2})
    assert s.get("faction.iron_oath.reputation") == 3


def test_dec_on_non_numeric_raises_type_error() -> None:
    s = WorldState()
    s.set("flag.x", [1, 2])
    with pytest.raises(TypeError):
        apply_effect(s, {"op": "dec", "path": "flag.x", "value": 1})


def test_inc_with_non_numeric_value_raises_type_error() -> None:
    s = WorldState()
    with pytest.raises(TypeError):
        apply_effect(s, {"op": "inc", "path": "r.v", "value": "not-a-number"})


# ----- add -----

def test_add_creates_list_and_appends() -> None:
    s = WorldState()
    apply_effect(s, {"op": "add", "path": "player.traits", "value": "observant"})
    assert s.get("player.traits") == ["observant"]


def test_add_skips_duplicate() -> None:
    s = WorldState()
    s.set("player.traits", ["observant"])
    apply_effect(s, {"op": "add", "path": "player.traits", "value": "observant"})
    assert s.get("player.traits") == ["observant"]


def test_add_on_non_list_raises_type_error() -> None:
    s = WorldState()
    s.set("player.traits", "observant")  # 字符串不是 list
    with pytest.raises(TypeError):
        apply_effect(s, {"op": "add", "path": "player.traits", "value": "new"})


# ----- remove -----

def test_remove_from_list() -> None:
    s = WorldState()
    s.set("player.traits", ["observant", "decisive"])
    apply_effect(s, {"op": "remove", "path": "player.traits", "value": "observant"})
    assert s.get("player.traits") == ["decisive"]


def test_remove_missing_path_is_noop() -> None:
    s = WorldState()
    apply_effect(s, {"op": "remove", "path": "player.traits", "value": "observant"})
    assert s.get("player.traits") is None


def test_remove_on_non_list_raises_type_error() -> None:
    s = WorldState()
    s.set("player.traits", "observant")
    with pytest.raises(TypeError):
        apply_effect(s, {"op": "remove", "path": "player.traits", "value": "observant"})


# ----- schema violations -----

def test_effect_missing_required_field_raises_value_error() -> None:
    s = WorldState()
    with pytest.raises(ValueError):
        apply_effect(s, {"op": "set", "path": "flag.x"})  # 缺 value


def test_effect_unknown_op_raises_value_error_via_schema_enum() -> None:
    s = WorldState()
    with pytest.raises(ValueError):
        apply_effect(s, {"op": "nuke", "path": "flag.x", "value": True})


def test_effect_extra_property_raises_value_error() -> None:
    s = WorldState()
    with pytest.raises(ValueError):
        apply_effect(
            s,
            {"op": "set", "path": "flag.x", "value": True, "surprise": 1},
        )
