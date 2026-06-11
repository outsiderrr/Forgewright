"""多 pass + 分拍场景生成引擎（结构层正式路径）—— 编排全部小调用.

设计：generator/experiments/multipass_structure/DESIGN_2026-06-10_formal_landing.md（作者批准 2026-06-10）；
收敛路由 × junction 承接修复：DESIGN_2026-06-11_convergent_routes.md（作者批准 2026-06-11）——
非入口节点的生成调用注入入口上下文（单入口 = 玩家原句承接；收敛多入口 = 收敛安全开头）。

调用序列（全部小调用；DESIGN §5 超时架构化）：
  ①契约 → ②拓扑规划（确定性校验，重试 ≤2，仍败回退脚手架）
  → 按 BFS 序逐 plan 节点：choice = 骨架 + 正文；beats = 分拍（reveals >4 自动分块）；
    end = 收束微调用
  → 确定性组装 → validator（schema + mechanical + AP-7/8/10）→ 指标。

失败语义（对齐 generate_scene.py 先例）：BudgetExceeded / ProviderError 不上抛，
落进 MultipassSceneResult.failure_reason，部分产物保留在 design 里供排查。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generator.budget import BudgetExceeded
from generator.llm_provider import ProviderError
from generator.multipass.assemble import assemble_graph
from generator.multipass.calls import structured_call
from generator.multipass.topology import fallback_topology, validate_topology
from generator.prompts.node.multipass import (
    PASS1_SKELETON_SYSTEM,
    PASS1_SKELETON_SYSTEM_DYNAMIC,
    PASS2_PROSE_SYSTEM,
    build_dynamic_node_schema,
    build_dynamic_node_user_prompt,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass2_schema,
    build_pass2_user_prompt,
    entry_context_block,
)
from generator.prompts.node.multipass.beat_pacing import (
    BEAT_PACING_SYSTEM,
    build_beat_pacing_schema,
    build_beat_pacing_user_prompt,
)
from generator.prompts.node.multipass.pass2_prose import (
    build_end_prose_schema,
    build_end_prose_user_prompt,
)
from generator.prompts.node.multipass.topology import (
    TOPOLOGY_SYSTEM,
    build_topology_schema,
    build_topology_user_prompt,
)

# 每次 beat-pacing 调用最多分配的线索数（一次产 2-3 拍、每拍 1-2 条；>4 条自动分块）
MAX_REVEALS_PER_BEAT_CALL = 4
TOPOLOGY_RETRIES = 2

# est_output_tokens（全部 ≤ calls.MAX_EST_OUTPUT_TOKENS 护栏）
_EST = {
    "contract": 600,
    "topology": 800,
    "skeleton": 900,
    "prose": 1500,
    "beats": 1200,
    "end": 400,
}


@dataclass
class SceneRunConfig:
    """一次正式运行的图级配置（机械字段来源；LLM 不写这些）。"""

    graph_id: str
    scene_anchor: str
    speaker_ref: str
    character_refs: list[str]
    npc_name: str = "NPC"


@dataclass
class MultipassSceneResult:
    """一次场景运行的全部产物（成功或失败都返回，不上抛）。"""

    status: str  # "success" | "budget_exceeded" | "provider_error"
    graph: dict[str, Any] | None
    design: dict[str, Any]  # contract / topology / skeletons / beats / ends（sidecar）
    call_metas: list[dict[str, Any]]
    validation: dict[str, Any]
    metrics: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    topology_fallback: bool = False
    failure_reason: str | None = None


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def _serialize_issues(issues: list[Any]) -> list[dict[str, Any]]:
    out = []
    for i in issues:
        if hasattr(i, "__dataclass_fields__"):
            out.append({k: getattr(i, k) for k in i.__dataclass_fields__})
        else:
            out.append({"message": str(i)})
    return out


def _bfs_order(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """BFS（父先于子）遍历 plan 节点——历史压缩需要祖先先生成。"""
    by_id = {n["node_id"]: n for n in plan["nodes"]}
    order: list[dict[str, Any]] = []
    seen: set[str] = set()
    frontier = [plan["entry_node_id"]]
    while frontier:
        nid = frontier.pop(0)
        if nid in seen or nid not in by_id:
            continue
        seen.add(nid)
        node = by_id[nid]
        order.append(node)
        if node.get("kind") == "choice":
            frontier.extend(r.get("to", "") for r in node.get("routes") or [])
        elif node.get("kind") == "beats":
            if node.get("next"):
                frontier.append(node["next"])
    return order


def _parents(plan: dict[str, Any]) -> dict[str, str | None]:
    """child plan_id → parent plan_id（纯树：唯一父亲）。"""
    parents: dict[str, str | None] = {plan["entry_node_id"]: None}
    for n in plan["nodes"]:
        if n.get("kind") == "choice":
            for r in n.get("routes") or []:
                parents[r.get("to", "")] = n["node_id"]
        elif n.get("kind") == "beats" and n.get("next"):
            parents[n["next"]] = n["node_id"]
    return parents


def _ancestor_chain(pid: str, parents: dict[str, str | None]) -> list[str]:
    chain: list[str] = []
    cur = parents.get(pid)
    while cur is not None:
        chain.append(cur)
        cur = parents.get(cur)
    chain.reverse()  # 入口 → … → 父
    return chain


def run_multipass_scene(
    provider: Any,
    scene_spec: dict[str, Any],
    config: SceneRunConfig,
) -> MultipassSceneResult:
    """跑一次完整多 pass + 分拍场景生成；返回结果（不上抛 provider/budget 失败）。"""
    metas: list[dict[str, Any]] = []
    design: dict[str, Any] = {}
    warnings: list[str] = []
    fallback_used = False

    def _call(label_kind: str, label: str, system: str, user: str, schema: dict) -> dict:
        content, m = structured_call(
            provider,
            system_prompt=system,
            user_prompt=user,
            json_schema=schema,
            est_output_tokens=_EST[label_kind],
            label=label,
        )
        metas.append(m)
        return content

    def _fail(status: str, reason: str) -> MultipassSceneResult:
        return MultipassSceneResult(
            status=status,
            graph=None,
            design=design,
            call_metas=metas,
            validation={},
            metrics=_metrics(metas, None, {}, fallback_used),
            warnings=warnings,
            topology_fallback=fallback_used,
            failure_reason=reason,
        )

    try:
        # ① 契约
        contract = _call(
            "contract",
            "contract",
            PASS1_SKELETON_SYSTEM,
            build_pass1_contract_user_prompt(scene_spec),
            build_pass1_contract_schema(),
        )
        design["contract"] = contract

        # ② 拓扑规划（动态；确定性校验 + 重试 + 回退）
        plan: dict[str, Any] | None = None
        errors: list[str] = []
        for attempt in range(1 + TOPOLOGY_RETRIES):
            candidate = _call(
                "topology",
                f"topology_attempt{attempt + 1}",
                TOPOLOGY_SYSTEM,
                build_topology_user_prompt(
                    scene_spec=scene_spec,
                    scene_contract=contract,
                    prior_errors=errors or None,
                ),
                build_topology_schema(),
            )
            errors = validate_topology(candidate)
            if not errors:
                plan = candidate
                break
            warnings.append(f"拓扑规划第 {attempt + 1} 次未过确定性校验：{errors}")
        if plan is None:
            plan = fallback_topology(scene_spec)
            fallback_used = True
            warnings.append("拓扑规划重试用尽，回退半固定脚手架（ADR-038 v1 形状）")
        design["topology"] = plan
        design["topology_fallback"] = fallback_used

        # ③④⑤⑥ 逐节点生成（BFS：父先于子，供历史压缩）
        parents = _parents(plan)
        by_id = {n["node_id"]: n for n in plan["nodes"]}
        skeletons: dict[str, dict[str, Any]] = {}
        proses: dict[str, dict[str, Any]] = {}
        beats_by_id: dict[str, list[dict[str, Any]]] = {}
        ends: dict[str, dict[str, Any]] = {}

        def _entry_context(pid: str) -> dict[str, Any] | None:
            """玩家是怎么走进节点 pid 的（收敛路由根因①⑥ + junction 承接的数据源）。

            BFS 父先于子 → 父节点的骨架/正文/分拍此刻必已生成：
              - 父 = choice：路由到 pid 的选项最终台词（1 条=单入口承接；≥2 条=收敛入口清单）；
              - 父 = beats：链尾拍的 continue 文本（单入口承接）。
            入口节点 / 无可用文本 → None（不注入）。
            """
            par = parents.get(pid)
            if not par:
                return None
            pnode = by_id[par]
            if pnode.get("kind") == "choice":
                skel_opts = (skeletons.get(par) or {}).get("options") or []
                prose_opts = (proses.get(par) or {}).get("options") or []
                entries = []
                for i, o in enumerate(skel_opts):
                    if o.get("route_to") != pid:
                        continue
                    text = (prose_opts[i].get("text", "") if i < len(prose_opts) else "") or o.get(
                        "intent", ""
                    )
                    if text:
                        entries.append({"text": text, "intent": o.get("intent", "")})
                if not entries:
                    return None
                stance = next(
                    (r.get("stance") for r in pnode.get("routes") or [] if r.get("to") == pid),
                    None,
                )
                return {
                    "mode": "single" if len(entries) == 1 else "convergent",
                    "entries": entries,
                    "stance": stance,
                }
            if pnode.get("kind") == "beats":
                beats = beats_by_id.get(par) or []
                last = ((beats[-1].get("continue_option") or {}).get("text") or "").strip() if beats else ""
                if not last:
                    return None
                return {"mode": "single", "entries": [{"text": last, "intent": ""}], "stance": None}
            return None

        def _history(pid: str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
            """祖先链 → (prior_nodes 摘要, 已揭露线索, 已用选项角度)。"""
            prior: list[dict[str, Any]] = []
            revealed: list[str] = []
            intents: list[str] = []
            for anc in _ancestor_chain(pid, parents):
                anc_plan = by_id[anc]
                if anc in skeletons:
                    sk = skeletons[anc]
                    prior.append(sk)
                    revealed.extend(sk.get("reveals") or [])
                    intents.extend(o.get("intent", "") for o in sk.get("options") or [])
                else:
                    # beats / end 祖先：用 plan 信息做摘要
                    prior.append(
                        {
                            "node_id": anc,
                            "function": anc_plan.get("function", ""),
                            "reveals": anc_plan.get("reveals") or [],
                            "options": [],
                        }
                    )
                    revealed.extend(anc_plan.get("reveals") or [])
            return prior, revealed, intents

        for pnode in _bfs_order(plan):
            pid = pnode["node_id"]
            kind = pnode.get("kind")
            prior, revealed, used_intents = _history(pid)
            entry_ctx = _entry_context(pid)

            if kind == "choice":
                allowed = [r.get("to") for r in pnode.get("routes") or []]
                skeleton: dict[str, Any] | None = None
                skel_errors: list[str] = []
                for attempt in range(2):  # 骨架路由违规重试 1 次
                    candidate = _call(
                        "skeleton",
                        f"skeleton_{pid}" + ("_retry" if attempt else ""),
                        PASS1_SKELETON_SYSTEM_DYNAMIC,
                        build_dynamic_node_user_prompt(
                            scene_spec=scene_spec,
                            scene_contract=contract,
                            node_id=pid,
                            function=pnode.get("function", ""),
                            planned_reveals=pnode.get("reveals") or [],
                            routes=pnode.get("routes") or [],
                            prior_nodes=prior,
                            entry_context=entry_ctx,
                        )
                        + (
                            f"\n\n## ⚠️ 上一次输出的路由问题（必须修正）\n- "
                            + "\n- ".join(skel_errors)
                            if skel_errors
                            else ""
                        ),
                        build_dynamic_node_schema(allowed),
                    )
                    candidate.setdefault("node_id", pid)
                    skel_errors = _route_violations(candidate, allowed)
                    skeleton = candidate
                    if not skel_errors:
                        break
                    warnings.append(f"choice {pid} 骨架路由违规：{skel_errors}")
                assert skeleton is not None
                skeletons[pid] = skeleton
                proses[pid] = _call(
                    "prose",
                    f"prose_{pid}",
                    PASS2_PROSE_SYSTEM,
                    build_pass2_user_prompt(
                        scene_contract=contract,
                        node_skeleton=skeleton,
                        revealed_clues=revealed,
                        used_option_intents=used_intents,
                        scene_anchor_facts=scene_spec.get("character_state"),
                        mid_scene=(pid != plan["entry_node_id"]),
                        entry_context=entry_ctx,
                    ),
                    build_pass2_schema(),
                )
            elif kind == "beats":
                reveals = pnode.get("reveals") or []
                chunks = _chunk(reveals, MAX_REVEALS_PER_BEAT_CALL)
                collected: list[dict[str, Any]] = []
                for ci, chunk in enumerate(chunks):
                    situation = pnode.get("function", "")
                    if pid != plan["entry_node_id"]:
                        situation += "\n（本链不是场景开场：空间与在场人物已建立，旁白不要重新做进场式描写）"
                    if ci == 0:
                        eb = entry_context_block(entry_ctx)
                        if eb:
                            situation += "\n\n" + eb  # 链首拍承接入口（chunk>1 走跨 chunk 传话）
                    if revealed:
                        situation += f"\n（此前已揭露：{'、'.join(revealed[-6:])}）"
                    if len(chunks) > 1:
                        situation += f"\n（本链第 {ci + 1}/{len(chunks)} 段，衔接前一段继续）"
                    if ci > 0 and collected:
                        prev = [r for c in chunks[:ci] for r in c]
                        situation += f"\n（本链前几拍已揭露：{'、'.join(prev)}）"
                        last_continue = (collected[-1].get("continue_option") or {}).get("text", "")
                        if last_continue:
                            situation += (
                                f"\n（上一拍玩家刚说：「{last_continue}」——本段第一拍的 NPC 对白必须先承接这句话）"
                            )
                    out = _call(
                        "beats",
                        f"beats_{pid}_part{ci + 1}",
                        BEAT_PACING_SYSTEM,
                        build_beat_pacing_user_prompt(
                            scene_contract=contract,
                            node_situation=situation,
                            reveals=chunk,
                            npc_name=config.npc_name,
                            scene_anchor_facts=scene_spec.get("character_state"),
                        ),
                        build_beat_pacing_schema(),
                    )
                    collected.extend(out.get("beats") or [])
                beats_by_id[pid] = collected
            elif kind == "end":
                path_bits = [by_id[a].get("function", "") for a in _ancestor_chain(pid, parents)]
                ends[pid] = _call(
                    "end",
                    f"end_{pid}",
                    PASS2_PROSE_SYSTEM,
                    build_end_prose_user_prompt(
                        scene_contract=contract,
                        node_function=pnode.get("function", ""),
                        path_summary="；".join(b for b in path_bits if b) or "（直达）",
                        scene_anchor_facts=scene_spec.get("character_state"),
                        entry_context=entry_ctx,
                    ),
                    build_end_prose_schema(),
                )

        design["skeletons"] = skeletons
        design["proses"] = proses
        design["beats"] = beats_by_id
        design["ends"] = ends

    except BudgetExceeded as e:
        return _fail("budget_exceeded", str(e))
    except ProviderError as e:
        return _fail("provider_error", f"{type(e).__name__}: {e}")

    # ⑦ 确定性组装
    graph, asm_warnings = assemble_graph(
        graph_id=config.graph_id,
        scene_anchor=config.scene_anchor,
        speaker_ref=config.speaker_ref,
        character_refs=config.character_refs,
        plan=plan,
        choice_data={pid: {"skeleton": skeletons[pid], "prose": proses.get(pid, {})} for pid in skeletons},
        beats_data=beats_by_id,
        end_data=ends,
    )
    warnings.extend(asm_warnings)

    # ⑧ validator（只读调用；AP flag 记录不拦截——复核期信号）
    validation = _validate(graph)

    metrics = _metrics(metas, graph, skeletons, fallback_used, validation)
    metrics["cross_branch_line_similarity"] = _cross_branch_line_similarity(
        parents, proses, beats_by_id, ends
    )

    return MultipassSceneResult(
        status="success",
        graph=graph,
        design=design,
        call_metas=metas,
        validation=validation,
        metrics=metrics,
        warnings=warnings,
        topology_fallback=fallback_used,
    )


def _route_violations(skeleton: dict[str, Any], allowed: list[str]) -> list[str]:
    """骨架选项的路由违规清单（route_to 非法 / 出边未被覆盖）。"""
    errors: list[str] = []
    used: set[str] = set()
    for i, o in enumerate(skeleton.get("options") or []):
        rt = o.get("route_to")
        if rt not in allowed:
            errors.append(f"options[{i}].route_to={rt!r} 不在出边 {allowed}")
        else:
            used.add(rt)
    missing = [t for t in allowed if t not in used]
    if missing:
        errors.append(f"出边 {missing} 没有任何选项使用")
    return errors


def _validate(graph: dict[str, Any]) -> dict[str, Any]:
    from validator import schema_check
    from validator.anti_pattern_detector import detect_anti_patterns
    from validator.dialogue_validator import validate_graph_mechanical

    schema_issues = _serialize_issues(schema_check.check(graph))
    mech = validate_graph_mechanical(graph)
    mech_issues = {
        nid: _serialize_issues(res.issues) for nid, res in mech.items() if res.issues
    }
    ap_flags = {}
    for nid, node in graph["nodes"].items():
        flags = detect_anti_patterns(node)
        if flags:
            ap_flags[nid] = _serialize_issues(flags)
    return {
        "schema_issues": schema_issues,
        "mechanical_issues": mech_issues,
        "ap_flags": ap_flags,
        "hard_pass": not schema_issues and not mech_issues,
    }


def _metrics(
    metas: list[dict[str, Any]],
    graph: dict[str, Any] | None,
    skeletons: dict[str, dict[str, Any]],
    fallback_used: bool,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    m: dict[str, Any] = {
        "total_calls": len(metas),
        "total_cost_usd": sum(x.get("actual_cost_usd", 0.0) for x in metas),
        "topology_fallback": fallback_used,
    }
    if graph:
        nodes = graph["nodes"]
        narr_lens = {nid: len(n.get("narration", "")) for nid, n in nodes.items()}
        m["node_count"] = len(nodes)
        m["narration_lengths"] = narr_lens
        m["narration_len_avg"] = (sum(narr_lens.values()) / len(narr_lens)) if narr_lens else 0
        m["option_counts"] = {nid: len(n.get("options") or []) for nid, n in nodes.items()}
        # 出边收敛度：choice 节点"出边 → 路由到它的选项数"（≥2 = 有意收敛；
        # 收敛稀释从此可量化跨 run 追踪——复核根因①观测项）
        convergence: dict[str, dict[str, int]] = {}
        for pid, sk in skeletons.items():
            per_route: dict[str, int] = {}
            for o in sk.get("options") or []:
                rt = o.get("route_to")
                if rt:
                    per_route[rt] = per_route.get(rt, 0) + 1
            if per_route:
                convergence[pid] = per_route
        m["route_convergence"] = convergence
        # choice 节点两两 intent 重叠（功能分化客观信号；越低越好）
        overlaps: dict[str, list[str]] = {}
        ids = sorted(skeletons)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                ia = {o.get("intent", "") for o in skeletons[a].get("options") or []}
                ib = {o.get("intent", "") for o in skeletons[b].get("options") or []}
                ov = sorted(x for x in (ia & ib) if x)
                if ov:
                    overlaps[f"{a}↔{b}"] = ov
        m["choice_intent_overlaps"] = overlaps
    if validation:
        m["hard_pass"] = validation.get("hard_pass")
        m["ap_flag_count"] = sum(len(v) for v in validation.get("ap_flags", {}).values())
    return m


def _cross_branch_line_similarity(
    parents: dict[str, str | None],
    proses: dict[str, dict[str, Any]],
    beats_by_id: dict[str, list[dict[str, Any]]],
    ends: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """平行分支（非祖先关系节点）对白行两两最大相似度——近原文复制的客观信号（根因⑥观测项）。

    纯本地计算（difflib，0 LLM）；只比 ≥8 字的对白行（短寒暄难免相似，不算信号）。
    """
    import difflib

    lines_by_node: dict[str, list[str]] = {}
    for pid, pr in proses.items():
        lines_by_node.setdefault(pid, []).extend(pr.get("dialogue") or [])
    for pid, beats in beats_by_id.items():
        for b in beats:
            lines_by_node.setdefault(pid, []).extend(b.get("dialogue") or [])
    for pid, e in ends.items():
        lines_by_node.setdefault(pid, []).extend(e.get("dialogue") or [])
    lines_by_node = {
        k: [s.strip() for s in v if len(s.strip()) >= 8] for k, v in lines_by_node.items()
    }

    def _ancestors(nid: str) -> set[str]:
        seen: set[str] = set()
        cur = parents.get(nid)
        while cur is not None and cur not in seen:
            seen.add(cur)
            cur = parents.get(cur)
        return seen

    max_ratio, max_pair = 0.0, None
    high_pairs: list[dict[str, Any]] = []
    ids = sorted(lines_by_node)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if a in _ancestors(b) or b in _ancestors(a):
                continue
            for la in lines_by_node[a]:
                for lb in lines_by_node[b]:
                    r = difflib.SequenceMatcher(None, la, lb).ratio()
                    if r > max_ratio:
                        max_ratio, max_pair = r, f"{a}↔{b}"
                    if r >= 0.8:
                        high_pairs.append(
                            {"nodes": f"{a}↔{b}", "ratio": round(r, 3), "a": la, "b": lb}
                        )
    return {
        "max_ratio": round(max_ratio, 3),
        "max_pair": max_pair,
        "high_similarity_lines": high_pairs[:10],
    }


def write_artifacts(result: MultipassSceneResult, out_dir: Path) -> dict[str, Path]:
    """落盘四件产物：scene.json / design.json / metrics.json / scene.md。"""
    from generator.multipass.render import render_scene_md

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    if result.graph is not None:
        paths["scene"] = out_dir / "scene.json"
        paths["scene"].write_text(
            json.dumps(result.graph, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    paths["design"] = out_dir / "design.json"
    paths["design"].write_text(
        json.dumps(
            {
                "design": result.design,
                "call_metas": result.call_metas,
                "warnings": result.warnings,
                "validation": result.validation,
                "status": result.status,
                "failure_reason": result.failure_reason,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["metrics"] = out_dir / "metrics.json"
    paths["metrics"].write_text(
        json.dumps(result.metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["scene_md"] = out_dir / "scene.md"
    paths["scene_md"].write_text(render_scene_md(result), encoding="utf-8")
    return paths


__all__ = [
    "SceneRunConfig",
    "MultipassSceneResult",
    "run_multipass_scene",
    "write_artifacts",
    "MAX_REVEALS_PER_BEAT_CALL",
    "TOPOLOGY_RETRIES",
]
