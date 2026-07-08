"""T-3P-2 回流硬报错矩阵：E1-E8 逐类 + 边界归属 + 混合多错一单收全.

语义基准 = format_spec.ERRORS 的逐 case 边界（单一真相源）；本文件把
"硬报错不许软化"钉死：任一 E → graph=None（不产 scene.json）、错误全收集不
fail-fast。骨架一律经 io.load_design_artifact 读（mini design 走同一 loader 契约）。
"""
from __future__ import annotations

import pytest

from generator.promptpack.ingest import ingest_reply, parse_reply
from generator.promptpack.io import load_design_artifact
from generator.promptpack.tests.helpers import MINI_GOOD_REPLY, write_mini_design


@pytest.fixture
def mini_design(tmp_path):
    return load_design_artifact(write_mini_design(tmp_path))


def _codes(result) -> list[str]:
    return [e.code for e in result.errors]


def _only(result, code: str):
    """断言结果恰好一条错误且为指定代码，返回它（错误归属唯一性检查）。"""
    assert _codes(result) == [code], [
        (e.code, e.node_id, e.actual) for e in result.errors
    ]
    return result.errors[0]


# ---------------------------------------------------------------------------
# 正向基线：合法回流零错误（错误矩阵的对照组）
# ---------------------------------------------------------------------------


def test_good_reply_zero_errors(mini_design) -> None:
    result = ingest_reply(mini_design, MINI_GOOD_REPLY)
    assert result.ok and result.errors == []
    assert result.graph is not None


# ---------------------------------------------------------------------------
# E1 missing_node
# ---------------------------------------------------------------------------


def test_e1_missing_node(mini_design) -> None:
    blocks = MINI_GOOD_REPLY.split("\n\n")
    reply = "\n\n".join(b for b in blocks if "[node: end_quick]" not in b)
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E1")
    assert err.node_id == "end_quick"
    assert result.graph is None


def test_e1_missing_beat_guidance_carries_locked_reveal(mini_design) -> None:
    """缺 beats 拍的修改指引要带上本拍锁定线索（编剧照着补写）。"""
    blocks = MINI_GOOD_REPLY.split("\n\n")
    reply = "\n\n".join(b for b in blocks if "[node: line_a_b2]" not in b)
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E1")
    assert err.node_id == "line_a_b2"
    assert "线索二" in err.guidance


# ---------------------------------------------------------------------------
# E2 unknown_node
# ---------------------------------------------------------------------------


def test_e2_unknown_node(mini_design) -> None:
    reply = MINI_GOOD_REPLY + "\n[node: extra_node]\nnarration: 不在清单里的块。\n"
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E2")
    assert err.node_id == "extra_node"
    assert result.graph is None


def test_e2_typo_node_id_reports_both_e1_and_e2(mini_design) -> None:
    """改 node_id 拼写 = 原节点缺失（E1）+ 冒出未知节点（E2），两条都要报。"""
    reply = MINI_GOOD_REPLY.replace("[node: end_quick]", "[node: end_qwick]")
    result = ingest_reply(mini_design, reply)
    assert _codes(result) == ["E1", "E2"]
    assert result.errors[0].node_id == "end_quick"
    assert result.errors[1].node_id == "end_qwick"


# ---------------------------------------------------------------------------
# E3 duplicate_node
# ---------------------------------------------------------------------------


def test_e3_duplicate_node(mini_design) -> None:
    reply = MINI_GOOD_REPLY + "\n[node: end_a]\nnarration: 同一节点第二个块。\n"
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E3")
    assert err.node_id == "end_a"
    assert "第二次出现" in err.actual


def test_e3_duplicate_block_content_discarded_and_not_nitpicked(mini_design) -> None:
    """重复块 = 影子块：内容不并入首块，块内问题不逐条挑错（E3 删块优先）。"""
    reply = MINI_GOOD_REPLY + "\n[node: end_a]\nnarration:\nbogus_key: 甲\n"
    result = ingest_reply(mini_design, reply)
    _only(result, "E3")  # 影子块内的 E7 空 narration / E6 未知 key 都不报
    parsed, _ = parse_reply(reply)
    assert parsed["end_a"].fields["narration"].startswith("你退出门外")


# ---------------------------------------------------------------------------
# E4 option_count_mismatch（锁定选项数 = 2）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lines, described",
    [
        ("  1: 我只交一条。", "1:"),  # 少交
        ("  1: 我交一。\n  2: 我交二。\n  3: 我多交了。", "3:"),  # 多交
        ("  1: 我交一。\n  3: 我跳号了。", "3:"),  # 不连续
        ("  1: 我交一。\n  1: 我重号了。", "1: / 1:"),  # 重复序号
        ("  2: 我从二开始。\n  3: 我到三。", "2: / 3:"),  # 起点不是 1
    ],
)
def test_e4_option_number_mismatch(mini_design, lines: str, described: str) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "  1: 我想打听一个人。\n  2: 我什么都不问，先走了。", lines
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E4")
    assert err.node_id == "start"
    assert "1..2" in err.expected
    assert described in err.actual
    assert result.graph is None


# ---------------------------------------------------------------------------
# E5 missing_field
# ---------------------------------------------------------------------------


def test_e5_missing_narration(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace("narration: 你转身离开，没有回头。\n", "")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E5")
    assert err.node_id == "end_quick"
    assert "narration" in err.expected


def test_e5_options_block_entirely_missing_is_e5_not_e4(mini_design) -> None:
    """options 块整体缺失 = E5（必填块缺失），与 E4（块在但序号不对）互斥。"""
    reply = MINI_GOOD_REPLY.replace(
        "options:\n  1: 我想打听一个人。\n  2: 我什么都不问，先走了。\n", ""
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E5")
    assert err.node_id == "start"
    assert "1..2" in err.guidance


def test_e5_missing_continue_on_beat(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace("continue: 我记下了。\n", "")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E5")
    assert err.node_id == "line_a_b2"
    assert "20 字" in err.guidance


# ---------------------------------------------------------------------------
# E6 unknown_key（未知 key / 错位块 / 重复已知 key）
# ---------------------------------------------------------------------------


def test_e6_unknown_key(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "[node: end_a]\nnarration:",
        "[node: end_a]\nspeaker: 露西\nnarration:",
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E6")
    assert err.node_id == "end_a"
    assert "speaker" in err.actual


def test_e6_unknown_key_block_content_swallowed_no_e8_cascade(mini_design) -> None:
    """未知 key 的块内容整体吞掉：一条 E6，不级联一串 E8。"""
    reply = MINI_GOOD_REPLY.replace(
        "[node: end_a]\nnarration:",
        "[node: end_a]\nnotes:\n  - 草稿一\n  - 草稿二\nnarration:",
    )
    result = ingest_reply(mini_design, reply)
    _only(result, "E6")


def test_e6_end_node_with_options_is_misplaced_block(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "narration: 你转身离开，没有回头。",
        "narration: 你转身离开，没有回头。\noptions:\n  1: 我不该在这里选。",
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E6")
    assert err.node_id == "end_quick"
    assert "options" in err.actual
    assert "end 节点" in err.guidance


def test_e6_choice_with_continue_is_misplaced_block(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "  2: 我什么都不问，先走了。",
        "  2: 我什么都不问，先走了。\ncontinue: 我不该有接话。",
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E6")
    assert err.node_id == "start"
    assert "continue" in err.actual


def test_e6_duplicate_known_key_recorded_at_second_occurrence(mini_design) -> None:
    """同块已知 key 第二次出现 = E6；首块正常归属（内容不被第二块覆盖）。"""
    reply = MINI_GOOD_REPLY.replace(
        "narration: 你转身离开，没有回头。",
        "narration: 你转身离开，没有回头。\nnarration: 第二个旁白块。",
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E6")
    assert err.node_id == "end_quick"
    assert "第二个" in err.actual
    assert (
        result.parsed["end_quick"].fields["narration"] == "你转身离开，没有回头。"
    )


# ---------------------------------------------------------------------------
# E7 empty_text（逐 case：空 narration / 空 continue / 空序号行 / 空 - 条目 / options 空块）
# ---------------------------------------------------------------------------


def test_e7_empty_narration(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "narration: 你转身离开，没有回头。", "narration:"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "end_quick"


def test_e7_empty_continue(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace("continue: 我记下了。", "continue:")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "line_a_b2"


def test_e7_empty_option_line_does_not_double_as_e4(mini_design) -> None:
    """`2: ` 空正文 = E7；序号集合本身是全的（1..2 都在），不连带误报 E4。"""
    reply = MINI_GOOD_REPLY.replace("  2: 我什么都不问，先走了。", "  2: ")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "start"
    assert "2: 」后正文为空" in err.actual


def test_e7_empty_dialogue_item(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "  - 想问什么就快点问。", "  - 想问什么就快点问。\n  - "
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "start"


def test_e7_quote_only_dialogue_item(mini_design) -> None:
    """只有引号包裹、去包裹后无正文的对白行 = E7（不许静默丢行——那是 assemble 语义）。"""
    reply = MINI_GOOD_REPLY.replace("  - 线索二在雨桶下面。", "  - 「」")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "line_a_b2"


def test_e7_empty_options_block_uniquely_owned_not_e4(mini_design) -> None:
    """options: 在但块内 0 条序号行 → 唯一归属 E7（空块），E4 让出。"""
    reply = MINI_GOOD_REPLY.replace(
        "options:\n  1: 我想打听一个人。\n  2: 我什么都不问，先走了。", "options:"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E7")
    assert err.node_id == "start"
    assert "空块" in err.actual


def test_dialogue_zero_items_is_legal_optional(mini_design) -> None:
    """dialogue: 0 行 = 合法可选（format_spec：不落 E7）。"""
    reply = MINI_GOOD_REPLY.replace(
        "dialogue:\n  - 线索二在雨桶下面。\n", "dialogue:\n"
    )
    result = ingest_reply(mini_design, reply)
    assert result.ok
    assert result.graph["nodes"]["line_a_b2"]["dialogue"] == []


# ---------------------------------------------------------------------------
# E8 parse_error（游离行 / 单行值续行 / 全角冒号 / 块外正文）
# ---------------------------------------------------------------------------


def test_e8_text_before_first_header_is_file_level(mini_design) -> None:
    reply = "编剧的开场留言，不属于任何节点。\n" + MINI_GOOD_REPLY
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id is None
    assert err.line_no == 1


def test_e8_continuation_after_continue_single_line_value(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "continue: 我记下了。", "continue: 我记下了。\n还想补一句续行。"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "line_a_b2"


def test_e8_free_line_inside_dialogue_block(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "  - 想问什么就快点问。", "  - 想问什么就快点问。\n这行忘了写连字符。"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "start"
    assert "- 」" in err.guidance


def test_e8_numbered_line_inside_dialogue_block(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "  - 想问什么就快点问。", "  - 想问什么就快点问。\n  1: 序号行跑错块了。"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "start"


def test_e8_fullwidth_colon_key_line_detected_with_guidance(mini_design) -> None:
    """全角冒号 key 行必须硬报错（不能被 narration 多行值静默吞掉造成对白丢失）。"""
    reply = MINI_GOOD_REPLY.replace("dialogue:\n  - 线索二在雨桶下面。", "dialogue：\n  - 线索二在雨桶下面。")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "line_a_b2"
    assert "半角冒号" in err.guidance
    # 恢复解析：全角冒号块的内容仍归位，不级联 E8
    assert result.parsed["line_a_b2"].fields["dialogue"] == ["线索二在雨桶下面。"]


def test_e8_fullwidth_colon_node_header(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace("[node: end_quick]", "[node： end_quick]")
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "end_quick"
    assert "半角冒号" in err.guidance


def test_e8_inline_value_after_dialogue_key(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "dialogue:\n  - 想问什么就快点问。", "dialogue: 想问什么就快点问。"
    )
    result = ingest_reply(mini_design, reply)
    err = _only(result, "E8")
    assert err.node_id == "start"
    assert "- 」开头" in err.guidance


# ---------------------------------------------------------------------------
# narration 多行值边界（唯一多行 key；吸行为合法而非 E8）
# ---------------------------------------------------------------------------


def test_narration_multiline_absorbs_dash_and_numbered_lines(mini_design) -> None:
    """narration 是唯一多行值：块内到下一个 key 行之前的 `- ` / 序号行都归 narration。"""
    reply = MINI_GOOD_REPLY.replace(
        "narration: 你转身离开，没有回头。",
        "narration: 你转身离开，没有回头。\n- 门轴响了一声。\n1: 这不是选项，是旁白。",
    )
    result = ingest_reply(mini_design, reply)
    assert result.ok
    narration = result.graph["nodes"]["end_quick"]["narration"]
    assert narration == "你转身离开，没有回头。\n- 门轴响了一声。\n1: 这不是选项，是旁白。"


# ---------------------------------------------------------------------------
# 收集语义：多错一单收全 + 退回单按代码分组排序
# ---------------------------------------------------------------------------


def test_mixed_errors_all_collected_in_one_pass(mini_design) -> None:
    """混合多错不 fail-fast：一次 ingest 收全 E1/E4/E6/E7/E8 五类。"""
    reply = (
        "文件开头的游离行。\n"  # E8（文件级）
        + MINI_GOOD_REPLY.replace(
            "  1: 我想打听一个人。\n  2: 我什么都不问，先走了。",
            "  1: 我想打听一个人。\n  3: 我跳号了。",  # E4
        )
        .replace("narration: 她把抹布放下。", "narration:")  # E7（line_a_b2）
        .replace(
            "[node: end_a]\nnarration: 你退出门外，把话都收进兜里。",
            "[node: end_a]\nnarration: 你退出门外，把话都收进兜里。\ncontinue: 错位接话。",  # E6
        )
        .replace("[node: end_quick]", "[node: end_wrong]")  # E1 + E2
    )
    result = ingest_reply(mini_design, reply)
    assert _codes(result) == ["E1", "E2", "E4", "E6", "E7", "E8"]
    assert result.graph is None


def test_errors_sorted_by_code_stable_within_group(mini_design) -> None:
    """退回单顺序 = 代码升序，组内保持收集顺序（同类错误相邻，编剧好批量修）。"""
    blocks = MINI_GOOD_REPLY.split("\n\n")
    # 去掉两个块（E1×2，骨架序 = line_a_b1 在 end_a 前）+ 加一个未知块（E2）
    reply = (
        "\n\n".join(
            b
            for b in blocks
            if "[node: line_a_b1]" not in b and "[node: end_a]" not in b
        )
        + "\n\n[node: extra]\nnarration: 未知块。\n"
    )
    result = ingest_reply(mini_design, reply)
    assert _codes(result) == ["E1", "E1", "E2"]
    assert [e.node_id for e in result.errors] == ["line_a_b1", "end_a", "extra"]
