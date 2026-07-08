"""T-3P-3 验收管线单测 + 落地 + 格式段↔解析器对偶.

覆盖（任务规格 §D 9-11）：
  - 验收 pass 全绿（lucy fixture 合并产物）；
  - 三层 fail（schema / graph / 一致性闭合各构造一路）；
  - 机械 fail（human 豁免 monotonic vs 非豁免 EFFECT_OP_INVALID 各一）；
  - AP flag 记录不拦截（pass 仍 True）；
  - 本体解析 issue 单列为 note、不计入 blocking；
  - `--land` 落地 + version sidecar（method=writer_ingest）；验收 fail 不落地；
  - **格式段↔解析器对偶**：P-A（render_pack）渲染的输出格式段模板块，填满后能被
    P-B（ingest）parser 成功解析 + 对齐 + 合并（P1 并行期两任务无法互测，落本任务）。
"""
from __future__ import annotations

import json
import re

import pytest

from generator.promptpack.acceptance import (
    AcceptanceReport,
    acceptance_paths_for,
    acceptance_report_dict,
    render_acceptance_md,
    run_acceptance,
)
from generator.promptpack.format_spec import EXIT_OK, EXIT_REJECTED
from generator.promptpack.ingest import ingest_reply, main
from generator.promptpack.io import load_design_artifact
from generator.promptpack.render_pack import render_pack
from generator.promptpack.tests.helpers import (
    FIXTURE_DESIGN,
    build_placeholder_reply,
    make_mini_design_wrapper,
    write_mini_design,
)

lucy_fixture = pytest.mark.skipif(
    not FIXTURE_DESIGN.exists(), reason="T-3P-0 augmented lucy fixture not present"
)

# FIXTURE_DESIGN = .../multipass_structure/2026-06-29_t3p_fixture/lucy/design.json
# parents[2] = multipass_structure ；specs/lucy.json 与实验目录同级
LUCY_SPEC = FIXTURE_DESIGN.parents[2] / "specs" / "lucy.json"
LUCY_REPLY_GOOD = (
    FIXTURE_DESIGN.parents[2] / "2026-07-08_t3p2_ingest_demo" / "reply_good.md"
)


def _mini_graph() -> dict:
    """合法 mini 合并产物（走 io loader + ingest_reply，与真实产物同路径）。"""
    design = load_design_artifact_from_wrapper(make_mini_design_wrapper())
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    return result.graph


def load_design_artifact_from_wrapper(wrapper: dict) -> dict:
    """把内存 wrapper 落临时盘再走 loader——保持"只经 io.load_design_artifact 读"契约。"""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "design.json"
        p.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
        return load_design_artifact(p)


# ---------------------------------------------------------------------------
# pass 全绿
# ---------------------------------------------------------------------------


def test_acceptance_pass_on_clean_merge() -> None:
    graph = _mini_graph()
    report = run_acceptance(graph)
    assert report.passed
    assert report.blocking_error_count == 0
    assert report.schema_errors == []
    assert report.graph_errors == []
    assert report.consistency_closure_errors == []
    assert report.mechanical_errors == []
    # mini refs (char_npc / scene_mini) 不在已加载本体 → 本体解析 note，但不拦
    assert report.consistency_ontology_notes  # 有 note
    assert "验收通过" in report.one_line_guidance()


@lucy_fixture
def test_acceptance_pass_on_lucy_merge() -> None:
    design = load_design_artifact(FIXTURE_DESIGN)
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok
    report = run_acceptance(result.graph)
    assert report.passed
    assert report.blocking_error_count == 0
    # 全部 cons issue 都是本体解析（与 test_reassemble_lucy_adr040 同口径）
    assert report.consistency_closure_errors == []
    assert report.consistency_ontology_notes


# ---------------------------------------------------------------------------
# 三层 fail
# ---------------------------------------------------------------------------


def test_acceptance_fail_schema_layer() -> None:
    graph = _mini_graph()
    # 删掉一个节点的必填 narration → schema 层报错
    some_nid = next(iter(graph["nodes"]))
    del graph["nodes"][some_nid]["narration"]
    report = run_acceptance(graph)
    assert not report.passed
    assert report.schema_errors  # schema 层抓到
    assert report.blocking_error_count >= 1


def test_acceptance_fail_graph_layer() -> None:
    graph = _mini_graph()
    # 把某选项的 target 指向不存在的节点 → 图论悬空
    for node in graph["nodes"].values():
        if node.get("options"):
            node["options"][0]["target_node_id"] = "node_that_does_not_exist"
            break
    report = run_acceptance(graph)
    assert not report.passed
    assert report.graph_errors
    assert report.blocking_error_count >= 1


def test_acceptance_fail_consistency_closure() -> None:
    """一致性闭合违规（dialogue[].speaker_ref 越出 character_refs）= 硬拦。"""
    graph = _mini_graph()
    entry = graph["entry_node_id"]
    graph["nodes"][entry]["dialogue"].append(
        {"speaker_ref": "char_undeclared", "line": "我不在花名册里。"}
    )
    report = run_acceptance(graph)
    assert not report.passed
    assert report.consistency_closure_errors
    assert any(
        "not declared in character_refs" in i.message
        for i in report.consistency_closure_errors
    )
    # 本体解析 note 与闭合违规分开——闭合违规里不该混进本体解析
    assert all(
        "does not resolve in ontology" not in i.message
        for i in report.consistency_closure_errors
    )


# ---------------------------------------------------------------------------
# 机械 fail：human 豁免 monotonic vs 非豁免 EFFECT_OP_INVALID
# ---------------------------------------------------------------------------


def test_acceptance_mechanical_human_exempts_monotonic() -> None:
    """monotonic 违规在 human 路径豁免——不应进 blocking（对比 llm 路径会报）。

    构造一个对同一 relationship 路径先 inc 再 dec 的选项（ADR-034 D11 monotonic
    违规）；human 路径豁免，验收仍 pass（该场景其余干净）。
    """
    graph = _mini_graph()
    # 找一个有选项的节点，注入 monotonic 违规 effects（human 应豁免）
    injected = False
    for node in graph["nodes"].values():
        if node.get("options"):
            node["options"][0]["effects"] = [
                {"op": "inc", "path": "relationship.char_npc.trust", "value": 1},
                {"op": "dec", "path": "relationship.char_npc.trust", "value": 1},
            ]
            injected = True
            break
    assert injected
    report = run_acceptance(graph)
    # human 豁免 monotonic → 机械层无 error → 仍 pass（其余层干净）
    assert report.mechanical_errors == [], [
        (r.node_id, r.code) for r in report.mechanical_errors
    ]
    assert report.passed


def test_acceptance_mechanical_non_exempt_effect_op_invalid() -> None:
    """非豁免机械违规（EFFECT_OP_INVALID）在 human 路径照样硬拦。"""
    graph = _mini_graph()
    for node in graph["nodes"].values():
        if node.get("options"):
            node["options"][0].setdefault("effects", []).append(
                {"op": "not_a_real_op", "path": "flag.some_flag", "value": True}
            )
            break
    report = run_acceptance(graph)
    assert not report.passed
    assert any(r.code == "EFFECT_OP_INVALID" for r in report.mechanical_errors)


# ---------------------------------------------------------------------------
# AP flag 记录不拦截
# ---------------------------------------------------------------------------


def test_acceptance_ap_flag_recorded_not_blocking() -> None:
    """AP-8（选项第三人称）flag 记录进报告，但不影响 passed。"""
    graph = _mini_graph()
    # AP-8：选项文本以第三人称意图动词"先"开头（程序化可检；见 _AP8_THIRD_PERSON_VERBS）
    for node in graph["nodes"].values():
        if node.get("options"):
            node["options"][0]["text"] = "先追问她那个人在哪。"
            break
    report = run_acceptance(graph)
    assert report.ap_flags  # 记录到了
    assert any(r.ap_id == "AP-8" for r in report.ap_flags)
    # AP 不拦：其余层干净 → 仍 pass
    assert report.passed
    assert report.blocking_error_count == 0


# ---------------------------------------------------------------------------
# 本体解析单列、报告渲染
# ---------------------------------------------------------------------------


def test_ontology_notes_not_counted_blocking() -> None:
    graph = _mini_graph()
    report = run_acceptance(graph)
    # mini refs 不解析 → 有 note，但 blocking=0、passed=True
    assert report.consistency_ontology_notes
    assert report.blocking_error_count == 0
    assert report.passed


def test_report_dict_and_md_render() -> None:
    graph = _mini_graph()
    report = run_acceptance(graph)
    d = acceptance_report_dict(report)
    assert d["passed"] is True
    assert d["graph_id"] == "mini_scene"
    assert "consistency_ontology_notes" in d
    md = render_acceptance_md(report)
    assert "回流验收报告" in md
    assert "PASS" in md
    assert "本体解析待挂" in md


# ---------------------------------------------------------------------------
# 落地（--land）+ version sidecar；验收 fail 不落地
# ---------------------------------------------------------------------------


@lucy_fixture
def test_land_writes_scene_and_version_sidecar(tmp_path) -> None:
    land_dir = tmp_path / "landed"
    if not LUCY_REPLY_GOOD.exists():
        pytest.skip("reply_good.md demo not present")
    rc = main(
        [
            str(FIXTURE_DESIGN),
            str(LUCY_REPLY_GOOD),
            "--land",
            str(land_dir),
        ]
    )
    assert rc == EXIT_OK
    scene = land_dir / "scene.json"
    assert scene.exists()
    sidecar = land_dir / "scene.version.json"
    assert sidecar.exists()
    meta = json.loads(sidecar.read_text(encoding="utf-8"))
    assert meta["generation_method"] == "writer_ingest"
    assert meta["version"] == 1
    # 验收报告成对落在 scene 旁
    md, js = acceptance_paths_for(scene)
    assert md.exists() and js.exists()
    assert json.loads(js.read_text(encoding="utf-8"))["passed"] is True


def test_land_refused_when_acceptance_fails(tmp_path, monkeypatch) -> None:
    """验收 fail → 不落地、不记版本、退出码 EXIT_REJECTED（合并本身成功）。

    路线 A 下合法回流不会产结构坏图，故用 monkeypatch 让验收对合并产物返回 fail
    （技术负路径：模拟"管线 bug / 被手改的 scene.json"这一验收闸真正防的东西）。
    """
    design_path = write_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    design = load_design_artifact(design_path)
    reply_path.write_text(build_placeholder_reply(design), encoding="utf-8")

    land_dir = tmp_path / "landed"

    fail_report = AcceptanceReport(graph_id="mini_scene", passed=False)
    # 造一个假的 schema error 让 blocking_error_count>0、guidance 走 fail 分支
    from validator.report import Issue

    fail_report.schema_errors = [Issue(level="schema", location="x", message="forced fail")]
    monkeypatch.setattr(
        "generator.promptpack.ingest.run_acceptance", lambda graph, **kw: fail_report
    )

    rc = main([str(design_path), str(reply_path), "--land", str(land_dir)])
    assert rc == EXIT_REJECTED
    # 未记版本 sidecar（不落地）
    assert not (land_dir / "scene.version.json").exists()
    # 且**不留**无版本 sidecar 的 scene.json 在落地目录（防"文件在=已落地"误读）
    assert not (land_dir / "scene.json").exists()
    # 验收报告 sidecar 留下供作者排查 fail 原因
    md, js = acceptance_paths_for(land_dir / "scene.json")
    assert md.exists() and js.exists()


# ---------------------------------------------------------------------------
# 格式段↔解析器对偶（D.10）
# ---------------------------------------------------------------------------


_FENCE_RE = re.compile(r"```\n(.*?)\n```", re.DOTALL)


def _extract_template_blocks(pack_md: str) -> str:
    """从 pack 的「六、输出格式」段抽出**填空模板**那个 fence（含逐块 [node:] 模板）。

    最后一个 fenced block 是逐节点填空模板（render_pack._render_format_section 结构）；
    取它并把每个 `<…>` 占位符替换成合法 filler（避开 AP-7/8/10 + 空文本 E7）。
    """
    fences = _FENCE_RE.findall(pack_md)
    assert fences, "pack 里没有 fenced code block"
    # 逐块模板 fence = 含多个 [node: ...] 行的那个（语法示例 fence 只含一个 <node_id>）
    template_fence = max(fences, key=lambda f: f.count("[node:"))
    assert template_fence.count("[node:") >= 2, "没找到逐块填空模板 fence"
    return template_fence


def _fill_placeholders(template: str) -> str:
    """把模板里的 `<…>` 占位符逐行填成合法 filler 正文（避开 AP 程序化反模式 + E7 空文本）。"""
    out_lines = []
    for line in template.splitlines():
        if "<…>" in line:
            # narration / dialogue / continue / options 各自填一句中性 filler
            line = line.replace("<…>", "灯光落在吧台边，杯子摆成一排。")
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"


@lucy_fixture
def test_format_section_templates_parse_back_through_ingest() -> None:
    """P-A 渲染的输出格式段模板块，填满后能被 P-B parser 解析 + 对齐 + 合并。

    这是格式契约的机器闭环：P-A 生成什么样的填空模板，P-B 就必须能解析什么——
    两任务 P1 并行期无法互测，落本任务。
    """
    design = load_design_artifact(FIXTURE_DESIGN)
    spec = json.loads(LUCY_SPEC.read_text(encoding="utf-8"))["spec"]
    pack_md = render_pack(design, spec)

    template = _extract_template_blocks(pack_md)
    reply = _fill_placeholders(template)

    result = ingest_reply(design, reply)
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    # 合并出的图节点数 = 期望 35（choice/beat/end 全覆盖）
    assert len(result.graph["nodes"]) == 35
    # 且填出来的图能过验收（模板 filler 结构上干净）
    report = run_acceptance(result.graph)
    assert report.blocking_error_count == 0


def test_mini_format_section_templates_parse_back(tmp_path) -> None:
    """mini design 上的格式段↔解析器对偶（不依赖 lucy fixture 存在，恒跑）。"""
    # render_pack 要求完整 contract（player_goal/npc_goal/npc_fear）——mini helper
    # 的 contract={} 只够 loader/ingest 用；本对偶测试补一个合法 contract 再渲染。
    wrapper = make_mini_design_wrapper()
    wrapper["design"]["contract"] = {
        "player_goal": "从 NPC 口中问出线索。",
        "npc_goal": "在不被偷听的前提下透露方位。",
        "npc_fear": "怕角落的人听见。",
        "forbidden": ["不得在吧台上直呼关键词。"],
    }
    p = tmp_path / "design_with_contract.json"
    p.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
    design = load_design_artifact(p)
    spec = {"background": "测试背景。", "character_state": "NPC 在擦杯子。"}
    pack_md = render_pack(design, spec)
    template = _extract_template_blocks(pack_md)
    reply = _fill_placeholders(template)
    result = ingest_reply(design, reply)
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    assert len(result.graph["nodes"]) == 5  # mini: start + 2 beats + 2 ends
