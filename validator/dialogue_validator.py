"""机械预检：dialogue node 级 9 类硬错（T-2.4 / R8 / ADR-020）。

定位：在 schema_check / graph_check / consistency_check 三层之外补一层"机械可数值化"
预检——把 image_validator 的 "code + issue 列表 + severity" 模型推到 dialogue node 级
别。STAGE_1_ACCEPTANCE §4 R8 教训：机械可检测维度不让 LLM 评。

不与三层 Issue 共享类型——本层针对单 node（field_path 定位到 options[i].text 这种细
粒度），与图论 / 一致性的 location 粒度不一致；调用方按需聚合。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["error", "warning"]

_PATH_NAMESPACES = ("world", "faction", "relationship", "flag", "player")
_UNAVAIL_BEHAVIORS = ("hide", "disable", "disable_with_hint")
_EFFECT_OPS = ("set", "inc", "dec", "add", "remove")
_CONDITION_OPS = ("eq", "neq", "gt", "gte", "lt", "lte", "has", "has_not")


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    field_path: str
    message: str


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def _count_text_length(text: str) -> int:
    """汉字 = char count；英文 = word count（按空白分词）；混合 = max(两值)。"""
    chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
    english_words = sum(
        1 for w in text.split() if any(c.isascii() and c.isalpha() for c in w)
    )
    return max(chinese_chars, english_words)


def _extract_slugs(ontology: dict | None) -> set[str] | None:
    """从本体抽 character entity 的 state_path_slug 集合。None → 跳过 C3。"""
    if not isinstance(ontology, dict):
        return None
    entities = ontology.get("entities") or []
    if not isinstance(entities, list):
        return set()
    return {
        e["state_path_slug"]
        for e in entities
        if isinstance(e, dict)
        and e.get("type") == "character"
        and isinstance(e.get("state_path_slug"), str)
    }


def _check_path_namespace(
    path: str, where: str, slugs: set[str] | None, issues: list[ValidationIssue]
) -> None:
    head = path.split(".", 1)[0]
    if head not in _PATH_NAMESPACES:
        issues.append(
            ValidationIssue(
                severity="error",
                code="PATH_NS_INVALID",
                field_path=where,
                message=(
                    f"state path {path!r} first segment {head!r} not in "
                    f"namespaces {_PATH_NAMESPACES}"
                ),
            )
        )
        return
    if head == "relationship" and slugs is not None:
        parts = path.split(".")
        if len(parts) >= 2 and parts[1] not in slugs:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="BOND_ID_UNKNOWN",
                    field_path=where,
                    message=(
                        f"state path {path!r} uses relationship slug "
                        f"{parts[1]!r} not found in ontology character entities"
                    ),
                )
            )


def _check_effect(
    eff: Any,
    where: str,
    slugs: set[str] | None,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(eff, dict):
        return
    op = eff.get("op")
    if isinstance(op, str) and op not in _EFFECT_OPS:
        issues.append(
            ValidationIssue(
                severity="error",
                code="EFFECT_OP_INVALID",
                field_path=f"{where}.op",
                message=f"state_effect.op {op!r} not in {_EFFECT_OPS}",
            )
        )
    p = eff.get("path")
    if isinstance(p, str):
        _check_path_namespace(p, f"{where}.path", slugs, issues)


def _check_condition(
    cond: Any,
    where: str,
    slugs: set[str] | None,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(cond, dict):
        return
    keys = set(cond)
    leaf_keys = {"op", "path", "value"} & keys
    composite_keys = {"all_of", "any_of", "not"} & keys
    if leaf_keys and composite_keys:
        issues.append(
            ValidationIssue(
                severity="error",
                code="STATE_CONDITION_FORM_MIX",
                field_path=where,
                message=(
                    f"StateCondition mixes leaf keys {sorted(leaf_keys)!r} "
                    f"with composite keys {sorted(composite_keys)!r}"
                ),
            )
        )
    op = cond.get("op")
    if isinstance(op, str) and op not in _CONDITION_OPS:
        issues.append(
            ValidationIssue(
                severity="error",
                code="CONDITION_OP_INVALID",
                field_path=f"{where}.op",
                message=f"state_condition.op {op!r} not in {_CONDITION_OPS}",
            )
        )
    p = cond.get("path")
    if isinstance(p, str):
        _check_path_namespace(p, f"{where}.path", slugs, issues)
    for key in ("all_of", "any_of"):
        subs = cond.get(key)
        if isinstance(subs, list):
            for i, sub in enumerate(subs):
                _check_condition(sub, f"{where}.{key}[{i}]", slugs, issues)
    if "not" in cond:
        _check_condition(cond["not"], f"{where}.not", slugs, issues)


def validate_node_mechanical(
    node: dict,
    *,
    ontology: dict | None = None,
    known_node_ids: set[str] | None = None,
) -> ValidationResult:
    """机械预检 dialogue node。返回多 issue 列表（不短路）。

    `known_node_ids` 提供时跑 C4 TARGET_UNREACHABLE；None 时跳过——单 node 调用方
    通常没有同图节点集合，C4 由 graph 入口聚合。
    `ontology` 提供时跑 C3 BOND_ID_UNKNOWN；None 时跳过该条。
    """
    issues: list[ValidationIssue] = []
    slugs = _extract_slugs(ontology)

    node_type = node.get("type")
    raw_options = node.get("options")
    options = raw_options if isinstance(raw_options, list) else []

    # C9 NODE_TYPE_OPTIONS_MISMATCH
    if node_type == "dialogue" and not options:
        issues.append(
            ValidationIssue(
                severity="error",
                code="NODE_TYPE_OPTIONS_MISMATCH",
                field_path="options",
                message='node type="dialogue" must have non-empty options',
            )
        )
    elif node_type == "end" and options:
        issues.append(
            ValidationIssue(
                severity="error",
                code="NODE_TYPE_OPTIONS_MISMATCH",
                field_path="options",
                message='node type="end" must have empty options',
            )
        )

    on_enter = node.get("on_enter_effects") or []
    if isinstance(on_enter, list):
        for idx, eff in enumerate(on_enter):
            _check_effect(eff, f"on_enter_effects[{idx}]", slugs, issues)

    for idx, opt in enumerate(options):
        if not isinstance(opt, dict):
            continue
        prefix = f"options[{idx}]"

        # C1 OPT_LEN_OVER
        text = opt.get("text")
        if isinstance(text, str):
            length = _count_text_length(text)
            if length > 25:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="OPT_LEN_OVER",
                        field_path=f"{prefix}.text",
                        message=(
                            f"option text length {length} > 25 "
                            f"(汉字 char count / 英文 word count / 混合 取 max)"
                        ),
                    )
                )

        # C4 TARGET_UNREACHABLE
        target = opt.get("target_node_id")
        if (
            known_node_ids is not None
            and isinstance(target, str)
            and target not in known_node_ids
        ):
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="TARGET_UNREACHABLE",
                    field_path=f"{prefix}.target_node_id",
                    message=(
                        f"target_node_id {target!r} not in graph nodes "
                        f"(dangling reference)"
                    ),
                )
            )

        # C5 UNAVAIL_BEHAVIOR_INVALID
        unavail = opt.get("unavailable_behavior")
        if isinstance(unavail, str) and unavail not in _UNAVAIL_BEHAVIORS:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="UNAVAIL_BEHAVIOR_INVALID",
                    field_path=f"{prefix}.unavailable_behavior",
                    message=(
                        f"unavailable_behavior {unavail!r} not in "
                        f"{_UNAVAIL_BEHAVIORS}"
                    ),
                )
            )

        # C7 EFFECT_OP_INVALID + C2 PATH_NS_INVALID + C3 BOND_ID_UNKNOWN（路径段）
        effects = opt.get("effects") or []
        if isinstance(effects, list):
            for e_idx, eff in enumerate(effects):
                _check_effect(eff, f"{prefix}.effects[{e_idx}]", slugs, issues)

        # C6 STATE_CONDITION_FORM_MIX + C8 CONDITION_OP_INVALID + C2/C3（路径段）
        cond = opt.get("condition")
        if cond is not None:
            _check_condition(cond, f"{prefix}.condition", slugs, issues)

    return ValidationResult(issues=issues)


def validate_graph_mechanical(
    graph: dict, *, ontology: dict | None = None
) -> dict[str, ValidationResult]:
    """对图内每个 node 跑 validate_node_mechanical，返回 node_id → result 字典。

    `known_node_ids` 由本函数从 graph["nodes"] 自动构造，避开 C4 在单 node 入口缺
    上下文的问题。非 dict 节点跳过（schema 层会抓）。
    """
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return {}
    known = set(nodes.keys())
    return {
        nid: validate_node_mechanical(
            node, ontology=ontology, known_node_ids=known
        )
        for nid, node in nodes.items()
        if isinstance(node, dict)
    }


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_node_mechanical",
    "validate_graph_mechanical",
]
