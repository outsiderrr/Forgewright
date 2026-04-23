"""T-0.7：evaluate_condition 对 8 种叶 op + 3 种复合 + 嵌套 + schema 违反。"""
from __future__ import annotations

import pytest

from state.conditions import evaluate_condition
from state.world_state import WorldState


def _fresh() -> WorldState:
    s = WorldState()
    s.set("relationship.vellin.trust", 3)
    s.set("relationship.corvan.trust", 2)
    s.set("player.traits", ["observant", "decisive"])
    s.set("player.name", "observant_ranger")
    s.set("flag.blood_letter_seen", True)
    s.set("flag.sworn_silence", False)
    return s


# ----- 8 个叶 op -----

def test_eq_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "eq", "path": "relationship.vellin.trust", "value": 3}) is True


def test_neq_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "neq", "path": "relationship.vellin.trust", "value": 99}) is True


def test_gt_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "gt", "path": "relationship.vellin.trust", "value": 2}) is True


def test_gte_true_boundary() -> None:
    assert evaluate_condition(_fresh(), {"op": "gte", "path": "relationship.corvan.trust", "value": 2}) is True


def test_lt_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "lt", "path": "relationship.corvan.trust", "value": 3}) is True


def test_lte_true_boundary() -> None:
    assert evaluate_condition(_fresh(), {"op": "lte", "path": "relationship.vellin.trust", "value": 3}) is True


def test_has_on_list_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "has", "path": "player.traits", "value": "observant"}) is True


def test_has_not_on_list_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "has_not", "path": "player.traits", "value": "silent"}) is True


# ----- has / has_not 对字符串与缺失 -----

def test_has_on_string_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "has", "path": "player.name", "value": "observant"}) is True


def test_has_on_missing_path_returns_false() -> None:
    assert evaluate_condition(_fresh(), {"op": "has", "path": "player.absent", "value": "x"}) is False


def test_has_not_on_missing_path_returns_true() -> None:
    assert evaluate_condition(_fresh(), {"op": "has_not", "path": "player.absent", "value": "x"}) is True


def test_gt_on_missing_path_returns_false() -> None:
    assert evaluate_condition(_fresh(), {"op": "gt", "path": "player.absent", "value": 0}) is False


def test_eq_on_missing_path_returns_false() -> None:
    assert evaluate_condition(_fresh(), {"op": "eq", "path": "player.absent", "value": 3}) is False


# ----- 复合形态 -----

def test_all_of_true() -> None:
    cond = {
        "all_of": [
            {"op": "has", "path": "player.traits", "value": "observant"},
            {"op": "gte", "path": "relationship.vellin.trust", "value": 3},
        ]
    }
    assert evaluate_condition(_fresh(), cond) is True


def test_all_of_false_when_one_child_false() -> None:
    cond = {
        "all_of": [
            {"op": "has", "path": "player.traits", "value": "observant"},
            {"op": "gt", "path": "relationship.vellin.trust", "value": 99},
        ]
    }
    assert evaluate_condition(_fresh(), cond) is False


def test_any_of_true() -> None:
    cond = {
        "any_of": [
            {"op": "gt", "path": "relationship.vellin.trust", "value": 99},
            {"op": "has", "path": "player.traits", "value": "observant"},
        ]
    }
    assert evaluate_condition(_fresh(), cond) is True


def test_not_inverts_leaf() -> None:
    cond = {"not": {"op": "eq", "path": "flag.blood_letter_seen", "value": False}}
    assert evaluate_condition(_fresh(), cond) is True


def test_nested_all_of_any_of_with_not() -> None:
    # 模仿 SCENE_v0.md N1.opt_read_the_room.condition:
    #   all_of[ has(player.traits, "observant"), not(eq(flag.read_the_room_used, True)) ]
    # 然后再套一层 any_of 做深度 2。
    s = _fresh()
    s.set("flag.read_the_room_used", False)
    cond = {
        "any_of": [
            {
                "all_of": [
                    {"op": "has", "path": "player.traits", "value": "observant"},
                    {"not": {"op": "eq", "path": "flag.read_the_room_used", "value": True}},
                ]
            },
            {"op": "gte", "path": "relationship.corvan.trust", "value": 100},
        ]
    }
    assert evaluate_condition(s, cond) is True


def test_nested_all_of_any_of_false_when_all_branches_fail() -> None:
    s = _fresh()
    s.set("flag.read_the_room_used", True)
    cond = {
        "any_of": [
            {
                "all_of": [
                    {"op": "has", "path": "player.traits", "value": "observant"},
                    {"not": {"op": "eq", "path": "flag.read_the_room_used", "value": True}},
                ]
            },
            {"op": "gte", "path": "relationship.corvan.trust", "value": 100},
        ]
    }
    assert evaluate_condition(s, cond) is False


# ----- schema violations -----

def test_condition_mixing_leaf_and_compound_raises_value_error() -> None:
    with pytest.raises(ValueError):
        evaluate_condition(
            _fresh(),
            {"op": "eq", "path": "a", "value": 1, "all_of": []},
        )


def test_condition_unknown_op_raises_value_error() -> None:
    with pytest.raises(ValueError):
        evaluate_condition(_fresh(), {"op": "matches", "path": "a", "value": "x"})


def test_condition_missing_op_and_compound_raises_value_error() -> None:
    with pytest.raises(ValueError):
        evaluate_condition(_fresh(), {"path": "a", "value": 1})
