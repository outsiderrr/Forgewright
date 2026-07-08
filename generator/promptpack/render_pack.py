"""P-A 场景级写作提示词包渲染器（T-3P-1；ADR-039 决策一，0 LLM）.

把锁定的结构骨架（structure-only design.json，含 beats_plan + run_config）确定性
渲染成**每场景一份**编剧写作提示词包 `<graph_id>.pack.md`：

  ① 任务头（结构锁定声明）② 场景契约 ③ 故事至此（便宜版连续性）
  ④ 逐节点树序填空单 ⑤ 文风与量化契约 ⑥ 输出格式段（format_spec 生成）

编剧（BYOM, bring your own model——自带模型）拿这一个 markdown 文件写正文，
按 ⑥ 的格式契约交回；回流解析与合并 = T-3P-2（不在本模块）。

设计要点（与任务规格逐条对应）：
  - **输入只经 promptpack/io.py 的两个 loader**（critique F-3；禁自写解析）；
    图级配置一律从 design.run_config 读，不另收配置参数。
  - **0 LLM、0 环境依赖**：纯确定性渲染（同输入两次渲染逐字节相等）。文风锚点
    直接读 load_anchors() 常量，不走 style_anchor_block 的
    FORGEWRIGHT_STYLE_ANCHORS 环境开关——那是生成期 A/B 实验旋钮，
    pack 渲染不受环境影响（否则确定性被环境变量打破）。
  - **文风段 = pack 内最小重述**（作者 2026-06-29 拍板，拆解 §8.8）：
    role_rules / 量化契约改写成对编剧（人）的说明书语气（原文含
    node.options[].text 等工程术语，注释标注来源行）；AP 条款与白描预设文本
    从常量**原样注入**（单一真相源，只换框架语句）；14 维 taxonomy / judge /
    完整资产重打包 = P-E，明确不做。
  - **树序遍历**借鉴 multipass/render.py 的 _walk（choice → 各 route 深先；
    beats → 整链 → next；end 叶子），另加两道 render.py 没有的输入卫兵：
    引用了不存在节点 / 存在从入口不可达的节点 → PromptpackInputError——
    不可达节点会被 pack 漏掉，编剧交稿必吃 E1（missing_node），必须在渲染期拦。

CLI（T-3P-0 约定：独立模块入口，不建共享 __main__.py；退出码三态见 format_spec）：

    python -m generator.promptpack.render_pack \
        --design <design.json> --spec <spec.json> \
        [--summaries <scene>.summary.json ...] [--out <pack.md>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from generator.context_assembler import (
    PriorSceneSummary,
    render_prior_scene_summaries_block,
    truncate_prior_scene_summaries,
)
from generator.promptpack.format_spec import (
    DIALOGUE_ITEM_PREFIX,
    ERRORS,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_USAGE,
    KEY_CONTINUE,
    KEY_DIALOGUE,
    KEY_NARRATION,
    KEY_OPTIONS,
    NODE_CATEGORY_KEYS,
    NODE_HEADER_TEMPLATE,
)
from generator.promptpack.io import (
    PromptpackInputError,
    load_design_artifact,
    load_scene_spec,
)
from generator.prompts.node.anti_pattern_blacklist import AP_TEXTS, UNIVERSAL_AP_IDS
from generator.prompts.style import load_anchors
from generator.prompts.style.presets import PRESETS
from generator.scene_summary_writer import read_summary_sidecar

# ---------------------------------------------------------------------------
# 量化文风契约（pack 内最小重述；来源 = 被退役 Pass 2 引擎的文本契约散落点，
# 拆解 §3.4 逐条：pass2_prose.py:47,57,59-60,233 / beat_pacing.py:30,37-38,42-49）
# ---------------------------------------------------------------------------

_CHOICE_NARRATION_REQ = "250-400 汉字"  # pass2_prose.py:47（写厚，别 150 字草草收尾）
_BEAT_NARRATION_REQ = "约 60-120 汉字"  # beat_pacing.py:30
_END_NARRATION_REQ = "80-200 汉字"  # pass2_prose.py:233
_OPTION_LEN_REQ = "≤25 汉字"  # pass2_prose.py:57
_CONTINUE_LEN_REQ = "≤20 汉字"  # beat_pacing.py:49

# 人称约定 D 两套并存（作者拍板 2026-06-12；pass2_prose.py:59-60）
_PERSON_CONVENTION = (
    "选择节点的选项是拿主意的话，**可以用「我」开头**（如「我不是来审你」）；"
    "对话链的接话则**第一人称隐含、别硬塞「我」**——两套约定并存，别混用。"
)

# 承接规则（beat_pacing.py:37-38）
_CARRY_RULE = (
    "第 N+1 拍的 NPC 对白必须先**承接第 N 拍玩家刚说的话**（回应它，或明确拒答），"
    "再推进新线索；不许答非所问、不许自顾自往下讲。链的第一拍同理，"
    "要承接玩家进入本链时说的那句选项台词。"
)

# 角色三分类的展示标题（与 style/__init__._ROLE_TITLES 同文案；
# 私有符号跨包不 import，此处本地定义——两处措辞改动需人工同步）
_ROLE_TITLES = {
    "narration": "旁白该写成这样",
    "npc_dialogue": "NPC 对白该写成这样",
    "player_option": "玩家选项该写成这样",
}

# 防搬运守卫（编剧版重述；来源 = style/__init__._ANTI_COPY_GUARD——原文断言样例
# 「来自其他场景」，但 pack 场景的锚点可能恰好出自本场景的已验收旧文本，
# 故改为「不一定属于本场景、事实以本包锁定内容为准」的更保守表述）
_ANTI_COPY_GUARD = (
    "下面的样例出自**已验收文本**，只示范文风、节奏与口吻。样例里的人名、地名、"
    "道具、事实细节**不一定属于本场景**——一律不得照搬进你的正文；"
    "本场景的事实以上文「结构锁定」「场景契约」「逐节点填空单」为准。"
)

# 3 分类角色守则（编剧版最小重述；来源 = prompts/node/role_rules.py 的
# ROLE_RULES_TEXT——原文是给 LLM 的工程契约（含 node.options[].text 等术语），
# 此处改写成对编剧（人）的说明书语气，条款内容一一对应、不增不减）
_ROLE_RULES_WRITER = f"""三类正文各管一摊，别越位：

**旁白（{KEY_NARRATION}）——第三人称叙述**
- 写：物理环境（光线 / 声音 / 气味 / 布置 / 时间）、客观可见的动作、玩家能直接观察到的细节。
- 不写：NPC 的内心活动（让 NPC 用话或动作带出来）；NPC 掌握的信息（必须由 NPC 在对白里自己说，
  旁白不代述——「她说莱特在人前是教授，人后是另一种人」这种写法不合规，要改成 NPC 直接说）；
  玩家的内心活动 / 价值判断（留给选项）；总结性评价（「她很狡猾」——用具体行为代替）。
- 旁白可以带 NPC 名字写动作 / 表情 / 视线 / 物理姿态（「露西把空杯子往水槽里一放」
  「她的指尖按着那张名片」），也可以以「你」为主语写玩家的身体感受（疲倦 / 寒意 / 心跳），
  但不要替玩家做价值判断或决定（「你决定要……」是错的）。
- 旁白中的玩家一律写「你」，**不得出现「玩家」二字**。

**NPC 对白（{KEY_DIALOGUE}）**
- 写 NPC 此刻说出口的话本身（必须是这个角色会说的措辞与节奏），交稿时裸正文、不带引号包裹。
- **场景的关键信息必须由 NPC 自己说出来**，不能让旁白替代。

**玩家台词（{KEY_OPTIONS} / {KEY_CONTINUE}）**
- 写玩家此刻要说的话或要做的动作本身，一律**第一人称语言**；动作可写成方括号形式
  （如「[放下几枚硬币]」「[记下路标]」）。
- 不要写成「追问 / 安慰 / 威胁 / 调查」这类第三人称意图标签。
- 如有检定标记可保留「[技能名]」前缀作为激活提示，但主体必须第一人称。"""


# ---------------------------------------------------------------------------
# 结构遍历（树序 + 输入卫兵）
# ---------------------------------------------------------------------------


def _nodes_by_id(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["node_id"]: n for n in topology.get("nodes") or []}


def _tree_order(topology: dict[str, Any]) -> list[str]:
    """树序遍历（借鉴 multipass/render.py 的 _walk）→ plan 节点 id 序列。

    两道 render.py 没有的卫兵（渲染期拦住会让编剧白写/漏写的坏结构）：
      - 引用了 topology 里不存在的节点（route.to / next 悬空）→ 报错；
      - 存在从入口不可达的节点 → 报错（pack 漏掉它，编剧交稿必吃 E1）。
    收敛路由（多个选项指向同一节点）合法：首次到达时渲染，后续入口只记不重渲。
    """
    by_id = _nodes_by_id(topology)
    order: list[str] = []
    seen: set[str] = set()

    def walk(nid: Any, via: str) -> None:
        if nid in seen:
            return
        node = by_id.get(nid)
        if node is None:
            raise PromptpackInputError(
                f"topology 里 {via} 指向不存在的节点 {nid!r}——design 结构悬空，"
                "请重跑 --structure-only 或人工修 design"
            )
        seen.add(nid)
        order.append(nid)
        kind = node.get("kind")
        if kind == "choice":
            for r in node.get("routes") or []:
                walk(r.get("to"), via=f"choice {nid!r} 的出边")
        elif kind == "beats":
            walk(node.get("next"), via=f"beats {nid!r} 的 next")
        # end：叶子，无出边

    walk(topology.get("entry_node_id"), via="entry_node_id")
    unreachable = [n["node_id"] for n in topology.get("nodes") or [] if n["node_id"] not in seen]
    if unreachable:
        raise PromptpackInputError(
            f"topology 存在从入口不可达的节点 {unreachable}——提示词包会漏掉它们，"
            "编剧交稿必然缺块（E1）；请重跑 --structure-only 或人工修 design"
        )
    return order


def _inbound_map(design: dict[str, Any]) -> dict[str, list[str]]:
    """节点 id → 入口描述列表（承接规则要可执行，编剧必须知道玩家从哪句进来）。

    choice 的入口 = 父 choice 骨架的「选项 i〔intent〕」（台词由编剧写，intent 已锁定）；
    beats 链讲完 = 其 next 节点的入口。
    """
    topology = design["topology"]
    skeletons = design.get("skeletons") or {}
    inbound: dict[str, list[str]] = {}
    for node in topology.get("nodes") or []:
        nid = node["node_id"]
        if node.get("kind") == "choice":
            options = (skeletons.get(nid) or {}).get("options") or []
            for i, opt in enumerate(options, start=1):
                to = opt.get("route_to")
                inbound.setdefault(to, []).append(
                    f"{nid} 选项 {i}〔{opt.get('intent', '')}〕"
                )
        elif node.get("kind") == "beats":
            inbound.setdefault(node.get("next"), []).append(f"{nid} 链讲完")
    return inbound


def _kind_label(node: dict[str, Any], design: dict[str, Any]) -> str:
    """节点头/去向里的人话标签：choice=选择节点·N 选项；beats=对话链·N 拍；end=终止节点。"""
    kind = node.get("kind")
    nid = node["node_id"]
    if kind == "choice":
        n = len(((design.get("skeletons") or {}).get(nid) or {}).get("options") or [])
        return f"选择节点 · {n} 选项"
    if kind == "beats":
        return f"对话链 · {len(design['beats_plan'][nid])} 拍"
    return "终止节点"


def _bullets(items: list[str] | None, empty: str = "（无）") -> str:
    if not items:
        return f"  - {empty}"
    return "\n".join(f"  - {it}" for it in items)


# ---------------------------------------------------------------------------
# ① 任务头 ② 场景契约 ③ 故事至此
# ---------------------------------------------------------------------------


def _render_header(design: dict[str, Any], total_blocks: int) -> str:
    rc = design["run_config"]
    return f"""# 写作提示词包 · {rc['graph_id']}

> 给编剧：这是一个完整场景的「填空单」，由结构锁定产物自动渲染。场景的节点、分支、
> 选项数量与去向已经**全部锁定**；你只写三类正文——旁白（{KEY_NARRATION}）、
> NPC 对白（{KEY_DIALOGUE}）、玩家台词（{KEY_OPTIONS} / {KEY_CONTINUE}）。
> 写完按「六、输出格式」整份交回（机器解析，逐字遵守）。

- 场景锚点：{rc['scene_anchor']}
- 本场 NPC：{rc['npc_name']}（{rc['speaker_ref']}）——全部对白默认出自这位 NPC，你不用写说话人
- 应交节点块：**{total_blocks} 个**（逐块清单见「六、输出格式」）

## 一、结构锁定声明（红线，违反任一条整份退回）

- **不改节点名**：`[node: …]` 的 node_id 必须与本包给定的逐字一致。
- **不增删节点**：应交 {total_blocks} 块，一块不多、一块不少。
- **不增删或调换选项序号**：每个选择节点的选项数量、顺序、意图与去向已锁定；
  台词由你写，序号与意图对应关系不变。
- 分支路由、检定、状态变更等结构字段全部由系统固定，不在你的交稿里出现。"""


def _check_contract(contract: Any) -> None:
    """B 阶段 finding（2026-07-08_T-3P-1_render_pack_review）：contract 缺失/半缺失
    不许静默降级成空契约 pack——场景契约是编剧防写崩的核心约束面，坏输入必须
    在渲染期硬报错（退出码 2 路径），不能等编剧回稿才暴露。"""
    if not isinstance(contract, dict):
        raise PromptpackInputError(
            "design.contract 缺失或不是 dict——场景契约是 pack 必备段，"
            "请先修 design.json 或重跑 structure-only"
        )
    for field in ("player_goal", "npc_goal", "npc_fear"):
        value = contract.get(field)
        if not isinstance(value, str) or not value.strip():
            raise PromptpackInputError(
                f"design.contract[{field!r}] 缺失或为空——场景契约不完整，拒绝渲染"
            )
    forbidden = contract.get("forbidden")
    if (
        not isinstance(forbidden, list)
        or not forbidden
        or not all(isinstance(x, str) and x.strip() for x in forbidden)
    ):
        raise PromptpackInputError(
            "design.contract['forbidden'] 必须是非空字符串列表（禁则为空的场景"
            "契约视为不完整，拒绝渲染）"
        )


def _render_contract(contract: dict[str, Any]) -> str:
    forbidden = contract.get("forbidden") or []
    return f"""## 二、场景契约

- **玩家目标**：{contract.get('player_goal', '')}
- **NPC 目标**：{contract.get('npc_goal', '')}
- **NPC 恐惧**：{contract.get('npc_fear', '')}
- **禁则（本场不许发生 / 不许写出的事）**：
{_bullets(list(forbidden))}"""


def _render_story_so_far(
    spec: dict[str, Any], summaries: list[PriorSceneSummary]
) -> str:
    if summaries:
        kept, _reason = truncate_prior_scene_summaries(summaries)
        prior_block = render_prior_scene_summaries_block(kept)
    else:
        prior_block = "本场景为首场（或无前情摘要）——不需要承接更早的场景。"
    character_state = spec.get("character_state") or "（无）"
    return f"""## 三、故事至此（跨场景连续性）

{prior_block}

**本场人物状态（作者手记，原样透传）**：
{character_state}"""


# ---------------------------------------------------------------------------
# ④ 逐节点树序填空单
# ---------------------------------------------------------------------------


def _fill_sheet_intro() -> str:
    return f"""## 四、逐节点填空单（树序）

三类节点各要写什么（字数等硬指标另见「五、文风与量化契约」）：

- **选择节点（choice）**：{KEY_NARRATION}（{_CHOICE_NARRATION_REQ}，写厚——每句至少承担一个功能：
  空间信息 / 视线与听觉风险 / NPC 物理状态 / 行动机会 / 可回收线索 / 少量物理异常）+
  NPC 对白（关键信息由 NPC 自己说）+ 逐条把已锁定的选项意图转写成玩家第一人称台词
  （每条 {_OPTION_LEN_REQ}）。**非开场节点的旁白不要重新做进场式全景描写**
  （不要再从门、灯光、整间屋子的布置写起），只写此刻的变化、动作与新的可观察细节。
- **对话链（beats，单选项拍）**：每拍 = 玩家看到的一屏——{KEY_NARRATION}（{_BEAT_NARRATION_REQ}，白描，
  承担空间 / 物理动作 / 可回收线索之一）+ NPC 对白 1-2 句 + 一句把对话推进到下一拍的接话
  （{KEY_CONTINUE}，{_CONTINUE_LEN_REQ}，自然口语）。写出「NPC 说一点 → 玩家接一句 → NPC 再说一点」的来回感。
  - **每拍只揭本拍锁定的线索**，不得提前揭后面拍的；线索标了残缺形态的
    （如「只给残缺记号」），只能写到该残缺程度，不得写出完整版本。
  - **承接**：{_CARRY_RULE}
  - **接话（{KEY_CONTINUE}）**：自然口语别电报体（「你为什么这么着急？」对，「为什么急？」错）；
    不把 NPC 刚说完的内容变成问题再问一遍；没有新追问点时用简短确认（「我知道了。」）或
    动作（「[记下路标]」）推进；末拍可收束。
  - 多入口的链（下面会标出）：第一拍的旁白与对白必须对每个入口都成立。
- **终止节点（end）**：{KEY_NARRATION}（{_END_NARRATION_REQ}，收束旁白——交代玩家带着什么离开、
  场景怎么收）+ NPC 收尾 0-2 句（可选；关键信息前文已给，这里不补新线索）。**没有玩家选项。**"""


def _render_choice(
    nid: str,
    design: dict[str, Any],
    inbound: dict[str, list[str]],
    entry_id: str,
) -> str:
    by_id = _nodes_by_id(design["topology"])
    sk = design["skeletons"][nid]  # loader 已保证 choice 必有骨架
    options = sk.get("options") or []
    opt_lines = "\n".join(
        f"  {i}. 〔{o.get('intent', '')}〕 → {o.get('route_to')}"
        f"（{_kind_label(by_id[o.get('route_to')], design)}）"
        for i, o in enumerate(options, start=1)
    )
    entry_line = (
        "场景开场（本场第一个节点）" if nid == entry_id else "；".join(inbound.get(nid, []))
    )
    return f"""### ◆ {nid}（{_kind_label(by_id[nid], design)}）

- 入口：{entry_line}
- 功能：{sk.get('function', '')}
- 局面：{sk.get('situation', '')}
- 选择压力：{sk.get('choice_pressure', '')}
- 本节点揭露：
{_bullets(list(sk.get('reveals') or []))}
- 不能给（留到后续节点）：
{_bullets(list(sk.get('hides') or []))}
- 选项（台词由你写；意图与去向已锁定，序号不变）：
{opt_lines}"""


def _render_beats_chain(
    nid: str,
    design: dict[str, Any],
    inbound: dict[str, list[str]],
) -> str:
    by_id = _nodes_by_id(design["topology"])
    node = by_id[nid]
    slots = design["beats_plan"][nid]
    entries = inbound.get(nid, [])
    entry_line = "；".join(entries)
    multi_entry_note = (
        "\n- 多入口提醒：本链第一拍的旁白与对白必须对上面每个入口都成立。"
        if len(entries) > 1
        else ""
    )
    beat_lines: list[str] = []
    for slot in slots:
        if slot["reveals"]:
            reveal = "；".join(slot["reveals"])
        else:
            reveal = "（无——过场拍：只做动作 / 氛围推进，不揭新线索）"
        last_note = "（末拍：接话可收束，如「我知道了。」或一个动作）" if slot["is_last"] else ""
        beat_lines.append(f"  - 〔{slot['beat_id']}〕本拍揭露：{reveal}{last_note}")
    next_id = node.get("next")
    return f"""### ─ {nid}（{_kind_label(node, design)}）

- 入口：{entry_line}{multi_entry_note}
- 功能：{node.get('function', '')}
- 链讲完去向：{next_id}（{_kind_label(by_id[next_id], design)}）
- 逐拍锁定线索（每拍只揭本拍这条，不许提前）：
{chr(10).join(beat_lines)}"""


def _render_end(
    nid: str,
    design: dict[str, Any],
    inbound: dict[str, list[str]],
) -> str:
    by_id = _nodes_by_id(design["topology"])
    node = by_id[nid]
    return f"""### ◆ {nid}（终止节点）

- 入口：{'；'.join(inbound.get(nid, []))}
- 功能：{node.get('function', '')}
- 收束要求：{KEY_NARRATION} {_END_NARRATION_REQ}，白描收束（交代玩家带着什么离开、场景怎么收）；
  {KEY_DIALOGUE} 可选 0-2 句（不补新线索）；**无选项、无接话**。"""


def _render_fill_sheet(design: dict[str, Any], order: list[str]) -> str:
    by_id = _nodes_by_id(design["topology"])
    inbound = _inbound_map(design)
    entry_id = design["topology"].get("entry_node_id")
    blocks: list[str] = [_fill_sheet_intro()]
    for nid in order:
        kind = by_id[nid].get("kind")
        if kind == "choice":
            blocks.append(_render_choice(nid, design, inbound, entry_id))
        elif kind == "beats":
            blocks.append(_render_beats_chain(nid, design, inbound))
        else:
            blocks.append(_render_end(nid, design, inbound))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# ⑤ 文风与量化契约
# ---------------------------------------------------------------------------


def _scene_call_types(design: dict[str, Any]) -> list[str]:
    """本场出现的调用类型（决定注入哪些锚点；顺序固定保确定性）。

    对应白描预设 ANCHOR_PLAN 的四个键：开场 choice → pass2_opening；
    非开场 choice → pass2_mid；beats 链 → beats；end → end。
    """
    topology = design["topology"]
    entry_id = topology.get("entry_node_id")
    kinds = {n["node_id"]: n.get("kind") for n in topology.get("nodes") or []}
    call_types: list[str] = []
    if kinds.get(entry_id) == "choice":
        call_types.append("pass2_opening")
    if any(k == "choice" for nid, k in kinds.items() if nid != entry_id):
        call_types.append("pass2_mid")
    if any(k == "beats" for k in kinds.values()):
        call_types.append("beats")
    if any(k == "end" for k in kinds.values()):
        call_types.append("end")
    return call_types


def _anchor_section(design: dict[str, Any], preset_name: str) -> str:
    """按角色挑锚点 few-shot（narration / npc_dialogue / player_option）。

    选取规则 = 白描预设 ANCHOR_PLAN 在本场出现的调用类型上的**按序并集去重**
    （单一真相源是预设的 ANCHOR_PLAN，本模块不自定锚点清单）。
    不走 style_anchor_block：那条路挂在 FORGEWRIGHT_STYLE_ANCHORS 环境开关上
    且按单调用类型注入，pack 是整场一份、渲染必须环境无关。
    """
    preset = PRESETS[preset_name]
    anchors = load_anchors()
    sections: list[str] = []
    for role in ("narration", "npc_dialogue", "player_option"):
        ids: list[str] = []
        for call_type in _scene_call_types(design):
            for aid in preset.ANCHOR_PLAN.get(call_type, {}).get(role, []):
                if aid in anchors and aid not in ids:
                    ids.append(aid)
        if not ids:
            continue
        lines = "\n".join(
            "- " + anchors[aid]["text"].replace("\n", "\n  ") for aid in ids
        )
        sections.append(f"#### {_ROLE_TITLES[role]}\n{lines}")
    if not sections:
        return ""
    body = "\n\n".join(sections)
    return f"""### 5.5 文风锚点（已验收样例——只学味道，严禁搬内容）

{_ANTI_COPY_GUARD}

{body}"""


def _ap_blocks(ids: tuple[str, ...]) -> str:
    """AP 条款文本按黑名单固定顺序原样注入（单一真相源 = AP_TEXTS）。"""
    order = [i for i in ("AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9") if i in ids]
    return "\n\n".join(AP_TEXTS[i] for i in order)


def _render_style_section(design: dict[str, Any], preset_name: str) -> str:
    preset = PRESETS[preset_name]
    quant_rows = "\n".join(
        f"| {slot} | {req} |"
        for slot, req in (
            (f"选择节点 {KEY_NARRATION}", f"{_CHOICE_NARRATION_REQ}；每句至少承担一个功能；非开场节点不重做进场式全景"),
            (f"对话链每拍 {KEY_NARRATION}", f"{_BEAT_NARRATION_REQ}；白描"),
            (f"终止节点 {KEY_NARRATION}", f"{_END_NARRATION_REQ}；收束"),
            (f"选择节点选项台词（{KEY_OPTIONS}）", f"每条 {_OPTION_LEN_REQ}；第一人称"),
            (f"对话链接话（{KEY_CONTINUE}）", f"{_CONTINUE_LEN_REQ}；自然口语别电报体"),
            (f"NPC 对白（{KEY_DIALOGUE}）", "关键信息由 NPC 自己说，旁白不抢答；对话链每拍 1-2 句"),
            ("人称（旁白）", "玩家一律写「你」，不得出现「玩家」二字"),
            ("人称（玩家台词）", _PERSON_CONVENTION),
            ("承接（对话链）", _CARRY_RULE),
        )
    )
    anchor_part = _anchor_section(design, preset_name)
    anchor_block = f"\n\n{anchor_part}" if anchor_part else ""
    return f"""## 五、文风与量化契约

### 5.1 三类正文的分工（谁能写什么）

{_ROLE_RULES_WRITER}

### 5.2 禁则 · 任何文风都不许犯

{_ap_blocks(UNIVERSAL_AP_IDS)}

### 5.3 本作文风预设：白描（预设条款；本作统一按此写）

{preset.PROSE_STYLE_RULES}

{_ap_blocks(preset.PRESET_AP_IDS)}

### 5.4 量化契约（主编按此审稿；写在指标内最省你返工）

| 槽位 | 要求 |
|---|---|
{quant_rows}{anchor_block}"""


# ---------------------------------------------------------------------------
# ⑥ 输出格式段（由 format_spec 常量生成；与 format_contract_sample.md 同源对齐）
# ---------------------------------------------------------------------------


def _node_categories(design: dict[str, Any], order: list[str]) -> list[tuple[str, str, int]]:
    """树序展开成**成品图节点块**清单：(node_id, category, 选项数)。

    beats 链在成品图里是逐拍微节点（{{pid}}_b{{i}}，beats_plan 已锁定），
    编剧对每拍交一块；choice / end 与 plan 节点同名同块。
    """
    by_id = _nodes_by_id(design["topology"])
    rows: list[tuple[str, str, int]] = []
    for nid in order:
        kind = by_id[nid].get("kind")
        if kind == "choice":
            n = len((design["skeletons"].get(nid) or {}).get("options") or [])
            rows.append((nid, "choice", n))
        elif kind == "beats":
            for slot in design["beats_plan"][nid]:
                rows.append((slot["beat_id"], "beat", 1))
        else:
            rows.append((nid, "end", 0))
    return rows


def _keys_desc(category: str, n_options: int) -> str:
    """一个节点块「应交 key」的人话描述——直接从 NODE_CATEGORY_KEYS 生成（单一真相源）。"""
    parts: list[str] = []
    for key in NODE_CATEGORY_KEYS[category]["required"]:
        if key == KEY_OPTIONS:
            parts.append(f"{key}（序号 1..{n_options} 连续完整）")
        else:
            parts.append(key)
    desc = " + ".join(parts)
    optional = NODE_CATEGORY_KEYS[category]["optional"]
    if optional:
        suffix = "（0-2 行）" if category == "end" else ""
        desc += "；" + " / ".join(optional) + f" 可选{suffix}"
    return desc


def _template_block(node_id: str, category: str, n_options: int) -> str:
    """一个节点的交稿模板块（把 <…> 换成正文）。

    dialogue 块只进 choice / beat 模板（关键信息由 NPC 说，基本必写）；
    end 默认不带（可选 0-2 行，需要的自行加）——避免编剧留下空 `- `（E7）。
    """
    lines = [NODE_HEADER_TEMPLATE.format(node_id=node_id), f"{KEY_NARRATION}: <…>"]
    if category in ("choice", "beat"):
        lines.append(f"{KEY_DIALOGUE}:")
        lines.append(f"  {DIALOGUE_ITEM_PREFIX}<…>")
    if category == "choice":
        lines.append(f"{KEY_OPTIONS}:")
        lines.extend(f"  {i}: <…>" for i in range(1, n_options + 1))
    elif category == "beat":
        lines.append(f"{KEY_CONTINUE}: <…>")
    return "\n".join(lines)


def _render_format_section(design: dict[str, Any], order: list[str]) -> str:
    rc = design["run_config"]
    rows = _node_categories(design, order)
    checklist = "\n".join(
        f"- `{NODE_HEADER_TEMPLATE.format(node_id=nid)}` → {_keys_desc(cat, n)}"
        for nid, cat, n in rows
    )
    error_rows = "\n".join(
        f"| {e.code} | {e.slug} | {e.meaning} |" for e in ERRORS.values()
    )
    templates = "\n\n".join(_template_block(nid, cat, n) for nid, cat, n in rows)
    return f"""## 六、输出格式（交稿必读；机器解析，逐字遵守）

交稿 = 一份纯文本：对下面清单里的**每个节点**交一个块，块与块顺序随意，
node_id 必须与清单逐字一致；不得增删节点、不得增删或改动选项序号。

语法（四个 key，只有这四个）：

```
{NODE_HEADER_TEMPLATE.format(node_id='<node_id>')}
{KEY_NARRATION}: <旁白正文>
{KEY_DIALOGUE}:
  {DIALOGUE_ITEM_PREFIX}<NPC 的一句话>
{KEY_OPTIONS}:
  1: <玩家第一人称台词>
{KEY_CONTINUE}: <接话>
```

- `{KEY_NARRATION}:` 的值从冒号后开始，**允许多行**，直到下一个 key 行或下一个
  `[node: …]` 为止（多行值只有 {KEY_NARRATION} 有）。
- `{KEY_DIALOGUE}:` 块每行以 `{DIALOGUE_ITEM_PREFIX}` 开头，**裸正文不带引号包裹**（「」/“”都不要）；
  说话人不用写——本场对白统一是 {rc['npc_name']}（{rc['speaker_ref']}）。
  0 行时整块省略，**不要留空的 `{DIALOGUE_ITEM_PREFIX.strip()}`**。
- `{KEY_OPTIONS}:` 序号行形如 `1: 台词`，一行一条写完；序号必须从 1 连续编到 N，不多不少。
- `{KEY_CONTINUE}:` 一句短话或动作，一行写完，不编号。
- `{KEY_CONTINUE}` 的值、{KEY_OPTIONS} 序号行、{KEY_DIALOGUE} 行都是**单行值**，
  换行续写会被判 E8（无法归属的游离行）。

### 本场应交清单（{len(rows)} 个节点块）

{checklist}

### 硬报错代码（任一条 → 整份退回重交，不落地）

| 代码 | 名称 | 含义 |
|---|---|---|
{error_rows}

### 交稿模板（复制整段，把 <…> 换成正文）

（{KEY_DIALOGUE} 块可选：该节点 NPC 不说话就把 `{KEY_DIALOGUE}:` 与其 `{DIALOGUE_ITEM_PREFIX.strip()}` 行整块删掉；
NPC 说几句就写几行 `{DIALOGUE_ITEM_PREFIX}`。end 节点模板未带 {KEY_DIALOGUE}，需要收尾 0-2 句可自行加块。）

```
{templates}
```"""


# ---------------------------------------------------------------------------
# 整包渲染 + CLI
# ---------------------------------------------------------------------------


def _render_with_stats(
    design: dict[str, Any],
    spec: dict[str, Any],
    summaries: list[PriorSceneSummary] | None,
    *,
    preset: str,
) -> tuple[str, int]:
    """渲染 + 返回 (pack 文本, 节点块数)——块数与正文同一次遍历得出，防两处计数漂移。"""
    summaries = summaries or []
    order = _tree_order(design["topology"])
    total_blocks = len(_node_categories(design, order))
    sections = [
        _render_header(design, total_blocks),
        _render_contract(design.get("contract") or {}),
        _render_story_so_far(spec, summaries),
        _render_fill_sheet(design, order),
        _render_style_section(design, preset),
        _render_format_section(design, order),
    ]
    return "\n\n".join(sections) + "\n", total_blocks


def render_pack(
    design: dict[str, Any],
    spec: dict[str, Any],
    summaries: list[PriorSceneSummary] | None = None,
    *,
    preset: str = "baimiao",
) -> str:
    """结构锁定 design + scene spec（+ 可选前情摘要）→ 整场写作提示词包 markdown。

    纯确定性：同输入两次渲染逐字节相等（无时间戳 / 无环境依赖 / 无随机性）。
    输入 dict 必须来自 promptpack.io 的两个 loader（形态校验在 loader 边界做；
    contract 完整性属 P-A 本地约束面，在此处把关——B 阶段 finding）。
    """
    _check_contract(design.get("contract"))
    return _render_with_stats(design, spec, summaries, preset=preset)[0]


_SUMMARY_SUFFIX = ".summary.json"


def _load_summary_sidecar(path: Path) -> PriorSceneSummary:
    """--summaries 的单个 sidecar 路径 → PriorSceneSummary（复用 scene_summary_writer 读取器）。

    read_summary_sidecar 收 scene 路径、自行拼 sidecar 名，故此处从 sidecar 路径
    反推 scene 路径（<name>.summary.json → <name>.json），读到的就是给定文件本身。
    显式给出的 sidecar 不存在 / 内容坏 = 输入错误（不静默跳过）。
    """
    if not path.name.endswith(_SUMMARY_SUFFIX):
        raise PromptpackInputError(
            f"{path}: --summaries 只接受 <scene>{_SUMMARY_SUFFIX} sidecar 路径"
        )
    scene_path = path.with_name(path.name[: -len(_SUMMARY_SUFFIX)] + ".json")
    try:
        summary = read_summary_sidecar(scene_path)
    except (ValueError, OSError) as e:
        # ValueError 含 json.JSONDecodeError（sidecar 在但内容坏）；OSError 覆盖
        # 权限/目录等读失败——统一归"输入错误 → 退出码 2"，不裸 traceback
        # （与 io._load_json 的异常面口径一致）
        raise PromptpackInputError(f"{path}: sidecar 读取失败或内容不合法（{e}）") from e
    if summary is None:
        raise PromptpackInputError(f"{path}: sidecar 文件不存在")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.promptpack.render_pack",
        description="P-A 写作提示词包渲染器（0 LLM）：structure-only design.json → <graph_id>.pack.md",
    )
    parser.add_argument(
        "--design", type=Path, required=True,
        help="structure-only 产物 design.json（wrapper 形态，含 beats_plan + run_config）",
    )
    parser.add_argument(
        "--spec", type=Path, required=True,
        help="场景 spec JSON（{config, spec} wrapper；config 与 design.run_config cross-check）",
    )
    parser.add_argument(
        "--summaries", type=Path, nargs="+", default=[],
        help=f"前情摘要 sidecar（<scene>{_SUMMARY_SUFFIX}）路径，按时间顺序给",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="输出路径（默认 = design.json 同目录 <graph_id>.pack.md）",
    )
    args = parser.parse_args(argv)

    try:
        design = load_design_artifact(args.design)
        spec = load_scene_spec(args.spec, design=design)
        summaries = [_load_summary_sidecar(p) for p in args.summaries]
        text, total = _render_with_stats(design, spec, summaries, preset="baimiao")
    except PromptpackInputError as e:
        print(f"输入错误：{e}", file=sys.stderr)
        return EXIT_USAGE

    out = args.out or args.design.parent / f"{design['run_config']['graph_id']}.pack.md"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    except OSError as e:
        print(f"写入失败：{out}（{type(e).__name__}: {e}）", file=sys.stderr)
        return EXIT_REJECTED  # 非输入错的运行失败 → 1（退出码三态约定）
    print(f"已渲染写作提示词包：{out}（{total} 个节点块）")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["render_pack", "main"]
