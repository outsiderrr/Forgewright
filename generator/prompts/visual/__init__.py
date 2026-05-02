"""Visual prompt templates for the Stage-1.5 image pipeline (T-1.5.6).

What lives here:

- `system_character.md` / `system_background.md` — bilingual prompt
  templates. Per ADR-014's C+B consistency strategy, each template carries
  the style baseline, fixed-feature block (injected from
  `character_features.CHARACTER_FEATURES`), and negative tail in one file
  with **two segments**: a `## 中文（给作者审）` block for the author to
  scan and a `## English (for ChatGPT)` block that GPT-Image actually sees.
  Splitting them across files would force the author to flip back and forth
  to confirm Chinese intent matches English output, which is the whole point
  of the bilingual layout.

- `character_features.py` — the CHARACTER_FEATURES dict. Stage-1.5 keeps
  this as a Python dict on purpose (not YAML, not Schema-formalised); the
  Stage-2/3 forge UI will move it into a YAML the author edits in-app, but
  that ergonomics work is out of scope here.

- `load_template(name)` / `render_template(...)` — small helpers so
  `generate_visual` doesn't have to know about template paths or
  placeholder syntax.

The substitution syntax is intentionally trivial — `{{TOKEN}}` markers
replaced with `str.replace`, no Jinja or f-string traps. We control both
ends of the string and there are no user-supplied template fragments, so a
templating engine would be over-engineering.
"""

from __future__ import annotations

from pathlib import Path

from generator.prompts.visual.character_features import (
    CHARACTER_FEATURES,
    fallback_features_from_card,
    format_features_block,
)

_TEMPLATE_DIR = Path(__file__).parent

CHARACTER_TEMPLATE = "system_character.md"
BACKGROUND_TEMPLATE = "system_background.md"


def load_template(name: str) -> str:
    """Read a bundled `.md` template by filename (e.g. `system_character.md`)."""
    path = _TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def render_template(template: str, substitutions: dict[str, str]) -> str:
    """Replace every `{{KEY}}` token in `template` with `substitutions[KEY]`.

    Tokens missing from `substitutions` are left in place — that surfaces a
    rendering bug as visible text in the prompt instead of swallowing it
    silently.
    """
    out = template
    for key, value in substitutions.items():
        out = out.replace("{{" + key + "}}", value)
    return out


__all__ = [
    "CHARACTER_FEATURES",
    "CHARACTER_TEMPLATE",
    "BACKGROUND_TEMPLATE",
    "fallback_features_from_card",
    "format_features_block",
    "load_template",
    "render_template",
]
