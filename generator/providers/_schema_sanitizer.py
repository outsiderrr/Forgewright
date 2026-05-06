"""Shared JSON-Schema → OpenAPI-subset sanitizer (R2.8 + R2.10a).

Both Gemini's ``response_schema`` and OpenAI-compatible relays that back
onto Gemini upstream (e.g. ``poloai.top``) accept only a strict subset of
JSON Schema. Sending the canonical schema through a thin ``$schema`` /
``$id`` strip is not enough: Gemini's protobuf request stage rejects
both the JSON-Schema array form ``"type": ["X", "null"]`` and the
2020-12 reference machinery (``$defs`` / ``$ref``) before any token is
spent — even when the request travels through an OpenAI relay.

R2.7 added ``PoloAIProvider`` with its own narrower sanitizer and shipped
without the type-array nullable rewrite that R2.2 had introduced for
Gemini. Baseline_006 (PR #22) caught the regression at 0% gross_pass_rate.
R2.8 unified the rule set into this shared module.

R2.10a adds ``$defs`` / ``$ref`` resolution. Pydantic's
``model_json_schema()`` emits both for nested models — the Node fill
schema has 14 ``$defs`` entries plus 23 ``$ref`` sites, including
recursive references via ``StateCondition`` (a discriminated union whose
``all_of`` / ``any_of`` / ``not`` arms cycle back to ``StateCondition``
itself). Baseline_009 (PR #27, commit 19531ef) caught this at 14/15 =
93.3% provider_error with body ``"Unknown name \"$defs\" at
'generation_config.response_schema'"`` + ``"Unknown name \"$ref\" at
'...properties[N].value'"``. PoloAI's relay surfaces the underlying
Gemini protobuf 400 wrapped as openai.RateLimitError + HTTP 429 — the
body excerpt is the only reliable disambiguator.

Rule set:

  1. Inline ``$defs`` + ``$ref``: extract the top-level ``$defs`` lookup
     table and recursively replace every ``$ref`` with a deep-walked
     copy of the referenced sub-schema. The top-level ``$defs`` key is
     dropped from the result. Sibling keywords on a ``$ref`` node
     (2020-12 style: ``{"$ref": "...", "description": "..."}``) merge
     onto the inlined sub-schema with sibling values winning.
  2. Cyclic refs (``StateCondition`` → ``StateConditionAllOf`` →
     ``StateCondition``) are replaced with the empty schema ``{}`` at
     the cycle point and a warning is logged. The validator layer
     keeps using the canonical, fully-recursive schema to check the
     LLM's response, so the lossy approximation only affects what
     Gemini sees at request time. Trade-off documented at the
     R2.10a kickoff: cyclic ``StateCondition`` is rare in fill output
     in practice (Option.condition is unset on the vast majority of
     baseline rows), and a finite truthful schema beats a request
     Gemini will reject before token generation.
  3. ``$ref`` targets outside ``#/$defs/<name>`` (e.g.
     ``#/properties/x``) raise :class:`NotImplementedError`. Pydantic
     never emits these and our hand-written schemas don't either, so a
     loud failure is safer than silently dropping the reference.
  4. Drop keywords the OpenAPI subset rejects (R2.2): ``$schema`` /
     ``$id`` / ``additionalProperties``.
  5. Rewrite ``"type": ["X", "null"]`` (or ``["null", "X"]``) into
     ``{"type": "X", "nullable": True}``; preserve sibling keywords
     (R2.2).
  6. Collapse trivially-duplicate ``["X", "X"]`` to ``"type": "X"``.
  7. Reject genuine multi-type unions (``["string", "integer"]``) with
     a ``NotImplementedError`` that names the JSON path — the right
     fix is in the schema source.
  8. Reject ``["null"]`` / ``[]`` with a ``ValueError`` for the same
     reason.

The original schema is left intact so the validator layer keeps using
the canonical JSON-Schema form.
"""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

# Keywords stripped recursively. ``additionalProperties`` is in the set
# because Gemini's protobuf rejects it; OpenAI strict json_schema mode
# wants it, but every PoloAI request goes through to Gemini upstream so
# the strict-mode benefit is moot in practice and the protobuf rejection
# is the binding constraint.
_UNSUPPORTED_KEYWORDS = frozenset({"additionalProperties", "$schema", "$id"})

_DEFS_REF_PREFIX = "#/$defs/"


def sanitize_schema_for_openapi(schema: Any, _path: str = "") -> Any:
    """Adapt JSON Schema input into the OpenAPI subset Gemini and OpenAI
    relays backed by Gemini accept.

    See module docstring for the full rule set. The transform is two
    passes: (1) inline ``$defs`` / ``$ref`` to get a reference-free
    schema, then (2) recursively strip unsupported keywords and rewrite
    nullable type-arrays.
    """
    inlined = _inline_refs(schema, _path)
    return _strip_and_rewrite(inlined, _path)


# ---------------------------------------------------------------------------
# Pass 1 — $defs / $ref inlining
# ---------------------------------------------------------------------------


def _inline_refs(schema: Any, path: str) -> Any:
    """Resolve ``$defs`` + ``$ref`` so the result contains no JSON-Schema
    reference machinery.

    Top-level ``$defs`` is the only definitions container considered;
    nested ``$defs`` (unusual but legal in 2020-12) is left in place and
    will be flagged downstream if it carries any keyword the OpenAPI
    subset rejects. Pydantic's ``model_json_schema()`` and our
    hand-written schemas always put ``$defs`` at the top level, so this
    is sufficient in practice.
    """
    if not isinstance(schema, dict):
        return schema
    defs_raw = schema.get("$defs")
    defs: dict[str, Any] = defs_raw if isinstance(defs_raw, dict) else {}
    body = {k: v for k, v in schema.items() if k != "$defs"}
    return _walk_inline(body, defs, expanding=frozenset(), path=path)


def _walk_inline(
    node: Any,
    defs: dict[str, Any],
    expanding: frozenset[str],
    path: str,
) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref_value = node["$ref"]
            ref_name = _parse_def_ref(ref_value, path)
            if ref_name in expanding:
                _LOG.warning(
                    "schema sanitizer: cyclic $ref %r at path=%s; "
                    "replacing with empty schema {}",
                    ref_value,
                    path or "<root>",
                )
                base_inlined: dict = {}
            elif ref_name not in defs:
                raise NotImplementedError(
                    f"Schema sanitizer: $ref {ref_value!r} at "
                    f"path={path or '<root>'} points to a name not in "
                    f"$defs (known: {sorted(defs)!r})"
                )
            else:
                base_inlined = _walk_inline(
                    defs[ref_name],
                    defs,
                    expanding | {ref_name},
                    path,
                )
                if not isinstance(base_inlined, dict):
                    _LOG.warning(
                        "schema sanitizer: $defs[%s] at path=%s inlined "
                        "to non-dict %s; using {} instead",
                        ref_name,
                        path or "<root>",
                        type(base_inlined).__name__,
                    )
                    base_inlined = {}
            siblings = {
                k: _walk_inline(v, defs, expanding, _join_path(path, k))
                for k, v in node.items()
                if k != "$ref"
            }
            return {**base_inlined, **siblings}
        return {
            k: _walk_inline(v, defs, expanding, _join_path(path, k))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [
            _walk_inline(item, defs, expanding, f"{path}[{i}]")
            for i, item in enumerate(node)
        ]
    return node


def _parse_def_ref(ref: Any, path: str) -> str:
    if not isinstance(ref, str) or not ref.startswith(_DEFS_REF_PREFIX):
        raise NotImplementedError(
            f"Schema sanitizer: only ``#/$defs/<name>`` references are "
            f"supported; got $ref={ref!r} at path={path or '<root>'}"
        )
    return ref[len(_DEFS_REF_PREFIX):]


# ---------------------------------------------------------------------------
# Pass 2 — keyword strip + nullable rewrite
# ---------------------------------------------------------------------------


def _strip_and_rewrite(schema: Any, _path: str = "") -> Any:
    if isinstance(schema, dict):
        converted = _convert_nullable_type_array(schema, _path)
        return {
            k: _strip_and_rewrite(v, _join_path(_path, k))
            for k, v in converted.items()
            if k not in _UNSUPPORTED_KEYWORDS
        }
    if isinstance(schema, list):
        return [
            _strip_and_rewrite(item, f"{_path}[{i}]")
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
