"""Visual context assembly for image generation (T-1.5.6).

Sibling of `generator.context_assembler` but for the visual pipeline. Builds a
`VisualGenerationContext` from the aggregate ontology file
(`/state/ontology/waystation.json`) and the test-scene fixture so
`generate_character_sheet` / `generate_scene_background` can render prompts
without re-reading those files in two places.

Three rules guide every read here (ADR-006 / ADR-014 / GPT-5.5 L2 §3.1):

1. **Read-only.** This module never writes to ontology or content files. The
   only visual writes are prompt packages, which `ManualImportProvider`
   handles one layer up.
2. **Aggregate ontology shape.** vellin / corvan / aelwin live as
   `entities[]` items with `type=="character"` inside the single
   `waystation.json` file — not as separate stub files. The same applies to
   the scene anchor (`type=="scene"`).
3. **Graceful degradation.** Stage-0 ontology stubs are deliberately thin
   (often only `id` / `display_name` / `type`); missing fields must not raise.
   `generate_visual` will still render a usable prompt by falling back to
   `character_features` (B-bottom-line for ADR-014 consistency) and a
   conservative scene description.

`CharacterSheetRequirement` / `SceneBackgroundRequirement` use `target_ref` /
`target_type` as the primary keys (Round 5 U-GPT-3 / GPT-5.5 L2 §4.3); the
older `character_ref` / `location_ref` names live only as mirror fields on
`ImageAsset` (the schema layer) and are not part of this module's API.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

_logger = logging.getLogger(__name__)


_DEFAULT_ONTOLOGY_PATH = Path("state/ontology/waystation.json")
_DEFAULT_SCENE_PATH = Path("content/test_scene_v0/scene.json")
_DEFAULT_REFERENCE_DIR = Path("content/visuals/_reference")


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class VisualGenerationContext:
    """Inputs `generate_visual` hands to the prompt renderer.

    Exactly one of `character_card` / `location_card` is populated per call
    (decided by `assemble_visual_context_for_*`); the other stays None so the
    template can branch with a simple truthiness check.
    """

    character_card: dict | None = None
    location_card: dict | None = None
    style_reference_paths: list[Path] = field(default_factory=list)
    character_features: dict | None = None


@dataclass
class CharacterSheetRequirement:
    target_ref: str
    n: int
    expressions: list[str]
    poses: list[str] = field(default_factory=lambda: ["torso_up"])
    target_type: Literal["character"] = "character"


@dataclass
class SceneBackgroundRequirement:
    target_ref: str
    target_type: Literal["location", "scene"]
    n: int
    times_of_day: list[str]
    weather: list[str] | None = None


# ---------------------------------------------------------------------------
# Ontology / scene readers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # Don't blow up on a malformed ontology — Stage-0 stubs are hand-edited
        # and partial; we'd rather degrade than crash a whole batch.
        _logger.warning("visual_context: failed to read %s: %s", path, exc)
        return None


def _entities(ontology: dict | None) -> list[dict]:
    if not ontology:
        return []
    raw = ontology.get("entities")
    return raw if isinstance(raw, list) else []


def _find_entity(
    ontology: dict | None,
    target_ref: str,
    allowed_types: tuple[str, ...],
) -> dict | None:
    for entity in _entities(ontology):
        if not isinstance(entity, dict):
            continue
        if entity.get("id") == target_ref and entity.get("type") in allowed_types:
            return entity
    return None


def _list_reference_paths(reference_dir: Path) -> list[Path]:
    """Return image files in `_reference/` (PNG / WEBP / JPG).

    Per task spec we only return *paths*, never read bytes — the prompt text
    references them by path; OpenAIImageProvider (T-1.5.9) is the layer that
    decides whether to actually upload them. If the directory is missing or
    empty we return [] and let the renderer add a WARN to the prompt.
    """
    if not reference_dir.exists() or not reference_dir.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(reference_dir.iterdir()):
        if child.is_file() and child.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}:
            out.append(child)
    return out


# ---------------------------------------------------------------------------
# Public assembly entry points
# ---------------------------------------------------------------------------


def assemble_visual_context_for_character(
    target_ref: str,
    *,
    ontology_path: Path = _DEFAULT_ONTOLOGY_PATH,
    reference_dir: Path = _DEFAULT_REFERENCE_DIR,
    character_features_lookup: dict[str, dict] | None = None,
) -> VisualGenerationContext:
    """Build context for `generate_character_sheet`.

    `character_features_lookup` is injected so tests can stub it without
    importing from `generator.prompts.visual.character_features` (which would
    couple test isolation to the actual fixture data). Production callers in
    `generate_visual` pass the real CHARACTER_FEATURES mapping.
    """
    ontology = _load_json(ontology_path)
    card = _find_entity(ontology, target_ref, ("character",))
    if card is None:
        _logger.warning(
            "visual_context: no character entity %r in %s — degrading to "
            "features-only prompt",
            target_ref,
            ontology_path,
        )

    features = None
    if character_features_lookup is not None:
        features = character_features_lookup.get(target_ref)
        if features is None:
            _logger.warning(
                "visual_context: no character_features for %r — falling back "
                "to ontology card description (ADR-014 C+B consistency may "
                "degrade).",
                target_ref,
            )

    return VisualGenerationContext(
        character_card=card,
        location_card=None,
        style_reference_paths=_list_reference_paths(reference_dir),
        character_features=features,
    )


def assemble_visual_context_for_location_or_scene(
    target_ref: str,
    target_type: Literal["location", "scene"],
    *,
    ontology_path: Path = _DEFAULT_ONTOLOGY_PATH,
    scene_path: Path = _DEFAULT_SCENE_PATH,
    reference_dir: Path = _DEFAULT_REFERENCE_DIR,
) -> VisualGenerationContext:
    """Build context for `generate_scene_background`.

    Lookup order:
      1. `entities[]` in the aggregate ontology, matching id + allowed type.
      2. If not found and we're asked for a `location`, peek at the scene
         fixture and surface its `scene_anchor` as a hint.
      3. Both miss → returned card stays None; renderer falls back to a
         conservative description keyed on `target_ref`.
    """
    if target_type not in ("location", "scene"):
        # Defensive: dataclass type hints don't enforce at runtime.
        raise ValueError(
            f"target_type must be 'location' or 'scene'; got {target_type!r}"
        )

    ontology = _load_json(ontology_path)
    card = _find_entity(ontology, target_ref, ("location", "scene"))

    # review of T-1.5.6 #4.1: Stage-0 ontology stubs only carry id/display_name/
    # type, so the location/scene card alone gives GPT-Image nothing to anchor
    # on (no banners, doors, lamps, oath sigil). The narrative scene.json is
    # the de-facto visual anchor source until the ontology gains real fields,
    # so we always merge its narration in — both when the ontology card exists
    # AND when we're falling back.
    scene = _load_json(scene_path)
    scene_narration = _collect_scene_narration(scene, target_ref)

    if card is None:
        # Fixture cross-reference: if the test scene happens to anchor on
        # this target, surface a minimal pseudo-card so the prompt has at
        # least an id + display hint to work with. Real graphs will populate
        # the entity proper.
        if scene and scene.get("scene_anchor") == target_ref:
            card = {
                "id": target_ref,
                "type": "scene",
                "display_name": target_ref,
                "_source": "scene.json fallback (entity not in ontology)",
            }
        else:
            _logger.warning(
                "visual_context: no %s entity %r in %s — degrading to "
                "target_ref-only prompt",
                target_type,
                target_ref,
                ontology_path,
            )

    if card is not None and scene_narration:
        card = {**card, "scene_narration": scene_narration}

    return VisualGenerationContext(
        character_card=None,
        location_card=card,
        style_reference_paths=_list_reference_paths(reference_dir),
        character_features=None,
    )


def _collect_scene_narration(
    scene: dict | None, target_ref: str, *, max_chars: int = 2500
) -> str:
    """Concatenate every node narration whose `location_ref == target_ref`.

    Returned string is truncated at `max_chars` so an unbounded scene file
    can't blow the prompt. The narration is informational — it goes to the
    prompt under a "Scene narration excerpts" header that explicitly tells
    the model to read it for atmosphere, not to depict any character it
    mentions (the background prompt already forbids characters globally).
    """
    if not scene:
        return ""
    nodes = scene.get("nodes")
    if not isinstance(nodes, dict):
        return ""
    chunks: list[str] = []
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        if node.get("location_ref") != target_ref:
            continue
        narration = node.get("narration")
        if isinstance(narration, str) and narration.strip():
            chunks.append(narration.strip())
    joined = "\n\n".join(chunks)
    if len(joined) > max_chars:
        joined = joined[:max_chars].rstrip() + "…"
    return joined
