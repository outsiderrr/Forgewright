"""确定性组装（0 LLM）：多 pass 产物 → 合法 dialogue_graph JSON.

架构共识 2（LLM 不能直接写状态）在此落地：LLM 各 pass 只产正文/设计候选，
node_id / option_id / target_node_id 接线与机械字段（condition=null / effects=[] /
unavailable_behavior="hide" / on_enter_effects=[]）**全部由本模块确定性填写**。

schema 不改（ADR-038）：单选项 beat 节点天然合法（type=dialogue ⇒ options minItems:1）。
组装产物交给 validator（schema + mechanical + AP 检测），engine 层调用。
"""
from __future__ import annotations

from typing import Any

def _quote(line: str) -> str:
    """NPC 对白行归一化为「」引号（裸句包裹；弯/直引号整句换成「」——复核发现 3/6 候选体例混用）。"""
    line = line.strip()
    if not line:
        return line
    # 整句被弯引号 / 直引号包裹 → 换成「」（确定性体例归一，不改内容）
    for opener, closer in (("“", "”"), ('"', '"')):
        if line.startswith(opener) and line.endswith(closer) and len(line) >= 2:
            line = line[len(opener) : -len(closer)].strip()
            break
    if line.startswith("「"):
        return line
    return f"「{line}」"


def _merge_narration(narration: str, dialogue: list[str] | None) -> str:
    """narration + NPC 对白合成 node.narration（schema 单字段；对白带引号成段）。"""
    parts = [narration.strip()] if narration and narration.strip() else []
    for line in dialogue or []:
        q = _quote(line)
        if q:
            parts.append(q)
    return "\n\n".join(parts)


def entry_graph_node_id(plan_node: dict[str, Any]) -> str:
    """plan 节点 → 它在成品图里的入口 node_id（beats 链入口 = 第 1 拍）。"""
    nid = plan_node["node_id"]
    return f"{nid}_b1" if plan_node.get("kind") == "beats" else nid


def _mk_option(option_id: str, text: str, target: str) -> dict[str, Any]:
    return {
        "option_id": option_id,
        "text": text,
        "target_node_id": target,
        "condition": None,
        "effects": [],
        "unavailable_behavior": "hide",
    }


def assemble_graph(
    *,
    graph_id: str,
    scene_anchor: str,
    speaker_ref: str,
    character_refs: list[str],
    plan: dict[str, Any],
    choice_data: dict[str, dict[str, Any]],
    beats_data: dict[str, list[dict[str, Any]]],
    end_data: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """组装 dialogue_graph dict；返回 (graph, warnings)。

    Args:
        graph_id / scene_anchor / speaker_ref / character_refs: 图级配置（SceneRunConfig）。
        plan: 已通过确定性校验的 TopologyPlan。
        choice_data: {plan_node_id: {"skeleton": ..., "prose": ...}}。
        beats_data: {plan_node_id: [beat, ...]}（多 chunk 已合并）。
        end_data: {plan_node_id: {"narration": ..., "dialogue": [...]}}。

    Warnings（不抛异常；如实记录交给复核）：
        - 选项 route_to 缺失/非法 → 回退到本节点第一条出边；
        - prose 与 skeleton 选项数不一致 → 按索引对齐截断。
    """
    warnings: list[str] = []
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    target_map = {nid: entry_graph_node_id(n) for nid, n in by_id.items()}

    nodes: dict[str, dict[str, Any]] = {}

    for pid, pnode in by_id.items():
        kind = pnode.get("kind")
        if kind == "choice":
            data = choice_data.get(pid) or {}
            skeleton = data.get("skeleton") or {}
            prose = data.get("prose") or {}
            skel_opts = skeleton.get("options") or []
            prose_opts = prose.get("options") or []
            if len(skel_opts) != len(prose_opts):
                warnings.append(
                    f"choice {pid}: skeleton {len(skel_opts)} 个选项 vs prose "
                    f"{len(prose_opts)} 个——按索引对齐截断"
                )
            allowed = [r.get("to") for r in pnode.get("routes") or []]
            options: list[dict[str, Any]] = []
            for i in range(min(len(skel_opts), len(prose_opts)) or len(prose_opts)):
                skel_o = skel_opts[i] if i < len(skel_opts) else {}
                text = (prose_opts[i] if i < len(prose_opts) else {}).get("text", "")
                route = skel_o.get("route_to")
                if route not in allowed:
                    if route is not None:
                        warnings.append(
                            f"choice {pid} 选项 {i}: route_to {route!r} 不在出边 {allowed}"
                            "——回退到第一条出边"
                        )
                    route = allowed[0] if allowed else None
                if route is None:
                    warnings.append(f"choice {pid} 选项 {i}: 无可用出边，选项被丢弃")
                    continue
                options.append(_mk_option(f"opt_{pid}_{i + 1}", text, target_map[route]))
            nodes[pid] = {
                "node_id": pid,
                "type": "dialogue",
                "narration": _merge_narration(prose.get("narration", ""), prose.get("dialogue")),
                "speaker_ref": speaker_ref,
                "location_ref": scene_anchor,
                "on_enter_effects": [],
                "options": options,
            }
        elif kind == "beats":
            beats = beats_data.get(pid) or []
            nxt = target_map.get(pnode.get("next", ""), "")
            for i, beat in enumerate(beats, start=1):
                bid = f"{pid}_b{i}"
                target = f"{pid}_b{i + 1}" if i < len(beats) else nxt
                nodes[bid] = {
                    "node_id": bid,
                    "type": "dialogue",
                    "narration": _merge_narration(beat.get("narration", ""), beat.get("dialogue")),
                    "speaker_ref": speaker_ref,
                    "location_ref": scene_anchor,
                    "on_enter_effects": [],
                    "options": [
                        _mk_option(
                            f"opt_{bid}_continue",
                            (beat.get("continue_option") or {}).get("text", ""),
                            target,
                        )
                    ],
                }
            if not beats:
                warnings.append(f"beats {pid}: 没有任何节拍产出——链塌缩为空，跳过")
        elif kind == "end":
            data = end_data.get(pid) or {}
            dialogue = data.get("dialogue") or []
            nodes[pid] = {
                "node_id": pid,
                "type": "end",
                "narration": _merge_narration(data.get("narration", ""), dialogue),
                "speaker_ref": speaker_ref if dialogue else None,
                "location_ref": scene_anchor,
                "on_enter_effects": [],
                "options": [],
            }

    graph = {
        "schema_version": "0.1.1",
        "graph_id": graph_id,
        "entry_node_id": target_map[plan["entry_node_id"]],
        "scene_anchor": scene_anchor,
        "character_refs": list(character_refs),
        "nodes": nodes,
    }
    return graph, warnings


__all__ = ["assemble_graph", "entry_graph_node_id"]
