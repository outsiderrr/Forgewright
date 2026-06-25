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

from generator.models import DialogueGraph, ImageAsset

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


def test_dialogue_graph_roundtrip_with_structured_dialogue() -> None:
    """ADR-040：携带 node.dialogue=[{speaker_ref, line}] 的图 survive validate→dump→reload.

    锁住 codegen 对新 optional `dialogue` 字段的捕获——若 regenerate_models.sh
    没把字段带进生成模型（extra='forbid' 会拒收），model_validate 即抛错。
    """
    original = {
        "schema_version": "0.1.1",
        "graph_id": "adr040_roundtrip",
        "entry_node_id": "opening",
        "scene_anchor": "scene_x",
        "character_refs": ["char_a"],
        "nodes": {
            "opening": {
                "node_id": "opening",
                "type": "dialogue",
                "narration": "门吱呀一声开了，灯芯抖了一下。",
                "speaker_ref": None,
                "location_ref": "scene_x",
                "dialogue": [
                    {"speaker_ref": "char_a", "line": "你来得正好。"},
                    {"speaker_ref": "char_a", "line": "坐，别站着。"},
                ],
                "options": [
                    {
                        "option_id": "opt_sit",
                        "text": "我坐下。",
                        "target_node_id": "the_end",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    }
                ],
            },
            "the_end": {
                "node_id": "the_end",
                "type": "end",
                "narration": "灯灭了。",
                "speaker_ref": None,
                "location_ref": "scene_x",
                "options": [],
            },
        },
    }

    graph = DialogueGraph.model_validate(original)
    roundtripped = json.loads(graph.model_dump_json(by_alias=True, exclude_unset=True))
    assert roundtripped == original


def test_image_asset_roundtrip_minimal_valid_object() -> None:
    """Minimum-required-fields ImageAsset survives validate -> dump -> reload.

    This locks the codegen step: if the second `datamodel-code-generator` pass
    in `regenerate_models.sh` ever drops a required field, mistypes an enum,
    or loosens a pattern, the load or the equality assertion will catch it.
    """
    original = {
        "asset_id": "img_vellin_neutral",
        "asset_kind": "character_sheet",
        "source_mode": "manual",
        "format": "png",
        "width": 1024,
        "height": 1024,
        "file_path": "content/visuals/vellin/img_vellin_neutral.png",
        # Pydantic AwareDatetime normalizes UTC to the trailing "Z" form on
        # dump. Use it in the fixture too so dump == load is bit-identical.
        "created_at": "2026-05-01T12:00:00Z",
        "target_ref": "char_vellin",
        "target_type": "character",
        "asset_role": "character_sheet",
    }

    asset = ImageAsset.model_validate(original)
    dumped = json.loads(asset.model_dump_json(exclude_unset=True))

    assert dumped == original
