"""LLMProvider Protocol — see ADR-011.

The Protocol is intentionally minimal: a single structured-output call plus a
cost estimator. Retry, budget, and prompt assembly all live one layer up
(`generate_node`, `budget.py`). Concrete providers live under
`generator/providers/` and are the only place where vendor SDKs may be
imported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Raised by a provider when a single API call fails (network, API,
    decoding). Callers decide whether to retry."""


@dataclass
class StructuredResponse:
    content: dict
    raw_text: str
    input_tokens: int
    output_tokens: int
    model_id: str
    finish_reason: str


@runtime_checkable
class LLMProvider(Protocol):
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse: ...

    def estimate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> float: ...
