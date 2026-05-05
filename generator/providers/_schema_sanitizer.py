"""Shared JSON-Schema → OpenAPI-subset sanitizer (R2.8).

Both Gemini's ``response_schema`` and OpenAI-compatible relays that back
onto Gemini upstream (e.g. ``poloai.top``) accept only a strict subset of
JSON Schema. Sending the canonical schema through a thin ``$schema`` /
``$id`` strip is not enough: Gemini's protobuf request stage still
rejects the JSON-Schema array form ``"type": ["X", "null"]`` before any
token is spent — even when the request travels through an OpenAI relay.

R2.7 added ``PoloAIProvider`` with its own narrower sanitizer and shipped
without the type-array nullable rewrite that R2.2 had introduced for
Gemini. Baseline_006 (PR #22) caught the regression at 0% gross_pass_rate.
This module exists so the rule set lives in exactly one place; both
providers share it via thin aliases.

Rule set (carried over from R2.2):

  1. Drop keywords the OpenAPI subset rejects:
     ``additionalProperties`` / ``$schema`` / ``$id``.
  2. Rewrite ``"type": ["X", "null"]`` (or ``["null", "X"]``) into
     ``{"type": "X", "nullable": True}``; preserve sibling keywords.
  3. Collapse trivially-duplicate ``["X", "X"]`` to ``"type": "X"``.
  4. Reject genuine multi-type unions (``["string", "integer"]``) with a
     ``NotImplementedError`` that names the JSON path — the right fix is
     in the schema source.
  5. Reject ``["null"]`` / ``[]`` with a ``ValueError`` for the same
     reason.

The original schema is left intact so the validator layer keeps using
the canonical JSON-Schema form.
"""

from __future__ import annotations

from typing import Any

# Keywords stripped recursively. ``additionalProperties`` is in the set
# because Gemini's protobuf rejects it; OpenAI strict json_schema mode
# wants it, but every PoloAI request goes through to Gemini upstream so
# the strict-mode benefit is moot in practice and the protobuf rejection
# is the binding constraint.
_UNSUPPORTED_KEYWORDS = frozenset({"additionalProperties", "$schema", "$id"})


def sanitize_schema_for_openapi(schema: Any, _path: str = "") -> Any:
    """Adapt JSON Schema input into the OpenAPI subset Gemini and OpenAI
    relays backed by Gemini accept.

    See module docstring for the full rule set. Recursive over nested
    ``dict`` and ``list`` (covers ``properties``, ``items``, ``$defs``).
    """
    if isinstance(schema, dict):
        converted = _convert_nullable_type_array(schema, _path)
        return {
            k: sanitize_schema_for_openapi(v, _join_path(_path, k))
            for k, v in converted.items()
            if k not in _UNSUPPORTED_KEYWORDS
        }
    if isinstance(schema, list):
        return [
            sanitize_schema_for_openapi(item, f"{_path}[{i}]")
            for i, item in enumerate(schema)
        ]
    return schema


def _convert_nullable_type_array(schema_dict: dict, path: str) -> dict:
    type_value = schema_dict.get("type")
    if not isinstance(type_value, list):
        return schema_dict

    non_null = [t for t in type_value if t != "null"]
    has_null = "null" in type_value
    where = path or "<root>"

    if not non_null:
        # ["null"] alone, or [] — neither is meaningful for response_schema.
        raise ValueError(
            f"Schema sanitizer: invalid type={type_value!r} at path={where}; "
            "expected at least one non-null type"
        )

    distinct = set(non_null)
    if len(distinct) > 1:
        raise NotImplementedError(
            f"Schema sanitizer: OpenAPI subset doesn't support multi-type unions; "
            f"got type={type_value!r} at path={where}"
        )

    new_dict = dict(schema_dict)
    new_dict["type"] = next(iter(distinct))
    if has_null:
        new_dict["nullable"] = True
    return new_dict


def _join_path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key
