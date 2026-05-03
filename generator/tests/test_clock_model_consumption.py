"""T-2.2：generated Clock pydantic model 可被 prompt context 消费。

本文件只验证 generated `generator.models.Clock` 能够：
- 用合法 sample（faction scope + every_n_scenes advance_rule + tick_effects）
  构造；
- 字段访问（scope / ticks_total / advance_rule.type / tick_effects[]）在
  model 实例上可读；
- 拒收 ADR-017 边界外样本（ticks_total > 20 / time_based 子类等）。

T-2.5 prompt 模板会以 active_clocks 字段（v1.0 §2.8）注入 GraphContext；
本测试是 T-2.5 / T-2.7 的前置 unit smoke test。**不**测 schema 校验本身
（那归 /schema/tests/）。
"""
from __future__ import annotations

import pytest

from generator.models import Clock


def _sample_clock_dict() -> dict:
    return {
        "schema_version": "0.3.0",
        "id": "clk_iron_oath_pursuit",
        "name": "铁誓追捕度",
        "scope": "faction",
        "ticks_total": 6,
        "ticks_filled": 0,
        "advance_rule": {"type": "every_n_scenes", "params": {"n": 2}},
        "tick_effects": [
            {
                "at_tick": 6,
                "effect_op": "set",
                "path": "flag.iron_oath_full_pursuit",
                "value": True,
            }
        ],
    }


def test_clock_model_validates_sample() -> None:
    clock = Clock.model_validate(_sample_clock_dict())
    assert clock.id == "clk_iron_oath_pursuit"
    assert clock.scope.value == "faction"
    assert clock.ticks_total == 6
    assert clock.ticks_filled == 0
    assert clock.advance_rule.type.value == "every_n_scenes"
    assert clock.tick_effects is not None
    assert len(clock.tick_effects) == 1
    assert clock.tick_effects[0].effect_op.value == "set"


def test_clock_model_rejects_ticks_total_above_20() -> None:
    bad = _sample_clock_dict()
    bad["ticks_total"] = 21
    with pytest.raises(Exception):
        Clock.model_validate(bad)


def test_clock_model_rejects_time_based_advance_rule() -> None:
    """ADR-017：advance_rule.type 不存在 time_based 子类。"""
    bad = _sample_clock_dict()
    bad["advance_rule"] = {"type": "time_based", "params": {}}
    with pytest.raises(Exception):
        Clock.model_validate(bad)


def test_clock_model_dump_roundtrip() -> None:
    src = _sample_clock_dict()
    clock = Clock.model_validate(src)
    import json
    dumped = json.loads(clock.model_dump_json(exclude_unset=True))
    assert dumped["id"] == src["id"]
    assert dumped["ticks_total"] == src["ticks_total"]
    assert dumped["advance_rule"]["type"] == src["advance_rule"]["type"]
    assert dumped["tick_effects"][0]["path"] == src["tick_effects"][0]["path"]
