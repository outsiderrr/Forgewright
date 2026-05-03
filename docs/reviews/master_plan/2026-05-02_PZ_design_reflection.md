# Project Zomboid 设计反思 + §9.2 长对话一致性延伸

> 2026-05-01/02 L1 规划讨论结论。给阶段 2/3 规划师起手时阅读，作为 synthesis §6/§7 占位指针的具体延伸输入。
>
> **本备忘不修改 L1 文档**（CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md）。备忘内任何条目要落地为 ADR / ROADMAP 修订须由作者明示授权 + 走专门执行会话。

**日期**：2026-05-02 · **版本**：v0.1 · **产出方**：L1 规划讨论会话（master plan 续接）
**触发问题**：作者从《Project Zomboid》（PZ）机制反思 Forgewright 架构；引出系统时钟概念 + §9.2 长对话一致性深入讨论 + 涌现叙事 sibling 项目可行性

---

## 1. 背景与讨论范围

作者接触 PZ（Steam 沙盒生存游戏，无显式剧情树却能持续涌现剧情），希望从架构层面反思 Forgewright。讨论按"哪些可借 / 哪些不可借 / 哪些是另一个项目"三层展开。

讨论**有意识守住**：

- ADR-001（玩家交互预生成选项式）
- ADR-002（运行时无 LLM）
- ADR-006（本体 SOT）
- ADR-008（LLM 不写状态）
- DEBATE §1（运行时模拟方向已彻底排除）

任何 PZ 启发的"运行时涌现"想法**只在生产期借鉴**，或作为未来 sibling 项目（§6）。

---

## 2. PZ 四层模型 vs Forgewright 架构映射

PZ 的"涌现叙事"= 四层耦合：World Substrate / Rule Layer / Character Build / Stochastic Sources。这条路 DEBATE §2 已经讨论过——评审者 Gemini 当时主张的"自下而上 Agent 模拟"就是 PZ 极致形态，结论 = **plot-centric 骨架 + character-centric 肌肉共存**。

四个 Forgewright 与 PZ **不能直接套**的根本差异：

| 维度 | PZ | Forgewright |
|---|---|---|
| NPC | 几乎缺位（B41 之前无；设计选择，避开 NPC 让涌现更稳） | NPC-heavy RPG，必须有；DEBATE §2 双失败模式都打在这层 |
| 玩家叙事化 | 玩家心智补足；系统不"产出"故事 | 玩家点选项；不要求玩家 RP；故事必须**预生成时就在** |
| 终结锚点 | 永久死亡（强制叙事压缩） | save/load 多周目；无压缩器，靠编剧理论 + 阵营时钟填补 |
| 长期目标 | 真空（玩家自定） | 显式英雄旅程（BG3 路线） |

**结论**：PZ 是参照系，不是模板。

### PZ 涌现的根本原因（权重排序）

不是单一原因，是组合。我的权重：**(B) 时间确定性退化 > (D) 永久死亡+目标真空 > (C) 特性钩子 > (A) 系统耦合**。

关键洞见——**(B) 是把"叙事"内化进系统而非剧本的关键变压器**。电力 9 天后中断 = 三幕剧机械化进时钟。其他三层 Forgewright 都已有等价物（编剧理论插件 / 角色卡 / 状态总线）。

**对 Forgewright 的实操含义**：从 PZ 借的就一件事——**节奏内化进系统**（=系统时钟）。详见 §3 + §4。

---

## 3. 对阶段 2 规划师的可执行输入

> 阶段 2 启动闸门 C1（synthesis §6 / ROADMAP §阶段 2）当前列 character / location / relation / state path 四级；下面三条建议**扩展或细化** C1 范围。最终采纳由阶段 2 规划师立 ADR-016+ 拍板。

### 3.1 把"系统时间"加进 C1 本体最小契约

C1 当前**无时钟概念**——这是 synthesis §6 一个隐藏洞。Forgewright 状态总线缺一个**叙事推进单元**作为基础时间轴，所有阵营时钟（DEBATE §6.1 已纳入）+ 节奏控制 + tick effects 都依赖它。

**作者拍板**（2026-05-02）：双轨

- `world.scene_count`（每场景退出 +1）= 被动节奏
- `world.long_rest_count`（玩家显式长休 +1）= 玩家节奏控制感

参考 BG3 长休机制——"时间"在 RPG 是**叙事推进单元**，不是物理时间。**不要做实时计时器**（不符合 RPG 传统、违反 ADR-002 极简运行时）。

### 3.2 时钟 schema 草图

基于 §3.1 的系统时间，叠时钟层级：

```json
"clocks": {
  "world": [...],          // 宏观世界时钟：神性危机 / 大逃亡浪潮 / 季节
  "faction": [...],        // 派系时钟（DEBATE §6.1 PbtA Faction Clocks）
  "environmental": [...]   // 环境时钟（PZ 同源）：基础设施 / 物资 / 道路
}
```

每个 clock 形态：

```json
{
  "id": "infrastructure_decay",
  "name": "基础设施衰退",
  "ticks_total": 9,
  "ticks_current": 0,
  "advance_rule": {
    "type": "every_n_scenes" | "on_long_rest" | "on_faction_action" | "on_player_choice",
    "params": {...}
  },
  "tick_effects": [
    {"at_tick": 9, "effect": "set", "path": "world.power", "value": false}
  ]
}
```

**`advance_rule.type` 是关键插件位**——Forgewright 应该**默认只做 event_based 类**（运行时是 JSON 播放器，"时间"是场景跳转或玩家选择数；不存在真时间步进）。

### 3.3 关系层加 `narrative_weight` 字段

DEBATE §6.5 接受了关系图谱概念，但没给 schema。建议草图：

```json
"relations": [{
  "from": "vellin", "to": "corvan",
  "type": "feud",      // feud / kinship / debt / romance / faction_member
  "strength": 0.8,     // 0-1
  "history": ["event_id_1"],
  "narrative_weight": "core"   // core / minor / context_only
}]
```

**`narrative_weight = core`** 的关系生产期 LLM 必须显性体现；`minor` 可选；`context_only` 仅作一致性 anchor。让作者控制"哪些关系真的进戏"，避免 LLM 把所有关系都写进每场对白污染节奏。这是 Stage 1 R3/R4/R5 prompt 治理的延长线。

### 3.4 风险提醒（隐藏闸门）

时钟系统有**爆炸的 tick_effects 让阶段 2 图论校验器爆炸**的风险——每个 tick effect 都成新状态分支，"任意合法状态组合下至少 1 个结局可达"会从难变到不可判定（**Round 5 U-GPT-1** 已标，DEBATE_NOTES.md:299）。

**时钟设计预留约束**：

- 每个 clock `ticks_total` 上限（建议 ≤ 20）
- 同时活跃 clocks 数上限（建议 ≤ 10）
- 否则 synthesis §6 推荐的 ADR-009 第二层拆 2A 拓扑 + 2B 抽样验证 / 有界符号执行 落不下来

---

## 4. "特性即故事钩子"——Stage 2 prompt 治理延长线

PZ 的角色特性（吸烟者 / 恐血症 / 急性子）作为**剧情触发器**而非数值修正。Forgewright Stage 1 R3/R5 已经看到反面教训——LLM 把特性当属性而非戏剧约束。

prompt 改造方向（**不立 ADR**，归 Stage 2 prompt 治理延长线）：

- ❌ "vellin 有恐血症特性"
- ✓ "vellin 见血必触发显性心理反应（颤抖 / 回避 / 战斗失误）。任何含血腥的场景，必须在选项或对白中体现这个反应——这是 vellin 的 dramatic differentiator，不可省略"

**Schema 配套**（推到 Stage 2/3 立 ADR）：character 实体加 `dramatic_triggers: [{trait, when, how}]` 字段，让特性显式承载戏剧化义务。

---

## 5. §9.2 长对话一致性延伸讨论

> 起源：作者听完 §9.1/§9.2/§9.3 三条未解后提出"恒定信息记进文档贯穿场景"思路，问是否被否决。深入讨论后落地为本节。

### 5.1 作者的方案就是当前 Forgewright 架构的核心

| 作者列举要素 | Forgewright 现有承载 | ADR |
|---|---|---|
| 玩家与阵营关系 | `/state/ontology/` 派系关系（本体）| ADR-006 |
| NPC 好感度 | 状态总线 `npc.<id>.affinity` | ADR-008 |
| 职业等级 / 技能 / 属性 | 状态总线 `pc.*` | ADR-008 |
| 永久身体属性（断腿）| 状态总线 + 不可逆 effect 标记 | ADR-008 + state op 白名单 |

**作者独立推到 ADR-006/008 = 架构验证**。这套架构**已经在做**——但仍然不够。问题不在架构，在 LLM 实操。

### 5.2 §9.2 仍然未解的 4 个局限

1. **prompt 越长注意力衰减越严重**（lost in the middle）——84K token prompt 装得下 ≠ LLM 看得清；中段事件大概率被淹没
2. **状态丢因果链**——状态总线是结果快照，不带因果。LLM 拿到 `injuries.left_leg = severed` + `combat_willingness = -50` 可能编造非腿伤的政治原因
3. **维护成本**——"恒定文档"谁记？作者人脑也会失忆；LLM 自动维护 = Generative Agents memory stream，提炼本身漂移；混合方案才可行
4. **状态空间爆炸 vs C1 边界**——每加一维状态都涨 schema 复杂度 + 校验难度（U-GPT-1）+ LLM 注意力分配难度。Stage 2 必须划清楚哪些进 schema、哪些进运行时但不进生成 prompt

### 5.3 §9.2 不是"没人想到"，是 LLM 实操开放问题

学术界 + 工业界都打这道墙：Generative Agents 2023 / RAG-based memory 2024 / Westworld 类项目 / CK 系列。**所有缓解策略都解一部分，没一个根治**——这才是"未解"的真实形态。

### 5.4 阶段 3 规划师必立 ADR 的 4 候选（U-CL-5）

ROADMAP §阶段 3 已增订占位指针（ROADMAP.md:211）。阶段 3 规划师起手必立 ADR，4 候选：

- **A. Generative Agents memory stream**（Park 2023）：每 NPC 多层级 memory items（episodic / semantic / reflective）
- **B. RAG over event log**：所有过往场景 embed，按相关性 retrieve 进 prompt
- **C. Author-side discipline**：作者人工审阅时担任长期记忆守护者
- **D. Hybrid (A + C)**：generator 自动 retrieve，作者兜底

**讨论中推荐 D**——纯自动化撞 §9.2 死墙；纯人工拖死 Stage 3 节奏。最终拍板归阶段 3 规划师。

---

## 6. 涌现叙事 sibling 项目备忘（未来 fork）

讨论中作者假设"另起项目支持运行时涌现剧情"——玩家在大逃亡背景下三选一（帮助 / 劫掠 / 世外桃源）。结论 3 句：

1. **这是派系级涌现，不是个体角色弧线涌现**——已解决问题（CK 系列做了 20 年），不是 §9.1/§9.2/§9.3 撞墙的那种
2. **NPC 用反应式即可**——三种位置（反应式 / 关系式 / 主动式），派系级涌现 + 反应式 NPC 够用；主动式 NPC 反而引发 DEBATE §2 叙事坍缩
3. **不是 Forgewright 延伸，是 sibling**——共享世界本体 + 编剧理论插件，但运行时完全不同（Forgewright = JSON 播放器；sibling = simulation runtime + 关系图 + 阵营时钟）

**强约束**：

- **不在 Stage 2/3 schema 里"预留"涌现接口**——premature abstraction，会毁当前简洁性
- **等阶段 4 完成 + Forgewright v0.1 开源剥离后再考虑 fork**——是 child 还是 sibling 到时拍板
- 可能映射到 ROADMAP 总览 C7 拆估的 "内容/开源另 6–10 月" 之后的更远路径

---

## 7. 作者态度记录（2026-05-02）

> 阶段 3 规划师起手时（最早可能 2026 年底 / 2027 年初）的视角可能与今天不同——AI 能力进化快，本节存作者今天的判断，避免被"未来作者"当成"现在仍然适用"的硬约束。

- **对 AI 能力进化有信心**——尤其"判断已有上下文 + 逻辑自洽"这条能力，作者认为当前不足但**进化空间大**。如果阶段 3 起手时（未来某 LLM 版本）这条能力已显著超过 2026-05 水平，§9.2 缓解 ADR 的紧迫度可降级
- **50-100 场景规模可能不撞 §9.2 真墙**——作者估计 ADR-010 锁定的 MVP 规模积累不到 84K token 状态量级。**这判断暂未验证**，等阶段 3 实测一周 10 场景的真实 token 累积曲线后才能确认
- **状态文件过长可再做一层抽象**——作者倾向"真遇到再说"，不预防性设计。这与 ADR-004 极简精神一致（不为"理论可能问题"提前架构）；但也意味着阶段 3 规划师必须保留**抽象层 hook**，避免阶段 3 中段才发现要重做
- **Sibling 涌现项目**——作者现阶段不投入；但保留为长期可能性

---

## 8. 与现有 L1 文档的兼容性

本备忘不与任何 L1 文档冲突：

- **DEBATE §2**（plot/character 共存）：本备忘 §2 + §6 延伸，未推翻
- **DEBATE §6.1**（PbtA Faction Clocks）：本备忘 §3 + §4 给 schema 草图细化
- **DEBATE §6.5**（关系图谱）：本备忘 §3.3 给 schema 草图
- **DEBATE §9**（三条未解）：本备忘 §5 给阶段 3 ADR 候选清单
- **ADR-001/002/006/008**：本备忘 §1 + §6 显式守住
- **Round 5 synthesis §6**（C1 启动闸门）：本备忘 §3.1/3.2 是延伸输入
- **Round 5 synthesis §7**（C2 阶段 3 完成标志）：本备忘 §5.4 给候选具体化
- **U-GPT-1**（ADR-009 第二层拆 2A/2B）：本备忘 §3.4 给约束建议
- **U-CL-5**（§9.2 路线图无缓解措施）：本备忘 §5.4 给 ADR 候选

**未来升格路径**：本备忘任何条目升格为 ADR-016+ / ROADMAP 修订须由作者明示授权 + 专门执行会话执行（参考 ADR-011/012/013/014/015 合入先例：commit `1d2030f` / `77a5f54` / `9851419`）。

---

## 9. 修订记录

- **2026-05-02 v0.1**：初版。基于 2026-05-01/02 L1 规划讨论（PZ 启发 + §9.2 延伸 + sibling 项目假设）落盘。讨论中作者拍板的内容（§3.1 双轨系统时间 / §6 sibling 不投入 / §7 态度记录三条）已固化。其余条目作为给阶段 2/3 规划师起手时的输入参考，最终落地由对应规划师立 ADR。

---

## 版本

本文件版本：v0.1
最后更新：2026-05-02
