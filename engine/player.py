"""T-0.6 终端播放器：读 JSON 对话图，在命令行里和玩家交互，走完图退出。

约束（严）：ADR-002 无运行时 LLM / 无网络 IO；ADR-004 极薄（整个 /engine 业务代码 ≤ 500 行）。
依赖：/schema（加载时校验）、/state（WorldState / apply_effect / evaluate_condition / ontology）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from state import ontology
from state.conditions import evaluate_condition
from state.effects import apply_effect
from state.world_state import WorldState

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
_SCHEMA_FILES = (
    "dialogue_graph.schema.json",
    "node.schema.json",
    "option.schema.json",
    "state_effect.schema.json",
    "state_condition.schema.json",
)
_EXPECTED_MAJOR = "0"
_VISIT_LIMIT = 1000


def _build_validator() -> Draft202012Validator:
    registry = Registry()
    for name in _SCHEMA_FILES:
        schema = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(
            uri=schema["$id"], resource=Resource.from_contents(schema)
        )
    root = json.loads((_SCHEMA_DIR / "dialogue_graph.schema.json").read_text("utf-8"))
    return Draft202012Validator(root, registry=registry)


_VALIDATOR = _build_validator()


def _fail(message: str, err: TextIO) -> None:
    err.write(message + "\n")
    err.flush()
    raise SystemExit(1)


def _load_graph(graph_path: str, err: TextIO) -> dict:
    path = Path(graph_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _fail(f"[错误] 加载对话图失败 {graph_path!r}: {e}", err)

    version = payload.get("schema_version") if isinstance(payload, dict) else None
    if isinstance(version, str):
        major = version.split(".", 1)[0]
        if major != _EXPECTED_MAJOR:
            _fail(
                f"[错误] schema_version MAJOR 不兼容: 文件 {version!r} vs "
                f"期望 {_EXPECTED_MAJOR}.x.x（SCHEMA_v0.md §1.3）",
                err,
            )

    errors = sorted(_VALIDATOR.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        details = "\n  - ".join(
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in errors
        )
        _fail(f"[错误] 对话图 Schema 校验失败:\n  - {details}", err)
    return payload


def _resolve_display(ref: str | None, err: TextIO) -> str:
    if ref is None:
        return "（旁白）"
    entity = ontology.get_entity(ref)
    if entity is None:
        err.write(f"[警告] 本体条目未找到: {ref}（使用原 ref 显示）\n")
        return ref
    return entity.get("display_name", ref)


def _print_node_header(node: dict, out: TextIO, err: TextIO) -> None:
    out.write("\n" + "-" * 60 + "\n")
    speaker = _resolve_display(node.get("speaker_ref"), err)
    location = _resolve_display(node.get("location_ref"), err)
    out.write(f"【{speaker} · {location}】\n\n")
    out.write(node["narration"] + "\n\n")


def _render_options(
    options: list, state: WorldState, out: TextIO
) -> list[tuple[int, dict]]:
    numbered: list[tuple[int, dict]] = []
    next_num = 1
    for opt in options:
        cond = opt.get("condition")
        available = True if cond is None else evaluate_condition(state, cond)
        if available:
            out.write(f"  {next_num}. {opt['text']}\n")
            numbered.append((next_num, opt))
            next_num += 1
            continue
        behavior = opt["unavailable_behavior"]
        if behavior == "hide":
            continue
        prefix = "[不可选·条件不满足]" if behavior == "disable_with_hint" else "[不可选]"
        out.write(f"  {prefix} {opt['text']}\n")
    out.write("\n")
    return numbered


def _prompt_choice(
    numbered: list[tuple[int, dict]], stdin: TextIO, out: TextIO
) -> dict:
    max_n = len(numbered)
    valid = {num: opt for num, opt in numbered}
    while True:
        out.write(f"> 选择（1-{max_n}）: ")
        out.flush()
        line = stdin.readline()
        if line == "":
            raise RuntimeError("stdin closed before a valid choice was entered")
        stripped = line.strip()
        if not stripped.isdigit():
            out.write("  （请输入数字）\n")
            continue
        idx = int(stripped)
        if idx in valid:
            return valid[idx]
        out.write(f"  （数字超出范围；请输入 1-{max_n}）\n")


def play(
    graph_path: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> dict:
    """运行播放器。返回终局 WorldState 的 as_dict()。

    校验失败（含 schema_version MAJOR 不匹配）会通过 sys.exit(1) 退出。
    """
    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout
    err_stream = stdout if stdout is not None else sys.stderr

    graph = _load_graph(graph_path, err_stream)

    state = WorldState()
    nodes = graph["nodes"]
    current_id = graph["entry_node_id"]
    visits: dict[str, int] = {}

    while True:
        visits[current_id] = visits.get(current_id, 0) + 1
        if visits[current_id] > _VISIT_LIMIT:
            raise RuntimeError(
                f"node {current_id!r} visited >{_VISIT_LIMIT} times; aborting (loop guard)"
            )

        node = nodes[current_id]
        _print_node_header(node, out_stream, err_stream)

        for effect in node.get("on_enter_effects", []):
            apply_effect(state, effect)

        if node["type"] == "end":
            out_stream.write("—— 结局 ——\n")
            break

        numbered = _render_options(node["options"], state, out_stream)
        if not numbered:
            out_stream.write("[无可选项；场景中止]\n")
            break

        chosen = _prompt_choice(numbered, in_stream, out_stream)
        for effect in chosen.get("effects", []):
            apply_effect(state, effect)
        current_id = chosen["target_node_id"]

    return state.as_dict()
