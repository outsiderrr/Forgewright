"""T-3P-2 确定性合并 + golden + 对偶三层校验 + CLI 冒烟.

golden 基于 T-3P-0 augmented lucy fixture（占位文本——只验格式 / 对齐 / 机械
合并正确性，不验文学质量）；对偶测试照 test_reassemble_lucy_adr040.py 模板：
合并产物过 schema / graph / 机械（source=human）/ AP / consistency 各层。
确定性 = 同 reply + 同 design → 逐字节相同；块顺序无关。
"""
from __future__ import annotations

import json

import pytest

from generator.promptpack.format_spec import EXIT_OK, EXIT_REJECTED, EXIT_USAGE
from generator.promptpack.ingest import ingest_reply, main
from generator.promptpack.io import load_design_artifact
from generator.promptpack.tests.helpers import (
    FIXTURE_DESIGN,
    MINI_GOOD_REPLY,
    build_placeholder_reply,
    write_mini_design,
    write_resolvable_mini_design,
)
from validator import consistency_check, graph_check, schema_check
from validator.anti_pattern_detector import detect_anti_patterns
from validator.dialogue_validator import validate_graph_mechanical

lucy_fixture = pytest.mark.skipif(
    not FIXTURE_DESIGN.exists(), reason="T-3P-0 augmented lucy fixture not present"
)


@pytest.fixture
def mini_design(tmp_path):
    return load_design_artifact(write_mini_design(tmp_path))


def _lucy_merge():
    design = load_design_artifact(FIXTURE_DESIGN)
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    return result.graph


# ---------------------------------------------------------------------------
# golden：augmented lucy fixture × 占位回流 → 全图机械正确
# ---------------------------------------------------------------------------


@lucy_fixture
def test_golden_lucy_graph_shape() -> None:
    graph = _lucy_merge()
    # 图级字段全部来自 design.run_config（不另收配置参数）
    assert graph["schema_version"] == "0.1.1"  # ADR-040：不 bump，兼容路径
    assert graph["graph_id"] == "lucy_roadhouse_multipass"
    assert graph["scene_anchor"] == "scene_hibo_roadhouse"
    assert graph["character_refs"] == ["char_lucy"]
    # beats 链入口映射：entry = opening（choice 原名）；choice 出边指向 {pid}_b1
    assert graph["entry_node_id"] == "opening"
    # 节点数 = 2 choice + (8+6+6+4+4) beats + 5 end = 35
    assert len(graph["nodes"]) == 35
    opening = graph["nodes"]["opening"]
    assert [o["target_node_id"] for o in opening["options"]] == [
        "soft_private_line_b1",
        "money_line_b1",
        "watch_corner",
        "pressure_line_b1",
    ]
    assert [o["option_id"] for o in opening["options"]] == [
        f"opt_opening_{i}" for i in range(1, 5)
    ]


@lucy_fixture
def test_golden_lucy_beats_chain_wiring() -> None:
    """beats 链 {pid}_b{i} 串接：拍内 continue 指向下一拍，末拍指向 plan.next。"""
    graph = _lucy_merge()
    for i in range(1, 8):
        node = graph["nodes"][f"soft_private_line_b{i}"]
        opt = node["options"][0]
        assert opt["option_id"] == f"opt_soft_private_line_b{i}_continue"
        assert opt["target_node_id"] == f"soft_private_line_b{i + 1}"
    last = graph["nodes"]["soft_private_line_b8"]
    assert last["options"][0]["target_node_id"] == "end_soft_leave"
    # 机械字段 = assemble 同款（mk_option 公开别名）
    assert last["options"][0]["condition"] is None
    assert last["options"][0]["effects"] == []
    assert last["options"][0]["unavailable_behavior"] == "hide"


@lucy_fixture
def test_golden_lucy_adr040_invariants_and_human_trace() -> None:
    graph = _lucy_merge()
    for nid, node in graph["nodes"].items():
        # ADR-040：节点 speaker_ref=null；dialogue[] 结构化、图级单说话人
        assert node["speaker_ref"] is None, nid
        for entry in node["dialogue"]:
            assert set(entry) == {"speaker_ref", "line"}
            assert entry["speaker_ref"] == "char_lucy"
            assert entry["line"]
        # node + option 级 generation_trace.source="human"（正文来源审计）
        assert node["generation_trace"] == {"source": "human"}, nid
        for opt in node["options"]:
            assert opt["generation_trace"] == {"source": "human"}
        # end 节点无选项；dialogue 节点至少 1 选项
        if node["type"] == "end":
            assert node["options"] == []
        else:
            assert node["options"]


# ---------------------------------------------------------------------------
# 对偶测试（照 test_reassemble_lucy_adr040.py 模板）：合并产物过三层校验
# ---------------------------------------------------------------------------


@lucy_fixture
def test_lucy_merge_passes_validator_layers_cleanly() -> None:
    graph = _lucy_merge()

    # schema + graph + 机械预检（source=human，T-3P-3 验收管线同款口径）+ AP：0 问题
    assert schema_check.check(graph) == []
    assert graph_check.check(graph)[0] == []
    mech_errors = {
        nid: r
        for nid, r in validate_graph_mechanical(
            graph, generation_source="human"
        ).items()
        if r.has_error
    }
    assert mech_errors == {}
    ap = {
        nid: detect_anti_patterns(n)
        for nid, n in graph["nodes"].items()
        if detect_anti_patterns(n)
    }
    assert ap == {}

    # consistency：无任何 speaker_ref / dialogue 闭合违规（char_lucy ⊆ character_refs）。
    # 剩余 cons 全是本体解析（露西 refs 不在已加载本体内，与合并器正交——
    # 与 test_reassemble_lucy_adr040 同口径）。
    cons = consistency_check.check(graph)
    closure_violations = [
        i for i in cons if "speaker_ref" in i.message or "dialogue" in i.location
    ]
    assert closure_violations == []
    assert all("does not resolve in ontology" in i.message for i in cons), [
        i.message for i in cons
    ]


# ---------------------------------------------------------------------------
# 合并细节：多行 narration / 引号归一（normalize_line 公开别名）
# ---------------------------------------------------------------------------


def test_merge_multiline_narration_and_quote_normalization(mini_design) -> None:
    reply = MINI_GOOD_REPLY.replace(
        "narration: 门口的灯亮着。柜台后没有人。",
        "narration: 门口的灯亮着。\n\n柜台后没有人。",
    ).replace("  - 想问什么就快点问。", "  - 「想问什么就快点问。」")
    result = ingest_reply(mini_design, reply)
    assert result.ok
    start = result.graph["nodes"]["start"]
    # 多行值：行间保留段落空行（\n\n）
    assert start["narration"] == "门口的灯亮着。\n\n柜台后没有人。"
    # 整句包裹引号归一为裸正文（ADR-040 dialogue[].line 体例）
    assert start["dialogue"] == [
        {"speaker_ref": "char_npc", "line": "想问什么就快点问。"}
    ]


def test_merge_mini_targets_and_types(mini_design) -> None:
    result = ingest_reply(mini_design, MINI_GOOD_REPLY)
    graph = result.graph
    assert graph["entry_node_id"] == "start"
    assert set(graph["nodes"]) == {"start", "line_a_b1", "line_a_b2", "end_a", "end_quick"}
    start = graph["nodes"]["start"]
    assert [o["target_node_id"] for o in start["options"]] == ["line_a_b1", "end_quick"]
    assert [o["text"] for o in start["options"]] == [
        "我想打听一个人。",
        "我什么都不问，先走了。",
    ]
    assert graph["nodes"]["line_a_b1"]["options"][0]["target_node_id"] == "line_a_b2"
    assert graph["nodes"]["line_a_b2"]["options"][0]["target_node_id"] == "end_a"
    assert graph["nodes"]["end_a"]["type"] == "end"
    assert graph["nodes"]["end_quick"]["type"] == "end"


# ---------------------------------------------------------------------------
# 确定性：同输入逐字节相同；回流块顺序无关
# ---------------------------------------------------------------------------


def _dump(graph: dict) -> str:
    return json.dumps(graph, ensure_ascii=False, indent=2)


@lucy_fixture
def test_deterministic_same_input_byte_identical() -> None:
    design_a = load_design_artifact(FIXTURE_DESIGN)
    design_b = load_design_artifact(FIXTURE_DESIGN)
    reply = build_placeholder_reply(design_a)
    out_a = _dump(ingest_reply(design_a, reply).graph)
    out_b = _dump(ingest_reply(design_b, reply).graph)
    assert out_a == out_b


def test_deterministic_reply_block_order_independent(mini_design) -> None:
    """块与块顺序随意（格式契约明示）→ 合并按 topology 序，输出与块序无关。"""
    blocks = [b for b in MINI_GOOD_REPLY.split("\n\n") if b.strip()]
    shuffled = "\n\n".join(reversed(blocks)) + "\n"
    out_a = _dump(ingest_reply(mini_design, MINI_GOOD_REPLY).graph)
    out_b = _dump(ingest_reply(mini_design, shuffled).graph)
    assert out_a == out_b


# ---------------------------------------------------------------------------
# CLI 冒烟（独立模块入口 + 退出码三态 + 退回单落盘）
# ---------------------------------------------------------------------------


def test_cli_good_reply_exit_0_writes_scene(tmp_path, capsys) -> None:
    # T-3P-3：合并成功后 CLI 会跑验收闸；用**本体可解析**的 design 让验收 PASS → EXIT_OK
    # （mini design 的 char_npc/scene_mini 不在已加载本体，验收会 FAIL — 那是本体守门）。
    design_path = write_resolvable_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    out_path = tmp_path / "out" / "scene.json"
    assert main([str(design_path), str(reply_path), "--out", str(out_path)]) == EXIT_OK
    graph = json.loads(out_path.read_text(encoding="utf-8"))
    assert graph["graph_id"] == "mini_resolvable_scene"
    assert not (tmp_path / "reply.reject.md").exists()
    assert "[合并成功]" in capsys.readouterr().out


def test_cli_default_out_is_reply_scene_json(tmp_path) -> None:
    design_path = write_resolvable_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    assert main([str(design_path), str(reply_path)]) == EXIT_OK
    assert (tmp_path / "reply.scene.json").exists()


def test_cli_bad_reply_exit_1_writes_reject_and_no_scene(tmp_path, capsys) -> None:
    design_path = write_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    bad = MINI_GOOD_REPLY.replace("  2: 我什么都不问，先走了。", "  3: 我跳号了。")
    reply_path.write_text(bad, encoding="utf-8")
    out_path = tmp_path / "scene.json"
    assert (
        main([str(design_path), str(reply_path), "--out", str(out_path)])
        == EXIT_REJECTED
    )
    assert not out_path.exists()  # 任一 E → 不产 scene.json
    reject = (tmp_path / "reply.reject.md").read_text(encoding="utf-8")
    assert "# 回流退回单：mini_scene（1 处需修改）" in reject
    assert "[E4 option_count_mismatch]" in reject
    assert "修改指引" in reject
    err_out = capsys.readouterr().err
    assert "[拒收]" in err_out and "退回单已写入" in err_out


def test_cli_success_removes_stale_reject(tmp_path) -> None:
    """上一轮的退回单在修好重交后自动清掉（留着会误导编剧）。"""
    # 验收 PASS 才走成功分支（清 stale reject）→ 用本体可解析 design（T-3P-3 口径）
    design_path = write_resolvable_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    stale = tmp_path / "reply.reject.md"
    stale.write_text("过时退回单", encoding="utf-8")
    assert main([str(design_path), str(reply_path)]) == EXIT_OK
    assert not stale.exists()


def test_cli_bad_reply_removes_stale_scene(tmp_path) -> None:
    """B 阶段 finding：同一 --out 先成功产 scene、再坏回流拒收，旧 scene 必须被删。
    否则「任一 E → 不产 scene.json」在文件系统层被软化成「目录里仍有可用场景」。"""
    # 第一次要走成功分支（产 scene）→ 用本体可解析 design 让验收 PASS（T-3P-3 口径）
    design_path = write_resolvable_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    out_path = tmp_path / "scene.json"

    # 第一次：合法回流成功产 scene.json
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    assert main([str(design_path), str(reply_path), "--out", str(out_path)]) == EXIT_OK
    assert out_path.exists()

    # 第二次：同一路径坏回流拒收 → 旧 scene 必须被删
    bad = MINI_GOOD_REPLY.replace("  2: 我什么都不问，先走了。", "  3: 我跳号了。")
    reply_path.write_text(bad, encoding="utf-8")
    assert (
        main([str(design_path), str(reply_path), "--out", str(out_path)])
        == EXIT_REJECTED
    )
    assert not out_path.exists()  # 拒收删旧 scene，不留可被误用的成功产物
    assert (tmp_path / "reply.reject.md").exists()


def test_cli_missing_design_exit_2(tmp_path) -> None:
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    assert main([str(tmp_path / "nope.json"), str(reply_path)]) == EXIT_USAGE


def test_cli_legacy_design_exit_2(tmp_path) -> None:
    """缺 beats_plan/run_config 的 legacy design 由 loader 拒收（design 侧问题 ≠ 编剧问题）。"""
    wrapper = json.loads((write_mini_design(tmp_path)).read_text(encoding="utf-8"))
    del wrapper["design"]["run_config"]
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(MINI_GOOD_REPLY, encoding="utf-8")
    assert main([str(legacy), str(reply_path)]) == EXIT_USAGE
    assert not (tmp_path / "reply.reject.md").exists()  # 不产退回单（不是编剧的错）


def test_cli_missing_reply_exit_2(tmp_path) -> None:
    design_path = write_mini_design(tmp_path)
    assert main([str(design_path), str(tmp_path / "nope.md")]) == EXIT_USAGE
