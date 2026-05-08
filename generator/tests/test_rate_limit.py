"""Unit tests for the T-3.5 RateLimitedProvider wrapper (ADR-026 / F14)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import pytest

from generator._rate_limit import (
    DEFAULT_RPM,
    RateLimitedProvider,
    TokenBucket,
    resolve_rpm,
)
from generator.llm_provider import StructuredResponse


# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------


def test_token_bucket_rejects_invalid_construction():
    with pytest.raises(ValueError):
        TokenBucket(rate=0, capacity=10)
    with pytest.raises(ValueError):
        TokenBucket(rate=10, capacity=0)


def test_token_bucket_rejects_invalid_acquire():
    bucket = TokenBucket(rate=10, capacity=5)
    with pytest.raises(ValueError):
        bucket.acquire(0)
    with pytest.raises(ValueError):
        bucket.acquire(6)  # exceeds capacity


def test_token_bucket_acquires_within_capacity_without_blocking(monkeypatch):
    """Capacity-many acquires in a row return immediately."""
    fake_now = [100.0]
    monkeypatch.setattr(
        "generator._rate_limit.time.monotonic", lambda: fake_now[0]
    )
    bucket = TokenBucket(rate=1.0, capacity=3)
    start = time.monotonic()
    bucket.acquire()
    bucket.acquire()
    bucket.acquire()
    # We never advanced the fake clock, so the loop never had to wait.
    assert time.monotonic() - start < 0.5  # generous wall clock margin


def test_token_bucket_blocks_when_drained(monkeypatch):
    """Once tokens drain, the next acquire waits for refill."""
    # Drive `time.monotonic` from a controllable list so the bucket
    # refill arithmetic is deterministic.
    fake_now = [100.0]

    def fake_monotonic():
        return fake_now[0]

    monkeypatch.setattr(
        "generator._rate_limit.time.monotonic", fake_monotonic
    )

    bucket = TokenBucket(rate=2.0, capacity=2)  # refill 2 tokens / sec
    bucket.acquire()  # 1 left
    bucket.acquire()  # 0 left

    # Replace the bucket's Condition.wait so we don't actually sleep —
    # advancing the fake clock and returning simulates a refill.
    real_cv = bucket._cv
    wait_calls = []
    original_wait = real_cv.wait

    def stub_wait(timeout=None):
        wait_calls.append(timeout)
        # Advance the fake clock by the timeout, then return as if the
        # refill happened.
        fake_now[0] += timeout if timeout is not None else 1.0
        return True

    monkeypatch.setattr(real_cv, "wait", stub_wait)

    bucket.acquire()
    assert wait_calls, "expected the bucket to wait when drained"
    assert wait_calls[0] > 0, "wait timeout should be the refill deficit"


# ---------------------------------------------------------------------------
# RateLimitedProvider
# ---------------------------------------------------------------------------


@dataclass
class _StubProvider:
    model_id: str = "stub-model"
    calls: list[tuple[str, str, dict]] = None

    def __post_init__(self):
        if self.calls is None:
            self.calls = []

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.calls.append((system_prompt, user_prompt, json_schema))
        return StructuredResponse(
            content={"ok": "yes"},
            raw_text='{"ok":"yes"}',
            input_tokens=10,
            output_tokens=4,
            model_id=self.model_id,
            finish_reason="STOP",
        )

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.001 * (input_tokens + output_tokens)


class _TrackingBucket:
    """Mock bucket that records acquire calls without sleeping."""

    def __init__(self):
        self.acquires: list[int] = []

    def acquire(self, n: int = 1) -> None:
        self.acquires.append(n)


def test_rate_limited_provider_calls_acquire_before_inner():
    inner = _StubProvider()
    bucket = _TrackingBucket()
    wrapped = RateLimitedProvider(inner, rpm=60, bucket=bucket)
    response = wrapped.generate_structured("sys", "user", {"type": "object"})
    assert bucket.acquires == [1]
    assert response.content == {"ok": "yes"}
    assert inner.calls == [("sys", "user", {"type": "object"})]


def test_rate_limited_provider_forwards_estimate_cost_unrate_limited():
    inner = _StubProvider()
    bucket = _TrackingBucket()
    wrapped = RateLimitedProvider(inner, rpm=60, bucket=bucket)
    cost = wrapped.estimate_cost(100, 50)
    assert cost == pytest.approx(0.001 * 150)
    # estimate_cost is not rate-limited.
    assert bucket.acquires == []


def test_rate_limited_provider_exposes_inner_attributes():
    inner = _StubProvider(model_id="custom-id")
    wrapped = RateLimitedProvider(inner, rpm=30, bucket=_TrackingBucket())
    assert wrapped.model_id == "custom-id"
    assert wrapped.inner is inner
    assert wrapped.rpm == 30


def test_rate_limited_provider_rejects_zero_rpm():
    with pytest.raises(ValueError):
        RateLimitedProvider(_StubProvider(), rpm=0)


def test_rate_limited_provider_serialises_acquire_under_threads():
    """Concurrent generate_structured calls must each acquire exactly
    once even though `acquire` is called under the wrapper's own lock.
    """
    inner = _StubProvider()
    bucket = _TrackingBucket()
    wrapped = RateLimitedProvider(inner, rpm=60, bucket=bucket)
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        wrapped.generate_structured("sys", "user", {"type": "object"})

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(bucket.acquires) == 8
    assert len(inner.calls) == 8


def test_resolve_rpm_default_when_unset(monkeypatch):
    monkeypatch.delenv("FORGEWRIGHT_PROVIDER_RPM", raising=False)
    assert resolve_rpm() == DEFAULT_RPM


def test_resolve_rpm_env_override(monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_PROVIDER_RPM", "120")
    assert resolve_rpm() == 120


def test_resolve_rpm_cli_wins_over_env(monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_PROVIDER_RPM", "120")
    assert resolve_rpm(cli_override=30) == 30
