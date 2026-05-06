"""Gemini implementation of LLMProvider.

Per ADR-011 / ADR-013: this is the only place in the repo that imports
`google.genai`. No retry, no budget — those belong to upper layers
(`generate_node`, `budget.py`).
"""

from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from generator.llm_provider import ProviderError, StructuredResponse
from generator.providers._retry import (
    _RETRYABLE_HTTP_STATUSES,
    retry_on_transient,
)
from generator.providers._schema_sanitizer import sanitize_schema_for_openapi

DEFAULT_MODEL_ID = "gemini-3.1-pro-preview"

# httpx default is 5s read timeout, which is too short for Gemini calls on
# longer prompts (parent chain + character cards). 120s is a generous upper
# bound for single-node generation.
#
# WARNING: google.genai's HttpOptions.timeout is documented as `int | None`
# with no unit hint, but the SDK treats it as MILLISECONDS internally. Passing
# an unconverted seconds value (e.g. 120) gets you a ~0.12s ConnectTimeout —
# fast enough that a TLS handshake (~0.8s through a SOCKS5 proxy) never
# completes. Always express this constant in ms.
_HTTP_TIMEOUT_MS = 120_000

# Fallback substring match for raw httpx-level exceptions that escape
# google.genai's APIError wrapping (proxy hiccups, mid-flight resets, TLS
# handshake stutters). The structured paths below — APIError with
# .code in {500, 502, 503, 504} — cover SDK-classified upstream 5xx. This
# list is the safety net for transport-level failures that bypass the
# SDK error hierarchy entirely.
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

# Gemini 3 Pro public pricing (USD per 1M tokens), input ≤ 200K context tier.
# Source: https://ai.google.dev/gemini-api/docs/pricing
# Captured: 2026-04-25.
# NOTE: Gemini 3.1 Pro is currently a preview SKU; Google has not published a
# separate price sheet for it as of the capture date. We use the public
# Gemini 3 Pro tier as a best-effort proxy. Update this constant in a follow-up
# PR once 3.1 Pro pricing lands. The > 200K context tier is intentionally not
# modelled — Stage 1 single-node prompts stay well under 200K.
_INPUT_USD_PER_MTOK = 2.00
_OUTPUT_USD_PER_MTOK = 12.00


class GeminiProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ProviderError(
                "GEMINI_API_KEY is not set; pass api_key= or set the env var."
            )
        self.model_id = model_id
        self._api_key = key
        self._client_cache: genai.Client | None = None

    @property
    def _client(self) -> genai.Client:
        # Lazy init: avoid HTTP/proxy setup at construction so callers (and
        # tests) can instantiate the provider without immediate side effects.
        if self._client_cache is None:
            self._client_cache = genai.Client(
                api_key=self._api_key,
                http_options=genai_types.HttpOptions(timeout=_HTTP_TIMEOUT_MS),
            )
        return self._client_cache

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse:
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=_sanitize_schema_for_gemini(json_schema),
        )
        response = self._call_with_transient_retry(config=config, user_prompt=user_prompt)

        raw_text = _extract_text(response)
        if raw_text is None:
            raise ProviderError("Gemini returned no text content")

        try:
            content: dict[str, Any] = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Gemini returned non-JSON despite response_mime_type=application/json: {exc}"
            ) from exc
        if not isinstance(content, dict):
            raise ProviderError(
                f"Gemini structured output is not a JSON object (got {type(content).__name__})"
            )

        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0

        finish_reason = "UNKNOWN"
        if response.candidates:
            fr = response.candidates[0].finish_reason
            if fr is not None:
                finish_reason = fr.name if hasattr(fr, "name") else str(fr)

        return StructuredResponse(
            content=content,
            raw_text=raw_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_id=self.model_id,
            finish_reason=finish_reason,
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * _INPUT_USD_PER_MTOK
            + output_tokens * _OUTPUT_USD_PER_MTOK
        ) / 1_000_000

    def _call_with_transient_retry(
        self,
        *,
        config: genai_types.GenerateContentConfig,
        user_prompt: str,
    ) -> genai_types.GenerateContentResponse:
        try:
            return retry_on_transient(
                lambda: self._client.models.generate_content(
                    model=self.model_id,
                    contents=user_prompt,
                    config=config,
                ),
                is_transient=_should_retry,
            )
        except genai_errors.APIError as exc:
            # SDK-classified API error that survived the retry path
            # (either non-retryable 4xx, or 5xx that exhausted retries).
            raise ProviderError.from_exception(
                exc, message=f"Gemini API error: {exc}"
            ) from exc
        except Exception as exc:  # connection-level / unwrapped httpx errors
            raise ProviderError.from_exception(
                exc, message=f"Gemini call failed: {exc}"
            ) from exc


def _should_retry(exc: BaseException) -> bool:
    """Classify whether a google.genai exception is worth retrying.

    Retryable: ``ServerError`` and any ``APIError`` whose ``.code`` lands
    in {500, 502, 503, 504} — upstream transient. Non-retryable: 4xx
    (``ClientError``: auth, sanitizer-gap, quota), 429 rate-limit. Raw
    httpx-level errors fall through to the substring-fallback path
    matching the PoloAIProvider shape.

    google.genai exposes the HTTP status as ``.code`` on its ``APIError``,
    not ``status_code``; that quirk is documented in the user-level
    memory note ``gemini_sdk_quirks.md`` (alongside ``HttpOptions.timeout``
    being milliseconds).
    """
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if isinstance(code, int) and code in _RETRYABLE_HTTP_STATUSES:
            return True
        return False
    return _is_transient_network_error(exc)


def _is_transient_network_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    return any(p in msg for p in _TRANSIENT_ERROR_SUBSTRINGS)


def _sanitize_schema_for_gemini(schema: Any, _path: str = "") -> Any:
    """Adapt JSON Schema input into the OpenAPI subset Gemini accepts.

    Thin alias kept for backwards-compatible imports (R2.2 tests, and
    any debug script that grabbed the symbol directly). The rule set
    lives in :func:`generator.providers._schema_sanitizer.sanitize_schema_for_openapi`
    and is shared with PoloAIProvider — see R2.8 for the consolidation
    rationale.
    """
    return sanitize_schema_for_openapi(schema, _path)


def _extract_text(response: genai_types.GenerateContentResponse) -> str | None:
    text = response.text
    if text:
        return text
    if not response.candidates:
        return None
    parts = response.candidates[0].content.parts if response.candidates[0].content else None
    if not parts:
        return None
    chunks = [p.text for p in parts if getattr(p, "text", None)]
    return "".join(chunks) if chunks else None
