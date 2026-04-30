# HANDOFF_STAGE_1_TO_2.md

> 阶段 1 规划师会话 → 阶段 2 规划师会话的交接档。
> 让下一个规划师不继承阶段 1 上下文也能快速上手。

**日期**：2026-04-30（v0.2 修订同日） · **版本**：v0.2 · **产出方**：阶段 1 规划师会话（v0.2 修订：Round 5 L1 实施会话，针对 Round 5 synthesis U-GPT-2 修过期 1.5 sequencing 叙述；其余条目保留 v0.1 文本）

---

## 项目是什么（三句话）

Forgewright 是一条 AI 辅助的分支叙事 RPG 内容生产流水线。短期用于作者本人一款类 BG3 的中小型 RPG；长期剥离出通用框架开源。核心价值不在游戏运行时，在内容生产期的工具链。

阶段 1 已落地"单节点 AI 文本生成"；阶段 2 是**场景级 AI 生成 + 图论校验**——一次生成一棵完整对话树，并保证图拓扑合法。

## 玩家交互模式铁律（别重开讨论）

预生成选项式——玩家点 3–6 个预生成选项。**运行时无 LLM 调用**。任何"反欺诈"/"实时生成"/"流式对齐"提议本项目都不适用，见 DEBATE_NOTES §1 已彻底排除。

## 阶段 1 做了什么（别重建）

14 次 commit，约 2200 行业务代码 + 7 份新文档。主线：

- `/generator/` 模块从无到有：模块骨架、Pydantic 自动生成、LLMProvider Protocol + GeminiProvider、budget.py 成本守卫、generate_node 主函数（B+ 上下文 + 重试循环）、experiment + review_cli + metrics 工具链
- 配套 ADR：011（Provider 可插拔）/ 012（成本治理）/ 013（Structured Output）
- AI-as-judge 替代人工审阅：21 维度 / 5 类评分体系
- 验收：`/docs/STAGE_1_ACCEPTANCE.md`（有条件通过：schema 85% / 接受率 100%）

## ▶ 阶段 1.5 与阶段 2 sequencing（2026-04-30 v0.2 修订；ADR-014 + ADR-015）

> **v0.1 原文（已过期）**：阶段 1.5 因等待图像生成 API 被推迟。
> **v0.2 现状**：阶段 1.5 已通过 **ADR-014 双模生成策略**（manual 主线 + API 后置）解除资金阻塞——manual 模式不依赖 OpenAI key，作者用 ChatGPT Plus 网页 + import CLI 即可走通流水线。1.5 不再被推迟，已规划为 forward 主线（详见 `/docs/STAGE_1.5_TASKS.md` v0.1）。

按 **ADR-015**（阶段 1.5 与阶段 2 sequencing）：

- **1.5 manual 主线先启动**——为 forward 实施主线
- **阶段 2 规划层工作可并行起草**——本体最小契约 / 角色槽位 ADR / synthesis §6 启动闸门细化等可在 1.5 实施期间由阶段 2 规划师并行推进；**实际 schema commit 等 1.5 验收**（遵守阶段 0/1.5 串行卡口先例）
- **路径来源**：ADR-014（双模生成）+ ADR-015（sequencing）+ Round 5 synthesis §10（启动建议）+ §9.1（已闭环开放决策）

**对阶段 2 规划师的影响**：
- 阶段 1.5 的 HANDOFF 已存在于 `/docs/HANDOFF_STAGE_1_TO_1.5.md`，**不要清理它**
- 阶段 2 工作不依赖视觉资产，规划层可并行起草；schema 实际 commit 串行
- **但阶段 2 规划师需要预留接口**：本体角色 Schema 在阶段 2 若被动到，应预留 `visual_assets` 字段（即使是空数组），便于 1.5 后续插入而无需 MAJOR bump
- 当 1.5 与 2 都完成时，作者再决定哪个先合入主分支（可能涉及小规模 schema 合并）
- **阶段 2 启动闸门**（C1 本体最小契约 / C3 R 项 cleanup gate / U-GPT-1 ADR-009 第二层拆 2A/2B / U-GPT-4 baseline 协议 / U-GPT-5 角色槽位持久化形态 等）由阶段 2 规划师基于 Round 5 synthesis §6 落地——见 ROADMAP 阶段 2 「启动闸门（Round 5 综合后）」小节占位指针

## 阶段 1 收尾时的架构遗留（R1–R8）

来自 `/docs/STAGE_1_ACCEPTANCE.md` §4。**阶段 2 规划师需要把 R1–R5/R7/R8 中的多数显式纳入阶段 2 任务清单**：

| 编号 | 内容 | 阶段 2 该不该处理 |
|---|---|---|
| **R1** | Schema 合格率 85%（目标 95%） | **是**：阶段 2 起手 prompt 调优可顺手补；R2/R3/R4 是其根因 |
| **R2** | 复合 condition few-shot 缺失 | **是**：补 1–2 个手写复合 condition few-shot 示例 |
| **R3** | 选项过长（5/13 节点 ≥ 27 字） | **是**：system prompt 加 ≤25 汉字硬约束 |
| **R4** | location_ref 错配（fixture 缺 location_candidates） | **是**：fixture 改成 location_candidates 数组形态 |
| **R5** | 本体污染（D1） | **强相关**：阶段 2 是本体 Schema 落地的好时机（ADR-006 真正的本体 Schema），见下方 §警示 |
| R6 | AI 判官替代人工 | 否（已生效；阶段 4 真用户反馈再校准） |
| **R7** | cost_log 高估 | **是**：阶段 2 启动前去 Google AI Studio 控制台对账；接入 usage_metadata 反向更新 |
| **R8** | 机械预检器（option 长度 / path 前缀 / bond ID 白名单） | **是**：阶段 2 工程化；在 generator 调 LLM 判官前先跑机械检查 |

**Stage 2 起手清理 PATCH 强烈建议含**：R2 / R3 / R4（这三条是 R1 的根因，修了 R1 自然过线）、R8（机械预检器）。R5 / R7 视规划师与作者校准。

## 阶段 2 启动条件（摘自 ROADMAP §阶段 2）

**目标函数**：
- `generate_scene(scene_setting, target_beats, participating_npcs) -> DialogueGraph`
- 输入：场景设定 + 目标节拍 + 参与 NPC
- 输出：通过 Schema 校验 + 通过图论校验的完整对话树
- **单次生成人工可接受率**：≥ 70%（高于阶段 1 的 50%）

**图论校验器要实现**（阶段 2 主交付物之二）：
- 前置条件路径闭合校验：每个 option 的 condition 在某条从 entry 出发的路径上可被满足
- 不可达节点检测：从 entry 出发的图遍历找出无法到达的节点
- 死锁检测：非 end 节点，所有 option 的 condition 在当前路径状态下均不可满足
- 分支收敛性校验：识别"多路径汇合"模式（BG3 式剧情容错）

**重点工作**：
- **新增 ADR**：角色槽位（role slot casting）与动态选角——支持 BG3 式"同一剧情功能由不同角色填充"模式
- **validator 扩展**：结局可达性保证（graceful degradation validation）——证明任意合法状态组合下至少有 1 个结局可达

**禁止事项**：
- 不得跨场景生成（阶段 3 再做）
- 不得处理多场景一致性（阶段 3 再做）
- Chapter/Act 层级结构是阶段 3 的事，阶段 2 只生成单场景

## ⚠️ Schema 扩展警示（CLAUDE.md 规则 2 + 9 的特殊情况）

**阶段 2 可能动 Schema 的两处**：

1. **角色槽位 Schema**（ADR-014 候选；新增字段或新 schema 文件）—— 由作者在 ROADMAP 「阶段 2 重点工作」隐含授权；规划师产出 ADR 时需要作者明确批准 schema 变更
2. **本体 Schema 真正落地**（ADR-006）—— 阶段 0/1 是桩；阶段 2 起作者**可能**要求落地真正的本体 Schema（角色花名册、地点、物品、派系关系、时间线）。这是较大改动，**规划师应先与作者确认是否在阶段 2 范围内**

**未授权改动**（即便阶段 2 内）：
- DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 任何已有字段（这些是阶段 0 锁定的核心 schema）
- CLAUDE.md / DECISIONS.md（除新增 ADR 外）

**Schema 升级走 MINOR bump**（schema_version 0.1.x → 0.2.0）若有任何字段新增。

## 阶段 2 规划粗想（给下一个规划师做参考，不照抄）

下一个规划师应按阶段 0/1 规划师的开场流程：**先读全部元文档 → 给作者理解确认 → 等作者校准 → 再规划**。下面是阶段 1 规划师对阶段 2 任务拆分的**粗预判**，**未与作者校准过**：

### 关键架构决策（需作者拍板）

1. **场景生成策略**：
   - **A. One-shot**（单次 LLM 调用生成整张图）：简单、原子性；但 token 巨大，复合 condition 出错率会再涨
   - **B. Iterative**（按节点逐个生成 + 上下文链）：复用 generate_node；但需协调 target_node_id ⇄ node_id 一致性
   - **C. Skeleton-first**（先 LLM 生成图骨架，再逐节点填内容）：分离结构与内容；中间产物可校验
   - **粗推荐**：C，最符合"plot-centric 骨架 + character-centric 肌肉"（DEBATE §2）
2. **图论校验器位置**：
   - **A. 扩展 /validator/**（新增 graph 层方法）：与现有 validator 一致
   - **B. 新建 /generator/scene_validator.py**：与生成耦合更紧
   - **粗推荐**：A，保持 /validator/ 作为图论真相之源
3. **角色槽位 Schema 形态**：
   - 候选 A：在 character entity 加 `slot_tags: ["confidant", "antagonist", ...]`
   - 候选 B：独立 `role_slot.schema.json`，引用 character_ref
   - 这是新 ADR 的核心议题，规划师应给作者列利弊
4. **R7 cost_log 校准窗口**：
   - 阶段 2 起手前要不要花 30 分钟去 Google AI Studio 控制台对账，校准 cost_log 高估幅度？
   - 如果校准发现 cost_log 高估 30%+，预算治理需要重新设计
5. **是否在阶段 2 落地真正的本体 Schema (ADR-006)**：
   - 规划师必须确认；阶段 0 桩可能不足以支撑场景级生成
   - 如果落地，工作量预估 +30%

### 任务拆分粗预判（阶段 1 是 8 任务，阶段 2 估计 10–14 任务）

- T-2.0：起手清理 PATCH（R2 复合 condition few-shot + R3 选项长度硬约束 + R4 location_candidates）
- T-2.1：新 ADR（角色槽位 + 场景生成策略；可能含 ADR-014 / 015）
- T-2.2：可能的本体 Schema 落地（取决于作者校准）
- T-2.3：图论校验器扩展（/validator/ graph 层）
- T-2.4：scene 级 prompt 模板 + skeleton-first 生成策略实现
- T-2.5：generate_scene 主函数
- T-2.6：R8 机械预检器
- T-2.7：scene 级 experiment + review CLI 扩展
- T-2.8：场景级 AI 判官 prompt（如何评一棵图，比 21 维度评单节点更复杂）
- T-2.9：阶段 2 验收报告

## 与作者协作的风格备忘（继承自阶段 0/1）

- **作者不会编程**。所有代码产出通过执行会话完成；规划师的输出是任务拆解 + 提示词，不写代码
- 作者偏好快速决策：要推荐值让他拍板；不喜欢"每项都分析一遍"——给利弊 + 推荐，由他"全同意"或逐条改
- 作者打字偶尔有错字（GitHub 账号 `outsiderrr`）——以环境探测值为准
- 作者已建立 **AI-as-judge 习惯**（阶段 1 引入）；阶段 2 同样可用，但场景级评审 prompt 需重写
- 作者明确不愿追求"最后 10% 完美主义"；阶段 1 schema 85% 留给阶段 2 收尾，但**阶段 2 也不必死磕到 100%**
- 作者对 **BG3 式剧情容错**（多路径汇合 / 角色槽位 / 结局可达性保证）有兴趣；阶段 2 的角色槽位 ADR + graceful degradation validation 是这一方向的落地

## 必读顺序（新规划师首轮阅读）

1. `/CLAUDE.md`
2. `/docs/ROADMAP.md`（特别是阶段 2 段 + 阶段 1 完成标志做对比）
3. `/docs/DECISIONS.md`（**全部 13 条**——尤其 ADR-001 / 003 / 005 / 006 / 008 / 009 / 011 / 012 / 013）
4. `/docs/DEBATE_NOTES.md`（至少 §1、§2、§5、§8）
5. `/docs/SCHEMA_v0.md`（场景级生成对象的 schema）
6. `/docs/STAGE_1_ACCEPTANCE.md`（特别 §4 R1–R8 哪些归属阶段 2）
7. `/docs/STAGE_1_TASKS.md`（执行会话提示词的产出格式参考）
8. `/content/test_scene_v0/scene.json`（《铁誓驿站》——阶段 2 的 gold standard 参考）
9. `/validator/` 现有三层校验代码
10. 本文件（HANDOFF_STAGE_1_TO_2.md）

## 工作模式（阶段 0/1 已跑通，不要改）

- **规划师会话**：产出任务拆分 + 提示词；不写代码；回答架构歧义时给利弊 + 推荐不替作者决定
- **执行会话**：只做单一任务；硬性限定在自己的模块目录；完成后 commit + push（末尾附 Co-Authored-By）
- **并行多会话**：模块互不重叠可并行；push 时 rebase 兜底
- **Schema 级变更**：阶段 2 可能动 Schema（角色槽位 / 本体 Schema），需作者明确授权；变更走 MINOR bump

## 阶段 1 残留的工作流改进建议（阶段 2 规划师可采纳）

- **R8 机械预检器**：图论校验器扩展时一并实现机械检测（option 长度 / path 前缀 / bond ID 白名单），让 LLM 判官只评 B/D/E 语义维度，效率 + 准确度双提升
- **AI 判官 prompt 视觉化**：阶段 2 场景图比单节点复杂得多，文本 prompt 难以直观；考虑在 review_cli 渲染图的可视化（mermaid / dot / 文本 ASCII 图）
- **cost_log 反向校准**（R7）：阶段 2 启动前去 Google AI Studio 控制台对账一次，确认 cost_log 高估幅度

## 阶段 1.5 与阶段 2 的合并预判（提前预警）

阶段 1.5 与阶段 2 是平行任务（文本/结构 vs 图像）。**理论上无冲突**，但实际可能两点摩擦：

1. **本体角色 Schema**：阶段 1.5 加 `visual_assets` 字段；阶段 2 可能加 `slot_tags` 字段；两者若同时改可能撞车——建议先合入先到的，后到的 rebase
2. **总预算**：阶段 2 估算 $30–$50（图论校验本身不烧 LLM；scene 生成 token 大但单次场景成本可控），1.5 估算 $50–$80；累计接近 $100，作者需做心理预期

合并到主分支由作者协调，规划师不替作者决定哪个先合。
