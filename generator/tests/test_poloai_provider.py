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
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

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


def test_raises_after_max_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R2.10b: 1 initial + 3 retries = 4 total attempts before giving up.
    Replaces R2.7's single-shot retry. baseline_010 iter 9-12 showed 4
    consecutive 500s in a 16-second window — three exponential delays
    (2 + 5 + 10 ≈ 17s) gives us the best shot at jumping the cluster."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise Exception("Server disconnected without sending a response")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 4


def test_exponential_backoff_delay_progression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retry helper must sleep [2.0, 5.0, 10.0] between attempts.
    This guards against silent drift of the policy that's our only line
    of defence against the iter 9-12 500-cluster pattern."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []
    sleep_log: list[float] = []

    def _create(**kwargs):
        call_log.append("call")
        raise Exception("Server disconnected without sending a response")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr(
        "generator.providers._retry.time.sleep", lambda s: sleep_log.append(s)
    )

    with pytest.raises(ProviderError):
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 4
    assert sleep_log == [2.0, 5.0, 10.0]


def _build_synth_status_error(status_code: int, body: str = "") -> Exception:
    """Stand-in for openai.APIStatusError carrying a status_code."""
    from openai import OpenAIError

    class _Synth(OpenAIError):
        def __init__(self) -> None:
            super().__init__(f"synthetic {status_code}")
            self.status_code = status_code
            self.body = body

    return _Synth()


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_retry_on_5xx_server_errors(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """5xx upstream errors trigger backoff retry. baseline_010 iter
    9-12 captured exactly this on HTTP 500 (Database error from upstream
    Gemini relay); 502/503/504 are the symmetric relay-fault shapes."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []
    fake = _fake_openai_response()

    def _create(**kwargs):
        call_log.append("call")
        if len(call_log) < 4:
            raise _build_synth_status_error(status, body="upstream gateway")
        return fake

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 4
    assert resp.content == {"ok": True}


def test_retry_on_api_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """openai.APIConnectionError is an OpenAIError subclass — before R2.10b
    it was caught by ``except OpenAIError`` and never retried, even though
    its semantic ('request never reached upstream') is exactly what backoff
    was designed for. baseline_010 iter 3/8/13 lost cost on this path."""
    from openai import APIConnectionError

    provider = _make_provider(monkeypatch)
    call_log: list[str] = []
    fake = _fake_openai_response()

    def _create(**kwargs):
        call_log.append("call")
        if len(call_log) < 2:
            # APIConnectionError requires a `request` kwarg; pass minimal mock
            raise APIConnectionError(request=SimpleNamespace())  # type: ignore[arg-type]
        return fake

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2
    assert resp.content == {"ok": True}


def test_retry_on_api_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """APITimeoutError is APIConnectionError subclass — same retry path."""
    from openai import APITimeoutError

    provider = _make_provider(monkeypatch)
    call_log: list[str] = []
    fake = _fake_openai_response()

    def _create(**kwargs):
        call_log.append("call")
        if len(call_log) < 2:
            raise APITimeoutError(request=SimpleNamespace())  # type: ignore[arg-type]
        return fake

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

    resp = provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 2


def test_no_retry_on_400_bad_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """4xx is the sanitizer-gap signal — retrying just burns cost on the
    same broken payload. The R2.9 metadata excerpt already gives a finder
    enough to root-cause from a single attempt."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise _build_synth_status_error(400, body='{"error": "Invalid schema"}')

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1
    assert exc_info.value.metadata_dict()["http_status"] == 400


def test_no_retry_on_429_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 = upstream is shedding load. Exponential backoff in-process
    doesn't fix that; the operator needs to widen the limit or back off
    at the batch layer. baseline_009 also showed PoloAI's relay can wrap
    a 429 in an HTTP 400 envelope — that path also stays non-retry
    because R2.9 body excerpts already disambiguate the real cause."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise _build_synth_status_error(429, body='{"error": "rate limit exceeded"}')

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1
    assert exc_info.value.metadata_dict()["http_status"] == 429


def test_no_retry_on_401_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise _build_synth_status_error(401, body='{"error": "invalid api key"}')

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1
    assert exc_info.value.metadata_dict()["http_status"] == 401


def test_max_retries_exhausted_carries_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When all 4 attempts hit the same 500, the final ProviderError must
    still carry R2.9 metadata so a baseline finder sees the upstream
    failure surface, not a generic 'retry exhausted' fog."""
    provider = _make_provider(monkeypatch)
    call_log: list[str] = []

    def _create(**kwargs):
        call_log.append("call")
        raise _build_synth_status_error(
            500, body='{"message": "Database error, please contact"}'
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
    )
    provider._client_cache = fake_client  # type: ignore[assignment]
    monkeypatch.setattr("generator.providers._retry.time.sleep", lambda _s: None)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 4
    md = exc_info.value.metadata_dict()
    assert md["http_status"] == 500
    assert "Database error" in (md["response_body_excerpt"] or "")


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

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    assert len(call_log) == 1
    # R2.9: even bare OpenAIError (no .status_code) carries an exception
    # class through the metadata_dict — that alone disambiguates an SDK
    # error from a transient httpx failure.
    md = exc_info.value.metadata_dict()
    assert md["exception_class"] == "openai.OpenAIError"
    assert md["http_status"] is None


def test_openai_status_error_metadata_flows_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic ``.status_code`` + ``.body``-shaped error stands in for
    openai.APIStatusError / RateLimitError. The wrapped ProviderError
    must surface both fields so a baseline finder can read them off
    scene_results.jsonl without a live retry."""
    from openai import OpenAIError

    class _SynthStatusError(OpenAIError):
        def __init__(self) -> None:
            super().__init__("rate-limited by upstream")
            self.status_code = 429
            self.body = '{"error": {"message": "rate limit exceeded"}}'

    provider = _make_provider(monkeypatch)
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_: (_ for _ in ()).throw(_SynthStatusError()))
        )
    )
    provider._client_cache = fake_client  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc_info:
        provider.generate_structured("sys", "user", {"type": "object"})
    md = exc_info.value.metadata_dict()
    assert md["http_status"] == 429
    assert md["exception_class"].endswith("._SynthStatusError")
    assert "rate limit" in (md["response_body_excerpt"] or "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_sanitize_strips_unsupported_keywords_recursively() -> None:
    """R2.8: ``additionalProperties`` is now stripped to match Gemini's
    rule set. PoloAI relays to Gemini upstream where protobuf rejects
    the keyword (baseline_006, PR #22) — the OpenAI-strict-mode benefit
    R2.7 tried to preserve never reached the wire in practice."""
    original = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "node.schema.json",
        "type": "object",
        "additionalProperties": False,
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
    assert "additionalProperties" not in sanitized
    # Recursive
    assert "$id" not in sanitized["properties"]["items"]["items"]
    # Original not mutated
    assert "$schema" in original
    assert original["additionalProperties"] is False


def test_sanitize_rewrites_type_array_nullable_for_poloai() -> None:
    """R2.8 regression guard: PoloAI's sanitizer must rewrite the
    JSON-Schema type-array nullable form. R2.7 shipped without this rule
    and baseline_006 caught the resulting upstream-protobuf rejection
    at 0% gross_pass_rate."""
    schema = {
        "type": "object",
        "properties": {
            "speaker_ref": {"type": ["string", "null"]},
            "extras": {
                "type": "array",
                "items": {"type": ["integer", "null"], "minimum": 0},
            },
        },
    }
    sanitized = _sanitize_schema_for_openai(schema)
    assert sanitized["properties"]["speaker_ref"] == {
        "type": "string",
        "nullable": True,
    }
    assert sanitized["properties"]["extras"]["items"] == {
        "type": "integer",
        "nullable": True,
        "minimum": 0,
    }


def test_sanitize_skeleton_schema_via_poloai_has_no_list_type_residue() -> None:
    """End-to-end check that the live ``_SKELETON_RESPONSE_SCHEMA`` —
    the one that triggered the baseline_006 0% pass rate — survives the
    PoloAI sanitizer cleanly. No real API call: pure schema transform."""
    from generator.scene_strategies import _SKELETON_RESPONSE_SCHEMA

    sanitized = _sanitize_schema_for_openai(_SKELETON_RESPONSE_SCHEMA)

    def _walk_types(node):
        if isinstance(node, dict):
            if "type" in node:
                yield node["type"]
            for v in node.values():
                yield from _walk_types(v)
        elif isinstance(node, list):
            for item in node:
                yield from _walk_types(item)

    for t in _walk_types(sanitized):
        assert not isinstance(t, list), f"list-form type leaked through: {t!r}"


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


def test_generate_structured_always_sends_max_tokens(monkeypatch):
    """R3.4（2026-07-08）：中转站 gpt-5.5 不带 max_tokens 返回空 content——必须显式携带。"""
    provider = PoloAIProvider(api_key="k", json_mode="prompt_only")
    seen = {}

    class _Msg:
        content = '{"ok": true}'

    class _Choice:
        message = _Msg()
        finish_reason = "stop"

    class _Resp:
        choices = [_Choice()]
        usage = None

    def fake_call(*, kwargs):
        seen.update(kwargs)
        return _Resp()

    monkeypatch.setattr(provider, "_call_with_transient_retry", fake_call)
    provider.generate_structured("s", "u", {"type": "object"})
    assert seen["max_tokens"] == 8000  # 默认值


def test_max_output_tokens_env_override(monkeypatch):
    monkeypatch.setenv("POLOAI_MAX_OUTPUT_TOKENS", "12345")
    provider = PoloAIProvider(api_key="k")
    assert provider.max_output_tokens == 12345
