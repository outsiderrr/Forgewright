"""Smoke test: one real PoloAI call. Costs < $0.01 (estimate).

Skipped by default (see conftest.py). Run with:
    pytest -m smoke generator/tests/test_poloai_smoke.py -s

Requires POLOAI_API_KEY in env / .env. Mirrors test_gemini_smoke shape.
"""

from __future__ import annotations

import os

import pytest

from generator.llm_provider import ProviderError, StructuredResponse
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


def test_poloai_skeleton_schema_e2e() -> None:
    """R2.8: real upstream pass for the live ``_SKELETON_RESPONSE_SCHEMA``.

    R2.7's smoke used a toy schema with no nullable fields, so the
    type-array nullable regression slipped past it — baseline_006 caught
    it later at 0% gross_pass_rate. This test exercises the schema that
    actually breaks Gemini protobuf when sanitization is incomplete, so
    a future regression of either provider's sanitizer is caught at
    smoke-time instead of at batch-generation time.

    Skipped unless POLOAI_API_KEY is set; one minimal call.
    """
    if not os.environ.get("POLOAI_API_KEY"):
        pytest.skip("POLOAI_API_KEY not set")

    from generator.scene_strategies import _SKELETON_RESPONSE_SCHEMA

    provider = PoloAIProvider()
    try:
        resp = provider.generate_structured(
            system_prompt=(
                "You are a scene skeleton drafter. Reply with valid JSON "
                "matching the supplied schema. Keep the response minimal — "
                "one node, one edge — just enough to satisfy the schema."
            ),
            user_prompt=(
                "Draft a single trivial 1-node skeleton (no choices) that "
                "validates against the schema. Do not invent content beyond "
                "what the schema requires."
            ),
            json_schema=_SKELETON_RESPONSE_SCHEMA,
        )
    except ProviderError as exc:
        pytest.fail(
            f"PoloAI rejected the sanitized _SKELETON_RESPONSE_SCHEMA — "
            f"the R2.8 regression has reappeared: {exc}"
        )

    assert isinstance(resp, StructuredResponse)
    assert isinstance(resp.content, dict)
    cost = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    print(
        f"\n[smoke] skeleton-schema e2e: model={resp.model_id} "
        f"json_mode={provider.json_mode} in={resp.input_tokens} "
        f"out={resp.output_tokens} finish={resp.finish_reason} "
        f"cost=${cost:.6f}"
    )
