"""文风评审（LLM-as-judge）system / user prompt 与输出契约.

口径（作者，2026-06-10/12）：judge 是**执行已有标准**，不是立新标准——
不为个案扩规则集；拿不准 = 不报。打分维度 = 作者拍板的 taxonomy（决策 A）；
违规检出 = 提示词版 7 条 AP（普适 5 条 + 白描预设 2 条；AP-7/8/10 程序化检测不归 judge）。
"""
from __future__ import annotations

from typing import Any

from generator.prompts.node.anti_pattern_blacklist import AP_TEXTS
from generator.judge.taxonomy import SCORED_DIM_IDS, TAXONOMY

_GROUP_TITLES = {
    "narration": "旁白维度",
    "dialogue": "NPC 对白维度",
    "options": "玩家选项维度",
    "global": "全局维度",
}


def _taxonomy_block() -> str:
    lines: list[str] = []
    for group in ("narration", "dialogue", "options", "global"):
        dims = [d for d in TAXONOMY if d.group == group]
        if not dims:
            continue
        lines.append(f"### {_GROUP_TITLES[group]}")
        for d in dims:
            tag = "打 1-5 分" if d.scored else "只描述，不打分"
            lines.append(f"- **{d.id} {d.name}**（{tag}）：{d.definition}")
    return "\n".join(lines)


def _ap_block() -> str:
    return "\n\n".join(AP_TEXTS[i] for i in ("AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9"))


def _build_system() -> str:
    return f"""你是 Forgewright 的 CRPG **文风评审员**。给你一段已生成场景的节点文本，你按
**固定标准**逐维打分并检出违规。

## 铁律（违反 = 评审无效）
1. **只按下面列出的维度与条款评审**——不得自创新标准、不得按个人口味加扣分项。
2. 每个分数和每条违规都必须**引用节点原文**作证据；引不出原文 = 不报。
3. **拿不准 = 不报**：宁可漏报，不可把合规文本误判成违规。
4. 打分对象是文本质感，不是剧情/结构——结构问题（分支、路由、节奏拆分）不归你管。

## 评分维度（作者批准 taxonomy；1=严重不符 3=及格 5=典范）
{_taxonomy_block()}

## 违规条款（Anti-pattern 提示词版 7 条；检出须引原句）
{_ap_block()}

## 输出
- dim_scores：对每个"打 1-5 分"维度给整数分 + 一句证据（引原文）。
  本块文本未涉及的维度（如无 end 节点时的 S7）给 score=0 表示"不适用"。
- ap_violations：检出的违规清单（ap_id / node_id / 原句 / 一句理由）；没有就空数组。
- notes：S13（温度）与 S14（人称约定一致性）的描述性观察，各 ≤2 句；没有就空数组。
- 必须是 valid JSON 单对象；第一个字符 `{{`，最后一个字符 `}}`；不含 markdown 围栏。
"""


STYLE_JUDGE_SYSTEM = _build_system()


def render_nodes_for_judge(nodes: list[tuple[str, dict[str, Any]]]) -> str:
    """把若干 (node_id, node) 渲染成 judge 可读文本（narration 含组装后的 NPC 引语）。"""
    parts: list[str] = []
    for nid, n in nodes:
        opts = "\n".join(f"  - {o.get('text', '')}" for o in n.get("options") or [])
        parts.append(
            f"### 节点 {nid}\n{n.get('narration', '')}\n"
            + (f"玩家选项：\n{opts}" if opts else "（终止节点，无选项）")
        )
    return "\n\n".join(parts)


def build_judge_user_prompt(
    *,
    chunk_nodes: list[tuple[str, dict[str, Any]]],
    scene_id: str,
    chunk_index: int,
    chunk_total: int,
) -> str:
    return f"""## 待评审文本（场景 {scene_id}；第 {chunk_index}/{chunk_total} 块，共 {len(chunk_nodes)} 个节点）

{render_nodes_for_judge(chunk_nodes)}

按 system 给定的维度与条款评审本块，返回输出 JSON。"""


def build_judge_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["dim_scores", "ap_violations", "notes"],
        "properties": {
            "dim_scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["dim", "score", "evidence"],
                    "properties": {
                        "dim": {"type": "string", "enum": list(SCORED_DIM_IDS)},
                        "score": {"type": "integer", "minimum": 0, "maximum": 5},
                        "evidence": {"type": "string", "description": "引原文的一句证据；score=0（不适用）可为空串"},
                    },
                },
            },
            "ap_violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["ap_id", "node_id", "quote", "reason"],
                    "properties": {
                        "ap_id": {
                            "type": "string",
                            "enum": ["AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9"],
                        },
                        "node_id": {"type": "string"},
                        "quote": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
            },
            "notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["dim", "note"],
                    "properties": {
                        "dim": {"type": "string", "enum": ["S13", "S14"]},
                        "note": {"type": "string"},
                    },
                },
            },
        },
    }


__all__ = [
    "STYLE_JUDGE_SYSTEM",
    "build_judge_user_prompt",
    "build_judge_schema",
    "render_nodes_for_judge",
]
