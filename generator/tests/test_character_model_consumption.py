"""T-2.2：generated Character pydantic model 可被 prompt context 消费。

本文件只验证 generated `generator.models.Character` 能够：
- 加载 waystation.json 中三个 character entity 全过；
- 关键字段（id / state_path_slug / character_features / relations /
  dramatic_triggers）在 model 实例上可访问；
- model_dump 结构 round-trip 与原 JSON dict 等价（modulo optional 字段）；

T-2.5 prompt 模板会以这些字段为 GraphContext 注入；本测试是 T-2.5 的前置
unit smoke test。**不**测 schema 校验本身（那归 /schema/tests/）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.models import Character

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_PATH = REPO_ROOT / "state" / "ontology" / "waystation.json"


def _load_character(char_id: str) -> dict:
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    return next(e for e in raw["entities"] if e.get("id") == char_id)


@pytest.mark.parametrize("char_id", ["char_vellin", "char_corvan", "char_aelwin"])
def test_character_model_validates_waystation_entity(char_id: str) -> None:
    raw = _load_character(char_id)
    char = Character.model_validate(raw)
    assert char.id == char_id
    assert char.type == "character"
    assert char.state_path_slug == char_id[len("char_"):]
    assert len(char.character_features) >= 1
    # relations 在三个 character 上首版至少 1 条（vellin/corvan/aelwin 互连）
    assert len(char.relations) >= 1


def test_character_model_dump_roundtrip_preserves_fields() -> None:
    """model_validate → model_dump round-trip 不丢字段。"""
    raw = _load_character("char_vellin")
    char = Character.model_validate(raw)
    dumped = json.loads(char.model_dump_json(exclude_unset=True))
    # 关键字段一一回填
    assert dumped["id"] == raw["id"]
    assert dumped["state_path_slug"] == raw["state_path_slug"]
    assert dumped["character_features"] == raw["character_features"]
    # relations 数量与 narrative_weight 不丢
    assert len(dumped["relations"]) == len(raw["relations"])
    for src, dst in zip(raw["relations"], dumped["relations"]):
        assert dst["target_character_ref"] == src["target_character_ref"]
        assert dst["narrative_weight"] == src["narrative_weight"]


def test_character_model_dramatic_triggers_optional_fields_present() -> None:
    """ADR-019 dramatic_triggers：vellin entity 起步含 1-2 条 seed；
    pydantic 模型应正确解析 trait/when/how + 可选 priority/cooldown_scenes。
    """
    raw = _load_character("char_vellin")
    char = Character.model_validate(raw)
    assert char.dramatic_triggers is not None
    assert len(char.dramatic_triggers) >= 1
    first = char.dramatic_triggers[0]
    assert first.trait
    assert first.when
    assert first.how


def test_character_model_rejects_bad_id_pattern() -> None:
    """envelope id pattern 卡口（v1.0 §2.5）由 pydantic 复现。"""
    raw = _load_character("char_vellin").copy()
    raw["id"] = "vellin"  # 缺 char_ 前缀
    with pytest.raises(Exception):
        Character.model_validate(raw)


def test_character_model_rejects_unknown_top_level_field() -> None:
    """character.schema.json additionalProperties: false → pydantic
    extra="forbid" 一致：未声明字段被拒。"""
    raw = _load_character("char_vellin").copy()
    raw["unknown_field"] = "x"
    with pytest.raises(Exception):
        Character.model_validate(raw)
