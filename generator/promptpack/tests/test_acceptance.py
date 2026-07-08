"""T-3P-3 验收管线单测 + 落地 + 格式段↔解析器对偶.

pass/fail 口径（作者 2026-07-09 拍板 Option 1；ADR-006）：**validator 三层
（schema/graph/cons）全部 issue 硬拦 + 机械预检 error 硬拦；只有 AP flag 记录不拦截**。
本体解析（does not resolve in ontology）与闭合违规同为硬拦。

覆盖（任务规格 §D 9-11 + C 阶段口径修订）：
  - 验收 PASS 全绿：用 refs 能在**已加载 waystation 本体**解析的最小图（char_vellin
    等），证明三层全过 + 机械干净时 PASS + --land 写入 + version sidecar；
  - 验收 FAIL：三层各构造一路（schema / graph / 一致性闭合 / **本体解析**）；
  - 机械 fail（human 豁免 monotonic vs 非豁免 EFFECT_OP_INVALID 各一）；
  - AP flag 记录不拦截（其余全过时 pass 仍 True）；
  - lucy 正例：验收 **FAIL、不落地**（引用未发布本体，守门在工作）；播放另测（直接喂合并产物）；
  - `--land`：PASS 才写 + version sidecar；验收 fail 不落地且不留 scene.json；
  - **格式段↔解析器对偶**：P-A（render_pack）渲染的输出格式段模板块，填满后能被
    P-B（ingest）parser 成功解析 + 对齐 + 合并（P1 并行期两任务无法互测，落本任务）。
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

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
    make_resolvable_mini_design_wrapper,
    write_mini_design,
    write_resolvable_mini_design,
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


def load_design_artifact_from_wrapper(wrapper: dict) -> dict:
    """把内存 wrapper 落临时盘再走 loader——保持"只经 io.load_design_artifact 读"契约。"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "design.json"
        p.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
        return load_design_artifact(p)


def _mini_graph() -> dict:
    """mini 合并产物（run_config refs = char_npc / scene_mini，**不在已加载本体**）。

    结构层干净，但本体解析会硬 fail——用于本体解析类 fail 测试（C 阶段口径）。
    """
    design = load_design_artifact_from_wrapper(make_mini_design_wrapper())
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    return result.graph


def _resolvable_mini_graph() -> dict:
    """本体可解析的 mini 合并产物（refs = waystation id → 验收三层全过 PASS）。"""
    design = load_design_artifact_from_wrapper(make_resolvable_mini_design_wrapper())
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok, [(e.code, e.node_id, e.actual) for e in result.errors]
    return result.graph


# ---------------------------------------------------------------------------
# PASS 全绿（refs 在已加载本体解析 → 三层全过）
# ---------------------------------------------------------------------------


def test_acceptance_pass_on_resolvable_merge() -> None:
    graph = _resolvable_mini_graph()
    report = run_acceptance(graph)
    assert report.passed, acceptance_report_dict(report)
    assert report.blocking_error_count == 0
    assert report.schema_errors == []
    assert report.graph_errors == []
    assert report.consistency_errors == []  # 本体全解析、闭合无违规
    assert report.mechanical_errors == []
    assert "验收通过" in report.one_line_guidance()


def test_land_pass_resolvable_writes_scene_and_version_sidecar(tmp_path) -> None:
    """PASS happy-path 全绿：本体可解析场景 → 验收 PASS → --land 写入 + version sidecar。"""
    design_path = write_resolvable_mini_design(tmp_path)
    design = load_design_artifact(design_path)
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(build_placeholder_reply(design), encoding="utf-8")

    land_dir = tmp_path / "landed"
    rc = main([str(design_path), str(reply_path), "--land", str(land_dir)])
    assert rc == EXIT_OK
    scene = land_dir / "scene.json"
    assert scene.exists()
    sidecar = land_dir / "scene.version.json"
    assert sidecar.exists()
    meta = json.loads(sidecar.read_text(encoding="utf-8"))
    assert meta["generation_method"] == "writer_ingest"
    assert meta["version"] == 1
    md, js = acceptance_paths_for(scene)
    assert md.exists() and js.exists()
    assert json.loads(js.read_text(encoding="utf-8"))["passed"] is True


# ---------------------------------------------------------------------------
# 三层 fail（schema / graph / 一致性闭合 / 本体解析）
# ---------------------------------------------------------------------------


def test_acceptance_fail_schema_layer() -> None:
    graph = _resolvable_mini_graph()
    # 删掉一个节点的必填 narration → schema 层报错
    some_nid = next(iter(graph["nodes"]))
    del graph["nodes"][some_nid]["narration"]
    report = run_acceptance(graph)
    assert not report.passed
    assert report.schema_errors  # schema 层抓到
    assert report.blocking_error_count >= 1


def test_acceptance_fail_graph_layer() -> None:
    graph = _resolvable_mini_graph()
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
    graph = _resolvable_mini_graph()
    entry = graph["entry_node_id"]
    graph["nodes"][entry]["dialogue"].append(
        {"speaker_ref": "char_undeclared", "line": "我不在花名册里。"}
    )
    report = run_acceptance(graph)
    assert not report.passed
    assert report.consistency_errors
    assert any(
        "not declared in character_refs" in i.message
        for i in report.consistency_errors
    )


def test_acceptance_fail_ontology_resolution_is_blocking() -> None:
    """本体解析 issue（does not resolve in ontology）现在硬拦（C 阶段 Option 1；ADR-006）。

    mini 图 refs = char_npc / scene_mini，不在已加载 waystation 本体 → cons 层报本体
    解析错误 → 验收 FAIL、blocking_error_count>0。这是本体一致性守门。
    """
    graph = _mini_graph()  # 不可解析 refs
    report = run_acceptance(graph)
    assert not report.passed
    assert report.consistency_errors
    assert any(
        "does not resolve in ontology" in i.message for i in report.consistency_errors
    )
    # 本体解析计入 blocking（不再降级为 note）
    assert report.blocking_error_count == len(report.consistency_errors)
    assert report.blocking_error_count > 0


# ---------------------------------------------------------------------------
# 机械 fail：human 豁免 monotonic vs 非豁免 EFFECT_OP_INVALID
# ---------------------------------------------------------------------------


def test_acceptance_mechanical_human_exempts_monotonic() -> None:
    """monotonic 违规在 human 路径豁免——不进 blocking（对比 llm 路径会报）。

    构造一个对同一 relationship 路径先 inc 再 dec 的选项（ADR-034 D11 monotonic
    违规）；human 路径豁免，机械层无 error。用本体可解析图，避免本体解析噪音干扰
    passed 断言（本 case 只验机械层豁免）。
    """
    graph = _resolvable_mini_graph()
    injected = False
    for node in graph["nodes"].values():
        if node.get("options"):
            node["options"][0]["effects"] = [
                {"op": "inc", "path": "relationship.char_vellin.trust", "value": 1},
                {"op": "dec", "path": "relationship.char_vellin.trust", "value": 1},
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
    graph = _resolvable_mini_graph()
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
# AP flag 记录不拦截（唯一的非阻断层）
# ---------------------------------------------------------------------------


def test_acceptance_ap_flag_recorded_not_blocking() -> None:
    """AP-8（选项第三人称）flag 记录进报告，但不影响 passed。"""
    graph = _resolvable_mini_graph()
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
# 报告渲染
# ---------------------------------------------------------------------------


def test_report_dict_and_md_render_pass() -> None:
    graph = _resolvable_mini_graph()
    report = run_acceptance(graph)
    d = acceptance_report_dict(report)
    assert d["passed"] is True
    assert d["graph_id"] == "mini_resolvable_scene"
    assert "consistency_errors" in d
    assert "consistency_ontology_notes" not in d  # 降级字段已取消
    md = render_acceptance_md(report)
    assert "回流验收报告" in md
    assert "PASS" in md


def test_report_dict_and_md_render_fail_ontology() -> None:
    graph = _mini_graph()  # 本体不可解析 → FAIL
    report = run_acceptance(graph)
    d = acceptance_report_dict(report)
    assert d["passed"] is False
    assert d["blocking_error_count"] > 0
    md = render_acceptance_md(report)
    assert "FAIL" in md
    assert "本体引用" in md or "本体" in report.one_line_guidance()


# ---------------------------------------------------------------------------
# lucy 正例：验收 FAIL、不落地（守门行为）；播放另测
# ---------------------------------------------------------------------------


@lucy_fixture
def test_lucy_merge_fails_acceptance_unpublished_ontology() -> None:
    """lucy 合并产物结构有效，但引用未发布本体 → 验收 **FAIL**（本体守门 ADR-006）。"""
    design = load_design_artifact(FIXTURE_DESIGN)
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok  # 合并本身成功（结构有效）
    report = run_acceptance(result.graph)
    assert not report.passed  # 验收 FAIL
    assert report.consistency_errors
    # lucy 的 cons issue 全是本体解析（char_lucy / scene_hibo_roadhouse 未发布）
    assert all(
        "does not resolve in ontology" in i.message for i in report.consistency_errors
    ), [i.message for i in report.consistency_errors]
    assert report.blocking_error_count > 0


@lucy_fixture
def test_lucy_land_refused_acceptance_fail(tmp_path) -> None:
    """lucy 正例经 CLI --land：验收 FAIL → 不落地、不留 scene.json、不记版本。"""
    if not LUCY_REPLY_GOOD.exists():
        pytest.skip("reply_good.md demo not present")
    land_dir = tmp_path / "landed"
    rc = main([str(FIXTURE_DESIGN), str(LUCY_REPLY_GOOD), "--land", str(land_dir)])
    assert rc == EXIT_REJECTED  # 验收 fail 归 EXIT_REJECTED
    assert not (land_dir / "scene.json").exists()  # 不留无版本 scene
    assert not (land_dir / "scene.version.json").exists()  # 不记版本
    # 验收报告 sidecar 留下供排查（显示 FAIL 是正确产物）
    md, js = acceptance_paths_for(land_dir / "scene.json")
    assert md.exists() and js.exists()
    assert json.loads(js.read_text(encoding="utf-8"))["passed"] is False


@lucy_fixture
def test_lucy_merge_product_plays_through_engine(tmp_path) -> None:
    """播放链路演示：直接把 P-B 合并产物喂 engine.play 能玩通到结局.

    如实注明：播放**不经验收闸**、engine 对未解析 ref 降级显示（原 ref）；落地才经闸。
    此测证明"合并产物结构可玩"，与"验收是否放行落地"正交。
    """
    from engine.player import play

    design = load_design_artifact(FIXTURE_DESIGN)
    result = ingest_reply(design, build_placeholder_reply(design))
    assert result.ok
    scene_path = tmp_path / "scene.json"
    scene_path.write_text(
        json.dumps(result.graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 驱动一条到结局的路径：opening 选 4（pressure 链）→ 每拍选 1 → end
    import io

    stdin = io.StringIO("4\n1\n1\n1\n1\n")
    stdout = io.StringIO()
    play(str(scene_path), stdin=stdin, stdout=stdout)
    out = stdout.getvalue()
    assert "—— 结局 ——" in out  # 玩到结局
    # engine 对未解析 ref 降级显示原 ref（不 crash）
    assert "char_lucy" in out


# ---------------------------------------------------------------------------
# 落地（--land）：验收 fail 不落地（技术负路径 monkeypatch）
# ---------------------------------------------------------------------------


def test_land_refused_when_acceptance_fails(tmp_path, monkeypatch) -> None:
    """验收 fail → 不落地、不记版本、退出码 EXIT_REJECTED（合并本身成功）。

    用 monkeypatch 让验收对合并产物返回 fail（技术负路径：模拟"管线 bug / 被手改的
    scene.json"这一验收闸真正防的东西，与本体解析 fail 路径互补）。
    """
    design_path = write_mini_design(tmp_path)
    reply_path = tmp_path / "reply.md"
    design = load_design_artifact(design_path)
    reply_path.write_text(build_placeholder_reply(design), encoding="utf-8")

    land_dir = tmp_path / "landed"

    fail_report = AcceptanceReport(graph_id="mini_scene", passed=False)
    from validator.report import Issue

    fail_report.schema_errors = [Issue(level="schema", location="x", message="forced fail")]
    monkeypatch.setattr(
        "generator.promptpack.ingest.run_acceptance", lambda graph, **kw: fail_report
    )

    rc = main([str(design_path), str(reply_path), "--land", str(land_dir)])
    assert rc == EXIT_REJECTED
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
            line = line.replace("<…>", "灯光落在吧台边，杯子摆成一排。")
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"


@lucy_fixture
def test_format_section_templates_parse_back_through_ingest() -> None:
    """P-A 渲染的输出格式段模板块，填满后能被 P-B parser 解析 + 对齐 + 合并。

    这是格式契约的机器闭环：P-A 生成什么样的填空模板，P-B 就必须能解析什么——
    两任务 P1 并行期无法互测，落本任务。**只验解析↔合并闭环**，不验本体解析
    （lucy refs 未发布 → 验收会 FAIL，那是本体守门的正交议题）。
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
    # 结构 / 图 / 机械层干净（本体解析除外——lucy refs 未发布，属正交议题）
    report = run_acceptance(result.graph)
    assert report.schema_errors == []
    assert report.graph_errors == []
    assert report.mechanical_errors == []


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
