"""ManualImportProvider — ADR-014 manual mode (the dev-default path).

Per ADR-014: this provider does NOT call any external API. It writes a
"prompt package" (`prompt.md` + `meta.json` + `README.md`) to
`<pending_root>/<asset_id_stub>/` so the author can paste the English prompt
into chatgpt.com, generate an image manually, drop it into the same
directory, and let `image_import` (T-1.5.7) ingest it.

The Protocol-level signature carries `target_ref` / `target_type` /
`asset_role` / `asset_id_stub` end-to-end (see `image_provider.py` docstring);
this provider mirrors them into `meta.json` so the import CLI doesn't have
to guess.

Out-of-scope here (handled by later T-1.5.x tasks):
    - Budget tracking (T-1.5.5 / T-1.5.6)
    - The substantive prompt template content (T-1.5.6 fills
      `generator/prompts/visual/*.md`; this task only wires in a placeholder
      so integration tests downstream don't block on missing files)
    - Anything OpenAI- or network-related (T-1.5.9 OpenAIImageProvider)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

from generator.image_provider import ImageGenerationResult

_logger = logging.getLogger(__name__)

_DEFAULT_PENDING_ROOT = Path("content/visuals/_pending")
_DEFAULT_PROMPT_TEMPLATE_DIR = Path("generator/prompts/visual")

_PLACEHOLDER_PROMPT_BODY = (
    "[PLACEHOLDER from T-1.5.3 — T-1.5.6 will fill]\n"
    "\n"
    "## 中文（给作者审）\n"
    "（T-1.5.6 will fill in the substantive Chinese prompt for review.）\n"
    "\n"
    "## English (for ChatGPT)\n"
    "(T-1.5.6 will fill in the substantive English prompt for ChatGPT.)\n"
)


def _english_segment(prompt_text: str) -> str:
    """Return the English half of a bilingual prompt for hashing.

    Convention (matches the placeholder + T-1.5.6 templates): the English
    half is everything after a `## English` heading. If no such heading is
    present (e.g. a single-language prompt), hash the whole text — the hash
    is for trace, not security, so a stable rule is enough.
    """
    marker = "## English"
    idx = prompt_text.find(marker)
    if idx == -1:
        return prompt_text
    return prompt_text[idx:]


class ManualImportProvider:
    """Writes a prompt package; no network calls; cost is always 0.

    Constructor args have safe defaults (`content/visuals/_pending` and
    `generator/prompts/visual`) so the common path is `ManualImportProvider()`.
    Tests override `pending_root` with `tmp_path` for isolation.
    """

    def __init__(
        self,
        pending_root: Path | None = None,
        prompt_template_dir: Path | None = None,
    ) -> None:
        self.pending_root = (
            pending_root if pending_root is not None else _DEFAULT_PENDING_ROOT
        )
        self.prompt_template_dir = (
            prompt_template_dir
            if prompt_template_dir is not None
            else _DEFAULT_PROMPT_TEMPLATE_DIR
        )

    def generate(
        self,
        *,
        prompt: str,
        ref_images: list[Path] | None = None,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        asset_kind: Literal["character_sheet", "scene_background"],
        target_ref: str,
        target_type: Literal["character", "location", "scene"],
        asset_role: Literal["character_sheet", "scene_background"],
        asset_id_stub: str,
        variant_label: str = "",
    ) -> ImageGenerationResult:
        # If the caller passed an empty/missing prompt, fall back to the
        # placeholder. T-1.5.6 will plug in the real templates; until then we
        # need *something* on disk so downstream integration tests (and the
        # author's manual workflow) aren't blocked. Logged at WARNING per the
        # task spec so it's visible but not fatal.
        if not prompt or prompt.strip() == "":
            _logger.warning(
                "ManualImportProvider: empty prompt for asset_id_stub=%s; "
                "writing placeholder body (T-1.5.6 will replace).",
                asset_id_stub,
            )
            prompt_body = _PLACEHOLDER_PROMPT_BODY
        else:
            prompt_body = prompt

        package_dir = self.pending_root / asset_id_stub
        package_dir.mkdir(parents=True, exist_ok=True)

        prompt_md_path = package_dir / "prompt.md"
        prompt_md_path.write_text(prompt_body, encoding="utf-8")

        # sha256 of the English segment — for trace, not security.
        prompt_hash = hashlib.sha256(
            _english_segment(prompt_body).encode("utf-8")
        ).hexdigest()

        # SCHEMA_v0.2.md §2.2 mirror-field consistency: character_ref / location_ref
        # are filled depending on target_type so image_import can write a
        # schema-valid ImageAsset without re-deriving the rule.
        character_ref = target_ref if target_type == "character" else None
        location_ref = target_ref if target_type in ("location", "scene") else None

        meta = {
            "asset_id_stub": asset_id_stub,
            "target_ref": target_ref,
            "target_type": target_type,
            "asset_role": asset_role,
            "asset_kind": asset_kind,
            "variant_label": variant_label,
            "size": list(size),
            "n": n,
            "source_mode": "manual",
            "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "prompt_hash": prompt_hash,
            "character_ref": character_ref,
            "location_ref": location_ref,
        }
        (package_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        readme = (
            f"# {asset_id_stub} — manual generation steps\n"
            "\n"
            "1. Open `prompt.md`; copy the **English** segment.\n"
            "2. Paste it into chatgpt.com (GPT-Image) and generate.\n"
            f"3. Download the chosen image to this directory as "
            f"`{asset_id_stub}.png`.\n"
            "4. Run:\n"
            "\n"
            "   ```\n"
            f"   python -m generator.image_import --asset-id {asset_id_stub}\n"
            "   ```\n"
            "\n"
            "The import CLI (T-1.5.7) will validate the file, move it to\n"
            "`/content/visuals/<target_ref>/`, and update the manifest.\n"
        )
        (package_dir / "README.md").write_text(readme, encoding="utf-8")

        return ImageGenerationResult(
            mode="manual",
            asset_id_stub=asset_id_stub,
            image_bytes=None,
            prompt_package_path=package_dir,
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
                "prompt_hash": prompt_hash,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        # ADR-014: manual mode is free at the margin (ChatGPT Plus subscription
        # is sunk cost). Always 0; budget layer still records the call for
        # uniformity.
        return 0.0
