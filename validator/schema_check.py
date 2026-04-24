"""第一层：JSON Schema 结构校验。

用 `/schema/` 下五个 JSON Schema 文件 + `jsonschema.Draft202012Validator` +
`referencing.Registry`（同 /engine/player.py）对一份 DialogueGraph 做结构校验。
每个错误以 Issue(level="schema", location=<RFC 6901 JSON Pointer>, message=...) 返回。
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .report import Issue

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
_SCHEMA_FILES = (
    "dialogue_graph.schema.json",
    "node.schema.json",
    "option.schema.json",
    "state_effect.schema.json",
    "state_condition.schema.json",
)


def _build_validator() -> Draft202012Validator:
    registry = Registry()
    for name in _SCHEMA_FILES:
        schema = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(
            uri=schema["$id"], resource=Resource.from_contents(schema)
        )
    root = json.loads(
        (_SCHEMA_DIR / "dialogue_graph.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(root, registry=registry)


_VALIDATOR = _build_validator()


def _escape_pointer_segment(seg: str) -> str:
    return seg.replace("~", "~0").replace("/", "~1")


def _to_json_pointer(path) -> str:
    parts = [_escape_pointer_segment(str(p)) for p in path]
    return "/" + "/".join(parts) if parts else ""


def check(graph: dict) -> list[Issue]:
    issues: list[Issue] = []
    for err in sorted(_VALIDATOR.iter_errors(graph), key=lambda e: list(e.absolute_path)):
        pointer = _to_json_pointer(err.absolute_path) or "<root>"
        issues.append(Issue(level="schema", location=pointer, message=err.message))
    return issues
