"""LLMProvider Protocol — see ADR-011.

The Protocol is intentionally minimal: a single structured-output call plus a
cost estimator. Retry, budget, and prompt assembly all live one layer up
(`generate_node`, `budget.py`). Concrete providers live under
`generator/providers/` and are the only place where vendor SDKs may be
imported.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# R2.9 diagnostic excerpt cap (see baseline_007 finding b3c0ca3). Length is
# a *budget* — we keep at most this many chars total, head-and-tail when the
# raw body is longer, so a reader can still see both the leading status line
# and the trailing failure marker without one drowning the other in the log.
_RESPONSE_BODY_MAX_CHARS = 500

# Mask anything that *looks* like a credential token if it ever leaks into a
# response body. In practice neither google.genai nor openai surface API keys
# in error bodies, but the cost of keeping a defense in depth here is one
# regex; the cost of one accidental key in a committed jsonl is much higher.
_REDACT_RE = re.compile(
    r"(?P<label>api[_-]?key|authorization|bearer)"
    r"(?P<sep>\s*[:=]?\s*)"
    r"(?P<token>[A-Za-z0-9._\-+/]+)",
    re.IGNORECASE,
)


def _qualified_class_name(exc: BaseException) -> str:
    cls = type(exc)
    module = cls.__module__
    if module in (None, "", "builtins"):
        return cls.__name__
    return f"{module}.{cls.__name__}"


def _extract_http_status(exc: BaseException) -> int | None:
    """Pull an HTTP status from common SDK error shapes.

    google.genai's APIError exposes ``.status_code``; openai's
    APIStatusError / APITimeoutError uses the same attribute on the
    exception itself, with a nested ``.response.status_code`` as a
    fallback for the older shape. Anything else (httpx network errors,
    connection resets) genuinely has no HTTP status — we return None
    rather than fabricate one.
    """
    direct = getattr(exc, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(exc, "response", None)
    if response is not None:
        nested = getattr(response, "status_code", None)
        if isinstance(nested, int):
            return nested
    return None


def _stringify_body(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — best-effort; never raise from extractor
            return None
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return repr(value)
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return None


def _extract_body_excerpt(exc: BaseException) -> str | None:
    """Best-effort body extract from common SDK error shapes.

    Tries a small ordered list of attribute paths; the first one that
    yields a non-empty string wins. The result is redacted and
    length-capped before returning.
    """
    candidate_paths: tuple[tuple[str, ...], ...] = (
        ("response_text",),       # google.genai older shape
        ("response_json",),        # google.genai dict shape
        ("body",),                 # openai BadRequestError etc.
        ("message",),              # generic SDK fallback
        ("response", "text"),     # openai APIStatusError (httpx Response)
    )
    for attr_path in candidate_paths:
        value: Any = exc
        for attr in attr_path:
            value = getattr(value, attr, None)
            if value is None:
                break
        text = _stringify_body(value)
        if text:
            return _truncate_and_redact(text)
    return None


def _truncate_and_redact(text: str) -> str:
    """Apply credential redaction then head/tail truncate at the char cap."""
    redacted = _REDACT_RE.sub(
        lambda m: f"{m.group('label')}{m.group('sep')}<redacted>", text
    )
    if len(redacted) <= _RESPONSE_BODY_MAX_CHARS:
        return redacted
    head = _RESPONSE_BODY_MAX_CHARS // 2
    tail = _RESPONSE_BODY_MAX_CHARS - head
    return redacted[:head] + "…" + redacted[-tail:]


class ProviderError(RuntimeError):
    """Raised by a provider when a single API call fails (network, API,
    decoding). Callers decide whether to retry.

    Optional R2.9 metadata fields surface diagnostic context from the
    underlying SDK exception so batch logs can disambiguate three
    failure surfaces (sanitizer gap / relay timeout / upstream quota)
    without a live re-run. See baseline_007 finding (b3c0ca3) for the
    motivating data.

    Backward-compat: callers can still ``raise ProviderError("msg")``
    with no metadata; the new fields default to ``None`` and ``__str__``
    is unchanged.
    """

    def __init__(
        self,
        message: str,
        *,
        exception_class: str | None = None,
        http_status: int | None = None,
        response_body_excerpt: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exception_class = exception_class
        self.http_status = http_status
        self.response_body_excerpt = response_body_excerpt

    @classmethod
    def from_exception(
        cls, exc: BaseException, *, message: str
    ) -> "ProviderError":
        """Build a ProviderError carrying diagnostic metadata extracted
        from `exc`.

        Use at provider raise sites so callers see classifiable
        ProviderError instances regardless of which SDK threw. Best-
        effort: each field is None if the underlying exception doesn't
        expose it (httpx network errors typically have no HTTP status).
        """
        return cls(
            message,
            exception_class=_qualified_class_name(exc),
            http_status=_extract_http_status(exc),
            response_body_excerpt=_extract_body_excerpt(exc),
        )

    def metadata_dict(self) -> dict:
        """Return the three R2.9 fields as a JSON-serialisable dict.

        Suitable for embedding into ``scene_results.jsonl`` under
        ``result.failure_metadata`` when ``failure_reason`` is
        ``provider_error``.
        """
        return {
            "exception_class": self.exception_class,
            "http_status": self.http_status,
            "response_body_excerpt": self.response_body_excerpt,
        }


@dataclass
class StructuredResponse:
    content: dict
    raw_text: str
    input_tokens: int
    output_tokens: int
    model_id: str
    finish_reason: str


@runtime_checkable
class LLMProvider(Protocol):
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse: ...

    def estimate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> float: ...
