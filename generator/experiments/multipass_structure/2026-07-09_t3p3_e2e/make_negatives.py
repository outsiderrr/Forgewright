"""T-3P-3 E2E 反例产物再生脚本（确定性；0 LLM）.

两层反例（如实标注各自性质，见本目录 README + E2E 报告）：
  1. 格式层：坏回流 reply_bad.md → ingest 退回单 reply_bad.reject.md
     （对**编剧错误**的真实拦截面；4 类 E 错误 E1/E4/E6/E8）。
  2. 语义层：直接构造非法 graph illegal_scene.json → 验收管线 fail
     （**技术负路径测试**，非编剧回流模拟——路线 A 下编剧触不到这些结构字段）。

用法（从仓库根跑）：
    python generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/make_negatives.py
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_REPO_ROOT = HERE.parents[3]
if str(_REPO_ROOT) not in sys.path:  # 允许从任意 cwd 直接 `python <此脚本>` 跑
    sys.path.insert(0, str(_REPO_ROOT))

from generator.promptpack.acceptance import (  # noqa: E402
    run_acceptance,
    write_acceptance_report,
)
LANDED_SCENE = (
    _REPO_ROOT
    / "content"
    / "_e2e_writer_loop"
    / "lucy_roadhouse"
    / "scene.json"
)


def make_format_negative() -> None:
    """从 reply_good.md 派生含 4 类 E 错误的坏回流（E1/E4/E6/E8）。

    确定性变异（供 E2E 报告逐条对照）：
      - E1：删掉 pressure_line_b4 整块（漏节点）；
      - E4：opening 选项序号 1,2,3,4 → 1,2,3,5（不连续）；
      - E6：end_soft_leave 加 options: 块（end 节点错位 key）；
      - E8：opening 块内插一行无法归属任何 key 的游离行。
    """
    good = (HERE / "reply_good.md").read_text(encoding="utf-8")
    # E4：opening 第 4 选项序号 4 → 5
    good = good.replace(
        "  4: 莱特的事，不说会更麻烦。", "  5: 莱特的事，不说会更麻烦。"
    )
    blocks = good.split("\n\n")
    new_blocks: list[str] = []
    for b in blocks:
        head = b.splitlines()[0].strip() if b.strip() else ""
        if head == "[node: pressure_line_b4]":  # E1：删块
            continue
        if head == "[node: end_soft_leave]":  # E6：end 加 options
            b = b + "\noptions:\n  1: 这个 end 节点不该有选项。"
        if head == "[node: opening]":  # E8：插游离行
            b = b + "\n（这是一行游离备注，既不是选项也不是对白，无法归属任何 key）"
        new_blocks.append(b)
    (HERE / "reply_bad.md").write_text(
        "\n\n".join(new_blocks) + "\n", encoding="utf-8"
    )
    print("wrote reply_bad.md（reject 单由 ingest CLI 生成——见 README 复现命令）")


def make_semantic_negative() -> None:
    """从已落地的合法 scene.json 派生非法 graph（闭合违规 + 机械违规）→ 验收 fail。

    确定性变异：
      - 闭合违规：entry 节点 dialogue[] 加一句 speaker_ref=char_ghost_writer
        （不在 character_refs=['char_lucy'] 里）；
      - 机械违规：某 choice 首选项加 effects op=not_a_real_op（EFFECT_OP_INVALID）
        + path 首段 flags（PATH_NS_INVALID）。
    """
    good = json.loads(LANDED_SCENE.read_text(encoding="utf-8"))
    bad = copy.deepcopy(good)
    entry = bad["entry_node_id"]
    bad["nodes"][entry]["dialogue"].append(
        {"speaker_ref": "char_ghost_writer", "line": "我是不该出现的说话人。"}
    )
    for node in bad["nodes"].values():
        if node.get("options"):
            node["options"][0].setdefault("effects", []).append(
                {"op": "not_a_real_op", "path": "flags.some_flag", "value": True}
            )
            break
    (HERE / "illegal_scene.json").write_text(
        json.dumps(bad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = run_acceptance(bad)
    write_acceptance_report(report, HERE / "illegal_scene.json")
    print(
        f"wrote illegal_scene.json + 验收报告：passed={report.passed} "
        f"blocking={report.blocking_error_count}"
    )


if __name__ == "__main__":
    make_format_negative()
    make_semantic_negative()
