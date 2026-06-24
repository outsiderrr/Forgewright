"""ADR-040 真实数据回归：用露西 design.json 重装配，验证 split dialogue 过校验器。

加载已落盘的露西多 pass 中间产物 design.json（其 proses / beats / ends 本就把
narration 旁白与 dialogue[] 对白行分开存），经更新后的确定性装配器 assemble_graph
重装配，断言：
  - narration = 纯旁白（无「」对白混入）、带 dialogue[] 的节点 speaker_ref=null；
  - dialogue[] 每项 {speaker_ref, line}，说话人 = 场景 NPC（char_lucy）；
  - 过 schema_check（0）+ graph_check（0）+ 机械预检（0）；
  - consistency_check 中**无任何 speaker_ref / dialogue 闭合违规**（char_lucy ⊆
    character_refs）；剩余 cons 问题仅本体解析（露西场景 refs 不在已加载本体内，
    与对白拆分正交——老的合并版 scene.json 同样如此）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.multipass.assemble import assemble_graph
from validator import consistency_check, graph_check, schema_check
from validator.anti_pattern_detector import detect_anti_patterns
from validator.dialogue_validator import validate_graph_mechanical

_LUCY = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "multipass_structure"
    / "2026-06-11_convfix"
    / "lucy"
)


def _reassemble() -> dict:
    design_doc = json.loads((_LUCY / "design.json").read_text(encoding="utf-8"))
    orig = json.loads((_LUCY / "scene.json").read_text(encoding="utf-8"))
    design = design_doc["design"]
    skeletons = design.get("skeletons", {})
    proses = design.get("proses", {})
    graph, _warnings = assemble_graph(
        graph_id=orig["graph_id"],
        scene_anchor=orig["scene_anchor"],
        speaker_ref="char_lucy",
        character_refs=orig["character_refs"],
        plan=design["topology"],
        choice_data={
            pid: {"skeleton": skeletons[pid], "prose": proses.get(pid, {})}
            for pid in skeletons
        },
        beats_data=design.get("beats", {}),
        end_data=design.get("ends", {}),
    )
    return graph


@pytest.mark.skipif(
    not (_LUCY / "design.json").exists(),
    reason="lucy experiment design.json not present",
)
def test_lucy_reassembles_into_split_dialogue() -> None:
    graph = _reassemble()
    op = graph["nodes"]["opening"]

    # narration = 纯旁白；对白不揉进 narration
    assert "「" not in op["narration"]
    assert op["narration"].startswith("希博公路酒馆")
    # 带 dialogue[] 的节点 speaker_ref=null（ADR-040 不变量）
    assert op["speaker_ref"] is None
    # dialogue[] 结构化、说话人 = char_lucy、line 为裸正文
    assert len(op["dialogue"]) == 3
    assert all(d["speaker_ref"] == "char_lucy" for d in op["dialogue"])
    assert op["dialogue"][0]["line"].startswith("声音放低")

    # 全图：每个 dialogue 条目都齐 {speaker_ref, line}、line 非空。
    # 注：体例归一只去**整句包裹**引号；源 design.json 个别行内嵌转述 tag
    # （如 "「知道了就别回头看。」露西说。"）非整句包裹，装配器忠实保留、不强拆
    # （拆内嵌 tag 属内容质量问题、确定性强拆易误伤——留给编剧/judge）。
    for node in graph["nodes"].values():
        for d in node.get("dialogue", []):
            assert set(d) == {"speaker_ref", "line"}
            assert d["line"]
    # 整句包裹引号确被去掉：opening 三句源数据含裸句 / 「」 / 弯引号，归一后均无包裹
    assert not any(op["dialogue"][i]["line"].startswith(("「", "“", '"')) for i in range(3))


@pytest.mark.skipif(
    not (_LUCY / "design.json").exists(),
    reason="lucy experiment design.json not present",
)
def test_lucy_split_passes_validator_layers_cleanly() -> None:
    graph = _reassemble()

    # schema + graph + 机械预检 + AP：对白拆分引入 0 问题
    assert schema_check.check(graph) == []
    assert graph_check.check(graph)[0] == []
    mech_errors = {
        nid: r for nid, r in validate_graph_mechanical(graph).items() if r.has_error
    }
    assert mech_errors == {}
    ap = {
        nid: detect_anti_patterns(n)
        for nid, n in graph["nodes"].items()
        if detect_anti_patterns(n)
    }
    assert ap == {}

    # consistency：无任何 speaker_ref / dialogue 闭合违规（char_lucy ⊆ character_refs）。
    # 剩余 cons 全是本体解析（露西 refs 不在已加载本体内，与对白拆分正交）。
    cons = consistency_check.check(graph)
    closure_violations = [
        i
        for i in cons
        if "speaker_ref" in i.message or "dialogue" in i.location
    ]
    assert closure_violations == [], [
        (i.location, i.message) for i in closure_violations
    ]
    assert all("does not resolve in ontology" in i.message for i in cons), [
        i.message for i in cons
    ]
