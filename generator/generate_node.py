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
            budget.check_and_charge(
                estimated_cost,
                model_id=getattr(provider, "model_id", "unknown"),
                input_tokens=input_tokens_est,
                output_tokens=output_tokens_est,
            )
        except BudgetExceeded as exc:
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

        total_cost += estimated_cost

        # ---- Validate. ----
        validator_errors = _validate_node(response.content, graph_context)
        attempts.append(
            AttemptRecord(
                attempt_index=attempt_idx,
                raw_text=response.raw_text,
                validator_errors=validator_errors,
                cost_usd=estimated_cost,
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
