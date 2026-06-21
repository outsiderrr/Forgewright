"""文风维度 taxonomy（决策 A，作者拍板 2026-06-12）—— 前控制 = 后校验的同一套清单.

来源：generator/experiments/aesthetic_layer/DESIGN_2026-06-12_phase2_style_layer.md §1。
岗位（上位讨论 2026-06-08）：维度 = 探索 + 校验，不是控制——控制权在锚点样例。
judge 用本清单逐维打 1-5 分；`scored=False` 的维度只做描述性输出（S13 温度校准值
有意 TBD；S14 是约定一致性检查）。gate 子集判"作者少改即可用"。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleDimension:
    id: str
    name: str
    group: str  # narration | dialogue | options | global
    definition: str
    scored: bool = True  # False = judge 只描述不打分


TAXONOMY: tuple[StyleDimension, ...] = (
    StyleDimension("S1", "白描密度", "narration", "细节先于评价；评价必须有可观察细节铺垫"),
    StyleDimension("S2", "修辞质量与克制", "narration", "比喻少而准；用喻必有锚（喻体与本体共同点清楚）"),
    StyleDimension("S3", "感官层次", "narration", "视觉之外有听/嗅/触觉分布，不是纯视觉陈设罗列"),
    StyleDimension("S4", "物理动作词汇多样性", "narration", "道具动作不跨节点复读；同一道具要有状态演进"),
    StyleDimension("S5", "异常呈现克制度", "narration", "超自然以可复核物理细节出现（最好经 NPC 之口），不堆形容词"),
    StyleDimension("S6", "句长节奏", "narration", "长短句交替；短句用在压力点，不连续等长句"),
    StyleDimension("S7", "收束质感", "narration", "end 节点物理收束 + 清点带走之物；不抒情总结、不评判"),
    StyleDimension("S8", "角色声纹", "dialogue", "措辞/句长/职业腔区分 NPC，不同 NPC 不可互换台词"),
    StyleDimension("S9", "潜台词浓度", "dialogue", "话里有未说尽的东西；动机靠行为与省略呈现，不自我剖白"),
    StyleDimension("S10", "对白口语质感", "dialogue", "NPC 说话像说话，不像书面公文/翻译腔；允许角色化文雅但不对仗成文"),
    StyleDimension("S11", "选项自然口语度", "options", "自然口语优先于短；反电报体（『你为什么这么着急？』✓『为什么急？』✗）"),
    StyleDimension("S12", "接话形态多样性", "options", "追问/确认代称/动作三形态合理混合；不复述 NPC 刚说的内容"),
    StyleDimension("S13", "温度对齐", "global", "暗黑+灰色基线；人物无纯善纯恶（校准值 TBD——只描述，不打分）", scored=False),
    StyleDimension(
        "S14", "选项人称约定一致性", "global",
        "choice 选项可带'我'，beat 接话第一人称隐含——两套约定并存但各自内部要一致（只检查，不打分）",
        scored=False,
    ),
)

# 决策 A 附带：判"作者少改即可用"的 gate 子集（均分 ≥ GATE_THRESHOLD）
GATE_DIM_IDS: tuple[str, ...] = ("S1", "S2", "S4", "S9", "S11", "S12")
GATE_THRESHOLD = 4.0

SCORED_DIM_IDS: tuple[str, ...] = tuple(d.id for d in TAXONOMY if d.scored)

__all__ = [
    "StyleDimension",
    "TAXONOMY",
    "GATE_DIM_IDS",
    "GATE_THRESHOLD",
    "SCORED_DIM_IDS",
]
