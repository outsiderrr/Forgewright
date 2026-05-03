"""第二层校验 2B：抽样验证 + 有界符号执行 (ADR-021)。

condition satisfiability 全部走本层（2A 仅做引用形态合法性）。

  - **抽样**：从 entry 出发，按 condition 满足的 option 随机选择，跟踪 state 演化，
    记录是否到 end。N=100 是经验阈值起步——不暗示充分证明 (ADR-021 §completion criteria)。
  - **有界符号执行**：在 state_var_domains 内枚举 state 组合（cap=bound），对每组
    检查 graph 是否仍有 entry → end 路径。

完成标志措辞 (ADR-021)：从 "证明任意合法状态组合下至少有 1 个结局可达" 改为
"抽样验证 N=100 路径 + 有界符号执行下未发现反例"。
"""
from __future__ import annotations

import itertools
import json
import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from state.conditions import evaluate_condition
from state.effects import apply_effect
from state.world_state import WorldState

from .graph_validation import normalize_effect_op

__all__ = [
    "FailedSample",
    "SamplingResult",
    "SymbolicResult",
    "validate_graph_sampling",
    "validate_graph_bounded_symbolic",
]


@dataclass
class FailedSample:
    path: list[str]
    state_at_failure: dict
    reason: str


@dataclass
class SamplingResult:
    sample_count: int
    reached_end_count: int
    deadlock_count: int
    avg_path_length: float
    end_distribution: dict[str, int] = field(default_factory=dict)
    failure_examples: list[FailedSample] = field(default_factory=list)
    condition_unsatisfiable_examples: list[tuple[str, str]] = field(default_factory=list)

    @property
    def reach_rate(self) -> float:
        if self.sample_count == 0:
            return 0.0
        return self.reached_end_count / self.sample_count


@dataclass
class SymbolicResult:
    explored_states: int
    states_without_path_to_end: list[dict] = field(default_factory=list)


def _seed_state(initial_state: dict | None) -> WorldState:
    """以 dotted-path 字典种入 WorldState。

    ``initial_state`` 形如 ``{"player.traits": ["observant"], "flag.foo": True}``；
    嵌套 dict 也接受（自动展平为 dotted path）。
    """
    state = WorldState()
    if not initial_state:
        return state
    for path, value in _flatten_initial(initial_state).items():
        state.set(path, value)
    return state


def _flatten_initial(d: dict, prefix: str = "") -> dict[str, Any]:
    """Flatten only when the key has no dot AND the value is a plain dict.

    保留作者直接写 dotted key 的能力（``{"player.traits": [...]}``），同时也接受
    嵌套形态（``{"player": {"traits": [...]}}``）。
    """
    out: dict[str, Any] = {}
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and "." not in k:
            out.update(_flatten_initial(v, path))
        else:
            out[path] = v
    return out


def _clone_state(state: WorldState) -> WorldState:
    new = WorldState()
    snapshot = deepcopy(state.as_dict())
    for path, value in _flatten_initial(snapshot).items():
        new.set(path, value)
    return new


def _state_signature(state: WorldState) -> str:
    try:
        return json.dumps(state.as_dict(), sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(state.as_dict())


def _apply_on_enter(state: WorldState, node: dict) -> None:
    for eff in (node.get("on_enter_effects") or []):
        try:
            apply_effect(state, normalize_effect_op(eff))
        except Exception:
            # 形态非法（namespace / op enum）由 2A 报；本层抽样阶段忽略不阻塞
            pass


def _try_apply_effects(state: WorldState, effects: Any) -> None:
    if not isinstance(effects, list):
        return
    for eff in effects:
        try:
            apply_effect(state, normalize_effect_op(eff))
        except Exception:
            pass


def _evaluate_or_false(state: WorldState, cond: Any) -> bool:
    if cond is None:
        return True
    if not isinstance(cond, dict):
        return False
    try:
        return evaluate_condition(state, cond)
    except Exception:
        return False


def validate_graph_sampling(
    graph: dict,
    *,
    initial_state: dict | None = None,
    sample_count: int = 100,
    max_path_length: int = 50,
    max_failure_examples: int = 5,
    seed: int | None = None,
) -> SamplingResult:
    """从 entry 出发随机选 option 跑 N 路径，记录 reach end 与 condition 满足情况。

    ADR-021 §completion criteria：N=100 起步，不暗示充分证明；阶段 2 实测后
    由 ADR-021 v0.2 倒推合理 N。
    """
    nodes = graph.get("nodes") or {}
    entry = graph.get("entry_node_id")
    if not isinstance(entry, str) or entry not in nodes:
        return SamplingResult(
            sample_count=0,
            reached_end_count=0,
            deadlock_count=0,
            avg_path_length=0.0,
        )

    rng = random.Random(seed)

    reached = 0
    deadlocks = 0
    end_dist: dict[str, int] = {}
    path_lengths: list[int] = []
    failures: list[FailedSample] = []
    cond_eval_count: dict[tuple[str, str], int] = {}
    cond_satisfied_count: dict[tuple[str, str], int] = {}

    for _ in range(sample_count):
        state = _seed_state(initial_state)
        node_id = entry
        path: list[str] = [node_id]
        _apply_on_enter(state, nodes[entry])

        success = False
        reason: str | None = None

        for _step in range(max_path_length):
            node = nodes[node_id]
            if node.get("type") == "end":
                success = True
                break
            options = node.get("options") or []
            valid: list[dict] = []
            for opt in options:
                if not isinstance(opt, dict):
                    continue
                opt_id = str(opt.get("option_id", "?"))
                key = (node_id, opt_id)
                cond_eval_count[key] = cond_eval_count.get(key, 0) + 1
                if _evaluate_or_false(state, opt.get("condition")):
                    cond_satisfied_count[key] = cond_satisfied_count.get(key, 0) + 1
                    valid.append(opt)
            if not valid:
                reason = "no valid option at non-end node (deadlock)"
                break
            chosen = rng.choice(valid)
            _try_apply_effects(state, chosen.get("effects"))
            target = chosen.get("target_node_id")
            if not isinstance(target, str) or target not in nodes:
                reason = f"option.target_node_id {target!r} missing or invalid"
                break
            node_id = target
            path.append(node_id)
            _apply_on_enter(state, nodes[node_id])
        else:
            reason = f"exceeded max_path_length={max_path_length}"

        path_lengths.append(len(path))
        if success:
            reached += 1
            end_dist[node_id] = end_dist.get(node_id, 0) + 1
        else:
            deadlocks += 1
            if len(failures) < max_failure_examples:
                failures.append(
                    FailedSample(
                        path=path,
                        state_at_failure=deepcopy(state.as_dict()),
                        reason=reason or "unknown",
                    )
                )

    cond_unsat = sorted(
        key
        for key, evals in cond_eval_count.items()
        if evals > 0 and cond_satisfied_count.get(key, 0) == 0
    )

    avg_len = sum(path_lengths) / len(path_lengths) if path_lengths else 0.0

    return SamplingResult(
        sample_count=sample_count,
        reached_end_count=reached,
        deadlock_count=deadlocks,
        avg_path_length=avg_len,
        end_distribution=end_dist,
        failure_examples=failures,
        condition_unsatisfiable_examples=cond_unsat,
    )


def _has_reachable_end(graph: dict, initial_state: dict) -> bool:
    """DFS：在给定初始 state 下，沿条件满足的 option 边能否到达任一 end 节点。

    cycle detection 用 (node_id, state_signature) 集合。
    """
    nodes = graph["nodes"]
    entry = graph["entry_node_id"]
    if entry not in nodes:
        return False

    seen: set[tuple[str, str]] = set()
    initial_world = _seed_state(initial_state)
    _apply_on_enter(initial_world, nodes[entry])
    stack: list[tuple[str, WorldState]] = [(entry, initial_world)]

    while stack:
        node_id, state = stack.pop()
        sig = (node_id, _state_signature(state))
        if sig in seen:
            continue
        seen.add(sig)
        node = nodes.get(node_id)
        if not isinstance(node, dict):
            continue
        if node.get("type") == "end":
            return True
        for opt in (node.get("options") or []):
            if not isinstance(opt, dict):
                continue
            if not _evaluate_or_false(state, opt.get("condition")):
                continue
            target = opt.get("target_node_id")
            if not isinstance(target, str) or target not in nodes:
                continue
            new_state = _clone_state(state)
            _try_apply_effects(new_state, opt.get("effects"))
            _apply_on_enter(new_state, nodes[target])
            stack.append((target, new_state))

    return False


def validate_graph_bounded_symbolic(
    graph: dict,
    *,
    state_var_domains: dict[str, list],
    bound: int = 10,
) -> SymbolicResult:
    """有界符号执行：枚举 ``state_var_domains`` 内的 state 组合（cap=bound），
    每组检查 entry → end 是否仍有可达路径。

    ``state_var_domains``：``{dotted_path: [v1, v2, ...]}``，由调用者声明（阶段 2
    起步不强制；T-2.7 落地后由实测倒推合理上限）。返回的 ``states_without_path_to_end``
    是反例集。
    """
    nodes = graph.get("nodes") or {}
    entry = graph.get("entry_node_id")
    if not isinstance(entry, str) or entry not in nodes:
        return SymbolicResult(explored_states=0)

    if not state_var_domains:
        # 单一空 state 视作一组组合
        ok = _has_reachable_end(graph, {})
        return SymbolicResult(
            explored_states=1,
            states_without_path_to_end=[] if ok else [{}],
        )

    keys = list(state_var_domains.keys())
    domain_lists = [state_var_domains[k] for k in keys]
    no_path: list[dict] = []
    explored = 0

    for combo in itertools.product(*domain_lists):
        if explored >= bound:
            break
        explored += 1
        initial = dict(zip(keys, combo))
        if not _has_reachable_end(graph, initial):
            no_path.append(initial)

    return SymbolicResult(
        explored_states=explored,
        states_without_path_to_end=no_path,
    )
