"""白描预设（baimiao）—— Forgewright 默认审美预设.

Phase 2 规则分层（作者拍板 2026-06-12 决策 B）：白描从"硬编码进生成 prompt 的规则"
降为**一个可替换的审美预设**。预设三件套：
  1. PROSE_STYLE_RULES —— 文风段（原 pass2 narration 规则里的白描句挪到这里）；
  2. PRESET_AP_IDS —— 归本预设的 AP 条款（AP-1 反对仗 / AP-5 总结代细节）；
  3. ANCHOR_PLAN —— 各调用类型注入哪些作者批准锚点（anchors_v1.json；决策 C）。
换文风 = 在本目录新建一个预设模块替换三件套，核心管线零改动。
"""
from __future__ import annotations

from generator.prompts.node.anti_pattern_blacklist import BAIMIAO_PRESET_AP_IDS

NAME = "baimiao"

PROSE_STYLE_RULES = """## 文风预设：白描
- 白描为主：少抽象评价、少漂亮警句，不排比 / 不对仗 / 不堆成语 / 不押韵。
- 评价必须有可观察细节铺垫；优先物理细节（动作 / 视线 / 声音 / 气味 / 触感）。
- 超自然 / 异常以可复核的物理细节出现（最好经 NPC 之口），不堆"诡异 / 不祥"类形容词。"""

PRESET_AP_IDS: tuple[str, ...] = BAIMIAO_PRESET_AP_IDS  # ("AP-1", "AP-5")

# 各调用类型注入的锚点 id（ADR-018 按需注入精神：只给该调用相关角色的样例）
ANCHOR_PLAN: dict[str, dict[str, list[str]]] = {
    "pass2_opening": {
        "narration": ["A1", "A2"],
        "npc_dialogue": ["A7", "A9"],
        "player_option": ["A16", "A17", "A18"],
    },
    "pass2_mid": {
        "narration": ["A3", "A4"],
        "npc_dialogue": ["A8", "A11"],
        "player_option": ["A16", "A17", "A18"],
    },
    "beats": {
        "narration": ["A3", "A4"],
        "npc_dialogue": ["A9", "A10", "A11"],
        "player_option": ["A13", "A14", "A15"],
    },
    "end": {
        "narration": ["A5", "A6"],
        "npc_dialogue": ["A12"],
        "player_option": [],
    },
}

__all__ = ["NAME", "PROSE_STYLE_RULES", "PRESET_AP_IDS", "ANCHOR_PLAN"]
