"""T-3Y-1 子 goal 1: Forward Planner 模块 A intent 单元测试."""
from __future__ import annotations

from generator.forward_planner.intent import compute_intent


def _base_graph() -> dict:
    return {
        "nodes": {
            "node_3_info_offer": {
                "node_id": "node_3_info_offer",
                "type": "dialogue",
                "foreground_goal": "r1_wright_double_life.stage_2",
                "background_seeds": ["S2_vick_dangerous", "S4_country_cottage_cache"],
            },
            "node_empty": {
                "node_id": "node_empty",
                "type": "dialogue",
            },
        }
    }


def test_intent_returns_node_fields() -> None:
    result = compute_intent(_base_graph(), "node_3_info_offer")
    assert result["foreground_goal"] == "r1_wright_double_life.stage_2"
    assert result["background_seeds"] == [
        "S2_vick_dangerous",
        "S4_country_cottage_cache",
    ]


def test_intent_missing_fields_returns_empty() -> None:
    """节点存在但未声明 foreground_goal / background_seeds → 空意图。"""
    result = compute_intent(_base_graph(), "node_empty")
    assert result["foreground_goal"] is None
    assert result["background_seeds"] == []


def test_intent_unknown_node_returns_empty() -> None:
    result = compute_intent(_base_graph(), "node_does_not_exist")
    assert result["foreground_goal"] is None
    assert result["background_seeds"] == []


def test_intent_background_seeds_is_fresh_list() -> None:
    """返回的 list 不应是节点字段的别名（保护原 graph 不被外部 mutation 污染）。"""
    g = _base_graph()
    result = compute_intent(g, "node_3_info_offer")
    result["background_seeds"].append("S_INJECTED")
    assert "S_INJECTED" not in g["nodes"]["node_3_info_offer"]["background_seeds"]
