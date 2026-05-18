"""T-3Y-1 子 goal 1: dialogue_graph + node 新增 schema 字段正/负样本测试.

覆盖：
  - ADR-034 D4 scene_metaparams（dict 自由形态）
  - ADR-034 D5 scene_reveals（ordered flag set / required_stages）
  - ADR-034 D6 scene_seeds（coverage_strategy enum）
  - ADR-016 v0.4 player_known_info（knowledge.* 命名空间 pattern）
  - node 新增 background_seeds + foreground_goal
  - gold-scene 兼容（不写新字段时仍通过）
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


def _registry() -> Registry:
    reg = Registry()
    for name in SCHEMA_FILES:
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        reg = reg.with_resource(uri=schema["$id"], resource=Resource.from_contents(schema))
    return reg


_REG = _registry()


def _dialogue_graph_validator() -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / "dialogue_graph.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_REG)


def _valid_dialogue_node(node_id: str = "node_1") -> dict:
    return {
        "node_id": node_id,
        "type": "dialogue",
        "narration": "...",
        "speaker_ref": None,
        "location_ref": "scene_inn",
        "options": [
            {
                "option_id": "opt_a",
                "text": "go",
                "target_node_id": "end_1",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            }
        ],
    }


def _valid_end_node(node_id: str = "end_1") -> dict:
    return {
        "node_id": node_id,
        "type": "end",
        "narration": "fin",
        "speaker_ref": None,
        "location_ref": "scene_inn",
        "options": [],
    }


def _base_graph() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "scene_inn_meet_lucy",
        "entry_node_id": "node_1",
        "scene_anchor": "scene_inn",
        "character_refs": ["char_lucy"],
        "nodes": {
            "node_1": _valid_dialogue_node("node_1"),
            "end_1": _valid_end_node("end_1"),
        },
    }


# ---------- 兼容性：不写新字段仍通过 ----------


def test_dialogue_graph_without_new_fields_still_valid() -> None:
    """gold scene 不写任何新字段 → 仍通过（兼容性硬规则）."""
    g = _base_graph()
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


# ---------- ADR-034 D4: scene_metaparams ----------


def test_scene_metaparams_free_dict_passes() -> None:
    g = _base_graph()
    g["scene_metaparams"] = {
        "culprit_id": "culprit_vick",
        "difficulty_level": "normal",
        "apparition_level": 2,
        "any_project_specific_key": "any_value",
    }
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_scene_metaparams_must_be_object_not_array() -> None:
    g = _base_graph()
    g["scene_metaparams"] = ["wrong", "type"]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


# ---------- ADR-034 D5: scene_reveals ----------


def test_scene_reveals_ordered_flag_set_passes() -> None:
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "r1_wright_double_life",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1, 2],
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_scene_reveals_missing_required_stages_rejected() -> None:
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "r1",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            # required_stages 缺失
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_scene_reveals_empty_trigger_node_ids_rejected() -> None:
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "r1",
            "trigger_node_ids": [],
            "completion_node_id": "node_1",
            "required_stages": [1],
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1  # minItems: 1


def test_scene_reveals_required_stages_zero_rejected() -> None:
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "r1",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [0],  # minimum: 1
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_scene_reveals_reveal_id_uppercase_rejected() -> None:
    """Codex review finding 4.2 收紧：reveal_id 大写应拒收（pattern ^[a-z0-9_]+$）。

    保护 ADR-016 v0.4 knowledge.<reveal_id>.stage_<n> 合法性——
    knowledge.* pattern 只允许小写段。
    """
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "R1_wright_double_life",  # 大写违规
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1],
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_scene_reveals_reveal_id_hyphen_rejected() -> None:
    """Codex review finding 4.2 收紧：reveal_id 连字符应拒收（pattern 只允 [a-z0-9_]）。"""
    g = _base_graph()
    g["scene_reveals"] = [
        {
            "reveal_id": "wright-double-life",  # 连字符违规
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1],
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_node_foreground_goal_uppercase_rejected() -> None:
    """Codex review finding 4.2：foreground_goal 中 reveal_id 段大写应拒收。"""
    g = _base_graph()
    g["nodes"]["node_1"]["foreground_goal"] = "R1.stage_2"  # 大写违规
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_node_foreground_goal_hyphen_rejected() -> None:
    """Codex review finding 4.2：foreground_goal 中 reveal_id 段连字符应拒收。"""
    g = _base_graph()
    g["nodes"]["node_1"]["foreground_goal"] = "wright-double-life.stage_2"
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


# ---------- ADR-034 D6: scene_seeds ----------


def test_scene_seeds_with_coverage_strategy_passes() -> None:
    g = _base_graph()
    g["scene_seeds"] = [
        {
            "seed_id": "S2_vick_dangerous",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_all_paths",
        },
        {
            "seed_id": "S4_country_cottage_cache",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "conditional_reward",
            "condition": {
                "op": "gte",
                "path": "relationship.lucy.trust",
                "value": 2,
            },
        },
        {
            "seed_id": "S1_atlantic_city_thugs",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_with_fallback",
        },
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_scene_seeds_invalid_coverage_strategy_rejected() -> None:
    g = _base_graph()
    g["scene_seeds"] = [
        {
            "seed_id": "S1",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "wrong_enum_value",
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_scene_seeds_missing_planted_in_node_ids_rejected() -> None:
    g = _base_graph()
    g["scene_seeds"] = [
        {
            "seed_id": "S1",
            "coverage_strategy": "mandatory_all_paths",
        }
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


# ---------- ADR-016 v0.4: player_known_info（knowledge.* 命名空间 pattern） ----------


def test_player_known_info_with_knowledge_path_passes() -> None:
    g = _base_graph()
    g["player_known_info"] = [
        {"knowledge_path": "knowledge.wright_dead", "stage": 1},
        {"knowledge_path": "knowledge.lucy_known_to_player"},
        {"knowledge_path": "knowledge.r1_wright_double_life.stage_2"},
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_player_known_info_bad_namespace_rejected() -> None:
    """knowledge_path 必须以 knowledge. 开头（不是 flag. / player. 等）."""
    g = _base_graph()
    g["player_known_info"] = [
        {"knowledge_path": "flag.not_knowledge"},
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_player_known_info_uppercase_rejected() -> None:
    g = _base_graph()
    g["player_known_info"] = [
        {"knowledge_path": "Knowledge.Bad_Capital"},
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_player_known_info_stage_zero_rejected() -> None:
    g = _base_graph()
    g["player_known_info"] = [
        {"knowledge_path": "knowledge.foo", "stage": 0},  # minimum: 1
    ]
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


# ---------- node 新增 background_seeds + foreground_goal ----------


def test_node_with_background_seeds_and_foreground_goal_passes() -> None:
    g = _base_graph()
    g["nodes"]["node_1"]["background_seeds"] = [
        "S2_vick_dangerous",
        "S4_country_cottage_cache",
    ]
    g["nodes"]["node_1"]["foreground_goal"] = "r1_wright_double_life.stage_2"
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_node_foreground_goal_no_stage_suffix_passes() -> None:
    """不分阶段 reveal 可省略 .stage_<n> 后缀."""
    g = _base_graph()
    g["nodes"]["node_1"]["foreground_goal"] = "r1_wright_double_life"
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


def test_node_foreground_goal_bad_stage_suffix_rejected() -> None:
    """stage 后缀必须是 .stage_<positive int>."""
    g = _base_graph()
    g["nodes"]["node_1"]["foreground_goal"] = "R1.stage_zero"
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_node_foreground_goal_stage_with_leading_zero_rejected() -> None:
    g = _base_graph()
    g["nodes"]["node_1"]["foreground_goal"] = "R1.stage_0"
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert len(errors) >= 1


def test_node_background_seeds_empty_array_passes() -> None:
    """空数组允许（节点不承载任何 seed）."""
    g = _base_graph()
    g["nodes"]["node_1"]["background_seeds"] = []
    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]


# ---------- 端到端：完整酒馆露西场景顶层 + node_3 字段联合 ----------


def test_inn_lucy_scene_end_to_end_full_fields() -> None:
    """模拟酒馆见露西场景的完整 T-3Y-1 字段填写——验证 4 个场景顶层 + 2 个节点字段联合通过."""
    g = _base_graph()
    g["scene_metaparams"] = {"culprit_id": "culprit_vick"}
    g["scene_reveals"] = [
        {
            "reveal_id": "r1_wright_double_life",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1, 2],
        }
    ]
    g["scene_seeds"] = [
        {
            "seed_id": "S2_vick_dangerous",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_all_paths",
        }
    ]
    g["player_known_info"] = [
        {"knowledge_path": "knowledge.wright_dead", "stage": 1},
    ]
    g["nodes"]["node_1"]["background_seeds"] = ["S2_vick_dangerous"]
    g["nodes"]["node_1"]["foreground_goal"] = "r1_wright_double_life.stage_2"

    errors = list(_dialogue_graph_validator().iter_errors(g))
    assert errors == [], [e.message for e in errors]
