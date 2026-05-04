"""Smoke tests for /generator/graph_view.py (T-2.8 §4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator import graph_view


_GOLD_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "content" / "test_scene_v0" / "scene.json"
)


@pytest.fixture(scope="module")
def gold_graph() -> dict:
    return json.loads(_GOLD_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------


def test_mermaid_renders_gold_standard(gold_graph):
    out = graph_view.render_mermaid(gold_graph)
    assert out.startswith("flowchart TD\n")
    # Every node must appear in the rendered text — check a sampling of
    # the well-known《铁誓驿站》node IDs.
    for node_id in (
        "arrival_waystation",
        "vellin_confession",
        "end_silent_ally",
    ):
        assert node_id in out
    # End nodes get the dedicated class style.
    assert "endNode" in out
    # Conditional edges should carry the [cond] marker — the gold scene
    # has at least one conditional option (opt_read_the_room).
    assert "cond" in out


def test_mermaid_handles_empty_graph():
    out = graph_view.render_mermaid({})
    assert "flowchart TD" in out
    assert "empty graph" in out


# ---------------------------------------------------------------------------
# DOT
# ---------------------------------------------------------------------------


def test_dot_renders_gold_standard(gold_graph):
    out = graph_view.render_dot(gold_graph)
    assert out.startswith("digraph G {")
    assert "rankdir=TB" in out
    assert '"arrival_waystation"' in out
    assert "->" in out
    # Conditional edges retain the [cond] marker via edge label.
    assert "cond" in out


def test_dot_escapes_quotes_in_node_label():
    g = {
        "entry_node_id": "n",
        "nodes": {
            "n": {
                "type": "dialogue",
                "speaker_ref": 'char with "quote"',
                "options": [],
            }
        },
    }
    out = graph_view.render_dot(g)
    # Backslash-escaped quote inside the node label.
    assert '\\"quote\\"' in out


# ---------------------------------------------------------------------------
# ASCII
# ---------------------------------------------------------------------------


def test_ascii_renders_gold_standard(gold_graph):
    out = graph_view.render_ascii(gold_graph)
    assert "entry: arrival_waystation" in out
    assert "arrival_waystation" in out
    # Box-drawing characters present somewhere in the output.
    assert any(c in out for c in "─│┌┐└┘╔╗╚╝═║")
    # End nodes section names known endings.
    assert "end nodes:" in out


def test_ascii_falls_back_on_cyclic_graph():
    """A graph with a cycle must still render, even though
    networkx.topological_generations would normally raise."""
    g = {
        "entry_node_id": "a",
        "nodes": {
            "a": {
                "type": "dialogue",
                "options": [{"target_node_id": "b"}],
            },
            "b": {
                "type": "dialogue",
                "options": [{"target_node_id": "a"}],
            },
        },
    }
    out = graph_view.render_ascii(g)
    assert "a" in out and "b" in out
