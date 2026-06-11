"""入口上下文（entry context）prompt 块 —— 收敛路由 × junction 承接的单一措辞来源.

设计：generator/experiments/multipass_structure/DESIGN_2026-06-11_convergent_routes.md §2-C
（作者批准 2026-06-11）。

修复的玩家可见穿帮（2026-06-10 复核根因①⑥ + §2.2 junction 遗留）：
  - 答非所问：收敛入口的链首拍预设了玩家没说过的话（vick/c1 business_entry_b1）；
  - junction（节点交界）失忆：链尾玩家末句被下游节点无视（whitcroft/c1 opening_b3）。

机制：引擎为每个非入口节点算出"玩家是怎么走进来的"（EntryContext dict），
四类生成调用（链首拍 / 子 choice 骨架 / 子 choice 正文 / end 收束）统一注入本模块
渲染的 prompt 块——措辞只在这里维护，避免四处各写一版漂移。

EntryContext 形态（引擎构造；本模块只渲染）：
  {"mode": "single" | "convergent",
   "entries": [{"text": 玩家选项最终台词, "intent": 设计意图（可空）}],
   "stance": 该入边在拓扑里的姿态描述（可空）}
"""
from __future__ import annotations

from typing import Any


def entry_context_block(entry_context: dict[str, Any] | None) -> str:
    """渲染入口上下文 prompt 块；entry_context 为 None / 无入口语句时返回空串。"""
    if not entry_context:
        return ""
    entries = [e for e in entry_context.get("entries") or [] if (e.get("text") or "").strip()]
    if not entries:
        return ""

    if entry_context.get("mode") == "single" or len(entries) == 1:
        text = entries[0]["text"].strip()
        return f"""## 入口上下文（玩家是这样走进本节点的）
玩家刚说/刚做：「{text}」
要求：本节点开头的 NPC 反应必须**先承接这句话**（回应它，或明确拒答），
再推进本节点的新内容；不许答非所问、不许当没听见重新自顾自开场。"""

    lines = []
    for e in entries:
        gloss = (e.get("intent") or "").strip()
        lines.append(f"- 「{e['text'].strip()}」" + (f"（{gloss}）" if gloss else ""))
    entry_list = "\n".join(lines)
    stance = (entry_context.get("stance") or "").strip()
    stance_line = f"（这些入口的共同姿态：{stance}）\n" if stance else ""
    return f"""## 入口上下文（收敛入口：玩家可能刚说过下面**任意一句**）
{entry_list}
{stance_line}要求：本节点开头的 NPC 反应必须**对所有入口都成立**——
不得预设玩家提过其中某句特有的信息（人名、事件、出价等只在个别入口出现的内容）；
可以回应这些入口的共同点，或先以中性反应（动作/试探/反问）接住，再引出本节点要给的信息。"""


__all__ = ["entry_context_block"]
