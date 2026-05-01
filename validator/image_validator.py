"""第四层：视觉资产机械预检（T-1.5.4）。

只覆盖**可数值化机械维度**：分辨率、格式（含 magic bytes）、文件大小、
alpha 通道（按 asset_kind 反向约束）、长宽比（可选）、EXIF 元数据。语义判
断（"是否含可识别角色 / 是否符合本体卡"）由 T-1.5.8 视觉 AI 判官负责
（STAGE_1_ACCEPTANCE §4 R8 教训：机械可检测维度不让 LLM 评）。

接口：`validate_image_asset(path, *, asset_kind, config) -> list[ImageValidationError]`。
空列表 = 通过；含 severity="error" 项 = 不可入库；severity="warning" = 可
入库但作者审阅时应注意。

不与 schema_validator / graph_validator / consistency_validator 共享 Issue
类型——本层针对**单个图像文件**而非 graph dict，定位单位是文件路径，与三层
JSON 校验体系并行。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, UnidentifiedImageError

Severity = Literal["error", "warning"]
AssetKind = Literal["character_sheet", "scene_background"]


@dataclass(frozen=True)
class ImageValidationError:
    code: str
    message: str
    severity: Severity


@dataclass(frozen=True)
class ImageValidationConfig:
    min_width: int = 768
    max_width: int = 4096
    min_height: int = 768
    max_height: int = 4096
    allowed_formats: tuple[str, ...] = ("png", "webp")
    max_file_size_bytes: int = 8 * 1024 * 1024
    require_alpha_for_character: bool = True
    forbid_alpha_for_background: bool = True
    require_aspect_ratio: tuple[float, float] | None = None


# magic byte signatures keyed by canonical short format name returned by PIL.
# Used to detect file-name forgery (e.g. JPEG renamed to .png).
_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),  # "RIFF????WEBP" — 4-byte size between; checked separately
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "bmp": (b"BM",),
    "tiff": (b"II*\x00", b"MM\x00*"),
}


def _detect_format_by_magic(path: Path) -> str | None:
    """读前 12 bytes 推断格式，不信扩展名。返回 'png' / 'webp' / 'jpeg' / ... 或 None。"""
    try:
        with path.open("rb") as f:
            head = f.read(12)
    except OSError:
        return None
    if head.startswith(_MAGIC_BYTES["png"][0]):
        return "png"
    if head.startswith(_MAGIC_BYTES["webp"][0]) and len(head) >= 12 and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(_MAGIC_BYTES["jpeg"][0]):
        return "jpeg"
    for sig in _MAGIC_BYTES["gif"]:
        if head.startswith(sig):
            return "gif"
    if head.startswith(_MAGIC_BYTES["bmp"][0]):
        return "bmp"
    for sig in _MAGIC_BYTES["tiff"]:
        if head.startswith(sig):
            return "tiff"
    return None


def validate_image_asset(
    image_path: Path,
    *,
    asset_kind: AssetKind,
    config: ImageValidationConfig | None = None,
) -> list[ImageValidationError]:
    cfg = config or ImageValidationConfig()
    errors: list[ImageValidationError] = []

    if not image_path.exists() or not image_path.is_file():
        return [
            ImageValidationError(
                code="FILE_NOT_FOUND",
                message=f"image_path {str(image_path)!r} does not exist or is not a regular file",
                severity="error",
            )
        ]

    file_size = image_path.stat().st_size
    if file_size > cfg.max_file_size_bytes:
        errors.append(
            ImageValidationError(
                code="FILE_SIZE_EXCEEDED",
                message=(
                    f"file size {file_size} bytes exceeds max "
                    f"{cfg.max_file_size_bytes} bytes"
                ),
                severity="error",
            )
        )

    detected = _detect_format_by_magic(image_path)
    if detected not in cfg.allowed_formats:
        errors.append(
            ImageValidationError(
                code="FORMAT_NOT_ALLOWED",
                message=(
                    f"detected format {detected!r} (from magic bytes) not in allowed "
                    f"formats {cfg.allowed_formats}; file extension is "
                    f"{image_path.suffix.lower()!r}"
                ),
                severity="error",
            )
        )
        # Magic bytes lie about the format → don't trust extension; still try to
        # open with Pillow to surface dimension/alpha errors, but skip if it fails.

    try:
        with Image.open(image_path) as img:
            img.load()
            width, height = img.size
            mode = img.mode
            exif = img.getexif()
    except (UnidentifiedImageError, OSError) as exc:
        # Pillow refuses the file outright; FORMAT_NOT_ALLOWED above already
        # signalled the format issue if applicable. Surface a single error so
        # downstream sees actionable info even if magic-byte path passed.
        if not any(e.code == "FORMAT_NOT_ALLOWED" for e in errors):
            errors.append(
                ImageValidationError(
                    code="FORMAT_NOT_ALLOWED",
                    message=f"PIL cannot decode {image_path.name}: {exc}",
                    severity="error",
                )
            )
        return errors

    if width < cfg.min_width or height < cfg.min_height:
        errors.append(
            ImageValidationError(
                code="RESOLUTION_TOO_LOW",
                message=(
                    f"resolution {width}x{height} is below minimum "
                    f"{cfg.min_width}x{cfg.min_height}"
                ),
                severity="error",
            )
        )
    if width > cfg.max_width or height > cfg.max_height:
        errors.append(
            ImageValidationError(
                code="RESOLUTION_TOO_HIGH",
                message=(
                    f"resolution {width}x{height} exceeds maximum "
                    f"{cfg.max_width}x{cfg.max_height}"
                ),
                severity="error",
            )
        )

    has_alpha = "A" in mode
    if asset_kind == "character_sheet" and cfg.require_alpha_for_character and not has_alpha:
        errors.append(
            ImageValidationError(
                code="ALPHA_REQUIRED",
                message=(
                    f"asset_kind=character_sheet requires alpha channel but PIL "
                    f"mode is {mode!r}"
                ),
                severity="error",
            )
        )
    if asset_kind == "scene_background" and cfg.forbid_alpha_for_background and has_alpha:
        errors.append(
            ImageValidationError(
                code="ALPHA_FORBIDDEN",
                message=(
                    f"asset_kind=scene_background must not carry alpha channel "
                    f"but PIL mode is {mode!r}"
                ),
                severity="error",
            )
        )

    if cfg.require_aspect_ratio is not None and height > 0:
        ratio = width / height
        lo, hi = cfg.require_aspect_ratio
        if ratio < lo or ratio > hi:
            errors.append(
                ImageValidationError(
                    code="ASPECT_RATIO_OUT_OF_RANGE",
                    message=(
                        f"aspect ratio {ratio:.3f} ({width}x{height}) outside "
                        f"required range [{lo}, {hi}]"
                    ),
                    severity="warning",
                )
            )

    if exif is not None and len(exif) > 0:
        errors.append(
            ImageValidationError(
                code="EXIF_PRESENT",
                message=(
                    f"image carries EXIF/IPTC metadata ({len(exif)} tag(s)); "
                    f"strip before publishing to avoid privacy / size leak"
                ),
                severity="warning",
            )
        )

    return errors


__all__ = [
    "ImageValidationConfig",
    "ImageValidationError",
    "validate_image_asset",
]
