"""T-0.7：本体桩对 SCENE_v0.md 所有合法 ref 的解析。"""
from __future__ import annotations

import pytest

from state.ontology import get_entity


def test_char_vellin() -> None:
    entity = get_entity("char_vellin")
    assert entity is not None
    assert entity["type"] == "character"
    assert entity["display_name"] == "Vellin"


def test_char_corvan() -> None:
    entity = get_entity("char_corvan")
    assert entity is not None
    assert entity["type"] == "character"
    assert entity["display_name"] == "Corvan"


def test_char_aelwin() -> None:
    entity = get_entity("char_aelwin")
    assert entity is not None
    assert entity["type"] == "character"
    assert entity["display_name"] == "Aelwin"


def test_scene_waystation_of_iron_oath() -> None:
    """T-2.2 envelope 迁移：scene_waystation_of_iron_oath 由 stage-0 桩态 `type=="scene"`
    迁到 stage-2 location envelope `type=="location"` + `location_type=="scene"`
    （ADR-016 / SCHEMA_v0.3.md §3）。loader 仍按 `entity["id"]` 索引，不破。
    """
    entity = get_entity("scene_waystation_of_iron_oath")
    assert entity is not None
    assert entity["type"] == "location"
    assert entity["location_type"] == "scene"
    assert entity["display_name"] == "Waystation of the Iron Oath"


def test_unknown_ref_returns_none() -> None:
    assert get_entity("char_unknown") is None


def test_error_variant_ref_is_deliberately_absent() -> None:
    """SCENE_v0.md §6.1 E1 例二的故意坏 ref；本体桩必须把它留在外面。"""
    assert get_entity("char_corvax_the_unknown") is None


@pytest.mark.parametrize(
    "entity_id",
    [
        "char_vellin",
        "char_corvan",
        "char_aelwin",
        "scene_waystation_of_iron_oath",
    ],
)
def test_scene_v0_refs_are_resolvable(entity_id: str) -> None:
    """冗余：SCENE_v0.md §1.2 + §1.3 的全部四条合法 ref 必须齐活。"""
    assert get_entity(entity_id) is not None
