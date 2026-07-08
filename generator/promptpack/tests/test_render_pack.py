"""P-A 写作提示词包渲染器单测（T-3P-1）.

覆盖任务规格四类完成标准：
  - golden-file：T-3P-0 共用 augmented lucy fixture（固定路径，不自行合成）渲染
    结果与已落盘的作者验收物逐字节一致；
  - 结构正确性：选项序号/意图/去向对齐 skeleton.route_to；逐拍清单对齐 beats_plan；
    每节点应交 key 清单与 format_spec（NODE_CATEGORY_KEYS）一致；
  - 确定性：同输入两次渲染逐字节相等（含环境无关：FORGEWRIGHT_STYLE_ANCHORS 不影响）；
  - 边界：无 summaries / 无 character_state / legacy design 报错 / sidecar 坏输入 /
    悬空引用与不可达节点在渲染期被拦。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from generator.context_assembler import PriorSceneSummary
from generator.promptpack.format_spec import (
    ERRORS,
    EXIT_OK,
    EXIT_USAGE,
    NODE_CATEGORY_KEYS,
)
from generator.promptpack.io import load_design_artifact, load_scene_spec
from generator.promptpack.render_pack import main, render_pack

_EXPERIMENTS = Path(__file__).resolve().parents[2] / "experiments" / "multipass_structure"
# T-3P-0 交付的共用 fixture（golden 必须引用这份，保证与 T-3P-2/3 字节级同源）
_FIXTURE_DESIGN = _EXPERIMENTS / "2026-06-29_t3p_fixture" / "lucy" / "design.json"
_LUCY_SPEC = _EXPERIMENTS / "specs" / "lucy.json"
# 作者验收物 = golden 基准（README 有复现命令；改渲染逻辑必须同步重渲此文件）
_GOLDEN_PACK = _EXPERIMENTS / "2026-07-08_t3p1_pack" / "lucy_roadhouse_multipass.pack.md"


@pytest.fixture(scope="module")
def lucy_design() -> dict:
    return load_design_artifact(_FIXTURE_DESIGN)


@pytest.fixture(scope="module")
def lucy_spec() -> dict:
    return load_scene_spec(_LUCY_SPEC)


@pytest.fixture(scope="module")
def lucy_pack(lucy_design: dict, lucy_spec: dict) -> str:
    return render_pack(lucy_design, lucy_spec)


def _node_section(pack: str, node_id: str) -> str:
    """取逐节点填空单里单个节点的小节文本（### 头到下一个 ### / ## 之间）。"""
    m = re.search(
        rf"^### [◆─] {re.escape(node_id)}（.*?(?=^### |^## )",
        pack,
        flags=re.S | re.M,
    )
    assert m, f"pack 里找不到节点小节 {node_id}"
    return m.group(0)


# ---------------------------------------------------------------------------
# golden + 确定性
# ---------------------------------------------------------------------------


def test_lucy_pack_matches_committed_golden(lucy_pack: str) -> None:
    """T-3P-0 固定 fixture 渲染 == 已落盘作者验收物（逐字节）。"""
    assert lucy_pack == _GOLDEN_PACK.read_text(encoding="utf-8")


def test_render_is_deterministic(lucy_design: dict, lucy_spec: dict) -> None:
    assert render_pack(lucy_design, lucy_spec) == render_pack(lucy_design, lucy_spec)


def test_render_ignores_style_anchor_env_switch(
    lucy_design: dict, lucy_spec: dict, lucy_pack: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FORGEWRIGHT_STYLE_ANCHORS 是生成期 A/B 旋钮；pack 渲染必须环境无关。"""
    monkeypatch.setenv("FORGEWRIGHT_STYLE_ANCHORS", "off")
    assert render_pack(lucy_design, lucy_spec) == lucy_pack


# ---------------------------------------------------------------------------
# 结构正确性（全部从 fixture 数据推导期望，不手抄）
# ---------------------------------------------------------------------------


def test_choice_options_align_with_skeleton_route_to(
    lucy_design: dict, lucy_pack: str
) -> None:
    """每个 choice 小节的选项行：序号连续、intent 与去向逐条对齐骨架。"""
    for nid, sk in lucy_design["skeletons"].items():
        section = _node_section(lucy_pack, nid)
        lines = re.findall(r"^  (\d+)\. 〔(.*?)〕 → (\S+?)（", section, flags=re.M)
        assert [int(i) for i, _, _ in lines] == list(range(1, len(sk["options"]) + 1))
        for (_, intent, target), opt in zip(lines, sk["options"]):
            assert intent == opt["intent"]
            assert target == opt["route_to"]


def test_beats_sections_align_with_beats_plan(lucy_design: dict, lucy_pack: str) -> None:
    """每条链小节：逐拍行按 beats_plan 顺序齐全，reveal 原文在拍行里，末拍带收束注。"""
    for pid, slots in lucy_design["beats_plan"].items():
        section = _node_section(lucy_pack, pid)
        beat_lines = re.findall(r"^  - 〔(\S+)〕本拍揭露：(.*)$", section, flags=re.M)
        assert [b for b, _ in beat_lines] == [s["beat_id"] for s in slots]
        for (_, line), slot in zip(beat_lines, slots):
            for reveal in slot["reveals"]:
                assert reveal in line
            assert ("末拍" in line) == slot["is_last"]


def test_multi_entry_chain_carries_junction_note(lucy_pack: str) -> None:
    """收敛入口链（watch_corner 两个选项 → observed_soft_line）必须带多入口提醒。"""
    assert "多入口提醒" in _node_section(lucy_pack, "observed_soft_line")
    assert "多入口提醒" not in _node_section(lucy_pack, "soft_private_line")


def test_tree_order_choice_then_branches(lucy_pack: str) -> None:
    """树序：父 choice 在前，各分支按 route 顺序深先展开。"""
    positions = [
        lucy_pack.index(f"### {marker} {nid}（")
        for marker, nid in (
            ("◆", "opening"),
            ("─", "soft_private_line"),
            ("◆", "end_soft_leave"),
            ("─", "money_line"),
            ("◆", "watch_corner"),
            ("─", "observed_soft_line"),
            ("─", "basement_line"),
            ("─", "pressure_line"),
            ("◆", "end_pressure_leave"),
        )
    ]
    assert positions == sorted(positions)


def test_format_checklist_matches_format_spec(lucy_design: dict, lucy_pack: str) -> None:
    """「本场应交清单」逐行与 format_spec 的 NODE_CATEGORY_KEYS 一致。"""
    checklist = re.findall(r"^- `\[node: (\S+)\]` → (.*)$", lucy_pack, flags=re.M)
    by_id = {n["node_id"]: n for n in lucy_design["topology"]["nodes"]}
    # 期望的成品图节点块清单（树序在 test_tree_order 验；这里验集合与 key 描述）
    expected_total = 0
    seen = dict(checklist)
    for nid, node in by_id.items():
        if node["kind"] == "choice":
            expected_total += 1
            n = len(lucy_design["skeletons"][nid]["options"])
            assert f"options（序号 1..{n} 连续完整）" in seen[nid]
            assert "narration" in seen[nid]
        elif node["kind"] == "beats":
            for slot in lucy_design["beats_plan"][nid]:
                expected_total += 1
                assert seen[slot["beat_id"]] == "narration + continue；dialogue 可选"
        else:
            expected_total += 1
            assert seen[nid] == "narration；dialogue 可选（0-2 行）"
            assert "options" not in seen[nid]
    assert len(checklist) == expected_total
    assert f"应交节点块：**{expected_total} 个**" in lucy_pack
    # required/optional key 描述与 format_spec 单一真相源不漂移
    assert NODE_CATEGORY_KEYS["beat"]["required"] == ["narration", "continue"]
    assert NODE_CATEGORY_KEYS["end"]["required"] == ["narration"]


def test_template_has_one_block_per_node(lucy_design: dict, lucy_pack: str) -> None:
    """交稿模板：每个成品图节点恰好一个 [node: X] 块（清单里另有一处反引号引用）。"""
    ids = []
    for node in lucy_design["topology"]["nodes"]:
        if node["kind"] == "beats":
            ids.extend(s["beat_id"] for s in lucy_design["beats_plan"][node["node_id"]])
        else:
            ids.append(node["node_id"])
    for nid in ids:
        # 出现两次：应交清单（`[node: X]`）+ 交稿模板（[node: X]）
        assert lucy_pack.count(f"[node: {nid}]") == 2, nid
    # choice 模板带精确选项数的序号占位；end 模板不带 options / continue
    assert "options:\n  1: <…>\n  2: <…>\n  3: <…>\n  4: <…>" in lucy_pack
    m = re.search(r"^\[node: end_soft_leave\]\nnarration: <…>\n\n", lucy_pack, flags=re.M)
    assert m, "end 节点模板应只有 narration 一行"


def test_error_table_covers_e1_to_e8(lucy_pack: str) -> None:
    for e in ERRORS.values():
        assert f"| {e.code} | {e.slug} | {e.meaning} |" in lucy_pack


def test_style_section_present(lucy_pack: str) -> None:
    """文风段最小齐全性：三分类守则 + 普适 AP + 白描预设 + 锚点三角色 + 量化契约。"""
    for needle in (
        "### 5.1 三类正文的分工",
        "AP-2", "AP-3", "AP-4", "AP-6", "AP-9",  # 普适层
        "文风预设：白描", "AP-1", "AP-5",  # 预设层
        "### 5.4 量化契约",
        "250-400 汉字", "约 60-120 汉字", "80-200 汉字", "≤25 汉字", "≤20 汉字",
        "#### 旁白该写成这样",
        "#### NPC 对白该写成这样",
        "#### 玩家选项该写成这样",
        "严禁搬内容",
    ):
        assert needle in lucy_pack, needle


# ---------------------------------------------------------------------------
# 故事至此（便宜版连续性）
# ---------------------------------------------------------------------------


def test_no_summaries_renders_first_scene_note(lucy_pack: str) -> None:
    assert "本场景为首场（或无前情摘要）" in lucy_pack
    assert "## 前置场景概要" not in lucy_pack


def test_summaries_render_in_order(lucy_design: dict, lucy_spec: dict) -> None:
    summaries = [
        PriorSceneSummary(scene_id="scene_a", summary="玩家验尸得知死状蹊跷", key_state_paths=["flags.autopsy_done"]),
        PriorSceneSummary(scene_id="scene_b", summary="玩家拿到酒馆地址", key_state_paths=[]),
    ]
    pack = render_pack(lucy_design, lucy_spec, summaries)
    assert "## 前置场景概要（按时间顺序）" in pack
    a = pack.index("- [scene_a] 玩家验尸得知死状蹊跷; 关键状态写入：flags.autopsy_done")
    b = pack.index("- [scene_b] 玩家拿到酒馆地址; 关键状态写入：（无）")
    assert a < b
    assert "本场景为首场" not in pack


def test_missing_character_state_renders_placeholder(lucy_design: dict) -> None:
    pack = render_pack(lucy_design, {"background": "x"})
    assert "**本场人物状态（作者手记，原样透传）**：\n（无）" in pack


# ---------------------------------------------------------------------------
# 边界（CLI + 输入卫兵）；synthetic 输入只用于负路径与 CLI 行为，
# golden/结构测试一律用 T-3P-0 fixture
# ---------------------------------------------------------------------------

_RUN_CONFIG = {
    "graph_id": "mini_scene",
    "scene_anchor": "scene_mini",
    "speaker_ref": "char_npc",
    "character_refs": ["char_npc"],
    "npc_name": "某人",
}


def _mini_design() -> dict:
    return {
        "contract": {"player_goal": "拿到线索", "npc_goal": "", "npc_fear": "", "forbidden": []},
        "topology": {
            "entry_node_id": "start",
            "nodes": [
                {
                    "node_id": "start",
                    "kind": "choice",
                    "function": "开场",
                    "reveals": [],
                    "routes": [{"to": "line_a", "stance": ""}, {"to": "end_b", "stance": ""}],
                },
                {"node_id": "line_a", "kind": "beats", "function": "追问",
                 "reveals": ["线索甲"], "next": "end_a"},
                {"node_id": "end_a", "kind": "end", "function": "带线索离开", "reveals": []},
                {"node_id": "end_b", "kind": "end", "function": "空手离开", "reveals": []},
            ],
        },
        "skeletons": {
            "start": {
                "node_id": "start",
                "function": "开场",
                "situation": "局面",
                "choice_pressure": "压力",
                "reveals": [],
                "hides": [],
                "options": [
                    {"intent": "追问", "route_to": "line_a"},
                    {"intent": "离开", "route_to": "end_b"},
                ],
            }
        },
        "beats_plan": {
            "line_a": [{"beat_id": "line_a_b1", "reveals": ["线索甲"], "is_last": True}]
        },
        "run_config": dict(_RUN_CONFIG),
    }


def _write_inputs(tmp_path: Path, design: dict) -> tuple[Path, Path]:
    design_path = tmp_path / "design.json"
    design_path.write_text(
        json.dumps(
            {"design": design, "call_metas": [], "warnings": [], "validation": {},
             "status": "success", "failure_reason": None},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {"config": dict(_RUN_CONFIG),
             "spec": {"background": "小场景", "character_state": "某人：紧张。"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return design_path, spec_path


def test_cli_renders_to_default_out(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    design_path, spec_path = _write_inputs(tmp_path, _mini_design())
    assert main(["--design", str(design_path), "--spec", str(spec_path)]) == EXIT_OK
    out = tmp_path / "mini_scene.pack.md"  # 默认 = design 同目录 <graph_id>.pack.md
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# 写作提示词包 · mini_scene" in text
    assert "[node: line_a_b1]" in text
    assert "（4 个节点块）" in capsys.readouterr().out


def test_cli_out_flag_and_summaries(tmp_path: Path) -> None:
    design_path, spec_path = _write_inputs(tmp_path, _mini_design())
    sidecar = tmp_path / "prev.summary.json"
    sidecar.write_text(
        json.dumps({"scene_id": "scene_prev", "summary": "前情一句",
                    "key_state_paths": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    out = tmp_path / "custom" / "pack.md"
    assert main([
        "--design", str(design_path), "--spec", str(spec_path),
        "--summaries", str(sidecar), "--out", str(out),
    ]) == EXIT_OK
    assert "- [scene_prev] 前情一句" in out.read_text(encoding="utf-8")


def test_cli_legacy_design_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """缺 beats_plan / run_config 的 legacy design → loader 拒收 → 退出码 2。"""
    design = _mini_design()
    del design["beats_plan"], design["run_config"]
    design_path, spec_path = _write_inputs(tmp_path, design)
    assert main(["--design", str(design_path), "--spec", str(spec_path)]) == EXIT_USAGE
    assert "structure-only" in capsys.readouterr().err


def test_cli_rejects_bad_summaries_paths(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    design_path, spec_path = _write_inputs(tmp_path, _mini_design())
    base = ["--design", str(design_path), "--spec", str(spec_path), "--summaries"]
    # 非 sidecar 命名
    assert main(base + [str(tmp_path / "scene.json")]) == EXIT_USAGE
    # sidecar 不存在
    assert main(base + [str(tmp_path / "ghost.summary.json")]) == EXIT_USAGE
    # sidecar 在但内容坏
    bad = tmp_path / "bad.summary.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(base + [str(bad)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert err.count("输入错误") == 3


def test_cli_dangling_next_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """beats.next 指向不存在节点（loader 不查这条）→ 渲染期卫兵拦 → 退出码 2。"""
    design = _mini_design()
    design["topology"]["nodes"][1]["next"] = "ghost_end"
    design["topology"]["nodes"] = [n for n in design["topology"]["nodes"] if n["node_id"] != "end_a"]
    design_path, spec_path = _write_inputs(tmp_path, design)
    assert main(["--design", str(design_path), "--spec", str(spec_path)]) == EXIT_USAGE
    assert "不存在的节点" in capsys.readouterr().err


def test_cli_unreachable_node_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """入口不可达节点会被 pack 漏掉（编剧交稿必吃 E1）→ 渲染期卫兵拦 → 退出码 2。"""
    design = _mini_design()
    design["topology"]["nodes"].append(
        {"node_id": "end_orphan", "kind": "end", "function": "孤儿", "reveals": []}
    )
    design_path, spec_path = _write_inputs(tmp_path, design)
    assert main(["--design", str(design_path), "--spec", str(spec_path)]) == EXIT_USAGE
    assert "不可达" in capsys.readouterr().err
