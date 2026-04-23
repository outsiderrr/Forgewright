"""T-0.7 阶段 0 世界状态总线。

内部用嵌套 dict 存储；对外 path 采用点分字符串（D5 决议，2026-04-24）。
类型白名单：bool / int / float / str / list / dict；其他类型的写入拒收。
"""
from __future__ import annotations

from typing import Any

_ALLOWED_VALUE_TYPES: tuple[type, ...] = (bool, int, float, str, list, dict)


def _split_path(path: str) -> list[str]:
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")
    if not path:
        raise ValueError("path must be a non-empty string")
    segments = path.split(".")
    if any(seg == "" for seg in segments):
        raise ValueError(f"path contains empty segment: {path!r}")
    return segments


class WorldState:
    """嵌套 dict 支持的状态总线。路径是点分字符串。"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, path: str) -> Any | None:
        segments = _split_path(path)
        node: Any = self._data
        for seg in segments:
            if not isinstance(node, dict) or seg not in node:
                return None
            node = node[seg]
        return node

    def has(self, path: str) -> bool:
        segments = _split_path(path)
        node: Any = self._data
        for seg in segments:
            if not isinstance(node, dict) or seg not in node:
                return False
            node = node[seg]
        return True

    def set(self, path: str, value: Any) -> None:
        if not isinstance(value, _ALLOWED_VALUE_TYPES):
            raise TypeError(
                f"unsupported value type {type(value).__name__}; "
                f"allowed: bool/int/float/str/list/dict"
            )
        segments = _split_path(path)
        node = self._data
        for seg in segments[:-1]:
            if seg not in node or not isinstance(node[seg], dict):
                node[seg] = {}
            node = node[seg]
        node[segments[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        return self._data
