"""T-2.7 §2A：graph_validation 拓扑 + condition 引用形态测试 (ADR-021)。

覆盖：
  - 4 类拓扑检查正反例（NEVER_REACHED / DEAD_END_NODE / CONDITION_FORM_INVALID / CONVERGENCE）
  - active clocks > 10 触发 warning
  - normalize_effect_op 统一映射
  - 《铁誓驿站》gold scene 上 2A 0 error
  - graph_check 既有出口（``check`` / ``Issue`` / ``validate``）回归
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator import (
    ACTIVE_CLOCKS_SOFT_LIMIT,
    STATE_PATH_NAMESPACES,
    TopologyIssue,
    TopologyResult,
    normalize_effect_op,
    validate_graph_topology,
)
from validator.graph_check import check as graph_check_layer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_SCENE = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"


def _load_gold() -> dict:
    return json.loads(GOLD_SCENE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Gold scene 2A pass — T-2.7 完成标志 (a)
# ---------------------------------------------------------------------------

def test_gold_scene_2A_topology_zero_errors():
    result = validate_graph_topology(_load_gold())
    assert isinstance(result, TopologyResult)
    errors = [i for i in result.issues if i.severity == "error"]
    assert errors == [], f"gold scene must produce 0 2A errors, got: {errors}"
    assert result.unreachable_nodes == []
    assert result.deadlock_nodes == []
    assert result.condition_form_issues == []


def test_gold_scene_2A_has_convergence_warning_at_end_nodes():
    """《铁誓驿站》end_silent_ally / end_iron_blade 都被 vellin_confession + patrol_arrives
    两条独立路径汇合到 → 入度 = 2 → CONVERGENCE warning。"""
    result = validate_graph_topology(_load_gold())
    convergence = [i for i in result.issues if i.code == "CONVERGENCE"]
    nodes_with_warn = {i.node_id for i in convergence}
    assert "end_silent_ally" in nodes_with_warn
    assert "end_iron_blade" in nodes_with_warn


# ---------------------------------------------------------------------------
# 2. NEVER_REACHED 反例
# ---------------------------------------------------------------------------

def _minimal_graph(extra_nodes: dict | None = None, entry: str = "n1") -> dict:
    nodes = {
        "n1": {
            "node_id": "n1",
            "type": "dialogue",
            "options": [
                {
                    "option_id": "o1",
                    "text": "to end",
                    "target_node_id": "n_end",
                    "condition": None,
                    "effects": [],
                    "unavailable_behavior": "hide",
                },
            ],
        },
        "n_end": {"node_id": "n_end", "type": "end", "options": []},
    }
    if extra_nodes:
        nodes.update(extra_nodes)
    return {"entry_node_id": entry, "nodes": nodes}


def test_never_reached_node_reports_error():
    g = _minimal_graph(extra_nodes={
        "orphan": {"node_id": "orphan", "type": "dialogue", "options": []},
    })
    r = validate_graph_topology(g)
    assert "orphan" in r.unreachable_nodes
    assert any(
        i.severity == "error" and i.code == "NEVER_REACHED" and i.node_id == "orphan"
        for i in r.issues
    )


# ---------------------------------------------------------------------------
# 3. DEAD_END_NODE 反例
# ---------------------------------------------------------------------------

def test_dead_end_no_options():
    g = {
        "entry_node_id": "n1",
        "nodes": {
            "n1": {"node_id": "n1", "type": "dialogue", "options": []},
        },
    }
    r = validate_graph_topology(g)
    assert "n1" in r.deadlock_nodes
    assert any(
        i.code == "DEAD_END_NODE" and i.node_id == "n1" for i in r.issues
    )


def test_dead_end_all_conditional_options():
    """非 end 节点可达 + 所有 option 都带 condition → 启发式 deadlock (2A)。"""
    g = _minimal_graph()
    g["nodes"]["n1"]["options"][0]["condition"] = {
        "op": "eq",
        "path": "flag.x",
        "value": True,
    }
    r = validate_graph_topology(g)
    assert "n1" in r.deadlock_nodes


def test_no_dead_end_when_unconditional_fallback_present():
    g = _minimal_graph()
    g["nodes"]["n1"]["options"].append({
        "option_id": "o2",
        "text": "conditional",
        "target_node_id": "n_end",
        "condition": {"op": "eq", "path": "flag.y", "value": True},
        "effects": [],
        "unavailable_behavior": "disable",
    })
    r = validate_graph_topology(g)
    assert r.deadlock_nodes == []


# ---------------------------------------------------------------------------
# 4. CONDITION_FORM_INVALID 反例
# ---------------------------------------------------------------------------

def test_condition_path_outside_namespace_reported():
    g = _minimal_graph()
    g["nodes"]["n1"]["options"][0]["condition"] = {
        "op": "eq",
        "path": "rogue_namespace.x",
        "value": 1,
    }
    r = validate_graph_topology(g)
    assert ("n1", "o1") in r.condition_form_issues
    assert any(
        i.code == "CONDITION_FORM_INVALID"
        and i.node_id == "n1"
        and "rogue_namespace" in i.message
        for i in r.issues
    )


def test_condition_op_invalid_reported():
    g = _minimal_graph()
    g["nodes"]["n1"]["options"][0]["condition"] = {
        "op": "weird_op",
        "path": "flag.x",
        "value": 1,
    }
    r = validate_graph_topology(g)
    assert ("n1", "o1") in r.condition_form_issues


def test_condition_leaf_composite_mix_reported():
    g = _minimal_graph()
    g["nodes"]["n1"]["options"][0]["condition"] = {
        "op": "eq",
        "path": "flag.x",
        "value": 1,
        "all_of": [{"op": "eq", "path": "flag.y", "value": 1}],
    }
    r = validate_graph_topology(g)
    assert ("n1", "o1") in r.condition_form_issues


def test_effect_path_outside_namespace_reported():
    g = _minimal_graph()
    g["nodes"]["n1"]["options"][0]["effects"] = [
        {"op": "set", "path": "junk.foo", "value": 1},
    ]
    r = validate_graph_topology(g)
    assert any(
        i.code == "CONDITION_FORM_INVALID" and "junk.foo" in i.message
        for i in r.issues
    )


def test_on_enter_effects_form_check():
    g = _minimal_graph()
    g["nodes"]["n1"]["on_enter_effects"] = [
        {"op": "set", "path": "outside.foo", "value": 1},
    ]
    r = validate_graph_topology(g)
    assert any(
        i.code == "CONDITION_FORM_INVALID"
        and i.option_id is None
        and "on_enter" in i.message
        for i in r.issues
    )


def test_namespace_constants_exposed():
    assert "world" in STATE_PATH_NAMESPACES
    assert "faction" in STATE_PATH_NAMESPACES
    assert "relationship" in STATE_PATH_NAMESPACES
    assert "flag" in STATE_PATH_NAMESPACES
    assert "player" in STATE_PATH_NAMESPACES


# ---------------------------------------------------------------------------
# 5. CONVERGENCE warning
# ---------------------------------------------------------------------------

def test_convergence_groups_recorded():
    """两路径汇合点的 in_degree > 1 → CONVERGENCE warning。"""
    g = {
        "entry_node_id": "n0",
        "nodes": {
            "n0": {
                "node_id": "n0",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_a",
                        "text": "a",
                        "target_node_id": "merge",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                    {
                        "option_id": "o_b",
                        "text": "b",
                        "target_node_id": "alt",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "alt": {
                "node_id": "alt",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_c",
                        "text": "c",
                        "target_node_id": "merge",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "merge": {
                "node_id": "merge",
                "type": "dialogue",
                "options": [
                    {
                        "option_id": "o_e",
                        "text": "to end",
                        "target_node_id": "n_end",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "n_end": {"node_id": "n_end", "type": "end", "options": []},
        },
    }
    r = validate_graph_topology(g)
    convergence = [i for i in r.issues if i.code == "CONVERGENCE"]
    assert any(i.node_id == "merge" for i in convergence)
    assert any(g_grp[0] == "merge" for g_grp in r.convergence_groups)


# ---------------------------------------------------------------------------
# 6. ACTIVE_CLOCKS_OVER_SOFT_LIMIT (ADR-017 D9)
# ---------------------------------------------------------------------------

def test_active_clocks_over_soft_limit_warns():
    g = _minimal_graph()
    ontology = {
        "clocks": [
            {"id": f"clock_{i}", "ticks_filled": 1, "ticks_total": 10}
            for i in range(ACTIVE_CLOCKS_SOFT_LIMIT + 1)
        ],
    }
    r = validate_graph_topology(g, ontology=ontology)
    assert any(
        i.code == "ACTIVE_CLOCKS_OVER_SOFT_LIMIT" and i.severity == "warning"
        for i in r.issues
    )


def test_active_clocks_under_limit_no_warning():
    g = _minimal_graph()
    ontology = {
        "clocks": [
            {"id": f"clock_{i}", "ticks_filled": 1, "ticks_total": 10}
            for i in range(3)
        ],
    }
    r = validate_graph_topology(g, ontology=ontology)
    assert not any(
        i.code == "ACTIVE_CLOCKS_OVER_SOFT_LIMIT" for i in r.issues
    )


def test_inactive_clocks_not_counted():
    """ticks_filled = 0 视作未启动，不计入活跃。"""
    g = _minimal_graph()
    ontology = {
        "clocks": [
            {"id": f"clock_{i}", "ticks_filled": 0, "ticks_total": 10}
            for i in range(ACTIVE_CLOCKS_SOFT_LIMIT + 5)
        ],
    }
    r = validate_graph_topology(g, ontology=ontology)
    assert not any(
        i.code == "ACTIVE_CLOCKS_OVER_SOFT_LIMIT" for i in r.issues
    )


# ---------------------------------------------------------------------------
# 7. normalize_effect_op 统一映射 (ADR-017 critique §9)
# ---------------------------------------------------------------------------

def test_normalize_state_effect_form():
    eff = {"op": "set", "path": "flag.x", "value": 1}
    out = normalize_effect_op(eff)
    assert out == {"op": "set", "path": "flag.x", "value": 1}


def test_normalize_tick_effect_form_drops_at_tick():
    eff = {"effect_op": "inc", "path": "faction.iron_oath.reputation",
           "value": 1, "at_tick": 3}
    out = normalize_effect_op(eff)
    assert out == {"op": "inc", "path": "faction.iron_oath.reputation", "value": 1}


def test_normalize_consistent_dual_keys():
    eff = {"op": "add", "effect_op": "add", "path": "player.bonds", "value": "x"}
    assert normalize_effect_op(eff) == {
        "op": "add", "path": "player.bonds", "value": "x"
    }


def test_normalize_inconsistent_dual_keys_raises():
    with pytest.raises(ValueError):
        normalize_effect_op(
            {"op": "set", "effect_op": "inc", "path": "flag.x", "value": 1}
        )


def test_normalize_missing_op_raises():
    with pytest.raises(ValueError):
        normalize_effect_op({"path": "flag.x", "value": 1})


def test_normalize_non_dict_raises():
    with pytest.raises(TypeError):
        normalize_effect_op("not a dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. graph_check 既有导出回归 (v1.0 §2.7 关键回归)
# ---------------------------------------------------------------------------

def test_graph_check_check_still_exports_and_returns_tuple():
    """graph_check.check 既有出口（list[Issue], list[Issue]）回归。"""
    errors, warnings = graph_check_layer(_load_gold())
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert errors == [], f"gold scene must pass legacy graph_check, got: {errors}"


def test_topology_issue_is_frozen_dataclass():
    """TopologyIssue 是 frozen dataclass，便于 set / dedup。"""
    a = TopologyIssue(severity="error", code="NEVER_REACHED",
                      node_id="x", option_id=None, message="m")
    b = TopologyIssue(severity="error", code="NEVER_REACHED",
                      node_id="x", option_id=None, message="m")
    assert a == b
    assert hash(a) == hash(b)
