"""Forgewright validator module: Schema / graph / consistency validation for generated content.

三层校验 (ADR-009 第一、二层子集)：
  - Layer 1 (schema)：JSON Schema Draft 2020-12 结构校验
  - Layer 2 (graph)：networkx 图论校验（悬空、不可达、结局缺失）
  - Layer 3 (cons)：跨对象一致性 + 本体引用闭合性

公开 API：validate(graph_dict) -> ValidationReport。三层全跑，不短路。

视觉资产（T-1.5.4）独立成第四入口：validate_image_asset(path, asset_kind=...) →
list[ImageValidationError]。它针对**单个图像文件**而非 graph dict，因此与上面三
层并行而非纳入 ValidationReport（定位单位不同）。

ADR-021 第二层方法论拆 2A 拓扑 + 2B 抽样 + 有界符号执行（T-2.7 落地）：
  - 2A：``validate_graph_topology`` （包装 ``graph_check`` ；纯拓扑 + condition 引用形态）
  - 2B：``validate_graph_sampling`` + ``validate_graph_bounded_symbolic``
        （condition satisfiability 全部走 2B）
"""
from __future__ import annotations

from . import consistency_check, graph_check, schema_check
from .graph_validation import (
    ACTIVE_CLOCKS_SOFT_LIMIT,
    STATE_PATH_NAMESPACES,
    TopologyIssue,
    TopologyResult,
    normalize_effect_op,
    validate_graph_topology,
)
from .image_validator import (
    ImageValidationConfig,
    ImageValidationError,
    validate_image_asset,
)
from .report import Issue, ValidationReport
from .sampling import (
    FailedSample,
    SamplingResult,
    SymbolicResult,
    validate_graph_bounded_symbolic,
    validate_graph_sampling,
)

__all__ = [
    "validate",
    "Issue",
    "ValidationReport",
    "validate_image_asset",
    "ImageValidationError",
    "ImageValidationConfig",
    # ADR-021 §2A
    "TopologyIssue",
    "TopologyResult",
    "validate_graph_topology",
    "normalize_effect_op",
    "STATE_PATH_NAMESPACES",
    "ACTIVE_CLOCKS_SOFT_LIMIT",
    # ADR-021 §2B
    "FailedSample",
    "SamplingResult",
    "SymbolicResult",
    "validate_graph_sampling",
    "validate_graph_bounded_symbolic",
]


def validate(graph_dict: dict) -> ValidationReport:
    """三层全跑。任一层出错不短路，返回完整 ValidationReport。"""
    schema_errors = schema_check.check(graph_dict)
    graph_errors, graph_warnings = graph_check.check(graph_dict)
    cons_errors = consistency_check.check(graph_dict)

    errors = schema_errors + graph_errors + cons_errors
    warnings = list(graph_warnings)
    by_level = {
        "schema": list(schema_errors),
        "graph": list(graph_errors) + list(graph_warnings),
        "cons": list(cons_errors),
    }
    return ValidationReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        issues_by_level=by_level,
    )
