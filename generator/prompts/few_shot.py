"""Few-shot examples drawn from the hand-authored Iron Oath waystation scene.

`load_iron_oath_few_shot()` reads `/content/test_scene_v0/scene.json` and
returns 5 `(input_context, expected_node)` pairs — one per node in the scene.
The `input_context` field is reconstructed: it's what a B+ context window
*would* have looked like at the moment that specific node was about to be
generated (parent chain only, no peek at sibling branches).

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
    """Return all 5 (input_context, expected_node) pairs from the test scene.

    The list order matches the hand-authored play order so prompt hashes are
    stable: arrival → confession → patrol_arrives → end_silent_ally →
    end_iron_blade.
    """
    graph = json.loads(_SCENE_PATH.read_text(encoding="utf-8"))
    order = [
        "arrival_waystation",
        "vellin_confession",
        "patrol_arrives",
        "end_silent_ally",
        "end_iron_blade",
    ]
    return [
        FewShotPair(
            input_context=_render_input_context(graph, nid),
            expected_node=graph["nodes"][nid],
        )
        for nid in order
    ]


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
