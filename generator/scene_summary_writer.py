"""Semi-automatic prior-scene summary writer (T-3.3 / ADR-024).

Author tool. Given a `scene.json` produced by `generate_scene`, this
module produces a sibling ``<scene>.summary.json`` sidecar carrying a
`PriorSceneSummary`-shaped record:

    {
      "scene_id": "<graph_id>",
      "summary":  "≤ 200 中文字符 prose digest",
      "key_state_paths": [...],
      "chapter_id": <from deps.json sidecar if present>,
      "act_id":    <from deps.json sidecar if present>
    }

Three modes (CLI flags):

  * **default (semi-auto)** — LLM drafts a summary; the author reviews
    on stdout and either accepts, drops into ``$EDITOR``, or aborts.
  * ``--auto-accept`` — LLM drafts; sidecar is written without review.
    Useful for batch back-fill once the author trusts the prompt.
  * ``--manual`` — skip the LLM call entirely and open ``$EDITOR`` on
    a template prefilled from the scene's metadata.

`key_state_paths` is **not** trusted to the LLM — `_extract_key_state_paths`
walks the scene graph itself (every node's ``effects`` /
``on_enter_effects`` and every option's ``effects``) and dedupes the
result. The LLM is asked only for the prose `summary`.

Module boundary (CLAUDE.md rule 2 / generator/CLAUDE.md): the file
talks to `LLMProvider` (never `google.genai` directly), always pre-flight
budget-checks via `budget.check_and_charge`, and writes only inside
``/content/`` (the sidecar lives next to the scene's `.json`). It does
**not** modify schema, ontology, or engine surfaces.

Wired-in callers don't exist yet — T-3.5 batch scheduler will read
these sidecars by path (``SceneSpec.prior_summary_paths``) and feed the
materialised `PriorSceneSummary` list into `generate_scene`.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from generator import budget
from generator.budget import BudgetExceeded
from generator.context_assembler import PriorSceneSummary
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse

_LOG = logging.getLogger(__name__)

# Aligns with the rest of the generator module — the prompt is short, but
# we still pre-flight the budget so a misconfigured PER_CALL_BUDGET_USD
# doesn't sneak through.
_CHARS_PER_TOKEN = 4
_OUTPUT_TOKEN_ESTIMATE = 320

# JSON Schema for the LLM call. Constrained to a single `summary` field
# so the response is unambiguous; the harness validates length post-hoc.
_SUMMARY_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}

_SUMMARY_SYSTEM_PROMPT = (
    "你是 Forgewright 项目的场景摘要生成器。"
    "目标：把一棵已生成的对话图压缩成一段 ≤ 200 中文字符 / ≤ 800 英文字符的"
    "概要，供后续场景生成时回顾。"
    "原则：交代场景核心冲突 + 关键决策走向 + 留下的余韵；不重述 narration 原文；"
    "不引入场景里没有的事实。"
    "输出必须是 valid JSON，仅含一个 `summary` 键。"
)

# Per-summary length cap. ADR-024 quotes "≤ 200 中文字符 / ≤ 800 英文字符";
# the ≤ 200 form is a CJK-codepoint count, the ≤ 800 form is a generic
# codepoint cap. We enforce *both* via `_validate_summary_text` so a
# pure-CJK summary tops out at 200 codepoints, a pure-Latin summary at
# 800, and a mixed summary at whichever bound it hits first. PR #44
# review §4.2 (B-phase finding 🟡): the LLM-draft, manual-edit, and
# direct-write paths all share this validator now — without it,
# provider-returned overlong summaries slipped past `--auto-accept`.
_SUMMARY_MAX_CJK_CHARS = 200
_SUMMARY_MAX_TOTAL_CHARS = 800

# scene_id pattern. Aligned with ADR-023 / dep_index schema's `scene_id`
# pattern `^[a-z0-9_]+$` (PR #44 review §4.3, B-phase finding 🟡).
# Strict-er than dialogue_graph.graph_id which still allows `-`; this
# normalisation matches the sidecar schema so prior_scene_summaries
# never carry IDs the dep_index schema would later reject.
_SCENE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")

# CJK Unified Ideographs ranges that count toward the ≤ 200 CJK cap.
# We use a conservative set: BMP CJK + extension A. Other CJK
# characters (kana, hangul, etc.) aren't in scope for "中文字符".
_CJK_RE = re.compile(r"[㐀-䶿一-鿿]")

# Extension convention for the sidecar — sits next to scene.json /
# scene.deps.json (T-3.2) / scene.version.json (T-3.8a).
_SUMMARY_SUFFIX = ".summary.json"
_DEPS_SUFFIX = ".deps.json"


def _validate_scene_id(scene_id: object, *, source: str) -> str:
    """Reject `scene_id` values that don't match the sidecar schema.

    `source` names the call site (``"sidecar"`` / ``"editor"`` /
    ``"draft"``) so the resulting error message points the author at
    where to fix the input. Centralised here (PR #44 review §4.3) so
    the LLM-draft, manual-edit, and direct read/write paths all share
    one rule rather than each rolling its own non-empty-string check.
    """
    if not isinstance(scene_id, str):
        raise ValueError(
            f"`scene_id` from {source} must be a string, got "
            f"{type(scene_id).__name__}"
        )
    if not _SCENE_ID_PATTERN.fullmatch(scene_id):
        raise ValueError(
            f"`scene_id` from {source} = {scene_id!r} does not match "
            f"ADR-023 pattern ^[a-z0-9_]+$ — re-name the source scene's "
            f"`graph_id` (or normalise here) before writing the sidecar"
        )
    return scene_id


def _validate_summary_text(summary: object, *, source: str) -> str:
    """Reject empty / over-long summary prose at every entry point.

    Enforces both ADR-024 caps:
      * ≤ `_SUMMARY_MAX_CJK_CHARS` (200) for CJK ideographs
      * ≤ `_SUMMARY_MAX_TOTAL_CHARS` (800) total codepoints

    Centralised so the LLM-draft path (`draft_to_summary`), manual-edit
    path (`_summary_from_edited`), and round-trip read path
    (`read_summary_sidecar`) all enforce the same cap (PR #44 review
    §4.2). Without this the `--auto-accept` flow could write an
    over-long sidecar straight to disk.
    """
    if not isinstance(summary, str):
        raise ValueError(
            f"`summary` from {source} must be a string, got "
            f"{type(summary).__name__}"
        )
    body = summary.strip()
    if not body:
        raise ValueError(
            f"`summary` from {source} is empty after stripping whitespace"
        )
    if len(body) > _SUMMARY_MAX_TOTAL_CHARS:
        raise ValueError(
            f"`summary` from {source} is {len(body)} codepoints, "
            f"exceeds {_SUMMARY_MAX_TOTAL_CHARS} (ADR-024 cap)"
        )
    cjk_count = len(_CJK_RE.findall(body))
    if cjk_count > _SUMMARY_MAX_CJK_CHARS:
        raise ValueError(
            f"`summary` from {source} contains {cjk_count} CJK characters, "
            f"exceeds {_SUMMARY_MAX_CJK_CHARS} (ADR-024 中文 cap)"
        )
    return body


@dataclass
class SummaryDraft:
    """LLM-side scratch result before the human review step.

    Distinct from `PriorSceneSummary` so the diff between "what the LLM
    produced" and "what the author committed" can be inspected in tests
    and at the CLI without conflating the two.
    """

    scene_id: str
    summary: str
    key_state_paths: list[str]
    chapter_id: str | None = None
    act_id: str | None = None
    raw_response_text: str | None = None
    cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Sidecar IO
# ---------------------------------------------------------------------------


def summary_sidecar_path(scene_path: Path) -> Path:
    """Return ``<scene>.summary.json`` for a given scene file path.

    Sibling format chosen to match ADR-023's deps sidecar — both live
    next to the scene file so an offline audit can read scene + summary
    + deps together via three sibling reads, no central index lookup.
    """
    return scene_path.with_name(scene_path.stem + _SUMMARY_SUFFIX)


def _deps_sidecar_path(scene_path: Path) -> Path:
    return scene_path.with_name(scene_path.stem + _DEPS_SUFFIX)


def write_summary_sidecar(
    summary: PriorSceneSummary, scene_path: Path
) -> Path:
    """Serialise a `PriorSceneSummary` to ``<scene>.summary.json``.

    Writes a flat JSON object. Optional `chapter_id` / `act_id` are
    omitted from the file when ``None`` so a freshly-authored sidecar
    doesn't carry meaningless ``null`` placeholders that drift out of
    sync as those fields acquire values later.

    PR #44 review §4.2 / §4.3: the sidecar's `scene_id` and `summary`
    are re-validated here as a final write-side guard, even when an
    upstream draft / edit path already enforced the same rules.
    Belt-and-braces because direct programmatic callers (T-3.5 batch
    scheduler, future pipelines) might bypass the CLI flows.
    """
    _validate_scene_id(summary.scene_id, source="write_summary_sidecar")
    _validate_summary_text(summary.summary, source="write_summary_sidecar")
    target = summary_sidecar_path(scene_path)
    payload: dict = {
        "scene_id": summary.scene_id,
        "summary": summary.summary,
        "key_state_paths": list(summary.key_state_paths),
    }
    if summary.chapter_id is not None:
        payload["chapter_id"] = summary.chapter_id
    if summary.act_id is not None:
        payload["act_id"] = summary.act_id
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def read_summary_sidecar(scene_path: Path) -> PriorSceneSummary | None:
    """Round-trip read for ``<scene>.summary.json``.

    Returns ``None`` when the sidecar is missing — callers (T-3.5) treat
    a missing sidecar as "no summary contributed by this scene". Raises
    ``ValueError`` only when the file exists but is malformed enough
    that we can't construct a `PriorSceneSummary` (so an audit notices
    the corruption instead of silently dropping the row).
    """
    target = summary_sidecar_path(scene_path)
    if not target.exists():
        return None
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(
            f"summary sidecar {target} top-level must be a JSON object, "
            f"got {type(raw).__name__}"
        )
    scene_id = _validate_scene_id(raw.get("scene_id"), source=str(target))
    summary = _validate_summary_text(raw.get("summary"), source=str(target))
    state_paths = raw.get("key_state_paths") or []
    if not isinstance(state_paths, list) or not all(
        isinstance(p, str) for p in state_paths
    ):
        raise ValueError(
            f"summary sidecar {target} `key_state_paths` must be a list of strings"
        )
    return PriorSceneSummary(
        scene_id=scene_id,
        summary=summary,
        key_state_paths=list(state_paths),
        chapter_id=raw.get("chapter_id") if isinstance(raw.get("chapter_id"), str) else None,
        act_id=raw.get("act_id") if isinstance(raw.get("act_id"), str) else None,
    )


# ---------------------------------------------------------------------------
# Scene introspection (LLM-free)
# ---------------------------------------------------------------------------


def load_scene(scene_path: Path) -> dict:
    """Load a scene JSON file. Caller-facing wrapper so tests can mock
    the I/O without touching `json.loads` directly."""
    return json.loads(scene_path.read_text(encoding="utf-8"))


def _iter_state_paths(graph: dict) -> Iterable[str]:
    """Yield every `path` string recorded by any node-level effect/condition.

    Walks `nodes[*].on_enter_effects` and `nodes[*].options[*].effects`.
    Other places (preconditions, condition_form siblings) don't write
    state, so they're out of scope for "key_state_paths".
    """
    nodes = graph.get("nodes") or {}
    if not isinstance(nodes, dict):
        return
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        for effect in node.get("on_enter_effects") or []:
            if isinstance(effect, dict):
                path = effect.get("path")
                if isinstance(path, str) and path:
                    yield path
        for opt in node.get("options") or []:
            if not isinstance(opt, dict):
                continue
            for effect in opt.get("effects") or []:
                if isinstance(effect, dict):
                    path = effect.get("path")
                    if isinstance(path, str) and path:
                        yield path


def extract_key_state_paths(graph: dict) -> list[str]:
    """Deduped, order-preserving list of state paths the scene writes.

    Order is the iteration order of `nodes` dict + each node's
    `options` array. Pinning this gives reviewers a stable diff target
    when comparing summary sidecars across versions of the same scene.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for path in _iter_state_paths(graph):
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _scene_id_from_graph(graph: dict, scene_path: Path) -> str:
    """Prefer the scene's own `graph_id`; fall back to filename stem.

    The DialogueGraph schema guarantees `graph_id` for any post-T-2.6
    file; the fallback is for early hand-written fixtures still landing
    in `/content/`."""
    candidate = graph.get("graph_id")
    if isinstance(candidate, str) and candidate:
        return candidate
    return scene_path.stem


def _read_chapter_act_from_deps(scene_path: Path) -> tuple[str | None, str | None]:
    """Pull `chapter_id` / `act_id` from the deps sidecar if present.

    Best effort: a malformed deps file falls through to ``(None, None)``
    and the writer carries on — sidecar metadata enrichment is
    nice-to-have, not load-bearing.
    """
    deps_path = _deps_sidecar_path(scene_path)
    if not deps_path.exists():
        return None, None
    try:
        deps = json.loads(deps_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — best-effort read
        _LOG.info("deps sidecar at %s unreadable; chapter/act left blank", deps_path)
        return None, None
    if not isinstance(deps, dict):
        return None, None
    chapter_id = deps.get("chapter_id") if isinstance(deps.get("chapter_id"), str) else None
    act_id = deps.get("act_id") if isinstance(deps.get("act_id"), str) else None
    return chapter_id, act_id


# ---------------------------------------------------------------------------
# LLM draft path (semi-auto + auto-accept)
# ---------------------------------------------------------------------------


def _build_summary_user_prompt(graph: dict, scene_id: str) -> str:
    """Render the user-side prompt fed to the LLM.

    Includes the scene's `scene_anchor` + the rendered narration list +
    the option text — all the inputs the model needs to write a faithful
    digest. Schema layer is the single response field, so we don't
    worry about leaking control tokens in the user prompt.
    """
    parts: list[str] = []
    scene_anchor = graph.get("scene_anchor") or scene_id
    parts.append(f"## 场景：`{scene_anchor}` (graph_id=`{scene_id}`)")
    nodes = graph.get("nodes") or {}
    parts.append("")
    parts.append("## 节点列表")
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            continue
        speaker = node.get("speaker_ref") or "（旁白）"
        narration = (node.get("narration") or "").strip()
        node_type = node.get("type") or "?"
        parts.append(f"### `{nid}` ({node_type}; speaker={speaker})")
        if narration:
            parts.append(narration)
        opts = node.get("options") or []
        if opts:
            parts.append("**options:**")
            for opt in opts:
                if not isinstance(opt, dict):
                    continue
                opt_text = (opt.get("text") or "").strip()
                target = opt.get("target_node_id") or "?"
                parts.append(f"- → `{target}`: {opt_text}")
        parts.append("")
    parts.append("## 输出要求")
    parts.append(
        f"输出 JSON 对象 `{{\"summary\": \"<≤ {_SUMMARY_MAX_CJK_CHARS} 中文字符 / ≤ {_SUMMARY_MAX_TOTAL_CHARS} 英文字符>\"}}`，"
        "概述本场冲突、关键决策走向、余韵。不要复述 narration 原文。"
    )
    return "\n".join(parts)


def _draft_summary_via_llm(
    *,
    scene_id: str,
    graph: dict,
    provider: LLMProvider,
) -> tuple[str, float, str | None]:
    """Run one budget-gated structured call and return ``(summary_text,
    cost_usd, raw_text)``. Raises `BudgetExceeded` or `ProviderError`
    upstream — the CLI top-level catches both and exits non-zero.
    """
    user_prompt = _build_summary_user_prompt(graph, scene_id)
    input_tokens_est = max(
        1, len(_SUMMARY_SYSTEM_PROMPT + user_prompt) // _CHARS_PER_TOKEN
    )
    estimated_cost = provider.estimate_cost(input_tokens_est, _OUTPUT_TOKEN_ESTIMATE)
    record_id = budget.check_and_charge(
        estimated_cost,
        model_id=getattr(provider, "model_id", "unknown"),
        input_tokens=input_tokens_est,
        output_tokens=_OUTPUT_TOKEN_ESTIMATE,
    )
    response: StructuredResponse = provider.generate_structured(
        _SUMMARY_SYSTEM_PROMPT, user_prompt, _SUMMARY_RESPONSE_SCHEMA
    )
    actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=response.input_tokens,
        actual_output_tokens=response.output_tokens,
        actual_cost_usd=actual_cost,
    )
    if not isinstance(response.content, dict):
        raise ProviderError(
            f"summary response content type {type(response.content).__name__} "
            f"!= dict (raw_text={response.raw_text!r})"
        )
    text = response.content.get("summary")
    # PR #44 review §4.2: enforce the ADR-024 length cap on the LLM's
    # raw output before the prose travels any further. ProviderError
    # (not ValueError) so the CLI surfaces it as `provider failure`
    # alongside other prompt-quality regressions.
    try:
        validated = _validate_summary_text(text, source="LLM response")
    except ValueError as exc:
        raise ProviderError(
            f"summary response failed length cap "
            f"(raw_text={response.raw_text!r}): {exc}"
        ) from exc
    return validated, actual_cost, response.raw_text


def draft_summary(
    *,
    scene_path: Path,
    provider: LLMProvider,
    graph: dict | None = None,
) -> SummaryDraft:
    """End-to-end LLM draft: load scene → call provider → assemble draft.

    Doesn't write the sidecar — the caller decides whether to round-trip
    through the editor / review CLI before committing. `graph` is an
    explicit override path used by tests so they can build a synthetic
    scene without touching disk.

    PR #44 review §4.3: `scene_id` is validated against the ADR-023
    pattern up-front so a draft built from a hyphenated graph_id
    surfaces as a clean ValueError instead of silently producing a
    sidecar the dep_index schema would later reject.
    """
    if graph is None:
        graph = load_scene(scene_path)
    scene_id = _validate_scene_id(
        _scene_id_from_graph(graph, scene_path), source=str(scene_path)
    )
    chapter_id, act_id = _read_chapter_act_from_deps(scene_path)
    summary_text, cost, raw_text = _draft_summary_via_llm(
        scene_id=scene_id, graph=graph, provider=provider
    )
    return SummaryDraft(
        scene_id=scene_id,
        summary=summary_text,
        key_state_paths=extract_key_state_paths(graph),
        chapter_id=chapter_id,
        act_id=act_id,
        raw_response_text=raw_text,
        cost_usd=cost,
    )


def draft_to_summary(draft: SummaryDraft) -> PriorSceneSummary:
    """Promote a `SummaryDraft` to the wire-shape `PriorSceneSummary`.

    Drops draft-only metadata (raw_response_text / cost_usd) so what
    lands in the sidecar matches the dataclass T-3.5 reads back. PR
    #44 review §4.2: re-validates length here too — the LLM-side check
    in `_draft_summary_via_llm` covers the wire path, but a future
    caller that builds a `SummaryDraft` by hand still hits the same
    cap.
    """
    return PriorSceneSummary(
        scene_id=_validate_scene_id(draft.scene_id, source="SummaryDraft"),
        summary=_validate_summary_text(draft.summary, source="SummaryDraft"),
        key_state_paths=list(draft.key_state_paths),
        chapter_id=draft.chapter_id,
        act_id=draft.act_id,
    )


# ---------------------------------------------------------------------------
# Manual (editor-driven) path
# ---------------------------------------------------------------------------


def _editor_command() -> list[str]:
    """``$EDITOR`` honouring the standard precedence (``EDITOR`` then
    ``VISUAL``); falls back to ``vi`` because ``nano`` may not be
    installed on every Mac dev box. Returns a tokenised argv so a user
    can set ``EDITOR='code -w'`` and the wait flag is preserved."""
    raw = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    return raw.split()


def _build_manual_template(
    *,
    scene_id: str,
    graph: dict,
    chapter_id: str | None,
    act_id: str | None,
    initial_summary: str | None = None,
) -> dict:
    """The JSON skeleton the editor opens.

    `initial_summary` is the LLM-drafted text when the author asks for
    edit-mode (CLI flow ``[E]dit``); ``None`` for ``--manual`` cold-
    start where the author writes from scratch. Empty string is
    distinct from ``None`` only at the call site — the template
    serialises both as ``""``.
    """
    template: dict = {
        "scene_id": scene_id,
        "summary": initial_summary or "",
        "key_state_paths": extract_key_state_paths(graph),
    }
    if chapter_id is not None:
        template["chapter_id"] = chapter_id
    if act_id is not None:
        template["act_id"] = act_id
    return template


def _open_editor_with(template: dict) -> dict:
    """Drop the template into a tempfile, run ``$EDITOR``, parse back.

    Raises ``RuntimeError`` if the user saves invalid JSON or empties the
    summary; caller catches and re-prompts. Tempfile is removed in the
    `finally` block regardless of outcome so a crashed editor doesn't
    litter /tmp.
    """
    fd, raw_path = tempfile.mkstemp(suffix=".summary.json", text=True)
    os.close(fd)
    tmp = Path(raw_path)
    try:
        tmp.write_text(
            json.dumps(template, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        cmd = _editor_command() + [str(tmp)]
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"editor exited with non-zero status {result.returncode}"
            )
        edited_raw = tmp.read_text(encoding="utf-8")
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    try:
        edited = json.loads(edited_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"editor saved invalid JSON: {exc}") from exc
    if not isinstance(edited, dict):
        raise RuntimeError(
            f"editor saved non-object top-level: {type(edited).__name__}"
        )
    return edited


def _summary_from_edited(edited: dict) -> PriorSceneSummary:
    """Validate the round-tripped template into a `PriorSceneSummary`.

    Length cap is checked *and rejected* (not silently truncated) so an
    over-long summary doesn't sneak into the sidecar — the author has
    to actively trim the prose, which preserves authorial intent.

    PR #44 review §4.2 / §4.3: shares `_validate_scene_id` and
    `_validate_summary_text` with the LLM-draft and write-sidecar
    paths. A bad template raises ``RuntimeError`` (not ``ValueError``)
    because the editor flow's existing caller already catches
    ``RuntimeError`` to re-prompt — we wrap the underlying error
    message verbatim so the author still sees the schema-aligned
    diagnostic.
    """
    state_paths = edited.get("key_state_paths") or []
    if not isinstance(state_paths, list) or not all(
        isinstance(p, str) for p in state_paths
    ):
        raise RuntimeError("`key_state_paths` must be a list of strings")
    try:
        scene_id = _validate_scene_id(edited.get("scene_id"), source="editor")
        body = _validate_summary_text(edited.get("summary"), source="editor")
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    chapter = edited.get("chapter_id")
    act = edited.get("act_id")
    return PriorSceneSummary(
        scene_id=scene_id,
        summary=body,
        key_state_paths=list(state_paths),
        chapter_id=chapter if isinstance(chapter, str) and chapter else None,
        act_id=act if isinstance(act, str) and act else None,
    )


def manual_edit(
    *,
    scene_path: Path,
    initial_draft: SummaryDraft | None = None,
    graph: dict | None = None,
) -> PriorSceneSummary:
    """Open ``$EDITOR`` on a template and parse the saved JSON back.

    `initial_draft` (when supplied) seeds the template with the LLM's
    text so the author edits in place — used by the semi-auto ``[E]dit``
    path. `--manual` mode passes ``initial_draft=None`` and the
    template's `summary` starts blank.

    PR #44 review §4.3: validate the seed scene_id against
    ADR-023 pattern up-front so a hyphenated graph_id can't slip into
    the editor template (and back out into the sidecar).
    """
    if graph is None:
        graph = load_scene(scene_path)
    seed_scene_id = (
        initial_draft.scene_id
        if initial_draft is not None
        else _scene_id_from_graph(graph, scene_path)
    )
    try:
        scene_id = _validate_scene_id(seed_scene_id, source=str(scene_path))
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    chapter_id, act_id = _read_chapter_act_from_deps(scene_path)
    if initial_draft is not None:
        if initial_draft.chapter_id is not None:
            chapter_id = initial_draft.chapter_id
        if initial_draft.act_id is not None:
            act_id = initial_draft.act_id
    template = _build_manual_template(
        scene_id=scene_id,
        graph=graph,
        chapter_id=chapter_id,
        act_id=act_id,
        initial_summary=(
            initial_draft.summary if initial_draft is not None else None
        ),
    )
    edited = _open_editor_with(template)
    return _summary_from_edited(edited)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print(stream, msg: str) -> None:
    """Tiny wrapper so tests can capture stdout/stderr identically."""
    print(msg, file=stream, flush=True)


def _prompt_review(draft: SummaryDraft, *, input_fn=input) -> str:
    """Prompt the author for ``[A]ccept / [E]dit / [Q]uit``.

    Returns the lowercase first letter so callers branch via simple
    ``in {"a", "e", "q"}`` checks. Empty input loops until a valid
    answer to keep the CLI honest about what it's about to do.
    """
    while True:
        answer = (input_fn("[A]ccept / [E]dit / [Q]uit ? ") or "").strip().lower()
        if answer.startswith("a"):
            return "a"
        if answer.startswith("e"):
            return "e"
        if answer.startswith("q"):
            return "q"


def _render_draft_for_review(draft: SummaryDraft) -> str:
    return (
        f"scene_id:        {draft.scene_id}\n"
        f"chapter_id:      {draft.chapter_id or '(none)'}\n"
        f"act_id:          {draft.act_id or '(none)'}\n"
        f"key_state_paths: {draft.key_state_paths}\n"
        f"cost_usd:        ${draft.cost_usd:.4f}\n"
        f"---\nsummary:\n{draft.summary}\n"
    )


def run_cli(
    *,
    scene_path: Path,
    auto_accept: bool,
    manual: bool,
    provider_factory,
    stdout=None,
    stderr=None,
    input_fn=input,
) -> int:
    """Tested orchestration entry. Returns the CLI exit code.

    `provider_factory` is a 0-arg callable returning an `LLMProvider`;
    inverting the dependency lets tests inject a `FakeProvider` without
    touching env vars or `dotenv`. `manual=True` skips it entirely so
    the test suite can exercise the editor flow without an LLM stub.
    """
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr

    if manual and auto_accept:
        _print(stderr, "error: --manual and --auto-accept are mutually exclusive.")
        return 2

    if not scene_path.exists():
        _print(stderr, f"error: scene file not found: {scene_path}")
        return 2

    graph = load_scene(scene_path)
    sidecar = summary_sidecar_path(scene_path)

    if manual:
        try:
            summary = manual_edit(scene_path=scene_path, graph=graph)
        except RuntimeError as exc:
            _print(stderr, f"error: manual edit aborted: {exc}")
            return 1
        write_summary_sidecar(summary, scene_path)
        _print(stdout, f"wrote {sidecar}")
        return 0

    provider = provider_factory()
    try:
        draft = draft_summary(
            scene_path=scene_path, provider=provider, graph=graph
        )
    except BudgetExceeded as exc:
        _print(stderr, f"error: budget exceeded before LLM call: {exc}")
        return 3
    except ProviderError as exc:
        _print(stderr, f"error: provider failure: {exc}")
        return 4

    _print(stdout, _render_draft_for_review(draft))

    if auto_accept:
        summary = draft_to_summary(draft)
        write_summary_sidecar(summary, scene_path)
        _print(stdout, f"auto-accepted; wrote {sidecar}")
        return 0

    answer = _prompt_review(draft, input_fn=input_fn)
    if answer == "q":
        _print(stdout, "aborted by user; no sidecar written.")
        return 5
    if answer == "a":
        summary = draft_to_summary(draft)
        write_summary_sidecar(summary, scene_path)
        _print(stdout, f"wrote {sidecar}")
        return 0
    # answer == "e"
    try:
        summary = manual_edit(
            scene_path=scene_path, initial_draft=draft, graph=graph
        )
    except RuntimeError as exc:
        _print(stderr, f"error: manual edit aborted: {exc}")
        return 1
    write_summary_sidecar(summary, scene_path)
    _print(stdout, f"wrote {sidecar}")
    return 0


def _build_default_provider() -> LLMProvider:
    """Lazy import so test fixtures can pass `provider_factory` without
    setting any provider env var at import time."""
    from generator.providers import get_default_provider

    return get_default_provider()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.scene_summary_writer",
        description=(
            "Write a <scene>.summary.json sidecar for ADR-024 "
            "long-conversation-consistency C-tier (T-3.3)."
        ),
    )
    parser.add_argument(
        "scene_path",
        type=Path,
        help="Path to the scene's JSON file (e.g. /content/scenes/foo.json).",
    )
    parser.add_argument(
        "--auto-accept",
        action="store_true",
        help=(
            "Skip the [A/E/Q] review prompt and write the LLM draft "
            "directly. Use only when batch-back-filling summaries you've "
            "already vetted out-of-band."
        ),
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help=(
            "Skip the LLM call and open $EDITOR on a template populated "
            "from the scene metadata. Mutually exclusive with --auto-accept."
        ),
    )
    args = parser.parse_args(argv)
    return run_cli(
        scene_path=args.scene_path,
        auto_accept=args.auto_accept,
        manual=args.manual,
        provider_factory=_build_default_provider,
    )


if __name__ == "__main__":  # pragma: no cover
    # Match the rest of the generator CLIs: load .env if present so the
    # user doesn't have to set provider creds inline.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    sys.exit(main())


__all__ = [
    "PriorSceneSummary",
    "SummaryDraft",
    "summary_sidecar_path",
    "write_summary_sidecar",
    "read_summary_sidecar",
    "load_scene",
    "extract_key_state_paths",
    "draft_summary",
    "draft_to_summary",
    "manual_edit",
    "run_cli",
    "main",
]
