"""确定性拆拍器（0 LLM）：topology beats 节点 → 锁定拆拍计划（ADR-039 决策三）.

把 beats 拆拍从"LLM 涌现"（beat_pacing pass 里 LLM 自决拆几拍/每拍揭哪条）改为
**确定性结构产物**：拆拍计划由本模块从 topology 的 reveals 清单纯代码切出，
每拍带 reveal 子集，编剧（BYOM）在整场提示词包里逐拍填正文（T-3P-1 消费）。

拆拍规则（数值参数化；默认值 = 常量）：
  - 每拍最多 DEFAULT_MAX_REVEALS_PER_BEAT（=2）条线索，沿 beat_pacing.py 现行
    "每拍只揭 1-2 条"约定的上限；按输入顺序贪心分块（8 条 → 2/2/2/2）。
  - 0 条 reveals 的链给 1 个过场拍（beats 链在图里至少要有 1 拍才能接线）。
  - beat_id = f"{pid}_b{i}"（1 起编），与 assemble.entry_graph_node_id 的
    "{pid}_b1 = 链入口"约定一致——T-3P-2 回流合并按此 id 对齐。

BeatSlot 载体形态在本任务锁死（T-3P-1/2/3 共同消费，不得增删 key）：
  {"beat_id": str, "reveals": list[str], "is_last": bool}
"""
from __future__ import annotations

from typing import Any, TypedDict


class BeatSlot(TypedDict):
    """一拍的锁定槽位（结构由我们锁定，正文由编剧填）。"""

    beat_id: str
    reveals: list[str]
    is_last: bool


# 每拍线索上限默认值（起点参考 beat_pacing.py "每拍只揭 1-2 条"的现行约定上限）
DEFAULT_MAX_REVEALS_PER_BEAT = 2


def chunk_reveals(reveals: list[str], size: int) -> list[list[str]]:
    """按输入顺序贪心分块；空输入给单个空块。

    两处消费必须同一实现（防两径漂移）：确定性拆拍（本模块，按拍分）与
    engine 的 beats 正文调用分块（MAX_REVEALS_PER_BEAT_CALL，按调用分）。
    """
    return [reveals[i : i + size] for i in range(0, len(reveals), size)] or [[]]


def split_beats(
    plan_node: dict[str, Any],
    *,
    max_reveals_per_beat: int = DEFAULT_MAX_REVEALS_PER_BEAT,
) -> list[BeatSlot]:
    """一个 topology beats 节点 → 确定性拆拍计划（单链）。

    不变量：同输入同输出；每条 reveal 恰好落一拍（无遗漏无重复）；保序；
    beat_id 与 assemble.entry_graph_node_id 约定一致；末拍 is_last=True。
    """
    if plan_node.get("kind") != "beats":
        raise ValueError(
            f"split_beats 只接受 kind='beats' 的 plan 节点，"
            f"得到 kind={plan_node.get('kind')!r}（node_id={plan_node.get('node_id')!r}）"
        )
    if max_reveals_per_beat < 1:
        raise ValueError(f"max_reveals_per_beat 必须 ≥1，得到 {max_reveals_per_beat}")

    pid = plan_node["node_id"]
    reveals = list(plan_node.get("reveals") or [])
    # 空链给 1 个过场拍（图里 beats 链至少 1 拍才能接线）
    chunks = chunk_reveals(reveals, max_reveals_per_beat)
    return [
        BeatSlot(
            beat_id=f"{pid}_b{i}",
            reveals=chunk,
            is_last=(i == len(chunks)),
        )
        for i, chunk in enumerate(chunks, start=1)
    ]


def build_beats_plan(
    plan: dict[str, Any],
    *,
    max_reveals_per_beat: int = DEFAULT_MAX_REVEALS_PER_BEAT,
) -> dict[str, list[BeatSlot]]:
    """整份 TopologyPlan → beats_plan（**dict 按链分组**，载体形态 T-3P-0 锁死）。

    只收 kind='beats' 的 plan 节点；key = plan 节点 id（链 id），value = 该链拆拍计划。
    """
    return {
        n["node_id"]: split_beats(n, max_reveals_per_beat=max_reveals_per_beat)
        for n in plan.get("nodes") or []
        if n.get("kind") == "beats"
    }


__all__ = [
    "BeatSlot",
    "DEFAULT_MAX_REVEALS_PER_BEAT",
    "chunk_reveals",
    "split_beats",
    "build_beats_plan",
]
