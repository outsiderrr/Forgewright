"""T-1.5.2：对 /schema/image_asset.schema.json（Draft 2020-12）的正/负样本测试。

GPT-5.5 L2 critique 4.2 修补：schema 关键路径必须有 schema 层测试，不能等
T-1.5.3 codegen 才发现 schema 错误。

覆盖维度（仅 schema 层 — 字段存在 / 类型 / 枚举 / 边界 / additionalProperties）：

- 最小正样本（character_sheet + scene_background）
- 三个硬闸门 required 缺失（target_ref / target_type / asset_role）
- Round 5 U-GPT-6 软闸门 provenance 字段默认值
- additionalProperties: false
- target_type 枚举越界
- width 边界（256 / 4096）

**不在本测试覆盖范围**：character_ref / location_ref 与 target_ref / target_type 的
一致性约束。这是 image_validator 语义层职责（image_asset.schema.json description 已声明）。
schema 层仅声明字段类型 / 枚举 / 边界。
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SCHEMA_DIR / "image_asset.schema.json"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------

def make_valid_character_asset() -> dict:
    """character_sheet 的最小合法样本。
    含全部 11 个 required 字段 + character_ref/location_ref 镜像约定。
    """
    return {
        "asset_id": "img_vellin_neutral",
        "asset_kind": "character_sheet",
        "target_ref": "char_vellin",
        "target_type": "character",
        "asset_role": "character_sheet",
        "character_ref": "char_vellin",
        "location_ref": None,
        "source_mode": "manual",
        "format": "png",
        "width": 1024,
        "height": 1536,
        "file_path": "content/visuals/vellin/img_vellin_neutral.png",
        "created_at": "2026-05-01T12:00:00Z",
    }


def make_valid_scene_background() -> dict:
    """scene_background 的最小合法样本（target_type=scene 试点）。"""
    return {
        "asset_id": "img_waystation_dusk",
        "asset_kind": "scene_background",
        "target_ref": "scene_waystation_of_iron_oath",
        "target_type": "scene",
        "asset_role": "scene_background",
        "character_ref": None,
        "location_ref": "scene_waystation_of_iron_oath",
        "source_mode": "api",
        "format": "webp",
        "width": 2048,
        "height": 1152,
        "file_path": "content/visuals/_scenes/img_waystation_dusk.webp",
        "created_at": "2026-05-01T12:00:00Z",
    }


# ---------------------------------------------------------------------------
# 正样本
# ---------------------------------------------------------------------------

def test_minimal_valid_character_asset():
    v = _validator()
    assert v.is_valid(make_valid_character_asset())


def test_minimal_valid_scene_background():
    v = _validator()
    assert v.is_valid(make_valid_scene_background())


def test_provenance_defaults():
    """Round 5 U-GPT-6 软闸门 provenance 字段默认值合法（schema 层接受）。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["reference_ids"] = []
    sample["reference_license_note"] = ""
    sample["open_source_ok"] = False
    sample["commercial_ok"] = False
    assert v.is_valid(sample)


def test_schema_version_const_when_present():
    """schema_version 可省略；若填则必为 '0.2.0'（const）。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["schema_version"] = "0.2.0"
    assert v.is_valid(sample)


# ---------------------------------------------------------------------------
# 负样本：required 缺失（三个硬闸门）
# ---------------------------------------------------------------------------

def test_missing_target_ref_fails():
    """Round 5 U-GPT-3 硬闸门：target_ref 必填。"""
    v = _validator()
    sample = make_valid_character_asset()
    del sample["target_ref"]
    assert not v.is_valid(sample)


def test_missing_target_type_fails():
    """Round 5 U-GPT-3 硬闸门：target_type 必填。"""
    v = _validator()
    sample = make_valid_character_asset()
    del sample["target_type"]
    assert not v.is_valid(sample)


def test_missing_asset_role_fails():
    """Round 5 U-GPT-3 硬闸门：asset_role 必填。"""
    v = _validator()
    sample = make_valid_character_asset()
    del sample["asset_role"]
    assert not v.is_valid(sample)


# ---------------------------------------------------------------------------
# 负样本：结构约束
# ---------------------------------------------------------------------------

def test_additional_properties_rejected():
    """additionalProperties: false — 未声明字段被拒收。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["unexpected_field"] = "noise"
    assert not v.is_valid(sample)


def test_invalid_target_type_enum():
    """target_type 枚举仅允许 character / location / scene。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["target_type"] = "other"
    assert not v.is_valid(sample)


# ---------------------------------------------------------------------------
# 负样本：分辨率边界
# ---------------------------------------------------------------------------

def test_resolution_below_min():
    """width < 256 拒收（缩略图最低边界）。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["width"] = 128
    assert not v.is_valid(sample)


def test_resolution_above_max():
    """width > 4096 拒收（API 上限 + 入库存储上限）。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["width"] = 8192
    assert not v.is_valid(sample)


def test_schema_version_wrong_value_rejected():
    """schema_version const='0.2.0'；其他值（如 '0.1.1' / '0.3.0'）拒收。"""
    v = _validator()
    sample = make_valid_character_asset()
    sample["schema_version"] = "0.1.1"
    assert not v.is_valid(sample)
