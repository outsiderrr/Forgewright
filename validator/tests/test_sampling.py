"""T-2.7 §2B：sampling + 有界符号执行测试 (ADR-021)。

覆盖：
  - 《铁誓驿站》gold scene N=100 全 reach end + 0 condition_unsatisfiable
  - 死锁图：2A DEAD_END + 2B 抽样命中失败样本
  - 有界符号执行：人造小定义域可枚举所有
  - 有界符号执行反例：构造 entry 永远不可达 end 的 state 组合
"""
from __future__ import annotations

import json
from pathlib import Path

from validator import (
    SamplingResult,
    SymbolicResult,
    validate_graph_bounded_symbolic,
    validate_graph_sampling,
    validate_graph_topology,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_SCENE = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"


def _load_gold() -> dict:
    return json.loads(GOLD_SCENE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Gold scene 2B pass — T-2.7 完成标志 (b)
# ---------------------------------------------------------------------------

def test_gold_scene_n100_all_reach_end():
    """ADR-021 完成标志措辞：抽样 N=100 全 reach end + 0 condition_unsatisfiable。"""
    initial = {
        # 让 opt_read_the_room (player.traits has observant) 与
        # opt_invoke_old_bond (player.bonds has lanridge_shared_past) 在某些样本可触发
        "player.traits": ["observant"],
        "player.bonds": ["lanridge_shared_past"],
    }
    r = validate_graph_sampling(_load_gold(), initial_state=initial,
                                sample_count=100, seed=42)
    assert isinstance(r, SamplingResult)
    assert r.sample_count == 100
    assert r.reached_end_count == 100, (
        f"expected 100/100 reach end, got {r.reached_end_count}/100; "
        f"failures={r.failure_examples}"
    )
    assert r.deadlock_count == 0
    assert r.reach_rate == 1.0
    assert r.condition_unsatisfiable_examples == [], (
        f"expected 0 unsatisfiable, got: {r.condition_unsatisfiable_examples}"
    )
    # 至少出现 2 个 end 节点（end_silent_ally + end_iron_blade）
    assert len(r.end_distribution) >= 2


def test_gold_scene_n100_empty_initial_still_reaches():
    """空 initial_state 也应 100% reach（unconditional 选项总在）。"""
    r = validate_graph_sampling(_load_gold(), sample_count=100, seed=7)
    assert r.reached_end_count == 100
    assert r.deadlock_count == 0


# ---------------------------------------------------------------------------
# 2. 死锁图：2A DEAD_END + 2B sampling 失败
# ---------------------------------------------------------------------------

def _deadlock_graph() -> dict:
    """非 end 节点 ``stuck`` 只有一个永远不可满足的 conditional 选项。"""
    return {
        "entry_node_id": "n0",
        "nodes": {
            "n0": {
                "node_id": "n0",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_to_stuck",
                        "text": "go",
                        "target_node_id": "stuck",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "stuck": {
                "node_id": "stuck",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_locked",
                        "text": "locked",
                        "target_node_id": "n_end",
                        "condition": {
                            "op": "eq",
                            "path": "flag.unset_flag",
                            "value": True,
                        },
                        "effects": [],
                        "unavailable_behavior": "disable",
                    },
                ],
            },
            "n_end": {"node_id": "n_end", "type": "end", "options": []},
        },
    }


def test_deadlock_graph_2A_reports_dead_end():
    """2A 启发式应抓 stuck（reachable + 全 conditional + 无 unconditional）。"""
    r = validate_graph_topology(_deadlock_graph())
    assert "stuck" in r.deadlock_nodes


def test_deadlock_graph_2B_sampling_fails():
    """2B 抽样应在 stuck 节点全部失败 → reached=0；condition unsatisfiable 命中。"""
    r = validate_graph_sampling(_deadlock_graph(), sample_count=20, seed=1)
    assert r.reached_end_count == 0
    assert r.deadlock_count == 20
    assert ("stuck", "o_locked") in r.condition_unsatisfiable_examples
    assert len(r.failure_examples) >= 1
    # 反例 path 包含 stuck
    assert all("stuck" in fs.path for fs in r.failure_examples)


# ---------------------------------------------------------------------------
# 3. 有界符号执行：人造小定义域
# ---------------------------------------------------------------------------

def _conditional_graph() -> dict:
    """两节点：n1 唯一 option 要求 ``flag.gate == True`` 才能到 end；
    flag.gate=False 时无路径。"""
    return {
        "entry_node_id": "n1",
        "nodes": {
            "n1": {
                "node_id": "n1",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_through",
                        "text": "go",
                        "target_node_id": "n_end",
                        "condition": {
                            "op": "eq",
                            "path": "flag.gate",
                            "value": True,
                        },
                        "effects": [],
                        "unavailable_behavior": "disable",
                    },
                ],
            },
            "n_end": {"node_id": "n_end", "type": "end", "options": []},
        },
    }


def test_bounded_symbolic_enumerates_full_small_domain():
    g = _conditional_graph()
    domains = {"flag.gate": [True, False]}
    r = validate_graph_bounded_symbolic(g, state_var_domains=domains, bound=10)
    assert isinstance(r, SymbolicResult)
    assert r.explored_states == 2
    # flag.gate=True 可达；flag.gate=False 不可达
    assert {"flag.gate": False} in r.states_without_path_to_end
    assert {"flag.gate": True} not in r.states_without_path_to_end


def test_bounded_symbolic_bound_caps_explored():
    """bound 比定义域积小时只跑 bound 个组合。"""
    g = _conditional_graph()
    # 4 个组合，但 bound=2 只跑 2 个
    domains = {"flag.gate": [True, False], "flag.other": [1, 2]}
    r = validate_graph_bounded_symbolic(g, state_var_domains=domains, bound=2)
    assert r.explored_states == 2


def test_bounded_symbolic_gold_scene_zero_counterexamples():
    """gold scene 在 player.traits / player.bonds 小定义域上 0 反例。"""
    g = _load_gold()
    domains = {
        "player.traits": [["observant"], []],
        "player.bonds": [["lanridge_shared_past"], []],
    }
    r = validate_graph_bounded_symbolic(g, state_var_domains=domains, bound=10)
    assert r.states_without_path_to_end == [], (
        f"expected 0 counter-example states on gold scene, got: "
        f"{r.states_without_path_to_end}"
    )


def test_bounded_symbolic_empty_domain_treated_as_single_state():
    g = _load_gold()
    r = validate_graph_bounded_symbolic(g, state_var_domains={}, bound=10)
    assert r.explored_states == 1
    assert r.states_without_path_to_end == []


def test_bounded_symbolic_finds_counterexample_in_artificial_graph():
    g = _conditional_graph()
    # 只暴露 False 的初始状态：必有反例
    domains = {"flag.gate": [False]}
    r = validate_graph_bounded_symbolic(g, state_var_domains=domains, bound=10)
    assert r.explored_states == 1
    assert r.states_without_path_to_end == [{"flag.gate": False}]


# ---------------------------------------------------------------------------
# 4. SamplingResult 边界：缺 entry / 空图
# ---------------------------------------------------------------------------

def test_sampling_missing_entry_returns_zero_samples():
    g = {"entry_node_id": "ghost", "nodes": {}}
    r = validate_graph_sampling(g, sample_count=100)
    assert r.sample_count == 0
    assert r.reached_end_count == 0


def test_sampling_seed_reproducibility():
    """同 seed 同输入应给出同分布。"""
    g = _load_gold()
    r1 = validate_graph_sampling(g, sample_count=50, seed=123)
    r2 = validate_graph_sampling(g, sample_count=50, seed=123)
    assert r1.end_distribution == r2.end_distribution
    assert r1.avg_path_length == r2.avg_path_length
