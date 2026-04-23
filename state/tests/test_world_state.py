"""T-0.7：WorldState 读写 API 测试。

覆盖 get / set / has / 嵌套自动创建 / 类型白名单 / as_dict 六组。
"""
from __future__ import annotations

import pytest

from state.world_state import WorldState


def test_set_then_get_returns_value() -> None:
    s = WorldState()
    s.set("relationship.vellin.trust", 3)
    assert s.get("relationship.vellin.trust") == 3


def test_get_missing_returns_none() -> None:
    s = WorldState()
    assert s.get("relationship.vellin.trust") is None


def test_has_existing_and_missing() -> None:
    s = WorldState()
    s.set("flag.blood_letter_seen", True)
    assert s.has("flag.blood_letter_seen") is True
    assert s.has("flag.unseen_flag") is False
    assert s.has("relationship.vellin.trust") is False


def test_nested_set_creates_intermediate_dicts() -> None:
    s = WorldState()
    s.set("faction.iron_oath.reputation", 2)
    snapshot = s.as_dict()
    assert snapshot == {"faction": {"iron_oath": {"reputation": 2}}}


def test_overwrite_existing_key() -> None:
    s = WorldState()
    s.set("flag.x", "first")
    s.set("flag.x", "second")
    assert s.get("flag.x") == "second"


def test_set_rejects_unsupported_type_none() -> None:
    s = WorldState()
    with pytest.raises(TypeError):
        s.set("flag.x", None)


def test_set_rejects_unsupported_type_tuple() -> None:
    s = WorldState()
    with pytest.raises(TypeError):
        s.set("flag.x", (1, 2, 3))


def test_set_rejects_unsupported_type_set() -> None:
    s = WorldState()
    with pytest.raises(TypeError):
        s.set("flag.x", {1, 2, 3})


def test_set_accepts_all_whitelisted_types() -> None:
    s = WorldState()
    s.set("p.b", True)
    s.set("p.i", 1)
    s.set("p.f", 1.5)
    s.set("p.s", "ok")
    s.set("p.l", [1, 2])
    s.set("p.d", {"k": "v"})
    assert s.get("p.b") is True
    assert s.get("p.i") == 1
    assert s.get("p.f") == 1.5
    assert s.get("p.s") == "ok"
    assert s.get("p.l") == [1, 2]
    assert s.get("p.d") == {"k": "v"}


def test_empty_path_raises() -> None:
    s = WorldState()
    with pytest.raises(ValueError):
        s.set("", 1)
    with pytest.raises(ValueError):
        s.get("")
    with pytest.raises(ValueError):
        s.has("")


def test_path_with_empty_segment_raises() -> None:
    s = WorldState()
    with pytest.raises(ValueError):
        s.set("a..b", 1)
    with pytest.raises(ValueError):
        s.get("a..b")


def test_get_descends_through_nonexistent_prefix_returns_none() -> None:
    s = WorldState()
    s.set("a.b", 1)
    assert s.get("a.b.c.d") is None
    assert s.has("a.b.c.d") is False


def test_as_dict_returns_live_snapshot_root() -> None:
    s = WorldState()
    s.set("a.b", 1)
    snap = s.as_dict()
    assert snap["a"]["b"] == 1
