"""PoloAI implementation of LLMProvider — R2.7.

Third-party OpenAI-compatible relay (https://poloai.top) backing onto
Gemini 3.1 Pro. Same Protocol contract as GeminiProvider; switchable via
the ``LLM_PROVIDER`` env var (see ``generator.providers.get_default_provider``).

Per ADR-011: this module is the only place in the repo that imports the
``openai`` SDK for chat completions. (``providers/openai_image.py`` also
imports ``openai`` but only for the ``images.generate`` path; that's a
separate Protocol — ``ImageProvider`` — and not affected by R2.7.)

Empirical probing (2026-05-05, see PR R2.7 description):
  - Auth: ``Authorization: Bearer sk-...`` confirmed.
  - Model literal: ``gemini-3.1-pro-preview`` confirmed via GET /v1/models.
  - JSON-mode contract (json_schema vs json_object vs prompt_only):
    NOT empirically verified. The probing token's distributor group had
    no channel binding so chat/completions returned ``model_not_found``
    for every listed model. The implementation defaults to
    ``json_mode='json_schema'`` (``strict=False``) on the assumption that
    the relay mirrors the OpenAI standard. Author can override at
    construction or via ``POLOAI_JSON_MODE`` env var. The schema is
    additionally embedded into the system prompt for ``json_object`` /
    ``prompt_only`` modes as defense-in-depth (in case the relay silently
    drops the ``response_format`` field).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from openai import APIConnectionError, APITimeoutError, OpenAI, OpenAIError

from generator.llm_provider import ProviderError, StructuredResponse, _extract_http_status
from generator.providers._retry import (
    _RETRYABLE_HTTP_STATUSES,
    retry_on_transient,
)
from generator.providers._schema_sanitizer import sanitize_schema_for_openapi

DEFAULT_MODEL_ID = "gemini-3.1-pro-preview"
DEFAULT_BASE_URL = "https://poloai.top/v1"

JsonMode = Literal["json_schema", "json_object", "prompt_only"]
DEFAULT_JSON_MODE: JsonMode = "json_schema"

# OpenAI SDK accepts seconds (float) for timeout, unlike google.genai which
# wants milliseconds. 120s mirrors GeminiProvider for parity on long prompts.
_HTTP_TIMEOUT_SEC = 120.0

# Fallback substring match for raw httpx-level exceptions that escape the
# OpenAI SDK's wrapping (proxy hiccups, mid-flight resets, TLS handshake
# stutters). The structured paths below — APIConnectionError /
# APITimeoutError / 5xx APIStatusError — cover the bulk of baseline_010's
# upstream-fault surface; this list is the safety net for anything that
# bypasses the SDK error hierarchy entirely.
_TRANSIENT_ERROR_SUBSTRINGS = (
    "Server disconnected",
    "Connection reset",
    "Read timeout",
    "ReadTimeout",
    "ConnectError",
    "ConnectTimeout",
    "RemoteProtocolError",
    "handshake",
    "timed out",
)

# Best-effort cost estimate. The relay backs onto Gemini 3.1 Pro per docs;
# we reuse Gemini's public per-MTok rate as a floor. Relay markup over
# official pricing is not modeled here — treat estimate_cost as a lower
# bound, not an authoritative invoice. Refine in a follow-up PR if/when
# poloai publishes per-call pricing.
_INPUT_USD_PER_MTOK = 2.00
_OUTPUT_USD_PER_MTOK = 12.00

# R3.4（2026-07-08 实测）：key77qiqi 中转站的 gpt-5.5 若请求不带 max_tokens，
# 会返回 content=None（completion token 烧在 reasoning 上不透出正文）——
# 必须显式给输出上限。env `POLOAI_MAX_OUTPUT_TOKENS` 可调，默认 8000
# （engine 结构 call 估算上限 2000 的 4 倍余量；这是 cap 不是 target，不增成本）。
_DEFAULT_MAX_OUTPUT_TOKENS = 8000


class PoloAIProvider:
    """OpenAI-compatible chat completions against poloai.top.

    Backend: Gemini 3.1 Pro (per relay docs). Constructor reads env vars
    when arguments are omitted:
      - ``POLOAI_API_KEY`` (required, no default)
      - ``POLOAI_MODEL_ID`` (default: ``gemini-3.1-pro-preview``)
      - ``POLOAI_BASE_URL`` (default: ``https://poloai.top/v1``)
      - ``POLOAI_JSON_MODE`` (default: ``json_schema``;
        accepts ``json_schema`` | ``json_object`` | ``prompt_only``)
      - ``POLOAI_STRICT_SCHEMA`` (default: ``false``; only consulted in
        ``json_schema`` mode)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        json_mode: JsonMode | None = None,
        strict_schema: bool | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("POLOAI_API_KEY")
        if not key:
            raise ProviderError(
                "POLOAI_API_KEY is not set; pass api_key= or set the env var."
            )
        self.model_id = (
            model_id
            if model_id is not None
            else os.environ.get("POLOAI_MODEL_ID", DEFAULT_MODEL_ID)
        )
        self._base_url = (
            base_url
            if base_url is not None
            else os.environ.get("POLOAI_BASE_URL", DEFAULT_BASE_URL)
        )
        resolved_mode = (
            json_mode
            if json_mode is not None
            else os.environ.get("POLOAI_JSON_MODE", DEFAULT_JSON_MODE)
        )
        if resolved_mode not in ("json_schema", "json_object", "prompt_only"):
            raise ProviderError(
                f"Unknown POLOAI_JSON_MODE: {resolved_mode!r} "
                "(expected json_schema | json_object | prompt_only)"
            )
        self.json_mode: JsonMode = resolved_mode  # type: ignore[assignment]
        if strict_schema is None:
            env_strict = os.environ.get("POLOAI_STRICT_SCHEMA", "").strip().lower()
            self.strict_schema = env_strict in ("1", "true", "yes")
        else:
            self.strict_schema = strict_schema
        raw_max = os.environ.get("POLOAI_MAX_OUTPUT_TOKENS", "").strip()
        try:
            self.max_output_tokens = (
                int(raw_max) if raw_max else _DEFAULT_MAX_OUTPUT_TOKENS
            )
        except ValueError as exc:
            raise ProviderError(
                f"POLOAI_MAX_OUTPUT_TOKENS 不是整数: {raw_max!r}"
            ) from exc
        self._api_key = key
        self._client_cache: OpenAI | None = None

    @property
    def _client(self) -> OpenAI:
        # Lazy: avoid network setup at construction so tests can build the
        # provider without side effects. Wrap any SDK __init__ failure in
        # ProviderError so callers see a single repo-local exception type
        # (mirrors openai_image.OpenAIImageProvider).
        if self._client_cache is None:
            try:
                self._client_cache = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=_HTTP_TIMEOUT_SEC,
                )
            except Exception as exc:
                raise ProviderError(f"PoloAI client setup failed: {exc}") from exc
        return self._client_cache

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse:
        sanitized_schema = _sanitize_schema_for_openai(json_schema)
        final_system = _augment_system_prompt(
            system_prompt, sanitized_schema, self.json_mode
        )

        messages: list[dict[str, str]] = []
        if final_system:
            messages.append({"role": "system", "content": final_system})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            # R3.4：不带 max_tokens 时中转站 gpt-5.5 返回空 content（见文件头注释）
            "max_tokens": self.max_output_tokens,
        }
        if self.json_mode == "json_schema":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "strict": self.strict_schema,
                    "schema": sanitized_schema,
                },
            }
        elif self.json_mode == "json_object":
            kwargs["response_format"] = {"type": "json_object"}
        # prompt_only: no response_format field.

        response = self._call_with_transient_retry(kwargs=kwargs)

        choices = getattr(response, "choices", None)
        if not choices:
            raise ProviderError("PoloAI returned no choices")
        message = getattr(choices[0], "message", None)
        raw_text = getattr(message, "content", None) if message else None
        if not raw_text:
            raise ProviderError("PoloAI returned empty message content")

        cleaned = _strip_json_codefence(raw_text)
        try:
            content = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"PoloAI returned non-JSON content "
                f"(json_mode={self.json_mode}): {exc}"
            ) from exc
        if not isinstance(content, dict):
            raise ProviderError(
                f"PoloAI structured output is not a JSON object "
                f"(got {type(content).__name__})"
            )

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0

        finish_reason_raw = getattr(choices[0], "finish_reason", None)
        finish_reason = str(finish_reason_raw) if finish_reason_raw else "UNKNOWN"

        return StructuredResponse(
            content=content,
            raw_text=raw_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_id=self.model_id,
            finish_reason=finish_reason,
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Best-effort floor; relay markup not modeled. See module docstring.
        return (
            input_tokens * _INPUT_USD_PER_MTOK
            + output_tokens * _OUTPUT_USD_PER_MTOK
        ) / 1_000_000

    def _call_with_transient_retry(self, *, kwargs: dict[str, Any]) -> Any:
        try:
            return retry_on_transient(
                lambda: self._client.chat.completions.create(**kwargs),
                is_transient=_should_retry,
            )
        except OpenAIError as exc:
            # SDK-classified errors that survived the retry path (either
            # never retryable — 4xx auth / sanitizer-gap / 429 rate-limit
            # — or retryable but exhausted). Wrap with full R2.9 metadata.
            raise ProviderError.from_exception(
                exc, message=f"PoloAI API error: {exc}"
            ) from exc
        except Exception as exc:  # connection-level / unwrapped httpx errors
            raise ProviderError.from_exception(
                exc, message=f"PoloAI call failed: {exc}"
            ) from exc


def _should_retry(exc: BaseException) -> bool:
    """Classify whether an exception from the OpenAI client is worth retrying.

    Retryable surfaces:
      - ``APIConnectionError`` / ``APITimeoutError`` — request never
        reached upstream (no HTTP status). baseline_010 iter 3/8/13.
      - ``APIStatusError`` with status in {500, 502, 503, 504} — upstream
        relay 5xx. baseline_010 iter 9/10/11/12 cluster.
      - Raw httpx-level errors that escape the SDK's wrapping (matched
        by the substring fallback in ``_is_transient_network_error``).

    Non-retryable: 4xx (auth, content-policy, sanitizer-gap), 429
    rate-limit (load-shed by upstream — exponential backoff doesn't
    help), and anything that doesn't fit either bucket.
    """
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, OpenAIError):
        status = _extract_http_status(exc)
        if status is not None and status in _RETRYABLE_HTTP_STATUSES:
            return True
        return False
    return _is_transient_network_error(exc)


def _is_transient_network_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    return any(p in msg for p in _TRANSIENT_ERROR_SUBSTRINGS)


def _sanitize_schema_for_openai(schema: Any) -> Any:
    """Adapt JSON Schema for the relay's ``response_format`` field.

    Thin alias over the shared sanitizer. R2.7 shipped its own narrower
    sanitizer that kept ``additionalProperties`` (in deference to OpenAI
    strict json_schema mode); baseline_006 (PR #22) showed every PoloAI
    request still hits Gemini upstream where protobuf rejects the same
    JSON-Schema features Gemini's response_schema does. R2.8 unifies the
    rule set with :func:`sanitize_schema_for_openapi` — both providers
    now strip ``additionalProperties`` and rewrite the type-array
    nullable form. The original schema is left intact so the validator
    layer keeps using the canonical version.
    """
    return sanitize_schema_for_openapi(schema)


def _augment_system_prompt(
    system_prompt: str, schema: dict, json_mode: JsonMode
) -> str:
    """Defense-in-depth: in non-strict json modes, embed the schema text
    into the system prompt so the model still has a JSON contract even if
    the relay silently drops ``response_format``. No-op for json_schema
    mode (relay handles the contract natively)."""
    if json_mode == "json_schema":
        return system_prompt
    schema_blob = json.dumps(schema, ensure_ascii=False)
    enforcement = (
        "\n\nReply with a single JSON object that matches this JSON Schema. "
        "Do not include markdown code fences, prose, or any other content "
        f"outside the JSON object.\nSchema:\n{schema_blob}"
    )
    return f"{system_prompt}{enforcement}" if system_prompt else enforcement.lstrip()


_CODEFENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(?P<body>.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE
)


def _strip_json_codefence(text: str) -> str:
    """Some relays wrap JSON in ```json ... ``` even when ``response_format``
    is set. Strip the fence if the entire content is exactly one fenced
    block; leave anything else untouched (json.loads will surface the real
    error)."""
    m = _CODEFENCE_RE.match(text)
    return m.group("body") if m else text
