"""Tests for `_sanitize_schema_for_gemini` — JSON Schema → Gemini OpenAPI subset.

Two concerns:

1. JSON-Schema type-array nullable form (`"type": ["X", "null"]`) must be
   rewritten to OpenAPI nullable form (`{"type": "X", "nullable": True}`).
   Gemini's Pydantic client-side validator rejects the array form
   pre-flight — see gemini_sdk_quirks #3 (T-2.12 baseline_005 client-side
   rejection on _SKELETON_RESPONSE_SCHEMA).

2. Pre-existing keyword stripping (additionalProperties / $schema / $id)
   must keep working through the rewritten code path.

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


def test_nullable_inside_defs_is_converted() -> None:
    schema = {
        "type": "object",
        "$defs": {
            "MaybeName": {"type": ["string", "null"]},
        },
        "properties": {"name": {"$ref": "#/$defs/MaybeName"}},
    }
    sanitized = _sanitize_schema_for_gemini(schema)
    assert sanitized["$defs"]["MaybeName"] == {
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
