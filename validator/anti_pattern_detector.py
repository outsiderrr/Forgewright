"""Anti-pattern detector（反模式检测器）— T-3Y-1 子 goal 2.

落地 A1 反馈 v0.1 §2 的 10 条 anti-pattern；其中 AP-7 / AP-8 / AP-10 程序化检测，
其他 7 条（AP-1 ~ AP-6 + AP-9）标 LLM-as-judge 待办.

检测对象：完成后的 node dict（含 narration + options[].text + speaker_ref）.

输出形态：list[AntiPatternFlag] —— 每条 flag 含 ap_id / location / excerpt / reason.

设计哲学：mini prototype 偏向**召回率**（少漏报，可接受假阳性）；
LLM-as-judge 后续承接精确确认 + 7 条无法纯程序化的 anti-pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

ApId = Literal[
    "AP-1", "AP-2", "AP-3", "AP-4", "AP-5",
    "AP-6", "AP-7", "AP-8", "AP-9", "AP-10",
]


@dataclass
class AntiPatternFlag:
    """单条 anti-pattern 检测结果."""

    ap_id: ApId
    """anti-pattern 编号（AP-1 ~ AP-10）."""

    location: str
    """触发位置：'narration' / 'options[<i>].text' / 'quote_in_narration'."""

    excerpt: str
    """触发文本片段（最多 80 汉字）."""

    reason: str
    """触发理由（人类可读）."""


# ---------- AP-7: 旁白抢 NPC 台词（narration 中含转述模式）----------

# 简化启发式：narration 含「她说 / 他说 / 她告诉 / 他告诉 / 她解释 / 他解释」
# 等转述模式，且不是紧接引号（"她说：「...」" 是正常用法，不 flag）。
# 2026-06-10 误报修复（作者授权；结构层复核实证的三种误报型，详
# generator/experiments/multipass_structure/2026-06-10_review/REVIEW_REPORT.md §2.7）：
#   a. 逗号引语归属——「…」她说，「…」（，/, 加入豁免集）；
#   b. "说话/讲话"是言说动作的物理描写不是转述（话 加入豁免集）；
#   c. 引号内对白是 NPC 自己的话，不属于旁白转述（detect 时跳过引号 span——
#      结构层组装会把 NPC 对白以「」并入 node.narration）。
# 三者都不在"旁白转述 NPC 信息"的定义内，排除不损召回。
_AP7_TRANSCRIPTION_RE = re.compile(
    r"(她|他)(说|告诉|解释|说道|交代|讲|表示|提到)(?![:：，,「\"“话])"
)


def detect_ap7_narration_steals_npc_speech(narration: str) -> list[AntiPatternFlag]:
    """AP-7 程序化检测：narration 中含第三人称转述模式（非紧接引号、不在引号内）."""
    if not narration:
        return []
    # 引号内 span（复用 AP-10 的引号正则）——只审旁白本身，不审 NPC 引号内对白
    quoted_spans = [m.span() for m in _AP10_QUOTE_RE.finditer(narration)]
    flags: list[AntiPatternFlag] = []
    for match in _AP7_TRANSCRIPTION_RE.finditer(narration):
        if any(s <= match.start() < e for s, e in quoted_spans):
            continue
        start = max(match.start() - 10, 0)
        end = min(match.end() + 30, len(narration))
        excerpt = narration[start:end].strip()
        flags.append(
            AntiPatternFlag(
                ap_id="AP-7",
                location="narration",
                excerpt=excerpt,
                reason=(
                    f"narration 含第三人称转述模式 '{match.group(0)}'——"
                    f"信息属于 NPC 的应让 NPC 自己说，旁白抢 NPC 台词违反 A1 反馈 v0.1 §2 AP-7"
                ),
            )
        )
    return flags


# ---------- AP-8: 选项第三人称化 ----------

# A1 反馈 §2 AP-8 明示：option.text 以「追问 / 共情 / 警告 / 离开 / 先 / 把」等
# 第三人称意图动词或动作概括开头 → flag. 第一人称（'我...' / '你...' / 引号开头）OK.
_AP8_THIRD_PERSON_VERBS = (
    "追问", "共情", "警告", "离开", "把", "与", "向", "对",
    "出卖", "调查", "跟随", "盘问", "质问", "揭穿", "暗示", "试探",
    "继续", "回头", "瞒住", "斥责", "讽刺", "嘲笑", "拒绝",
    "先",  # A1 明示「先追问 X」「先把 Y 坐实」都属第三人称意图描述
)

# 去除 [skill_name] 前缀
_AP8_SKILL_PREFIX_RE = re.compile(r"^\s*\[[^\[\]]+\]\s*")


def _strip_skill_prefix(text: str) -> str:
    return _AP8_SKILL_PREFIX_RE.sub("", text or "").lstrip()


def detect_ap8_option_third_person(
    options: list[dict[str, Any]],
) -> list[AntiPatternFlag]:
    """AP-8 程序化检测：option.text 主体（去 [skill] 前缀）以第三人称动词开头."""
    flags: list[AntiPatternFlag] = []
    for i, opt in enumerate(options or []):
        raw = opt.get("text", "") or ""
        body = _strip_skill_prefix(raw)
        if not body:
            continue
        # 引号开头（玩家直接说的话）跳过
        if body[0] in {'"', "「", "“", "'", "‘"}:
            continue
        # 第一人称 "我 / 你" 开头跳过
        if body.startswith(("我", "你")):
            continue
        # 命中第三人称动词前缀 → flag
        for verb in _AP8_THIRD_PERSON_VERBS:
            if body.startswith(verb):
                flags.append(
                    AntiPatternFlag(
                        ap_id="AP-8",
                        location=f"options[{i}].text",
                        excerpt=raw[:80],
                        reason=(
                            f"option.text 主体以第三人称动词 '{verb}' 开头——"
                            f"违反 A1 反馈 v0.1 §2 AP-8（选项必须第一人称语言）"
                        ),
                    )
                )
                break
    return flags


# ---------- AP-10: NPC 引号内用单字代称自己 ----------

# 检测引号内文本（NPC 直接说的话）是否含 "女孩 / 男孩 / 小孩 / 老娘 / 老子" 等
# 单字代称模式。引号识别：中文「」+ 英文 "" + 中文 ""
_AP10_QUOTE_RE = re.compile(r"[「\"“]([^「」\"“”]+)[」\"”]")
_AP10_SELF_NICKNAMES = ("女孩", "男孩", "小孩", "老娘", "老子", "本姑娘", "本少爷")


def detect_ap10_npc_self_nickname_in_quote(
    narration: str, options: list[dict[str, Any]] | None = None
) -> list[AntiPatternFlag]:
    """AP-10 程序化检测：引号内文本含单字代称自己模式."""
    flags: list[AntiPatternFlag] = []

    def _scan(text: str, where: str) -> None:
        for q_match in _AP10_QUOTE_RE.finditer(text or ""):
            quoted = q_match.group(1)
            for nick in _AP10_SELF_NICKNAMES:
                if nick in quoted:
                    flags.append(
                        AntiPatternFlag(
                            ap_id="AP-10",
                            location=where,
                            excerpt=quoted[:80],
                            reason=(
                                f"NPC 引号内文本含单字代称 '{nick}'——"
                                f"违反 A1 反馈 v0.1 §2 AP-10（用'我'或具体名字）"
                            ),
                        )
                    )
                    break

    _scan(narration, "quote_in_narration")
    for i, opt in enumerate(options or []):
        _scan(opt.get("text", ""), f"quote_in_options[{i}].text")
    return flags


# ---------- LLM-as-judge 待办（7 条非程序化）----------

LLM_AS_JUDGE_PENDING: tuple[ApId, ...] = (
    "AP-1",  # AI 对仗式 / 重复对应感过强
    "AP-2",  # 修辞失底（喻体与本体无共同点）
    "AP-3",  # 修辞方向 / 物理逻辑错误
    "AP-4",  # 假靶子否定
    "AP-5",  # 总结代细节
    "AP-6",  # 锚定未说明的标准
    "AP-9",  # 读不懂的省略
)


# ---------- 主入口 ----------

def detect_anti_patterns(node: dict[str, Any]) -> list[AntiPatternFlag]:
    """对一个完成后的 node 跑全部程序化 anti-pattern 检测.

    Args:
        node: 完成后的 Node dict（含 narration + options[].text）

    Returns:
        所有触发的 AntiPatternFlag 列表（按 ap_id + location 顺序）.
        空 list = 未触发任何程序化 anti-pattern（不代表 7 条 LLM-as-judge 待办未触发）
    """
    narration = node.get("narration", "") or ""
    options = node.get("options", []) or []

    flags: list[AntiPatternFlag] = []
    flags.extend(detect_ap7_narration_steals_npc_speech(narration))
    flags.extend(detect_ap8_option_third_person(options))
    flags.extend(detect_ap10_npc_self_nickname_in_quote(narration, options))
    return flags


__all__ = [
    "ApId",
    "AntiPatternFlag",
    "LLM_AS_JUDGE_PENDING",
    "detect_ap7_narration_steals_npc_speech",
    "detect_ap8_option_third_person",
    "detect_ap10_npc_self_nickname_in_quote",
    "detect_anti_patterns",
]
