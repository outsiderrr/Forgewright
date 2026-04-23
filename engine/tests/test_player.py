"""T-0.6 终端播放器测试。

覆盖：
- 路径 A / B：走完基准场景的两条不同结局；断言 stdout / 终局状态
- 路径 C：StateCondition 守卫在状态满足时暴露隐藏选项
- 非法输入：非数字 + 超范围 + 合法数字 → 不 crash
- Schema 失败：sys.exit(1)
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from engine import play

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCENE_PATH = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"
SCENE_BROKEN_SCHEMA_PATH = (
    REPO_ROOT / "content" / "test_scene_v0" / "scene_broken_schema.json"
)


def _run(scene: str | Path, inputs: str) -> tuple[dict, str]:
    stdin = io.StringIO(inputs)
    stdout = io.StringIO()
    final = play(str(scene), stdin=stdin, stdout=stdout)
    return final, stdout.getvalue()


# ---------------------------------------------------------------------------
# 路径 A：N1.opt_confront_letter → N2.opt_promise_silence → end_silent_ally
# ---------------------------------------------------------------------------

def test_path_a_reaches_silent_ally_ending():
    final, out = _run(SCENE_PATH, "1\n1\n")
    # N4 旁白结局的叙述片段
    assert "三天后，东边的牧人废屋空了" in out
    assert "—— 结局 ——" in out
    # Path A 穿过 N2 触发 on_enter_effects：flag.player_saw_blood_letter=true
    assert final["flag"]["player_saw_blood_letter"] is True
    # N2.opt_promise_silence 的 effects
    assert final["flag"]["oath_broken_conspiracy"] is True
    assert final["relationship"]["vellin"]["trust"] == 2


# ---------------------------------------------------------------------------
# 路径 B：N1.opt_sit_and_wait → N3.opt_reveal_to_corvan → end_iron_blade
# ---------------------------------------------------------------------------

def test_path_b_reaches_iron_blade_ending_with_path_specific_flag():
    final, out = _run(SCENE_PATH, "2\n2\n")
    # N5 结局叙述片段
    assert "铁誓卫队没有让你失望" in out
    # 路径特有 flag：出卖 Aelwin
    assert final["flag"]["aelwin_betrayed"] is True
    assert final["faction"]["iron_oath"]["reputation"] == 2
    # 没走 N2 — 不应触发 on_enter_effects
    assert "player_saw_blood_letter" not in final.get("flag", {})


# ---------------------------------------------------------------------------
# 路径 C：StateCondition 守卫（has player.items key）在状态满足时出现
# ---------------------------------------------------------------------------

_SCENE_C = {
    "schema_version": "0.1.1",
    "graph_id": "test_state_gate",
    "entry_node_id": "n_start",
    "scene_anchor": "scene_test",
    "character_refs": [],
    "nodes": {
        "n_start": {
            "node_id": "n_start",
            "type": "dialogue",
            "narration": "桌上放着一把黄铜钥匙。",
            "speaker_ref": None,
            "location_ref": "loc_test",
            "on_enter_effects": [],
            "options": [
                {
                    "option_id": "opt_grab_key",
                    "text": "拿起黄铜钥匙。",
                    "target_node_id": "n_gate",
                    "condition": None,
                    "effects": [
                        {"op": "add", "path": "player.items", "value": "key"}
                    ],
                    "unavailable_behavior": "hide",
                },
                {
                    "option_id": "opt_skip",
                    "text": "看都不看径直离开。",
                    "target_node_id": "n_gate",
                    "condition": None,
                    "effects": [],
                    "unavailable_behavior": "hide",
                },
            ],
        },
        "n_gate": {
            "node_id": "n_gate",
            "type": "dialogue",
            "narration": "一道紧锁的铁门挡在前面。",
            "speaker_ref": None,
            "location_ref": "loc_test",
            "on_enter_effects": [],
            "options": [
                {
                    "option_id": "opt_use_key",
                    "text": "用黄铜钥匙开门。",
                    "target_node_id": "n_end_unlocked",
                    "condition": {
                        "op": "has", "path": "player.items", "value": "key"
                    },
                    "effects": [],
                    "unavailable_behavior": "hide",
                },
                {
                    "option_id": "opt_walk_away",
                    "text": "原路返回。",
                    "target_node_id": "n_end_locked",
                    "condition": None,
                    "effects": [],
                    "unavailable_behavior": "hide",
                },
            ],
        },
        "n_end_unlocked": {
            "node_id": "n_end_unlocked",
            "type": "end",
            "narration": "铁门哐当一声开了。",
            "speaker_ref": None,
            "location_ref": "loc_test",
            "options": [],
        },
        "n_end_locked": {
            "node_id": "n_end_locked",
            "type": "end",
            "narration": "你放弃了那扇门。",
            "speaker_ref": None,
            "location_ref": "loc_test",
            "options": [],
        },
    },
}


def test_path_c_state_gated_option_appears_when_condition_met(tmp_path):
    scene_file = tmp_path / "scene_c.json"
    scene_file.write_text(json.dumps(_SCENE_C, ensure_ascii=False), encoding="utf-8")

    # 先拿钥匙（opt_grab_key=1），再用钥匙开门（opt_use_key=1）
    final, out = _run(scene_file, "1\n1\n")

    # 在 n_gate 节点，'用黄铜钥匙开门' 应作为有编号的选项出现（非 [不可选]）
    gate_start = out.index("一道紧锁的铁门挡在前面。")
    end_start = out.index("铁门哐当一声开了。")
    gate_block = out[gate_start:end_start]
    assert "用黄铜钥匙开门" in gate_block
    assert "[不可选]" not in gate_block  # hide 行为，不应出现"不可选"前缀
    assert final["player"]["items"] == ["key"]


def test_path_c_state_gated_option_hidden_when_condition_unmet(tmp_path):
    scene_file = tmp_path / "scene_c.json"
    scene_file.write_text(json.dumps(_SCENE_C, ensure_ascii=False), encoding="utf-8")

    # 不拿钥匙（opt_skip=2），然后 n_gate 仅剩 opt_walk_away（=1）
    final, out = _run(scene_file, "2\n1\n")

    gate_start = out.index("一道紧锁的铁门挡在前面。")
    end_start = out.index("你放弃了那扇门。")
    gate_block = out[gate_start:end_start]
    # 钥匙条件未满足 + hide → 选项文本完全不出现
    assert "用黄铜钥匙开门" not in gate_block
    assert "items" not in final.get("player", {})


# ---------------------------------------------------------------------------
# 非法输入：非数字、超范围 → 重新 prompt，不 crash
# ---------------------------------------------------------------------------

def test_invalid_input_does_not_crash():
    # N1 可见选项共 2 个（#1/#2；opt_read_the_room 因条件不满足走 disable_with_hint）
    # 依次喂：abc（非数字）→ 99（超范围）→ 0（超范围）→ 1（合法 → opt_confront_letter）
    # N2 可见 2 个，喂：foo → 1（合法 → opt_promise_silence）
    final, out = _run(SCENE_PATH, "abc\n99\n0\n1\nfoo\n1\n")
    assert "请输入数字" in out
    assert "数字超出范围" in out
    assert "三天后，东边的牧人废屋空了" in out
    assert final["flag"]["oath_broken_conspiracy"] is True


# ---------------------------------------------------------------------------
# Schema 失败 → sys.exit(1)
# ---------------------------------------------------------------------------

def test_schema_failure_exits_with_code_1():
    with pytest.raises(SystemExit) as exc_info:
        _run(SCENE_BROKEN_SCHEMA_PATH, "")
    assert exc_info.value.code == 1


def test_major_mismatch_exits_with_code_1(tmp_path):
    bad = dict(_SCENE_C)
    bad = json.loads(json.dumps(_SCENE_C))  # deep copy
    bad["schema_version"] = "1.0.0"  # MAJOR 1 != 期望 0
    scene_file = tmp_path / "bad_version.json"
    scene_file.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        _run(scene_file, "")
    assert exc_info.value.code == 1
