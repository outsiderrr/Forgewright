"""T-1.6 + T-2.11: end-to-end tests for `generate_node` using a FakeProvider.

Six original scenarios cover the contract laid out in ADR-013:

  scenario_1: first attempt valid              → success, attempts=1
  scenario_2: first invalid, second valid      → success, attempts=2
  scenario_3: three invalid attempts           → failure_reason="schema_invalid"
  scenario_4: provider raises BudgetExceeded   → failure_reason="budget_exceeded"
                (triggered via budget cap, not by the provider itself —
                 BudgetExceeded comes from /generator/budget.py)
  scenario_5: provider raises ProviderError    → failure_reason="provider_error"
  scenario_6: empty parent_chain (entry node)  → prompt assembly stays clean

T-2.11 adds reconcile + tri-state refund hook integration tests at the bottom.

No real Gemini calls — that's T-1.7's territory.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from generator import budget, cost_log
from generator.context_assembler import GraphContext, NodeRequirement
from generator.generate_node import GenerationResult, generate_node
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse

# ---------------------------------------------------------------------------
# Fixtures: budget isolation + fake content
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    """Each test gets its own cost log + a generous default budget so we
    don't accidentally trip BudgetExceeded outside scenario_4."""
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


_SCENE = json.loads(
    (Path(__file__).resolve().parent.parent.parent
     / "content" / "test_scene_v0" / "scene.json").read_text(encoding="utf-8")
)


def _valid_dialogue_node() -> dict:
    """A real, schema-valid dialogue node lifted from the test scene.

    Lifted (not synthesised) so we know it satisfies every JSON-Schema
    constraint — the generator's own validator should accept it cleanly.
    """
    return copy.deepcopy(_SCENE["nodes"]["arrival_waystation"])


def _valid_end_node() -> dict:
    return copy.deepcopy(_SCENE["nodes"]["end_silent_ally"])


def _invalid_node_missing_required() -> dict:
    """Drops `narration` — a required field — to force a schema error."""
    bad = _valid_dialogue_node()
    del bad["narration"]
    return bad


def _make_response(content: dict) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=1234,
        output_tokens=567,
        model_id="fake-model",
        finish_reason="STOP",
    )


# ---------------------------------------------------------------------------
# FakeProvider: scripted per-call responses
# ---------------------------------------------------------------------------


class _ScriptedProvider:
    """Returns / raises items from `script` in order, one per call.

    Items can be `StructuredResponse` (returned) or `Exception` (raised).
    `estimate_cost` returns a fixed small value so the budget guard passes
    in every scenario except the one that overrides PER_CALL_BUDGET_USD.
    """

    model_id = "fake-model"

    def __init__(self, script: list[StructuredResponse | Exception]) -> None:
        self._script = list(script)
        self._idx = 0
        self.call_count = 0

    def generate_structured(
        self, system_prompt: str, user_prompt: str, json_schema: dict
    ) -> StructuredResponse:
        self.call_count += 1
        if self._idx >= len(self._script):
            raise AssertionError(
                f"FakeProvider exhausted on call #{self.call_count}; "
                f"script length = {len(self._script)}"
            )
        item = self._script[self._idx]
        self._idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.001


def _ctx(parent_chain: list[dict] | None = None) -> GraphContext:
    return GraphContext(
        scene_anchor="scene_waystation_of_iron_oath",
        location_card={"location_id": "scene_waystation_of_iron_oath", "name": "铁誓驿站"},
        parent_chain=parent_chain if parent_chain is not None else [],
        involved_characters=[
            {"character_id": "char_vellin", "summary": "驿站管事，旧识"},
            {"character_id": "char_corvan", "summary": "巡逻官，旧识"},
            {"character_id": "char_aelwin", "summary": "逃兵，少年兵旧识"},
        ],
        faction_clocks={},
    )


def _req() -> NodeRequirement:
    return NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_vellin",
        narrative_intent="建立场景张力，让玩家在『过路客 / 介入者』之间表态",
    )


# ---------------------------------------------------------------------------
# Sanity check: FakeProvider satisfies the LLMProvider Protocol
# ---------------------------------------------------------------------------


def test_fake_provider_is_an_llm_provider():
    assert isinstance(_ScriptedProvider([]), LLMProvider)


# ---------------------------------------------------------------------------
# scenario_1: first attempt valid
# ---------------------------------------------------------------------------


def test_scenario_1_first_attempt_valid_succeeds():
    provider = _ScriptedProvider([_make_response(_valid_dialogue_node())])
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert isinstance(result, GenerationResult)
    assert result.success is True
    assert result.failure_reason is None
    assert result.node is not None
    assert result.node["node_id"] == "arrival_waystation"
    assert len(result.attempts) == 1
    assert result.attempts[0].attempt_index == 1
    assert result.attempts[0].validator_errors == []
    assert provider.call_count == 1
    assert result.total_cost_usd > 0


# ---------------------------------------------------------------------------
# scenario_2: first invalid, second valid
# ---------------------------------------------------------------------------


def test_scenario_2_invalid_then_valid_succeeds_on_retry():
    provider = _ScriptedProvider(
        [
            _make_response(_invalid_node_missing_required()),
            _make_response(_valid_dialogue_node()),
        ]
    )
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert result.success is True
    assert result.failure_reason is None
    assert len(result.attempts) == 2
    assert result.attempts[0].validator_errors  # first attempt had errors
    assert result.attempts[1].validator_errors == []
    assert provider.call_count == 2


# ---------------------------------------------------------------------------
# scenario_3: three invalid attempts
# ---------------------------------------------------------------------------


def test_scenario_3_three_invalid_returns_schema_invalid():
    provider = _ScriptedProvider(
        [
            _make_response(_invalid_node_missing_required()),
            _make_response(_invalid_node_missing_required()),
            _make_response(_invalid_node_missing_required()),
        ]
    )
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert result.success is False
    assert result.failure_reason == "schema_invalid"
    assert result.node is None
    assert len(result.attempts) == 3
    assert all(a.validator_errors for a in result.attempts)
    assert provider.call_count == 3


# ---------------------------------------------------------------------------
# scenario_4: budget exceeded before the provider is even called
# ---------------------------------------------------------------------------


def test_scenario_4_budget_exceeded_returns_clean_failure(monkeypatch):
    # Drop the per-call cap below the FakeProvider's flat $0.001 estimate
    # so check_and_charge raises immediately on the first call.
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.0000001")

    provider = _ScriptedProvider([_make_response(_valid_dialogue_node())])
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert result.success is False
    assert result.failure_reason == "budget_exceeded"
    assert result.node is None
    assert provider.call_count == 0  # provider never reached
    assert len(result.attempts) == 1
    assert "budget_exceeded" in result.attempts[0].validator_errors[0]


# ---------------------------------------------------------------------------
# scenario_5: provider raises ProviderError
# ---------------------------------------------------------------------------


def test_scenario_5_provider_error_returns_clean_failure():
    provider = _ScriptedProvider([ProviderError("simulated network failure")])
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert result.success is False
    assert result.failure_reason == "provider_error"
    assert result.node is None
    assert provider.call_count == 1
    assert len(result.attempts) == 1
    assert "provider_error" in result.attempts[0].validator_errors[0]


# ---------------------------------------------------------------------------
# scenario_6: empty parent_chain (entry-node position) still assembles cleanly
# ---------------------------------------------------------------------------


def test_scenario_6_empty_parent_chain_assembles_and_succeeds():
    captured: dict[str, str] = {}

    class _CapturingProvider(_ScriptedProvider):
        def generate_structured(
            self, system_prompt: str, user_prompt: str, json_schema: dict
        ) -> StructuredResponse:
            captured["system"] = system_prompt
            captured["user"] = user_prompt
            return super().generate_structured(system_prompt, user_prompt, json_schema)

    provider = _CapturingProvider([_make_response(_valid_dialogue_node())])
    result = generate_node(
        graph_context=_ctx(parent_chain=[]),
        node_requirement=_req(),
        provider=provider,
    )

    assert result.success is True
    # The entry-node case must produce a prompt that announces the absent
    # parents rather than crashing or rendering an empty section.
    assert "无父节点" in captured["user"]
    assert provider.call_count == 1


# ===========================================================================
# T-2.11 R7: reconcile + tri-state refund hook integration
# ===========================================================================


def _read_log(tmp_path) -> list[dict]:
    p = tmp_path / "cost_log.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text("utf-8").splitlines()]


def test_t211_success_path_reconciles_each_attempt(tmp_path):
    """Mock SDK usage_metadata flows through to cost_log via reconcile_after_call."""
    # ScriptedProvider.estimate_cost returns a flat 0.001 for any token count,
    # so the reconciled actual_cost equals 0.001 regardless of input/output.
    response = _make_response(_valid_dialogue_node())  # input=1234, output=567
    provider = _ScriptedProvider([response])

    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )
    assert result.success is True

    rows = _read_log(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    # Estimate token counts came from generate_node's own char-based heuristic;
    # post-reconcile they should match the StructuredResponse fields.
    assert row["input_tokens"] == 1234
    assert row["output_tokens"] == 567
    assert row["reconciled"] is True
    assert "reconciled_at" in row
    assert "status" not in row  # success, not refunded


def test_t211_pre_call_budget_fail_writes_no_record(tmp_path, monkeypatch):
    """tri-state #1 (pre_call_budget_fail): no record_id, cost_log untouched."""
    # Push the per-call cap below the FakeProvider's flat $0.001 estimate.
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "0.0000001")

    provider = _ScriptedProvider([_make_response(_valid_dialogue_node())])
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )

    assert result.success is False
    assert result.failure_reason == "budget_exceeded"
    assert provider.call_count == 0
    assert _read_log(tmp_path) == []  # nothing ever recorded


def test_t211_request_sent_failure_keeps_estimated_charge(tmp_path):
    """tri-state #3 (request_sent_failure): row remains charged, no refund flag."""
    provider = _ScriptedProvider([ProviderError("simulated 500 from server")])
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )
    assert result.success is False
    assert result.failure_reason == "provider_error"

    rows = _read_log(tmp_path)
    assert len(rows) == 1
    # The estimate stays on the books — generate_node did NOT call
    # refund_estimated for ProviderError (R2.1 follow-up will classify
    # connect-fail vs API-error and decide).
    assert "status" not in rows[0]
    assert "reconciled" not in rows[0]
    assert rows[0]["cost_usd"] > 0  # estimated charge retained


def test_t211_request_not_sent_refund_via_direct_api(tmp_path):
    """tri-state #2 (request_not_sent): exercise the refund_estimated path.

    generate_node currently defaults all ProviderError to request_sent_failure
    (see T-2.11 PR body). The request_not_sent API surface is exercised here
    via direct budget call so the round-trip is covered ahead of R2.1.
    """
    record_id = budget.check_and_charge(
        0.45, model_id="m", input_tokens=1, output_tokens=1
    )
    assert budget.today_total_usd() == pytest.approx(0.45)

    budget.refund_estimated(record_id, reason="request_not_sent")

    rows = _read_log(tmp_path)
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 0.0
    assert rows[0]["status"] == "refunded"
    assert rows[0]["refund_reason"] == "request_not_sent"
    assert budget.today_total_usd() == pytest.approx(0.0)


def test_t211_retry_attempts_reconcile_independently(tmp_path):
    """Each LLM call gets its own row; each row is reconciled on success."""
    provider = _ScriptedProvider(
        [
            _make_response(_invalid_node_missing_required()),  # attempt 1: schema fail
            _make_response(_valid_dialogue_node()),             # attempt 2: success
        ]
    )
    result = generate_node(
        graph_context=_ctx(), node_requirement=_req(), provider=provider
    )
    assert result.success is True

    rows = _read_log(tmp_path)
    assert len(rows) == 2
    # Both API calls actually returned, so both rows should be reconciled.
    # schema_invalid does not refund — the LLM was billed.
    assert all(r.get("reconciled") is True for r in rows)
    assert all("status" not in r for r in rows)
    # And the record_ids are unique.
    assert len({r["record_id"] for r in rows}) == 2
