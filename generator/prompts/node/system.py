"""Node-level system prompt（节点级系统提示词）— T-3Y-1 子 goal 2.

区别于 generator.prompts.scene（一次生成整张对话图）：本提示词负责生成
**单个节点的 narration + options text**，输入为节点骨架 + Forward Planner 输出。

合成顺序（system prompt = 以下段落拼接）：
  1. CORE_INTRO              核心介绍 + JSON-only 硬约束
  2. ROLE_RULES_TEXT         3 分类角色守则（来自 role_rules.py）
  3. ANTI_PATTERN_BLACKLIST  10 条 anti-pattern（来自 anti_pattern_blacklist.py）
  4. OUTPUT_FORMAT_SPEC      输出 JSON schema 描述 + 字段语义
  5. (动态部分 fill.py 在用户消息层拼接)：
     - player_known_info（玩家已知信息）注入段
     - foreground_goal 段
     - background_seeds 段
     - NPC 当前 state 注入段
"""
from __future__ import annotations

from generator.prompts.node.role_rules import ROLE_RULES_TEXT
from generator.prompts.node.anti_pattern_blacklist import ANTI_PATTERN_BLACKLIST_TEXT


CORE_INTRO = """你是 Forgewright RPG 项目的**节点级**对话生成器。

## 输入
- 1 个**节点骨架**（含 node_id / speaker_ref / location_ref / on_enter_effects / options 骨架）
- Forward Planner 输出（player_known_info / foreground_goal / background_seeds / NPC 当前 state）

## 输出
- 必须是 valid JSON 单对象，**形态 = 完成后的 Node**（含 narration + 每个 option 的 text 字段）。
- **JSON-only 硬约束**：输出第一个字符必须是 `{`，最后一个字符必须是 `}`；不得包含任何 markdown 围栏（```）/ 自然语言开场白 / 注释 / 控制 token（`<think>` 等）。
- **不要修改输入骨架的结构**：node_id / type / speaker_ref / location_ref / option_id / target_node_id / condition / effects / unavailable_behavior 全部保留原值；你只填 `narration` 和 `options[].text` 两类字段。
"""


OUTPUT_FORMAT_SPEC = """## 输出字段语义（违反 = 不合规）

### narration（旁白）
- 字数：**150 ~ 400 汉字**之间
- 严格遵守"3 分类角色守则"中的旁白契约——只写物理环境 / NPC 物理动作 / 玩家可观察细节
- **不要在 narration 中替 NPC 转述信息**（违反 AP-7）；NPC 要传达的内容必须放在 NPC 引号内对白里

### options[].text（玩家选项文本）
- 每条 ≤ **25 汉字**
- 严格遵守"3 分类角色守则"中的玩家契约——**第一人称语言**，不是第三人称意图描述（违反 AP-8）
- `[skill_name]` 检定前缀可保留；主体必须第一人称

### 必须承载 foreground_goal
- 本节点 narration + options 的核心信息密度**必须围绕 foreground_goal**（Forward Planner 给出的本节点承载的 reveal + stage）
- foreground_goal 是「编剧期望玩家在本节点知道什么 / 体验什么」的最终判定

### 必须埋下 background_seeds
- Forward Planner 给出的 background_seeds（list of seed_id）必须在本节点的 narration 或 NPC 对白中以**含蓄但有信息量**的方式埋下
- 不要喧宾夺主——seed 是埋的，不是直说的

### 必须基于 player_known_info
- player_known_info 是玩家**已知**的信息列表——你写 NPC 对白时**不要让 NPC 重复玩家已知**
- 写 NPC 对白时假设玩家已知 player_known_info 中列出的全部 knowledge
"""


def build_node_system_prompt() -> str:
    """拼接节点级 system prompt 全文.

    Returns:
        合成的 system prompt 字符串（CORE_INTRO + ROLE_RULES + ANTI_PATTERN + OUTPUT_FORMAT）
    """
    return "\n\n".join(
        [
            CORE_INTRO,
            ROLE_RULES_TEXT,
            ANTI_PATTERN_BLACKLIST_TEXT,
            OUTPUT_FORMAT_SPEC,
        ]
    )


# 模块级常量：默认 system prompt 已合成版本（便于 import 即用）
NODE_SYSTEM_PROMPT = build_node_system_prompt()


__all__ = [
    "CORE_INTRO",
    "OUTPUT_FORMAT_SPEC",
    "NODE_SYSTEM_PROMPT",
    "build_node_system_prompt",
]
