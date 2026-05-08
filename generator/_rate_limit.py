"""RateLimitedProvider wrapper for the T-3.5 batch scheduler (ADR-026 / F14).

Per STAGE_3_TASKS §3.5 + ADR-026 §"RateLimitedProvider wrapper (F14)":
the scheduler's N=3 worker pool would, without rate limiting, fan out
into burst calls that trip the upstream relay's per-account RPM ceiling
(PoloAI in particular returned ``insufficient_user_quota`` in
baseline_008 once concurrent calls exceeded its configured rate). The
fix is **not** an outer per-worker semaphore — that wouldn't gate the
internal skeleton/fill/judge calls each scene generation makes through
its `LLMProvider` instance. We wrap the inner provider with a
`RateLimitedProvider` whose `generate_structured` blocks on a shared
token bucket before delegating, so every API call (skeleton, every
fill, judge replay, probe) feeds through the same RPM budget.

Bucket parameters
-----------------
* `capacity` = the RPM ceiling. The bucket can absorb that many calls
  in one second of burst.
* `rate` = `rpm / 60` tokens per second. Default `rpm=60`
  (`FORGEWRIGHT_PROVIDER_RPM`).

Concurrency contract
--------------------
* `acquire(n)` blocks until `n` tokens are available; any number of
  threads can call it concurrently and they FIFO-ish through a
  `threading.Condition`.
* `RateLimitedProvider.generate_structured` is sync (not async) — the
  scheduler runs `generate_scene` under `asyncio.to_thread`, so a
  blocking `acquire` inside the wrapper just parks one of those worker
  threads without affecting the asyncio event loop.
* `model_id` is a property on most providers (Gemini / PoloAI) — we
  forward it via `__getattr__` so callers that introspect attributes
  not declared on `LLMProvider` (e.g. `getattr(provider, "model_id",
  "unknown")` in `generate_node` / `generate_scene`) keep working.

Why a separate module
---------------------
* CLAUDE.md rule 2: T-3.5's allowed-modification list explicitly carves
  out `/generator/_rate_limit.py` (new file). The wrapper does not
  belong inside `llm_provider.py` (that file is the Protocol / shared
  error surface — adding implementation would creep its scope).
* Tests can monkey-patch `time.monotonic` to drive the bucket
  deterministically without touching `LLMProvider` internals.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from generator.llm_provider import LLMProvider, StructuredResponse

# Default rate-per-minute. Mirrors STAGE_3_TASKS §2.4 / ADR-026 §"配置".
# Operators override via `FORGEWRIGHT_PROVIDER_RPM`; the scheduler also
# accepts a `--rpm N` CLI flag that wins over the env var.
DEFAULT_RPM = 60


class TokenBucket:
    """Thread-safe leaky-bucket throttle.

    `acquire(n)` blocks until `n` tokens are available, refilling at
    `rate` tokens/sec up to `capacity`. Construction validates the
    inputs so a misconfigured RPM (zero / negative) fails fast at
    wrapper instantiation rather than at first call.
    """

    def __init__(self, *, rate: float, capacity: int) -> None:
        if rate <= 0:
            raise ValueError(f"TokenBucket rate must be > 0, got {rate!r}")
        if capacity <= 0:
            raise ValueError(
                f"TokenBucket capacity must be > 0, got {capacity!r}"
            )
        self._rate = float(rate)
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._cv = threading.Condition()

    def acquire(self, n: int = 1) -> None:
        """Block until `n` tokens are available, then consume them."""
        if n <= 0:
            raise ValueError(f"acquire(n) requires n > 0, got {n!r}")
        if n > self._capacity:
            raise ValueError(
                f"acquire({n}) exceeds bucket capacity {self._capacity!r}"
            )
        with self._cv:
            while True:
                now = time.monotonic()
                elapsed = max(0.0, now - self._last_refill)
                self._tokens = min(
                    self._capacity, self._tokens + elapsed * self._rate
                )
                self._last_refill = now
                if self._tokens >= n:
                    self._tokens -= n
                    self._cv.notify()
                    return
                # Wait for enough tokens to accumulate. The wakeup is
                # purely a pacing hint — we re-check the loop condition
                # under the lock either way (spurious wakeups are benign).
                deficit = n - self._tokens
                wait = deficit / self._rate
                self._cv.wait(timeout=wait)


class RateLimitedProvider:
    """LLMProvider wrapper that gates `generate_structured` via a token bucket.

    The wrapper conforms to the `LLMProvider` Protocol structurally
    (`generate_structured` + `estimate_cost`); `__getattr__` forwards
    any other attribute access (notably `model_id`) to the inner
    provider so callers that pluck attributes off the provider keep
    working.

    `bucket` can be injected by tests (passing a mock with the same
    `acquire` interface) so behaviour can be asserted without sleeping.
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        rpm: int = DEFAULT_RPM,
        bucket: TokenBucket | None = None,
    ) -> None:
        if rpm <= 0:
            raise ValueError(f"rpm must be > 0, got {rpm!r}")
        self._inner = inner
        self._rpm = rpm
        # Lock around `acquire` so token consumption is strictly
        # serialised even if the underlying bucket is reused. The
        # bucket's own `Condition` is also serialised internally; the
        # extra lock is belt-and-braces for callers that pass their
        # own bucket subclass without internal locking.
        self._lock = threading.Lock()
        self._bucket = bucket if bucket is not None else TokenBucket(
            rate=rpm / 60.0, capacity=rpm
        )

    # -- LLMProvider Protocol surface --------------------------------------

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse:
        with self._lock:
            self._bucket.acquire()
        return self._inner.generate_structured(
            system_prompt, user_prompt, json_schema
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Estimation is local arithmetic — no API call, no rate-limit gate.
        return self._inner.estimate_cost(input_tokens, output_tokens)

    # -- Attribute forwarding ---------------------------------------------

    def __getattr__(self, name: str) -> Any:
        # `__getattr__` is only consulted when the attribute is missing
        # on the wrapper — `_inner`, `_bucket`, etc. are normal
        # attributes and don't reach this path. Safe to delegate
        # everything else (notably `model_id`).
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._inner, name)

    @property
    def inner(self) -> LLMProvider:
        return self._inner

    @property
    def rpm(self) -> int:
        return self._rpm


def resolve_rpm(*, cli_override: int | None = None) -> int:
    """Resolve the active RPM. Precedence: CLI flag > env var > default.

    Negative or zero values are treated as a misconfiguration —
    `RateLimitedProvider.__init__` raises on construction so the batch
    aborts at wrapper instantiation rather than discovering the broken
    bucket on first call.
    """
    if cli_override is not None:
        return int(cli_override)
    raw = os.environ.get("FORGEWRIGHT_PROVIDER_RPM")
    if raw is None or raw == "":
        return DEFAULT_RPM
    return int(raw)


__all__ = [
    "DEFAULT_RPM",
    "RateLimitedProvider",
    "TokenBucket",
    "resolve_rpm",
]
