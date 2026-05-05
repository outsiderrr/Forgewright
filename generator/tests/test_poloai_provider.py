"""Unit tests for generator.providers.poloai.PoloAIProvider — R2.7.

No real API calls. The OpenAI client is monkeypatched at the
``chat.completions.create`` level so we exercise:
  - response decoding (content / usage / finish_reason mapping)
  - response_format injection per json_mode (json_schema / json_object /
    prompt_only)
  - system-prompt schema augmentation (defense-in-depth for non-strict
    modes)
  - codefence stripping
  - api_key / unknown-mode validation
  - transient-error retry mirroring GeminiProvider
  - estimate_cost arithmetic
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.providers.poloai import (
    DEFAULT_MODEL_ID,
    PoloAIProvider,
    _is_transient_network_error,
    _sanitize_schema_for_openai,
    _strip_json_codefence,
)


def _fake_openai_response(
    content: str = '{"ok": true}',
    prompt_tokens: int = 12,
    completion_tokens: int = 7,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    """Stand-in for openai.types.chat.ChatCompletion."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


class _RecordingClient:
    """Captures the kwargs handed to chat.completions.create and returns
    a pre-set response (or raises a pre-set exception)."""

    def __init__(
        self, response: SimpleNamespace | None = None, exc: Exception | None = None
    ) -> None:
        self.response = response
        self.exc = exc
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return self.response


def _make_provider(monkeypatch: pytest.MonkeyPatch, **kwargs) -> PoloAIProvider:
    monkeypatch.setenv("POLOAI_API_KEY", "sk-test-dummy")
    # Ensure env-var leakage from a real .env doesn't perturb tests.
    monkeypatch.delenv("POLOAI_JSON_MODE", raising=False)
    monkeypatch.delenv("POLOAI_STRICT_SCHEMA", raising=False)
    monkeypatch.delenv("POLOAI_MODEL_ID", raising=False)
    monkeypatch.delenv("POLOAI_BASE_URL", raising=False)
    return PoloAIProvider(**kwargs)


# ---------------------------------------------------------------------------
# Construction / config
# ---------------------------------------------------------------------------


def test_satisfies_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(monkeypatch)
    assert isinstance(provider, LLMProvider)


def test_raises_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLOAI_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        PoloAIProvider()


def test_default_model_and_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(monkeypatch)
    assert provider.model_id == DEFAULT_MODEL_ID
    assert provider._base_url == "https://poloai.top/v1"
    assert provider.json_mode == "json_schema"
    assert provider.strict_schema is False


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLOAI_API_KEY", "sk-test")
    monkeypatch.setenv("POLOAI_MODEL_ID", "custom-model-id")
    monkeypatch.setenv("POLOAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("POLOAI_JSON_MODE", "json_object")
    monkeypatch.setenv("POLOAI_STRICT_SCHEMA", "true")
    provider = PoloAIProvider()
    assert provider.model_id == "custom-model-id"
    assert provider._base_url == "https://example.test/v1"
    assert provider.json_mode == "json_object"
    assert provider.strict_schema is True


def test_constructor_args_beat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLOAI_API_KEY", "sk-test")
    monkeypatch.setenv("POLOAI_JSON_MODE", "json_object")
    provider = PoloAIProvider(json_mode="prompt_only", strict_schema=True)
    assert provider.json_mode == "prompt_only"
    assert provider.strict_schema is True


def test_unknown_json_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLOAI_API_KEY", "sk-test")
    with pytest.raises(ProviderError):
        PoloAIProvider(json_mode="bogus")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


def test_estimate_cost_known_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pricing constants are fixed; verify the arithmetic doesn't drift."""
    provider = _make_provider(monkeypatch)
    # 1M input + 1M output @ 2.00 + 12.00 USD per Mtok = 14.00 USD
    assert provider.estimate_cost(1_000_000, 1_000_000) == pytest.approx(14.00)
    assert provider.estimate_cost(0, 0) == 0.0


# ---------------------------------------------------------------------------
# generate_structured: response decoding
# ---------------------------------------------------------------------------


def test_generate_structured_decodes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    fake = _fake_openai_response(
        content='{"a": 1, "b": "two"}',
        prompt_tokens=33,
        completion_tokens=7,
        finish_reason="stop",
    )
    client = _RecordingClient(response=fake)
    provider._client_cache = client  # type: ignore[assignment]

    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert isinstance(resp, StructuredResponse)
    assert resp.content == {"a": 1, "b": "two"}
    assert resp.input_tokens == 33
    assert resp.output_tokens == 7
    assert resp.model_id == DEFAULT_MODEL_ID
    assert resp.finish_reason == "stop"
    assert resp.raw_text == '{"a": 1, "b": "two"}'


def test_generate_structured_strips_json_codefence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    fenced = '```json\n{"x": 1}\n```'
    client = _RecordingClient(response=_fake_openai_response(content=fenced))
    provider._client_cache = client  # type: ignore[assignment]
    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert resp.content == {"x": 1}


def test_generate_structured_raises_on_empty_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    client = _RecordingClient(response=_fake_openai_response(content=""))
    provider._client_cache = client  # type: ignore[assignment]
    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})


def test_generate_structured_raises_on_non_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    client = _RecordingClient(response=_fake_openai_response(content="not json at all"))
    provider._client_cache = client  # type: ignore[assignment]
    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})


def test_generate_structured_rejects_non_object_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller contract demands ``content: dict``; arrays / scalars are
    a contract violation regardless of relay-side flexibility."""
    provider = _make_provider(monkeypatch)
    client = _RecordingClient(response=_fake_openai_response(content="[1, 2, 3]"))
    provider._client_cache = client  # type: ignore[assignment]
    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})


# ---------------------------------------------------------------------------
# generate_structured: response_format / system-prompt injection per mode
# ---------------------------------------------------------------------------


def test_json_schema_mode_injects_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch, json_mode="json_schema")
    client = _RecordingClient(response=_fake_openai_response())
    provider._client_cache = client  # type: ignore[assignment]
    schema = {"type": "object", "$schema": "ignored", "properties": {"k": {"type": "string"}}}
    provider.generate_structured("sys-prompt", "user-prompt", schema)

    call = client.calls[0]
    assert call["model"] == DEFAULT_MODEL_ID
    rf = call["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "structured_output"
    assert rf["json_schema"]["strict"] is False
    # Sanitized: $schema dropped.
    assert "$schema" not in rf["json_schema"]["schema"]
    assert rf["json_schema"]["schema"]["type"] == "object"
    # System prompt unchanged in json_schema mode.
    assert call["messages"][0] == {"role": "system", "content": "sys-prompt"}
    assert call["messages"][1] == {"role": "user", "content": "user-prompt"}


def test_json_schema_mode_strict_flag_passes_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(
        monkeypatch, json_mode="json_schema", strict_schema=True
    )
    client = _RecordingClient(response=_fake_openai_response())
    provider._client_cache = client  # type: ignore[assignment]
    provider.generate_structured("sys", "user", {"type": "object"})
    assert client.calls[0]["response_format"]["json_schema"]["strict"] is True


def test_json_object_mode_uses_object_response_format_and_embeds_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch, json_mode="json_object")
    client = _RecordingClient(response=_fake_openai_response())
    provider._client_cache = client  # type: ignore[assignment]
    schema = {"type": "object", "properties": {"k": {"type": "string"}}}
    provider.generate_structured("sys-prompt", "user-prompt", schema)

    call = client.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    sys_msg = call["messages"][0]
    assert sys_msg["role"] == "system"
    # Original system prompt preserved.
    assert sys_msg["content"].startswith("sys-prompt")
    # Schema text embedded as defense-in-depth.
    assert "JSON Schema" in sys_msg["content"]
    assert json.dumps(schema, ensure_ascii=False) in sys_msg["content"]


def test_prompt_only_mode_omits_response_format_and_embeds_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch, json_mode="prompt_only")
    client = _RecordingClient(response=_fake_openai_response())
    provider._client_cache = client  # type: ignore[assignment]
    schema = {"type": "object", "properties": {"k": {"type": "string"}}}
    provider.generate_structured("sys-prompt", "user-prompt", schema)

    call = client.calls[0]
    assert "response_format" not in call
    sys_content = call["messages"][0]["content"]
    assert sys_content.startswith("sys-prompt")
    assert "JSON Schema" in sys_content
    assert json.dumps(schema, ensure_ascii=False) in sys_content


def test_empty_system_prompt_no_role_when_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If system_prompt is empty in json_schema mode, no system message
    is emitted (the relay handles JSON contract via response_format)."""
    provider = _make_provider(monkeypatch, json_mode="json_schema")
    client = _RecordingClient(response=_fake_openai_response())
    provider._client_cache = client  # type: ignore[assignment]
    provider.generate_structured("", "user-prompt", {"type": "object"})
    msgs = client.calls[0]["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Transient retry
# ---------------------------------------------------------------------------


def test_is_transient_network_error_recognises_known_patterns() -> None:
    assert _is_transient_network_error(
        Exception("Server disconnected without sending a response")
    )
    assert _is_transient_network_error(
        Exception("[Errno 54] Connection reset by peer")
    )
    assert _is_transient_network_error(Exception("ReadTimeout: timed out"))
    # Negative cases — non-network bugs do NOT get silently retried.
    assert not _is_transient_network_error(ValueError("invalid input"))
    assert not _is_transient_network_error(Exception("unrelated server bug"))


def test_retries_once_on_transient_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    fake = _fake_openai_response()
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        if len(call_log) == 1:
            raise Exception("Server disconnected without sending a response")
        return fake

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers.poloai.time.sleep", lambda _s: None)

    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2
    assert resp.content == {"ok": True}


def test_does_not_retry_non_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise ValueError("invalid input that is not a network issue")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1


def test_raises_after_two_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise Exception("Server disconnected without sending a response")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers.poloai.time.sleep", lambda _s: None)

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2


def test_openai_error_wraps_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK-classified errors (auth, 4xx/5xx) wrap to ProviderError without
    retry. Mirrors GeminiProvider's stance — caller decides recovery."""
    from openai import OpenAIError

    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise OpenAIError("synthetic SDK error")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_sanitize_strips_unsupported_keywords_recursively() -> None:
    original = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "node.schema.json",
        "type": "object",
        "additionalProperties": False,  # KEPT — OpenAI strict mode wants it
        "properties": {
            "items": {
                "type": "array",
                "items": {"$id": "nested", "type": "object"},
            }
        },
    }
    sanitized = _sanitize_schema_for_openai(original)
    assert "$schema" not in sanitized
    assert "$id" not in sanitized
    # additionalProperties kept (unlike Gemini's sanitizer)
    assert sanitized["additionalProperties"] is False
    # Recursive
    assert "$id" not in sanitized["properties"]["items"]["items"]
    # Original not mutated
    assert "$schema" in original


def test_strip_codefence_handles_plain_json() -> None:
    assert _strip_json_codefence('{"x": 1}') == '{"x": 1}'


def test_strip_codefence_handles_json_fence() -> None:
    assert _strip_json_codefence('```json\n{"x": 1}\n```') == '{"x": 1}'


def test_strip_codefence_handles_bare_fence() -> None:
    assert _strip_json_codefence('```\n{"x": 1}\n```') == '{"x": 1}'


def test_strip_codefence_leaves_non_fenced_with_prose_alone() -> None:
    """If the content isn't *exactly* one fenced block, leave it alone so
    json.loads surfaces the real error rather than us silently mangling."""
    text = 'prefix\n```json\n{"x": 1}\n```\nsuffix'
    assert _strip_json_codefence(text) == text
