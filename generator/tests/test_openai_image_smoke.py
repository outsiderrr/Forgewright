"""Smoke test: one real OpenAI image call. Costs ≤ $0.20.

Skipped by default (see conftest.py). Run with:
    pytest -m smoke generator/tests/test_openai_image_smoke.py -s

Per T-1.5.9: GPT-Image-1's smallest supported size is 1024×1024 (256×256 is
dall-e-2 only). We pin `quality` low via the cheapest supported size and
trust OpenAI's pricing — the conservative `estimate_cost` upper bound is
$0.17, which is below the $0.20 cap from the task spec.
"""

from __future__ import annotations

import os

import pytest

from generator.image_provider import ImageGenerationResult
from generator.providers import OpenAIImageProvider

pytestmark = pytest.mark.smoke


def test_openai_image_minimal_call() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    provider = OpenAIImageProvider()
    result = provider.generate(
        prompt=(
            "A simple character sheet illustration: a single neutral-pose "
            "humanoid figure on a transparent background, painterly style. "
            "Test image for smoke verification — minimum complexity."
        ),
        asset_kind="character_sheet",
        target_ref="char_smoke_test",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_smoke_test_neutral",
        size=(1024, 1024),
    )

    assert isinstance(result, ImageGenerationResult)
    assert result.mode == "api"
    assert result.image_bytes is not None and len(result.image_bytes) > 0
    assert result.cost_usd > 0
    assert result.raw_metadata["model_id"] == "gpt-image-1"
    assert result.raw_metadata["target_ref"] == "char_smoke_test"
    # OpenAI returns a populated response dict; verify the SDK round-tripped.
    assert "openai_response" in result.raw_metadata

    print(
        f"\n[smoke] model={result.raw_metadata['model_id']} "
        f"size={result.raw_metadata['size_requested']} "
        f"bytes={len(result.image_bytes)} "
        f"cost=${result.cost_usd:.4f}"
    )
