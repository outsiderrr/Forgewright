"""T-0.7 StateCondition 求值器。

阶段 0 白名单（D6 决议 2026-04-24，承袭 SCHEMA_v0.md §3.5 候选集）：
eq / neq / gt / gte / lt / lte / has / has_not。

复合形态：all_of / any_of / not（D4 决议，叶/复合互斥由 JSON Schema 层强制）。

语义细节：
- 缺失 path 时：has → False，has_not → True（SCHEMA_v0.md §3.5 的自然默认）。
- 缺失 path 对 eq：等价于 None == value（多数情况 False，除非 value 也为 None）。
- 缺失 path 对 gt/gte/lt/lte：返回 False（与 None 无法有序比较）。
- has/has_not 对字符串与数组均生效；对其它非字符串/数组的已存在值返回 False（has）/ True（has_not）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .world_state import WorldState

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schema"
    / "state_condition.schema.json"
)
_CONDITION_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_CONDITION_VALIDATOR = Draft202012Validator(_CONDITION_SCHEMA)


def evaluate_condition(state: WorldState, condition: dict) -> bool:
    errors = sorted(_CONDITION_VALIDATOR.iter_errors(condition), key=lambda e: e.path)
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ValueError(f"StateCondition schema violation: {messages}")
    return _eval(state, condition)


def _eval(state: WorldState, condition: dict) -> bool:
    if "all_of" in condition:
        return all(_eval(state, c) for c in condition["all_of"])
    if "any_of" in condition:
        return any(_eval(state, c) for c in condition["any_of"])
    if "not" in condition:
        return not _eval(state, condition["not"])

    op = condition["op"]
    path = condition["path"]
    value = condition["value"]

    if not isinstance(path, str):
        raise ValueError(
            "StateCondition.path must be a dotted string per D5 (2026-04-24); "
            f"got {type(path).__name__}"
        )

    current: Any = state.get(path)

    if op == "eq":
        return current == value
    if op == "neq":
        return current != value
    if op in ("gt", "gte", "lt", "lte"):
        if current is None:
            return False
        try:
            if op == "gt":
                return current > value
            if op == "gte":
                return current >= value
            if op == "lt":
                return current < value
            return current <= value
        except TypeError:
            return False
    if op == "has":
        if current is None or not isinstance(current, (str, list)):
            return False
        return value in current
    if op == "has_not":
        if current is None or not isinstance(current, (str, list)):
            return True
        return value not in current

    raise ValueError(f"unknown op {op!r} (defensive; schema enum should have caught it)")
