"""审美预设目录——每个预设一个模块（默认 baimiao；核心层对预设中立）."""
from __future__ import annotations

from generator.prompts.style.presets import baimiao

PRESETS = {baimiao.NAME: baimiao}

__all__ = ["PRESETS", "baimiao"]
