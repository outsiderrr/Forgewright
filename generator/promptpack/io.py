"""promptpack IO envelope 冻结 + 共享 loader（T-3P-0，critique F-3）.

P-A（T-3P-1 渲染器）/ P-B（T-3P-2 回流合并）**只准经本模块读输入**，禁止各写一套：

  - design.json 沿 engine.write_artifacts 现有 **wrapper 形态**
    （顶层 = {design, call_metas, warnings, validation, status, failure_reason}），
    消费者读 payload["design"]；
  - spec 文件沿 specs/lucy.json 现有 **{config, spec} wrapper**，消费者读
    payload["spec"]；config 段与 design.run_config 同源同形，给了 design 时
    cross-check 一致性。

输入不符合冻结契约 → PromptpackInputError（CLI 层对应退出码 EXIT_USAGE=2）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PromptpackInputError(ValueError):
    """输入文件不符合冻结的 IO envelope 契约（对应 CLI 退出码 2 用法・输入错误）。"""


# design.json 的 design 段必须携带的两 key（T-3P-0 structure-only 起才有；
# 缺 = legacy 产物，报错引导重新产出而不是静默兜底）
REQUIRED_DESIGN_KEYS = ("beats_plan", "run_config")

# run_config / spec config 段的同源同形五字段（SceneRunConfig 落盘形态）
RUN_CONFIG_FIELDS = ("graph_id", "scene_anchor", "speaker_ref", "character_refs", "npc_name")

# spec config 段省略 npc_name 时的默认值（与 SceneRunConfig.npc_name 默认一致）
_NPC_NAME_DEFAULT = "NPC"


# BeatSlot 载体形态（与 beat_split.BeatSlot 一致；T-3P-0 锁死为恰好三 key）
_BEAT_SLOT_KEYS = frozenset({"beat_id", "reveals", "is_last"})


def load_design_artifact(path: str | Path) -> dict[str, Any]:
    """读 design.json（wrapper 形态）→ 返回内层 design dict。

    边界拒收（全部 PromptpackInputError，按 wrapper 的 status 分诊）：
      - 失败运行产物（status != success）→ 透出 status + failure_reason；
      - 成功但缺 beats_plan / run_config → 非 structure-only 产物（legacy 或
        全量生成），引导先跑 --structure-only；
      - beats_plan / run_config 载体形态不符（非 dict / 缺字段 / BeatSlot 走形）。
    """
    path = Path(path)
    payload = _load_json(path)
    if not isinstance(payload, dict) or "design" not in payload:
        raise PromptpackInputError(
            f"{path}: 不是 design.json 的 wrapper 形态（顶层缺 'design' key；"
            "期望 engine.write_artifacts 产物：{design, call_metas, warnings, "
            "validation, status, failure_reason}）"
        )
    design = payload["design"]
    if not isinstance(design, dict):
        raise PromptpackInputError(f"{path}: wrapper 的 design 段不是 dict")
    status = payload.get("status")
    if status != "success":
        raise PromptpackInputError(
            f"{path}: 该 design.json 来自失败运行（status={status!r}，"
            f"failure_reason={payload.get('failure_reason')!r}）——先解决失败原因、"
            "重跑 --structure-only 产出成功产物"
        )
    missing = [k for k in REQUIRED_DESIGN_KEYS if k not in design]
    if missing:
        raise PromptpackInputError(
            f"{path}: design 段缺 {missing}——这不是 structure-only 产物"
            "（legacy 或全量生成的 design.json）；请用 `python generator/scripts/"
            "run_multipass_scene.py --spec <spec> --structure-only` 产出携带 "
            "beats_plan / run_config 的 design.json"
        )
    _check_beats_plan_shape(design["beats_plan"], path)
    _check_run_config_shape(design["run_config"], path)
    _check_beats_plan_consistency(design["beats_plan"], design.get("topology"), path)
    return design


def _check_beats_plan_shape(beats_plan: Any, path: Path) -> None:
    """beats_plan 载体形态校验：dict 按链分组，值 = BeatSlot（恰好三 key + 叶类型）列表。"""
    if not isinstance(beats_plan, dict):
        raise PromptpackInputError(
            f"{path}: beats_plan 不是 dict（载体形态 T-3P-0 锁死为按链分组的 dict，"
            "不是 flat list）"
        )
    for pid, slots in beats_plan.items():
        if not isinstance(slots, list):
            raise PromptpackInputError(f"{path}: beats_plan[{pid!r}] 不是 list")
        for i, slot in enumerate(slots):
            if not isinstance(slot, dict) or set(slot) != _BEAT_SLOT_KEYS:
                raise PromptpackInputError(
                    f"{path}: beats_plan[{pid!r}][{i}] 不是 BeatSlot 三 key 形态 "
                    "{beat_id, reveals, is_last}"
                )
            if (
                not isinstance(slot["beat_id"], str)
                or not isinstance(slot["reveals"], list)
                or not all(isinstance(r, str) for r in slot["reveals"])
                or not isinstance(slot["is_last"], bool)
            ):
                raise PromptpackInputError(
                    f"{path}: beats_plan[{pid!r}][{i}] 叶类型不符"
                    "（beat_id: str / reveals: list[str] / is_last: bool）"
                )


def _check_beats_plan_consistency(
    beats_plan: dict[str, Any], topology: Any, path: Path
) -> None:
    """beats_plan ↔ topology 一致性核对（cap 无关，不复算拆拍策略）。

    防"改了 topology 没重跑拆拍"（或反之）的错位产物流进 P-A/P-B：
      - 链集合 = topology 里全部 kind=beats 节点；
      - 每链线索并集按序 = topology 节点的 reveals（不检查每拍几条——那是可调参数）；
      - beat_id = {pid}_b{1..N} 连续、末拍 is_last=True。
    """
    if not isinstance(topology, dict):
        raise PromptpackInputError(f"{path}: design 缺合法 topology 段，无法核对 beats_plan")
    beats_nodes = {
        n["node_id"]: n
        for n in topology.get("nodes") or []
        if isinstance(n, dict) and n.get("kind") == "beats"
    }
    if set(beats_plan) != set(beats_nodes):
        raise PromptpackInputError(
            f"{path}: beats_plan 链集合 {sorted(beats_plan)} 与 topology 的 beats 节点 "
            f"{sorted(beats_nodes)} 不一致——topology 与拆拍计划疑似不同批产物"
        )
    for pid, slots in beats_plan.items():
        flattened = [r for slot in slots for r in slot["reveals"]]
        expected = list(beats_nodes[pid].get("reveals") or [])
        if flattened != expected:
            raise PromptpackInputError(
                f"{path}: beats_plan[{pid!r}] 的线索并集与 topology 该链 reveals 不一致"
                "——topology 改动后未重跑 structure-only（或反之）"
            )
        ids = [slot["beat_id"] for slot in slots]
        if ids != [f"{pid}_b{i}" for i in range(1, len(slots) + 1)] or (
            slots and [s["is_last"] for s in slots] != [False] * (len(slots) - 1) + [True]
        ):
            raise PromptpackInputError(
                f"{path}: beats_plan[{pid!r}] 的 beat_id 编号 / is_last 不符合 "
                "{pid}_b{{1..N}} 连续 + 末拍 is_last 约定"
            )


def _check_run_config_shape(run_config: Any, path: Path) -> None:
    """run_config 载体形态校验：dict 且冻结五字段齐全。"""
    if not isinstance(run_config, dict):
        raise PromptpackInputError(f"{path}: run_config 不是 dict")
    missing = [f for f in RUN_CONFIG_FIELDS if f not in run_config]
    if missing:
        raise PromptpackInputError(
            f"{path}: run_config 缺字段 {missing}（冻结五字段 = {RUN_CONFIG_FIELDS}）"
        )


def load_scene_spec(
    path: str | Path, *, design: dict[str, Any] | None = None
) -> dict[str, Any]:
    """读 spec 文件（{config, spec} wrapper）→ 返回内层 spec dict。

    给了 design 时 cross-check payload["config"] 与 design["run_config"] 一致
    （五字段同源同形；npc_name 省略按 SceneRunConfig 默认 'NPC' 比对），
    不一致报错——防止拿 A 场景的 spec 配 B 场景的 design。
    """
    path = Path(path)
    payload = _load_json(path)
    if not isinstance(payload, dict) or "config" not in payload or "spec" not in payload:
        raise PromptpackInputError(
            f"{path}: 不是 spec 文件的 {{config, spec}} wrapper 形态"
            "（期望 specs/lucy.json 现状：顶层 config + spec 两段）"
        )
    if not isinstance(payload["config"], dict):
        raise PromptpackInputError(f"{path}: config 段不是 dict")
    if not isinstance(payload["spec"], dict):
        raise PromptpackInputError(f"{path}: spec 段不是 dict")
    if design is not None:
        run_config = design.get("run_config")
        _check_run_config_shape(run_config, path)
        _cross_check_config(payload["config"], run_config, path)
    return payload["spec"]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise PromptpackInputError(f"{path}: 文件不存在") from e
    except json.JSONDecodeError as e:
        raise PromptpackInputError(f"{path}: 不是合法 JSON（{e}）") from e


def _cross_check_config(
    config: dict[str, Any], run_config: dict[str, Any], path: Path
) -> None:
    """spec config ↔ design.run_config 五字段一致性核对；列出全部不一致字段后一次报错。"""
    mismatches: list[str] = []
    for f in RUN_CONFIG_FIELDS:
        cfg_val = config.get(f, _NPC_NAME_DEFAULT) if f == "npc_name" else config.get(f)
        rc_val = run_config.get(f)
        if cfg_val != rc_val:
            mismatches.append(f"{f}: spec config={cfg_val!r} vs design.run_config={rc_val!r}")
    if mismatches:
        raise PromptpackInputError(
            f"{path}: spec config 与 design.run_config 不一致（两者本应同源同形；"
            f"疑似拿错场景的 spec/design 配对）：\n  - " + "\n  - ".join(mismatches)
        )


__all__ = [
    "PromptpackInputError",
    "REQUIRED_DESIGN_KEYS",
    "RUN_CONFIG_FIELDS",
    "load_design_artifact",
    "load_scene_spec",
]
