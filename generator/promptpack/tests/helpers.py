"""T-3P-2 ingest 测试共享物料：mini design（快路径错误矩阵）+ lucy 占位回流构造器.

mini design = 最小合法 structure-only design（1 choice×2 选项 + 1 beats 链×2 拍 +
2 end），走 io.load_design_artifact 读取（loader 契约同真实产物）。
lucy 占位回流基于 T-3P-0 augmented fixture 构造——golden 允许占位文本
（只验格式 / 对齐 / 机械合并正确性，不验文学质量；拆解 §5.3）。
占位文本刻意避开 AP-7/8/10 程序化反模式（对偶测试要过 AP 预检）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# T-3P-0 augmented lucy fixture（任务规格钉死的固定路径）
FIXTURE_DESIGN = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "multipass_structure"
    / "2026-06-29_t3p_fixture"
    / "lucy"
    / "design.json"
)


def make_mini_design_wrapper() -> dict[str, Any]:
    """最小合法 design.json wrapper（structure-only 形态；过 loader 全部校验）。

    成品图期望节点：start / line_a_b1 / line_a_b2 / end_a / end_quick（5 个）。
    """
    design = {
        "contract": {},
        "topology": {
            "entry_node_id": "start",
            "nodes": [
                {
                    "node_id": "start",
                    "kind": "choice",
                    "routes": [{"to": "line_a"}, {"to": "end_quick"}],
                    "reveals": [],
                },
                {
                    "node_id": "line_a",
                    "kind": "beats",
                    "routes": [],
                    "next": "end_a",
                    "reveals": ["线索一", "线索二"],
                },
                {"node_id": "end_a", "kind": "end", "routes": [], "reveals": []},
                {"node_id": "end_quick", "kind": "end", "routes": [], "reveals": []},
            ],
        },
        "skeletons": {
            "start": {"options": [{"route_to": "line_a"}, {"route_to": "end_quick"}]}
        },
        "proses": {},
        "beats": {},
        "ends": {},
        "beats_plan": {
            "line_a": [
                {"beat_id": "line_a_b1", "reveals": ["线索一"], "is_last": False},
                {"beat_id": "line_a_b2", "reveals": ["线索二"], "is_last": True},
            ]
        },
        "run_config": {
            "graph_id": "mini_scene",
            "scene_anchor": "scene_mini",
            "speaker_ref": "char_npc",
            "character_refs": ["char_npc"],
            "npc_name": "NPC",
        },
    }
    return {
        "design": design,
        "call_metas": [],
        "warnings": [],
        "validation": None,
        "status": "success",
        "failure_reason": None,
    }


def write_mini_design(tmp_path: Path) -> Path:
    path = tmp_path / "design.json"
    path.write_text(
        json.dumps(make_mini_design_wrapper(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


# mini design 的合法回流（5 节点全交齐；正文避开 AP 反模式）
MINI_GOOD_REPLY = """\
[node: start]
narration: 门口的灯亮着。柜台后没有人。
dialogue:
  - 想问什么就快点问。
options:
  1: 我想打听一个人。
  2: 我什么都不问，先走了。

[node: line_a_b1]
narration: 她压低了声音。
dialogue:
  - 线索一在北边。
continue: 我继续听。

[node: line_a_b2]
narration: 她把抹布放下。
dialogue:
  - 线索二在雨桶下面。
continue: 我记下了。

[node: end_a]
narration: 你退出门外，把话都收进兜里。

[node: end_quick]
narration: 你转身离开，没有回头。
"""


def build_placeholder_reply(design: dict[str, Any]) -> str:
    """按锁定骨架构造合法占位回流（每个期望节点一块，块序 = topology 序）。"""
    blocks = []
    for node in design["topology"]["nodes"]:
        pid = node["node_id"]
        kind = node.get("kind")
        if kind == "choice":
            n = len(design["skeletons"][pid]["options"])
            option_lines = "\n".join(
                f"  {i}: 我按第{i}条占位台词往下走。" for i in range(1, n + 1)
            )
            blocks.append(
                f"[node: {pid}]\n"
                f"narration: 占位旁白（{pid}）。灯光落在吧台边。\n"
                "dialogue:\n"
                f"  - 占位对白（{pid}）。\n"
                "options:\n"
                f"{option_lines}"
            )
        elif kind == "beats":
            for slot in design["beats_plan"][pid]:
                bid = slot["beat_id"]
                blocks.append(
                    f"[node: {bid}]\n"
                    f"narration: 占位旁白（{bid}）。她把杯子放下。\n"
                    "dialogue:\n"
                    f"  - 占位对白（{bid}）。\n"
                    "continue: 我接着往下问。"
                )
        elif kind == "end":
            blocks.append(f"[node: {pid}]\nnarration: 占位旁白（{pid}）。你起身离开。")
    return "\n\n".join(blocks) + "\n"


__all__ = [
    "FIXTURE_DESIGN",
    "MINI_GOOD_REPLY",
    "build_placeholder_reply",
    "make_mini_design_wrapper",
    "write_mini_design",
]
