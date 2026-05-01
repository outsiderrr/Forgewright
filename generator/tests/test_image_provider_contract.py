"""Contract tests for the ImageProvider Protocol — no real API calls.

Verifies:
1. A hand-rolled FakeImageProvider passes `isinstance(..., ImageProvider)`
   (Protocol is `runtime_checkable`).
2. ManualImportProvider satisfies the same structural check.
3. ImageGenerationResult exposes the documented fields.
"""

from __future__ import annotations

from pathlib import Path

from generator.image_provider import ImageGenerationResult, ImageProvider
from generator.providers import ManualImportProvider


class FakeImageProvider:
    """In-memory stand-in for tests. Returns a fixed ImageGenerationResult."""

    def generate(
        self,
        *,
        prompt: str,
        ref_images: list[Path] | None = None,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        asset_kind: str,
        target_ref: str,
        target_type: str,
        asset_role: str,
        asset_id_stub: str,
        variant_label: str = "",
    ) -> ImageGenerationResult:
        return ImageGenerationResult(
            mode="manual",
            asset_id_stub=asset_id_stub,
            image_bytes=None,
            prompt_package_path=None,
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        return 0.0


def test_fake_image_provider_satisfies_protocol() -> None:
    fake = FakeImageProvider()
    assert isinstance(fake, ImageProvider)


def test_manual_import_provider_satisfies_protocol() -> None:
    provider = ManualImportProvider()
    assert isinstance(provider, ImageProvider)


def test_fake_image_provider_returns_well_formed_result() -> None:
    fake = FakeImageProvider()
    result = fake.generate(
        prompt="hi",
        asset_kind="character_sheet",
        target_ref="char_test",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_test_neutral",
    )
    assert isinstance(result, ImageGenerationResult)
    assert result.mode == "manual"
    assert result.asset_id_stub == "img_test_neutral"
    assert result.image_bytes is None
    assert result.cost_usd == 0.0
    assert result.raw_metadata["target_ref"] == "char_test"


def test_fake_image_provider_estimate_cost_is_float() -> None:
    fake = FakeImageProvider()
    cost = fake.estimate_cost(n=1, size=(1024, 1024))
    assert isinstance(cost, float)
