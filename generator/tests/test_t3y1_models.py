"""T-3Y-1 C 阶段 finding 4.1: Pydantic models 新字段 model_validate 测试.

Codex review finding 4.1 [IMPORTANT]：
- schema/dialogue_graph.schema.json 加了 4 字段
  (scene_metaparams / scene_reveals / scene_seeds / player_known_info)
- schema/node.schema.json 加了 2 字段 (background_seeds / foreground_goal)
- 重新生成 generator/models/_generated/*.py 后，本测试断言含这些新字段的 graph
  能通过 DialogueGraph.model_validate（确认 extra="forbid" 不拒收新字段）.

也补 4.2 收紧的 pattern 验证：reveal_id 大写 / 连字符 → ValidationError.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from generator.models import DialogueGraph


def _base_graph_dict() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "scene_inn_meet_lucy",
        "entry_node_id": "node_1",
        "scene_anchor": "scene_inn",
        "character_refs": ["char_lucy"],
        "nodes": {
            "node_1": {
                "node_id": "node_1",
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
            },
            "end_1": {
                "node_id": "end_1",
                "type": "end",
                "narration": "fin",
                "speaker_ref": None,
                "location_ref": "scene_inn",
                "options": [],
            },
        },
    }


# ---------- 新字段 model_validate 正样本 ----------


def test_model_validate_with_scene_metaparams() -> None:
    g = _base_graph_dict()
    g["scene_metaparams"] = {"culprit_id": "culprit_vick", "difficulty_level": "normal"}
    graph = DialogueGraph.model_validate(g)
    assert graph.scene_metaparams == {
        "culprit_id": "culprit_vick",
        "difficulty_level": "normal",
    }


def test_model_validate_with_scene_reveals() -> None:
    g = _base_graph_dict()
    g["scene_reveals"] = [
        {
            "reveal_id": "r1_wright_double_life",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1, 2],
        }
    ]
    graph = DialogueGraph.model_validate(g)
    assert graph.scene_reveals is not None
    assert len(graph.scene_reveals) == 1
    assert graph.scene_reveals[0].reveal_id == "r1_wright_double_life"
    # required_stages 被 datamodel-codegen 包成 RootModel；用 .root 解 wrapper
    stages = [s.root for s in graph.scene_reveals[0].required_stages]
    assert stages == [1, 2]


def test_model_validate_with_scene_seeds_all_coverage_strategies() -> None:
    g = _base_graph_dict()
    g["scene_seeds"] = [
        {
            "seed_id": "s1",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_all_paths",
        },
        {
            "seed_id": "s2",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_with_fallback",
        },
        {
            "seed_id": "s3",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "conditional_reward",
            "condition": {"op": "gte", "path": "relationship.lucy.trust", "value": 2},
        },
    ]
    graph = DialogueGraph.model_validate(g)
    assert graph.scene_seeds is not None
    assert len(graph.scene_seeds) == 3


def test_model_validate_with_player_known_info_knowledge_path() -> None:
    g = _base_graph_dict()
    g["player_known_info"] = [
        {"knowledge_path": "knowledge.wright_dead", "stage": 1},
        {"knowledge_path": "knowledge.lucy_known_to_player"},
    ]
    graph = DialogueGraph.model_validate(g)
    assert graph.player_known_info is not None
    assert len(graph.player_known_info) == 2
    assert graph.player_known_info[0].knowledge_path == "knowledge.wright_dead"
    assert graph.player_known_info[0].stage == 1
    assert graph.player_known_info[1].stage is None


def test_model_validate_with_node_background_seeds_and_foreground_goal() -> None:
    g = _base_graph_dict()
    g["nodes"]["node_1"]["background_seeds"] = ["s1", "s2"]
    g["nodes"]["node_1"]["foreground_goal"] = "r1_wright_double_life.stage_2"
    graph = DialogueGraph.model_validate(g)
    n1 = graph.nodes["node_1"]
    assert n1.background_seeds == ["s1", "s2"]
    assert n1.foreground_goal == "r1_wright_double_life.stage_2"


def test_model_validate_full_t3y1_combined() -> None:
    """模拟 dry-run 实际用的酒馆见露西场景：4 顶层 + 2 节点字段全部联合."""
    g = _base_graph_dict()
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
            "seed_id": "s2_vick_dangerous",
            "planted_in_node_ids": ["node_1"],
            "coverage_strategy": "mandatory_all_paths",
        }
    ]
    g["player_known_info"] = [
        {"knowledge_path": "knowledge.wright_dead", "stage": 1},
    ]
    g["nodes"]["node_1"]["background_seeds"] = ["s2_vick_dangerous"]
    g["nodes"]["node_1"]["foreground_goal"] = "r1_wright_double_life.stage_2"

    # 应一次通过；不抛 ValidationError
    graph = DialogueGraph.model_validate(g)
    assert graph.scene_metaparams["culprit_id"] == "culprit_vick"
    assert graph.scene_reveals[0].reveal_id == "r1_wright_double_life"
    assert graph.scene_seeds[0].coverage_strategy.value == "mandatory_all_paths"
    assert graph.player_known_info[0].knowledge_path == "knowledge.wright_dead"
    assert graph.nodes["node_1"].background_seeds == ["s2_vick_dangerous"]
    assert graph.nodes["node_1"].foreground_goal == "r1_wright_double_life.stage_2"


# ---------- 兼容性：不写新字段（gold scene 路径） ----------


def test_model_validate_without_new_fields_still_valid() -> None:
    """gold scene 不写新字段路径——确认 schema 兼容性（finding 4.1 + 4.2 不破）."""
    graph = DialogueGraph.model_validate(_base_graph_dict())
    assert graph.scene_metaparams is None
    assert graph.scene_reveals is None
    assert graph.scene_seeds is None
    assert graph.player_known_info is None


# ---------- finding 4.2 pattern 收紧验证（pydantic 层）----------


def test_model_validate_rejects_uppercase_reveal_id() -> None:
    """Codex finding 4.2: 大写 reveal_id 应被 pydantic ValidationError 拒收."""
    g = _base_graph_dict()
    g["scene_reveals"] = [
        {
            "reveal_id": "R1_wright_double_life",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1],
        }
    ]
    with pytest.raises(ValidationError):
        DialogueGraph.model_validate(g)


def test_model_validate_rejects_uppercase_foreground_goal() -> None:
    """Codex finding 4.2: 大写 foreground_goal reveal_id 段应被 pydantic 拒收."""
    g = _base_graph_dict()
    g["nodes"]["node_1"]["foreground_goal"] = "R1.stage_2"
    with pytest.raises(ValidationError):
        DialogueGraph.model_validate(g)


def test_model_validate_rejects_hyphen_reveal_id() -> None:
    """Codex finding 4.2: reveal_id 含连字符应被 pydantic 拒收（pattern 只允 [a-z0-9_]）."""
    g = _base_graph_dict()
    g["scene_reveals"] = [
        {
            "reveal_id": "wright-double-life",
            "trigger_node_ids": ["node_1"],
            "completion_node_id": "node_1",
            "required_stages": [1],
        }
    ]
    with pytest.raises(ValidationError):
        DialogueGraph.model_validate(g)
