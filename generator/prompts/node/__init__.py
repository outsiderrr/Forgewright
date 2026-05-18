"""Node-level prompt（节点级提示词）子包 — T-3Y-1 子 goal 2.

区别于 generator.prompts.scene（场景级一次生成整张图），本子包是
**节点级单点生成**——给定一个节点骨架 + Forward Planner 输出 + 3 分类角色守则 +
anti-pattern blacklist，生成本节点的 narration + options text.

模块：
  - system.py                  节点级 system prompt（含 3 分类角色守则 + JSON-only 硬约束）
  - fill.py                    动态填充段（player_known_info / foreground_goal / background_seeds / NPC 状态注入）
  - anti_pattern_blacklist.py  10 条 anti-pattern 黑名单 prompt 段（inject 到 system）
  - role_rules.py              3 分类角色守则（旁白 / NPC / 玩家）写作约束的纯文本段
"""
__all__ = ["system", "fill", "anti_pattern_blacklist", "role_rules"]
