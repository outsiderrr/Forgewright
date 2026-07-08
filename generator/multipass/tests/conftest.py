"""multipass tests 共享 fixture."""
from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_budget(tmp_path, monkeypatch):
    """预算隔离：cost log 进 tmp、额度放宽——防测试污染真实成本台账。"""
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")
