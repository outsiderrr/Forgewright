"""Persona library tests (T-3.4 / ADR-022 P-1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.playtest import personas as personas_mod
from generator.playtest.personas import (
    PERSONAS_DIR,
    Persona,
    PersonaLoadError,
    hash_persona,
    hash_personas,
    load_all_personas,
    load_persona,
)


EXPECTED_PERSONA_IDS = {
    "cautious",
    "aggressive",
    "completionist",
    "speedrunner",
    "role_player",
}


# ---------------------------------------------------------------------------
# Bundled library
# ---------------------------------------------------------------------------


def test_bundled_library_has_five_personas():
    personas = load_all_personas()
    ids = {p.persona_id for p in personas}
    assert ids == EXPECTED_PERSONA_IDS
    assert len(personas) == 5
    # sorted by persona_id for stable manifest hashes
    sorted_ids = sorted(ids)
    assert [p.persona_id for p in personas] == sorted_ids


@pytest.mark.parametrize("persona_id", sorted(EXPECTED_PERSONA_IDS))
def test_bundled_persona_loads_with_required_fields(persona_id):
    persona = load_persona(persona_id)
    assert isinstance(persona, Persona)
    assert persona.persona_id == persona_id
    assert persona.display_name
    assert persona.base_traits  # at least one trait
    assert isinstance(persona.favors, tuple)
    assert isinstance(persona.avoids, tuple)
    # T-3.4 P-1: augmented_description hook left null in v1
    assert persona.augmented_description is None


def test_persona_is_frozen():
    persona = load_persona("cautious")
    with pytest.raises(Exception):  # FrozenInstanceError
        persona.persona_id = "evil_twin"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_hash_persona_is_deterministic():
    persona = load_persona("cautious")
    h1 = hash_persona(persona)
    h2 = hash_persona(persona)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_hash_personas_keys_sorted():
    personas = load_all_personas()
    hashes = hash_personas(personas)
    assert list(hashes.keys()) == sorted(EXPECTED_PERSONA_IDS)


def test_hash_changes_when_traits_change(tmp_path):
    base = tmp_path / "personas"
    base.mkdir()
    (base / "test.json").write_text(json.dumps({
        "persona_id": "test",
        "display_name": "Test",
        "base_traits": ["a"],
        "selection_bias": {"favors": [], "avoids": []},
        "augmented_description": None,
    }), encoding="utf-8")
    p1 = load_persona("test", root=base)
    h1 = hash_persona(p1)

    (base / "test.json").write_text(json.dumps({
        "persona_id": "test",
        "display_name": "Test",
        "base_traits": ["a", "b"],
        "selection_bias": {"favors": [], "avoids": []},
        "augmented_description": None,
    }), encoding="utf-8")
    p2 = load_persona("test", root=base)
    h2 = hash_persona(p2)
    assert h1 != h2


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_load_persona_missing_file_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_persona("does_not_exist", root=tmp_path)


def test_load_persona_invalid_json_raises_persona_load_error(tmp_path):
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(PersonaLoadError):
        load_persona("broken", root=tmp_path)


def test_load_persona_id_mismatch_raises(tmp_path):
    (tmp_path / "alice.json").write_text(json.dumps({
        "persona_id": "bob",
        "display_name": "Bob",
        "base_traits": [],
        "selection_bias": {"favors": [], "avoids": []},
        "augmented_description": None,
    }), encoding="utf-8")
    with pytest.raises(PersonaLoadError):
        load_persona("alice", root=tmp_path)


def test_load_persona_non_string_trait_raises(tmp_path):
    (tmp_path / "broken.json").write_text(json.dumps({
        "persona_id": "broken",
        "display_name": "Broken",
        "base_traits": [123],
        "selection_bias": {"favors": [], "avoids": []},
        "augmented_description": None,
    }), encoding="utf-8")
    with pytest.raises(PersonaLoadError):
        load_persona("broken", root=tmp_path)


def test_load_persona_empty_display_name_raises(tmp_path):
    (tmp_path / "blank.json").write_text(json.dumps({
        "persona_id": "blank",
        "display_name": "",
        "base_traits": ["x"],
        "selection_bias": {"favors": [], "avoids": []},
        "augmented_description": None,
    }), encoding="utf-8")
    with pytest.raises(PersonaLoadError):
        load_persona("blank", root=tmp_path)


def test_load_all_personas_empty_dir_returns_empty_list(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert load_all_personas(root=empty) == []


def test_personas_dir_resolves_to_bundled_module():
    assert PERSONAS_DIR.exists()
    assert PERSONAS_DIR.is_dir()
    files = sorted(p.stem for p in PERSONAS_DIR.glob("*.json"))
    assert set(files) == EXPECTED_PERSONA_IDS
