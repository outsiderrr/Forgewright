"""回流格式契约 v1 常量表单测（T-3P-0；拆解文档 §4 落码，代码为准）.

format_spec 只定义契约（常量 + 错误分类），不含解析器（解析器 = T-3P-2）。
本测试把 §4.1 标签语法 / 节点类别必交 key 表 / §4.2 E1-E8 逐 case 钉死，
防止后续任务无声改契约。
"""
from __future__ import annotations

from generator.promptpack.format_spec import (
    DIALOGUE_ITEM_PREFIX,
    ERRORS,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_USAGE,
    KEY_CONTINUE,
    KEY_DIALOGUE,
    KEY_NARRATION,
    KEY_OPTIONS,
    NODE_CATEGORY_KEYS,
    NODE_HEADER_TEMPLATE,
    OPTION_LINE_TEMPLATE,
)


def test_tag_syntax_constants_match_spec_v1() -> None:
    """§4.1 标签语法逐字面锁定。"""
    assert NODE_HEADER_TEMPLATE.format(node_id="soft_line_b1") == "[node: soft_line_b1]"
    assert (KEY_NARRATION, KEY_DIALOGUE, KEY_OPTIONS, KEY_CONTINUE) == (
        "narration",
        "dialogue",
        "options",
        "continue",
    )
    assert DIALOGUE_ITEM_PREFIX == "- "
    assert OPTION_LINE_TEMPLATE.format(index=1, text="我直说了。") == "1: 我直说了。"


def test_node_category_required_keys() -> None:
    """节点类别 → 必交 key：choice=narration+options；beats 拍=narration+continue；end=narration。"""
    assert set(NODE_CATEGORY_KEYS) == {"choice", "beat", "end"}
    assert NODE_CATEGORY_KEYS["choice"]["required"] == ["narration", "options"]
    assert NODE_CATEGORY_KEYS["beat"]["required"] == ["narration", "continue"]
    assert NODE_CATEGORY_KEYS["end"]["required"] == ["narration"]
    # dialogue 对三类节点都是可选（end 0-2 行可选同样走这里）
    for cat in ("choice", "beat", "end"):
        assert NODE_CATEGORY_KEYS[cat]["optional"] == ["dialogue"]


def test_node_category_keys_survive_json_round_trip() -> None:
    """契约数据 JSON-native（架构共识 1）：dumps→loads 后与常量原值相等。"""
    import json

    assert json.loads(json.dumps(NODE_CATEGORY_KEYS)) == NODE_CATEGORY_KEYS


def test_error_codes_e1_to_e8_locked() -> None:
    """§4.2 硬报错分类：八个 code、slug 逐条对应。"""
    assert [e.code for e in ERRORS.values()] == [f"E{i}" for i in range(1, 9)]
    slugs = {e.code: e.slug for e in ERRORS.values()}
    assert slugs == {
        "E1": "missing_node",
        "E2": "unknown_node",
        "E3": "duplicate_node",
        "E4": "option_count_mismatch",
        "E5": "missing_field",
        "E6": "unknown_key",
        "E7": "empty_text",
        "E8": "parse_error",
    }


def test_error_boundary_cases_documented() -> None:
    """边界判定逐 case 定死：options 整体缺失=E5；序号缺/多/不连续=E4；错位块=E6。"""
    assert "整体缺失" in ERRORS["E5"].boundary and "options" in ERRORS["E5"].boundary
    for kw in ("缺号", "多号", "不连续"):
        assert kw in ERRORS["E4"].boundary
    assert "end" in ERRORS["E6"].boundary and "options" in ERRORS["E6"].boundary


def test_exit_codes_three_states() -> None:
    """CLI 退出码三态：0=成功 / 1=回流拒收 / 2=用法・输入错误。"""
    assert (EXIT_OK, EXIT_REJECTED, EXIT_USAGE) == (0, 1, 2)
