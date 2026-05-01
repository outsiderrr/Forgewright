"""ManualImportProvider unit tests — fully isolated under tmp_path.

Covers:
  - generate() writes prompt.md / meta.json / README.md to <pending_root>/<stub>/
  - meta.json carries every required tracing field, with prompt_hash a 64-char
    sha256 hex
  - character_ref / location_ref mirror the SCHEMA_v0.2.md §2.2 rule based on
    target_type
  - returned ImageGenerationResult is shaped per ADR-014 (cost 0, no bytes,
    package path points at the per-stub dir, raw_metadata mirrors target_*)
  - estimate_cost() is always 0.0
  - empty prompt falls back to placeholder body and emits a WARNING (so
    integration tests downstream don't break before T-1.5.6 lands templates)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import pytest

from generator.image_provider import ImageGenerationResult
from generator.providers import ManualImportProvider

_BILINGUAL_PROMPT = (
    "## 中文（给作者审）\n"
    "测试角色 Vellin，中性表情。\n"
    "\n"
    "## English (for ChatGPT)\n"
    "A character sheet of Vellin, neutral expression, painterly style.\n"
)


def _make_provider(tmp_path: Path) -> ManualImportProvider:
    return ManualImportProvider(
        pending_root=tmp_path / "pending",
        prompt_template_dir=tmp_path / "templates",  # intentionally absent
    )


def test_generate_writes_full_prompt_package(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    result = provider.generate(
        prompt=_BILINGUAL_PROMPT,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
        variant_label="neutral",
    )

    package_dir = tmp_path / "pending" / "img_vellin_neutral"
    assert package_dir.is_dir()
    assert (package_dir / "prompt.md").is_file()
    assert (package_dir / "meta.json").is_file()
    assert (package_dir / "README.md").is_file()

    assert result.prompt_package_path == package_dir
    assert (package_dir / "prompt.md").read_text(encoding="utf-8") == _BILINGUAL_PROMPT


def test_meta_json_carries_full_tracing_fields(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    provider.generate(
        prompt=_BILINGUAL_PROMPT,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
        variant_label="neutral",
        n=2,
        size=(1024, 1280),
    )

    meta = json.loads(
        (tmp_path / "pending" / "img_vellin_neutral" / "meta.json").read_text(
            encoding="utf-8"
        )
    )

    assert meta["asset_id_stub"] == "img_vellin_neutral"
    assert meta["target_ref"] == "char_vellin"
    assert meta["target_type"] == "character"
    assert meta["asset_role"] == "character_sheet"
    assert meta["asset_kind"] == "character_sheet"
    assert meta["variant_label"] == "neutral"
    assert meta["source_mode"] == "manual"
    assert meta["n"] == 2
    assert meta["size"] == [1024, 1280]
    assert "created_at" in meta and meta["created_at"]
    # SCHEMA_v0.2.md §2.2 mirror-field rule: target_type=character ⇒
    # character_ref==target_ref AND location_ref==null.
    assert meta["character_ref"] == "char_vellin"
    assert meta["location_ref"] is None


def test_meta_json_prompt_hash_is_sha256_hex_of_english_segment(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    provider.generate(
        prompt=_BILINGUAL_PROMPT,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
    )
    meta = json.loads(
        (tmp_path / "pending" / "img_vellin_neutral" / "meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert re.fullmatch(r"[a-f0-9]{64}", meta["prompt_hash"])

    english_idx = _BILINGUAL_PROMPT.find("## English")
    expected = hashlib.sha256(
        _BILINGUAL_PROMPT[english_idx:].encode("utf-8")
    ).hexdigest()
    assert meta["prompt_hash"] == expected


def test_meta_mirror_fields_for_scene_target(tmp_path: Path) -> None:
    """target_type ∈ {location, scene} ⇒ location_ref==target_ref, character_ref=null."""
    provider = _make_provider(tmp_path)
    provider.generate(
        prompt=_BILINGUAL_PROMPT,
        asset_kind="scene_background",
        target_ref="scene_waystation_of_iron_oath",
        target_type="scene",
        asset_role="scene_background",
        asset_id_stub="img_waystation_dusk",
    )
    meta = json.loads(
        (tmp_path / "pending" / "img_waystation_dusk" / "meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert meta["character_ref"] is None
    assert meta["location_ref"] == "scene_waystation_of_iron_oath"


def test_returned_result_is_shaped_per_adr_014(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    result = provider.generate(
        prompt=_BILINGUAL_PROMPT,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
    )
    assert isinstance(result, ImageGenerationResult)
    assert result.mode == "manual"
    assert result.asset_id_stub == "img_vellin_neutral"
    assert result.image_bytes is None
    assert result.cost_usd == 0.0
    assert result.raw_metadata["target_ref"] == "char_vellin"
    assert result.raw_metadata["target_type"] == "character"
    assert result.raw_metadata["asset_role"] == "character_sheet"
    assert "prompt_hash" in result.raw_metadata


def test_estimate_cost_is_always_zero(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)
    assert provider.estimate_cost(n=1, size=(1024, 1024)) == 0.0
    assert provider.estimate_cost(n=4, size=(2048, 2048)) == 0.0


def test_empty_prompt_falls_back_to_placeholder_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    provider = _make_provider(tmp_path)
    with caplog.at_level(logging.WARNING, logger="generator.providers.manual_import"):
        provider.generate(
            prompt="",
            asset_kind="character_sheet",
            target_ref="char_vellin",
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub="img_vellin_placeholder",
        )

    body = (tmp_path / "pending" / "img_vellin_placeholder" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "PLACEHOLDER from T-1.5.3" in body
    assert any("placeholder" in r.message.lower() for r in caplog.records)
