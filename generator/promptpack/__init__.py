"""generator/promptpack —— 写作提示词包载体（ADR-039 P-A / P-B）.

本包是"写作提示词包转向"（ADR-039：不自建正文生成，编剧 BYOM 写正文、
我们守结构与验收）的公共地基（T-3P-0 浇筑）：

  - format_spec.py：回流格式契约 v1 单一真相源（标签语法常量 + 节点类别必交
    key 表 + E1-E8 硬报错分类 + CLI 退出码三态）。只定义契约，不含解析器。
  - io.py：IO envelope 冻结 + 共享 loader（load_design_artifact /
    load_scene_spec）。P-A / P-B 只准经 loader 读输入。

后续任务在本包内落地（消费本地基，不改契约）：
  - T-3P-1（P-A 渲染器）：render_pack.py —— design.json → 整场写作提示词包；
  - T-3P-2（P-B 回流合并）：ingest.py —— 编剧回流文本 → 解析 + node_id/序号
    对齐 + 确定性合并 + 硬报错退回单。

CLI 约定（T-3P-0 定死）：v1 各工具用**独立模块入口**
（`python -m generator.promptpack.render_pack` / `python -m generator.promptpack.ingest`），
**不建共享 `__main__.py`**（P1 两任务并行不碰同一文件、可独立 revert；统一分发
入口留给 T-3P-3 接线时视需要加）。退出码三态 = EXIT_OK(0) / EXIT_REJECTED(1) /
EXIT_USAGE(2)，见 format_spec。

边界：只在 /generator（开发期）；不碰 /schema /engine（运行时永远无 LLM）。
"""
from __future__ import annotations

from generator.promptpack.format_spec import (
    ERRORS,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_USAGE,
    NODE_CATEGORY_KEYS,
    ErrorSpec,
)
from generator.promptpack.io import (
    PromptpackInputError,
    load_design_artifact,
    load_scene_spec,
)

__all__ = [
    "ERRORS",
    "ErrorSpec",
    "EXIT_OK",
    "EXIT_REJECTED",
    "EXIT_USAGE",
    "NODE_CATEGORY_KEYS",
    "PromptpackInputError",
    "load_design_artifact",
    "load_scene_spec",
]
