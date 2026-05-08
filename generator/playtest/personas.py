"""Persona library for playtest bots (T-3.4 / ADR-022).

Five hand-written personas live as JSON sidecars in
``generator/playtest/personas/``. Each carries:

  * ``persona_id`` — stable string id (file basename minus ``.json``)
  * ``display_name`` — human-readable label for reports
  * ``base_traits`` — short list of trait keywords used in the runner's
    LLM prompt to bias option selection
  * ``selection_bias.favors`` / ``selection_bias.avoids`` — coarse
    keyword hints (option text / metadata that "looks like" combat,
    diplomacy, etc.); the LLM does the actual mapping
  * ``augmented_description`` — reserved hook for the future LLM-augment
    step; **always null in v1** (T-3.4 explicitly leaves the augment
    pipeline for a later stage; the runner must still tolerate the
    field present-but-null)

The :class:`Persona` dataclass is the only contract callers need; JSON
shape is validated on load so a malformed persona file fails fast at
batch start, not mid-run.

Hashing: :func:`hash_persona` returns a SHA-256 of the canonical JSON
form. Used in ``run_manifest.json`` so a future replay can confirm the
persona definition is byte-identical to what produced the worst-10%
list.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PERSONAS_DIR = Path(__file__).parent / "personas"


class PersonaLoadError(ValueError):
    """Raised when a persona JSON file is missing fields or malformed."""


@dataclass(frozen=True)
class Persona:
    """One persona definition (immutable).

    Frozen so the runner can't accidentally mutate a shared instance
    between paths. ``base_traits`` and bias lists are tuples after
    loading for the same reason.
    """

    persona_id: str
    display_name: str
    base_traits: tuple[str, ...]
    favors: tuple[str, ...]
    avoids: tuple[str, ...]
    augmented_description: str | None

    def to_canonical_dict(self) -> dict:
        """Stable dict form used for hashing + manifest serialisation.

        Keys ordered alphabetically; tuples → lists so the result
        round-trips through ``json.dumps``.
        """
        return {
            "augmented_description": self.augmented_description,
            "base_traits": list(self.base_traits),
            "display_name": self.display_name,
            "persona_id": self.persona_id,
            "selection_bias": {
                "avoids": list(self.avoids),
                "favors": list(self.favors),
            },
        }


def _coerce_str_list(value: object, *, field: str, persona_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PersonaLoadError(
            f"persona {persona_id!r}: field {field!r} must be a list of strings"
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise PersonaLoadError(
                f"persona {persona_id!r}: field {field!r} contains non-string item {item!r}"
            )
        items.append(item)
    return tuple(items)


def _persona_from_dict(data: dict, *, source: str) -> Persona:
    persona_id_raw = data.get("persona_id")
    if not isinstance(persona_id_raw, str) or not persona_id_raw:
        raise PersonaLoadError(
            f"persona file {source}: persona_id must be a non-empty string"
        )
    display_name = data.get("display_name")
    if not isinstance(display_name, str) or not display_name:
        raise PersonaLoadError(
            f"persona {persona_id_raw!r}: display_name must be a non-empty string"
        )
    base_traits = _coerce_str_list(
        data.get("base_traits"), field="base_traits", persona_id=persona_id_raw
    )
    bias = data.get("selection_bias") or {}
    if not isinstance(bias, dict):
        raise PersonaLoadError(
            f"persona {persona_id_raw!r}: selection_bias must be an object"
        )
    favors = _coerce_str_list(
        bias.get("favors"), field="selection_bias.favors", persona_id=persona_id_raw
    )
    avoids = _coerce_str_list(
        bias.get("avoids"), field="selection_bias.avoids", persona_id=persona_id_raw
    )
    augmented = data.get("augmented_description", None)
    if augmented is not None and not isinstance(augmented, str):
        raise PersonaLoadError(
            f"persona {persona_id_raw!r}: augmented_description must be string or null"
        )
    return Persona(
        persona_id=persona_id_raw,
        display_name=display_name,
        base_traits=base_traits,
        favors=favors,
        avoids=avoids,
        augmented_description=augmented,
    )


def load_persona(persona_id: str, *, root: Path | None = None) -> Persona:
    """Load a single persona by id from ``root`` (default: bundled dir).

    Raises ``FileNotFoundError`` if the file is missing and
    :class:`PersonaLoadError` for malformed JSON.
    """
    base = root or PERSONAS_DIR
    path = base / f"{persona_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"persona file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PersonaLoadError(f"persona {persona_id!r}: invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise PersonaLoadError(f"persona {persona_id!r}: top-level value must be object")
    persona = _persona_from_dict(data, source=str(path))
    if persona.persona_id != persona_id:
        raise PersonaLoadError(
            f"persona file {path}: persona_id field {persona.persona_id!r} "
            f"does not match filename {persona_id!r}"
        )
    return persona


def load_all_personas(*, root: Path | None = None) -> list[Persona]:
    """Load every persona JSON in ``root``, sorted by persona_id.

    Sorted output makes manifest hashes stable across machines.
    """
    base = root or PERSONAS_DIR
    if not base.exists():
        return []
    files = sorted(p for p in base.iterdir() if p.suffix == ".json" and p.is_file())
    return [load_persona(p.stem, root=base) for p in files]


def hash_persona(persona: Persona) -> str:
    """SHA-256 of the canonical persona dict, lowercase hex.

    Stable across runs: keys sorted, no trailing whitespace, UTF-8
    encoded. Used in ``run_manifest.json`` so replay can confirm the
    persona is byte-identical.
    """
    payload = json.dumps(
        persona.to_canonical_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_personas(personas: Iterable[Persona]) -> dict[str, str]:
    """Map persona_id → SHA-256 hash, dict-ordered by persona_id."""
    return {p.persona_id: hash_persona(p) for p in sorted(personas, key=lambda x: x.persona_id)}


__all__ = [
    "PERSONAS_DIR",
    "Persona",
    "PersonaLoadError",
    "hash_persona",
    "hash_personas",
    "load_all_personas",
    "load_persona",
]
