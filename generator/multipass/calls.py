"""小调用 helper（structured_call）—— budget 拦截 + provider + 对账/退款 + 尺寸护栏.

把原型脚本 multipass_lucy_dry_run._one_call 正式化（DESIGN §5）：
  - 每次文本 LLM 调用前 budget.check_and_charge()（ADR-012，无例外）；
  - ProviderError 全额退款再抛；成功后按实际 token 对账；
  - **est_output_tokens 护栏**：超过 MAX_EST_OUTPUT_TOKENS 直接抛 CallTooLargeError——
    注定触发中转站上游超时（实测 751s 后 502）的大调用根本不让出门。
    引擎只允许 6 种已验证的小调用类型（契约/拓扑/骨架/正文/beat 链/end 收束）。
"""
from __future__ import annotations

import time
from typing import Any

from generator import budget
from generator.llm_provider import ProviderError

# 中转站实测：复杂大输出（一次设计 4 节点 ≈ 数千 token 输出）持续 502；
# 已验证小调用（≤1500 est output tokens）3-35s 正常。上限留一点余量。
MAX_EST_OUTPUT_TOKENS = 2000


class CallTooLargeError(ValueError):
    """est_output_tokens 超护栏——该调用必须拆小，不允许发出。"""


def structured_call(
    provider: Any,
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    est_output_tokens: int,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """跑一次结构化小调用；返回 (content, meta)。

    Args:
        provider: LLMProvider 实现（generate_structured + estimate_cost + model_id）。
        system_prompt / user_prompt / json_schema: 调用三件套。
        est_output_tokens: 预估输出 token（budget 预充 + 尺寸护栏用）。
        label: 调用标签（meta / 退款理由用）。

    Raises:
        CallTooLargeError: est_output_tokens 超 MAX_EST_OUTPUT_TOKENS。
        BudgetExceeded: 预算不足（budget 层抛出）。
        ProviderError: provider 失败（已退款）。
    """
    if est_output_tokens > MAX_EST_OUTPUT_TOKENS:
        raise CallTooLargeError(
            f"调用 {label!r} est_output_tokens={est_output_tokens} > "
            f"{MAX_EST_OUTPUT_TOKENS}：大结构生成必须拆小（DESIGN §5），不允许发出。"
        )
    est_input_tokens = (len(system_prompt) + len(user_prompt)) // 4
    est_cost = provider.estimate_cost(est_input_tokens, est_output_tokens)
    record_id = budget.check_and_charge(
        est_cost,
        model_id=provider.model_id,
        input_tokens=est_input_tokens,
        output_tokens=est_output_tokens,
    )
    t0 = time.time()
    try:
        resp = provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
        )
    except ProviderError:
        budget.refund_estimated(record_id, reason=f"provider_error in {label}")
        raise
    elapsed = time.time() - t0
    actual_cost = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=resp.input_tokens,
        actual_output_tokens=resp.output_tokens,
        actual_cost_usd=actual_cost,
    )
    meta = {
        "label": label,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "actual_cost_usd": actual_cost,
        "elapsed_sec": elapsed,
        "finish_reason": resp.finish_reason,
    }
    return resp.content, meta


__all__ = ["structured_call", "CallTooLargeError", "MAX_EST_OUTPUT_TOKENS"]
