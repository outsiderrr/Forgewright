"""T-3.0 R3.1: json-only output guard for scene-level prompts.

Pins the hard-constraint phrasing the system prompt + per-fill extras
emit so a future refactor can't quietly soften it back to the pre-R3.1
"仅输出 JSON 本身" wording (which baseline_010 / baseline_011 advisory
caught at iter07 / iter09 / iter11 leaking markdown fences + control
tokens inside json mode).

Two surfaces, two assertions:

  * ``SCENE_SYSTEM_PROMPT`` — system message; covers skeleton + fill
    requests. The "JSON-only 硬约束" section must list the explicit
    first-char / last-char rule.
  * ``render_fill_extras`` / ``render_json_only_guard`` — per-fill
    user-context; defense in depth right next to the response site.
"""
from __future__ import annotations

from generator.prompts.scene.fill import (
    render_fill_extras,
    render_json_only_guard,
)
from generator.prompts.scene.system import SCENE_SYSTEM_PROMPT


_FIRST_CHAR_PHRASE = "输出第一个字符必须是 `{` 或 `["
_LAST_CHAR_PHRASE = "最后一个字符必须是 `}` 或 `]`"
_NO_FENCE_PHRASE = "markdown code fence"


def test_system_prompt_contains_json_only_hard_constraint():
    """The shared system prompt must carry the R3.1 first-char / last-char
    rule. Skeleton and fill calls both inherit this; if it weakens, both
    R2.7 sanitizer and R2.10b retry can't recover an LLM that prepends
    "好的，这是 JSON" preamble."""
    assert "JSON-only 硬约束" in SCENE_SYSTEM_PROMPT
    assert _FIRST_CHAR_PHRASE in SCENE_SYSTEM_PROMPT
    assert _LAST_CHAR_PHRASE in SCENE_SYSTEM_PROMPT
    assert _NO_FENCE_PHRASE in SCENE_SYSTEM_PROMPT


def test_render_json_only_guard_contains_hard_constraint():
    """Per-fill user-context guard: the standalone helper emits the
    same first/last-char phrasing so callers that bypass
    ``render_fill_extras`` (future scenarios) still get the constraint."""
    body = render_json_only_guard()
    assert "JSON-only 输出格式" in body
    assert _FIRST_CHAR_PHRASE in body
    assert _LAST_CHAR_PHRASE in body
    assert _NO_FENCE_PHRASE in body
    assert "<think>" in body  # control-token pre-emption


def test_render_fill_extras_appends_json_only_guard_last():
    """``render_fill_extras`` must include the json-only guard, and the
    guard must sit at the tail of the rendered block — instruction
    following is statistically strongest closest to the response site,
    so the constraint goes after the bleed-through guard, not before.
    """
    rendered = render_fill_extras(
        filled_so_far=[("n_arrival", "推开沉重的橡木门 …")],
        beat="承认",
        index=2,
        total=5,
    )
    assert "JSON-only 输出格式" in rendered
    json_section_idx = rendered.index("JSON-only 输出格式")
    bleed_section_idx = rendered.index("context bleed-through 防御")
    assert json_section_idx > bleed_section_idx, (
        "json-only guard must follow the bleed-through guard so it's the "
        "last constraint the LLM sees before generating the response."
    )


def test_render_fill_extras_first_node_skips_summary_but_keeps_guards():
    """First-node case (``filled_so_far == []``) intentionally omits the
    'previously filled' summary section (R2.6) — but both guards must
    still render so the json-only constraint is enforced from node 0."""
    rendered = render_fill_extras(
        filled_so_far=[],
        beat="抵达驿站",
        index=0,
        total=5,
    )
    assert "前面已生成节点的 narration 摘要" not in rendered
    assert "context bleed-through 防御" in rendered
    assert "JSON-only 输出格式" in rendered
