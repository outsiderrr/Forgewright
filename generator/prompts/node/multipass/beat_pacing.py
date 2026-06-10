"""对话节拍编排（beat pacing）—— 把信息密集节点拆成多个单选项节拍（探索/样例阶段）.

承接作者反馈（2026-06-08）：CRPG 里 node = 一个对话节拍（NPC 文本 + 1~N 个玩家回应）；
单选项"继续/追问"节拍是标配。信息密集的节点（如露西一口气 7 条线索）应拆成 2-3 个
**单选项节拍**一拍一拍喂，而不是一锅端。

schema 已支持（node.schema.json: type=dialogue ⇒ options minItems=1），故本探索**不动 schema**，
只在生成层把一个 reveal-heavy 骨架节点 pace 成 beat 链。作者批准"先产样例过目，再定为默认"。
"""
from __future__ import annotations

from typing import Any

from generator.prompts.node.anti_pattern_blacklist import ANTI_PATTERN_BLACKLIST_TEXT
from generator.prompts.node.role_rules import ROLE_RULES_TEXT


def _build_system() -> str:
    return f"""你是 Forgewright 的 CRPG **对话节拍编排器**。

## 你的任务
给你一个**信息密集**的节点（它的局面 + 要揭露的线索清单），你把它拆成 **2-3 个单选项节拍**
（continue beat），一拍一拍把信息喂出来，**不要一口气全说**。

每个节拍 = 玩家会看到的一屏：
1. narration：简短旁白（白描，约 60-120 字，承担空间 / 物理动作 / 可回收线索之一）。
2. dialogue：露西此刻说的 1-2 句（**关键信息由露西在引号里自己说**，不让旁白抢）。
3. continue_option：把玩家推进到下一拍的**一句短话或动作**。

## 节拍规则
- 把线索清单**分散**到各拍，**每拍只揭 1-2 条**；不要一拍说完。
- 各拍之间要有"露西说一点 → 玩家接一句 → 露西再说一点"的来回感。
- 最后一拍的 continue_option 可以是收束（如"我记下了。"）。
- **场景锚定**：在场人物与空间以任务给定的"场景锚定事实"为准——**不得新增任何人物**
  （侍者/伙计/仆人等都不许凭空出现），**不得转移空间**；旁白中的玩家一律写"你"，
  不得出现"玩家"二字。

## continue_option 文本规则（作者反馈）
- 选项默认就是玩家的话，**第一人称隐含，别硬塞"我"**。
- 写成一句**短追问 / 短回应 / 动作**：如"然后呢？""钥匙在哪？""[记下路标]""我记下了。"
- ≤ 15 汉字。

{ROLE_RULES_TEXT}

{ANTI_PATTERN_BLACKLIST_TEXT}

## 输出格式
- valid JSON 单对象，第一个字符 `{{`，最后一个字符 `}}`，无 markdown 围栏。
- 形态：{{"beats": [{{"narration": "...", "dialogue": ["...", "..."], "continue_option": {{"text": "..."}}}}]}}
- 2-3 个 beat。
"""


BEAT_PACING_SYSTEM = _build_system()


def build_beat_pacing_user_prompt(
    *,
    scene_contract: dict[str, Any],
    node_situation: str,
    reveals: list[str],
    npc_name: str = "露西",
    scene_anchor_facts: str | None = None,
) -> str:
    """拼接 beat pacing user message（要分拍的节点 = 局面 + 线索清单 + 场景锚定）。

    Args:
        scene_anchor_facts: 在场人物/空间锚定事实（复核根因④：多 pass 后段会丢场景锚定、
            凭空冒出侍者/仆人；注入后链内每拍都以此为准，不得新增人物/转场）。
    """
    import json

    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    rv = "\n".join(f"- {r}" for r in reveals) if reveals else "（无）"
    anchor_block = (
        f"""
## 场景锚定事实（每一拍都以此为准；不得新增人物、不得转移空间）
{scene_anchor_facts}
"""
        if scene_anchor_facts
        else ""
    )
    return f"""## 场景契约（固定上下文）
{sc}
{anchor_block}
## 要分拍的节点
当前局面：{node_situation}

## 要在这些节拍里揭露的线索（分散到 2-3 拍，每拍 1-2 条）
{rv}

把上面这个信息密集的节点，拆成 2-3 个单选项节拍（{npc_name} 一拍说 1-2 条，玩家一句短追问推进到下一拍）。
按下面的输出 JSON schema 返回。
"""


def build_beat_pacing_schema() -> dict[str, Any]:
    """beat 链输出契约（2-3 个单选项节拍）。"""
    return {
        "type": "object",
        "required": ["beats"],
        "properties": {
            "beats": {
                "type": "array",
                "minItems": 2,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["narration", "dialogue", "continue_option"],
                    "properties": {
                        "narration": {"type": "string"},
                        "dialogue": {"type": "array", "items": {"type": "string"}},
                        "continue_option": {
                            "type": "object",
                            "required": ["text"],
                            "properties": {
                                "text": {"type": "string", "description": "玩家短追问/回应/动作；第一人称隐含；≤15 字"}
                            },
                        },
                    },
                },
            }
        },
    }


__all__ = [
    "BEAT_PACING_SYSTEM",
    "build_beat_pacing_user_prompt",
    "build_beat_pacing_schema",
]
