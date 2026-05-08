"""T-3.2 schema 关键卡口测试（ADR-023 + F15 字段约束加严）。

覆盖目标（v1.0 ≥ 8 case）：
- 有效 sidecar（全字段填）→ pass
- 有效 sidecar（仅 required 字段，optional 全省）→ pass
- schema_version 错（"0.4.0"）→ fail
- prompt_template_hash 格式错（缺 "sha256:" 前缀）→ fail
- **state_paths_read 含非五命名空间路径（"invalid.foo"）→ fail**（F15 新增）
- **state_paths_written 含重复元素（uniqueItems 违反）→ fail**（F15 新增）
- **scene_id pattern 错（大写字母 "MyScene"）→ fail**（F15 新增）
- **summaries_injected_count = 6（超 ≤ 5 上限）→ fail**（v1.0 新增 token metrics 字段）

附加卡口（schema 层防御）：
- additionalProperties: false（未声明字段被拒）
- required 字段缺失（如缺 prompt_template_hash）
- optional 字段不允许 null（chapter_id null）
- chapter_id pattern 错（缺 chap_ 前缀）
- truncation_reason enum 越界
- state_paths_read 命名空间正样本（world / flag / player 单段；faction.x / relationship.x.x 嵌套）

**不在本测试覆盖范围**：scene_id 与 sidecar 所在目录 scene.json graph_id 一致性
（dep_propagate / batch_scheduler 兜底）；ontology_ids_read 内 id 在本体可解析
（dep_propagate 兜底）；summary_source_hashes 长度与 summaries_injected_count
一致性（写入器兜底）。schema 层只声明字段类型 / 枚举 / 边界 / pattern。

新建 schema 与既有 schema 解耦：content_dependency_index 首版 const "0.3.0"，与
character / location / clock / chapter schema 同源演进；既有 dialogue_graph
const 保持 "0.1.1" 不动（参 SCHEMA_v0.3.md §1 复合版本号语义）。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SCHEMA_DIR / "content_dependency_index.schema.json"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

VALID_SHA256 = "sha256:" + "a" * 64
VALID_SHA256_2 = "sha256:" + "b" * 64


def make_minimal_sidecar() -> dict:
    """仅 required 字段的最小合法 sidecar。

    所有 optional 字段全省略——验证 missing-only 兼容路径（F15）。
    """
    return {
        "schema_version": "0.3.0",
        "scene_id": "glades_ironoath_waystation",
        "generated_at": "2026-05-08T12:00:00Z",
        "ontology_ids_read": [
            "char_vellin",
            "char_corvan",
            "scene_waystation_of_iron_oath",
        ],
        "state_paths_read": [
            "relationship.vellin.trust",
            "world.scene_count",
        ],
        "state_paths_written": [
            "relationship.vellin.trust",
        ],
        "prompt_template_hash": VALID_SHA256,
    }


def make_full_sidecar() -> dict:
    """全字段填充的 sidecar（含 ADR-024 token metrics + scene_history hook）。"""
    return {
        "schema_version": "0.3.0",
        "scene_id": "ironoath_chapter2_pursuit",
        "generated_at": "2026-05-08T12:00:00Z",
        "ontology_ids_read": [
            "char_vellin",
            "char_corvan",
            "char_aelwin",
            "scene_waystation_of_iron_oath",
            "loc_vellin_office",
            "clk_iron_oath_pursuit",
            "chap_iron_oath_betrayal",
        ],
        "state_paths_read": [
            "world.scene_count",
            "world.long_rest_count",
            "faction.iron_oath.reputation",
            "relationship.vellin.trust",
            "relationship.corvan.trust",
            "flag.player_knows_letter",
            "player.gold",
        ],
        "state_paths_written": [
            "relationship.vellin.trust",
            "flag.iron_oath_full_pursuit",
        ],
        "prompt_template_hash": VALID_SHA256,
        "visual_asset_ids_referenced": [
            "img_vellin_neutral",
            "img_waystation_dusk",
        ],
        "clock_ids_referenced": ["clk_iron_oath_pursuit"],
        "chapter_id": "chap_iron_oath_betrayal",
        "act_id": "act_arrival",
        "scene_history_referenced": [
            "glades_ironoath_waystation",
            "ironoath_chapter2_intro",
        ],
        "prompt_token_estimate": 4200,
        "summaries_injected_count": 2,
        "summary_source_hashes": [VALID_SHA256, VALID_SHA256_2],
        "truncation_reason": "none",
    }


# ---------------------------------------------------------------------------
# 1. 正样本：minimal + full
# ---------------------------------------------------------------------------

def test_minimal_sidecar_only_required_fields_passes() -> None:
    """v1.0 卡口：仅 required 字段 + optional 全省 = pass（missing-only 兼容路径）。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "minimal sidecar failed schema: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_full_sidecar_all_fields_passes() -> None:
    """v1.0 卡口：全字段填充（含 ADR-024 token metrics + scene_history hook）= pass。"""
    v = _validator()
    sidecar = make_full_sidecar()
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "full sidecar failed schema: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


# ---------------------------------------------------------------------------
# 2. schema_version 卡口
# ---------------------------------------------------------------------------

def test_schema_version_wrong_const_rejected() -> None:
    """const "0.3.0" 严约：不允许 0.4.0 / 0.2.0 等其他版本。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["schema_version"] = "0.4.0"
    assert not v.is_valid(bad)


def test_schema_version_required_not_optional() -> None:
    """sidecar 由自动写入，不存在迁移期省略——schema_version 是 required 字段。"""
    v = _validator()
    bad = make_minimal_sidecar()
    del bad["schema_version"]
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 3. prompt_template_hash 格式卡口
# ---------------------------------------------------------------------------

def test_prompt_template_hash_missing_sha256_prefix_rejected() -> None:
    """pattern ^sha256:[a-f0-9]{64}$ 严约：缺 sha256: 前缀拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["prompt_template_hash"] = "a" * 64  # 缺 sha256: 前缀
    assert not v.is_valid(bad)


def test_prompt_template_hash_uppercase_hex_rejected() -> None:
    """pattern 仅 lowercase a-f：大写 hex 拒收（一致性约束）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["prompt_template_hash"] = "sha256:" + "A" * 64
    assert not v.is_valid(bad)


def test_prompt_template_hash_short_hex_rejected() -> None:
    """pattern {64} 严约：长度不足拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["prompt_template_hash"] = "sha256:" + "a" * 32
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 4. F15 新增：state_paths_read 命名空间 pattern
# ---------------------------------------------------------------------------

def test_state_paths_read_invalid_namespace_rejected() -> None:
    """F15 新增：path 不落入 ADR-016 五命名空间（world/faction/relationship/flag/player）拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_read"] = ["invalid.foo"]
    assert not v.is_valid(bad)


def test_state_paths_read_accepts_all_five_namespaces() -> None:
    """F15 正样本：五命名空间全部 + 嵌套深度通过。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["state_paths_read"] = [
        "world.scene_count",
        "faction.iron_oath.reputation",
        "relationship.vellin.trust",
        "flag.player_knows_letter",
        "player.gold",
        "world",  # 单段也合法（仅 namespace 本身）
        "flag",
        "player",
    ]
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "five-namespace happy paths failed: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_state_paths_read_faction_requires_faction_id_segment() -> None:
    """faction.* 命名空间 pattern 要求 faction.<id> 形态；裸 'faction' 拒收
    （与 ADR-016 §state path 命名空间表"faction.<faction_id>.*"形态一致）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_read"] = ["faction"]  # 裸 faction，缺 faction_id
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 5. F15 新增：state_paths_written uniqueItems 卡口
# ---------------------------------------------------------------------------

def test_state_paths_written_duplicates_rejected() -> None:
    """F15 新增：uniqueItems 违反拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_written"] = [
        "relationship.vellin.trust",
        "relationship.vellin.trust",  # 重复
    ]
    assert not v.is_valid(bad)


def test_ontology_ids_read_uniqueItems_enforced() -> None:
    """F15 一致性约束：ontology_ids_read 同样 uniqueItems。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["ontology_ids_read"] = ["char_vellin", "char_vellin"]  # 重复
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 6. F15 新增：scene_id pattern 卡口
# ---------------------------------------------------------------------------

def test_scene_id_uppercase_rejected() -> None:
    """F15 新增：scene_id pattern ^[a-z][a-z0-9_]*$ 严约：大写字母拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["scene_id"] = "MyScene"
    assert not v.is_valid(bad)


def test_scene_id_starts_with_digit_rejected() -> None:
    """scene_id pattern 首字母 [a-z]：数字起首拒收（pattern ^[a-z]）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["scene_id"] = "1scene"
    assert not v.is_valid(bad)


def test_scene_id_with_hyphen_rejected() -> None:
    """scene_id pattern 字符集 [a-z0-9_]：连字符拒收（与 dialogue_graph.graph_id
    pattern 比更紧——避免 sidecar 文件名与目录解析歧义）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["scene_id"] = "my-scene"
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 7. v1.0 新增：summaries_injected_count 上限卡口（ADR-024 token metrics）
# ---------------------------------------------------------------------------

def test_summaries_injected_count_over_5_rejected() -> None:
    """v1.0 新增（ADR-024）：summaries_injected_count 上限 5（prompt 模板上限）。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["summaries_injected_count"] = 6
    assert not v.is_valid(bad)


def test_summaries_injected_count_zero_accepted() -> None:
    """ADR-024 minimum 0：本 scene 未注入任何 prior summary（合法状态）。"""
    v = _validator()
    sidecar = make_full_sidecar()
    sidecar["summaries_injected_count"] = 0
    sidecar["summary_source_hashes"] = []
    sidecar["scene_history_referenced"] = []
    sidecar["truncation_reason"] = "none"
    assert v.is_valid(sidecar)


def test_summaries_injected_count_negative_rejected() -> None:
    """minimum 0：负值拒收。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["summaries_injected_count"] = -1
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 8. additionalProperties / required / optional missing-only 防御卡口
# ---------------------------------------------------------------------------

def test_additional_properties_rejected() -> None:
    """schema 层 additionalProperties: false（未声明字段被拒）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["unknown_field"] = "should be rejected"
    assert not v.is_valid(bad)


def test_required_missing_prompt_template_hash_rejected() -> None:
    """required 字段缺失（prompt_template_hash 是 dep_propagate 的核心 hash 比对锚点）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    del bad["prompt_template_hash"]
    assert not v.is_valid(bad)


def test_chapter_id_null_rejected() -> None:
    """F15 missing-only：optional 字段不允许 null（schema 未声明 null 类型）。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["chapter_id"] = None
    assert not v.is_valid(bad)


def test_chapter_id_missing_chap_prefix_rejected() -> None:
    """chapter_id pattern ^chap_[a-z0-9_]+$ 严约。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["chapter_id"] = "iron_oath_betrayal"  # 缺 chap_ 前缀
    assert not v.is_valid(bad)


def test_truncation_reason_invalid_enum_rejected() -> None:
    """truncation_reason enum 越界拒收。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["truncation_reason"] = "unknown_reason"
    assert not v.is_valid(bad)


def test_truncation_reason_all_four_enums_accepted() -> None:
    """ADR-024 truncation_reason 四档全合法。"""
    v = _validator()
    for reason in ("none", "summaries_over_5", "token_budget", "manual_override"):
        sidecar = make_full_sidecar()
        sidecar["truncation_reason"] = reason
        assert v.is_valid(sidecar), f"truncation_reason={reason!r} should be accepted"


# ---------------------------------------------------------------------------
# 9. scene_history_referenced pattern（与 scene_id 同源）
# ---------------------------------------------------------------------------

def test_scene_history_referenced_pattern_aligned_with_scene_id() -> None:
    """scene_history_referenced items pattern 与 scene_id 同源 ^[a-z][a-z0-9_]*$。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["scene_history_referenced"] = ["MyPriorScene"]  # 大写拒收
    assert not v.is_valid(bad)


def test_scene_history_referenced_uniqueItems() -> None:
    """ADR-024 hook：scene_history_referenced uniqueItems 强约。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["scene_history_referenced"] = ["scene_a", "scene_a"]
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 10. summary_source_hashes pattern 与 prompt_template_hash 同源
# ---------------------------------------------------------------------------

def test_summary_source_hashes_pattern_aligned() -> None:
    """summary_source_hashes items pattern 与 prompt_template_hash 同源
    ^sha256:[a-f0-9]{64}$（溯源用）。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["summary_source_hashes"] = ["not-a-hash"]
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 11. const 0.3.0 与 ontology 模块同源验证（schema 文件层硬约）
# ---------------------------------------------------------------------------

def test_schema_const_version_matches_ontology_module() -> None:
    """SCHEMA_v0.3.md §1：content_dependency_index 与 character/location/clock/
    chapter 同 ontology 模块版本号语义；首版 const '0.3.0'。本测试在文件层
    断言 const 没被偷偷 bump（防 schema 漂移）。"""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "0.3.0"


def test_schema_additionalProperties_is_false() -> None:
    """SCHEMA_v0.3.md §1：sidecar 顶层 additionalProperties: false 是 F15
    严约的核心防御点（schema 漂移 / 字段悄悄加 = 写入器写废 sidecar 但 schema 接受）。"""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False


# ---------------------------------------------------------------------------
# 12. parametrized 验证 state_paths_written 同 state_paths_read 命名空间约束
#     一致（write 侧 F15 加严同 read 侧）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_path", [
    "invalid.foo",
    "FACTION.iron_oath.reputation",  # 大写命名空间名拒收
    "faction",  # 裸 faction，缺 id 段
    "relationship",  # 裸 relationship，缺 slug 段
    ".world",  # 起始 . 拒收
])
def test_state_paths_written_invalid_namespace_rejected(bad_path: str) -> None:
    """F15 加严：write 侧命名空间 pattern 与 read 侧同源严约。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_written"] = [bad_path]
    assert not v.is_valid(bad), f"path {bad_path!r} should be rejected"
