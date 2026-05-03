"""T-2.2 loader 兼容测试（critique 4.5）。

目标（不改 loader 代码，只验证）：
- 现有 loader（state/ontology/__init__.py，按 entity["id"] 索引）在阶段 2
  扩展后的 waystation.json 下仍然能加载所有 entity（不破阶段 0/1 既有
  loader 测试）。
- state_path_slug 字段被 loader 正确透传（loader 不解释字段，但 entity 字典
  应包含该字段，下游消费者按 entity["state_path_slug"] 取值）。
- envelope 迁移：scene_waystation_of_iron_oath 的 type 已迁到 "location"
  + location_type "scene"（与 SCHEMA_v0.3.md §3 / character.schema.json /
  location.schema.json 一致）。
- 顶层新增 system_time / clocks / chapters 字段不影响 loader 行为（loader
  目前仅扫 `entities[]`，其他字段不抛错）。

注：本文件**不**重复 test_ontology.py 已覆盖的 stage-0 ref 解析行为；这里
专测 T-2.2 stage-2 字段扩展。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from state.ontology import _reset_cache_for_tests, get_entity

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_PATH = REPO_ROOT / "state" / "ontology" / "waystation.json"


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    """Loader 用模块级 _CACHE；每个测试前清，避免序列污染。"""
    _reset_cache_for_tests()
    yield
    _reset_cache_for_tests()


@pytest.mark.parametrize("char_id", ["char_vellin", "char_corvan", "char_aelwin"])
def test_loader_resolves_character_with_stage2_fields(char_id: str) -> None:
    """三个 character entity loader 解析后必须含 T-2.2 stage-2 新字段。"""
    entity = get_entity(char_id)
    assert entity is not None
    assert entity["type"] == "character"
    assert entity["state_path_slug"] == char_id[len("char_"):]
    assert isinstance(entity["character_features"], list)
    assert len(entity["character_features"]) >= 1
    assert isinstance(entity["relations"], list)
    assert isinstance(entity["description"], str) and entity["description"]


def test_loader_resolves_scene_with_envelope_migrated() -> None:
    """envelope 迁移（T-2.2）：scene_waystation_of_iron_oath 的 type 字段已迁
    "scene" → "location"，且 location_type=="scene" + description 必填。"""
    entity = get_entity("scene_waystation_of_iron_oath")
    assert entity is not None
    assert entity["type"] == "location"
    assert entity["location_type"] == "scene"
    assert isinstance(entity["description"], str) and entity["description"]


def test_loader_does_not_break_on_top_level_clocks_chapters() -> None:
    """ADR-016 / ADR-017：waystation.json 顶层新增 system_time / clocks /
    chapters 字段；loader 只扫 entities[]，不应对这些顶层字段抛任何错。
    """
    # 第一次访问触发懒加载；不抛异常即证明顶层新字段不破。
    entity = get_entity("char_vellin")
    assert entity is not None


def test_loader_state_path_slug_is_unique_within_world() -> None:
    """character_validator（T-2.4）会兜底 state_path_slug 全本体唯一；loader
    层只透传字段，本测试是低成本的早期回归——若作者未来手改 waystation
    把两个 character slug 写重，先在本测试报警。
    """
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    slugs = [
        e["state_path_slug"]
        for e in raw["entities"]
        if e.get("type") == "character"
    ]
    assert len(slugs) == len(set(slugs)), (
        f"重复的 state_path_slug: {slugs}"
    )


def test_loader_top_level_chapters_clocks_initially_empty() -> None:
    """T-2.2 起手：clocks / chapters 顶层数组从空起步（作者后续 L3 任务填充）；
    system_time 双轨字段（world.scene_count / world.long_rest_count）从 0 起步。
    本测试锁定 stage-2 起步状态，作者以后改值时本测试需同步。
    """
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    assert raw["clocks"] == []
    assert raw["chapters"] == []
    assert raw["system_time"]["scene_count"] == 0
    assert raw["system_time"]["long_rest_count"] == 0


def test_loader_relations_pair_consistency_seed() -> None:
    """ADR-018 嵌入式关系（不引入全局表）：T-2.2 起步给三对关系
    （vellin↔corvan / vellin↔aelwin / corvan↔aelwin）。本测试只断言相邻字段
    存在 + narrative_weight 落入合法枚举；具体配对一致性留给 character_validator
    （T-2.4 范围）。
    """
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    for entity in raw["entities"]:
        if entity.get("type") != "character":
            continue
        for rel in entity["relations"]:
            assert rel["target_character_ref"].startswith("char_")
            assert rel["narrative_weight"] in {"core", "minor", "context_only"}
