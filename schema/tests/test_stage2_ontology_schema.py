"""T-2.2 schema 关键卡口测试（critique 4.5；STAGE_2_TASKS §2.4 / §2.5 / §2.6）。

覆盖目标：
- waystation.json 三个 character 对象通过 character.schema.json 校验（含 envelope
  字段 + state_path_slug + character_features + relations + dramatic_triggers
  + visual_assets）。
- scene_waystation_of_iron_oath（envelope 迁移后 type="location"）通过
  location.schema.json。
- 构造 sample clock 通过 clock.schema.json；超界（ticks_total > 20）拒收；
  advance_rule.type 不存在 time_based 子类（ADR-017）。
- 构造空 chapter（acts 空数组）通过 chapter.schema.json。
- **关键回归**：gold scene `/content/test_scene_v0/scene.json` 仍 pass
  dialogue_graph schema v0.1.1（critique 3.2 / §2.4 核心约束）。
- generation_trace 含 slot_assignments 在 dialogue_graph schema 下被接受
  （ADR-019 / §2.4 兼容路径）。
- state path 命名空间表（world / faction / relationship / flag / player）枚举
  校验：作为白名单注释存在，本测试只断言 gold scene 中实际使用的所有 path
  前缀都落入这五个命名空间。

新建 schema 与既有 dialogue_graph 解耦：character / location / clock / chapter
首版 const "0.3.0"；既有 dialogue_graph / node / option / state_effect /
state_condition 的 schema_version const **保持 "0.1.1" 不动**（v1.0 §2.4）。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCHEMA_DIR.parent
ONTOLOGY_PATH = REPO_ROOT / "state" / "ontology" / "waystation.json"
GOLD_SCENE_PATH = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"

DIALOGUE_GRAPH_SCHEMA_FILES = [
    "dialogue_graph.schema.json",
    "node.schema.json",
    "option.schema.json",
    "state_effect.schema.json",
    "state_condition.schema.json",
]

STAGE_2_SCHEMA_FILES = [
    "character.schema.json",
    "location.schema.json",
    "clock.schema.json",
    "chapter.schema.json",
]

# ADR-016 五个 state path 命名空间（v1.0 §2.6 修订：`relationship.<state_path_slug>.*`）
STATE_PATH_NAMESPACES = ("world", "faction", "relationship", "flag", "player")


def _load_registry() -> Registry:
    """合并 dialogue_graph cluster + 阶段 2 ontology cluster 到单一 referencing
    registry，以便 dialogue_graph 跨文件 $ref 解析仍然正常。
    """
    registry = Registry()
    for name in DIALOGUE_GRAPH_SCHEMA_FILES + STAGE_2_SCHEMA_FILES:
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(uri=schema["$id"], resource=resource)
    return registry


_REGISTRY = _load_registry()


def _validator(schema_filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_REGISTRY)


def _load_ontology() -> dict:
    return json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. character.schema.json — waystation.json 三个 character 全过 + envelope 卡口
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("char_id", ["char_vellin", "char_corvan", "char_aelwin"])
def test_waystation_character_passes_character_schema(char_id: str) -> None:
    """三个 character entity 完整对象通过 character.schema.json（含 envelope 字段）。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    entity = next(e for e in ontology["entities"] if e.get("id") == char_id)
    errors = sorted(v.iter_errors(entity), key=lambda e: e.path)
    assert errors == [], (
        f"{char_id} failed character.schema.json validation: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_character_schema_rejects_wrong_id_pattern() -> None:
    """envelope 卡口（v1.0 §2.5）：character entity id 必须 `^char_[a-z0-9_]+$`。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    entity = copy.deepcopy(
        next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    )
    entity["id"] = "vellin"  # 缺 char_ 前缀
    assert not v.is_valid(entity)


def test_character_schema_rejects_wrong_type_const() -> None:
    """envelope 卡口（v1.0 §2.5）：type const 必须为 "character"。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    entity = copy.deepcopy(
        next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    )
    entity["type"] = "location"
    assert not v.is_valid(entity)


def test_character_schema_state_path_slug_pattern() -> None:
    """v1.0 §2.6：state_path_slug 仅允许小写字母/数字/下划线。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    base = next(e for e in ontology["entities"] if e["id"] == "char_vellin")

    bad = copy.deepcopy(base)
    bad["state_path_slug"] = "Vellin"  # 大写不允许
    assert not v.is_valid(bad)

    bad2 = copy.deepcopy(base)
    bad2["state_path_slug"] = "vellin-bad"  # 连字符不允许
    assert not v.is_valid(bad2)


def test_character_schema_relations_narrative_weight_enum() -> None:
    """ADR-018：narrative_weight 仅允许 core / minor / context_only。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    bad = copy.deepcopy(
        next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    )
    bad["relations"][0]["narrative_weight"] = "mandatory"
    assert not v.is_valid(bad)


def test_character_schema_dramatic_triggers_required_fields() -> None:
    """ADR-019：dramatic_triggers 每项 trait/when/how 必填。"""
    v = _validator("character.schema.json")
    ontology = _load_ontology()
    bad = copy.deepcopy(
        next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    )
    bad["dramatic_triggers"].append({"trait": "x", "when": "y"})  # 缺 how
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 2. location.schema.json — 迁移后 scene_waystation_of_iron_oath 全过 + envelope
# ---------------------------------------------------------------------------

def test_scene_waystation_passes_location_schema() -> None:
    """envelope 迁移（T-2.2）后 scene_waystation_of_iron_oath 应通过 location.schema.json。"""
    v = _validator("location.schema.json")
    ontology = _load_ontology()
    entity = next(
        e for e in ontology["entities"] if e["id"] == "scene_waystation_of_iron_oath"
    )
    errors = sorted(v.iter_errors(entity), key=lambda e: e.path)
    assert errors == [], (
        "scene_waystation_of_iron_oath failed location.schema.json: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )
    # 显式断言迁移后的 envelope 与 location_type 对齐
    assert entity["type"] == "location"
    assert entity["location_type"] == "scene"


def test_location_schema_id_pattern_accepts_loc_prefix() -> None:
    """ADR-016：location id 兼容 scene_*（场景）+ loc_*（子位置）双前缀。"""
    v = _validator("location.schema.json")
    sample = {
        "id": "loc_vellin_office",
        "type": "location",
        "display_name": "Vellin's office",
        "description": "驿站二楼角落的小账房；只有 Vellin 进出。",
        "location_type": "sublocation",
        "parent_location_ref": "scene_waystation_of_iron_oath",
    }
    assert v.is_valid(sample)


def test_location_schema_rejects_wrong_id_pattern() -> None:
    v = _validator("location.schema.json")
    sample = {
        "id": "char_vellin",  # character 前缀不能用于 location
        "type": "location",
        "display_name": "x",
        "description": "y",
        "location_type": "scene",
    }
    assert not v.is_valid(sample)


# ---------------------------------------------------------------------------
# 3. clock.schema.json — sample 通过 + 超界拒收 + ADR-017 advance_rule 枚举
# ---------------------------------------------------------------------------

def _sample_clock() -> dict:
    return {
        "schema_version": "0.3.0",
        "id": "clk_iron_oath_pursuit",
        "name": "铁誓追捕度",
        "scope": "faction",
        "ticks_total": 6,
        "ticks_filled": 0,
        "advance_rule": {"type": "every_n_scenes", "params": {"n": 2}},
        "tick_effects": [
            {
                "at_tick": 6,
                "effect_op": "set",
                "path": "flag.iron_oath_full_pursuit",
                "value": True,
            }
        ],
    }


def test_clock_schema_sample_valid() -> None:
    v = _validator("clock.schema.json")
    assert v.is_valid(_sample_clock())


def test_clock_schema_ticks_total_max_20() -> None:
    """ADR-017 schema maximum：单 clock ticks_total ≤ 20。"""
    v = _validator("clock.schema.json")
    bad = _sample_clock()
    bad["ticks_total"] = 21
    assert not v.is_valid(bad)


def test_clock_schema_advance_rule_no_time_based() -> None:
    """ADR-017：advance_rule.type 不存在 time_based 子类（运行时无真时间）。"""
    v = _validator("clock.schema.json")
    bad = _sample_clock()
    bad["advance_rule"] = {"type": "time_based", "params": {"interval_minutes": 5}}
    assert not v.is_valid(bad)


def test_clock_schema_id_pattern() -> None:
    v = _validator("clock.schema.json")
    bad = _sample_clock()
    bad["id"] = "clock_no_clk_prefix"
    assert not v.is_valid(bad)


# ---------------------------------------------------------------------------
# 4. chapter.schema.json — 空 acts 通过 + 含一个 act 通过
# ---------------------------------------------------------------------------

def test_chapter_schema_empty_acts_valid() -> None:
    v = _validator("chapter.schema.json")
    sample = {
        "chapter_id": "chap_iron_oath_betrayal",
        "display_name": "铁誓背叛",
        "acts": [],
    }
    assert v.is_valid(sample)


def test_chapter_schema_with_one_act_valid() -> None:
    v = _validator("chapter.schema.json")
    sample = {
        "chapter_id": "chap_iron_oath_betrayal",
        "display_name": "铁誓背叛",
        "acts": [
            {
                "act_id": "act_arrival",
                "display_name": "驿站抵达",
                "included_scenes": ["scene_waystation_of_iron_oath"],
            }
        ],
    }
    assert v.is_valid(sample)


def test_chapter_schema_rejects_bad_act_id_pattern() -> None:
    v = _validator("chapter.schema.json")
    sample = {
        "chapter_id": "chap_x",
        "display_name": "x",
        "acts": [
            {
                "act_id": "ACT_1",  # 大写 / 缺 act_ 前缀
                "display_name": "y",
                "included_scenes": [],
            }
        ],
    }
    assert not v.is_valid(sample)


# ---------------------------------------------------------------------------
# 5. 关键回归：gold scene 仍 pass dialogue_graph schema v0.1.1（critique 3.2 / §2.4）
# ---------------------------------------------------------------------------

def test_gold_scene_still_passes_dialogue_graph_v0_1_1() -> None:
    """T-2.2 v1.0 §2.4 核心约束：既有 schema const 不动 → gold scene 不破。"""
    v = _validator("dialogue_graph.schema.json")
    gold = json.loads(GOLD_SCENE_PATH.read_text(encoding="utf-8"))
    errors = sorted(v.iter_errors(gold), key=lambda e: e.path)
    assert errors == [], (
        "gold scene failed dialogue_graph schema v0.1.1: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )
    # 显式断言 const 没有被本任务误改
    assert gold["schema_version"] == "0.1.1"


def test_dialogue_graph_schema_version_const_unchanged() -> None:
    """T-2.2 v1.0 §2.4：dialogue_graph const 严格保持 0.1.1，不允许 bump。"""
    schema = json.loads((SCHEMA_DIR / "dialogue_graph.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "0.1.1"


def test_node_schema_version_const_unchanged() -> None:
    """T-2.2 v1.0 §2.4：node 不直接定义 schema_version 字段，但其上游
    dialogue_graph 的 const 不能 bump（已由上一测试覆盖）；本测试断言 node
    schema 自身没被 schema_version 字段偷偷塞进来。"""
    schema = json.loads((SCHEMA_DIR / "node.schema.json").read_text(encoding="utf-8"))
    assert "schema_version" not in schema.get("required", [])
    assert "schema_version" not in schema.get("properties", {})


# ---------------------------------------------------------------------------
# 6. generation_trace.slot_assignments 兼容路径（ADR-019 / §2.4）
# ---------------------------------------------------------------------------

def _minimal_dialogue_graph() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "tmp_test_graph",
        "entry_node_id": "n_start",
        "scene_anchor": "scene_waystation_of_iron_oath",
        "character_refs": ["char_vellin"],
        "nodes": {
            "n_start": {
                "node_id": "n_start",
                "type": "end",
                "narration": "the end",
                "speaker_ref": None,
                "location_ref": "scene_waystation_of_iron_oath",
                "options": [],
            }
        },
    }


def test_slot_assignments_accepted_in_node_generation_trace() -> None:
    """ADR-019 / §2.4：generation_trace.slot_assignments 作为 optional 字段
    在 node schema 下被接受；既有 v0.1.1 trace（无该字段）继续合法。
    """
    v = _validator("dialogue_graph.schema.json")
    g = _minimal_dialogue_graph()
    g["nodes"]["n_start"]["generation_trace"] = {
        "source": "llm",
        "slot_assignments": {
            "the_betrayer": {
                "character_ref": "char_vellin",
                "assigned_at": "2026-05-03T10:00:00Z",
                "source_prompt_hash": "a" * 64,
            }
        },
    }
    errors = sorted(v.iter_errors(g), key=lambda e: e.path)
    assert errors == [], "; ".join(
        f"{list(e.path)}: {e.message}" for e in errors
    )


def test_slot_assignments_absent_still_valid() -> None:
    """generation_trace 不含 slot_assignments 仍合法（向后兼容 v0.1.x）。"""
    v = _validator("dialogue_graph.schema.json")
    g = _minimal_dialogue_graph()
    g["nodes"]["n_start"]["generation_trace"] = {"source": "human"}
    assert v.is_valid(g)


def test_slot_assignments_missing_required_subfield_rejected() -> None:
    """slot_assignments 内每个 entry 必须三键齐全（character_ref / assigned_at /
    source_prompt_hash），缺失任一被 schema 拒收。"""
    v = _validator("dialogue_graph.schema.json")
    g = _minimal_dialogue_graph()
    g["nodes"]["n_start"]["generation_trace"] = {
        "source": "llm",
        "slot_assignments": {
            "the_witness": {
                "character_ref": "char_aelwin",
                # 缺 assigned_at
                "source_prompt_hash": None,
            }
        },
    }
    assert not v.is_valid(g)


def test_slot_assignments_bad_character_ref_rejected() -> None:
    """slot_assignments.<slot>.character_ref 必须 `^char_[a-z0-9_]+$`。"""
    v = _validator("dialogue_graph.schema.json")
    g = _minimal_dialogue_graph()
    g["nodes"]["n_start"]["generation_trace"] = {
        "source": "llm",
        "slot_assignments": {
            "the_betrayer": {
                "character_ref": "vellin",  # 缺 char_ 前缀
                "assigned_at": "2026-05-03T10:00:00Z",
                "source_prompt_hash": None,
            }
        },
    }
    assert not v.is_valid(g)


# ---------------------------------------------------------------------------
# 7. state path 命名空间表（ADR-016 / §2.6）— gold scene 用到的所有 path 全部
#    落入五个命名空间之一
# ---------------------------------------------------------------------------

def _collect_paths_from_node(node: dict) -> set[str]:
    """递归收集节点中 effects + condition 内出现的所有 path 字符串首段。"""
    prefixes: set[str] = set()

    def visit_effect_or_condition(obj: dict) -> None:
        path = obj.get("path")
        if isinstance(path, str):
            prefixes.add(path.split(".", 1)[0])
        elif isinstance(path, list) and path:
            prefixes.add(path[0])
        # 复合 condition 递归
        for compound_key in ("all_of", "any_of"):
            if compound_key in obj:
                for child in obj[compound_key]:
                    visit_effect_or_condition(child)
        if "not" in obj:
            visit_effect_or_condition(obj["not"])

    for eff in node.get("on_enter_effects", []) or []:
        visit_effect_or_condition(eff)
    for opt in node.get("options", []) or []:
        for eff in opt.get("effects", []) or []:
            visit_effect_or_condition(eff)
        cond = opt.get("condition")
        if isinstance(cond, dict):
            visit_effect_or_condition(cond)
    return prefixes


def test_gold_scene_paths_all_within_state_namespace_whitelist() -> None:
    """ADR-016 五个 state path 命名空间作为白名单：gold scene 中所有 effect /
    condition 的 path 首段必须落入 (world / faction / relationship / flag /
    player) 之一。本测试为 schema 与 ADR-016 命名空间表的端到端一致性回归——
    若未来 ADR 修订命名空间，本测试会先报警。"""
    gold = json.loads(GOLD_SCENE_PATH.read_text(encoding="utf-8"))
    all_prefixes: set[str] = set()
    for node in gold["nodes"].values():
        all_prefixes |= _collect_paths_from_node(node)
    illegal = all_prefixes - set(STATE_PATH_NAMESPACES)
    assert illegal == set(), (
        f"gold scene 用到了 ADR-016 命名空间表外的 path 首段: {illegal!r}"
    )
