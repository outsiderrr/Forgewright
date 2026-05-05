"""Tests for generator.providers.get_default_provider — R2.7.

Verifies the LLM_PROVIDER selector switches between GeminiProvider and
PoloAIProvider, defaults to gemini when unset, and rejects unknown values.
"""

from __future__ import annotations

import pytest

from generator.providers import (
    GeminiProvider,
    PoloAIProvider,
    get_default_provider,
)


def test_default_is_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    provider = get_default_provider()
    assert isinstance(provider, GeminiProvider)


def test_explicit_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    provider = get_default_provider()
    assert isinstance(provider, GeminiProvider)


def test_explicit_poloai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "poloai")
    monkeypatch.setenv("POLOAI_API_KEY", "sk-dummy")
    monkeypatch.delenv("POLOAI_JSON_MODE", raising=False)
    monkeypatch.delenv("POLOAI_STRICT_SCHEMA", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, PoloAIProvider)


def test_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "PoloAI")
    monkeypatch.setenv("POLOAI_API_KEY", "sk-dummy")
    monkeypatch.delenv("POLOAI_JSON_MODE", raising=False)
    monkeypatch.delenv("POLOAI_STRICT_SCHEMA", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, PoloAIProvider)


def test_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """``.env`` values can pick up trailing whitespace from editors;
    don't punish the user for that."""
    monkeypatch.setenv("LLM_PROVIDER", "  poloai  ")
    monkeypatch.setenv("POLOAI_API_KEY", "sk-dummy")
    monkeypatch.delenv("POLOAI_JSON_MODE", raising=False)
    monkeypatch.delenv("POLOAI_STRICT_SCHEMA", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, PoloAIProvider)


def test_unknown_provider_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Misconfiguration fails fast at startup, not mid-batch."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_default_provider()


def test_provider_construction_errors_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The factory doesn't swallow provider __init__ errors. PoloAIProvider
    raises ProviderError on missing key — the caller sees that, not a
    masked ValueError."""
    from generator.llm_provider import ProviderError

    monkeypatch.setenv("LLM_PROVIDER", "poloai")
    monkeypatch.delenv("POLOAI_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        get_default_provider()
