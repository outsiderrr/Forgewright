"""确定性组装（0 LLM）：多 pass 产物 → 合法 dialogue_graph JSON.

架构共识 2（LLM 不能直接写状态）在此落地：LLM 各 pass 只产正文/设计候选，
node_id / option_id / target_node_id 接线与机械字段（condition=null / effects=[] /
unavailable_behavior="hide" / on_enter_effects=[]）**全部由本模块确定性填写**。

schema：单选项 beat 节点天然合法（ADR-038；type=dialogue ⇒ options minItems:1）。
ADR-040（B1 结构化对白）：narration = 旁白（场景/动作白描，无说话人）；NPC 对白拆进
结构化 `dialogue=[{speaker_ref, line}]`（**不再揉进 narration**）；带非空 dialogue[] 的
节点 `speaker_ref=null`（旁白无归属，对白说话人在 dialogue[] 内）。schema_version 不 bump
（dialogue 走 optional + additionalProperties 兼容路径）。组装产物交给 validator
（schema + mechanical + AP 检测），engine 层调用。
"""
from __future__ import annotations

from typing import Any

def _normalize_line(line: str) -> str:
    """对白行体例归一为**裸正文**：去掉整句包裹引号（「」/半角 ""/全角 ""）。

    ADR-040：对白进结构化 dialogue[].line，line 存裸正文（不含包裹引号体例），
    引号 / 气泡等呈现由宿主 / 渲染层施加。复核发现 3/6 候选体例混用（裸句 / 「」 /
    弯引号），统一去包裹得干净内容；只去**整句包裹**，句内引用（如露西转述莱特的话）不动。
    """
    line = line.strip()
    if not line:
        return line
    for opener, closer in (("「", "」"), ("“", "”"), ('"', '"')):
        if (
            line.startswith(opener)
            and line.endswith(closer)
            and len(line) >= len(opener) + len(closer)
        ):
            return line[len(opener) : -len(closer)].strip()
    return line


def _dialogue_entries(
    speaker_ref: str, lines: list[str] | None
) -> list[dict[str, Any]]:
    """对白行数组 → 结构化 [{speaker_ref, line}]（ADR-040）。

    line 体例归一为裸正文；空行丢弃。speaker_ref 为图级单说话人（场景内对白同一 NPC）。
    """
    entries: list[dict[str, Any]] = []
    for raw in lines or []:
        line = _normalize_line(raw)
        if line:
            entries.append({"speaker_ref": speaker_ref, "line": line})
    return entries


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
                "narration": (prose.get("narration", "") or "").strip(),
                "dialogue": _dialogue_entries(speaker_ref, prose.get("dialogue")),
                "speaker_ref": None,
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
                    "narration": (beat.get("narration", "") or "").strip(),
                    "dialogue": _dialogue_entries(speaker_ref, beat.get("dialogue")),
                    "speaker_ref": None,
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
            nodes[pid] = {
                "node_id": pid,
                "type": "end",
                "narration": (data.get("narration", "") or "").strip(),
                "dialogue": _dialogue_entries(speaker_ref, data.get("dialogue")),
                "speaker_ref": None,
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
