"""Pass 1 — 骨架设计 system prompt（多 pass 原型；结构层）.

design-first 多 pass 改造的**第 1 遍**：从场景 spec **设计**互动结构
（Scene Contract + 4 节点 Interaction Skeleton），**只带结构规则，0 条文风/AP 规则**。

与 generator.prompts.node.system（T-3Y-1 单 pass）的区别：
  - system.py：输入**已有**骨架 + Forward Planner 输出，一次填 narration + options text。
  - 本模块：从场景 spec **设计骨架本身**（4 节点的功能/局面/选项意图），不写正文。
正文交给 pass2_prose 第 2 遍逐节点写。

两种调用粒度（同一个 system prompt）：
  (a) 一次出全部（build_pass1_user_prompt / build_pass1_schema）——最少调用，但要求模型
      一次设计 4 个节点的大结构；对慢/有上游超时的中转站（如 new-api 转 gpt-5.5）会因
      "复杂推理 + 大输出 > 网关超时"而 502。
  (b) **拆细**（contract 1 次 + per-node 各 1 次）——每次中等大小，过得了超时；且逐节点
      设计时把前序节点喂进去，节点功能分化更强。实测 (a) 在 new-api+gpt-5.5 上 751s 超时，
      故原型默认用 (b)。

设计动机（针对 baseline 结构类弱点）：
  - 给骨架一个**专门 pass**，强制"节点功能分化" → 修 baseline 的 N1↔N2 近重复。
  - 骨架层的 option 用第三人称 `intent`（设计意图）即可——玩家第一人称台词是 Pass 2
    的事；这天然把 AP-8（选项第三人称化）从结构层移开，留给 Pass 2 + validator。
"""
from __future__ import annotations

from typing import Any

PASS1_SKELETON_SYSTEM = """你是 Forgewright 的 design-first CRPG **骨架设计器**。

## 你的任务
只设计**互动结构**：Scene Contract（场景契约）+ 4 个节点的 Interaction Skeleton（互动骨架）。
**绝不写节点正文**——不写 narration（旁白）、不写 NPC 对白、不写玩家选项的最终台词。正文是下一遍的事。

## 结构规则（只有结构，没有文风）

### 1. 节点功能必须分化【最重要】
4 个节点各有**不同功能**，**严禁两个节点用同一套选项或同一个局面**：
- **N1 shared opening（定向开场）**：建立"谁在场 / 空间 / 当前风险 / 玩家的初始姿态"。只给玩家**怎么接近**的入口选择。**N1 不得预先泄露深层线索**（小屋完整路线 / 铁盒 / 钥匙 / 空间异常都不在 N1 给）。
- **N2 hub（枢纽）**：基于 N1 的接近方式**升格**成真正的分歧——"低压软问"还是"高压施压"——并据此**路由**到 N3 / N4。N2 不是 N1 的重复菜单；它要把局面往"选边"推。
- **N3 branch A（低压 / 有限信任）**：完整线索路径。
- **N4 branch B（高压 / 低信任）**：残缺线索路径。

每个节点 skeleton 必须写明 `function`（一句话功能），且**四个 function 互不重叠**。

### 2. Choice pressure（每个选项的设计意图；第三人称设计语言即可）
每个选项写清楚四问：
- `intent`：玩家**想做什么**（设计意图标签，第三人称 OK，如"软问路线"。这只是给第 2 遍写正文用的，不是最终玩家台词。）
- `payoff`：能得到什么
- `cost`：要付出什么
- `relationship_delta`：对 trust / fear / cooperability / affinity（信任/恐惧/合作度/好感）的影响 + 理由

### 3. 线索分层（同一关键线索多路径可得，但完整度不同）
- N3（低压）：完整路线 + 雨桶钥匙 + 空间异常。
- N4（高压）：只给残缺记号（如 "7 / 北 / 断杆"），不给钥匙、不给异常。
- 每个节点写明 `reveals`（本节点揭露哪些线索）和 `hides`（刻意不给哪些）。
- 同一地址/线索**禁止**在多个分支里原文复制；不同分支必须改变完整度。

## 不要做的事
- 不要写 narration / 对白 / 选项最终台词（第 2 遍才写）。
- 不要评论文风、AI 腔、白描（与本遍无关）。
- 不要让 N1 和 N2 变成同一套选项。

## 输出格式
- 必须是 valid JSON 单对象；第一个字符 `{`，最后一个字符 `}`。
- 不含 markdown 围栏（```）、开场白、注释。
"""


# 4 节点的固定功能（design-first / handoff §3② 已规定；逐节点拆分时直接喂给模型，
# 既保证功能分化，又省掉"让模型现想 4 个功能"的那一大坨推理）。
NODE_FUNCTIONS: dict[str, str] = {
    "N1": (
        "shared opening（定向开场）：建立谁在场 / 空间 / 当前风险 / 玩家初始姿态；"
        "只给'怎么接近'的入口选择；**不得预先泄露**小屋完整路线 / 铁盒 / 钥匙 / 空间异常。"
    ),
    "N2": (
        "hub（枢纽）：把 N1 的接近方式**升格**成'低压软问 vs 高压施压'的真正分歧，"
        "并据此路由到 N3 / N4；**不是 N1 的重复菜单**，要把局面往'选边'推。"
    ),
    "N3": (
        "branch A（低压 / 有限信任）：完整线索路径——给完整路线 + 雨桶钥匙 + 空间异常。"
    ),
    "N4": (
        "branch B（高压 / 低信任）：残缺线索路径——只给残缺记号（如 '7 / 北 / 断杆'），"
        "**不给**钥匙、**不给**空间异常。"
    ),
}


# ---------- schema 构件（contract / node 复用）----------


def _scene_contract_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "player_goal",
            "npc_goal",
            "npc_fear",
            "required_clues",
            "optional_clues",
            "failsafe_path",
            "forbidden",
        ],
        "properties": {
            "player_goal": {"type": "string"},
            "npc_goal": {"type": "string"},
            "npc_fear": {"type": "string"},
            "required_clues": {"type": "array", "items": {"type": "string"}},
            "optional_clues": {"type": "array", "items": {"type": "string"}},
            "failsafe_path": {"type": "string", "description": "玩家失去信任也能继续的残缺路径"},
            "forbidden": {"type": "array", "items": {"type": "string"}},
        },
    }


def _node_skeleton_schema() -> dict[str, Any]:
    option_skeleton = {
        "type": "object",
        "required": ["intent", "payoff", "cost", "relationship_delta"],
        "properties": {
            "intent": {"type": "string", "description": "设计意图标签（第三人称 OK），如'软问路线'"},
            "payoff": {"type": "string", "description": "能得到什么"},
            "cost": {"type": "string", "description": "要付出什么"},
            "relationship_delta": {
                "type": "string",
                "description": "对 trust/fear/cooperability/affinity 的影响 + 理由",
            },
        },
    }
    return {
        "type": "object",
        "required": [
            "node_id",
            "function",
            "situation",
            "choice_pressure",
            "reveals",
            "hides",
            "options",
        ],
        "properties": {
            "node_id": {"type": "string", "description": "N1 / N2 / N3 / N4 之一"},
            "function": {"type": "string", "description": "一句话功能；四个节点互不重叠"},
            "situation": {"type": "string", "description": "当前局面（谁在场/空间/风险）"},
            "choice_pressure": {"type": "string", "description": "本节点选择压力来源"},
            "reveals": {"type": "array", "items": {"type": "string"}},
            "hides": {"type": "array", "items": {"type": "string"}},
            "options": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": option_skeleton,
            },
        },
    }


# ---------- 场景 spec → user prompt 片段 ----------


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


# ---------- (a) 一次出全部（保留；最少调用，但大中转站易超时）----------


def build_pass1_user_prompt(scene_spec: dict[str, Any]) -> str:
    """一次设计 Scene Contract + 4 节点骨架的 user prompt。"""
    return f"""请按 Forgewright design-first 方法，为下面场景**只设计互动骨架**
（Scene Contract + N1 / N2 / N3 / N4 的 Interaction Skeleton），**不要写正文**。

{_scene_spec_block(scene_spec)}

## 节点要求（只设计 4 个 node，功能互不重叠）
- N1 shared opening：定向开场，**不预先泄露**小屋 / 铁盒 / 钥匙 / 异常。
- N2 hub：把 N1 的接近方式**升格**成"软问 vs 施压"的分歧，路由到 N3 / N4。
- N3 branch A：低压 / 有限信任，完整线索。
- N4 branch B：高压 / 低信任，残缺线索。

每个 node 写：function（一句话功能，四者不重叠）/ situation（当前局面）/
choice_pressure（这个节点的选择压力来自哪里）/ 3-5 个 option（每个含 intent / payoff /
cost / relationship_delta）/ reveals（本节点揭露的线索）/ hides（刻意不给的线索）。

按下面的输出 JSON schema 返回。
"""


def build_pass1_schema() -> dict[str, Any]:
    """一次出全部的输出契约（Scene Contract + 4 节点骨架）。"""
    return {
        "type": "object",
        "required": ["scene_contract", "nodes"],
        "properties": {
            "scene_contract": _scene_contract_schema(),
            "nodes": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": _node_skeleton_schema(),
            },
        },
    }


# ---------- (b) 拆细：契约 1 次 + per-node 各 1 次（默认；过超时 + 分化更强）----------


def build_pass1_contract_user_prompt(scene_spec: dict[str, Any]) -> str:
    """**只**设计 Scene Contract 的 user prompt（小输出，过超时）。"""
    return f"""请按 Forgewright design-first 方法，为下面场景**只设计 Scene Contract（场景契约）**。
**不要**设计任何节点、**不要**写正文。

{_scene_spec_block(scene_spec)}

只输出场景契约：玩家目标 / 露西目标 / 露西恐惧 / 必须线索 / 可选线索 /
失败也能继续的残缺路径 / 本场景禁止发生的事。按下面的输出 JSON schema 返回。
"""


def build_pass1_contract_schema() -> dict[str, Any]:
    """只含 scene_contract 的输出契约。"""
    return _scene_contract_schema()


def build_pass1_node_user_prompt(
    *,
    scene_spec: dict[str, Any],
    scene_contract: dict[str, Any],
    node_id: str,
    prior_nodes: list[dict[str, Any]],
) -> str:
    """设计**单个**节点骨架的 user prompt（喂前序节点 → 强制功能分化 + 线索分层）。"""
    import json

    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    func = NODE_FUNCTIONS.get(node_id, "（功能未指定）")
    if prior_nodes:
        prior_lines = []
        for p in prior_nodes:
            intents = "、".join(o.get("intent", "") for o in p.get("options", []))
            prior_lines.append(
                f"- {p.get('node_id')}（{p.get('function','')}）"
                f"\n    已揭露线索：{('、'.join(p.get('reveals', []))) or '（无）'}"
                f"\n    已用选项角度：{intents or '（无）'}"
            )
        prior_block = "\n".join(prior_lines)
    else:
        prior_block = "（这是第一个节点，前面还没有已设计的节点）"

    return f"""请只设计**一个**节点的 Interaction Skeleton（互动骨架），**不要写正文**。

{_scene_spec_block(scene_spec)}

## 场景契约（已定，固定上下文）
{sc}

## 你现在要设计的节点
node_id = **{node_id}**
固定功能（必须严格扣住，不能偏成别的节点的功能）：{func}

## 已设计的前序节点（你必须与它们**功能不重叠**，并遵守**线索分层**）
{prior_block}

要求：
- 严格扣住本节点的固定功能；不要重复前序节点的局面或选项角度。
- 写 function（一句话，呼应固定功能）/ situation / choice_pressure /
  3-5 个 option（每个含 intent / payoff / cost / relationship_delta）/ reveals / hides。
- 遵守线索分层：N3 给完整线索，N4 只给残缺记号；同一线索不要在分支间原样复制。

按下面的输出 JSON schema 返回**单个节点对象**。
"""


def build_pass1_node_schema() -> dict[str, Any]:
    """单个节点骨架的输出契约。"""
    return _node_skeleton_schema()


# ---------- (c) 动态拓扑版：单 choice 节点骨架（拓扑规划 pass 给定功能 + 出边）----------
#
# 与 (b) 的区别：节点功能/出边不再来自固定的 NODE_FUNCTIONS（露西 4 节点脚手架），
# 而来自拓扑规划 pass 的 TopologyPlan；每个 option 必须声明 route_to ∈ 本节点出边目标集合，
# 供组装层确定性接线（option.target_node_id 由代码填，LLM 不写状态）。

PASS1_SKELETON_SYSTEM_DYNAMIC = """你是 Forgewright 的 design-first CRPG **骨架设计器**。

## 你的任务
只设计**单个 choice 节点**的 Interaction Skeleton（互动骨架）。
**绝不写节点正文**——不写 narration（旁白）、不写 NPC 对白、不写玩家选项的最终台词。正文是下一遍的事。

## 结构规则（只有结构，没有文风）

### 1. 节点功能必须分化【最重要】
- 严格扣住任务给定的本节点 `function`（拓扑规划已定），不要偏成别的节点的功能。
- **严禁**与已设计的前序节点用同一套选项角度或同一个局面。
- 开场类节点不得预先泄露深层线索。

### 2. Choice pressure（每个选项的设计意图；第三人称设计语言即可）
每个选项写清楚四问 + 路由：
- `intent`：玩家**想做什么**（设计意图标签，第三人称 OK，如"软问路线"。这只是给写正文那遍用的，不是最终玩家台词。）
- `payoff`：能得到什么
- `cost`：要付出什么
- `relationship_delta`：对 trust / fear / cooperability / affinity（信任/恐惧/合作度/好感）的影响 + 理由
- `route_to`：本选项把玩家送往哪条出边（**必须**从任务给定的出边目标里选；每条出边至少被一个选项使用）

### 2.5 选项数量（1-5 之间灵活，由真实玩家反应数决定；作者修订 2026-06-11）
- 唯一硬下限：**每条出边至少 1 个选项**把玩家送过去；选项数**不必等于出边数**。
- 是真选择就给足姿态变体制造选择压力；只是推进则少给。
- **不要为凑数发明选项**：每个额外选项必须是其所路由出边姿态的真变体
  （多个选项共享一条出边时，它们的共同语义必须与该出边 stance 一致），
  语义对不上任何出边的选项宁可不写。

### 3. 线索分层
- 每个节点写明 `reveals`（本节点揭露哪些线索）和 `hides`（刻意不给哪些）。
- 遵守任务给定的本节点线索分配；不要把别的分支的线索提前抖出来。
- 同一线索**禁止**在多个分支里原文复制；不同分支必须改变完整度。

## 不要做的事
- 不要写 narration / 对白 / 选项最终台词（下一遍才写）。
- 不要评论文风、AI 腔、白描（与本遍无关）。
- 不要增删出边或发明新的 route 目标。

## 输出格式
- 必须是 valid JSON 单对象；第一个字符 `{`，最后一个字符 `}`。
- 不含 markdown 围栏（```）、开场白、注释。
"""


def build_dynamic_node_user_prompt(
    *,
    scene_spec: dict[str, Any],
    scene_contract: dict[str, Any],
    node_id: str,
    function: str,
    planned_reveals: list[str],
    routes: list[dict[str, str]],
    prior_nodes: list[dict[str, Any]],
    entry_context: dict[str, Any] | None = None,
) -> str:
    """动态拓扑版：设计单个 choice 节点骨架的 user prompt.

    Args:
        scene_spec: 场景 spec。
        scene_contract: 契约 pass 产出。
        node_id: 本节点 id（来自 TopologyPlan）。
        function: 本节点一句话功能（来自 TopologyPlan）。
        planned_reveals: 拓扑规划分配给本节点的线索。
        routes: 本节点出边（[{"to": ..., "stance": ...}]，来自 TopologyPlan）。
        prior_nodes: 已设计的前序节点摘要（node_id / function / reveals / options[].intent）。
        entry_context: 玩家进入本节点的入口上下文（单入口=玩家原句 / 收敛多入口=语句清单；
            参与 situation / choice_pressure 设计——junction 承接从骨架层就开始）。
    """
    import json

    from generator.prompts.node.multipass.entry_context import entry_context_block

    sc = json.dumps(scene_contract, ensure_ascii=False, indent=2)
    route_lines = "\n".join(
        f"- route_to = `{r['to']}`：{r.get('stance', '')}" for r in routes
    )
    reveals_block = (
        "\n".join(f"- {r}" for r in planned_reveals) if planned_reveals else "（本节点不揭露新线索）"
    )
    if prior_nodes:
        prior_lines = []
        for p in prior_nodes:
            intents = "、".join(o.get("intent", "") for o in p.get("options", []))
            prior_lines.append(
                f"- {p.get('node_id')}（{p.get('function','')}）"
                f"\n    已揭露线索：{('、'.join(p.get('reveals', []))) or '（无）'}"
                f"\n    已用选项角度：{intents or '（无）'}"
            )
        prior_block = "\n".join(prior_lines)
    else:
        prior_block = "（这是第一个节点，前面还没有已设计的节点）"

    min_opts = max(1, len(routes))
    entry_block = entry_context_block(entry_context)
    entry_section = f"\n{entry_block}\n" if entry_block else ""
    return f"""请只设计**一个** choice 节点的 Interaction Skeleton（互动骨架），**不要写正文**。

{_scene_spec_block(scene_spec)}

## 场景契约（已定，固定上下文）
{sc}
{entry_section}
## 你现在要设计的节点
node_id = **{node_id}**
固定功能（必须严格扣住）：{function}

### 本节点的出边（拓扑已定；每个 option 的 route_to 必须从这里选，每条出边至少被一个选项使用）
{route_lines}

### 拓扑分配给本节点揭露的线索
{reveals_block}

## 已设计的前序节点（你必须与它们**功能不重叠**，并遵守**线索分层**）
{prior_block}

要求：
- 写 function（一句话，呼应固定功能）/ situation（当前局面）/ choice_pressure（选择压力来源）/
  {min_opts}-5 个 option（数量灵活，由真实玩家反应数决定；每条出边至少 1 个选项；
  不为凑数发明选项；每个含 intent / payoff / cost / relationship_delta / route_to）/ reveals / hides。
- 不要重复前序节点的局面或选项角度；不要把别的分支线索提前抖出来。

按下面的输出 JSON schema 返回**单个节点对象**。
"""


def build_dynamic_node_schema(allowed_route_targets: list[str]) -> dict[str, Any]:
    """动态拓扑版单节点骨架输出契约：option 多一个 route_to（enum = 本节点出边目标）。

    选项数 1-5 灵活（作者修订 2026-06-11）：minItems = 出边数（每条出边至少 1 个选项的
    schema 层下限；出边覆盖本身由引擎 _route_violations 校验），不与出边数上绑定。
    """
    option_skeleton = {
        "type": "object",
        "required": ["intent", "payoff", "cost", "relationship_delta", "route_to"],
        "properties": {
            "intent": {"type": "string", "description": "设计意图标签（第三人称 OK），如'软问路线'"},
            "payoff": {"type": "string", "description": "能得到什么"},
            "cost": {"type": "string", "description": "要付出什么"},
            "relationship_delta": {
                "type": "string",
                "description": "对 trust/fear/cooperability/affinity 的影响 + 理由",
            },
            "route_to": {
                "enum": list(allowed_route_targets),
                "description": "本选项路由到的出边目标（拓扑已定，不得发明）",
            },
        },
    }
    return {
        "type": "object",
        "required": [
            "node_id",
            "function",
            "situation",
            "choice_pressure",
            "reveals",
            "hides",
            "options",
        ],
        "properties": {
            "node_id": {"type": "string"},
            "function": {"type": "string", "description": "一句话功能；与前序节点互不重叠"},
            "situation": {"type": "string", "description": "当前局面（谁在场/空间/风险）"},
            "choice_pressure": {"type": "string", "description": "本节点选择压力来源"},
            "reveals": {"type": "array", "items": {"type": "string"}},
            "hides": {"type": "array", "items": {"type": "string"}},
            "options": {
                "type": "array",
                "minItems": max(1, len(allowed_route_targets)),
                "maxItems": 5,
                "items": option_skeleton,
            },
        },
    }


__all__ = [
    "PASS1_SKELETON_SYSTEM",
    "PASS1_SKELETON_SYSTEM_DYNAMIC",
    "NODE_FUNCTIONS",
    "build_pass1_user_prompt",
    "build_pass1_schema",
    "build_pass1_contract_user_prompt",
    "build_pass1_contract_schema",
    "build_pass1_node_user_prompt",
    "build_pass1_node_schema",
    "build_dynamic_node_user_prompt",
    "build_dynamic_node_schema",
]
