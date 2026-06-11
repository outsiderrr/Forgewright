"""generator/multipass —— 结构层正式生成引擎（多 pass + 分拍 + 动态拓扑）.

作者批准的设计：generator/experiments/multipass_structure/DESIGN_2026-06-10_formal_landing.md
决策依据：ADR-038（分拍节点图）+ Phase 1 FINDINGS（多 pass 结构子集 +0.75）。

管线（每场景一次运行，全部是小调用——超时应对架构化，DESIGN §5）：
  scene_spec → ①契约 → ②拓扑规划（动态拓扑；失败回退半固定脚手架）
            → ③逐 choice 节点骨架 → ④逐 choice 节点正文
            → ⑤逐 beats 链分拍（reveals 自动分块）→ ⑥end 收束微调用
            → ⑦确定性组装（0 LLM；机械字段由代码填——LLM 不写状态）
            → ⑧validator（schema + mechanical + AP-7/8/10 程序化检测）
            → 产物：scene.json / design.json / scene.md / metrics.json

与 system.py 单 pass 路径**并存**（不同工位：那边是"给定骨架填单节点正文"，
本引擎是"从场景 spec 设计 + 写整场"）；本引擎 = 结构层默认生成路径。

边界：只在 /generator；不改 schema（ADR-038）；validator 只读调用。
"""
from __future__ import annotations

from generator.multipass.engine import MultipassSceneResult, SceneRunConfig, run_multipass_scene

__all__ = ["MultipassSceneResult", "SceneRunConfig", "run_multipass_scene"]
