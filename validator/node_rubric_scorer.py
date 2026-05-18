"""Node rubric scorer（节点评分器）— T-3Y-1 子 goal 2.

最简版 2 维度（mini prototype）：
  1. information_density 信息密度
     基于 narration 字数 + options 数量 + NPC 引号段数的启发式分数
  2. baimiao_compliance  白描合规度
     基于 narration 中"评价性词"和"比喻词"占比的反向分数（越少 = 合规度越高）

每维度返回 [0.0, 10.0] 浮点分数 + 计算痕迹（trace）便于 dry-run 报告复盘.

完整 rubric（含更多维度如"信息含蓄度" / "节奏" / "角色弧光承载"等）推迟到 T-3Y v0.2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------- 评价性词清单（违反白描原则）----------
# 这些词暗示总结性评价 / 主观判断 / 概略描述，应替换为具体物理细节
_EVALUATION_WORDS = (
    "显然", "明显", "似乎", "大约", "看起来", "听上去",
    "好像", "彷佛", "仿佛", "宛如", "犹如",
    "也许", "或许", "大概", "可能", "估计",
    "总之", "无论如何", "总而言之",
    "充满", "弥漫", "笼罩",  # 过度抽象的氛围词
)

# 比喻 / 修辞词（明喻和暗喻 + AI 喜爱的对仗连接词）
_FIGURATIVE_WORDS = (
    "像", "如同", "好比", "犹如", "宛若", "宛如",
    "般", "似的",
)


@dataclass
class RubricScore:
    """单维度评分结果."""

    dimension: str
    """维度名（如 'information_density' / 'baimiao_compliance'）."""

    score: float
    """0.0 ~ 10.0 分数."""

    trace: dict[str, Any] = field(default_factory=dict)
    """计算痕迹（参与计算的中间值，便于复盘）."""


def _count_chinese_chars(text: str) -> int:
    """统计中文字符数（粗略：U+4E00 ~ U+9FFF）."""
    return sum(1 for ch in text or "" if "一" <= ch <= "鿿")


def _count_substring_occurrences(text: str, substrings: tuple[str, ...]) -> int:
    """统计 substrings 在 text 中的累计出现次数."""
    if not text:
        return 0
    return sum(text.count(s) for s in substrings)


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


# ---------- 维度 1: information_density ----------

def score_information_density(node: dict[str, Any]) -> RubricScore:
    """信息密度评分.

    启发式公式：
        base = (narration 字数 / 50) * 0.5 + len(options) * 1.0 + 引号段数 * 1.0
        score = clamp(base, 0, 10)

    - narration 字数：每 50 字 +0.5 分
    - options 数量：每个 +1 分（每个选项是一份信息分支）
    - NPC 引号段数：每段 +1 分（NPC 直接说话比旁白转述信息密度更高）
    """
    narration = node.get("narration", "") or ""
    options = node.get("options", []) or []
    char_count = _count_chinese_chars(narration)
    option_count = len(options)
    quote_count = len(re.findall(r"[「\"“][^「」\"“”]+[」\"”]", narration))

    base = (char_count / 50.0) * 0.5 + option_count * 1.0 + quote_count * 1.0
    score = _clamp(base)

    return RubricScore(
        dimension="information_density",
        score=score,
        trace={
            "narration_char_count": char_count,
            "option_count": option_count,
            "quote_count": quote_count,
            "formula": "(chars/50)*0.5 + options*1.0 + quotes*1.0",
            "raw_base_before_clamp": round(base, 2),
        },
    )


# ---------- 维度 2: baimiao_compliance ----------

def score_baimiao_compliance(node: dict[str, Any]) -> RubricScore:
    """白描合规度评分.

    启发式公式：
        violation_density = (评价词数 + 比喻词数) / (narration 字数 / 100)
        score = clamp(10 - violation_density * 2)

    - 每 100 字内每 1 个违规词扣 2 分
    - 0 违规 = 10.0
    - 5 违规 / 100 字 = 0.0（已 clamp）

    narration 太短（< 30 字）无法判断 → 返回中性 5.0 + warning trace.
    """
    narration = node.get("narration", "") or ""
    char_count = _count_chinese_chars(narration)

    if char_count < 30:
        return RubricScore(
            dimension="baimiao_compliance",
            score=5.0,
            trace={
                "narration_char_count": char_count,
                "warning": "narration 字数 < 30，样本太小无法可靠评估白描合规度",
            },
        )

    eval_count = _count_substring_occurrences(narration, _EVALUATION_WORDS)
    fig_count = _count_substring_occurrences(narration, _FIGURATIVE_WORDS)
    violation_count = eval_count + fig_count
    violation_density = violation_count / (char_count / 100.0)
    score = _clamp(10.0 - violation_density * 2.0)

    return RubricScore(
        dimension="baimiao_compliance",
        score=score,
        trace={
            "narration_char_count": char_count,
            "evaluation_word_count": eval_count,
            "figurative_word_count": fig_count,
            "violation_density_per_100_chars": round(violation_density, 2),
            "formula": "10 - (eval+figurative)/(chars/100) * 2",
        },
    )


# ---------- 主入口 ----------

def score_node(node: dict[str, Any]) -> dict[str, RubricScore]:
    """跑全部 rubric 维度，返回 dict[dimension_name -> RubricScore]."""
    return {
        "information_density": score_information_density(node),
        "baimiao_compliance": score_baimiao_compliance(node),
    }


__all__ = [
    "RubricScore",
    "score_information_density",
    "score_baimiao_compliance",
    "score_node",
]
