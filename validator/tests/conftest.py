"""Pillow-generated image fixtures for image_validator tests (T-1.5.4).

测试图**现场生成**到 tmp_path_factory 共享目录，不提交二进制；避免仓库膨胀（任务
提示词"不要把测试图作为二进制文件提交到 git"）。fixture 命名遵循 GPT-5.5 L2
critique 5.1 修补：`small_character.png`（故意小尺寸触发 RESOLUTION_TOO_LOW）/
`perfect_character.png`（默认配置真正合格）/ `perfect_background.png`（与 character
对称）。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


def _save_png(path: Path, size: tuple[int, int], mode: str) -> Path:
    img = Image.new(mode, size, color=(0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
    img.save(path, format="PNG")
    return path


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """生成全部图像 fixture 到一个会话级 tmp 目录，返回路径。"""
    base = tmp_path_factory.mktemp("image_fixtures")

    _save_png(base / "small_character.png", (512, 768), "RGBA")
    _save_png(base / "perfect_character.png", (1024, 1280), "RGBA")
    _save_png(base / "perfect_background.png", (1024, 1024), "RGB")
    _save_png(base / "too_small.png", (100, 100), "RGBA")
    _save_png(base / "alpha_in_bg.png", (1024, 1024), "RGBA")

    # JPEG content with .png file extension — magic-byte forgery probe.
    jpeg_path = base / "jpeg_disguised.png"
    Image.new("RGB", (1024, 1024), color=(255, 255, 255)).save(
        jpeg_path, format="JPEG"
    )

    # PNG with EXIF — Pillow's Exif object lets us inject a tag before saving.
    exif_path = base / "with_exif.png"
    img_exif = Image.new("RGBA", (1024, 1280), color=(0, 0, 0, 0))
    exif = img_exif.getexif()
    exif[0x010F] = "Forgewright Test"  # Make tag
    img_exif.save(exif_path, format="PNG", exif=exif.tobytes())

    return base
