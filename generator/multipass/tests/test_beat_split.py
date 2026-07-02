"""确定性拆拍器单测（T-3P-0；ADR-039 决策三）.

不变量（任务规格逐条对应断言）：
  - 确定性：同输入同输出；
  - 每条 reveal 恰好落一拍（无遗漏无重复）；
  - 保序：拍内/拍间线索顺序 = 输入顺序；
  - beat_id 与 assemble.entry_graph_node_id 的 {pid}_b1 约定一致；
  - 末拍 is_last=True；
  - 0 条 reveals 的链给 1 个过场拍；
  - 每拍上限参数化（默认 ≤2 条）。
"""
from __future__ import annotations

import pytest

from generator.multipass.assemble import entry_graph_node_id
from generator.multipass.beat_split import (
    DEFAULT_MAX_REVEALS_PER_BEAT,
    build_beats_plan,
    split_beats,
)

_REVEALS_8 = [f"线索{c}" for c in "甲乙丙丁戊己庚辛"]


def _beats_node(pid: str = "soft_line", reveals: list[str] | None = None) -> dict:
    return {
        "node_id": pid,
        "kind": "beats",
        "function": "软分支：交底",
        "reveals": _REVEALS_8 if reveals is None else reveals,
        "next": "end_soft",
    }


def test_default_cap_is_two() -> None:
    assert DEFAULT_MAX_REVEALS_PER_BEAT == 2


def test_deterministic_same_input_same_output() -> None:
    node = _beats_node()
    assert split_beats(node) == split_beats(node)
    assert split_beats(_beats_node()) == split_beats(_beats_node())


def test_every_reveal_exactly_once_and_in_order() -> None:
    slots = split_beats(_beats_node())
    flattened = [r for s in slots for r in s["reveals"]]
    assert flattened == _REVEALS_8  # 无遗漏、无重复、保序一次断言


def test_beat_id_matches_assemble_entry_convention() -> None:
    node = _beats_node(pid="money_line", reveals=["a", "b", "c"])
    slots = split_beats(node)
    assert slots[0]["beat_id"] == entry_graph_node_id(node)  # {pid}_b1
    assert [s["beat_id"] for s in slots] == [
        f"money_line_b{i}" for i in range(1, len(slots) + 1)
    ]


def test_only_last_slot_is_last() -> None:
    slots = split_beats(_beats_node())
    assert [s["is_last"] for s in slots] == [False] * (len(slots) - 1) + [True]


def test_default_cap_two_splits_eight_into_four() -> None:
    slots = split_beats(_beats_node())
    assert [len(s["reveals"]) for s in slots] == [2, 2, 2, 2]


def test_odd_count_leaves_remainder_in_last_beat() -> None:
    slots = split_beats(_beats_node(reveals=["a", "b", "c", "d", "e"]))
    assert [len(s["reveals"]) for s in slots] == [2, 2, 1]


def test_zero_reveals_chain_gets_one_transitional_beat() -> None:
    slots = split_beats(_beats_node(reveals=[]))
    assert len(slots) == 1
    assert slots[0] == {"beat_id": "soft_line_b1", "reveals": [], "is_last": True}


def test_cap_is_parameterizable() -> None:
    slots = split_beats(_beats_node(), max_reveals_per_beat=3)
    assert [len(s["reveals"]) for s in slots] == [3, 3, 2]
    assert all(len(s["reveals"]) <= 3 for s in slots)


def test_cap_below_one_rejected() -> None:
    with pytest.raises(ValueError):
        split_beats(_beats_node(), max_reveals_per_beat=0)


def test_non_beats_node_rejected() -> None:
    with pytest.raises(ValueError):
        split_beats({"node_id": "opening", "kind": "choice", "reveals": []})


def test_slot_shape_is_locked_to_three_keys() -> None:
    """BeatSlot 载体形态在 T-3P-0 锁死：恰好 beat_id / reveals / is_last 三 key。"""
    for slot in split_beats(_beats_node()):
        assert set(slot) == {"beat_id", "reveals", "is_last"}


def test_beat_ids_match_assemble_numbering_for_all_beats() -> None:
    """{pid}_b{i} 编号在拆拍器与 assemble 两个循环里必须全程一致（不只 b1）。

    T-3P-2 回流按 beat_id 对齐；entry_graph_node_id 只钉住 b1，这里把 i≥2 也
    钉在一起：同拍数下 assemble 产出的链节点 id 集合 == 拆拍计划的 beat_id 集合。
    """
    from generator.multipass.assemble import assemble_graph

    node = _beats_node(pid="soft_line", reveals=["a", "b", "c", "d", "e"])  # 3 拍
    slots = split_beats(node)
    plan = {
        "entry_node_id": "soft_line",
        "nodes": [node, {"node_id": "end_soft", "kind": "end", "function": "", "reveals": []}],
    }
    beats_data = {
        "soft_line": [
            {"narration": f"n{i}", "dialogue": [], "continue_option": {"text": "……"}}
            for i in range(len(slots))
        ]
    }
    graph, _ = assemble_graph(
        graph_id="t",
        scene_anchor="scene_x",
        speaker_ref="char_x",
        character_refs=["char_x"],
        plan=plan,
        choice_data={},
        beats_data=beats_data,
        end_data={"end_soft": {"narration": "e", "dialogue": []}},
    )
    chain_ids = sorted(nid for nid in graph["nodes"] if nid.startswith("soft_line_b"))
    assert chain_ids == [s["beat_id"] for s in slots]


def test_build_beats_plan_groups_by_chain() -> None:
    """beats_plan = dict 按链分组（非 flat list）；只收 kind=beats 节点。"""
    plan = {
        "entry_node_id": "opening",
        "nodes": [
            {"node_id": "opening", "kind": "choice", "function": "", "reveals": [],
             "routes": [{"to": "soft_line", "stance": ""}, {"to": "hard_line", "stance": ""}]},
            _beats_node(pid="soft_line", reveals=["a", "b", "c"]),
            _beats_node(pid="hard_line", reveals=["d"]),
            {"node_id": "end_soft", "kind": "end", "function": "", "reveals": []},
        ],
    }
    beats_plan = build_beats_plan(plan)
    assert set(beats_plan) == {"soft_line", "hard_line"}
    assert beats_plan["soft_line"] == split_beats(plan["nodes"][1])
    assert [s["beat_id"] for s in beats_plan["hard_line"]] == ["hard_line_b1"]
