"""Fixed character features — the **B** half of ADR-014's C+B consistency.

Why this file exists
--------------------
GPT-Image (and ChatGPT-Plus's web UI) does not support ControlNet / LoRA, so
we cannot pin a character's identity to model weights. Instead we lean on
two things:

  - **C — Tolerance.** We accept minor variation between portraits of the
    same character (subtle pose / lighting / colour drift).
  - **B — Bottom-line.** Every prompt for a given character carries an
    explicit, opinionated description of build / eyes / hair / scars /
    outfit / props / demeanor; those anchors are what keeps multiple
    portraits readably the same person.

Anything in this file directly contradicting a character's `narration` in
the test scene (`/content/test_scene_v0/scene.json`) is a bug — the source
of truth lives in the scene, this file extends it. Inferred details
(hair / eye colour for characters whose narration didn't pin them) are
flagged in the per-character comment so the author can override later
without hunting.

Why a Python dict and not YAML
------------------------------
Stage-1.5 is the pilot fixture; only three characters need entries.
Stage-2/3 will turn this into an author-editable YAML inside the forge UI
(see ADR-015 sequencing). Premature YAML-ification now would force a
schema design pass that we have explicitly deferred (path A: do not
formalise a Character schema until the forge needs one).
"""

from __future__ import annotations


# Field shape for one character. Every key is optional from a code
# perspective; the renderer skips missing keys. Keep the *meaning* of each
# key consistent so future YAML migration is mechanical.
#
#   build     — body shape, age band, posture
#   eyes      — colour + shape descriptor
#   hair      — colour + length + how it's worn
#   scars     — visible distinguishing marks (stable across portraits)
#   outfit    — clothing (silhouette + materials + faction signals)
#   props     — held / worn items that read as identity (rings, weapons, etc.)
#   demeanor  — habitual emotional read; biases facial expression baseline
CHARACTER_FEATURES: dict[str, dict] = {
    # Vellin — heavy NPC tier (10 portraits). Features mirror the task
    # specification exactly; every detail is scene-supported (the brow scar
    # is canonical from arrival_waystation: "左眉骨上多了一道新伤"; the
    # innkeeper apron and forced smile are likewise canonical).
    "char_vellin": {
        "build": "lean, late 20s, road-worn",
        "eyes": "amber, narrow",
        "hair": "ash brown, shoulder-length, tied back loosely",
        "scars": "fresh diagonal scar over left brow, ~3cm",
        "outfit": (
            "innkeeper's leather apron over a coarse linen shirt, "
            "sleeves rolled"
        ),
        "props": (
            "worn copper rings on right hand, faint ink stains on fingers"
        ),
        "demeanor": "tense alertness behind a forced smile",
    },
    # Corvan — light NPC tier (5 portraits). Iron Oath patrol officer.
    # Scene-supported anchors: helmet (摘下头盔), military boots (马靴重重
    # 踢开), longsword on belt (右手已经按在腰间剑柄上), Iron Oath insignia
    # (断剑与铁环), shared past with the player at Lanridge / 兰岭 (so a
    # five-year-veteran read). Build / hair / eye colour are *inferred* —
    # not contradicted by narration but not pinned by it; flagged here so
    # the author can override.
    "char_corvan": {
        "build": "broad-shouldered, mid-30s, weathered (inferred)",
        "eyes": "steel grey, sharp (inferred)",
        "hair": (
            "short black, military cut, slight grey at the temples (inferred)"
        ),
        "scars": "faint old scar across the right cheek (inferred)",
        "outfit": (
            "Iron Oath patrol officer's plate-and-leather harness over a "
            "dark gambeson; broken-sword-and-iron-ring sigil stitched on "
            "the chest; heavy military boots"
        ),
        "props": (
            "longsword on a steel-buckled belt, plumed steel helmet held "
            "or set close at hand; right hand resting habitually on the "
            "sword pommel"
        ),
        "demeanor": (
            "stern composure of a five-year veteran; reads more disciplined "
            "than cruel"
        ),
    },
    # Aelwin — light NPC tier (4 portraits). Deserter from the Iron Oath
    # supply line, hiding in the shepherd's abandoned hut. Scene-supported
    # anchors: young (三年前 with player at the 陶窑山口 pottery-kiln pass,
    # so early-20s now), wearing the regiment-issue coarse linen undershirt
    # he was given at that pass (粗麻内衬), gaunt from desertion. Hair / eye
    # colour are inferred and flagged.
    "char_aelwin": {
        "build": "wiry, early-20s, gaunt from weeks of hiding",
        "eyes": "hazel, hollow with exhaustion (inferred)",
        "hair": "dirty blond, unkempt, growing out (inferred)",
        "scars": (
            "chapped lips, dirt caked along the forearms; old training "
            "calluses on the hands (inferred)"
        ),
        "outfit": (
            "regiment-issue coarse linen undershirt (the same garment he "
            "received at the 陶窑 / pottery-kiln pass three years ago), no "
            "armour; mud-stained roughspun trousers"
        ),
        "props": "no weapons or insignia — a man trying not to be a soldier",
        "demeanor": (
            "haunted, wary, hollow; the bearing of someone who has not "
            "slept fully in weeks"
        ),
    },
}


_FEATURE_LABELS = {
    "build": "Build",
    "eyes": "Eyes",
    "hair": "Hair",
    "scars": "Distinguishing marks",
    "outfit": "Outfit",
    "props": "Identifying props",
    "demeanor": "Demeanor",
}


def format_features_block(features: dict) -> str:
    """Render one character's feature dict as a stable bullet list.

    Stable ordering matters: `ManualImportProvider` hashes the English half
    of the prompt for trace, so reshuffling field order would needlessly
    invalidate hashes across runs.
    """
    lines: list[str] = []
    for key, label in _FEATURE_LABELS.items():
        value = features.get(key)
        if not value:
            continue
        lines.append(f"- **{label}:** {value}")
    return "\n".join(lines) if lines else "- (no features registered)"


def fallback_features_from_card(card: dict | None) -> dict:
    """Build a thin features dict from an ontology card when no entry exists.

    Stage-0 stubs typically only carry `id` and `display_name`, so the
    fallback is mostly a single demeanour line that names the character
    explicitly. The point is: even with no feature dict, the prompt should
    *say something* about the subject so ChatGPT doesn't invent freely.
    """
    if not card:
        return {}
    name = card.get("display_name") or card.get("id") or "(unnamed)"
    return {
        "demeanor": (
            f"{name} (no fixed-feature entry registered; render conservatively "
            "from the scene context above)"
        ),
    }
