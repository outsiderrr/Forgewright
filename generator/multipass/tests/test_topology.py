"""TopologyPlan 确定性校验 + 回退脚手架单测（0 LLM、0 预算）。"""
from __future__ import annotations

import copy

from generator.multipass.topology import fallback_topology, validate_topology

_SPEC = {
    "background": "BG",
    "design_goal": "GOAL",
    "character_state": "STATE",
    "required_clues": ["R1", "R2"],
    "optional_clues": ["O1"],
    "forbidden_events": ["F1"],
}


def _valid_plan() -> dict:
    return {
        "entry_node_id": "opening",
        "nodes": [
            {
                "node_id": "opening",
                "kind": "choice",
                "function": "开场",
                "reveals": [],
                "routes": [
                    {"to": "soft_line", "stance": "软问"},
                    {"to": "press_line", "stance": "施压"},
                ],
            },
            {"node_id": "soft_line", "kind": "beats", "function": "软分支", "reveals": ["R1", "R2", "O1"], "next": "end_good"},
            {"node_id": "press_line", "kind": "beats", "function": "硬分支", "reveals": ["R1 的残缺记号"], "next": "end_bad"},
            {"node_id": "end_good", "kind": "end", "function": "完整收束", "reveals": []},
            {"node_id": "end_bad", "kind": "end", "function": "残缺收束", "reveals": []},
        ],
    }


def test_valid_plan_passes() -> None:
    assert validate_topology(_valid_plan()) == []


def test_fallback_topology_passes_validation() -> None:
    """回退脚手架自身必须永远合法（安全网不能是坏的）。"""
    assert validate_topology(fallback_topology(_SPEC)) == []


def test_fallback_clue_layering() -> None:
    """软分支 = required + optional 全量；硬分支 = 仅 required。"""
    plan = fallback_topology(_SPEC)
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    assert by_id["branch_soft"]["reveals"] == ["R1", "R2", "O1"]
    assert by_id["branch_hard"]["reveals"] == ["R1", "R2"]


def test_missing_end_rejected() -> None:
    plan = _valid_plan()
    for n in plan["nodes"]:
        if n["kind"] == "end":
            n["kind"] = "beats"
            n["next"] = "opening"  # 顺手做成回环
    errs = validate_topology(plan)
    assert any("end" in e for e in errs)


def test_cross_edge_rejected() -> None:
    """两个父亲指向同一节点（入度 2）= 违反纯树。"""
    plan = _valid_plan()
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    by_id["press_line"]["next"] = "end_good"  # end_good 现在有两个父亲
    errs = validate_topology(plan)
    assert any("入度" in e for e in errs)


def test_unreachable_node_rejected() -> None:
    plan = _valid_plan()
    plan["nodes"].append({"node_id": "orphan", "kind": "end", "function": "孤儿", "reveals": []})
    errs = validate_topology(plan)
    assert any("orphan" in e for e in errs)


def test_dangling_target_rejected() -> None:
    plan = _valid_plan()
    plan["nodes"][0]["routes"][0]["to"] = "nowhere"
    errs = validate_topology(plan)
    assert any("nowhere" in e for e in errs)


def test_no_real_fork_rejected() -> None:
    """所有 choice 都只有 1 条出边 = 没有真分歧。"""
    plan = _valid_plan()
    plan["nodes"][0]["routes"] = [{"to": "soft_line", "stance": "唯一路"}]
    # press_line / end_bad 因此孤立——只看真分歧错误存在即可
    errs = validate_topology(plan)
    assert any("真分歧" in e for e in errs)


def test_self_loop_rejected() -> None:
    plan = _valid_plan()
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    by_id["soft_line"]["next"] = "soft_line"
    errs = validate_topology(plan)
    assert any("自环" in e for e in errs)


def test_bad_node_id_rejected() -> None:
    plan = _valid_plan()
    plan["nodes"][1]["node_id"] = "Soft-Line"
    errs = validate_topology(plan)
    assert any("不合法" in e for e in errs)


def test_node_count_caps() -> None:
    plan = _valid_plan()
    # 塞到 13 个节点：在软分支和 end_good 之间串 8 个 beats（接线保持合法树）
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    prev_node = by_id["soft_line"]
    for i in range(8):
        nid = f"pad_{i}"
        prev_node["next"] = nid
        new_node = {"node_id": nid, "kind": "beats", "function": f"垫{i}", "reveals": [], "next": "end_good"}
        plan["nodes"].append(new_node)
        prev_node = new_node
    errs = validate_topology(plan)
    assert any("超界" in e for e in errs)


def test_deep_copy_safety() -> None:
    """validate 不应修改输入 plan。"""
    plan = _valid_plan()
    snapshot = copy.deepcopy(plan)
    validate_topology(plan)
    assert plan == snapshot
