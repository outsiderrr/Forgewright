"""拓扑规划 pass（topology planning）prompt —— 动态拓扑（ADR-038 follow-up (1)）.

让 LLM 按场景自决节点数 / 类型 / 分支接线，替代 v1 的半固定脚手架
（开场 → 枢纽 → 两分支 → end）。

超时安全（DESIGN_2026-06-10 §6）：本 pass 输出**只有结构骨架 JSON**
（每节点 id / kind / 一句话功能 / 线索分配 / 接线），不含任何正文——
输出尺寸与契约 pass 同级（数百 token），不触发中转站大请求超时。

确定性校验 + 回退在 generator/multipass/topology.py（引擎层，0 LLM）。
"""
from __future__ import annotations

import json
from typing import Any

TOPOLOGY_SYSTEM = """你是 Forgewright 的 design-first CRPG **拓扑规划器**。

## 你的任务
只规划一场戏的**节点图拓扑**：有哪些节点、每个节点什么类型、线索分配到哪、节点之间怎么连。
**绝不写正文**——不写旁白、不写对白、不写选项台词，也不设计选项细节（那是后续 pass 的事）。

## 节点类型（kind）
- **choice**：多选项决策点（玩家面临真选择）。写 `routes`：1-4 条出边，每条带 `stance`
  （一句话：这条出边代表玩家什么姿态/去向）。**出边数 = 真实分歧数**：玩家会有几类
  语义不同的反应（问不同的事 / 亮不同的牌 / 走不同的方向），就给几条出边（≤4）；
  只有当多个选项确实是**同一姿态的不同说法**时才共享一条出边，此时 `stance` 必须写出
  这条边上所有选项的**共同语义**（后续 pass 要靠它写出对每个入口都成立的承接）。
- **beats**：单选项节拍链（信息密集内容分拍铺开：NPC 说一点 → 玩家接一句 → 再说一点）。
  写 `next`：唯一出边。
- **end**：终止节点。无出边。

## 拓扑规则
1. **纯树结构**：除入口外每个节点恰好被一条边指到；禁止交叉边、禁止回环。
2. 节点总数 **3-12**（一条 beats 链算 1 个规划节点）。
3. 至少 1 个 choice 节点 routes ≥ 2（场景要有真分歧）；至少 1 个 end。
4. **节点功能分化**：每个节点写一句话 `function`，互不重叠；开场节点不预先泄露深层线索。
5. **线索分层**：把场景线索分配到各节点 `reveals`；不同分支完整度必须不同
   （低压/高信任分支给完整线索，高压/低信任分支只给残缺碎片——残缺版要在 reveals 文本里
   **写明残缺形态**，如"地址只剩门牌号，无街名"）。
   **同一线索原文复制到两个平行分支会被结构校验直接拒收**。
6. 拓扑要从场景自然长出来：信息密集处用 beats 链铺陈；真分歧处用 choice；
   不要为了凑数加空节点。

## 输出格式
- 必须是 valid JSON 单对象；第一个字符 `{`，最后一个字符 `}`。
- 不含 markdown 围栏（```）、开场白、注释。
"""


def _scene_spec_block(scene_spec: dict[str, Any]) -> str:
    def _bullets(items: list[str] | None) -> str:
        return "\n".join(f"- {x}" for x in items) if items else "（无）"

    return f"""## 场景背景
{scene_spec['background']}

## 核心设计目标
{scene_spec['design_goal']}

## 已知角色状态
{scene_spec['character_state']}

## 必须输出的线索
{_bullets(scene_spec.get('required_clues'))}

## 可选输出的线索
{_bullets(scene_spec.get('optional_clues'))}

## 不允许发生的事
{_bullets(scene_spec.get('forbidden_events'))}"""


def build_topology_user_prompt(
    *,
    scene_spec: dict[str, Any],
    scene_contract: dict[str, Any],
    prior_errors: list[str] | None = None,
) -> str:
    """拼接拓扑规划 user prompt.

    Args:
        scene_spec: 场景 spec（background / design_goal / clues / forbidden_events）。
        scene_contract: 契约 pass 产出（固定上下文）。
        prior_errors: 上一次规划未过确定性校验的错误清单（重试时注入，引导修正）。
    """
    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    retry_block = ""
    if prior_errors:
        errs = "\n".join(f"- {e}" for e in prior_errors)
        retry_block = f"""
## ⚠️ 上一次规划未通过结构校验，原因如下（必须全部修正）
{errs}
"""
    return f"""请为下面场景**只规划节点图拓扑**（不写任何正文）。

{_scene_spec_block(scene_spec)}

## 场景契约（已定，固定上下文）
{sc}
{retry_block}
按下面的输出 JSON schema 返回：entry_node_id + nodes 数组
（每个节点含 node_id / kind / function / reveals / routes 或 next）。
node_id 用小写英文蛇形命名（如 opening / hub_pressure / soft_line / end_leave）。
"""


def build_topology_schema() -> dict[str, Any]:
    """拓扑规划输出契约 JSON Schema（小输出；纯结构）。"""
    return {
        "type": "object",
        "required": ["entry_node_id", "nodes"],
        "properties": {
            "entry_node_id": {"type": "string", "description": "入口节点 node_id"},
            "nodes": {
                "type": "array",
                "minItems": 3,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "required": ["node_id", "kind", "function"],
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "pattern": "^[a-z][a-z0-9_]*$",
                            "description": "小写蛇形；图内唯一",
                        },
                        "kind": {"enum": ["choice", "beats", "end"]},
                        "function": {
                            "type": "string",
                            "description": "一句话功能；各节点互不重叠",
                        },
                        "reveals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "本节点揭露的线索（end 节点留空；残缺版写明残缺形态）",
                        },
                        "routes": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 4,
                            "items": {
                                "type": "object",
                                "required": ["to", "stance"],
                                "properties": {
                                    "to": {"type": "string", "description": "目标 node_id"},
                                    "stance": {
                                        "type": "string",
                                        "description": "这条出边代表玩家的姿态/去向（一句话）",
                                    },
                                },
                            },
                            "description": "仅 choice 节点：出边",
                        },
                        "next": {
                            "type": "string",
                            "description": "仅 beats 节点：唯一出边目标 node_id",
                        },
                    },
                },
            },
        },
    }


__all__ = [
    "TOPOLOGY_SYSTEM",
    "build_topology_user_prompt",
    "build_topology_schema",
]
