"""多 pass 节点生成 prompt（multi-pass node generation prompts）— 结构层正式路径.

design-first 生成从"一个大 prompt"改造成 **2 遍**（参考 StoryWriter plan-compose-write）：

  Pass 1（pass1_skeleton）：从场景 spec **设计**互动结构
      → Scene Contract + 4 节点 Interaction Skeleton
      → **只带结构规则**（节点功能分化 / choice pressure / 线索分层）
      → **0 条文风/AP 规则**

  Pass 2（pass2_prose）：把骨架当固定输入，**逐节点**写正文
      → narration + NPC dialogue + 玩家选项第一人称文本
      → **带瘦身后的文风规则**（AP-1~6 + AP-9；去掉 AP-7/8/10——validator 程序化抓）
      → 带**历史压缩**输入（前文已揭露线索 + 已用选项角度），避免节点间重复

状态（2026-06-10 正式落地，作者批准的设计见
generator/experiments/multipass_structure/DESIGN_2026-06-10_formal_landing.md）：
  本子包已从"隔离原型"升格为 **generator 结构层正式生成路径**的 prompt 层，
  由 generator/multipass/ 引擎编排（含动态拓扑 pass）。
  system.py 单 pass 路径**并存**（不同工位："给定骨架填单节点正文"）。
"""
from __future__ import annotations

from generator.prompts.node.multipass.pass1_skeleton import (
    NODE_FUNCTIONS,
    PASS1_SKELETON_SYSTEM,
    PASS1_SKELETON_SYSTEM_DYNAMIC,
    build_dynamic_node_schema,
    build_dynamic_node_user_prompt,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass1_node_schema,
    build_pass1_node_user_prompt,
    build_pass1_schema,
    build_pass1_user_prompt,
)
from generator.prompts.node.multipass.pass2_prose import (
    PASS2_PROSE_SYSTEM,
    build_end_prose_schema,
    build_end_prose_user_prompt,
    build_pass2_schema,
    build_pass2_user_prompt,
)
from generator.prompts.node.multipass.topology import (
    TOPOLOGY_SYSTEM,
    build_topology_schema,
    build_topology_user_prompt,
)

__all__ = [
    "NODE_FUNCTIONS",
    "PASS1_SKELETON_SYSTEM",
    "PASS1_SKELETON_SYSTEM_DYNAMIC",
    "build_dynamic_node_schema",
    "build_dynamic_node_user_prompt",
    "build_pass1_schema",
    "build_pass1_user_prompt",
    "build_pass1_contract_schema",
    "build_pass1_contract_user_prompt",
    "build_pass1_node_schema",
    "build_pass1_node_user_prompt",
    "PASS2_PROSE_SYSTEM",
    "build_pass2_schema",
    "build_pass2_user_prompt",
    "build_end_prose_schema",
    "build_end_prose_user_prompt",
    "TOPOLOGY_SYSTEM",
    "build_topology_schema",
    "build_topology_user_prompt",
]
