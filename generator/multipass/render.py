"""剧本式 markdown 渲染（作者审阅形态）—— 树序遍历整场.

作者审任何产物必须 render 成 concrete 形态（剧本式 markdown），
不能只给字段/schema——本模块就是那个形态。
"""
from __future__ import annotations

from typing import Any


def _opts_block(options: list[dict[str, Any]], skeleton_opts: list[dict[str, Any]]) -> str:
    lines = []
    for i, o in enumerate(options):
        intent = skeleton_opts[i].get("intent", "") if i < len(skeleton_opts) else ""
        suffix = f"　*(intent: {intent})*" if intent else ""
        lines.append(f"{i + 1}. {o.get('text', '')} → `{o.get('target_node_id', '')}`{suffix}")
    return "\n".join(lines) or "（无）"


def render_scene_md(result: Any) -> str:
    """MultipassSceneResult → 剧本式 markdown（树序：父节点 → 各分支）。"""
    design = result.design
    plan = design.get("topology") or {}
    by_id = {n["node_id"]: n for n in plan.get("nodes", [])}
    skeletons = design.get("skeletons", {})
    graph_nodes = (result.graph or {}).get("nodes", {})
    m = result.metrics
    v = result.validation or {}

    blocks: list[str] = []

    def _walk(pid: str) -> None:
        pnode = by_id.get(pid)
        if pnode is None:
            return
        kind = pnode.get("kind")
        if kind == "choice":
            gnode = graph_nodes.get(pid, {})
            sk = skeletons.get(pid, {})
            opts = gnode.get("options") or []
            blocks.append(
                f"""## ◆ {pid}（选择节点 · {len(opts)} 选项）
> 功能：{pnode.get('function', '')}

{gnode.get('narration', '')}

**玩家可选：**
{_opts_block(opts, sk.get('options') or [])}
"""
            )
            for r in pnode.get("routes") or []:
                _walk(r.get("to", ""))
        elif kind == "beats":
            beat_ids = sorted(
                (nid for nid in graph_nodes if nid.startswith(f"{pid}_b")),
                key=lambda x: int(x.rsplit("_b", 1)[1]),
            )
            parts = [f"## ─ {pid}（{len(beat_ids)} 个单选项节拍）\n> 功能：{pnode.get('function', '')}"]
            for bid in beat_ids:
                g = graph_nodes[bid]
                opt = (g.get("options") or [{}])[0]
                parts.append(
                    f"""**〔{bid}〕**
{g.get('narration', '')}
　→ `[ {opt.get('text', '')} ]` → `{opt.get('target_node_id', '')}`"""
                )
            blocks.append("\n\n".join(parts))
            _walk(pnode.get("next", ""))
        elif kind == "end":
            g = graph_nodes.get(pid, {})
            blocks.append(
                f"""## ◆ {pid}（终止节点）
> 功能：{pnode.get('function', '')}

{g.get('narration', '')}
"""
            )

    entry = plan.get("entry_node_id", "")
    _walk(entry)

    hard = "✅ 通过" if v.get("hard_pass") else "❌ 未通过"
    ap_n = m.get("ap_flag_count", 0)
    fallback_note = "（⚠️ 动态拓扑回退到半固定脚手架）" if result.topology_fallback else ""
    contract = design.get("contract", {})

    return f"""# 多 pass 分拍场景 · {(result.graph or {}).get('graph_id', '（未组装）')}

> 调用 {m.get('total_calls', 0)} 次 · 成本 ${m.get('total_cost_usd', 0):.4f} · 节点 {m.get('node_count', '?')} 个
> validator 硬校验：{hard} · AP flag：{ap_n} 处 · 拓扑：{'动态' if not result.topology_fallback else '回退'}{fallback_note}

## 场景契约
- 玩家目标：{contract.get('player_goal', '')}
- NPC 目标：{contract.get('npc_goal', '')}
- NPC 恐惧：{contract.get('npc_fear', '')}
- 失败可续路径：{contract.get('failsafe_path', '')}

{chr(10).join(blocks)}
"""


__all__ = ["render_scene_md"]
