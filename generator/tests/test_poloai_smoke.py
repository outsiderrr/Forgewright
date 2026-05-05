"""Smoke test: one real PoloAI call. Costs < $0.01 (estimate).

Skipped by default (see conftest.py). Run with:
    pytest -m smoke generator/tests/test_poloai_smoke.py -s

Requires POLOAI_API_KEY in env / .env. Mirrors test_gemini_smoke shape.
"""

from __future__ import annotations

import os

import pytest

from generator.llm_provider import StructuredResponse
from generator.providers import PoloAIProvider

pytestmark = pytest.mark.smoke


def test_poloai_minimal_structured_call() -> None:
    if not os.environ.get("POLOAI_API_KEY"):
        pytest.skip("POLOAI_API_KEY not set")

    provider = PoloAIProvider()
    schema = {
        "type": "object",
        "properties": {"echo": {"type": "string"}},
        "required": ["echo"],
    }
    resp = provider.generate_structured(
        system_prompt=(
            "You are an echo bot. Reply with valid JSON matching the schema."
        ),
        user_prompt='Set "echo" to the string "ping".',
        json_schema=schema,
    )

    assert isinstance(resp, StructuredResponse)
    assert isinstance(resp.content, dict)
    assert "echo" in resp.content
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.model_id  # non-empty (POLOAI_MODEL_ID may override)
    assert resp.finish_reason  # non-empty string

    cost = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    print(
        f"\n[smoke] model={resp.model_id} json_mode={provider.json_mode} "
        f"in={resp.input_tokens} out={resp.output_tokens} "
        f"finish={resp.finish_reason} cost=${cost:.6f}\n"
        f"[smoke] content={resp.content}"
    )
