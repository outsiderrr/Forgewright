"""Three-way DialogueGraph visualisation (T-2.8 / U-GPT-7 strong rec).

Three render functions, each pure (input dict → string), no I/O:

  * `render_mermaid(graph)` — flowchart TD compatible with GitHub's
    fenced ```mermaid block. End nodes get a different style class so
    they stand out at a glance.
  * `render_dot(graph)`     — DOT digraph compatible with `dot -Tpng`.
    Same style intent (end nodes filled red) plus edge labels for
    conditional / unavailable_behavior options.
  * `render_ascii(graph)`   — Layered ASCII via networkx topological
    generations. Box-drawing characters frame each node; edges are
    listed below the layout because true 2-D ASCII edge routing is a
    rabbit hole and a flat edge list is just as readable in a terminal.

End nodes are highlighted so reviewers can see ending coverage at a
glance — `expected end nodes ≥ 2` is a baseline-protocol invariant
(ADR-020 §4); making it visible in every render helps the author spot
violations in scene_review_cli.

Edge labels surface two facts the validator three-class summary already
checks but isn't easy to eyeball:

  * `[cond]`     — option has a non-null `condition` (sampling 2B may
                   flag this if it's unsatisfiable from the entry state).
  * `unav=hide`  — non-default `unavailable_behavior` (ADR-016 enum).
"""
from __future__ import annotations

from typing import Any

import networkx as nx

__all__ = ["render_mermaid", "render_dot", "render_ascii"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _nodes(graph: dict) -> dict[str, dict]:
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, dict):
        return {}
    return {nid: n for nid, n in nodes.items() if isinstance(n, dict)}


def _entry(graph: dict) -> str | None:
    e = graph.get("entry_node_id") if isinstance(graph, dict) else None
    return e if isinstance(e, str) else None


def _edges(nodes: dict[str, dict]) -> list[tuple[str, str, dict]]:
    """Yield `(from_id, to_id, option_metadata)` for every option edge."""
    out: list[tuple[str, str, dict]] = []
    for nid, node in nodes.items():
        for opt in node.get("options") or []:
            if not isinstance(opt, dict):
                continue
            target = opt.get("target_node_id")
            if not isinstance(target, str):
                continue
            out.append((nid, target, opt))
    return out


def _edge_label(opt: dict) -> str:
    """Compact label highlighting cond / non-default unavailable_behavior."""
    bits: list[str] = []
    if opt.get("condition") is not None:
        bits.append("cond")
    unav = opt.get("unavailable_behavior")
    if isinstance(unav, str) and unav != "hide":
        bits.append(f"unav={unav}")
    return ", ".join(bits)


def _is_end(node: dict) -> bool:
    return node.get("type") == "end"


# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------


def _mermaid_escape(text: str) -> str:
    """Mermaid node labels live inside `[...]`; quote double-quotes and pipes."""
    return text.replace('"', "&quot;").replace("|", "&#124;")


def render_mermaid(graph: dict) -> str:
    """Render the graph as a Mermaid `flowchart TD` block.

    The leading `flowchart TD` line is intentionally bare (no fence) so
    callers can wrap it in either ```` ```mermaid ```` (GitHub) or feed
    it to a renderer directly.
    """
    nodes = _nodes(graph)
    if not nodes:
        return "flowchart TD\n  empty[\"(empty graph)\"]\n"

    lines: list[str] = ["flowchart TD"]
    entry = _entry(graph)

    for nid, node in nodes.items():
        speaker = node.get("speaker_ref") or "(narrator)"
        marker = " [entry]" if nid == entry else ""
        label = _mermaid_escape(f"{nid}{marker}\\n{node.get('type')} · {speaker}")
        if _is_end(node):
            lines.append(f"  {nid}([\"{label}\"]):::endNode")
        else:
            lines.append(f"  {nid}[\"{label}\"]")

    for from_id, to_id, opt in _edges(nodes):
        label = _edge_label(opt)
        if label:
            lines.append(f"  {from_id} -->|{_mermaid_escape(label)}| {to_id}")
        else:
            lines.append(f"  {from_id} --> {to_id}")

    lines.append("  classDef endNode fill:#fce4ec,stroke:#ad1457;")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# DOT (graphviz)
# ---------------------------------------------------------------------------


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\"", "\\\"")


def render_dot(graph: dict) -> str:
    nodes = _nodes(graph)
    if not nodes:
        return "digraph G {\n  empty [label=\"(empty graph)\"];\n}\n"

    lines: list[str] = [
        "digraph G {",
        "  rankdir=TB;",
        "  node [shape=box, fontname=\"Helvetica\"];",
    ]
    entry = _entry(graph)

    for nid, node in nodes.items():
        speaker = node.get("speaker_ref") or "(narrator)"
        marker = " [entry]" if nid == entry else ""
        label = _dot_escape(f"{nid}{marker}\\n{node.get('type')} · {speaker}")
        attrs = f"label=\"{label}\""
        if _is_end(node):
            attrs += ", shape=oval, style=filled, fillcolor=\"#fce4ec\""
        lines.append(f"  \"{nid}\" [{attrs}];")

    for from_id, to_id, opt in _edges(nodes):
        label = _edge_label(opt)
        if label:
            lines.append(
                f"  \"{from_id}\" -> \"{to_id}\" "
                f"[label=\"{_dot_escape(label)}\"];"
            )
        else:
            lines.append(f"  \"{from_id}\" -> \"{to_id}\";")

    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# ASCII
# ---------------------------------------------------------------------------


def _topological_layers(nodes: dict[str, dict]) -> list[list[str]]:
    """Return BFS-style layers from the graph entry; falls back to one-per-row.

    networkx.topological_generations() needs a DAG. DialogueGraphs are
    expected DAGs (graph_check rejects cycles), but a malformed graph
    must still render — we catch NetworkXUnfeasible and fall back to one
    node per layer in insertion order so the call never raises.
    """
    g = nx.DiGraph()
    g.add_nodes_from(nodes.keys())
    for from_id, to_id, _opt in _edges(nodes):
        if to_id in nodes:
            g.add_edge(from_id, to_id)
    try:
        return [list(layer) for layer in nx.topological_generations(g)]
    except nx.NetworkXUnfeasible:
        return [[nid] for nid in nodes]


def _ascii_box(nid: str, node: dict, max_width: int) -> list[str]:
    """Three-line box: `┌──┐ / │ id │ / └──┘` with a type/speaker subscript."""
    speaker = node.get("speaker_ref") or "(narr)"
    sub = f"{node.get('type', '?')[:3]} · {speaker}"
    inner_w = max(len(nid), len(sub))
    inner_w = min(inner_w, max(8, max_width - 4))
    nid_clipped = nid[:inner_w]
    sub_clipped = sub[:inner_w]
    is_end = _is_end(node)
    horiz = "═" if is_end else "─"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if is_end else ("┌", "┐", "└", "┘")
    side = "║" if is_end else "│"
    top = f"{tl}{horiz * (inner_w + 2)}{tr}"
    mid_id = f"{side} {nid_clipped:<{inner_w}} {side}"
    mid_sub = f"{side} {sub_clipped:<{inner_w}} {side}"
    bot = f"{bl}{horiz * (inner_w + 2)}{br}"
    return [top, mid_id, mid_sub, bot]


def render_ascii(graph: dict, max_width: int = 80) -> str:
    """Render the graph as a layered ASCII diagram.

    Layout: each topological layer is one horizontal band of boxes,
    separated by a blank line. Edges are listed below the diagram as
    `from → to  [labels]` so a reviewer can see the wiring without
    fighting ASCII edge routing.
    """
    nodes = _nodes(graph)
    if not nodes:
        return "(empty graph)\n"

    layers = _topological_layers(nodes)
    entry = _entry(graph)

    lines: list[str] = []
    if entry:
        lines.append(f"entry: {entry}")
        lines.append("")

    for layer_idx, layer in enumerate(layers):
        boxes = [_ascii_box(nid, nodes[nid], max_width) for nid in layer]
        # Pack boxes side-by-side; wrap to a new band if width would overflow.
        packed_rows: list[list[list[str]]] = [[]]
        cur_w = 0
        for box in boxes:
            box_w = len(box[0])
            if packed_rows[-1] and cur_w + box_w + 2 > max_width:
                packed_rows.append([])
                cur_w = 0
            packed_rows[-1].append(box)
            cur_w += box_w + 2
        for band in packed_rows:
            for line_idx in range(4):
                lines.append("  ".join(box[line_idx] for box in band))
            lines.append("")
        if layer_idx < len(layers) - 1:
            lines.append("  │")
            lines.append("  ▼")
            lines.append("")

    edges = _edges(nodes)
    if edges:
        lines.append("edges:")
        for from_id, to_id, opt in edges:
            label = _edge_label(opt)
            if label:
                lines.append(f"  {from_id} → {to_id}  [{label}]")
            else:
                lines.append(f"  {from_id} → {to_id}")

    end_ids = [nid for nid, n in nodes.items() if _is_end(n)]
    if end_ids:
        lines.append("")
        lines.append(f"end nodes: {', '.join(end_ids)}")

    return "\n".join(lines) + "\n"
