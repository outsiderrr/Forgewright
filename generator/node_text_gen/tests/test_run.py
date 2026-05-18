"""T-3Y-1 子 goal 2: /generator/node_text_gen/ 单元测试.

覆盖：
  - MockLLMProvider 调用记录 + 响应改写
  - render_node_prompt 返回 {system, user} + 内容正确
  - run_node_generation 端到端：render → mock provider → JSON 解析
  - run_node_generation 非 valid JSON 抛 ValueError
"""
from __future__ import annotations

import json

import pytest

from generator.node_text_gen.mock_provider import MockLLMProvider, make_mock_node_response
from generator.node_text_gen.render import render_node_prompt
from generator.node_text_gen.run import run_node_generation


def _skeleton() -> dict:
    return {
        "node_id": "node_3_info_offer",
        "type": "dialogue",
        "narration": "",
        "speaker_ref": "char_lucy",
        "location_ref": "scene_inn",
        "on_enter_effects": [],
        "options": [
            {
                "option_id": "opt_a",
                "text": "",
                "target_node_id": "node_end",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
        ],
    }


# ---------- MockLLMProvider ----------


def test_mock_provider_records_calls() -> None:
    p = MockLLMProvider(response='{"key": "value"}')
    out = p.generate(system="sys", user="usr")
    assert out == '{"key": "value"}'
    assert len(p.calls) == 1
    assert p.calls[0] == {"system": "sys", "user": "usr"}


def test_mock_provider_set_response_changes_output() -> None:
    p = MockLLMProvider()
    p.set_response('{"new": true}')
    assert p.generate(system="x", user="y") == '{"new": true}'


def test_mock_provider_reset_clears_calls() -> None:
    p = MockLLMProvider()
    p.generate(system="x", user="y")
    p.reset()
    assert p.calls == []


def test_make_mock_node_response_is_valid_json() -> None:
    raw = make_mock_node_response()
    parsed = json.loads(raw)
    assert parsed["node_id"] == "node_3_info_offer"
    assert parsed["type"] == "dialogue"
    assert len(parsed["options"]) == 2
    assert all("opt_mock" in opt["option_id"] for opt in parsed["options"])


# ---------- render_node_prompt ----------


def test_render_returns_system_and_user_keys() -> None:
    out = render_node_prompt(
        node_skeleton=_skeleton(),
        player_known_info=[],
        foreground_goal=None,
        background_seeds=[],
    )
    assert set(out.keys()) == {"system", "user"}
    assert "节点级**对话生成器" in out["system"]
    assert "node_3_info_offer" in out["user"]


def test_render_propagates_forward_planner_outputs_to_user() -> None:
    out = render_node_prompt(
        node_skeleton=_skeleton(),
        player_known_info=[{"knowledge_path": "knowledge.wright_dead", "stage": 1}],
        foreground_goal="r1_wright_double_life.stage_2",
        background_seeds=["S2_vick_dangerous"],
        npc_state={"trust": 1},
    )
    user = out["user"]
    assert "knowledge.wright_dead" in user
    assert "r1_wright_double_life.stage_2" in user
    assert "S2_vick_dangerous" in user
    assert "trust" in user


# ---------- run_node_generation ----------


def test_run_end_to_end_with_mock_returns_parsed_dict() -> None:
    provider = MockLLMProvider(response=make_mock_node_response())
    result = run_node_generation(
        provider=provider,
        node_skeleton=_skeleton(),
        player_known_info=[{"knowledge_path": "knowledge.wright_dead"}],
        foreground_goal="r1.stage_1",
        background_seeds=["S1"],
    )
    assert result["node_id"] == "node_3_info_offer"
    assert "narration" in result and len(result["narration"]) > 0
    assert len(result["options"]) == 2


def test_run_provider_received_correct_args() -> None:
    """run 应调 provider.generate 一次，并传 system + user."""
    provider = MockLLMProvider(response=make_mock_node_response())
    run_node_generation(
        provider=provider,
        node_skeleton=_skeleton(),
        player_known_info=[],
        foreground_goal=None,
        background_seeds=[],
    )
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert "system" in call and "user" in call
    assert "节点级**对话生成器" in call["system"]
    assert "node_3_info_offer" in call["user"]


def test_run_raises_value_error_on_bad_json() -> None:
    provider = MockLLMProvider(response="not a valid json {{{")
    with pytest.raises(ValueError, match="非 valid JSON"):
        run_node_generation(
            provider=provider,
            node_skeleton=_skeleton(),
            player_known_info=[],
            foreground_goal=None,
            background_seeds=[],
        )
