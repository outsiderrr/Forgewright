"""Roundtrip the hand-written test scene through the auto-generated Pydantic models.

Loads /content/test_scene_v0/scene.json, parses it into DialogueGraph, dumps it
back via .model_dump_json(), and asserts deep equality with the original (modulo
key order and whitespace — we re-parse both sides into Python dicts).

Why this matters for T-1.3: it's the smoke test that confirms the codegen step
faithfully captures the Schema. If a generator bug or a Schema/scene drift
sneaks in, this test fires before any /generator code starts depending on the
models.
"""

from __future__ import annotations

import json
from pathlib import Path

from generator.models import DialogueGraph

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENE_PATH = REPO_ROOT / "content" / "test_scene_v0" / "scene.json"


def test_dialogue_graph_roundtrip_preserves_scene() -> None:
    raw = SCENE_PATH.read_text(encoding="utf-8")
    original = json.loads(raw)

    graph = DialogueGraph.model_validate(original)

    # by_alias=True so StateConditionNot.not_ serializes back as "not".
    # exclude_unset=True so we don't materialize optional fields that the
    # source JSON simply omitted (e.g. authoring, reachability_condition).
    dumped_json = graph.model_dump_json(by_alias=True, exclude_unset=True)
    roundtripped = json.loads(dumped_json)

    # Python dict equality is recursive and order-insensitive, which gives us
    # the "modulo key order and whitespace" comparison the task spec requires.
    assert roundtripped == original
