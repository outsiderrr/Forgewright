"""Few-shot examples drawn from the hand-authored Iron Oath waystation scene.

`load_iron_oath_few_shot()` reads `/content/test_scene_v0/scene.json` and
returns 5 scene-derived `(input_context, expected_node)` pairs — one per node
in the scene — concatenated with **2 hand-written composite-condition demos**
added at the tail (T-2.0 R2 cleanup). The composite demos exist solely to make
the StateCondition leaf-vs-composite split unambiguous; baseline_004 showed
the scene-derived pairs alone weren't enough signal for the model to keep the
two forms separate.

The scene-derived `input_context` field is reconstructed: it's what a B+
context window *would* have looked like at the moment that specific node was
about to be generated (parent chain only, no peek at sibling branches). The
composite demos build their `input_context` directly so the precondition state
can be stated explicitly.

Reading from /content/ is read-only; this module never mutates the scene.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_SCENE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "content"
    / "test_scene_v0"
    / "scene.json"
)


@dataclass(frozen=True)
class FewShotPair:
    """One demonstration: B+ input context as plain prose, plus the
    canonical Node JSON we want the model to learn to mirror."""

    input_context: str
    expected_node: dict


def _build_parent_chain(graph: dict, node_id: str, max_depth: int = 3) -> list[dict]:
    """Walk back through option targets to reconstruct up to 3 ancestors of
    `node_id` (oldest first). The hand-authored scene is a small DAG so a
    BFS-from-entry is fine."""
    nodes = graph["nodes"]
    parent_of: dict[str, str] = {}
    for parent_id, node in nodes.items():
        for opt in node.get("options", []) or []:
            target = opt.get("target_node_id")
            if target and target not in parent_of and target != graph["entry_node_id"]:
                parent_of[target] = parent_id

    chain: list[str] = []
    cursor = node_id
    while cursor in parent_of and len(chain) < max_depth:
        cursor = parent_of[cursor]
        chain.append(cursor)
    chain.reverse()
    return [nodes[nid] for nid in chain]


def _render_input_context(graph: dict, node_id: str) -> str:
    """Render the prose description of the B+ context that would precede
    generating `node_id`. Mirrors the layout of
    context_assembler.assemble_context_block."""
    node = graph["nodes"][node_id]
    parent_chain = _build_parent_chain(graph, node_id)

    parts: list[str] = []
    parts.append(f"## 场景锚点")
    parts.append(f"- scene_anchor: `{graph['scene_anchor']}`")

    parts.append("")
    parts.append("## 父链（按时间顺序，最近的父节点在最后）")
    if parent_chain:
        for idx, parent in enumerate(parent_chain):
            parts.append(f"### 父节点 {idx + 1}（id=`{parent['node_id']}`，speaker=`{parent.get('speaker_ref')}`）")
            parts.append(f"> {parent['narration'][:160].replace(chr(10), ' ')}…")
    else:
        parts.append("（无父节点——本节点为入口节点位置）")

    parts.append("")
    parts.append("## 出场角色（图层 character_refs）")
    parts.append(", ".join(f"`{r}`" for r in graph.get("character_refs", [])))

    parts.append("")
    parts.append("## 本次生成要求")
    parts.append(f"- 节点类型 (`type`): `{node['type']}`")
    speaker = node.get("speaker_ref")
    parts.append(
        f"- 说话者 (`speaker_ref`): `{'null（旁白）' if speaker is None else speaker}`"
    )
    intent = _infer_intent(node)
    parts.append(f"- 叙事意图: {intent}")

    return "\n".join(parts)


def _infer_intent(node: dict) -> str:
    """Heuristic 1-line intent label so the few-shot pair feels like a real
    request from the upper layer. Pulled from a small lookup table — these
    are author-flavoured intents for the 5 fixed nodes, not LLM-derived."""
    table = {
        "arrival_waystation": "建立场景张力，让玩家在『过路客 / 介入者』之间表态",
        "vellin_confession": "把秘密摊开；逼玩家在共谋与告发之间二选一",
        "patrol_arrives": "外部压力到场，提供高难度可见的旧情诉求路线",
        "end_silent_ally": "共谋分支的余韵收尾——以书信回响代替直接交代",
        "end_iron_blade": "告发分支的代价收尾——具体感官细节传达悔意",
    }
    return table.get(node["node_id"], "承接前情，给出 3–6 个体现性格倾向的选项")


def load_iron_oath_few_shot() -> list[FewShotPair]:
    """Return 5 scene-derived pairs followed by 2 composite-condition demos.

    The scene-derived pairs come first in hand-authored play order so prompt
    hashes are stable: arrival → confession → patrol_arrives → end_silent_ally
    → end_iron_blade. The composite-condition demos (T-2.0 R2 cleanup) are
    appended at the tail and explicitly annotate the all_of+not / any_of
    shapes the model must mirror — see load_composite_condition_few_shot.
    """
    graph = json.loads(_SCENE_PATH.read_text(encoding="utf-8"))
    order = [
        "arrival_waystation",
        "vellin_confession",
        "patrol_arrives",
        "end_silent_ally",
        "end_iron_blade",
    ]
    scene_pairs = [
        FewShotPair(
            input_context=_render_input_context(graph, nid),
            expected_node=graph["nodes"][nid],
        )
        for nid in order
    ]
    return scene_pairs + load_composite_condition_few_shot()


def load_composite_condition_few_shot() -> list[FewShotPair]:
    """Return 2 hand-built demos illustrating composite StateCondition shapes.

    Demo 1 (`all_of` + nested `not`): mirrors the
    `arrival_waystation.opt_read_the_room` pattern but pulled out of the scene
    so the input_context can spell out exactly which leaf conditions are true
    when the option is supposed to be available.

    Demo 2 (`any_of`): mirrors `patrol_arrives.opt_invoke_old_bond` — either
    branch alone makes the option visible.

    Both demos:
    - use only state paths legal in the v0.1.1 namespace (`player.*`,
      `flag.*`, `relationship.<char>.*`)
    - keep `Option.text` ≤ 25 漢字 so the R3 cleanup constraint is honoured
    - pick `location_ref` from the demo's `location_candidates` (R4 cleanup)
    """
    return [_demo_all_of_not(), _demo_any_of()]


def _demo_all_of_not() -> FewShotPair:
    """Demo: dialogue option with `all_of[<has>, <not eq>]` composite condition.

    Reads as: "this option is available when player.traits contains
    'observant' AND flag.composite_demo_used is not yet set."
    """
    input_context = (
        "## 场景锚点\n"
        "- scene_anchor: `scene_demo_composite`\n"
        "\n"
        "## 候选地点\n"
        "- 主地点（推荐默认 `location_ref`）：`scene_demo_composite`\n"
        "```json\n"
        "{\n"
        '  "location_id": "scene_demo_composite",\n'
        '  "name": "演示场景"\n'
        "}\n"
        "```\n"
        "\n"
        "## 当前状态摘录\n"
        "- `player.traits` 包含 `\"observant\"`\n"
        "- `flag.composite_demo_used` 未被置位（视为 false）\n"
        "\n"
        "## 本次生成要求\n"
        "- 节点类型 (`type`): `dialogue`\n"
        "- 说话者 (`speaker_ref`): `char_demo`\n"
        "- 叙事意图: 演示 `all_of[has, not eq]` 复合条件——仅当玩家"
        "具备 observant 且未触发过该选项时显示。"
    )
    expected_node = {
        "node_id": "demo_all_of_not",
        "type": "dialogue",
        "narration": "（演示：复合条件 all_of + not 的标准形态。）",
        "speaker_ref": "char_demo",
        "location_ref": "scene_demo_composite",
        "on_enter_effects": [],
        "options": [
            {
                "option_id": "opt_observant_first_use",
                "text": "[观察入微] 我注意到了。",
                "target_node_id": "demo_target_observed",
                "condition": {
                    "all_of": [
                        {
                            "op": "has",
                            "path": "player.traits",
                            "value": "observant",
                        },
                        {
                            "not": {
                                "op": "eq",
                                "path": "flag.composite_demo_used",
                                "value": True,
                            }
                        },
                    ]
                },
                "effects": [
                    {
                        "op": "set",
                        "path": "flag.composite_demo_used",
                        "value": True,
                    }
                ],
                "unavailable_behavior": "disable_with_hint",
            },
            {
                "option_id": "opt_pass",
                "text": "我没看出什么。",
                "target_node_id": "demo_target_pass",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
            {
                "option_id": "opt_leave",
                "text": "我先走了。",
                "target_node_id": "demo_target_leave",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
        ],
    }
    return FewShotPair(input_context=input_context, expected_node=expected_node)


def _demo_any_of() -> FewShotPair:
    """Demo: dialogue option with `any_of[<gte>, <has>]` composite condition.

    Reads as: "this option is available when relationship.demo_npc.trust ≥ 2
    OR player.bonds contains 'demo_shared_past' — either alone is enough."
    """
    input_context = (
        "## 场景锚点\n"
        "- scene_anchor: `scene_demo_composite`\n"
        "\n"
        "## 候选地点\n"
        "- 主地点（推荐默认 `location_ref`）：`scene_demo_composite`\n"
        "```json\n"
        "{\n"
        '  "location_id": "scene_demo_composite",\n'
        '  "name": "演示场景"\n'
        "}\n"
        "```\n"
        "\n"
        "## 当前状态摘录\n"
        "- `relationship.demo_npc.trust` 当前值 = 3（≥ 2 成立）\n"
        "- `player.bonds` 不含 `\"demo_shared_past\"`（has 不成立）\n"
        "- 二者**任一**成立即可让此选项显示\n"
        "\n"
        "## 本次生成要求\n"
        "- 节点类型 (`type`): `dialogue`\n"
        "- 说话者 (`speaker_ref`): `char_demo_npc`\n"
        "- 叙事意图: 演示 `any_of[gte, has]` 复合条件——"
        "信任度足够 **或** 拥有共同往事，二者其一即可。"
    )
    expected_node = {
        "node_id": "demo_any_of",
        "type": "dialogue",
        "narration": "（演示：复合条件 any_of 的标准形态。）",
        "speaker_ref": "char_demo_npc",
        "location_ref": "scene_demo_composite",
        "on_enter_effects": [],
        "options": [
            {
                "option_id": "opt_old_bond",
                "text": "[诉诸旧情] 你欠我一次。",
                "target_node_id": "demo_target_bond",
                "condition": {
                    "any_of": [
                        {
                            "op": "gte",
                            "path": "relationship.demo_npc.trust",
                            "value": 2,
                        },
                        {
                            "op": "has",
                            "path": "player.bonds",
                            "value": "demo_shared_past",
                        },
                    ]
                },
                "effects": [
                    {
                        "op": "inc",
                        "path": "relationship.demo_npc.trust",
                        "value": 1,
                    }
                ],
                "unavailable_behavior": "disable",
            },
            {
                "option_id": "opt_neutral",
                "text": "我们就事论事。",
                "target_node_id": "demo_target_neutral",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
            {
                "option_id": "opt_walk_away",
                "text": "我没什么好说的。",
                "target_node_id": "demo_target_walkaway",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
        ],
    }
    return FewShotPair(input_context=input_context, expected_node=expected_node)


def render_few_shot_block(pairs: list[FewShotPair]) -> str:
    """Render the few-shot block as a markdown prompt fragment.

    Pulled out so generate_node can cache it across attempts (the few-shot
    block is identical on retries; only the error-feedback tail changes)."""
    parts: list[str] = ["## Few-shot 示范"]
    for idx, pair in enumerate(pairs, start=1):
        parts.append(f"### 示范 {idx}")
        parts.append("**输入 context（节选）**：")
        parts.append(pair.input_context)
        parts.append("")
        parts.append("**期望输出 Node JSON**：")
        parts.append("```json")
        parts.append(json.dumps(pair.expected_node, ensure_ascii=False, indent=2))
        parts.append("```")
        parts.append("")
    return "\n".join(parts)
