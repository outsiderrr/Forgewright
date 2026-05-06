"""Shared exponential-backoff retry helper for LLM providers — R2.10b.

Two providers (PoloAIProvider, GeminiProvider) need the same retry policy
on transient upstream failures (5xx server errors, connection failures,
timeouts). Before R2.10b, each provider rolled its own one-shot 2.0s
retry that didn't catch SDK-classified 5xx (the OpenAI ``InternalServerError``
hierarchy is wrapped by ``OpenAIError`` and was raised through unconditionally).
baseline_010 (commit 8373e01) caught 7/15 PoloAI iterations failing on
exactly that surface — 4× HTTP 500 in a 16-second window plus 3×
APIConnectionError — none of which the existing logic retried.

This module owns the *policy*: how many attempts, what delays between
them, and which HTTP statuses are retryable. The *predicate* — is this
specific exception transient? — stays at the provider level because the
SDKs differ (openai uses ``OpenAIError`` subclasses + ``status_code``;
google.genai uses ``APIError`` subclasses + ``code``). Centralising just
the policy prevents R2.7-style drift (where the two providers' sanitizers
diverged silently) without forcing the predicates into a leaky union shape.

Policy: 1 initial attempt + up to 3 retries = 4 total attempts. Backoff
between attempts is [2.0s, 5.0s, 10.0s] — chosen to cross the iter 9–12
~16-second 500 cluster baseline_010 captured (cumulative ~17s sleeps).
HTTP statuses {500, 502, 503, 504} are retryable; other 5xx (e.g. 501
Not Implemented, 505 HTTP Version Not Supported) are not — those signal
configuration issues that wouldn't resolve on retry.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

# Single source of truth for retry policy. Exposed for tests to assert
# the sequence and for two providers to import-and-grep so they cannot
# drift apart.
_MAX_RETRIES = 3
_RETRY_DELAYS_SEC: tuple[float, ...] = (2.0, 5.0, 10.0)
assert len(_RETRY_DELAYS_SEC) == _MAX_RETRIES, (
    "_RETRY_DELAYS_SEC must have one entry per retry"
)

# 5xx codes that signal upstream transient state. Excludes 501 / 505 /
# 511 because those reflect server configuration, not load.
_RETRYABLE_HTTP_STATUSES: frozenset[int] = frozenset({500, 502, 503, 504})


T = TypeVar("T")


def retry_on_transient(
    fn: Callable[[], T],
    *,
    is_transient: Callable[[BaseException], bool],
) -> T:
    """Run ``fn()`` with exponential backoff on transient failures.

    Calls ``fn`` up to ``1 + _MAX_RETRIES`` times. Between attempts,
    sleeps ``_RETRY_DELAYS_SEC[attempt_idx]``. The caller-supplied
    ``is_transient`` predicate decides which exceptions trigger the
    next retry; non-transient exceptions and the final-attempt failure
    propagate unchanged so the caller can wrap them into ``ProviderError``
    with provider-specific framing.

    The predicate receives the raw exception — implementations can
    inspect SDK class hierarchies, ``.status_code``, ``.code``, message
    substrings, or whatever the SDK exposes.
    """
    last_attempt = _MAX_RETRIES  # zero-indexed: attempts go 0..max_retries
    for attempt_idx in range(1 + _MAX_RETRIES):
        try:
            return fn()
        except BaseException as exc:
            if attempt_idx == last_attempt or not is_transient(exc):
                raise
            time.sleep(_RETRY_DELAYS_SEC[attempt_idx])
    # Unreachable: every iteration either returns or raises.
    raise RuntimeError(
        "retry_on_transient: loop exited without return — unreachable"
    )
