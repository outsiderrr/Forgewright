"""T-2.4 dialogue 机械预检测试。

每个 9 类 issue 各自正反例 + 单 node / 全图两种用法 + ontology=None 时 C3 跳过 +
《铁誓驿站》gold standard 全节点应通过（不修 gold；任何机械 issue 视为本会话信号
回报作者）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator import (
    ValidationIssue,
    ValidationResult,
    validate_graph_mechanical,
    validate_node_mechanical,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_SCENE = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"


def _codes(result: ValidationResult) -> set[str]:
    return {i.code for i in result.issues}


# ---------------------------------------------------------------------------
# Helpers: 构造干净的 dialogue node / option / ontology
# ---------------------------------------------------------------------------

def _option(**overrides) -> dict:
    base = {
        "option_id": "opt_ok",
        "text": "短选项。",
        "target_node_id": "next",
        "condition": None,
        "effects": [],
        "unavailable_behavior": "hide",
    }
    base.update(overrides)
    return base


def _node(**overrides) -> dict:
    base = {
        "node_id": "n",
        "type": "dialogue",
        "narration": "x",
        "speaker_ref": "char_x",
        "location_ref": "scene_x",
        "on_enter_effects": [],
        "options": [_option()],
    }
    base.update(overrides)
    return base


def _ontology(slugs: tuple[str, ...] = ("vellin", "corvan")) -> dict:
    return {
        "entities": [
            {
                "id": f"char_{s}",
                "type": "character",
                "display_name": s.capitalize(),
                "state_path_slug": s,
            }
            for s in slugs
        ]
    }


# ---------------------------------------------------------------------------
# 干净基线
# ---------------------------------------------------------------------------

def test_clean_dialogue_node_passes():
    res = validate_node_mechanical(_node(), known_node_ids={"next"})
    assert res.issues == []
    assert not res.has_error


def test_clean_end_node_passes():
    res = validate_node_mechanical(
        _node(type="end", options=[]), known_node_ids=set()
    )
    assert res.issues == []


# ---------------------------------------------------------------------------
# C1 OPT_LEN_OVER
# ---------------------------------------------------------------------------

def test_c1_chinese_over_25():
    long_text = "啊" * 26
    res = validate_node_mechanical(
        _node(options=[_option(text=long_text)]), known_node_ids={"next"}
    )
    assert "OPT_LEN_OVER" in _codes(res)


def test_c1_chinese_exactly_25_passes():
    res = validate_node_mechanical(
        _node(options=[_option(text="啊" * 25)]), known_node_ids={"next"}
    )
    assert "OPT_LEN_OVER" not in _codes(res)


def test_c1_english_over_25_words():
    text = " ".join(["word"] * 26)
    res = validate_node_mechanical(
        _node(options=[_option(text=text)]), known_node_ids={"next"}
    )
    assert "OPT_LEN_OVER" in _codes(res)


def test_c1_long_english_few_words_passes():
    """30 chars 但只有 3 单词 → 中文计数 0、英文计数 3、max=3 ≤ 25。"""
    text = "supercalifragilisticexpialidocious cat ran"
    res = validate_node_mechanical(
        _node(options=[_option(text=text)]), known_node_ids={"next"}
    )
    assert "OPT_LEN_OVER" not in _codes(res)


# ---------------------------------------------------------------------------
# C2 PATH_NS_INVALID
# ---------------------------------------------------------------------------

def test_c2_invalid_namespace_in_effect():
    eff = {"op": "set", "path": "stats.hp", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]), known_node_ids={"next"}
    )
    assert "PATH_NS_INVALID" in _codes(res)


def test_c2_valid_namespace_passes():
    eff = {"op": "inc", "path": "faction.iron_oath.reputation", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]), known_node_ids={"next"}
    )
    assert "PATH_NS_INVALID" not in _codes(res)


# ---------------------------------------------------------------------------
# C3 BOND_ID_UNKNOWN — v1.0 关键测试
# ---------------------------------------------------------------------------

def test_c3_known_slug_passes():
    eff = {"op": "inc", "path": "relationship.vellin.trust", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]),
        ontology=_ontology(),
        known_node_ids={"next"},
    )
    assert "BOND_ID_UNKNOWN" not in _codes(res)


def test_c3_unknown_slug_fails():
    eff = {"op": "inc", "path": "relationship.unknown_slug.trust", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]),
        ontology=_ontology(),
        known_node_ids={"next"},
    )
    assert "BOND_ID_UNKNOWN" in _codes(res)


def test_c3_skipped_when_ontology_none():
    eff = {"op": "inc", "path": "relationship.unknown_slug.trust", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]),
        ontology=None,
        known_node_ids={"next"},
    )
    assert "BOND_ID_UNKNOWN" not in _codes(res)


def test_c3_in_condition_path():
    cond = {"op": "gte", "path": "relationship.unknown.trust", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]),
        ontology=_ontology(),
        known_node_ids={"next"},
    )
    assert "BOND_ID_UNKNOWN" in _codes(res)


# ---------------------------------------------------------------------------
# C4 TARGET_UNREACHABLE
# ---------------------------------------------------------------------------

def test_c4_dangling_target():
    res = validate_node_mechanical(
        _node(options=[_option(target_node_id="ghost")]),
        known_node_ids={"next", "n"},
    )
    assert "TARGET_UNREACHABLE" in _codes(res)


def test_c4_skipped_when_no_known_nodes():
    """known_node_ids=None → 单 node 入口跳过 C4（避免误报）。"""
    res = validate_node_mechanical(
        _node(options=[_option(target_node_id="ghost")])
    )
    assert "TARGET_UNREACHABLE" not in _codes(res)


# ---------------------------------------------------------------------------
# C5 UNAVAIL_BEHAVIOR_INVALID
# ---------------------------------------------------------------------------

def test_c5_invalid_unavail_behavior():
    res = validate_node_mechanical(
        _node(options=[_option(unavailable_behavior="show")]),
        known_node_ids={"next"},
    )
    assert "UNAVAIL_BEHAVIOR_INVALID" in _codes(res)


@pytest.mark.parametrize("ub", ["hide", "disable", "disable_with_hint"])
def test_c5_valid_unavail_behaviors_pass(ub):
    res = validate_node_mechanical(
        _node(options=[_option(unavailable_behavior=ub)]),
        known_node_ids={"next"},
    )
    assert "UNAVAIL_BEHAVIOR_INVALID" not in _codes(res)


# ---------------------------------------------------------------------------
# C6 STATE_CONDITION_FORM_MIX
# ---------------------------------------------------------------------------

def test_c6_leaf_and_composite_mixed():
    cond = {
        "op": "eq",
        "path": "flag.x",
        "value": True,
        "all_of": [{"op": "eq", "path": "flag.y", "value": True}],
    }
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]), known_node_ids={"next"}
    )
    assert "STATE_CONDITION_FORM_MIX" in _codes(res)


def test_c6_pure_leaf_passes():
    cond = {"op": "eq", "path": "flag.x", "value": True}
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]), known_node_ids={"next"}
    )
    assert "STATE_CONDITION_FORM_MIX" not in _codes(res)


def test_c6_pure_composite_passes():
    cond = {"all_of": [{"op": "eq", "path": "flag.x", "value": True}]}
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]), known_node_ids={"next"}
    )
    assert "STATE_CONDITION_FORM_MIX" not in _codes(res)


# ---------------------------------------------------------------------------
# C7 EFFECT_OP_INVALID
# ---------------------------------------------------------------------------

def test_c7_invalid_effect_op():
    eff = {"op": "multiply", "path": "flag.x", "value": 2}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]), known_node_ids={"next"}
    )
    assert "EFFECT_OP_INVALID" in _codes(res)


@pytest.mark.parametrize("op", ["set", "inc", "dec", "add", "remove"])
def test_c7_valid_effect_ops_pass(op):
    eff = {"op": op, "path": "flag.x", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(effects=[eff])]), known_node_ids={"next"}
    )
    assert "EFFECT_OP_INVALID" not in _codes(res)


# ---------------------------------------------------------------------------
# C8 CONDITION_OP_INVALID
# ---------------------------------------------------------------------------

def test_c8_invalid_condition_op():
    cond = {"op": "between", "path": "flag.x", "value": 1}
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]), known_node_ids={"next"}
    )
    assert "CONDITION_OP_INVALID" in _codes(res)


def test_c8_invalid_op_inside_composite():
    cond = {
        "all_of": [
            {"op": "eq", "path": "flag.x", "value": True},
            {"op": "weird", "path": "flag.y", "value": 1},
        ]
    }
    res = validate_node_mechanical(
        _node(options=[_option(condition=cond)]), known_node_ids={"next"}
    )
    assert "CONDITION_OP_INVALID" in _codes(res)


# ---------------------------------------------------------------------------
# C9 NODE_TYPE_OPTIONS_MISMATCH
# ---------------------------------------------------------------------------

def test_c9_dialogue_with_empty_options():
    res = validate_node_mechanical(
        _node(type="dialogue", options=[]), known_node_ids=set()
    )
    assert "NODE_TYPE_OPTIONS_MISMATCH" in _codes(res)


def test_c9_end_with_options():
    res = validate_node_mechanical(
        _node(type="end", options=[_option()]), known_node_ids={"next"}
    )
    assert "NODE_TYPE_OPTIONS_MISMATCH" in _codes(res)


# ---------------------------------------------------------------------------
# 全图入口
# ---------------------------------------------------------------------------

def test_validate_graph_mechanical_returns_per_node_results():
    graph = {
        "nodes": {
            "n1": _node(node_id="n1", options=[_option(target_node_id="n2")]),
            "n2": _node(node_id="n2", type="end", options=[]),
        }
    }
    results = validate_graph_mechanical(graph)
    assert set(results) == {"n1", "n2"}
    assert all(isinstance(r, ValidationResult) for r in results.values())
    assert all(not r.has_error for r in results.values())


def test_validate_graph_mechanical_detects_dangling_target():
    graph = {
        "nodes": {
            "n1": _node(node_id="n1", options=[_option(target_node_id="ghost")]),
            "n2": _node(node_id="n2", type="end", options=[]),
        }
    }
    results = validate_graph_mechanical(graph)
    assert "TARGET_UNREACHABLE" in _codes(results["n1"])


def test_validate_graph_mechanical_propagates_ontology_to_c3():
    graph = {
        "nodes": {
            "n1": _node(
                node_id="n1",
                options=[
                    _option(
                        target_node_id="n2",
                        effects=[
                            {
                                "op": "inc",
                                "path": "relationship.unknown.trust",
                                "value": 1,
                            }
                        ],
                    )
                ],
            ),
            "n2": _node(node_id="n2", type="end", options=[]),
        }
    }
    results = validate_graph_mechanical(graph, ontology=_ontology())
    assert "BOND_ID_UNKNOWN" in _codes(results["n1"])


# ---------------------------------------------------------------------------
# 不短路：多 issue 聚合
# ---------------------------------------------------------------------------

def test_multiple_issues_aggregated_in_single_node():
    """单 node 含 4 类 issue：C1 + C2 + C5 + C7。"""
    eff = {"op": "multiply", "path": "stats.hp", "value": 1}
    opt = _option(
        text="啊" * 30,
        unavailable_behavior="show",
        effects=[eff],
    )
    res = validate_node_mechanical(
        _node(options=[opt]), known_node_ids={"next"}
    )
    codes = _codes(res)
    assert {
        "OPT_LEN_OVER",
        "PATH_NS_INVALID",
        "UNAVAIL_BEHAVIOR_INVALID",
        "EFFECT_OP_INVALID",
    }.issubset(codes)


# ---------------------------------------------------------------------------
# Severity 矩阵：所有 9 类都是 error 级
# ---------------------------------------------------------------------------

def test_all_nine_codes_are_error_severity():
    """ADR-020 机械失败口径全是硬错（无 warning）。"""
    eff_bad_op_path = {"op": "multiply", "path": "stats.hp", "value": 1}
    eff_bad_slug = {"op": "inc", "path": "relationship.ghost.trust", "value": 1}
    cond_form_mix = {
        "op": "eq",
        "path": "flag.x",
        "value": True,
        "all_of": [{"op": "eq", "path": "flag.y", "value": True}],
    }
    cond_bad_op = {"op": "between", "path": "flag.x", "value": 1}

    nodes = {
        "n_dialogue_empty": {
            "node_id": "n_dialogue_empty",
            "type": "dialogue",
            "options": [],
        },
        "n_end_with_opts": {
            "node_id": "n_end_with_opts",
            "type": "end",
            "options": [_option()],
        },
        "n_packed": _node(
            node_id="n_packed",
            options=[
                _option(
                    text="啊" * 30,
                    target_node_id="ghost",
                    unavailable_behavior="show",
                    effects=[eff_bad_op_path, eff_bad_slug],
                ),
                _option(option_id="opt_b", condition=cond_form_mix),
                _option(option_id="opt_c", condition=cond_bad_op),
            ],
        ),
    }
    graph = {"nodes": nodes}
    results = validate_graph_mechanical(graph, ontology=_ontology())
    all_issues: list[ValidationIssue] = []
    for r in results.values():
        all_issues.extend(r.issues)
    seen = {i.code for i in all_issues}
    expected = {
        "OPT_LEN_OVER",
        "PATH_NS_INVALID",
        "BOND_ID_UNKNOWN",
        "TARGET_UNREACHABLE",
        "UNAVAIL_BEHAVIOR_INVALID",
        "STATE_CONDITION_FORM_MIX",
        "EFFECT_OP_INVALID",
        "CONDITION_OP_INVALID",
        "NODE_TYPE_OPTIONS_MISMATCH",
    }
    assert expected.issubset(seen), (
        f"missing codes: {expected - seen}"
    )
    for i in all_issues:
        assert i.severity == "error", f"{i.code} unexpectedly {i.severity}"


# ---------------------------------------------------------------------------
# Gold standard《铁誓驿站》：全节点应通过
# ---------------------------------------------------------------------------

def test_gold_scene_only_known_c1_issues(capsys):
    """《铁誓驿站》是阶段 1.5 验收实测产物（commit 9be7a3e）；机械层不修 gold（任务指
    示），只报告。这里的契约是：除已知 OPT_LEN_OVER（3 处长选项，作者审阅时拍板要不
    要 C 阶段缩文）外，不许冒出任何**其他** code——任何其他 code 都是机械预检对 gold
    误报，会被视为本任务的回归。
    """
    graph = json.loads(GOLD_SCENE.read_text(encoding="utf-8"))
    ontology = _ontology(slugs=("vellin", "corvan", "aelwin"))
    results = validate_graph_mechanical(graph, ontology=ontology)

    by_node = {nid: r.issues for nid, r in results.items() if r.issues}
    other_codes = {
        i.code
        for issues in by_node.values()
        for i in issues
        if i.code != "OPT_LEN_OVER"
    }
    if by_node:
        # 显式把发现物 dump 到 stderr 给作者（pytest -s 可见；A 阶段报告手动收集）
        report = "\n".join(
            f"{nid} {i.field_path} {i.code}: {i.message}"
            for nid, issues in by_node.items()
            for i in issues
        )
        print(f"\n[T-2.4 gold scene mechanical findings]\n{report}")
    assert not other_codes, (
        f"gold scene produced unexpected non-C1 codes: {other_codes}"
    )
