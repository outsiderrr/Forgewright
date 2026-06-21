"""Anti-pattern blacklist（反模式黑名单）— A1 反馈 v0.1 §2 的提示词版（7 条）.

canonical 10 条见 /docs/reviews/master_plan/2026-05-14_A1_text_review_feedback_v0.1.md §2。
其中 AP-7 / AP-8 / AP-10 已由 validator/anti_pattern_detector.py **程序化检测**
（detect_ap7 / ap8 / ap10），按 Phase 1 结构层落地决策（FINDINGS §3 / ADR-038 follow-up）
**不再进任何生成提示词**——留在 prompt 里纯属白占注意力，校验器兜底。

Phase 2 规则分层（作者拍板 2026-06-12；设计 =
generator/experiments/aesthetic_layer/DESIGN_2026-06-12_phase2_style_layer.md §2）：
提示词版 7 条进一步拆为两层——
  - **普适结构层**（AP-2/3/4/6/9）：任何文风都不该犯（坏比喻 / 物理逻辑错 / 假靶子 /
    无锚标准 / 读不懂的省略），永远注入，不随审美预设切换；
  - **审美预设层**（AP-1/AP-5）：反对仗、细节代总结是"白描"这一预设的条款，
    随 generator/prompts/style/ 预设装配，可开关 / 替换。
`ANTI_PATTERN_BLACKLIST_TEXT`（7 条合体）保留供单 pass 旧路径（system.py）使用，行为不变。
"""
from __future__ import annotations

_HEADER = """## Anti-pattern 黑名单（A1 反馈 v0.1 §2 提示词版 7 条；违反 = 不合规）
（AP-7 / AP-8 / AP-10 已由校验器程序化检测，不在此列；编号保持原编号。）"""

# 每条独立成块；普适/预设分层只动组合方式，不动条款文本（单一真相源）。
AP_TEXTS: dict[str, str] = {
    "AP-1": """### AP-1: AI 对仗式 / 重复对应感过强
- 单段内避免成对对仗式结构；前半已暗示的，后半不要重复明示
- 反例：「前厅摆着……像一张给警察和好人看的脸；真正的热闹从后门那条窄楼梯往下漏」（前半已暗示"另一面"，后半冗余）""",
    "AP-2": """### AP-2: 修辞失底（喻体与本体无共同点）
- 用比喻 / 类比前必须明示喻体和本体的共同点；说不清就直接白描，不用修辞
- 反例：「托盘在她指尖稳得像变戏法」（"变戏法" 与"托盘稳" 无共同点）
- 反例：「你别摆那副法官脸」（"法官脸" 究竟指什么——正义？审视？怀疑？——无线索）""",
    "AP-3": """### AP-3: 修辞方向 / 物理逻辑错误
- 用动词 / 修辞前检查物理方向 / 逻辑是否与场景一致
- 反例：「真正的热闹从后门那条窄楼梯往下漏」（"漏" 是从上往下，但热闹是从地下传上来的，方向相反）""",
    "AP-4": """### AP-4: 假靶子否定
- 否定句必须否定读者真实预期的靶子；不要竖一个读者本来没预期的靶子去否定
- 反例：「名字落下去时，露西脸上的笑没有碎」（没人预期笑会"碎"）
- 改法：直接写"露西脸上的笑只是停了一拍\"""",
    "AP-5": """### AP-5: 总结代细节
- 先给具体行为 / 物理细节，避免直接给评价；如果必须给评价，前后要有具体细节铺垫
- 反例：「眼神却老练得不像二十五六岁的人」（"老练"是评价，无可观察细节）
- 正例：「她扫了你一眼，先看鞋，再看手，再看你有没有像常客那样急着找酒」（具体行为）""",
    "AP-6": """### AP-6: 锚定未说明的标准
- 不要引入读者不知道的"一般标准"作为对比基准
- 反例：「她的金发颜色新得过分」（"金发的一般标准"读者不知道）
- 改法：写具体细节（如"她的金发还有刚染过的化学气味"）""",
    "AP-9": """### AP-9: 读不懂的省略
- 留白前必须确保读者有线索能 fill in；如果线索还没出现，直接交代
- 反例：「有些人欠钱会怕打手，莱特怕的不是打手」（莱特怕的是什么？读者不知道）""",
}

# Phase 2 分层（作者拍板 2026-06-12 决策 B：8 普适 + 2 预设）
UNIVERSAL_AP_IDS: tuple[str, ...] = ("AP-2", "AP-3", "AP-4", "AP-6", "AP-9")
BAIMIAO_PRESET_AP_IDS: tuple[str, ...] = ("AP-1", "AP-5")

_PROMPT_ORDER: tuple[str, ...] = ("AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9")


def universal_ap_block() -> str:
    """普适结构层条款（任何审美预设都注入；不随预设切换）。"""
    body = "\n\n".join(AP_TEXTS[i] for i in _PROMPT_ORDER if i in UNIVERSAL_AP_IDS)
    return f"""## Anti-pattern 黑名单 · 普适结构层（任何文风都不该犯；违反 = 不合规）
（AP-7 / AP-8 / AP-10 已由校验器程序化检测；AP-1 / AP-5 归审美预设层；编号保持原编号。）

{body}"""


def preset_ap_block(ids: tuple[str, ...]) -> str:
    """审美预设层条款（由 generator/prompts/style/ 预设装配；可换）。"""
    body = "\n\n".join(AP_TEXTS[i] for i in _PROMPT_ORDER if i in ids)
    if not body:
        return ""
    return body


# 7 条合体（旧形态；单 pass 路径 system.py 仍用它，行为不变）
ANTI_PATTERN_BLACKLIST_TEXT = _HEADER + "\n\n" + "\n\n".join(
    AP_TEXTS[i] for i in _PROMPT_ORDER
) + "\n"

__all__ = [
    "ANTI_PATTERN_BLACKLIST_TEXT",
    "AP_TEXTS",
    "UNIVERSAL_AP_IDS",
    "BAIMIAO_PRESET_AP_IDS",
    "universal_ap_block",
    "preset_ap_block",
]
