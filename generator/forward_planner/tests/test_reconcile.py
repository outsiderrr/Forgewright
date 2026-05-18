"""T-3Y-1 子 goal 1: Forward Planner 模块 C reconcile 单元测试."""
from __future__ import annotations

from generator.forward_planner.reconcile import reconcile


def test_reconcile_pass_when_all_present() -> None:
    intent = {
        "foreground_goal": "r1_wright_double_life.stage_2",
        "background_seeds": ["S2"],
    }
    known = [{"knowledge_path": "knowledge.wright_dead", "stage": 1}]
    result = reconcile(intent, known)
    assert result["verdict"] == "pass"
    assert "stub" in result["reason"]


def test_reconcile_unreachable_when_missing_foreground_goal() -> None:
    intent = {"foreground_goal": None, "background_seeds": []}
    known = [{"knowledge_path": "knowledge.foo"}]
    result = reconcile(intent, known)
    assert result["verdict"] == "unreachable"
    assert "foreground_goal" in result["reason"]


def test_reconcile_unreachable_when_empty_known_info() -> None:
    intent = {
        "foreground_goal": "r1.stage_1",
        "background_seeds": [],
    }
    known: list[dict] = []
    result = reconcile(intent, known)
    assert result["verdict"] == "unreachable"
    assert "relevant_known_info" in result["reason"]


def test_reconcile_unreachable_when_empty_foreground_goal_string() -> None:
    """空字符串 foreground_goal 视为缺失."""
    intent = {"foreground_goal": "", "background_seeds": []}
    known = [{"knowledge_path": "knowledge.foo"}]
    result = reconcile(intent, known)
    assert result["verdict"] == "unreachable"


def test_reconcile_ignores_skill_preconditions_in_stub() -> None:
    """skill_preconditions 参数 T-3Y-1 阶段未消费，传任意值不影响结果."""
    intent = {
        "foreground_goal": "r1.stage_1",
        "background_seeds": ["S1"],
    }
    known = [{"knowledge_path": "knowledge.foo"}]
    result = reconcile(intent, known, skill_preconditions=["skill_psychology"])
    assert result["verdict"] == "pass"
