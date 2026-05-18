"""Forward Planner（前向规划器）— T-3Y 进展报告 §6 三子模块.

T-3Y-1 mini prototype 阶段：提供 stub 函数 + 单元测试；完整算法实现推迟到 T-3Y v0.2+。

三子模块：
  - intent.py        模块 A 剧本意图层（intent layer）：从 dialogue_graph 结构 + chapter outline
                     推导每节点的 intended_foreground_goal / intended_background_seeds
  - state_summary.py 模块 B 状态摘要层（state summary layer）：从 state path + NPC 状态机 +
                     检定结果计算 actual_player_known_info（玩家在本节点实际已知信息）
  - reconcile.py     模块 C 协调层（reconcile layer）：意图 + 状态 + skill 前置 →
                     pass / split_node / weaken_goal / rewrite_seeds / unreachable 五分支
"""

__all__ = ["intent", "state_summary", "reconcile"]
