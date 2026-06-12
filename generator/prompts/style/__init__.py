"""文风层装配（Phase 2）—— 审美预设分层 + 作者批准样例锚点注入.

设计 + 作者拍板记录：generator/experiments/aesthetic_layer/DESIGN_2026-06-12_phase2_style_layer.md
（决策 A/B/C/D，2026-06-12）。上位机制：样例 = 控制（example-conditioning，范例条件化），
比规则强；维度 = 探索 + 校验（taxonomy 在 generator/judge/taxonomy.py，judge 同维打分）。

分层：
  - 普适结构条款（AP-2/3/4/6/9）：任何预设都注入（anti_pattern_blacklist.universal_ap_block）；
  - 审美预设（默认白描 baimiao）：预设 AP 条款（AP-1/AP-5）+ 文风段，可换；
  - 锚点（anchors_v1.json，作者批准 18 条）：按调用类型挑相关角色样例注入 user prompt。

开关（A/B 对照用）：环境变量 FORGEWRIGHT_STYLE_ANCHORS=off 关闭锚点注入
（预设规则段不受此开关影响——A/B 只对照"带锚点 vs 不带"，规则两臂一致）。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from generator.prompts.node.anti_pattern_blacklist import (
    preset_ap_block,
    universal_ap_block,
)
from generator.prompts.style.presets import PRESETS

ANCHORS_PATH = Path(__file__).parent / "anchors_v1.json"

ANCHORS_ENV_VAR = "FORGEWRIGHT_STYLE_ANCHORS"

# 角色三分类的展示标题（与 role_rules 三契约对应）
_ROLE_TITLES = {
    "narration": "旁白该写成这样",
    "npc_dialogue": "NPC 对白该写成这样",
    "player_option": "玩家选项该写成这样",
}

_ANTI_COPY_GUARD = (
    "下面的样例来自**其他场景**的作者批准文本，只示范文风、节奏与口吻。\n"
    "样例里的人名、地名、道具、事实细节都不属于本场景——**一律不得出现在你的输出里**。"
)


@lru_cache(maxsize=1)
def load_anchors() -> dict[str, dict[str, Any]]:
    """读锚点库 v1（id → 条目）；进程内缓存。"""
    payload = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
    return {a["id"]: a for a in payload["anchors"]}


def anchors_enabled() -> bool:
    """锚点注入开关（默认开；FORGEWRIGHT_STYLE_ANCHORS=off 关）。"""
    return os.environ.get(ANCHORS_ENV_VAR, "on").strip().lower() != "off"


def style_rules_block(preset: str = "baimiao") -> str:
    """预设规则段（文风段 + 预设 AP 条款）——进 system prompt，不随锚点开关动。"""
    p = PRESETS[preset]
    ap = preset_ap_block(p.PRESET_AP_IDS)
    ap_part = (
        f"\n\n## Anti-pattern · 审美预设条款（{p.NAME} 预设；违反 = 不合规）\n\n{ap}" if ap else ""
    )
    return f"{p.PROSE_STYLE_RULES}{ap_part}"


def style_anchor_block(call_type: str, preset: str = "baimiao") -> str:
    """锚点样例块（进 user prompt）；锚点关闭或该调用类型无锚点时返回空串。

    Args:
        call_type: "pass2_opening" | "pass2_mid" | "beats" | "end"
            （预设 ANCHOR_PLAN 的键；未知类型返回空串，不抛——文风层不许打断生成）。
        preset: 审美预设名。
    """
    if not anchors_enabled():
        return ""
    plan = PRESETS[preset].ANCHOR_PLAN.get(call_type)
    if not plan:
        return ""
    anchors = load_anchors()
    sections: list[str] = []
    for role in ("narration", "npc_dialogue", "player_option"):
        ids = [i for i in plan.get(role, []) if i in anchors]
        if not ids:
            continue
        lines = "\n".join(f"- {anchors[i]['text']}" for i in ids)
        sections.append(f"### {_ROLE_TITLES[role]}\n{lines}")
    if not sections:
        return ""
    body = "\n\n".join(sections)
    return f"""## 文风锚点（作者批准样例 v1——只学质感，严禁搬内容）
{_ANTI_COPY_GUARD}

{body}"""


__all__ = [
    "ANCHORS_PATH",
    "ANCHORS_ENV_VAR",
    "load_anchors",
    "anchors_enabled",
    "style_rules_block",
    "style_anchor_block",
    "universal_ap_block",
]
