"""assemble 复用符号公共化单测（T-3P-0）.

T-3P-2（P-B 回流合并）要复用 assemble 的三个确定性工具函数；把"事实共享契约"
显式化为公开别名 + __all__ 导出，避免跨包 import 私有符号。
**别名必须是同一对象**（不改任何现有函数行为——硬边界）。
"""
from __future__ import annotations

from generator.multipass import assemble


def test_public_aliases_are_same_objects() -> None:
    assert assemble.normalize_line is assemble._normalize_line
    assert assemble.dialogue_entries is assemble._dialogue_entries
    assert assemble.mk_option is assemble._mk_option


def test_public_aliases_exported_in_all() -> None:
    for name in ("normalize_line", "dialogue_entries", "mk_option", "entry_graph_node_id"):
        assert name in assemble.__all__


def test_alias_behavior_smoke() -> None:
    """经公开别名走一遍既有行为（行为本身已有既存测试覆盖，这里只 smoke 别名可用）。"""
    assert assemble.normalize_line("「先听着。」") == "先听着。"
    entries = assemble.dialogue_entries("char_lucy", ["「一句。」", "", "两句。"])
    assert entries == [
        {"speaker_ref": "char_lucy", "line": "一句。"},
        {"speaker_ref": "char_lucy", "line": "两句。"},
    ]
    opt = assemble.mk_option("opt_x_1", "我直说了。", "hub")
    assert opt["option_id"] == "opt_x_1" and opt["target_node_id"] == "hub"
    assert opt["condition"] is None and opt["unavailable_behavior"] == "hide"
