"""多 pass prompt 模块单测——验证"瘦身"假设落地 + builder/schema 结构.

不调 LLM、不花预算；纯 prompt 装配逻辑（提交前 pytest 必过）。
"""
from __future__ import annotations

from generator.prompts.node.multipass import (
    NODE_FUNCTIONS,
    PASS1_SKELETON_SYSTEM,
    PASS2_PROSE_SYSTEM,
    SLIMMED_AP_KEEP,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass1_node_schema,
    build_pass1_node_user_prompt,
    build_pass1_schema,
    build_pass1_user_prompt,
    build_pass2_schema,
    build_pass2_user_prompt,
    slimmed_anti_patterns,
)

_SPEC = {
    "background": "BG_MARKER",
    "design_goal": "GOAL_MARKER",
    "character_state": "STATE_MARKER",
    "required_clues": ["REQ1"],
    "optional_clues": ["OPT1"],
    "forbidden_events": ["FORBID1"],
}


def test_slimmed_keep_set_is_1_to_6_and_9() -> None:
    assert SLIMMED_AP_KEEP == frozenset({1, 2, 3, 4, 5, 6, 9})


def test_slimmed_keeps_only_target_aps() -> None:
    s = slimmed_anti_patterns()
    for n in (1, 2, 3, 4, 5, 6, 9):
        assert f"### AP-{n}:" in s, f"AP-{n} 应保留"
    for n in (7, 8, 10):
        assert f"### AP-{n}:" not in s, f"AP-{n} 应被瘦身掉（validator 程序化抓）"


def test_pass1_carries_structure_rules_and_no_anti_pattern_block() -> None:
    # 结构层 prompt 不带任何 AP 黑名单
    assert "### AP-" not in PASS1_SKELETON_SYSTEM
    assert "黑名单" not in PASS1_SKELETON_SYSTEM
    # 但必须带"节点功能分化"这一核心结构规则 + 4 节点定义
    assert "节点功能必须分化" in PASS1_SKELETON_SYSTEM
    assert "N1 shared opening" in PASS1_SKELETON_SYSTEM
    assert "N2 hub" in PASS1_SKELETON_SYSTEM
    assert "choice pressure" in PASS1_SKELETON_SYSTEM.lower()


def test_pass2_carries_slimmed_aps_plus_role_rules() -> None:
    for n in (1, 2, 3, 4, 5, 6, 9):
        assert f"### AP-{n}:" in PASS2_PROSE_SYSTEM, f"AP-{n} 应保留在 Pass 2"
    for n in (7, 8, 10):
        assert f"### AP-{n}:" not in PASS2_PROSE_SYSTEM, f"AP-{n} 不应出现在 Pass 2"
    # role_rules 三契约保留（结构性"谁说什么"，非文风黑名单）
    assert "3 分类角色守则" in PASS2_PROSE_SYSTEM
    # 历史压缩 + 第一人称选项规则在系统提示里有交代
    assert "历史压缩" in PASS2_PROSE_SYSTEM
    assert "第一人称" in PASS2_PROSE_SYSTEM


def test_pass1_user_prompt_includes_all_scene_fields() -> None:
    spec = {
        "background": "BG_MARKER",
        "design_goal": "GOAL_MARKER",
        "character_state": "STATE_MARKER",
        "required_clues": ["REQ1", "REQ2"],
        "optional_clues": ["OPT1"],
        "forbidden_events": ["FORBID1"],
    }
    u = build_pass1_user_prompt(spec)
    for needle in ("BG_MARKER", "GOAL_MARKER", "STATE_MARKER", "REQ1", "REQ2", "OPT1", "FORBID1"):
        assert needle in u


def test_pass2_user_prompt_injects_history_compression() -> None:
    sc = {"player_goal": "PG", "npc_name": "Lucy"}
    sk = {
        "node_id": "N2",
        "function": "hub",
        "speaker_ref": "Lucy",
        "options": [{"intent": "软问路线"}, {"intent": "高压施压"}],
    }
    u = build_pass2_user_prompt(
        scene_contract=sc,
        node_skeleton=sk,
        revealed_clues=["旧测绘小屋"],
        used_option_intents=["点破角落男人"],
    )
    assert "旧测绘小屋" in u  # 祖先已揭露线索注入
    assert "点破角落男人" in u  # 祖先已用选项角度注入
    assert "软问路线" in u and "高压施压" in u  # 本节点 option intents


def test_pass2_user_prompt_first_node_states_no_history() -> None:
    sk = {"node_id": "N1", "options": []}
    u = build_pass2_user_prompt(
        scene_contract={}, node_skeleton=sk, revealed_clues=[], used_option_intents=[]
    )
    assert "还没揭露任何线索" in u


def test_schemas_shapes() -> None:
    s1 = build_pass1_schema()
    assert s1["required"] == ["scene_contract", "nodes"]
    assert s1["properties"]["nodes"]["minItems"] == 4
    assert s1["properties"]["nodes"]["maxItems"] == 4
    s2 = build_pass2_schema()
    assert s2["required"] == ["narration", "dialogue", "options"]
    assert s2["properties"]["options"]["items"]["required"] == ["intent", "text"]


# ---- 拆细版 Pass 1（契约 + 逐节点骨架）----


def test_node_functions_cover_four_nodes() -> None:
    assert set(NODE_FUNCTIONS) == {"N1", "N2", "N3", "N4"}
    # N1 不得预先泄露；N4 是残缺路径——固定功能里要点明
    assert "不得预先泄露" in NODE_FUNCTIONS["N1"]
    assert "残缺" in NODE_FUNCTIONS["N4"]


def test_pass1_contract_builder_only_contract() -> None:
    u = build_pass1_contract_user_prompt(_SPEC)
    assert "场景契约" in u
    assert "BG_MARKER" in u and "REQ1" in u
    s = build_pass1_contract_schema()
    assert "player_goal" in s["properties"] and "failsafe_path" in s["properties"]
    # 契约 schema 不含 nodes（那是逐节点单独出的）
    assert "nodes" not in s["properties"]


def test_pass1_node_builder_injects_function_and_prior_nodes() -> None:
    u = build_pass1_node_user_prompt(
        scene_spec=_SPEC,
        scene_contract={"player_goal": "PG"},
        node_id="N2",
        prior_nodes=[
            {
                "node_id": "N1",
                "function": "定向开场",
                "reveals": ["莱特来过酒馆"],
                "options": [{"intent": "软问路线"}],
            }
        ],
    )
    assert "N2" in u
    assert "hub" in u  # 来自 NODE_FUNCTIONS["N2"]
    assert "莱特来过酒馆" in u  # 前序节点已揭露线索注入
    assert "软问路线" in u  # 前序节点选项角度注入
    s = build_pass1_node_schema()
    assert s["required"] == [
        "node_id",
        "function",
        "situation",
        "choice_pressure",
        "reveals",
        "hides",
        "options",
    ]


def test_pass1_node_builder_first_node_no_prior() -> None:
    u = build_pass1_node_user_prompt(
        scene_spec=_SPEC, scene_contract={}, node_id="N1", prior_nodes=[]
    )
    assert "还没有已设计的节点" in u
