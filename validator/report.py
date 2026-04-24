"""ValidationReport + Issue 数据结构。

三层校验器（schema / graph / consistency）共享的通用出参类型。Issue 是一个
dataclass：`level` ∈ {"schema","graph","cons"}，`location` 是对该层友好的定位串
（JSON Pointer / node_id / "<node_id>/<option_id>"），`message` 是人话描述。
ValidationReport 聚合三层输出；`passed = (errors == [])`。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    level: str
    location: str
    message: str


@dataclass
class ValidationReport:
    passed: bool
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    issues_by_level: dict[str, list[Issue]] = field(default_factory=dict)
