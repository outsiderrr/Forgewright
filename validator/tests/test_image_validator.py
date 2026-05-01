"""T-1.5.4 image_validator 测试。

每个 ImageValidationError.code 至少一个 case；完美图返回空列表；config 覆盖
能改变结果（min_width 调高 → 原本通过的图变 RESOLUTION_TOO_LOW）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from PIL import Image, features

from validator import (
    ImageValidationConfig,
    ImageValidationError,
    validate_image_asset,
)


def _codes(errors: list[ImageValidationError]) -> set[str]:
    return {e.code for e in errors}


# ---------------------------------------------------------------------------
# 完美图：默认配置下空列表
# ---------------------------------------------------------------------------

def test_perfect_character_passes_default(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png", asset_kind="character_sheet"
    )
    assert errors == [], f"expected empty list, got {errors}"


def test_perfect_background_passes_default(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "perfect_background.png", asset_kind="scene_background"
    )
    assert errors == [], f"expected empty list, got {errors}"


@pytest.mark.skipif(not features.check("webp"), reason="Pillow built without WebP support")
def test_perfect_webp_background_passes_default(fixtures_dir: Path):
    """WebP 是 allowed_formats 默认的另一半；锁住 magic-byte 判断 + 默认配置兼容。"""
    errors = validate_image_asset(
        fixtures_dir / "perfect_background.webp", asset_kind="scene_background"
    )
    assert errors == [], f"expected empty list, got {errors}"


# ---------------------------------------------------------------------------
# 每个 code 至少一个 case
# ---------------------------------------------------------------------------

def test_file_not_found(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "does_not_exist.png", asset_kind="character_sheet"
    )
    assert _codes(errors) == {"FILE_NOT_FOUND"}
    assert errors[0].severity == "error"


def test_format_not_allowed_via_magic_bytes(fixtures_dir: Path):
    """jpeg 内容伪装为 .png 扩展名 → magic bytes 校验抓出。"""
    errors = validate_image_asset(
        fixtures_dir / "jpeg_disguised.png", asset_kind="scene_background"
    )
    assert "FORMAT_NOT_ALLOWED" in _codes(errors)
    assert any(
        e.code == "FORMAT_NOT_ALLOWED" and e.severity == "error" for e in errors
    )


def test_format_not_allowed_via_extension(fixtures_dir: Path):
    """PNG 内容但扩展名 .jpg → 即便 magic bytes 合法，扩展名也不在 allowed_formats，应拒收（SCHEMA_v0.2 §2 file_path pattern 只允许 .png / .webp）。"""
    errors = validate_image_asset(
        fixtures_dir / "wrong_extension.jpg", asset_kind="character_sheet"
    )
    assert "FORMAT_NOT_ALLOWED" in _codes(errors)
    assert any(
        e.code == "FORMAT_NOT_ALLOWED" and e.severity == "error" for e in errors
    )


def test_file_size_exceeded(fixtures_dir: Path):
    cfg = ImageValidationConfig(max_file_size_bytes=128)  # 128 bytes 任意 PNG 都超
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png",
        asset_kind="character_sheet",
        config=cfg,
    )
    assert "FILE_SIZE_EXCEEDED" in _codes(errors)


def test_resolution_too_low(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "small_character.png", asset_kind="character_sheet"
    )
    assert "RESOLUTION_TOO_LOW" in _codes(errors)


def test_resolution_too_low_with_too_small(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "too_small.png", asset_kind="character_sheet"
    )
    assert "RESOLUTION_TOO_LOW" in _codes(errors)


def test_resolution_too_high(fixtures_dir: Path):
    cfg = ImageValidationConfig(max_width=512, max_height=512)
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png",
        asset_kind="character_sheet",
        config=cfg,
    )
    assert "RESOLUTION_TOO_HIGH" in _codes(errors)


def test_decompression_bomb_does_not_crash(
    fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    """畸形超大 PNG 不能让 validator 抛 DecompressionBombError；必须返回 RESOLUTION_TOO_HIGH（R8 机械层硬卡）。"""
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png", asset_kind="character_sheet"
    )
    assert "RESOLUTION_TOO_HIGH" in _codes(errors)
    assert all(
        e.severity == "error"
        for e in errors
        if e.code == "RESOLUTION_TOO_HIGH"
    )


def test_alpha_required(fixtures_dir: Path):
    """RGB 图（无 alpha）当作 character_sheet 应触发 ALPHA_REQUIRED。"""
    errors = validate_image_asset(
        fixtures_dir / "perfect_background.png", asset_kind="character_sheet"
    )
    assert "ALPHA_REQUIRED" in _codes(errors)


def test_alpha_forbidden(fixtures_dir: Path):
    """RGBA 图当作 scene_background 应触发 ALPHA_FORBIDDEN。"""
    errors = validate_image_asset(
        fixtures_dir / "alpha_in_bg.png", asset_kind="scene_background"
    )
    assert "ALPHA_FORBIDDEN" in _codes(errors)


def test_aspect_ratio_out_of_range(fixtures_dir: Path):
    """perfect_character 是 1024x1280（ratio=0.8）；要求 [1.0, 2.0] 则警告。"""
    cfg = ImageValidationConfig(require_aspect_ratio=(1.0, 2.0))
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png",
        asset_kind="character_sheet",
        config=cfg,
    )
    assert "ASPECT_RATIO_OUT_OF_RANGE" in _codes(errors)
    assert all(
        e.severity == "warning"
        for e in errors
        if e.code == "ASPECT_RATIO_OUT_OF_RANGE"
    )


def test_aspect_ratio_default_not_checked(fixtures_dir: Path):
    """require_aspect_ratio=None（默认）→ 不校验。"""
    errors = validate_image_asset(
        fixtures_dir / "perfect_character.png", asset_kind="character_sheet"
    )
    assert "ASPECT_RATIO_OUT_OF_RANGE" not in _codes(errors)


def test_exif_present(fixtures_dir: Path):
    errors = validate_image_asset(
        fixtures_dir / "with_exif.png", asset_kind="character_sheet"
    )
    assert "EXIF_PRESENT" in _codes(errors)
    assert all(
        e.severity == "warning" for e in errors if e.code == "EXIF_PRESENT"
    )


# ---------------------------------------------------------------------------
# Config 覆盖：原本通过的图随 min_width 调高变 RESOLUTION_TOO_LOW
# ---------------------------------------------------------------------------

def test_config_override_changes_outcome(fixtures_dir: Path):
    path = fixtures_dir / "perfect_character.png"
    assert validate_image_asset(path, asset_kind="character_sheet") == []
    cfg = ImageValidationConfig(min_width=2048)
    errors = validate_image_asset(path, asset_kind="character_sheet", config=cfg)
    assert "RESOLUTION_TOO_LOW" in _codes(errors)


# ---------------------------------------------------------------------------
# 多错误聚合：不短路
# ---------------------------------------------------------------------------

def test_multiple_errors_aggregated(fixtures_dir: Path):
    """too_small RGBA 当 scene_background：触发 RESOLUTION_TOO_LOW + ALPHA_FORBIDDEN。"""
    errors = validate_image_asset(
        fixtures_dir / "too_small.png", asset_kind="scene_background"
    )
    codes = _codes(errors)
    assert "RESOLUTION_TOO_LOW" in codes
    assert "ALPHA_FORBIDDEN" in codes


# ---------------------------------------------------------------------------
# Severity 分布断言
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code,expected_severity",
    [
        ("FILE_NOT_FOUND", "error"),
        ("FORMAT_NOT_ALLOWED", "error"),
        ("FILE_SIZE_EXCEEDED", "error"),
        ("RESOLUTION_TOO_LOW", "error"),
        ("RESOLUTION_TOO_HIGH", "error"),
        ("ALPHA_REQUIRED", "error"),
        ("ALPHA_FORBIDDEN", "error"),
        ("ASPECT_RATIO_OUT_OF_RANGE", "warning"),
        ("EXIF_PRESENT", "warning"),
    ],
)
def test_code_severity_matrix(code: str, expected_severity: str, fixtures_dir: Path):
    """每个 code 的 severity 必须与任务表一致——抗未来误改。"""
    code_to_call = {
        "FILE_NOT_FOUND": lambda: validate_image_asset(
            fixtures_dir / "nope.png", asset_kind="character_sheet"
        ),
        "FORMAT_NOT_ALLOWED": lambda: validate_image_asset(
            fixtures_dir / "jpeg_disguised.png", asset_kind="scene_background"
        ),
        "FILE_SIZE_EXCEEDED": lambda: validate_image_asset(
            fixtures_dir / "perfect_character.png",
            asset_kind="character_sheet",
            config=ImageValidationConfig(max_file_size_bytes=64),
        ),
        "RESOLUTION_TOO_LOW": lambda: validate_image_asset(
            fixtures_dir / "small_character.png", asset_kind="character_sheet"
        ),
        "RESOLUTION_TOO_HIGH": lambda: validate_image_asset(
            fixtures_dir / "perfect_character.png",
            asset_kind="character_sheet",
            config=ImageValidationConfig(max_width=512, max_height=512),
        ),
        "ALPHA_REQUIRED": lambda: validate_image_asset(
            fixtures_dir / "perfect_background.png", asset_kind="character_sheet"
        ),
        "ALPHA_FORBIDDEN": lambda: validate_image_asset(
            fixtures_dir / "alpha_in_bg.png", asset_kind="scene_background"
        ),
        "ASPECT_RATIO_OUT_OF_RANGE": lambda: validate_image_asset(
            fixtures_dir / "perfect_character.png",
            asset_kind="character_sheet",
            config=ImageValidationConfig(require_aspect_ratio=(1.0, 2.0)),
        ),
        "EXIF_PRESENT": lambda: validate_image_asset(
            fixtures_dir / "with_exif.png", asset_kind="character_sheet"
        ),
    }
    errors = code_to_call[code]()
    matched = [e for e in errors if e.code == code]
    assert matched, f"{code} not produced; got codes={_codes(errors)}"
    assert all(e.severity == expected_severity for e in matched)
