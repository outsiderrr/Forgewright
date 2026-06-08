"""多 pass 节点生成原型（multi-pass node generation prototype）— Phase 1 结构层.

design-first 生成从"一个大 prompt"改造成 **2 遍**（参考 StoryWriter plan-compose-write）：

  Pass 1（pass1_skeleton）：从场景 spec **设计**互动结构
      → Scene Contract + 4 节点 Interaction Skeleton
      → **只带结构规则**（节点功能分化 / choice pressure / 线索分层）
      → **0 条文风/AP 规则**

  Pass 2（pass2_prose）：把骨架当固定输入，**逐节点**写正文
      → narration + NPC dialogue + 玩家选项第一人称文本
      → **带瘦身后的文风规则**（AP-1~6 + AP-9；去掉 AP-7/8/10——validator 程序化抓）
      → 带**历史压缩**输入（前文已揭露线索 + 已用选项角度），避免节点间重复

边界（CLAUDE.md 规则 2 / 3 + generator/CLAUDE.md）：
  本子包是**隔离原型**，只在 /generator 内。**不修改**现有
  system.py / anti_pattern_blacklist.py / role_rules.py 及其测试（T-3Y-1 定型代码）。
  信号正向后再单独提正式落改。
"""
from __future__ import annotations

from generator.prompts.node.multipass.pass1_skeleton import (
    NODE_FUNCTIONS,
    PASS1_SKELETON_SYSTEM,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass1_node_schema,
    build_pass1_node_user_prompt,
    build_pass1_schema,
    build_pass1_user_prompt,
)
from generator.prompts.node.multipass.pass2_prose import (
    PASS2_PROSE_SYSTEM,
    SLIMMED_AP_KEEP,
    build_pass2_schema,
    build_pass2_user_prompt,
    slimmed_anti_patterns,
)

__all__ = [
    "NODE_FUNCTIONS",
    "PASS1_SKELETON_SYSTEM",
    "build_pass1_schema",
    "build_pass1_user_prompt",
    "build_pass1_contract_schema",
    "build_pass1_contract_user_prompt",
    "build_pass1_node_schema",
    "build_pass1_node_user_prompt",
    "PASS2_PROSE_SYSTEM",
    "SLIMMED_AP_KEEP",
    "build_pass2_schema",
    "build_pass2_user_prompt",
    "slimmed_anti_patterns",
]
