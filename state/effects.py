"""T-0.7 StateEffect 执行器。

阶段 0 白名单（D6 决议 2026-04-24，承袭 SCHEMA_v0.md §3.4 候选集）：
set / inc / dec / add / remove。

path 采用点分字符串（D5 决议 2026-04-24）；schema 层仍接受段数组形态以兼容未来，
但本执行器仅接受字符串形式（对外 API 约束）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .world_state import WorldState

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "schema" / "state_effect.schema.json"
)
_EFFECT_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_EFFECT_VALIDATOR = Draft202012Validator(_EFFECT_SCHEMA)


def _require_numeric(name: str, path: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{name} requires numeric {path!r}, got {type(value).__name__}"
        )


def apply_effect(state: WorldState, effect: dict) -> None:
    errors = sorted(_EFFECT_VALIDATOR.iter_errors(effect), key=lambda e: e.path)
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ValueError(f"StateEffect schema violation: {messages}")

    op = effect["op"]
    path = effect["path"]
    value = effect["value"]

    if not isinstance(path, str):
        raise ValueError(
            "StateEffect.path must be a dotted string per D5 (2026-04-24); "
            f"got {type(path).__name__}"
        )

    if op == "set":
        state.set(path, value)
        return

    if op in ("inc", "dec"):
        _require_numeric(op, path, value)
        current = state.get(path)
        if current is None:
            current = 0
        elif isinstance(current, bool) or not isinstance(current, (int, float)):
            raise TypeError(
                f"{op} requires numeric current value at {path!r}, "
                f"got {type(current).__name__}"
            )
        delta = value if op == "inc" else -value
        state.set(path, current + delta)
        return

    if op == "add":
        current = state.get(path)
        if current is None:
            current = []
        if not isinstance(current, list):
            raise TypeError(
                f"add requires list at {path!r}, got {type(current).__name__}"
            )
        if value not in current:
            current = current + [value]
        state.set(path, current)
        return

    if op == "remove":
        current = state.get(path)
        if current is None:
            return
        if not isinstance(current, list):
            raise TypeError(
                f"remove requires list at {path!r}, got {type(current).__name__}"
            )
        if value in current:
            current = [x for x in current if x != value]
            state.set(path, current)
        return

    raise ValueError(f"unknown op {op!r} (defensive; schema enum should have caught it)")
