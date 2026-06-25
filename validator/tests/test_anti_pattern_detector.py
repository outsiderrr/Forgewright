"""T-3Y-1 子 goal 2: anti_pattern_detector 单元测试.

覆盖：
  - AP-7 narration 转述模式 flag（含 / 不含 / 引号紧接豁免）
  - AP-8 option 第三人称动词 flag（含 / 不含 / [skill] 前缀剥离 / 引号开头豁免 / 第一人称豁免）
  - AP-10 引号内单字代称 flag（含 / 不含）
  - detect_anti_patterns 集成 + LLM_AS_JUDGE_PENDING 清单（7 条非程序化标记）
"""
from __future__ import annotations

from validator.anti_pattern_detector import (
    AntiPatternFlag,
    LLM_AS_JUDGE_PENDING,
    detect_anti_patterns,
    detect_ap7_narration_steals_npc_speech,
    detect_ap8_option_third_person,
    detect_ap10_npc_self_nickname_in_quote,
)


# ---------- AP-7 ----------


def test_ap7_flags_third_person_transcription() -> None:
    """narration 含「她说莱特……」不接引号 → flag."""
    narration = "她进来时神色慌张。她说莱特在人前是教授，人后是另一种人。"
    flags = detect_ap7_narration_steals_npc_speech(narration)
    assert len(flags) >= 1
    assert flags[0].ap_id == "AP-7"
    assert "她说" in flags[0].excerpt or "她说" in flags[0].reason


def test_ap7_flags_he_says_pattern() -> None:
    flags = detect_ap7_narration_steals_npc_speech("他告诉你他害怕维克。")
    assert any(f.ap_id == "AP-7" for f in flags)


def test_ap7_exempts_when_followed_by_colon_and_quote() -> None:
    """「她说：「莱特死了」」是正常引用模式，不 flag."""
    narration = "她抬头看你。她说：「莱特死了。」"
    flags = detect_ap7_narration_steals_npc_speech(narration)
    assert flags == []


def test_ap7_exempts_when_followed_by_chinese_quote() -> None:
    """「她说「莱特死了」」也是正常引用模式（无冒号，但有引号紧接）."""
    narration = "她抬头。她说「莱特死了」就低下头。"
    flags = detect_ap7_narration_steals_npc_speech(narration)
    assert flags == []


def test_ap7_no_flags_for_clean_narration() -> None:
    """纯物理描写无任何转述 → 无 flag."""
    narration = "你推开门走进酒馆，灯光昏黄。露西站在柜台后擦拭一只玻璃杯。"
    assert detect_ap7_narration_steals_npc_speech(narration) == []


def test_ap7_empty_narration_returns_empty() -> None:
    assert detect_ap7_narration_steals_npc_speech("") == []


# ---- 2026-06-10 误报修复（结构层复核实证三种误报型；作者授权）----


def test_ap7_exempts_comma_attribution() -> None:
    """「…」她说，「…」是引语归属不是转述 → 不 flag."""
    narration = "「不在主路旁。」她说，「从酒馆后方那条土路绕过去。」"
    assert detect_ap7_narration_steals_npc_speech(narration) == []


def test_ap7_exempts_speaking_as_physical_action() -> None:
    """"她说话时没有抬头" 是言说动作的物理描写不是转述 → 不 flag."""
    assert detect_ap7_narration_steals_npc_speech("她说话时没有抬头，声音被楼下的低音盖住。") == []
    assert detect_ap7_narration_steals_npc_speech("他讲话的间隙，炉火响了一声。") == []


def test_ap7_exempts_transcription_inside_quotes() -> None:
    """引号内对白是 NPC 自己的话（如露西转述莱特），不属于旁白转述 → 不 flag."""
    narration = "露西压低声音。\n\n「他说，屋子外面只有二十步宽，里面量出来却多了四步。」"
    assert detect_ap7_narration_steals_npc_speech(narration) == []


def test_ap7_still_flags_transcription_outside_quotes() -> None:
    """引号外的真转述仍要抓（召回不降级）."""
    narration = "她说莱特怕的不是打手。「坐下。」她指了指椅子。"
    flags = detect_ap7_narration_steals_npc_speech(narration)
    assert any(f.ap_id == "AP-7" for f in flags)


# ---------- AP-8 ----------


def test_ap8_flags_third_person_verb_prefix() -> None:
    options = [
        {"option_id": "opt_a", "text": "追问那个大学生：给我名字或住址"},
    ]
    flags = detect_ap8_option_third_person(options)
    assert len(flags) == 1
    assert flags[0].ap_id == "AP-8"
    assert "options[0]" in flags[0].location
    assert "追问" in flags[0].reason


def test_ap8_flags_先_prefix() -> None:
    """A1 §2 AP-8 明示「先追问 / 先把」属第三人称意图描述."""
    options = [
        {"option_id": "opt_a", "text": "先追问赌债和维克名片，把浅层线索坐实"},
    ]
    flags = detect_ap8_option_third_person(options)
    assert len(flags) == 1


def test_ap8_strips_skill_prefix_then_checks() -> None:
    """[skill_name] 前缀剥离后检查主体."""
    options = [
        {"option_id": "opt_a", "text": "[观察入微] 追问赌债"},
    ]
    flags = detect_ap8_option_third_person(options)
    assert len(flags) == 1
    assert flags[0].ap_id == "AP-8"


def test_ap8_exempts_first_person_我_prefix() -> None:
    options = [
        {"option_id": "opt_a", "text": "我不是来审你。我想知道他怎么死的。"},
    ]
    assert detect_ap8_option_third_person(options) == []


def test_ap8_exempts_quote_prefix() -> None:
    """引号开头（直接对白）豁免."""
    options = [
        {"option_id": "opt_a", "text": "「教授的朋友可真多。」"},
    ]
    assert detect_ap8_option_third_person(options) == []


def test_ap8_exempts_你_prefix() -> None:
    """你... 视角（自言自语 / 反诘）豁免."""
    options = [
        {"option_id": "opt_a", "text": "你别摆那副法官脸——我只是想说话。"},
    ]
    assert detect_ap8_option_third_person(options) == []


def test_ap8_with_skill_prefix_first_person_body_ok() -> None:
    """[skill_name] + 第一人称主体 → 不 flag (A1 §3.3.2 正例)."""
    options = [
        {"option_id": "opt_a", "text": "[观察入微] 我先把酒馆里不喝酒的人记下来"},
    ]
    assert detect_ap8_option_third_person(options) == []


def test_ap8_multiple_options_independent_flags() -> None:
    options = [
        {"option_id": "opt_a", "text": "我直接问她。"},
        {"option_id": "opt_b", "text": "追问那个大学生"},
        {"option_id": "opt_c", "text": "[心理学] 共情她的处境"},
    ]
    flags = detect_ap8_option_third_person(options)
    flagged_locs = {f.location for f in flags}
    assert "options[1].text" in flagged_locs
    assert "options[2].text" in flagged_locs
    assert "options[0].text" not in flagged_locs


def test_ap8_empty_options() -> None:
    assert detect_ap8_option_third_person([]) == []


# ---------- AP-10 ----------


def test_ap10_flags_女孩_self_reference_in_quote() -> None:
    """A1 §4.1.5 反例：「女孩也得活下去，你别摆那副法官脸」."""
    narration = "露西摇头。「女孩也得活下去，你别摆那副法官脸。」她低声说。"
    flags = detect_ap10_npc_self_nickname_in_quote(narration)
    assert len(flags) == 1
    assert flags[0].ap_id == "AP-10"
    assert "女孩" in flags[0].reason


def test_ap10_flags_老娘_in_quote() -> None:
    narration = '她摇头。"老娘可没那个胆子。"'
    flags = detect_ap10_npc_self_nickname_in_quote(narration)
    assert len(flags) == 1


def test_ap10_no_flag_outside_quotes() -> None:
    """女孩出现在旁白外（非引号内）不 flag——只检测引号内 NPC 自称."""
    narration = "那个女孩走过来，看了你一眼。"
    flags = detect_ap10_npc_self_nickname_in_quote(narration)
    assert flags == []


def test_ap10_no_flag_with_clean_self_reference() -> None:
    """正常用「我」自称 → 不 flag."""
    narration = "露西摇头。「我也得活下去，你别摆那副法官脸。」她低声说。"
    flags = detect_ap10_npc_self_nickname_in_quote(narration)
    assert flags == []


def test_ap10_flags_in_options_quoted_text() -> None:
    """options[].text 引号内也检查."""
    options = [{"option_id": "opt", "text": "「女孩说错话了——别太当回事。」"}]
    flags = detect_ap10_npc_self_nickname_in_quote("", options)
    assert len(flags) == 1
    assert "options[0]" in flags[0].location


def test_ap10_flags_self_nickname_in_dialogue_line() -> None:
    """ADR-040：对白移进 dialogue[].line（裸正文，无「」）后，AP-10 须直接扫整行."""
    dialogue = [
        {"speaker_ref": "char_lucy", "line": "你听着。"},
        {"speaker_ref": "char_lucy", "line": "老娘可没那个胆子。"},
    ]
    flags = detect_ap10_npc_self_nickname_in_quote("", None, dialogue)
    assert len(flags) == 1
    assert flags[0].ap_id == "AP-10"
    assert "老娘" in flags[0].reason
    assert "dialogue[1].line" in flags[0].location


def test_ap10_no_flag_clean_dialogue_line() -> None:
    """dialogue[].line 用「我」自称 → 不 flag."""
    dialogue = [{"speaker_ref": "char_lucy", "line": "我可没那个胆子。"}]
    flags = detect_ap10_npc_self_nickname_in_quote("", None, dialogue)
    assert flags == []


# ---------- detect_anti_patterns 集成 ----------


def test_detect_all_scans_dialogue_line_for_ap10() -> None:
    """ADR-040 集成：detect_anti_patterns 对结构化 dialogue[].line 也跑 AP-10."""
    node = {
        "node_id": "node_split",
        "narration": "她把杯子推过来。",
        "speaker_ref": None,
        "dialogue": [{"speaker_ref": "char_lucy", "line": "女孩也得活下去。"}],
        "options": [{"option_id": "opt", "text": "我点头。"}],
    }
    flags = detect_anti_patterns(node)
    ap10 = [f for f in flags if f.ap_id == "AP-10"]
    assert len(ap10) == 1
    assert "dialogue[0].line" in ap10[0].location


# ---------- detect_anti_patterns 集成（原有） ----------


def test_detect_all_returns_flags_for_3_violation_node() -> None:
    """构造一个同时违反 AP-7 + AP-8 + AP-10 的 node，检测器应给出 3+ flag."""
    node = {
        "node_id": "node_bad",
        "narration": "她说莱特死得不简单。「女孩也是受害者。」她又低声说。",
        "speaker_ref": "char_lucy",
        "options": [
            {"option_id": "opt_a", "text": "追问那个大学生"},
            {"option_id": "opt_b", "text": "我先听她说完。"},
        ],
    }
    flags = detect_anti_patterns(node)
    flagged_ids = {f.ap_id for f in flags}
    assert "AP-7" in flagged_ids
    assert "AP-8" in flagged_ids
    assert "AP-10" in flagged_ids


def test_detect_all_clean_node_returns_empty() -> None:
    """合规节点 → 无 flag."""
    node = {
        "node_id": "node_clean",
        "narration": "你推开门走进酒馆。露西站在柜台后擦拭杯子，抬头看你一眼。",
        "speaker_ref": "char_lucy",
        "options": [
            {"option_id": "opt_a", "text": "我点了杯威士忌坐下。"},
            {"option_id": "opt_b", "text": "「教授的朋友可真多。」"},
        ],
    }
    assert detect_anti_patterns(node) == []


def test_detect_handles_missing_fields() -> None:
    """node 缺字段时不抛异常."""
    assert detect_anti_patterns({}) == []


def test_llm_as_judge_pending_contains_7_aps() -> None:
    """LLM_AS_JUDGE_PENDING 必须含 AP-1/2/3/4/5/6/9（7 条非程序化）."""
    assert set(LLM_AS_JUDGE_PENDING) == {
        "AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9"
    }
    assert "AP-7" not in LLM_AS_JUDGE_PENDING
    assert "AP-8" not in LLM_AS_JUDGE_PENDING
    assert "AP-10" not in LLM_AS_JUDGE_PENDING


def test_flag_dataclass_serializable_shape() -> None:
    """AntiPatternFlag 含 ap_id / location / excerpt / reason 四字段."""
    f = AntiPatternFlag(ap_id="AP-8", location="options[0].text", excerpt="X", reason="Y")
    assert f.ap_id == "AP-8"
    assert f.location == "options[0].text"
    assert f.excerpt == "X"
    assert f.reason == "Y"
