"""T-3Y-1 子 goal 2: /generator/prompts/node/ 单元测试.

覆盖：
  - role_rules 文本含 3 分类关键词
  - anti_pattern_blacklist 文本含 10 条 AP-1 ~ AP-10
  - system.NODE_SYSTEM_PROMPT 是 3 段拼接（CORE_INTRO + ROLE_RULES + AP_BLACKLIST + OUTPUT_FORMAT）
  - fill.build_node_user_message 渲染 6 段（known_info / foreground_goal / background_seeds / npc_state / skeleton / 任务说明）
"""
from __future__ import annotations

from generator.prompts.node.anti_pattern_blacklist import ANTI_PATTERN_BLACKLIST_TEXT
from generator.prompts.node.fill import (
    build_node_user_message,
    render_background_seeds,
    render_foreground_goal,
    render_npc_state,
    render_player_known_info,
)
from generator.prompts.node.role_rules import ROLE_RULES_TEXT
from generator.prompts.node.system import (
    CORE_INTRO,
    NODE_SYSTEM_PROMPT,
    OUTPUT_FORMAT_SPEC,
    build_node_system_prompt,
)


# ---------- role_rules ----------


def test_role_rules_covers_three_categories() -> None:
    """3 分类角色守则文本含旁白 / NPC / 玩家 三段."""
    assert "旁白" in ROLE_RULES_TEXT
    assert "NPC" in ROLE_RULES_TEXT
    assert "玩家" in ROLE_RULES_TEXT


def test_role_rules_mentions_first_person_for_options() -> None:
    """玩家选项必须第一人称——关键约束."""
    assert "第一人称" in ROLE_RULES_TEXT


def test_role_rules_forbids_narration_stealing_npc_speech() -> None:
    """旁白契约禁止抢 NPC 台词（AP-7 防御）."""
    assert "NPC" in ROLE_RULES_TEXT and ("自己说" in ROLE_RULES_TEXT or "NPC 要传达的内容" in ROLE_RULES_TEXT or "由 NPC 自己说出来" in ROLE_RULES_TEXT)


# ---------- anti_pattern_blacklist ----------


def test_anti_pattern_blacklist_lists_all_10() -> None:
    """anti-pattern 文本必须含 AP-1 ~ AP-10 全部 10 个标题."""
    for i in range(1, 11):
        assert f"AP-{i}:" in ANTI_PATTERN_BLACKLIST_TEXT, f"missing AP-{i}"


def test_anti_pattern_blacklist_marks_programmatic_ones() -> None:
    """AP-7 / AP-8 / AP-10 标【程序化检测】."""
    assert "AP-7: 旁白抢 NPC 的台词【程序化检测】" in ANTI_PATTERN_BLACKLIST_TEXT
    assert "AP-8: 选项第三人称化【程序化检测】" in ANTI_PATTERN_BLACKLIST_TEXT
    assert "AP-10: 指代不清 / 用单字代称自己【程序化检测】" in ANTI_PATTERN_BLACKLIST_TEXT


# ---------- system.NODE_SYSTEM_PROMPT ----------


def test_system_prompt_contains_4_sections() -> None:
    """NODE_SYSTEM_PROMPT = CORE_INTRO + ROLE_RULES + AP_BLACKLIST + OUTPUT_FORMAT."""
    p = NODE_SYSTEM_PROMPT
    assert "节点级**对话生成器" in p  # CORE_INTRO
    assert "3 分类角色守则" in p       # ROLE_RULES_TEXT
    assert "AP-1" in p and "AP-10" in p  # ANTI_PATTERN_BLACKLIST
    assert "输出字段语义" in p          # OUTPUT_FORMAT_SPEC


def test_system_prompt_is_deterministic_assembly() -> None:
    """build_node_system_prompt() 多次调用结果一致 + 含全部 4 段."""
    p1 = build_node_system_prompt()
    p2 = build_node_system_prompt()
    assert p1 == p2 == NODE_SYSTEM_PROMPT


def test_system_prompt_enforces_json_only() -> None:
    """JSON-only 硬约束必须在 prompt 内."""
    assert "JSON-only" in NODE_SYSTEM_PROMPT
    assert "markdown" in NODE_SYSTEM_PROMPT


def test_system_prompt_constrains_narration_length() -> None:
    """narration 字数约束 (150 ~ 400) 必须在 prompt."""
    assert "150" in OUTPUT_FORMAT_SPEC and "400" in OUTPUT_FORMAT_SPEC


def test_system_prompt_constrains_option_text_length() -> None:
    """option.text ≤ 25 汉字约束必须在 prompt."""
    assert "25" in OUTPUT_FORMAT_SPEC


# ---------- fill.build_node_user_message ----------


def test_render_player_known_info_with_items() -> None:
    items = [
        {"knowledge_path": "knowledge.wright_dead", "stage": 1},
        {"knowledge_path": "knowledge.lucy_known_to_player"},
    ]
    block = render_player_known_info(items, all_known_info_summary="测试摘要")
    assert "knowledge.wright_dead" in block
    assert "knowledge.lucy_known_to_player" in block
    assert "阶段 1" in block
    assert "测试摘要" in block
    assert "已经知道以上信息" in block


def test_render_player_known_info_empty() -> None:
    block = render_player_known_info([])
    assert "玩家暂无已知信息" in block


def test_render_foreground_goal_with_value() -> None:
    block = render_foreground_goal("r1_wright_double_life.stage_2")
    assert "r1_wright_double_life.stage_2" in block
    assert "围绕" in block


def test_render_foreground_goal_none() -> None:
    block = render_foreground_goal(None)
    assert "无指定 foreground_goal" in block


def test_render_background_seeds_with_values() -> None:
    block = render_background_seeds(["S2_vick_dangerous", "S4_country_cottage_cache"])
    assert "S2_vick_dangerous" in block
    assert "S4_country_cottage_cache" in block
    assert "含蓄但有信息量" in block


def test_render_background_seeds_empty() -> None:
    block = render_background_seeds([])
    assert "不埋任何种子" in block


def test_render_npc_state_with_speaker() -> None:
    block = render_npc_state("char_lucy", {"trust": 1, "fear": 2})
    assert "char_lucy" in block
    assert "trust" in block and "fear" in block


def test_render_npc_state_null_speaker_is_narration_only() -> None:
    block = render_npc_state(None, None)
    assert "无 NPC 主讲" in block


def test_build_user_message_includes_all_sections() -> None:
    skeleton = {
        "node_id": "node_3_info_offer",
        "type": "dialogue",
        "speaker_ref": "char_lucy",
        "options": [],
    }
    user = build_node_user_message(
        node_skeleton=skeleton,
        player_known_info=[
            {"knowledge_path": "knowledge.wright_dead", "stage": 1},
        ],
        foreground_goal="r1_wright_double_life.stage_2",
        background_seeds=["S2_vick_dangerous"],
        npc_state={"trust": 1},
    )
    # 6 段分隔
    assert user.count("---") >= 5
    # 关键字段全部出现
    assert "knowledge.wright_dead" in user
    assert "r1_wright_double_life.stage_2" in user
    assert "S2_vick_dangerous" in user
    assert "char_lucy" in user
    assert "node_3_info_offer" in user
    assert "任务" in user
