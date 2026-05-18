"""T-3.2 schema 关键卡口测试（ADR-023 + F15 字段约束加严；GPT-5.5 review C 阶段修订）。

覆盖目标（v1.0 ≥ 8 case）：
- 有效 sidecar（全字段填）→ pass
- 有效 sidecar（仅 required 字段，optional 全省）→ pass
- schema_version 错（"0.4.0"）→ fail
- prompt_template_hash 格式错（缺 "sha256:" 前缀）→ fail
- **state_paths_read 含非五命名空间路径（"invalid.foo"）→ fail**（F15 新增）
- **state_paths_written 含重复元素（uniqueItems 违反）→ fail**（F15 新增）
- **scene_id pattern 错（大写字母 "MyScene"）→ fail**（F15 新增）
- **summaries_injected_count = 6（超 ≤ 5 上限）→ fail**（v1.0 新增 token metrics 字段）

GPT-5.5 review C 阶段修订（PR #40 B 阶段反馈整合）：
- **review 3.1 🔴**：state path pattern 加严——裸 namespace（world / flag /
  player / relationship.<slug>）全部拒收（详 test_state_paths_read_bare_
  namespace_rejected + test_state_paths_written_invalid_namespace_rejected
  扩展 case）。
- **review 3.2 🔴**：scene_id pattern 与 ADR-023 决策核心明示对齐
  `^[a-z0-9_]+$`——数字起首改为合法（详 test_scene_id_starts_with_digit_
  accepted；scene_history_referenced.items.pattern 同步）。
- **review 4.1 🟡**：act_id pattern 与 chapter.schema.json `^act_[a-z0-9_]
  {1,64}$` 严格同源（详 test_act_id_with_underscore_accepted +
  test_act_id_invalid_patterns_rejected）。
- **review 5.1 🟢**：$schema 改 draft/2020-12 + $id 改 forgewright.local
  与既有 schema 同源（schema 层硬约 + 不影响测试逻辑）。

附加卡口（schema 层防御）：
- additionalProperties: false（未声明字段被拒）
- required 字段缺失（如缺 prompt_template_hash）
- optional 字段不允许 null（chapter_id null）
- chapter_id pattern 错（缺 chap_ 前缀）
- truncation_reason enum 越界
- state_paths_read 命名空间正样本（world.x / faction.x / relationship.x.x
  / flag.x / player.x 全部至少 namespace + 一段）

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
    """F15 正样本：五命名空间全部 + 嵌套深度通过。GPT-5.5 review 3.1 修订：
    五命名空间至少需要一个段（裸 namespace 拒收，详
    test_state_paths_read_bare_namespace_rejected）。relationship.* 至少需 slug
    + field 两段（与 gold scene `relationship.vellin.trust` 形态对齐）。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["state_paths_read"] = [
        "world.scene_count",
        "world.long_rest_count.deep_nested",  # 嵌套深度
        "faction.iron_oath.reputation",
        "faction.iron_oath",  # faction.<id> 一段也合法
        "relationship.vellin.trust",
        "relationship.vellin.trust.sub_field",  # relationship 嵌套
        "flag.player_knows_letter",
        "flag.deep.nested.flag",  # flag 嵌套深度
        "player.gold",
        "player.inventory.weapons",
    ]
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "five-namespace happy paths failed: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_state_paths_read_accepts_knowledge_namespace() -> None:
    """Codex review PR #66 finding 4.3 正样本：第 6 命名空间 knowledge.*（ADR-016 v0.4）
    sidecar state_paths_read 接受 knowledge.* 路径——T-3Y 场景 player_known_info
    + scene_reveals 派生的 state path 不再在 sidecar 校验阶段被拒。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["state_paths_read"] = [
        "knowledge.wright_dead",
        "knowledge.lucy_known_to_player",
        "knowledge.r1_wright_double_life.stage_1",  # 嵌套（reveal_id.stage_n）
        "knowledge.r1_wright_double_life.stage_2",
    ]
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "knowledge.* namespace should be accepted in state_paths_read: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_state_paths_written_accepts_knowledge_namespace() -> None:
    """Codex review PR #66 finding 4.3 正样本：sidecar state_paths_written 也接受
    knowledge.*（T-3Y 场景 effect set knowledge.* 进入 over-approx trace）。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["state_paths_written"] = [
        "knowledge.wright_dead",
        "knowledge.r1_wright_double_life.stage_1",
    ]
    errors = sorted(v.iter_errors(sidecar), key=lambda e: list(e.path))
    assert errors == [], (
        "knowledge.* namespace should be accepted in state_paths_written: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_state_paths_knowledge_uppercase_rejected() -> None:
    """与 ADR-016 v0.4 knowledge.* pattern ^knowledge\\.[a-z0-9_]+ 一致——
    大写不接受（保证 reveal_id 收紧规则跨 schema 一致）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_read"] = ["knowledge.R1_Wright"]
    assert not v.is_valid(bad)


def test_state_paths_knowledge_bare_namespace_rejected() -> None:
    """与其他 5 命名空间一致——裸 'knowledge' 拒收（必须至少一个段）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_read"] = ["knowledge"]
    assert not v.is_valid(bad)


@pytest.mark.parametrize("bare_path", [
    "world",  # 裸 world 拒收（GPT-5.5 review 3.1）
    "flag",   # 裸 flag 拒收
    "player",  # 裸 player 拒收
    "faction",  # 裸 faction（缺 id）拒收
    "relationship",  # 裸 relationship（缺 slug）拒收
    "relationship.vellin",  # 仅 slug 段拒收（缺 field 段；ADR-016 形态 relationship.<slug>.<field>）
])
def test_state_paths_read_bare_namespace_rejected(bare_path: str) -> None:
    """GPT-5.5 review 3.1 修订：F15 加严要求 sidecar state_paths_read 必须落入
    完整 ADR-016 命名空间路径，**裸 namespace（world / flag / player /
    relationship.<slug>）拒收**——避免 dep_propagate 反向 propagate 时把
    'world' 整个命名空间的 stale-mark 与具体 'world.scene_count' 混淆。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_read"] = [bare_path]
    assert not v.is_valid(bad), f"bare namespace {bare_path!r} should be rejected"


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
    """F15 新增：scene_id pattern `^[a-z0-9_]+$` 严约：大写字母拒收。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["scene_id"] = "MyScene"
    assert not v.is_valid(bad)


def test_scene_id_starts_with_digit_accepted() -> None:
    """GPT-5.5 review 3.2 修订：scene_id pattern `^[a-z0-9_]+$` 与 ADR-023
    决策核心明示对齐——数字起首合法（与 dialogue_graph.graph_id 形态对齐，仅
    去掉连字符）。本测试是 review 3.2 反向锁——防止未来错回 `^[a-z]...$` 收紧。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["scene_id"] = "1scene"
    assert v.is_valid(sidecar)


def test_scene_id_with_hyphen_rejected() -> None:
    """scene_id pattern 字符集 [a-z0-9_]：连字符拒收（与 dialogue_graph.graph_id
    pattern 比仅去掉连字符——避免 sidecar 文件名与目录解析歧义）。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["scene_id"] = "my-scene"
    assert not v.is_valid(bad)


def test_scene_id_underscore_only_accepted() -> None:
    """scene_id pattern 仅约下划线 + 字母数字；典型 `glades_ironoath_waystation`
    （gold scene graph_id 形态）合法。"""
    v = _validator()
    sidecar = make_minimal_sidecar()
    sidecar["scene_id"] = "glades_ironoath_waystation"
    assert v.is_valid(sidecar)


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


def test_act_id_with_underscore_accepted() -> None:
    """GPT-5.5 review 4.1 修订：act_id pattern 与 chapter.schema.json
    `^act_[a-z0-9_]{1,64}$` 严格同源——典型 'act_arrival' 合法。"""
    v = _validator()
    sidecar = make_full_sidecar()
    sidecar["act_id"] = "act_arrival"
    assert v.is_valid(sidecar)


@pytest.mark.parametrize("bad_act_id", [
    "act",  # GPT-5.5 review 4.1：缺下划线 + 后缀拒收
    "actarrival",  # GPT-5.5 review 4.1：缺下划线分隔拒收
    "ACT_arrival",  # 大写拒收
    "act-arrival",  # 连字符拒收
    "act_",  # 缺后缀字符拒收（pattern 后缀至少 1 字符）
])
def test_act_id_invalid_patterns_rejected(bad_act_id: str) -> None:
    """GPT-5.5 review 4.1 修订：act_id 与 chapter.schema.json 严格同源——
    避免 sidecar 引用侧记录 chapter 不可解析的 id。本组反例锁严约边界。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["act_id"] = bad_act_id
    assert not v.is_valid(bad), f"act_id={bad_act_id!r} should be rejected"


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
    """scene_history_referenced items pattern 与 scene_id 同源 `^[a-z0-9_]+$`
    （GPT-5.5 review 3.2 修订）：大写 / 连字符拒收；数字起首合法。"""
    v = _validator()
    bad = make_full_sidecar()
    bad["scene_history_referenced"] = ["MyPriorScene"]  # 大写拒收
    assert not v.is_valid(bad)


def test_scene_history_referenced_digit_lead_accepted() -> None:
    """GPT-5.5 review 3.2 反向锁：与 scene_id 同源——数字起首合法。"""
    v = _validator()
    sidecar = make_full_sidecar()
    sidecar["scene_history_referenced"] = ["1prior_scene"]
    assert v.is_valid(sidecar)


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
    "relationship.vellin",  # GPT-5.5 review 3.1：仅 slug，缺 field 段
    "world",  # GPT-5.5 review 3.1：裸 world 拒收
    "flag",  # GPT-5.5 review 3.1：裸 flag 拒收
    "player",  # GPT-5.5 review 3.1：裸 player 拒收
    ".world",  # 起始 . 拒收
])
def test_state_paths_written_invalid_namespace_rejected(bad_path: str) -> None:
    """F15 加严：write 侧命名空间 pattern 与 read 侧同源严约。GPT-5.5 review 3.1
    修订：裸 namespace（world / flag / player / faction / relationship.<slug>）
    全部拒收，避免 dep_propagate 反向 propagate 时把命名空间整体 stale-mark
    与具体 path 混淆。"""
    v = _validator()
    bad = make_minimal_sidecar()
    bad["state_paths_written"] = [bad_path]
    assert not v.is_valid(bad), f"path {bad_path!r} should be rejected"
