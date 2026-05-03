"""Single-node generation entry point (T-1.6, ADR-013).

`generate_node` is the only function the upper layers (scene scheduler,
T-1.7 batch runner, /tools审阅 UI) should call to produce one DialogueNode.
It owns three responsibilities:

  1. Assemble a B+ prompt (system + few-shot + context + requirement).
  2. Drive the **3-attempt** structured-output loop (1 initial + 2 retries),
     re-feeding validator errors into the user prompt on retries.
  3. Charge `budget.check_and_charge()` *before* every API call, and **never
     raise** to the caller for non-programmer errors — failures come back as
     `GenerationResult(success=False, failure_reason=...)`.

Validation goes through `/validator/`'s schema layer (we wrap the candidate
node into a minimal envelope so we can re-use the existing JSON-Schema
machinery without copying it). Graph-layer "subset" checks against a
single isolated node are limited to the dialogue/end ⇄ options invariant
(the only structural rule that can be evaluated without sibling nodes).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from generator import budget
from generator.budget import BudgetExceeded
from generator.context_assembler import (
    GraphContext,
    NodeRequirement,
    assemble_context_block,
)
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.models import Node
from generator.prompts import (
    SYSTEM_PROMPT,
    load_iron_oath_few_shot,
    render_few_shot_block,
)
from validator import schema_check

_LOG = logging.getLogger(__name__)

# Rough token-count heuristic. Real tokenisers belong to providers; we only
# need a pre-call estimate for the budget guard. ~4 chars/token is the
# conventional ballpark for mixed CJK/English prompts.
_CHARS_PER_TOKEN = 4
# Output token budget for one Node (narration + 3-6 options). Overshoots are
# fine — budget.check_and_charge gates the *cost*, not the token count.
_OUTPUT_TOKEN_ESTIMATE = 1500

# The few-shot block is identical across every call, so cache it at import
# time. This also makes prompt hashes deterministic for the same scene file.
_FEW_SHOT_BLOCK: str | None = None


def _few_shot_block() -> str:
    global _FEW_SHOT_BLOCK
    if _FEW_SHOT_BLOCK is None:
        _FEW_SHOT_BLOCK = render_few_shot_block(load_iron_oath_few_shot())
    return _FEW_SHOT_BLOCK


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AttemptRecord:
    """Bookkeeping for a single LLM call inside the retry loop."""

    attempt_index: int  # 1-based: 1 = initial, 2/3 = retries
    raw_text: str | None
    validator_errors: list[str]
    cost_usd: float
    finish_reason: str | None = None


@dataclass
class GenerationResult:
    success: bool
    node: dict | None = None
    failure_reason: str | None = None  # "schema_invalid" | "budget_exceeded" | "provider_error"
    attempts: list[AttemptRecord] = field(default_factory=list)
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_node(
    *,
    graph_context: GraphContext,
    node_requirement: NodeRequirement,
    provider: LLMProvider,
    max_retries: int = 2,
) -> GenerationResult:
    """Produce one Node JSON conforming to /schema/node.schema.json.

    Total attempts = 1 + max_retries (default = 3). On every attempt the
    budget is charged *before* the API call. The first BudgetExceeded or
    ProviderError aborts the loop and is reported via failure_reason; only
    schema_invalid is retryable.
    """
    json_schema = Node.model_json_schema()

    base_user_prompt = (
        _few_shot_block()
        + "\n\n## 当前任务\n\n"
        + assemble_context_block(graph_context, node_requirement)
        + "\n\n请输出符合 schema 的单个 Node JSON。"
    )

    attempts: list[AttemptRecord] = []
    total_cost = 0.0
    last_validator_errors: list[str] = []

    for attempt_idx in range(1, max_retries + 2):  # 1 .. (1 + max_retries)
        if attempt_idx == 1:
            user_prompt = base_user_prompt
        else:
            user_prompt = base_user_prompt + _retry_feedback(last_validator_errors)

        # ---- Pre-call budget guard (ADR-012). ----
        input_tokens_est = max(1, len(SYSTEM_PROMPT + user_prompt) // _CHARS_PER_TOKEN)
        output_tokens_est = _OUTPUT_TOKEN_ESTIMATE
        estimated_cost = provider.estimate_cost(input_tokens_est, output_tokens_est)
        try:
            record_id = budget.check_and_charge(
                estimated_cost,
                model_id=getattr(provider, "model_id", "unknown"),
                input_tokens=input_tokens_est,
                output_tokens=output_tokens_est,
            )
        except BudgetExceeded as exc:
            # pre_call_budget_fail: no record was written, nothing to refund.
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_idx,
                    raw_text=None,
                    validator_errors=[f"budget_exceeded: {exc}"],
                    cost_usd=0.0,
                )
            )
            return GenerationResult(
                success=False,
                failure_reason="budget_exceeded",
                attempts=attempts,
                total_cost_usd=total_cost,
            )

        # ---- LLM call. ----
        try:
            response: StructuredResponse = provider.generate_structured(
                SYSTEM_PROMPT, user_prompt, json_schema
            )
        except ProviderError as exc:
            # T-2.11 tri-state refund. Provider-neutral classification:
            # if the exception chain looks like a pre-flight / connect
            # failure (request never reached the server), refund the
            # estimated charge (request_not_sent). Otherwise default to
            # request_sent_failure — the call may have billed.
            # Provider-specific exception types (ConnectFailureError vs
            # APIError vs MidFlightResetError) remain R2.1 work.
            if _is_request_not_sent(exc):
                budget.refund_estimated(record_id, reason="request_not_sent")
                attempts.append(
                    AttemptRecord(
                        attempt_index=attempt_idx,
                        raw_text=None,
                        validator_errors=[f"provider_error: {exc}"],
                        cost_usd=0.0,
                    )
                )
                return GenerationResult(
                    success=False,
                    failure_reason="provider_error",
                    attempts=attempts,
                    total_cost_usd=total_cost,
                )
            _log_refund_deferred(record_id, str(exc))
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_idx,
                    raw_text=None,
                    validator_errors=[f"provider_error: {exc}"],
                    cost_usd=estimated_cost,
                )
            )
            total_cost += estimated_cost
            return GenerationResult(
                success=False,
                failure_reason="provider_error",
                attempts=attempts,
                total_cost_usd=total_cost,
            )

        # ---- Reconcile pre-call estimate with provider-reported actuals. ----
        # T-2.11 scope: `actual_cost_usd` is recomputed here via
        # `provider.estimate_cost(...)` rather than carried on
        # `StructuredResponse`. Adding the field to that dataclass
        # (and the cached/billable/reasoning sub-fields the reviewer
        # also asked for) requires editing /generator/llm_provider.py,
        # which is outside this task's allowed module set — deferred to
        # R2.1 alongside the differential exception classification.
        actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
        budget.reconcile_after_call(
            record_id,
            actual_input_tokens=response.input_tokens,
            actual_output_tokens=response.output_tokens,
            actual_cost_usd=actual_cost,
        )
        total_cost += actual_cost

        # ---- Validate. ----
        validator_errors = _validate_node(response.content, graph_context)
        # T-2.5 critique 4.9: when the caller (scene_strategies.fill_skeleton)
        # has frozen the legal target set, reject any option pointing
        # outside it. Surfaced as a schema_invalid line so the existing
        # retry loop re-feeds it to the LLM unchanged — no new failure
        # reason at this layer.
        validator_errors.extend(
            _check_allowed_targets(response.content, node_requirement.allowed_targets)
        )
        # T-2.5 C-phase (review 4.1): the LLM can return a schema-valid
        # node that silently violates the skeleton's plan — e.g. an
        # `end` node where the skeleton wanted a `dialogue` node.
        # `options=[]` would then bypass `_check_allowed_targets` (no
        # options = no targets to check) and `success=True` bubbles up
        # to fill_skeleton with the topology already corrupted. Pin
        # type / speaker_ref to the requirement before declaring success.
        validator_errors.extend(
            _check_node_requirement(response.content, node_requirement)
        )
        attempts.append(
            AttemptRecord(
                attempt_index=attempt_idx,
                raw_text=response.raw_text,
                validator_errors=validator_errors,
                cost_usd=actual_cost,
                finish_reason=response.finish_reason,
            )
        )

        if not validator_errors:
            return GenerationResult(
                success=True,
                node=response.content,
                attempts=attempts,
                total_cost_usd=total_cost,
            )
        last_validator_errors = validator_errors

    # Exhausted all attempts.
    return GenerationResult(
        success=False,
        failure_reason="schema_invalid",
        attempts=attempts,
        total_cost_usd=total_cost,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _retry_feedback(errors: list[str]) -> str:
    """Tail appended to the user prompt on attempts 2 and 3.

    Kept short and structural — the prompt body is unchanged (ADR-013:
    "重试不换 prompt"); only the trailing feedback differs.
    """
    bullet_list = "\n".join(f"- {e}" for e in errors)
    return (
        "\n\n---\n\n"
        "上次生成失败，错误如下：\n"
        f"{bullet_list}\n\n"
        "请基于以下要求修正后重新输出**完整**节点 JSON。"
    )


def _log_refund_deferred(record_id: str, error_msg: str) -> None:
    """Note that a ProviderError row stays charged pending R2.1 classification."""
    _LOG.info(
        "request_sent_failure refund deferred to R2.1 (record_id=%s, error=%s)",
        record_id,
        error_msg,
    )


# Provider-neutral connect-failure markers. Walks the exception chain
# (`exc.__cause__` ...) for either a stdlib connection-error class or a
# message keyword that strongly implies the request never left the host
# — TLS handshake failures, refused/reset connections, read timeouts.
# Producer-side responses with a status code (HTTP 4xx/5xx, etc.) do
# *not* match here; they belong to request_sent_failure.
_REQUEST_NOT_SENT_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    ConnectionAbortedError,
    TimeoutError,
)
_REQUEST_NOT_SENT_KEYWORDS = (
    "Server disconnected",
    "Connection reset",
    "Connection refused",
    "Connection aborted",
    "Read timeout",
    "ReadTimeout",
    "ConnectError",
    "ConnectTimeout",
    "RemoteProtocolError",
    "handshake",
    "timed out",
    "Name or service not known",
    "Temporary failure in name resolution",
    "call failed",  # GeminiProvider's connect-level wrapper prefix
)


def _is_request_not_sent(exc: BaseException) -> bool:
    """Heuristic: did the request fail before reaching the provider?

    Walks `exc` and its `__cause__` chain looking for a stdlib connection
    error subclass or one of the well-known transient-network markers in
    the message. Provider-specific exception subclasses are R2.1 work; this
    check is intentionally conservative — when in doubt, return False so
    the row stays charged (under-refund is safer than over-refund).
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, _REQUEST_NOT_SENT_TYPES):
            return True
        msg = f"{type(cur).__name__}: {cur}"
        if any(p in msg for p in _REQUEST_NOT_SENT_KEYWORDS):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _check_node_requirement(
    node_dict: Any, node_requirement: NodeRequirement
) -> list[str]:
    """Check the LLM's response matches the structural requirement.

    Two invariants beyond what the JSON Schema layer catches:

      * `node["type"]` matches `node_requirement.node_type`. The schema
        accepts either `dialogue` or `end`; without this check, the LLM
        can produce an `end` node when the skeleton wanted a `dialogue`
        and `options=[]` will bypass `_check_allowed_targets` silently.
      * When `expected_speaker_ref` is non-None, `node["speaker_ref"]`
        must match it exactly. `None` (旁白) is intentionally
        unconstrained — the prompt already says "如确无可用 ID，宁可让
        说话者为旁白". Mismatch on a *named* speaker, by contrast, means
        the skeleton's casting decision was overridden, which T-2.5
        skeleton-first wants to forbid.

    Returned errors share the schema_invalid bucket so the existing
    retry loop re-feeds them. No new failure_reason category needed.
    """
    if not isinstance(node_dict, dict):
        return []  # _validate_node already flagged the wrong shape
    errors: list[str] = []
    actual_type = node_dict.get("type")
    if actual_type != node_requirement.node_type:
        errors.append(
            f"/type: expected {node_requirement.node_type!r} "
            f"(skeleton requirement), got {actual_type!r}"
        )
    expected_speaker = node_requirement.expected_speaker_ref
    if expected_speaker is not None:
        actual_speaker = node_dict.get("speaker_ref")
        if actual_speaker != expected_speaker:
            errors.append(
                f"/speaker_ref: expected {expected_speaker!r} "
                f"(skeleton requirement), got {actual_speaker!r}"
            )
    return errors


def _check_allowed_targets(
    node_dict: Any, allowed_targets: list[str] | None
) -> list[str]:
    """Reject `option.target_node_id` values outside the skeleton's frozen set.

    `allowed_targets is None` → backwards-compat mode (T-1.6 single-node
    generation): no constraint.

    Empty list (`[]`) is *also* a constraint, expressing "this node is an
    `end` node — no targets allowed". The schema layer already enforces
    that `end` nodes have `options == []`, so an empty list here is mostly
    redundant, but we still flag any option that slipped through with a
    populated target — that defends against the case where the LLM
    misidentifies the node type.
    """
    if allowed_targets is None:
        return []
    if not isinstance(node_dict, dict):
        return []  # _validate_node will already have flagged the wrong shape
    options = node_dict.get("options")
    if not isinstance(options, list):
        return []
    allowed_set = set(allowed_targets)
    errors: list[str] = []
    for idx, opt in enumerate(options):
        if not isinstance(opt, dict):
            continue
        target = opt.get("target_node_id")
        if not isinstance(target, str):
            continue  # schema layer will catch missing/non-string targets
        if target not in allowed_set:
            allowed_repr = ", ".join(sorted(allowed_set)) if allowed_set else "(空)"
            errors.append(
                f"/options/{idx}/target_node_id: target {target!r} "
                f"not in skeleton allowed_targets ({allowed_repr})"
            )
    return errors


def _validate_node(node_dict: Any, graph_context: GraphContext) -> list[str]:
    """Run /validator/'s schema layer on the candidate node, plus the
    dialogue/end ⇄ options invariant that JSON Schema expresses via
    `allOf + if/then`.

    Returns a flat list of human-readable error messages (suitable for
    re-feeding into the LLM). Empty list = node passed validation.
    """
    if not isinstance(node_dict, dict):
        return [f"top-level output is {type(node_dict).__name__}, expected JSON object"]

    node_id = node_dict.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        return ["missing or non-string `node_id`"]

    # Wrap the candidate into a minimal but schema-valid envelope so we can
    # re-use validator.schema_check unchanged. The envelope's other fields
    # are *control* — we synthesise them ourselves and trust them, then
    # filter the issue list to only those whose JSON-Pointer location lies
    # inside our candidate node.
    speaker_ref = node_dict.get("speaker_ref")
    char_refs = list(
        {
            *(c.get("character_id") for c in graph_context.involved_characters
              if isinstance(c, dict) and isinstance(c.get("character_id"), str)),
            *([speaker_ref] if isinstance(speaker_ref, str) else []),
        }
    )
    envelope = {
        "schema_version": "0.1.1",
        "graph_id": "_stub_for_single_node_validation",
        "entry_node_id": node_id,
        "scene_anchor": graph_context.scene_anchor,
        "character_refs": char_refs,
        "nodes": {node_id: node_dict},
    }

    pointer_prefix = f"/nodes/{node_id}"
    schema_issues = [
        i for i in schema_check.check(envelope)
        if i.location == pointer_prefix or i.location.startswith(pointer_prefix + "/")
    ]
    errors = [f"{i.location}: {i.message}" for i in schema_issues]

    # Independent-node graph subset: dialogue ⇒ options non-empty; end ⇒ empty.
    # (Encoded as allOf+if/then in node.schema.json; validator will catch
    # this too via the envelope above, so it's a belt-and-braces guard for
    # cases where schema_check skipped due to upstream errors.)
    node_type = node_dict.get("type")
    options = node_dict.get("options")
    if node_type == "dialogue" and (not isinstance(options, list) or not options):
        msg = "type='dialogue' requires `options` to be a non-empty array"
        if msg not in (i.message for i in schema_issues):
            errors.append(f"{pointer_prefix}/options: {msg}")
    if node_type == "end" and (not isinstance(options, list) or len(options) > 0):
        msg = "type='end' requires `options` to be an empty array"
        if msg not in (i.message for i in schema_issues):
            errors.append(f"{pointer_prefix}/options: {msg}")

    return errors
