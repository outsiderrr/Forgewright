"""T-3Y-1 子 goal 1: state_path_validator 单元测试.

覆盖：
  - 6 命名空间 classify_namespace 正/负样本（特别 knowledge.* 第 6 个）
  - is_monotonic_path 正/负样本（flag.player_* / knowledge.*）
  - validate_effect_namespace 正/负
  - validate_monotonic 正/负 + human-source 豁免
  - validate_effects 集成（多条 effects + 索引报错）
"""
from __future__ import annotations

import pytest

from validator.state_path_validator import (
    ALL_OPS,
    ALLOWED_OPS_MONOTONIC,
    FORBIDDEN_OPS_MONOTONIC,
    classify_namespace,
    is_monotonic_path,
    validate_effect_namespace,
    validate_effects,
    validate_monotonic,
)


# ---------- classify_namespace ----------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("world.scene_count", "world"),
        ("world.long_rest_count", "world"),
        ("faction.iron_oath.reputation", "faction"),
        ("faction.cthulhu_cult.influence", "faction"),
        ("relationship.vellin.trust", "relationship"),
        ("relationship.lucy.fear", "relationship"),
        ("flag.player_saw_blood_letter", "flag"),
        ("flag.lucy_alerted", "flag"),
        ("player.traits", "player"),
        ("player.bonds", "player"),
        ("player.gold", "player"),
        ("knowledge.npc_is_killer", "knowledge"),
        ("knowledge.r1_wright_double_life.stage_1", "knowledge"),
        ("knowledge.r1_wright_double_life.stage_2", "knowledge"),
    ],
)
def test_classify_namespace_positive(path: str, expected: str) -> None:
    assert classify_namespace(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "Knowledge.bad_capitalization",  # 大写首字母拒收
        "knowledge.",                     # 空段拒收
        "knowledge",                      # 缺点 + 段拒收
        "something.else",                 # 未知命名空间
        "FLAG.foo",                       # 大写命名空间名拒收
        "",                               # 空字符串
        "flag",                           # 缺值
    ],
)
def test_classify_namespace_negative(path: str) -> None:
    assert classify_namespace(path) is None


def test_classify_knowledge_is_sixth_namespace() -> None:
    """ADR-016 v0.4 第 6 命名空间硬规则确认."""
    assert "knowledge" in {
        classify_namespace("knowledge.foo"),
        classify_namespace("knowledge.r1.stage_1"),
    }


# ---------- is_monotonic_path ----------


@pytest.mark.parametrize(
    "path",
    [
        "flag.player_saw_blood_letter",
        "flag.player_got_vick_card",
        "flag.player_lucy_opened_up",
        "knowledge.npc_is_killer",
        "knowledge.r1_wright_double_life.stage_1",
    ],
)
def test_monotonic_positive(path: str) -> None:
    assert is_monotonic_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "flag.lucy_alerted",          # flag.* 但非 player_ 前缀
        "flag.eye_noticed",
        "relationship.vellin.trust",  # relationship.* 允许双向
        "player.traits",              # ADR-034 D11 明示 player.traits 不在 monotonic 清单
        "player.bonds",
        "player.gold",
        "world.scene_count",          # world.* 允许双向
        "faction.iron_oath.reputation",
    ],
)
def test_monotonic_negative(path: str) -> None:
    assert not is_monotonic_path(path)


# ---------- validate_effect_namespace ----------


def test_validate_namespace_pass_flag() -> None:
    assert (
        validate_effect_namespace({"op": "set", "path": "flag.foo", "value": True}) == []
    )


def test_validate_namespace_pass_knowledge() -> None:
    """knowledge.* 第 6 命名空间通过."""
    assert (
        validate_effect_namespace(
            {"op": "set", "path": "knowledge.npc_is_killer", "value": True}
        )
        == []
    )


def test_validate_namespace_pass_path_as_segments() -> None:
    """path 形态：字符串段数组（state_effect.schema.json oneOf 第二支）."""
    assert (
        validate_effect_namespace(
            {"op": "inc", "path": ["relationship", "vellin", "trust"], "value": 1}
        )
        == []
    )


def test_validate_namespace_fail_invalid_namespace() -> None:
    errors = validate_effect_namespace(
        {"op": "set", "path": "random.unknown", "value": True}
    )
    assert len(errors) == 1
    assert "未落入 6 个允许的命名空间" in errors[0]


def test_validate_namespace_fail_bad_path_type() -> None:
    errors = validate_effect_namespace({"op": "set", "path": 42, "value": True})
    assert len(errors) == 1
    assert "必须为字符串或字符串段数组" in errors[0]


# ---------- validate_monotonic ----------


def test_monotonic_set_allowed() -> None:
    assert (
        validate_monotonic({"op": "set", "path": "knowledge.foo", "value": True}) == []
    )


def test_monotonic_inc_allowed() -> None:
    assert (
        validate_monotonic({"op": "inc", "path": "flag.player_foo", "value": 1}) == []
    )


def test_monotonic_add_allowed() -> None:
    assert (
        validate_monotonic(
            {"op": "add", "path": "knowledge.evidence_list", "value": "lucy_card"}
        )
        == []
    )


def test_monotonic_dec_rejected_on_knowledge() -> None:
    errors = validate_monotonic({"op": "dec", "path": "knowledge.foo", "value": 1})
    assert len(errors) == 1
    assert "monotonic 违反" in errors[0]
    assert "dec" in errors[0]


def test_monotonic_remove_rejected_on_flag_player() -> None:
    errors = validate_monotonic(
        {"op": "remove", "path": "flag.player_saw_blood_letter", "value": None}
    )
    assert len(errors) == 1
    assert "monotonic 违反" in errors[0]
    assert "remove" in errors[0]


def test_monotonic_human_source_exempt_dec() -> None:
    """human-source 内容豁免 — ADR-034 D11 明示作者手填不受约束."""
    assert (
        validate_monotonic(
            {"op": "dec", "path": "knowledge.foo", "value": 1},
            generation_source="human",
        )
        == []
    )


def test_monotonic_human_source_exempt_remove() -> None:
    assert (
        validate_monotonic(
            {"op": "remove", "path": "flag.player_got_vick_card", "value": None},
            generation_source="human",
        )
        == []
    )


def test_monotonic_player_traits_allow_dec_for_llm() -> None:
    """ADR-034 D11 明示 player.traits 不在 monotonic 清单（喝酒 → 观察能力下降允许）。"""
    assert (
        validate_monotonic(
            {"op": "dec", "path": "player.traits", "value": "observant"},
            generation_source="llm",
        )
        == []
    )


def test_monotonic_relationship_allow_dec_for_llm() -> None:
    """relationship.* 允许双向变化（信任崩塌 / 关系破裂）."""
    assert (
        validate_monotonic(
            {"op": "dec", "path": "relationship.lucy.trust", "value": 999},
            generation_source="llm",
        )
        == []
    )


# ---------- validate_effects 集成 ----------


def test_validate_effects_all_pass() -> None:
    effects = [
        {"op": "set", "path": "flag.foo", "value": True},
        {"op": "inc", "path": "relationship.vellin.trust", "value": 1},
        {"op": "set", "path": "knowledge.npc_is_killer", "value": True},
    ]
    assert validate_effects(effects, generation_source="llm") == []


def test_validate_effects_mixed_errors() -> None:
    """混合错误：第 2 条 monotonic 违反、第 3 条命名空间违反."""
    effects = [
        {"op": "set", "path": "flag.foo", "value": True},                       # OK
        {"op": "dec", "path": "knowledge.baz", "value": 1},                      # monotonic 违反
        {"op": "set", "path": "random.unknown", "value": True},                  # 命名空间违反
    ]
    errors = validate_effects(effects, generation_source="llm")
    assert any("effect[1]:" in e and "monotonic" in e for e in errors)
    assert any("effect[2]:" in e and "未落入" in e for e in errors)


def test_validate_effects_human_source_passes_all_monotonic() -> None:
    """human-source 全部豁免 monotonic（即使 dec knowledge.*）."""
    effects = [
        {"op": "dec", "path": "knowledge.foo", "value": 1},
        {"op": "remove", "path": "flag.player_bar", "value": None},
    ]
    assert validate_effects(effects, generation_source="human") == []


# ---------- 常量自检 ----------


def test_constants_consistency() -> None:
    """ALL_OPS = ALLOWED_OPS_MONOTONIC ∪ FORBIDDEN_OPS_MONOTONIC + 其他（无）"""
    assert ALLOWED_OPS_MONOTONIC | FORBIDDEN_OPS_MONOTONIC == ALL_OPS
    assert ALLOWED_OPS_MONOTONIC.isdisjoint(FORBIDDEN_OPS_MONOTONIC)
