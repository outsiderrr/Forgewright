"""T-3Y-1 子 goal 1: Forward Planner 模块 B state_summary 单元测试."""
from __future__ import annotations

from generator.forward_planner.state_summary import compute_player_known_info


def _base_graph() -> dict:
    return {
        "player_known_info": [
            {"knowledge_path": "knowledge.wright_dead", "stage": 1},
            {"knowledge_path": "knowledge.lucy_known_to_player"},
            {"knowledge_path": "knowledge.gangster_watching_lucy"},
        ]
    }


def test_filter_by_state_only_set_known_returned() -> None:
    state = {
        "knowledge.wright_dead": True,
        "knowledge.lucy_known_to_player": True,
        # gangster_watching_lucy 未 set
    }
    result = compute_player_known_info(_base_graph(), state)
    paths = {item["knowledge_path"] for item in result}
    assert paths == {
        "knowledge.wright_dead",
        "knowledge.lucy_known_to_player",
    }


def test_empty_state_returns_empty_list() -> None:
    result = compute_player_known_info(_base_graph(), current_state={})
    assert result == []


def test_falsy_value_is_treated_as_unknown() -> None:
    """state 中 path 存在但 value falsy（False / 0 / None / []）当作未 set."""
    state = {
        "knowledge.wright_dead": False,
        "knowledge.lucy_known_to_player": 0,
        "knowledge.gangster_watching_lucy": None,
    }
    result = compute_player_known_info(_base_graph(), state)
    assert result == []


def test_preserves_stage_field() -> None:
    state = {"knowledge.wright_dead": True}
    result = compute_player_known_info(_base_graph(), state)
    assert len(result) == 1
    assert result[0]["stage"] == 1


def test_graph_without_player_known_info_returns_empty() -> None:
    """player_known_info 字段缺失（optional）→ 返回空列表，不抛异常."""
    result = compute_player_known_info({}, {"knowledge.anything": True})
    assert result == []
