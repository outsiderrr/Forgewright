"""Tests for `_sanitize_schema_for_gemini` — JSON Schema → Gemini OpenAPI subset.

Three concerns:

1. JSON-Schema type-array nullable form (`"type": ["X", "null"]`) must be
   rewritten to OpenAPI nullable form (`{"type": "X", "nullable": True}`).
   Gemini's Pydantic client-side validator rejects the array form
   pre-flight — see gemini_sdk_quirks #3 (T-2.12 baseline_005 client-side
   rejection on _SKELETON_RESPONSE_SCHEMA).

2. Pre-existing keyword stripping (additionalProperties / $schema / $id)
   must keep working through the rewritten code path.

3. JSON-Schema 2020-12 reference machinery (`$defs` / `$ref`) must be
   inlined before being sent to Gemini's response_schema. Gemini's
   protobuf rejects both keywords with "Unknown name \\"$defs\\"" /
   "Unknown name \\"$ref\\"" errors. Pydantic's `model_json_schema()`
   emits both for nested models — this is what baseline_009 (PR #27)
   caught at 14/15 = 93.3% provider_error.

The real `_SKELETON_RESPONSE_SCHEMA` from `scene_strategies` is read-only
fixture: this test verifies sanitize is a closed transform on it (no
list-form `type` survives) without modifying the source.
"""

from __future__ import annotations

import pytest

from generator.providers.gemini import _sanitize_schema_for_gemini
from generator.scene_strategies import _SKELETON_RESPONSE_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _walk_types(node):
    """Yield every `type` value found anywhere in a schema subtree."""
    if isinstance(node, dict):
        if "type" in node:
            yield node["type"]
        for v in node.values():
            yield from _walk_types(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_types(item)


def _walk_keys(node):
    """Yield every dict key found anywhere in a schema subtree."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


# ---------------------------------------------------------------------------
# Real schema sanity — _SKELETON_RESPONSE_SCHEMA from scene_strategies
# ---------------------------------------------------------------------------


def test_skeleton_schema_sanitize_has_no_list_type_residue() -> None:
    sanitized = _sanitize_schema_for_gemini(_SKELETON_RESPONSE_SCHEMA)
    for t in _walk_types(sanitized):
        assert not isinstance(t, list), f"list-form type leaked through sanitize: {t!r}"


def test_skeleton_schema_speaker_ref_becomes_openapi_nullable() -> None:
    sanitized = _sanitize_schema_for_gemini(_SKELETON_RESPONSE_SCHEMA)
    speaker_ref = (
        sanitized["properties"]["nodes"]["items"]["properties"]["speaker_ref"]
    )
    assert speaker_ref["type"] == "string"
    assert speaker_ref["nullable"] is True


def test_skeleton_schema_sanitize_does_not_mutate_source() -> None:
    # Source must keep the JSON Schema standard form. Sanitizer is a
    # compatibility layer, not a rewrite of the canonical schema.
    original_speaker_ref_type = (
        _SKELETON_RESPONSE_SCHEMA["properties"]["nodes"]["items"]
        ["properties"]["speaker_ref"]["type"]
    )
    _sanitize_schema_for_gemini(_SKELETON_RESPONSE_SCHEMA)
    after_speaker_ref_type = (
        _SKELETON_RESPONSE_SCHEMA["properties"]["nodes"]["items"]
        ["properties"]["speaker_ref"]["type"]
    )
    assert original_speaker_ref_type == ["string", "null"]
    assert after_speaker_ref_type == ["string", "null"]


# ---------------------------------------------------------------------------
# Synthetic fixtures — edge cases
# ---------------------------------------------------------------------------


def test_nullable_string_x_then_null_order() -> None:
    schema = {"type": ["string", "null"], "description": "name or unset"}
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized == {
        "type": "string",
        "nullable": True,
        "description": "name or unset",
    }


def test_nullable_null_then_x_order() -> None:
    schema = {"type": ["null", "integer"], "minimum": 0}
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized == {"type": "integer", "nullable": True, "minimum": 0}


def test_sibling_fields_preserved_through_conversion() -> None:
    schema = {
        "type": ["string", "null"],
        "description": "freeform",
        "pattern": r"^[a-z]+$",
        "enum": ["a", "b", None],
        "minLength": 1,
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized["type"] == "string"
    assert sanitized["nullable"] is True
    assert sanitized["description"] == "freeform"
    assert sanitized["pattern"] == r"^[a-z]+$"
    assert sanitized["enum"] == ["a", "b", None]
    assert sanitized["minLength"] == 1


def test_multi_type_non_null_union_raises() -> None:
    schema = {"type": ["string", "integer"]}
    with pytest.raises(NotImplementedError) as exc_info:
        _sanitize_schema_for_gemini(schema)
    msg = str(exc_info.value)
    assert "multi-type unions" in msg
    assert "string" in msg and "integer" in msg


def test_three_type_union_with_null_still_raises() -> None:
    # ["string", "integer", "null"] — multi-type even after stripping null.
    schema = {"type": ["string", "integer", "null"]}
    with pytest.raises(NotImplementedError):
        _sanitize_schema_for_gemini(schema)


def test_lone_null_array_raises() -> None:
    schema = {"type": ["null"]}
    with pytest.raises(ValueError) as exc_info:
        _sanitize_schema_for_gemini(schema)
    assert "expected at least one non-null type" in str(exc_info.value)


def test_empty_type_array_raises() -> None:
    schema = {"type": []}
    with pytest.raises(ValueError):
        _sanitize_schema_for_gemini(schema)


def test_duplicate_same_type_collapses() -> None:
    # Edge case but reasonable: ["string", "string"] becomes "string".
    schema = {"type": ["string", "string"], "description": "dup"}
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized == {"type": "string", "description": "dup"}
    assert "nullable" not in sanitized


def test_duplicate_with_null_collapses() -> None:
    schema = {"type": ["string", "null", "string"]}
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized == {"type": "string", "nullable": True}


def test_scalar_type_passes_through_untouched() -> None:
    schema = {"type": "string", "description": "x"}
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized == {"type": "string", "description": "x"}


# ---------------------------------------------------------------------------
# Recursion — nested properties / items / $defs
# ---------------------------------------------------------------------------


def test_nullable_inside_nested_properties_is_converted() -> None:
    schema = {
        "type": "object",
        "properties": {
            "outer": {
                "type": "object",
                "properties": {
                    "inner": {"type": ["string", "null"]},
                },
            },
        },
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    inner = sanitized["properties"]["outer"]["properties"]["inner"]
    assert inner == {"type": "string", "nullable": True}


def test_nullable_inside_array_items_is_converted() -> None:
    schema = {
        "type": "array",
        "items": {"type": ["integer", "null"], "minimum": 0},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized["items"] == {
        "type": "integer",
        "nullable": True,
        "minimum": 0,
    }


def test_nullable_inside_defs_is_inlined_and_converted() -> None:
    # R2.10a: $defs is now inlined and dropped from the result; the
    # nullable rewrite must reach into the inlined sub-schema.
    schema = {
        "type": "object",
        "$defs": {
            "MaybeName": {"type": ["string", "null"]},
        },
        "properties": {"name": {"$ref": "#/$defs/MaybeName"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    assert sanitized["properties"]["name"] == {
        "type": "string",
        "nullable": True,
    }


def test_multi_type_union_nested_reports_path() -> None:
    schema = {
        "type": "object",
        "properties": {
            "outer": {
                "type": "object",
                "properties": {
                    "bad": {"type": ["string", "integer"]},
                },
            },
        },
    }
    with pytest.raises(NotImplementedError) as exc_info:
        _sanitize_schema_for_gemini(schema)
    # Path should locate the offending node so the schema author can fix
    # the source. Exact format isn't load-bearing; presence of the field
    # name is.
    assert "bad" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Regression — existing keyword stripping still works through new code path
# ---------------------------------------------------------------------------


def test_unsupported_keywords_still_stripped_alongside_nullable_rewrite() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "x.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": ["string", "null"]},
            "tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"v": {"type": ["integer", "null"]}},
                },
            },
        },
    }
    sanitized = _sanitize_schema_for_gemini(schema)

    assert "$schema" not in sanitized
    assert "$id" not in sanitized
    assert "additionalProperties" not in sanitized
    assert "additionalProperties" not in sanitized["properties"]["tags"]["items"]

    assert sanitized["properties"]["name"] == {"type": "string", "nullable": True}
    assert sanitized["properties"]["tags"]["items"]["properties"]["v"] == {
        "type": "integer",
        "nullable": True,
    }


# ---------------------------------------------------------------------------
# R2.10a — $defs / $ref inlining
# ---------------------------------------------------------------------------


def test_inlines_simple_def() -> None:
    schema = {
        "type": "object",
        "$defs": {
            "Name": {"type": "string", "minLength": 1},
        },
        "properties": {"name": {"$ref": "#/$defs/Name"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    assert "$ref" not in list(_walk_keys(sanitized))
    assert sanitized["properties"]["name"] == {"type": "string", "minLength": 1}


def test_inlines_nested_def() -> None:
    # A → B → C: three layers of $ref must all resolve.
    schema = {
        "$defs": {
            "A": {"$ref": "#/$defs/B"},
            "B": {"$ref": "#/$defs/C"},
            "C": {"type": "integer", "minimum": 0},
        },
        "properties": {"x": {"$ref": "#/$defs/A"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    assert "$ref" not in list(_walk_keys(sanitized))
    assert sanitized["properties"]["x"] == {"type": "integer", "minimum": 0}


def test_inlines_multi_use_def() -> None:
    # Same $defs entry referenced from two different positions; both
    # sites must independently inline (the result has no shared aliasing
    # so a downstream mutation of one wouldn't affect the other).
    schema = {
        "$defs": {
            "Coord": {"type": "number"},
        },
        "properties": {
            "x": {"$ref": "#/$defs/Coord"},
            "y": {"$ref": "#/$defs/Coord"},
        },
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    assert sanitized["properties"]["x"] == {"type": "number"}
    assert sanitized["properties"]["y"] == {"type": "number"}
    # Independent dicts (no aliasing).
    assert sanitized["properties"]["x"] is not sanitized["properties"]["y"]


def test_ref_with_sibling_keywords_merges_with_sibling_priority() -> None:
    # 2020-12 sibling form: {"$ref": "...", "description": "..."} —
    # sibling keywords merge onto the inlined sub-schema with sibling
    # values winning over the referenced sub-schema's same-named keys.
    schema = {
        "$defs": {
            "Base": {
                "type": "string",
                "description": "base description",
                "minLength": 1,
            },
        },
        "properties": {
            "x": {
                "$ref": "#/$defs/Base",
                "description": "override description",
            },
        },
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    x = sanitized["properties"]["x"]
    assert x["type"] == "string"
    assert x["minLength"] == 1
    # Sibling description wins over the base.
    assert x["description"] == "override description"


def test_circular_ref_replaced_with_empty_schema() -> None:
    # A→B, B→A direct cycle. R2.10a chose lossy approximation
    # (collapse cycle point to {}) rather than raise — the canonical
    # use case (Pydantic-emitted StateCondition fill schema) has cycles
    # by design and we need to keep generation flowing. Validator layer
    # still uses the canonical recursive schema for response checks.
    schema = {
        "$defs": {
            "A": {"type": "object", "properties": {"b": {"$ref": "#/$defs/B"}}},
            "B": {"type": "object", "properties": {"a": {"$ref": "#/$defs/A"}}},
        },
        "properties": {"root": {"$ref": "#/$defs/A"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    assert "$ref" not in list(_walk_keys(sanitized))
    # Walk down: root → A inlined → properties.b → B inlined →
    # properties.a → A again (cycle) → {}.
    cycle_point = (
        sanitized["properties"]["root"]["properties"]["b"]["properties"]["a"]
    )
    assert cycle_point == {}


def test_self_ref_replaced_with_empty_schema() -> None:
    # Self-reference: A → A. Should replace inner A with {} on the
    # second hit and keep the outer A's siblings.
    schema = {
        "$defs": {
            "Tree": {
                "type": "object",
                "properties": {"child": {"$ref": "#/$defs/Tree"}},
            },
        },
        "properties": {"root": {"$ref": "#/$defs/Tree"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert "$defs" not in sanitized
    root = sanitized["properties"]["root"]
    assert root["type"] == "object"
    assert root["properties"]["child"] == {}


def test_ref_outside_defs_raises() -> None:
    # JSON pointer to a non-$defs path. Pydantic doesn't emit these and
    # our hand-written schemas don't either; raising forces the schema
    # author to fix the source rather than letting us silently drop.
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "alias": {"$ref": "#/properties/name"},
        },
    }
    with pytest.raises(NotImplementedError) as exc_info:
        _sanitize_schema_for_gemini(schema)
    assert "#/$defs/" in str(exc_info.value)
    assert "#/properties/name" in str(exc_info.value)


def test_ref_to_unknown_def_raises() -> None:
    schema = {
        "$defs": {"Known": {"type": "string"}},
        "properties": {"x": {"$ref": "#/$defs/Missing"}},
    }
    with pytest.raises(NotImplementedError) as exc_info:
        _sanitize_schema_for_gemini(schema)
    assert "Missing" in str(exc_info.value)


def test_node_fill_schema_round_trip_has_no_ref_machinery() -> None:
    # The fill schema that breaks Gemini protobuf in baseline_009. After
    # R2.10a sanitize, no $defs / $ref / $schema / $id residue may
    # remain — that's the load-bearing invariant the upstream call
    # relies on.
    from generator.models import Node

    fill_schema = Node.model_json_schema()
    sanitized = _sanitize_schema_for_gemini(fill_schema)

    keys = set(_walk_keys(sanitized))
    assert "$defs" not in keys
    assert "$ref" not in keys
    assert "$schema" not in keys
    assert "$id" not in keys
    assert "additionalProperties" not in keys
    # And no list-form `type` survived (R2.2 invariant carried forward).
    for t in _walk_types(sanitized):
        assert not isinstance(t, list), f"list-form type leaked: {t!r}"


def test_node_fill_schema_round_trip_does_not_mutate_source() -> None:
    # Validator layer keeps using the canonical fully-recursive schema;
    # sanitizer must not mutate the Pydantic-emitted schema in place.
    from generator.models import Node

    fill_schema = Node.model_json_schema()
    assert "$defs" in fill_schema  # premise
    _sanitize_schema_for_gemini(fill_schema)
    assert "$defs" in fill_schema  # still there
    # And StateCondition still has its anyOf with $ref children.
    state_condition = fill_schema["$defs"]["StateCondition"]
    assert "anyOf" in state_condition
    assert any("$ref" in arm for arm in state_condition["anyOf"])
