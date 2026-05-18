"""State path validator（状态路径校验器）— ADR-016 v0.4 第 6 命名空间 + ADR-034 D11 player-monotonic.

落地内容：
  - 6 个 state path 命名空间（namespace）：world.* / faction.<id>.* / relationship.<slug>.*
    / flag.* / player.* / knowledge.*
  - ADR-016 v0.4 修订承接 ADR-034.1：knowledge.* 是第 6 个命名空间（progressive disclosure /
    渐进揭露 + Ink LIST + Articy Glossary 业界对齐）。pattern：^knowledge\\.[a-z0-9_]+(\\.[a-z0-9_]+)*$
  - ADR-034 D11 player-monotonic 原则：在 monotonic 命名空间下，LLM 生成的 state_effect 只允许
    op ∈ {set, inc, add}；禁止 op ∈ {dec, remove}。Monotonic 清单：flag.player_* + knowledge.*
  - human-source 豁免（generation_trace.source == "human"）：作者手填内容不受 monotonic 约束

留给后续：
  - 跨场景 state path 唯一性 / 类型一致性等高级校验在本模块外（属 graph_validator / consistency_check）
  - 本模块只做单条 state_effect 的 path + op 合规性检查
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

# ---------- 6 个命名空间的正则 ----------

NAMESPACE_PATTERNS: dict[str, re.Pattern[str]] = {
    "world":        re.compile(r"^world\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
    "faction":      re.compile(r"^faction\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
    "relationship": re.compile(r"^relationship\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
    "flag":         re.compile(r"^flag\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
    "player":       re.compile(r"^player\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
    # ADR-016 v0.4 第 6 命名空间
    "knowledge":    re.compile(r"^knowledge\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),
}

# ---------- Monotonic（player-monotonic 原则）清单 ----------
# 凡 path 匹配以下任一 pattern，LLM 生成内容必须只用 set / inc / add；human-source 豁免

MONOTONIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^flag\.player_[a-z0-9_]+(\.[a-z0-9_]+)*$"),  # flag.player_* 玩家见证 flag
    re.compile(r"^knowledge\.[a-z0-9_]+(\.[a-z0-9_]+)*$"),    # knowledge.* 玩家知识
]

ALLOWED_OPS_MONOTONIC: frozenset[str] = frozenset({"set", "inc", "add"})
FORBIDDEN_OPS_MONOTONIC: frozenset[str] = frozenset({"dec", "remove"})

# state_effect.schema.json op enum 全集（与 schema 保持同步）
ALL_OPS: frozenset[str] = frozenset({"set", "inc", "dec", "add", "remove"})


# ---------- 单元函数 ----------

def _normalize_path(path: Any) -> Optional[str]:
    """把 state_effect.path 规范化成点分字符串；支持字符串 / 字符串段数组两种 schema 形态。

    返回 None 表示 path 形态不合法（不是 str 也不是 list[str]）。
    """
    if isinstance(path, str):
        return path
    if isinstance(path, list) and all(isinstance(seg, str) for seg in path):
        return ".".join(path)
    return None


def classify_namespace(path: str) -> Optional[str]:
    """返回 path 命中的命名空间名（world / faction / relationship / flag / player / knowledge）；
    不命中返回 None。
    """
    for name, pattern in NAMESPACE_PATTERNS.items():
        if pattern.match(path):
            return name
    return None


def is_monotonic_path(path: str) -> bool:
    """判断 path 是否落在 monotonic 命名空间内（flag.player_* 或 knowledge.*）。"""
    return any(p.match(path) for p in MONOTONIC_PATTERNS)


# ---------- 校验入口 ----------

def validate_effect_namespace(effect: dict[str, Any]) -> list[str]:
    """校验单条 state_effect 的 path 是否落入 6 个命名空间之一。

    返回错误消息列表；空 list 表示通过。
    """
    raw = effect.get("path")
    normalized = _normalize_path(raw)
    if normalized is None:
        return [
            f"state effect path 必须为字符串或字符串段数组，得到 {type(raw).__name__}"
        ]
    if classify_namespace(normalized) is None:
        return [
            f"state effect path '{normalized}' 未落入 6 个允许的命名空间之一 "
            f"(world / faction / relationship / flag / player / knowledge)；"
            f"见 ADR-016 v0.4"
        ]
    return []


def validate_monotonic(
    effect: dict[str, Any],
    *,
    generation_source: Optional[str] = None,
) -> list[str]:
    """校验 monotonic 规则：LLM 生成（generation_source != 'human'）的 effect 若 path 落在
    monotonic 命名空间内（flag.player_* / knowledge.*），op 只能为 set / inc / add；
    dec / remove 拒收。human-source（generation_source == 'human'）豁免。

    返回错误消息列表；空 list 表示通过。
    """
    if generation_source == "human":
        return []

    normalized = _normalize_path(effect.get("path"))
    if normalized is None or not is_monotonic_path(normalized):
        return []

    op = effect.get("op", "")
    if op in FORBIDDEN_OPS_MONOTONIC:
        return [
            f"monotonic 违反：path '{normalized}' 属于 monotonic 命名空间 "
            f"(flag.player_* / knowledge.*)，ADR-034 D11 禁止 LLM 生成内容使用 op='{op}'；"
            f"允许的 op 集合 = {sorted(ALLOWED_OPS_MONOTONIC)}"
        ]
    return []


def validate_effects(
    effects: Iterable[dict[str, Any]],
    *,
    generation_source: Optional[str] = None,
) -> list[str]:
    """对一组 state_effect 跑全部校验（命名空间 + monotonic），返回所有错误消息（带 effect 索引）。

    Args:
        effects: state_effect dict 的可迭代对象（典型来自 node.on_enter_effects 或 option.effects）
        generation_source: 'human'（手填）或 'llm'（生成）；'human' 豁免 monotonic 校验

    Returns:
        错误消息字符串列表；空 list 表示全部通过
    """
    errors: list[str] = []
    for i, effect in enumerate(effects):
        for msg in validate_effect_namespace(effect):
            errors.append(f"effect[{i}]: {msg}")
        for msg in validate_monotonic(effect, generation_source=generation_source):
            errors.append(f"effect[{i}]: {msg}")
    return errors


__all__ = [
    "NAMESPACE_PATTERNS",
    "MONOTONIC_PATTERNS",
    "ALLOWED_OPS_MONOTONIC",
    "FORBIDDEN_OPS_MONOTONIC",
    "ALL_OPS",
    "classify_namespace",
    "is_monotonic_path",
    "validate_effect_namespace",
    "validate_monotonic",
    "validate_effects",
]
