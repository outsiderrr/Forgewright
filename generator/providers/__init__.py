"""Concrete LLM/Image provider implementations + the text-LLM factory.

Per ADR-011: vendor SDK imports (``google.genai``, ``openai``) live only
inside this package. Business code calls :func:`get_default_provider` (or
constructs a specific provider directly) and never imports an SDK.
"""

from __future__ import annotations

import os

from generator.llm_provider import LLMProvider
from generator.providers.gemini import GeminiProvider
from generator.providers.manual_import import ManualImportProvider
from generator.providers.openai_image import OpenAIImageProvider
from generator.providers.poloai import PoloAIProvider

__all__ = [
    "GeminiProvider",
    "ManualImportProvider",
    "OpenAIImageProvider",
    "PoloAIProvider",
    "get_default_provider",
]

DEFAULT_PROVIDER_NAME = "gemini"

_TEXT_PROVIDERS: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "poloai": PoloAIProvider,
}


def get_default_provider() -> LLMProvider:
    """Construct the text-LLM provider selected by ``LLM_PROVIDER``.

    Defaults to ``gemini`` when the env var is unset. Raises ``ValueError``
    on an unknown name so misconfiguration fails fast at startup rather
    than mid-batch. Per-provider env vars (``GEMINI_API_KEY``,
    ``POLOAI_API_KEY``, etc.) are validated by the provider's own
    constructor (``ProviderError`` on missing key)."""
    name = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER_NAME).strip().lower()
    cls = _TEXT_PROVIDERS.get(name)
    if cls is None:
        known = ", ".join(sorted(_TEXT_PROVIDERS))
        raise ValueError(
            f"Unknown LLM_PROVIDER: {name!r} (expected one of: {known})"
        )
    return cls()
