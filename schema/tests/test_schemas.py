"""T-0.5：对 /schema/ 下五个 JSON Schema（Draft 2020-12）的正/负样本测试。

覆盖要求（按 T-0.5 任务说明）：
- 每个 schema ≥1 正样本、≥1 负样本（附拒收原因）
- 额外负样本：D1（end+非空 options）、D2（枚举外 unavailable_behavior）、D4（叶+复合混用）、
  D7（graph_id 含空格）、D8（generation_trace 缺 source）
- 额外正样本：D8 整体省略、D4 嵌套 2 层复合、D5 path 字符串/段数组两种

跨文件 $ref 经 referencing.Registry 解析（jsonschema >=4.18 的 registry API）。
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILES = [
    "dialogue_graph.schema.json",
    "node.schema.json",
    "option.schema.json",
    "state_effect.schema.json",
    "state_condition.schema.json",
]


def _load_registry() -> Registry:
    registry = Registry()
    for name in SCHEMA_FILES:
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(uri=schema["$id"], resource=resource)
    return registry


_REGISTRY = _load_registry()


def _validator(schema_filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_REGISTRY)


# ---------------------------------------------------------------------------
# 样本工厂
# ---------------------------------------------------------------------------

def make_valid_effect() -> dict:
    return {"op": "set", "path": "flag.seen", "value": True}


def make_valid_leaf_condition() -> dict:
    return {"op": "eq", "path": "flag.seen", "value": True}


def make_valid_option(
    *,
    option_id: str = "opt_go",
    target: str = "node_end",
    condition=None,
    effects=None,
    behavior: str = "hide",
) -> dict:
    return {
        "option_id": option_id,
        "text": "go",
        "target_node_id": target,
        "condition": condition,
        "effects": list(effects) if effects is not None else [],
        "unavailable_behavior": behavior,
    }


def make_valid_dialogue_node(
    *,
    node_id: str = "node_start",
    options: list | None = None,
    speaker: str | None = "char_a",
) -> dict:
    return {
        "node_id": node_id,
        "type": "dialogue",
        "narration": "narration text",
        "speaker_ref": speaker,
        "location_ref": "loc_a",
        "options": options if options is not None else [make_valid_option()],
    }


def make_valid_end_node(node_id: str = "node_end") -> dict:
    return {
        "node_id": node_id,
        "type": "end",
        "narration": "the end",
        "speaker_ref": None,
        "location_ref": "loc_a",
        "options": [],
    }


def make_valid_graph() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "test_graph",
        "entry_node_id": "node_start",
        "scene_anchor": "scene_anchor_1",
        "character_refs": ["char_a"],
        "nodes": {
            "node_start": make_valid_dialogue_node(),
            "node_end": make_valid_end_node(),
        },
    }


# ---------------------------------------------------------------------------
# 每 schema 基础正/负样本
# ---------------------------------------------------------------------------

def test_state_effect_positive_minimal():
    v = _validator("state_effect.schema.json")
    assert v.is_valid(make_valid_effect())


def test_state_effect_negative_op_not_in_enum():
    """D6 候选枚举外的 op 拒收。"""
    v = _validator("state_effect.schema.json")
    bad = {"op": "obliterate", "path": "flag.seen", "value": True}
    assert not v.is_valid(bad)


def test_state_condition_positive_leaf():
    v = _validator("state_condition.schema.json")
    assert v.is_valid(make_valid_leaf_condition())


def test_state_condition_negative_unknown_op_in_leaf():
    """D6 候选枚举外的 op 拒收。"""
    v = _validator("state_condition.schema.json")
    bad = {"op": "approximately_equals", "path": "x", "value": 1}
    assert not v.is_valid(bad)


def test_option_positive_with_condition():
    v = _validator("option.schema.json")
    opt = make_valid_option(condition=make_valid_leaf_condition())
    assert v.is_valid(opt)


def test_option_negative_missing_option_id():
    """option_id 是 🟢 必需字段，缺失拒收。"""
    v = _validator("option.schema.json")
    opt = make_valid_option()
    del opt["option_id"]
    assert not v.is_valid(opt)


def test_node_positive_dialogue():
    v = _validator("node.schema.json")
    assert v.is_valid(make_valid_dialogue_node())


def test_node_negative_missing_narration():
    """narration 是 🟢 必需字段，缺失拒收（对应 E3a 变体）。"""
    v = _validator("node.schema.json")
    node = make_valid_dialogue_node()
    del node["narration"]
    assert not v.is_valid(node)


def test_dialogue_graph_positive_minimal():
    v = _validator("dialogue_graph.schema.json")
    assert v.is_valid(make_valid_graph())


def test_dialogue_graph_negative_missing_required_field():
    """schema_version 缺失拒收。"""
    v = _validator("dialogue_graph.schema.json")
    g = make_valid_graph()
    del g["schema_version"]
    assert not v.is_valid(g)


# ---------------------------------------------------------------------------
# 任务说明「额外必须覆盖的负样本」
# ---------------------------------------------------------------------------

def test_d1_end_node_with_non_empty_options_rejected():
    """D1 互斥：type=end 的节点 options 必须为空数组。"""
    v = _validator("node.schema.json")
    node = make_valid_end_node()
    node["options"] = [make_valid_option()]
    assert not v.is_valid(node)


def test_d2_unavailable_behavior_out_of_enum_rejected():
    """D2：unavailable_behavior 仅允许 hide/disable/disable_with_hint。"""
    v = _validator("option.schema.json")
    opt = make_valid_option(behavior="grey_out_with_sparkles")
    assert not v.is_valid(opt)


def test_d4_mixed_leaf_and_compound_rejected():
    """D4：同时含 op 和 all_of 属形态混用，必须拒收。"""
    v = _validator("state_condition.schema.json")
    bad = {
        "op": "eq",
        "path": "x",
        "value": 1,
        "all_of": [make_valid_leaf_condition()],
    }
    assert not v.is_valid(bad)


def test_d7_graph_id_with_space_rejected():
    """D7：graph_id 正则不允许空格。"""
    v = _validator("dialogue_graph.schema.json")
    g = make_valid_graph()
    g["graph_id"] = "has space"
    assert not v.is_valid(g)


def test_d8_generation_trace_missing_source_rejected():
    """D8：generation_trace 整体可省；但若存在则 source 必填。"""
    v = _validator("option.schema.json")
    opt = make_valid_option()
    opt["generation_trace"] = {
        "generated_at": None,
        "model_id": None,
        "prompt_hash": None,
        "reviewed_by": None,
        "reviewed_at": None,
    }
    assert not v.is_valid(opt)


# ---------------------------------------------------------------------------
# 任务说明「额外必须覆盖的正样本」
# ---------------------------------------------------------------------------

def test_d8_generation_trace_absent_is_valid():
    """D8：generation_trace 整体省略合法。"""
    v_opt = _validator("option.schema.json")
    opt = make_valid_option()
    assert "generation_trace" not in opt
    assert v_opt.is_valid(opt)

    v_node = _validator("node.schema.json")
    node = make_valid_dialogue_node()
    assert "generation_trace" not in node
    assert v_node.is_valid(node)


def test_d4_nested_two_level_compound_is_valid():
    """D4：all_of[any_of[...]] 两层复合合法（借 $ref '#' 自引用）。"""
    v = _validator("state_condition.schema.json")
    nested = {
        "all_of": [
            {"op": "gte", "path": "relationship.vellin.trust", "value": 1},
            {
                "any_of": [
                    {"op": "has", "path": "player.traits", "value": "observant"},
                    {"not": {"op": "eq", "path": "flag.read_the_room_used", "value": True}},
                ]
            },
        ]
    }
    assert v.is_valid(nested)


def test_d5_path_as_dotted_string_is_valid():
    """D5 占位：path 点分字符串合法。"""
    v = _validator("state_effect.schema.json")
    eff = {"op": "inc", "path": "relationship.vellin.trust", "value": 1}
    assert v.is_valid(eff)


def test_d5_path_as_segment_array_is_valid():
    """D5 占位：path 段数组合法。"""
    v = _validator("state_effect.schema.json")
    eff = {"op": "inc", "path": ["relationship", "vellin", "trust"], "value": 1}
    assert v.is_valid(eff)

    v_cond = _validator("state_condition.schema.json")
    cond = {"op": "eq", "path": ["flag", "read_the_room_used"], "value": True}
    assert v_cond.is_valid(cond)


# ---------------------------------------------------------------------------
# 额外回归：跨文件 $ref 端到端（根图 → 节点 → 选项 → 条件/效果）
# ---------------------------------------------------------------------------

def test_graph_with_compound_condition_and_on_enter_effects_end_to_end():
    """端到端正样本：根 DialogueGraph 经 $ref 解析子 schema 成功。"""
    v = _validator("dialogue_graph.schema.json")
    g = make_valid_graph()
    g["nodes"]["node_start"]["on_enter_effects"] = [make_valid_effect()]
    g["nodes"]["node_start"]["options"][0]["condition"] = {
        "any_of": [
            make_valid_leaf_condition(),
            {"not": make_valid_leaf_condition()},
        ]
    }
    g["nodes"]["node_start"]["options"][0]["effects"] = [make_valid_effect()]
    assert v.is_valid(g)


def test_graph_dialogue_node_with_empty_options_rejected_via_root():
    """D1 通过根 schema 的 $ref 传导：dialogue 节点 options 为空也应拒收。"""
    v = _validator("dialogue_graph.schema.json")
    g = make_valid_graph()
    g["nodes"]["node_start"]["options"] = []
    assert not v.is_valid(g)


