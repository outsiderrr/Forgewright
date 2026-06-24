"""第三层：一致性校验。

跨对象一致性检查：节点内 option_id 唯一性、图内 speaker_ref 必须在 character_refs 中
（含 ADR-040 结构化对白 dialogue[].speaker_ref——每句对白的说话人同样要在花名册里声明），
以及本体引用闭合性（character_refs、scene_anchor、location_ref、StateEffect.ontology_ref、
StateCondition.ontology_ref）。本体查询走 state.ontology.get_entity（ADR-006 单一事实源）。
"""
from __future__ import annotations

from typing import Any, Iterator

from state import ontology

from .report import Issue


def _is_mapping(x: Any) -> bool:
    return isinstance(x, dict)


def _walk_conditions(cond: Any) -> Iterator[dict]:
    if not _is_mapping(cond):
        return
    yield cond
    for key in ("all_of", "any_of"):
        subs = cond.get(key)
        if isinstance(subs, list):
            for s in subs:
                yield from _walk_conditions(s)
    if "not" in cond:
        yield from _walk_conditions(cond.get("not"))


def _check_ontology_ref(ref: Any) -> bool:
    """True if ref resolves in ontology; None/non-string refs are treated as N/A."""
    if ref is None or not isinstance(ref, str):
        return True
    return ontology.get_entity(ref) is not None


def check(graph: dict) -> list[Issue]:
    issues: list[Issue] = []

    nodes = graph.get("nodes")
    if not _is_mapping(nodes):
        nodes = {}

    character_refs_raw = graph.get("character_refs")
    character_refs = (
        [r for r in character_refs_raw if isinstance(r, str)]
        if isinstance(character_refs_raw, list)
        else []
    )
    char_ref_set = set(character_refs)

    scene_anchor = graph.get("scene_anchor")
    if isinstance(scene_anchor, str) and ontology.get_entity(scene_anchor) is None:
        issues.append(
            Issue(
                level="cons",
                location="scene_anchor",
                message=(
                    f"scene_anchor {scene_anchor!r} does not resolve in ontology"
                ),
            )
        )

    for idx, ref in enumerate(character_refs):
        if ontology.get_entity(ref) is None:
            issues.append(
                Issue(
                    level="cons",
                    location=f"character_refs[{idx}]",
                    message=(
                        f"character_refs entry {ref!r} does not resolve in ontology"
                    ),
                )
            )

    for node_id, node in nodes.items():
        if not _is_mapping(node):
            continue

        options = node.get("options") or []
        if isinstance(options, list):
            seen: dict[str, int] = {}
            for idx, opt in enumerate(options):
                if not _is_mapping(opt):
                    continue
                opt_id = opt.get("option_id")
                if not isinstance(opt_id, str):
                    continue
                if opt_id in seen:
                    issues.append(
                        Issue(
                            level="cons",
                            location=f"{node_id}/{opt_id}",
                            message=(
                                f"duplicate option_id {opt_id!r} within node "
                                f"{node_id!r} (first at index {seen[opt_id]}, "
                                f"again at index {idx})"
                            ),
                        )
                    )
                else:
                    seen[opt_id] = idx

        speaker_ref = node.get("speaker_ref")
        if isinstance(speaker_ref, str) and speaker_ref not in char_ref_set:
            issues.append(
                Issue(
                    level="cons",
                    location=node_id,
                    message=(
                        f"speaker_ref {speaker_ref!r} is not declared in "
                        f"character_refs"
                    ),
                )
            )

        # ADR-040：结构化对白行 dialogue[].speaker_ref 同样必须 ∈ character_refs
        # （与 node.speaker_ref 同闭合逻辑——对白每句的说话人都要在花名册里声明）。
        dialogue = node.get("dialogue")
        if isinstance(dialogue, list):
            for d_idx, entry in enumerate(dialogue):
                if not _is_mapping(entry):
                    continue
                d_speaker = entry.get("speaker_ref")
                if isinstance(d_speaker, str) and d_speaker not in char_ref_set:
                    issues.append(
                        Issue(
                            level="cons",
                            location=f"{node_id}/dialogue[{d_idx}]",
                            message=(
                                f"dialogue[{d_idx}].speaker_ref {d_speaker!r} is "
                                f"not declared in character_refs"
                            ),
                        )
                    )

        location_ref = node.get("location_ref")
        if isinstance(location_ref, str) and ontology.get_entity(location_ref) is None:
            issues.append(
                Issue(
                    level="cons",
                    location=node_id,
                    message=(
                        f"location_ref {location_ref!r} does not resolve in ontology"
                    ),
                )
            )

        on_enter = node.get("on_enter_effects") or []
        if isinstance(on_enter, list):
            for idx, eff in enumerate(on_enter):
                if not _is_mapping(eff):
                    continue
                onto = eff.get("ontology_ref")
                if not _check_ontology_ref(onto):
                    issues.append(
                        Issue(
                            level="cons",
                            location=f"{node_id}/on_enter_effects[{idx}]",
                            message=(
                                f"StateEffect.ontology_ref {onto!r} does not "
                                f"resolve in ontology"
                            ),
                        )
                    )

        if isinstance(options, list):
            for opt in options:
                if not _is_mapping(opt):
                    continue
                opt_id = opt.get("option_id", "?")
                loc = f"{node_id}/{opt_id}"

                effects = opt.get("effects") or []
                if isinstance(effects, list):
                    for idx, eff in enumerate(effects):
                        if not _is_mapping(eff):
                            continue
                        onto = eff.get("ontology_ref")
                        if not _check_ontology_ref(onto):
                            issues.append(
                                Issue(
                                    level="cons",
                                    location=f"{loc}/effects[{idx}]",
                                    message=(
                                        f"StateEffect.ontology_ref {onto!r} does "
                                        f"not resolve in ontology"
                                    ),
                                )
                            )

                cond = opt.get("condition")
                for sub in _walk_conditions(cond):
                    onto = sub.get("ontology_ref")
                    if not _check_ontology_ref(onto):
                        issues.append(
                            Issue(
                                level="cons",
                                location=f"{loc}/condition",
                                message=(
                                    f"StateCondition.ontology_ref {onto!r} does "
                                    f"not resolve in ontology"
                                ),
                            )
                        )

    return issues
