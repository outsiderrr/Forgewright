"""文风层装配单测（不调 LLM）—— 锚点库 / 预设分层 / 注入开关.

对应设计：generator/experiments/aesthetic_layer/DESIGN_2026-06-12_phase2_style_layer.md
（作者拍板 2026-06-12 决策 A/B/C/D）。
"""
from __future__ import annotations

import pytest

from generator.prompts.node.anti_pattern_blacklist import (
    ANTI_PATTERN_BLACKLIST_TEXT,
    AP_TEXTS,
    BAIMIAO_PRESET_AP_IDS,
    UNIVERSAL_AP_IDS,
    preset_ap_block,
    universal_ap_block,
)
from generator.prompts.style import (
    ANCHORS_ENV_VAR,
    anchors_enabled,
    load_anchors,
    style_anchor_block,
    style_rules_block,
)
from generator.prompts.style.presets import PRESETS

# ---- 锚点库 v1（决策 C：A1-A18 全批）----


def test_anchor_library_v1_complete_and_clean() -> None:
    anchors = load_anchors()
    assert set(anchors) == {f"A{i}" for i in range(1, 19)}, "锚点库 v1 = 作者批准的 A1-A18"
    for a in anchors.values():
        assert a["role"] in {"narration", "npc_dialogue", "player_option"}
        assert a["text"].strip()
        assert a["source"].startswith("generator/experiments/"), "来源必须是项目自产文本"
        # 版权红线：只收项目自产已接受文本
        assert a["license_origin"] == "project_generated"


def test_anchor_plan_only_references_existing_anchors() -> None:
    anchors = load_anchors()
    for preset in PRESETS.values():
        for call_type, plan in preset.ANCHOR_PLAN.items():
            for role, ids in plan.items():
                for i in ids:
                    assert i in anchors, f"{preset.NAME}/{call_type}/{role} 引用了不存在的锚点 {i}"
                    assert anchors[i]["role"] == role, f"{i} 的角色与 ANCHOR_PLAN 归类不一致"


# ---- 规则分层（决策 B：8 普适 + AP-1/AP-5 归白描预设）----


def test_universal_block_carries_exactly_the_universal_aps() -> None:
    block = universal_ap_block()
    for ap in UNIVERSAL_AP_IDS:
        assert f"### {ap}:" in block
    for ap in BAIMIAO_PRESET_AP_IDS:
        assert f"### {ap}:" not in block, f"{ap} 是预设条款，不得进普适层"
    for ap in ("AP-7", "AP-8", "AP-10"):
        assert f"### {ap}:" not in block, f"{ap} 已程序化检测，不进任何生成 prompt"


def test_baimiao_preset_carries_ap1_ap5_and_prose_rules() -> None:
    block = style_rules_block("baimiao")
    assert "### AP-1:" in block and "### AP-5:" in block
    assert "白描" in block
    for ap in UNIVERSAL_AP_IDS:
        assert f"### {ap}:" not in block, "普适条款不进预设块（避免重复注入）"


def test_legacy_blacklist_text_unchanged_in_coverage() -> None:
    # 单 pass 旧路径（system.py）仍用 7 条合体，覆盖面不变
    for n in (1, 2, 3, 4, 5, 6, 9):
        assert f"### AP-{n}:" in ANTI_PATTERN_BLACKLIST_TEXT
    for n in (7, 8, 10):
        assert f"### AP-{n}:" not in ANTI_PATTERN_BLACKLIST_TEXT
    assert "程序化检测" in ANTI_PATTERN_BLACKLIST_TEXT
    assert set(AP_TEXTS) == {"AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9"}
    assert preset_ap_block(()) == ""


# ---- 锚点注入（按需注入 + 防搬运 + 开关）----


def test_anchor_block_per_call_type_selects_right_roles() -> None:
    opening = style_anchor_block("pass2_opening")
    assert "办公室贴着冷藏库的外墙" in opening  # A1 开场旁白
    assert "希博公路酒馆" in opening  # A2 开场旁白
    assert "我不是来审你" in opening  # A16 choice 选项
    assert "记下路标" not in opening  # A15 是 beat 接话锚点，不进 choice 调用

    beats = style_anchor_block("beats")
    assert "杯沿在木桌上留下一圈湿痕" in beats  # A3 节拍旁白
    assert "你为什么这么着急？" in beats  # A13 接话
    assert "办公室贴着冷藏库的外墙" not in beats  # 开场全景不进节拍调用

    end = style_anchor_block("end")
    assert "你把第七码碑" in end  # A5 收束旁白
    assert "别在走廊里提我的名字" in end  # A12 收尾对白
    assert "玩家选项该写成这样" not in end  # end 无选项锚点

    assert style_anchor_block("unknown_call_type") == ""


def test_anchor_block_carries_anti_copy_guard() -> None:
    for ct in ("pass2_opening", "pass2_mid", "beats", "end"):
        block = style_anchor_block(ct)
        assert "一律不得出现在你的输出里" in block, f"{ct} 锚点块必须带防搬运守则"
        assert "只学质感" in block


def test_anchor_switch_off_disables_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ANCHORS_ENV_VAR, "off")
    assert not anchors_enabled()
    assert style_anchor_block("pass2_opening") == ""
    monkeypatch.setenv(ANCHORS_ENV_VAR, "on")
    assert anchors_enabled()
    assert style_anchor_block("pass2_opening") != ""


def test_anchor_switch_does_not_touch_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ANCHORS_ENV_VAR, "off")
    block = style_rules_block("baimiao")
    assert "### AP-1:" in block and "白描" in block, "规则段不受锚点开关影响（A/B 两臂规则一致）"


# ---- 注入进生成 user prompt（pass2 / beats / end）----


def test_pass2_user_prompt_injects_anchors_by_scene_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from generator.prompts.node.multipass.pass2_prose import build_pass2_user_prompt

    sk = {"node_id": "n", "function": "f", "options": [{"intent": "I"}]}
    kwargs = dict(
        scene_contract={}, node_skeleton=sk, revealed_clues=[], used_option_intents=[]
    )
    u_open = build_pass2_user_prompt(**kwargs, mid_scene=False)
    assert "办公室贴着冷藏库的外墙" in u_open  # 开场锚点
    u_mid = build_pass2_user_prompt(**kwargs, mid_scene=True)
    assert "办公室贴着冷藏库的外墙" not in u_mid
    assert "杯沿在木桌上留下一圈湿痕" in u_mid  # 中段锚点

    monkeypatch.setenv(ANCHORS_ENV_VAR, "off")
    u_off = build_pass2_user_prompt(**kwargs, mid_scene=False)
    assert "文风锚点" not in u_off


def test_beats_and_end_user_prompts_inject_anchors(monkeypatch: pytest.MonkeyPatch) -> None:
    from generator.prompts.node.multipass.beat_pacing import build_beat_pacing_user_prompt
    from generator.prompts.node.multipass.pass2_prose import build_end_prose_user_prompt

    ub = build_beat_pacing_user_prompt(
        scene_contract={}, node_situation="SIT", reveals=["R1"]
    )
    assert "你为什么这么着急？" in ub
    ue = build_end_prose_user_prompt(scene_contract={}, node_function="F", path_summary="P")
    assert "你把第七码碑" in ue

    monkeypatch.setenv(ANCHORS_ENV_VAR, "off")
    assert "文风锚点" not in build_beat_pacing_user_prompt(
        scene_contract={}, node_situation="SIT", reveals=["R1"]
    )
    assert "文风锚点" not in build_end_prose_user_prompt(
        scene_contract={}, node_function="F", path_summary="P"
    )


def test_decision_d_two_conventions_documented_in_pass2_system() -> None:
    from generator.prompts.node.multipass.pass2_prose import PASS2_PROSE_SYSTEM

    assert "选择节点的选项可用\"我\"开头" in PASS2_PROSE_SYSTEM
    assert "不硬塞" in PASS2_PROSE_SYSTEM


def test_anchor_block_token_increment_within_budget() -> None:
    """锚点注入的 prompt 增量护栏（设计 §3：单调用 ≲ 350-900 汉字）。"""
    sizes = {ct: len(style_anchor_block(ct)) for ct in ("pass2_opening", "pass2_mid", "beats", "end")}
    assert all(s > 0 for s in sizes.values())
    assert sizes["pass2_opening"] <= 1200, sizes  # 两段开场全景较大，给上限护栏
    assert sizes["pass2_mid"] <= 700, sizes
    assert sizes["beats"] <= 700, sizes
    assert sizes["end"] <= 900, sizes
