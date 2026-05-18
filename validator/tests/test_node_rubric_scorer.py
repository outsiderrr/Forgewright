"""T-3Y-1 子 goal 2: node_rubric_scorer 单元测试.

覆盖：
  - score_information_density：高密度 / 低密度 / clamp / trace
  - score_baimiao_compliance：合规 / 评价词违规 / 比喻词违规 / clamp / 短文本中性 / trace
  - score_node 集成：返回 dict 含两维度 + 每维度 [0, 10] 范围
"""
from __future__ import annotations

from validator.node_rubric_scorer import (
    RubricScore,
    score_baimiao_compliance,
    score_information_density,
    score_node,
)


# ---------- score_information_density ----------


def test_information_density_high_for_rich_node() -> None:
    """长 narration + 多 options + 多 quotes → 高分."""
    node = {
        "narration": "你推开酒馆的门。" + "字数填充" * 30,  # ~60+ 汉字
        "options": [
            {"option_id": "opt_1", "text": "我点酒。"},
            {"option_id": "opt_2", "text": "「教授的朋友可真多。」"},
            {"option_id": "opt_3", "text": "我转身离开。"},
        ],
    }
    result = score_information_density(node)
    assert isinstance(result, RubricScore)
    assert result.dimension == "information_density"
    assert result.score > 0
    assert result.score <= 10.0
    assert "narration_char_count" in result.trace
    assert "option_count" in result.trace
    assert result.trace["option_count"] == 3


def test_information_density_low_for_empty_node() -> None:
    node = {"narration": "", "options": []}
    result = score_information_density(node)
    assert result.score == 0.0
    assert result.trace["narration_char_count"] == 0
    assert result.trace["option_count"] == 0


def test_information_density_clamped_at_10() -> None:
    """极端 rich node 不应超过 10."""
    node = {
        "narration": "字" * 2000,  # 巨长
        "options": [{"option_id": f"opt_{i}", "text": "「..."} for i in range(20)],
    }
    result = score_information_density(node)
    assert result.score == 10.0


def test_information_density_counts_quotes_in_narration() -> None:
    """narration 中引号段加分."""
    node = {
        "narration": "「教授的朋友可真多。」她低声说。" * 3,
        "options": [],
    }
    result = score_information_density(node)
    assert result.trace["quote_count"] >= 3


def test_information_density_trace_has_formula() -> None:
    node = {"narration": "测试", "options": []}
    result = score_information_density(node)
    assert "formula" in result.trace


# ---------- score_baimiao_compliance ----------


def test_baimiao_compliance_high_for_clean_narration() -> None:
    """纯物理白描无评价词 / 比喻词 → 高分."""
    node = {
        "narration": (
            "你推开酒馆的门走进去。露西站在柜台后擦拭一只玻璃杯，"
            "抬头看你一眼。她把杯子放下，转身去后厨。"
            "酒馆里有六张桌子，三张已经坐了人。"
            "墙上的钟指向七点四十五分。"
        ),
    }
    result = score_baimiao_compliance(node)
    assert result.dimension == "baimiao_compliance"
    assert result.score >= 8.0  # 合规度高
    assert result.trace["evaluation_word_count"] == 0
    assert result.trace["figurative_word_count"] == 0


def test_baimiao_compliance_low_for_evaluation_heavy() -> None:
    """评价词密集 → 低分."""
    node = {
        "narration": (
            "她显然有些紧张，似乎在隐藏什么。她大约二十五岁，"
            "看起来明显比同龄人老练。她的眼神好像在评估你，"
            "或许是想确定你是不是警察。总之她保持着距离。"
            "她的表情仿佛刚刚经历过什么。可能是因为莱特的事。"
        ),
    }
    result = score_baimiao_compliance(node)
    assert result.score < 5.0
    assert result.trace["evaluation_word_count"] >= 5


def test_baimiao_compliance_low_for_figurative_heavy() -> None:
    """比喻词密集 → 低分."""
    node = {
        "narration": (
            "她的眼神像刀子一样锋利。她的笑容如同假面具。"
            "她的动作好比舞台演员。她的话语犹如冰水般冷。"
            "她的姿态宛如雕像。她的声音像风一般轻。"
        ),
    }
    result = score_baimiao_compliance(node)
    assert result.score < 5.0
    assert result.trace["figurative_word_count"] >= 4


def test_baimiao_compliance_clamped_at_0() -> None:
    """极端违规不应低于 0."""
    node = {
        "narration": "显然似乎大约看起来好像彷佛仿佛宛如犹如" * 5,
    }
    result = score_baimiao_compliance(node)
    assert result.score == 0.0


def test_baimiao_compliance_neutral_for_short_narration() -> None:
    """narration 太短（<30 字）返回 5.0 + warning."""
    node = {"narration": "短文本。"}
    result = score_baimiao_compliance(node)
    assert result.score == 5.0
    assert "warning" in result.trace


def test_baimiao_compliance_trace_includes_density() -> None:
    node = {
        "narration": "你推开门走进酒馆。露西站在柜台后擦拭玻璃杯，抬头看你一眼。她把杯子放下转身去后厨。"
    }
    result = score_baimiao_compliance(node)
    assert "violation_density_per_100_chars" in result.trace
    assert "formula" in result.trace


# ---------- score_node 集成 ----------


def test_score_node_returns_both_dimensions() -> None:
    node = {
        "narration": "你推开酒馆的门走进去。露西站在柜台后擦拭一只玻璃杯，抬头看你一眼。",
        "options": [
            {"option_id": "opt_1", "text": "我点酒坐下。"},
            {"option_id": "opt_2", "text": "我转身离开。"},
        ],
    }
    result = score_node(node)
    assert set(result.keys()) == {"information_density", "baimiao_compliance"}
    for dim, score in result.items():
        assert isinstance(score, RubricScore)
        assert score.dimension == dim
        assert 0.0 <= score.score <= 10.0


def test_score_node_handles_missing_fields() -> None:
    """node 缺 narration / options 不抛异常."""
    result = score_node({})
    assert "information_density" in result
    assert "baimiao_compliance" in result
    assert result["information_density"].score == 0.0


def test_rubric_score_dataclass_shape() -> None:
    s = RubricScore(dimension="x", score=7.5, trace={"k": "v"})
    assert s.dimension == "x"
    assert s.score == 7.5
    assert s.trace == {"k": "v"}
