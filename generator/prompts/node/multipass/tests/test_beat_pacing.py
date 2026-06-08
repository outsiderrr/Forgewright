"""beat_pacing 模块单测（不调 LLM）。"""
from __future__ import annotations

from generator.prompts.node.multipass.beat_pacing import (
    BEAT_PACING_SYSTEM,
    build_beat_pacing_schema,
    build_beat_pacing_user_prompt,
)


def test_schema_2_to_3_single_option_beats() -> None:
    s = build_beat_pacing_schema()
    beats = s["properties"]["beats"]
    assert beats["minItems"] == 2 and beats["maxItems"] == 3
    item = beats["items"]
    assert item["required"] == ["narration", "dialogue", "continue_option"]
    assert item["properties"]["continue_option"]["required"] == ["text"]


def test_system_slimmed_aps_and_first_person_implied() -> None:
    for n in (1, 2, 3, 4, 5, 6, 9):
        assert f"### AP-{n}:" in BEAT_PACING_SYSTEM
    for n in (7, 8, 10):
        assert f"### AP-{n}:" not in BEAT_PACING_SYSTEM
    assert "单选项节拍" in BEAT_PACING_SYSTEM
    assert "别硬塞" in BEAT_PACING_SYSTEM  # 选项第一人称隐含规则
    assert "3 分类角色守则" in BEAT_PACING_SYSTEM  # role rules 保留


def test_user_prompt_injects_situation_and_reveals() -> None:
    u = build_beat_pacing_user_prompt(
        scene_contract={"player_goal": "PG"},
        node_situation="SIT_MARK",
        reveals=["R_ALPHA", "R_BETA"],
    )
    assert "SIT_MARK" in u
    assert "R_ALPHA" in u and "R_BETA" in u
