"""Contract tests for the LLMProvider Protocol — no real API calls.

Verifies:
1. A hand-rolled FakeProvider passes `isinstance(..., LLMProvider)` (Protocol
   is `runtime_checkable`).
2. GeminiProvider satisfies the same structural check.
3. StructuredResponse exposes the documented fields.
"""

from __future__ import annotations

import os

import pytest

from types import SimpleNamespace

from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.providers import GeminiProvider
from generator.providers.gemini import (
    _is_transient_network_error,
    _sanitize_schema_for_gemini,
)


def _fake_gemini_response(text: str = '{"ok": true}') -> SimpleNamespace:
    """Minimal stand-in for genai_types.GenerateContentResponse."""
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5),
        candidates=[
            SimpleNamespace(
                finish_reason=SimpleNamespace(name="STOP"),
                content=None,
            )
        ],
    )


class FakeProvider:
    """In-memory stand-in for tests. Returns a fixed StructuredResponse."""

    model_id = "fake-model-1"

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse:
        return StructuredResponse(
            content={"echo": user_prompt},
            raw_text='{"echo": "..."}',
            input_tokens=len(system_prompt) + len(user_prompt),
            output_tokens=10,
            model_id=self.model_id,
            finish_reason="STOP",
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens + output_tokens) * 1e-6


def test_fake_provider_satisfies_protocol() -> None:
    fake = FakeProvider()
    assert isinstance(fake, LLMProvider)


def test_fake_provider_returns_well_formed_response() -> None:
    fake = FakeProvider()
    resp = fake.generate_structured("sys", "hello", {"type": "object"})
    assert isinstance(resp, StructuredResponse)
    assert resp.content == {"echo": "hello"}
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.model_id == "fake-model-1"
    assert resp.finish_reason == "STOP"


def test_fake_provider_estimate_cost_is_float() -> None:
    fake = FakeProvider()
    cost = fake.estimate_cost(1000, 2000)
    assert isinstance(cost, float)
    assert cost > 0


def test_gemini_provider_satisfies_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    """GeminiProvider must structurally match the Protocol regardless of env."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider()
    assert isinstance(provider, LLMProvider)


def test_gemini_provider_estimate_cost_known_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pricing constants are fixed; verify the arithmetic doesn't drift."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider()
    # 1M input + 1M output @ 2.00 + 12.00 USD per Mtok = 14.00 USD
    assert provider.estimate_cost(1_000_000, 1_000_000) == pytest.approx(14.00)
    assert provider.estimate_cost(0, 0) == 0.0


def test_gemini_provider_raises_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        GeminiProvider()


def test_gemini_provider_accepts_explicit_model_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider(model_id="gemini-3.1-flash-preview")
    assert provider.model_id == "gemini-3.1-flash-preview"


def test_is_transient_network_error_recognises_known_patterns() -> None:
    assert _is_transient_network_error(
        Exception("Server disconnected without sending a response")
    )
    assert _is_transient_network_error(Exception("[Errno 54] Connection reset by peer"))
    assert _is_transient_network_error(Exception("ReadTimeout: timed out"))
    assert _is_transient_network_error(Exception("ConnectError: peer refused"))
    # Negative cases — stays False so non-network bugs don't get silently retried.
    assert not _is_transient_network_error(ValueError("invalid input"))
    assert not _is_transient_network_error(Exception("unrelated server bug"))


def test_gemini_retries_once_on_transient_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider()

    # Fake client: first call raises transient, second call returns success.
    call_log: list[str] = []
    fake_response = _fake_gemini_response()

    def fake_generate_content(**kwargs):
        call_log.append("call")
        if len(call_log) == 1:
            raise Exception("Server disconnected without sending a response")
        return fake_response

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers.gemini.time.sleep", lambda _s: None)

    response = provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2
    assert response.content == {"ok": True}


def test_gemini_does_not_retry_non_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider()

    call_log: list[str] = []

    def fake_generate_content(**kwargs):
        call_log.append("call")
        raise ValueError("invalid input that is not a network issue")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1  # No retry for non-transient
    # R2.9: the raised ProviderError must carry diagnostic metadata so
    # the upstream catch site can populate failure_metadata.
    md = exc_info.value.metadata_dict()
    assert md["exception_class"] == "ValueError"
    assert md["http_status"] is None


def test_gemini_raises_after_two_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-instantiation")
    provider = GeminiProvider()

    call_log: list[str] = []

    def fake_generate_content(**kwargs):
        call_log.append("call")
        raise Exception("Server disconnected without sending a response")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers.gemini.time.sleep", lambda _s: None)

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2  # 1 initial + 1 retry, then give up


# ---------------------------------------------------------------------------
# ProviderError diagnostic metadata (R2.9 — baseline_007 finding b3c0ca3)
# ---------------------------------------------------------------------------
#
# These cover the three failure surfaces baseline_007 conflated under a single
# `provider_error` reason: SDK-classified status errors (sanitizer-gap shape),
# httpx-style timeouts (relay-truncation shape), and bare exceptions
# (programming-bug fallback). The point is one jsonl row per failure should
# tell a finder which surface fired without a live retry.


class _FakeStatusError(Exception):
    """Stand-in for openai.APIStatusError / genai.errors.ClientError —
    both expose ``.status_code`` plus a body attribute."""

    def __init__(self, message: str, *, status_code: int, body: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class _FakeTimeoutError(Exception):
    """Stand-in for httpx.TimeoutError / openai.APITimeoutError — no
    HTTP status is exposed because the request never got a response."""


def test_provider_error_from_exception_captures_status_error_metadata() -> None:
    exc = _FakeStatusError(
        "Bad Request: schema additionalProperties not supported",
        status_code=400,
        body='{"error": "Invalid JSON payload received. Unknown name \\"additionalProperties\\""}',
    )
    err = ProviderError.from_exception(exc, message="Gemini API error")
    md = err.metadata_dict()
    assert md["http_status"] == 400
    assert md["exception_class"].endswith("._FakeStatusError")
    assert "additionalProperties" in (md["response_body_excerpt"] or "")
    # __str__ must stay the original message — existing assertions about
    # the wrapped error text rely on this.
    assert str(err) == "Gemini API error"


def test_provider_error_from_exception_captures_timeout_metadata() -> None:
    exc = _FakeTimeoutError("Read timeout: 120s exceeded")
    err = ProviderError.from_exception(exc, message="Gemini call failed")
    md = err.metadata_dict()
    # Timeout → no HTTP status (request never completed).
    assert md["http_status"] is None
    assert md["exception_class"].endswith("._FakeTimeoutError")
    # `.message` attribute fallback supplies the body excerpt for the
    # generic SDK shape.
    assert md["response_body_excerpt"] is None or isinstance(
        md["response_body_excerpt"], str
    )


def test_provider_error_from_exception_handles_plain_exception() -> None:
    err = ProviderError.from_exception(
        ValueError("totally generic"), message="Gemini call failed"
    )
    md = err.metadata_dict()
    assert md["exception_class"] == "ValueError"
    assert md["http_status"] is None


def test_provider_error_from_exception_extracts_nested_response_status() -> None:
    """openai's older APIStatusError shape: status_code lives on
    `.response.status_code` rather than the exception itself."""

    class _Resp:
        status_code = 504
        text = "upstream gateway timed out"

    class _NestedErr(Exception):
        response = _Resp()

    err = ProviderError.from_exception(_NestedErr("relay 504"), message="x")
    md = err.metadata_dict()
    assert md["http_status"] == 504
    assert "upstream" in (md["response_body_excerpt"] or "")


def test_provider_error_from_exception_redacts_credentials_in_body() -> None:
    """Defense in depth: even though SDK error bodies don't normally
    include API keys, we mask anything that looks like one before it
    lands in the jsonl. Single regex; no false-negative cost worth
    skipping it for."""
    exc = _FakeStatusError(
        "auth error",
        status_code=401,
        body='{"detail": "missing api_key=sk-secretvalue123 for Bearer xyz789"}',
    )
    md = ProviderError.from_exception(exc, message="auth").metadata_dict()
    body = md["response_body_excerpt"] or ""
    assert "sk-secretvalue123" not in body
    assert "xyz789" not in body
    assert "<redacted>" in body


def test_provider_error_from_exception_truncates_long_body() -> None:
    long_body = "X" * 5000
    exc = _FakeStatusError("big body", status_code=500, body=long_body)
    md = ProviderError.from_exception(exc, message="x").metadata_dict()
    excerpt = md["response_body_excerpt"]
    assert excerpt is not None
    # Cap is 500 chars + one ellipsis separator.
    assert len(excerpt) <= 501
    assert "…" in excerpt


def test_provider_error_backward_compat_no_metadata() -> None:
    """``raise ProviderError("msg")`` (no kwargs) must keep working —
    every existing test asserting `pytest.raises(ProviderError)` and
    `str(exc)` formatting depends on it."""
    err = ProviderError("nothing fancy")
    assert err.exception_class is None
    assert err.http_status is None
    assert err.response_body_excerpt is None
    assert err.metadata_dict() == {
        "exception_class": None,
        "http_status": None,
        "response_body_excerpt": None,
    }
    assert str(err) == "nothing fancy"


def test_provider_error_metadata_dict_is_json_serialisable() -> None:
    """The dict has to land in scene_results.jsonl unchanged — None /
    int / str only, no exception objects leaking through."""
    import json as _json

    err = ProviderError.from_exception(
        _FakeStatusError("x", status_code=429, body="rate limit"),
        message="poloai 429",
    )
    payload = _json.dumps(err.metadata_dict())
    assert '"http_status": 429' in payload
    assert "rate limit" in payload


def test_sanitize_strips_unsupported_keywords_recursively() -> None:
    original = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "node.schema.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"id": {"type": "string"}},
                },
            },
            "metadata": {
                "type": "object",
                "$id": "nested",
                "properties": {"k": {"type": "string"}},
            },
        },
    }
    sanitized = _sanitize_schema_for_gemini(original)

    # Top-level unsupported keys are gone.
    assert "additionalProperties" not in sanitized
    assert "$schema" not in sanitized
    assert "$id" not in sanitized

    # Nested ones are gone too.
    assert "additionalProperties" not in sanitized["properties"]["options"]["items"]
    assert "$id" not in sanitized["properties"]["metadata"]

    # Supported keys survive.
    assert sanitized["type"] == "object"
    assert sanitized["properties"]["options"]["items"]["properties"]["id"]["type"] == "string"

    # Original is not mutated.
    assert original["additionalProperties"] is False
    assert "$schema" in original
