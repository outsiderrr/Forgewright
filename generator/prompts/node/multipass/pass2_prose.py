"""Pass 2 — 节点正文写作 system prompt（多 pass 原型；结构层任务的"写"那一遍）.

design-first 多 pass 改造的**第 2 遍**：把 Pass 1 设计好的**单个节点骨架**当固定输入，
写该节点的 narration + NPC dialogue + 玩家选项第一人称文本。**不改结构**。

瘦身（handoff §3③ "验证减负假设"；已正式落地）：
  - **AP-7 / AP-8 / AP-10 不进生成 prompt**——这 3 条已由 validator/anti_pattern_detector.py
    程序化检测（detect_ap7/ap8/ap10），留在生成 prompt 里纯属"白占注意力"。
    canonical 提示词版黑名单（anti_pattern_blacklist.py）即 7 条，直接 inject，无需再过滤。
  - role_rules 三契约**保留**——它是结构性的"谁说什么"，不是文风黑名单。

历史压缩（按需注入 / ADR-018 narrative_weight 思想）：
  user message 只注入"本节点之前已揭露线索 + 已用选项角度"的几十字摘要，不传前文全文。
  目的：narration 聚焦本节点新信息（修 baseline narration 短 + N1↔N2 重复）。
"""
from __future__ import annotations

from typing import Any

from generator.prompts.node.anti_pattern_blacklist import ANTI_PATTERN_BLACKLIST_TEXT
from generator.prompts.node.role_rules import ROLE_RULES_TEXT


def _build_pass2_system() -> str:
    return f"""你是 Forgewright 的 CRPG **节点正文写作器**。

## 你的任务
给定一个**已经设计好的节点骨架**（function / situation / choice_pressure / 每个 option 的
intent 都已固定），你只写这个节点的：
1. narration（旁白）
2. NPC dialogue（NPC 在本节点说的话）
3. options[].text（把每个骨架 option 的 intent 转写成玩家第一人称台词/动作）
**不要改结构**：不增删节点、不改 option 的设计意图、不改线索分层。

{ROLE_RULES_TEXT}

{ANTI_PATTERN_BLACKLIST_TEXT}

## Narration 规则
- 白描为主：少抽象评价、少漂亮警句，不排比 / 不对仗 / 不堆成语 / 不押韵。
- **长度 250-400 汉字**（把节点写厚；不要只写到 150 字下限草草收尾）。
- 每一句至少承担一个功能：空间信息 / 视线与听觉风险 / NPC 物理状态 / 行动机会 /
  可回收线索 / 物理异常（少量，需有人注意或回避）。
- **不替 NPC 转述信息**：NPC 知道的事让 NPC 在 dialogue 引号里自己说，narration 不抢答。
- **旁白中的玩家一律写"你"**，不得出现"玩家"二字（"视线越过玩家肩侧"是错的，要写"越过你的肩侧"）。
- **不替玩家总结选择结构**：不写"谈话到了可进可退的位置""再多一句就如何"这类元叙述；
  选择压力用在场的物理事实呈现，判断留给玩家。

## 玩家选项规则
- 逐条对应骨架的 option：把它的 `intent` 转写成玩家**第一人称**可说出口的台词，或直接行动语言。
- 每条 ≤ 25 汉字；可保留 `[skill_name]` 检定前缀，但主体必须第一人称。
- 不要写成"追问 / 安慰 / 威胁 / 调查"这类第三人称意图标签。

## 历史压缩（避免与前文重复）
- user message 会给你"本节点之前已揭露的线索"和"已用过的选项角度"。
- narration 聚焦本节点 `reveals` 里的**新**信息，**不复述**前文已揭露的线索。
- 本节点的选项角度不要和"已用过的选项角度"雷同。

## 输出格式
- 必须是 valid JSON 单对象；第一个字符 `{{`，最后一个字符 `}}`。
- 不含 markdown 围栏、开场白、注释。
"""


PASS2_PROSE_SYSTEM = _build_pass2_system()


def build_pass2_user_prompt(
    *,
    scene_contract: dict[str, Any],
    node_skeleton: dict[str, Any],
    revealed_clues: list[str],
    used_option_intents: list[str],
) -> str:
    """拼接 Pass 2 user message（单节点 + 历史压缩摘要）.

    Args:
        scene_contract: Pass 1 产出的场景契约。
        node_skeleton: Pass 1 产出的**本节点**骨架。
        revealed_clues: 本节点之前已揭露的线索（历史压缩；几十字）。
        used_option_intents: 本节点之前已用过的选项 intent（历史压缩）。
    """
    import json

    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    sk = json.dumps(node_skeleton, ensure_ascii=False, indent=2)
    revealed = "、".join(revealed_clues) if revealed_clues else "（这是第一个节点，前面还没揭露任何线索）"
    used = "；".join(used_option_intents) if used_option_intents else "（无）"
    opt_lines = "\n".join(
        f"  {i + 1}. intent = {o.get('intent', '')}"
        for i, o in enumerate(node_skeleton.get("options", []))
    )
    speaker = node_skeleton.get("speaker_ref") or scene_contract.get("npc_name") or "NPC"

    return f"""## 场景契约（固定上下文）
{sc}

## 本节点骨架（结构已定，不要改）
node_id = {node_skeleton.get('node_id')} ；function = {node_skeleton.get('function')}
{sk}

## 历史压缩（避免与前文重复）
- 本节点之前**已揭露的线索**：{revealed}
- 本节点之前**已用过的选项角度**：{used}
（要求：narration 聚焦本节点 reveals 的新信息，不复述上面已揭露的线索；选项角度不要和"已用过的"雷同。）

## 你要写的
1. narration：本节点旁白（遵守 narration 规则）。
2. dialogue：{speaker} 在本节点说的话（引号内；关键信息由 NPC 自己说，不让旁白抢）。
3. options：逐条把下面骨架 option 的 intent 转写成玩家**第一人称**台词/动作（≤25 字）：
{opt_lines}

按下面的输出 JSON schema 返回。
"""


def build_pass2_schema() -> dict[str, Any]:
    """Pass 2 输出契约 JSON Schema（单节点正文）."""
    return {
        "type": "object",
        "required": ["narration", "dialogue", "options"],
        "properties": {
            "narration": {
                "type": "string",
                "description": "节点旁白；250-400 汉字；白描；每句承担功能",
            },
            "dialogue": {
                "type": "array",
                "items": {"type": "string"},
                "description": "NPC 在本节点说的话（引号内内容；关键信息由 NPC 自己说）",
            },
            "options": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["intent", "text"],
                    "properties": {
                        "intent": {"type": "string", "description": "对应的骨架 intent（echo，便于对账）"},
                        "text": {"type": "string", "description": "玩家第一人称台词/动作；≤25 汉字"},
                    },
                },
            },
        },
    }


# ---------- end 节点收束正文（动态拓扑配套的微调用；输出极小，无超时风险）----------


def build_end_prose_user_prompt(
    *,
    scene_contract: dict[str, Any],
    node_function: str,
    path_summary: str,
    scene_anchor_facts: str | None = None,
) -> str:
    """end（终止）节点收束旁白的 user prompt.

    Args:
        scene_contract: 契约 pass 产出（固定上下文）。
        node_function: 本 end 节点一句话功能（来自 TopologyPlan，如"带完整线索离开"）。
        path_summary: 到达本结局的路径摘要（走了什么分支、拿到了什么）。
        scene_anchor_facts: 在场人物/空间锚定事实（复核根因④：收束段最易凭空加人/转场）。
    """
    import json

    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    anchor_block = (
        f"""
## 场景锚定事实（以此为准；不得新增人物、不得转移空间）
{scene_anchor_facts}
"""
        if scene_anchor_facts
        else ""
    )
    return f"""## 场景契约（固定上下文）
{sc}
{anchor_block}
## 你要写的：一个**终止节点（end）**的收束旁白
- 本结局功能：{node_function}
- 玩家到达路径：{path_summary}

要求：
1. narration：80-200 汉字收束旁白（白描；交代玩家带着什么离开 / 场景怎么收；
   玩家一律写"你"，不得出现"玩家"二字）。
2. dialogue：NPC 收尾的 0-2 句话（可为空数组；关键信息已在前文给过，这里不补新线索）。
3. **没有玩家选项**（终止节点），不要输出 options。

按下面的输出 JSON schema 返回。
"""


def build_end_prose_schema() -> dict[str, Any]:
    """end 节点收束正文输出契约（narration + 可选 dialogue；无 options）。"""
    return {
        "type": "object",
        "required": ["narration", "dialogue"],
        "properties": {
            "narration": {
                "type": "string",
                "description": "收束旁白；80-200 汉字；白描",
            },
            "dialogue": {
                "type": "array",
                "items": {"type": "string"},
                "description": "NPC 收尾的 0-2 句（可空）",
            },
        },
    }


__all__ = [
    "PASS2_PROSE_SYSTEM",
    "build_pass2_user_prompt",
    "build_pass2_schema",
    "build_end_prose_user_prompt",
    "build_end_prose_schema",
]
