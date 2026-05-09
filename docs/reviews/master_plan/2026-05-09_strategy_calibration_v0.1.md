# 战略校准 v0.1（CEO Review 产出）

> 2026-05-09 L1 规划讨论结论。给阶段 4 规划师起手时阅读，作为 ROADMAP §阶段 4 + memory [opensource_strategy] 的战略层补充。
>
> **本备忘不修改 L1 文档**（CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md / STAGE_*_TASKS.md）。备忘内任何条目要落地为 ADR / ROADMAP 修订须由作者明示授权 + 走专门执行会话。

**日期**：2026-05-09 · **版本**：v0.1 · **产出方**：L1 规划讨论会话（master plan 续接）
**触发**：作者引入 gstack `/plan-ceo-review` 方法论（only-read 不安装），用其框架对 Forgewright 项目战略层做 CEO Review

---

## 1. 背景与方法论

### 触发与方法论来源

作者新装 gstack（`garrytan/gstack`，GitHub 开源 MIT，Garry Tan / YC CEO 个人配置开源版），但因 gstack 的工作流大量面向"多人 SaaS 创业团队"且与 Forgewright 现有治理（Round 5 + L1/L2/L3 + ABC 流程 + 治理备忘 v0.3 + baseline 协议）冲突大，决定 **only-read 不安装**。本会话仅读取 `~/.claude/skills/gstack/plan-ceo-review/SKILL.md` 提取方法论，适配到 Forgewright 的 L1 战略反思场景。

### 方法论核心

gstack `/plan-ceo-review` 提供了 4 种 Posture（评审姿态）：
- **SCOPE EXPANSION**（建大教堂模式）
- **SELECTIVE EXPANSION**（守 scope + 单点 cherry-pick）
- **HOLD SCOPE**（最大严谨）
- **SCOPE REDUCTION**（外科砍裁）

Step 0 五步：
- **0A. Premise Challenge** —— 这是要解决的对的问题吗？真正的 outcome 是什么？不做会怎样？
- **0B. Existing Code Leverage** —— 已有代码杠杆（不适配 L1 战略层，跳过）
- **0C. Dream State Mapping** —— 12 个月后理想终态 vs 当前增量 vs 现状
- **0C-bis. Implementation Alternatives** —— 实现方案备选（不适配 L1 层，跳过）
- **0D. Mode-Specific Analysis** —— 按 posture 跑深入分析

18 条 Cognitive Patterns（CEO 思维本能），强相关 Forgewright 的 6 条：
- **#1 Classification instinct**（按可逆性 × 量级分类决策）
- **#3 Inversion reflex**（"如何赢"也问"什么会让我失败"）
- **#4 Focus as subtraction**（核心价值是决定不做什么）
- **#7 Proxy skepticism**（指标是否还在服务真实欲望）
- **#9 Temporal depth**（5-10 年视角）
- **#13 Willfulness as strategy**（在一个方向上推够久）
- **#14 Leverage obsession**（小投入产出大杠杆）

### 本次 CEO Review 适配执行

- 选择 **SELECTIVE EXPANSION** posture（scope 已锁但欢迎单点 cherry-pick）
- 跑了 **0A Premise Challenge**（Q1 + Q1.1-Q1.5）+ **0C Dream State Mapping**（Q1.6）
- 跳过 0B / 0C-bis / 0D 的深入版（不适配 L1 战略层）
- 0E Temporal Interrogation 部分穿插在 Q1.4，未独立深跑

---

## 2. Premise Challenge 拍板（0A）

### Q1.1：真正问题是什么？

**作者拍板**：通过 C（AI 辅助叙事生产方法论）路径达成 A（作者本人作品）。

三个候选 framing：
- **A** = 作者本人完成一款 BG3 风格中小型 RPG
- **B** = 让独立作者群体也能用同样工具做 RPG
- **C** = AI 辅助叙事内容生产方法论本身

A 和 B 同类（都是降低游戏制作门槛的"效果"层）；**C 是"路径"层**。当前阶段优先级：

- **当前阶段 0-3** = C 主（工具 + 方法论建设）
- **阶段 4 之后** = A 主（做内容）

### Q1.2：A vs B 工程投入比例

**作者澄清问题 + 反思**：A 优先 ≠ B 优先在工程上**结构性差异**（B 比 A 多 3-5x 工程量）。

| 维度 | A 优先（只服务作者本人） | B 优先（服务广大独立作者） |
|---|---|---|
| 文档 | 不需要（作者本人记得） | 必须 README / Tutorial / Examples / Cookbook |
| 错误信息 | 简陋即可（自己 debug） | 必须友好（教用户怎么修） |
| 安装 | 自己机器配好了 | 必须 `pip install` 一行 |
| Schema validator | 隐含约束够 | 必须严格校验 + 友好报错 |
| 向后兼容 | 不需要（自己迁移） | 必须有迁移路径 |
| 可视化 UI | 直接编 JSON 也行 | 必须 GUI |
| 插件机制 | 自己 fork 改 | 必须支持外部扩展不 fork |
| CI / 测试基础设施 | 简单跑跑就行 | 必须完整 CI + 测试样例 + 覆盖率 |
| 社区治理 | 不需要 | RFC / contributor guide / code of conduct |
| 版本号 / changelog | 不需要 | 必须语义化版本 + release notes |
| 性能 / 资源 | 自己机器够用 | 必须考虑各种用户机器配置 |
| i18n | 中/英任选 | 多语言（如有国际用户） |

### Q1.3：B 是否值得作为目标？

**作者拍板**：**不值得**作为目标（"可遇而不可求"）。

逻辑（应用 CP #3 Inversion reflex + #4 Focus as subtraction）：

- **主权维度**：B 主权在外部（市场、其他作者、推广运气），A 和 C 主权在作者本人
- **过程 vs 目标**：C 和 A 都是"过程为中心"——即便效果不好，过程本身就有回报；B 是"目标为中心"——目标达不成会觉得亏
- **回报确定性**：C 高（写完工具就有工具）；A 高（写完作品就有作品 + 过程乐趣）；B 低（社区采用不可控）
- **行动成本**：B 涉及推广/融资/市场——都是低主权 + 低过程价值

战略原则：**选高主权 + 高过程价值的目标，避开低主权 + 低过程价值的目标**。

### Q1.4：阶段 4 切换的强约束机制

**作者拍板**：不死板冻结工具——平衡机制：

- **北极星指标** = 阶段 4 切换之后**更快更好完成 A**
- **工具改进的唯一合法理由** = "能更快达成 A"
- 触发条件：写内容时遇到工具瓶颈
- 评估问句：这个工具改进会让 A 完成时间缩短吗？
- 即"工具是杠杆"（CP #14 Leverage obsession），不是终点

**Scope 弹性**：MVP 不再硬性 50-100 场景，改为**10-100 场景的弹性区间**——从 10 起步快速 end-to-end 反馈，验证后阶梯扩张。

### Q1.5：A 完成定义

**作者拍板**：(b)→(c)→(d) 三档，**跳过 (e)**。

| 定义 | 信号 | 选择 |
|---|---|---|
| (a) Build 跑通 | 10 场景 JSON 包能在 engine 里从头玩到尾 | 必经过 |
| (b) 作者本人玩通 | 亲自玩通一遍 + 觉得满意 | ✓ 目标档之一 |
| (c) 3-5 朋友玩通 | 小范围 alpha 测试 | ✓ 目标档之一 |
| (d) itch.io 免费发布 | 公开发布且玩家能玩 | ✓ 目标档之一 |
| (e) Steam 卖 | 商业发布 | ✗ 跳过（除非 itch.io 反响好后再考虑）|

**理由**：Steam 真实成本远超直觉——

- $100 USD Steam Direct 沉没（免费游戏拿不回）
- 8 种规格胶囊 + Logo + Hero + Background + ≥ 5 截图 + Trailer 视频
- IARC 自评级强制问卷
- Valve build 审核 2-5 工作日 + 必须 Win/Mac binary 通过测试
- 必须用 Steamworks SDK 集成（Forgewright Python 播放器需 PyInstaller / Electron 包装）
- 中国作者需走 W-8BEN 个人税务身份验证
- 首次上架时间 2-4 周

而 itch.io 完全免费 + 1-3 小时上架 + 是 indie RPG 事实标准发布平台之一（《Disco Elysium》早期 demo 等都在 itch）。

---

## 3. Dream State Mapping（0C）

### 12 个月愿景

```
┌─ 个人产物：1 款小巧的、令我满意的 RPG 作品
│
├─ 工具核心点 1：剧本（数）生成能力
│   ├─ 1A 前后逻辑统一（玩家属性 / 事件 / 系统时钟 / 阵营时钟 / 宏观事件）= BG3 级别
│   └─ 1B 戏剧理论支撑的文学性（AI 生成 + 作者审美调教）
│
├─ 工具核心点 2：多世界观兼容性
│   ├─ 加载不同世界规则（DND / 克苏鲁 / 赛博朋克 / 现代都市...）
│   ├─ 战斗 + 探索 + 对话三大互动界面相对固定
│   └─ 每种世界 = 一个"模块"，不动工具底层
│
└─ 社区想象：开源世界规则模块 → 哈利波特 / 诡秘之主 / 爱好者世界 → 中小型游戏涌现
```

### CEO 视角诊断：Proxy Skepticism

Q1.3 拍板 **"B 不作为目标"**。但 Dream State 描述的最终形态——多世界观社区 + 爱好者赋能 + 开源世界规则模块——**正是 B 的具体形态**。

应用 CP #7 Proxy Skepticism——口头指标（A 主）和真实欲望（B 涌现）可能不对齐。

### Q1.6：Dream State 落地原则

**作者拍板**：**(a+) "美好但不主动追求 + 不主动排除"**。

精细于 (a) "美好但不主动追求 / YAGNI"和 (b) "真要追求 / 留架构钩子"两选项，作者给出第三种：

- 行动**不主动追求 B**（不投正向资源）
- 工程阶段**不主动排除 B**（保持 two-way doors，不做让 B 永远不可能的硬编码）
- 应用 CP #1 Classification instinct（按可逆性 × 量级分类决策）

**作者原话**："基于目标制定行动计划，那目的还是 A。但因为想要 B，所以执行过程中保留 B 可能实现的可能性，不要在工程阶段就排除了 B 的可能性。"

### 具体行动指南

- 在 schema / prompt / 代码中**避免硬编码单一世界观**
- 不引入"DND-style fantasy"、"dnd_class"等绑定单一世界的字段名 / 模板段
- 战斗系统不实现（YAGNI 自动符合）
- 与 ADR-004 极简精神 + 不引入世界绑定假设 = 同源

### 零额外工程量诊断

四个潜在架构钩子，**当前架构已天然满足**——

| 钩子 | 当前架构状态 |
|---|---|
| Ontology schema | 由作者定义，未硬编码具体世界 ✓ |
| 战斗系统 | 当前根本没有 ✓ |
| Prompt 模板 | ADR-005 + ADR-018 用抽象戏剧理论术语（character_features / narrative_weight），不带具体世界假设 ✓ |
| Plugin 注册机制 | ADR-005 已 plugin 化 ✓ |

**结论**：(a+) 拍板**零额外工程量**——阶段 2-3 task 清单不需要改。后续 L2/L3 规划师只需**意识到这条原则**：写代码 / schema / prompt 时**不引入硬编码单一世界观假设**。

---

## 4. 战略哲学（来自 CEO Review）

### 应用的 CEO Cognitive Patterns

- **#1 Classification instinct**（按可逆性 × 量级分类决策）→ Q1.6 (a+) 拍板基础
- **#3 Inversion reflex**（"如何赢"也问"什么会让我失败"）→ Q1.4 切换协议 + Q1.3 主动放弃 B 的逻辑
- **#4 Focus as subtraction**（核心价值是决定不做什么）→ B 不作目标 + 跳过 Steam (e) + Scope 弹性区间 10-100
- **#7 Proxy skepticism**（指标是否还在服务真实欲望）→ §3 识别 Dream State vs 拍板的张力
- **#9 Temporal depth**（5-10 年视角）→ 阶段 0-3 vs 阶段 4 之后的优先级切换
- **#13 Willfulness as strategy**（推够久）→ 选定 C → A 路径长期推
- **#14 Leverage obsession**（小投入产出大杠杆）→ 工具是杠杆不是终点

### 战略心法（一句话总结）

- **选高主权 + 高过程价值的目标**（C, A）
- **避开低主权 + 低过程价值的目标**（B 作为目标，e 作为强追求）
- **Inversion**（防御性）+ **Subtraction**（聚焦）= 当前阶段心法
- **工具是杠杆，不是终点**

### 失败模式警示（来自 CEO Review §0E 部分讨论）

**真实的失败模式**：很多独立创作者在"做工具"阶段乐在其中（C 阶段），但切换到"做内容"阶段（A 阶段）后发现：

1. 工具完美但内容创作仍然慢（每场戏要审阅）
2. 创作者发现自己其实不喜欢"批量生产对话"
3. 创作者意识到"我其实更想做工具不是做内容"
4. 于是又回去"完善工具"——**永远完成不了 A**

防御机制即 §2 Q1.4 的"北极星指标 + 工具改进必须服务 A 完成时间"。

---

## 5. 与现有 L1 文档兼容性

- **CLAUDE.md**：本备忘不修改
- **ADR-001~021**：本备忘 §3 Dream State 落地原则与 ADR-004（极简）+ ADR-005（编剧理论插件）+ ADR-006（本体 SOT）+ ADR-018（narrative_weight）同源，无冲突
- **ROADMAP §阶段 4**：本备忘 §2 Q1.4（阶段 4 切换协议）+ §2 Q1.5（A 完成定义）给 ROADMAP §阶段 4 增加战略层细化
- **memory [opensource_strategy.md]**：本备忘 §2 Q1.3（B 不作目标）和 §3（不主动排除 B）与该 memory 的开源策略同源，给开源策略增加战略层 framing
- **配套姊妹反思**：同日 L1 会话另一份产出 `2026-05-09_yoroll_and_opensource_design_reflection.md`（外部信息源镜像 + 开源策略 5 论证 + AI 时代时间观校准）—— 一份讲"为什么开源"，本备忘讲"开源 / 工具 / 内容三者优先级"。两份独立 PR，归档时序不互相依赖

### 潜在 L1 升格路径

本备忘任何条目升格为 ADR / ROADMAP 修订须由作者明示授权 + 专门执行会话执行：

- **ROADMAP §阶段 4 修订**：是否正式吸收 §2 Q1.4 切换协议 + Q1.5 完成定义？
- **ADR-010 修订**：是否将"MVP 50-100 场景"改为弹性区间 10-100 场景？
- **新 ADR 候选**：是否就"不主动排除 B 的工程原则"立一个新 ADR（ADR-022 候选）作为给后续 L2/L3 规划师的硬约束？

---

## 6. 给后续规划师 / L1 续接会话的输入

### 给阶段 3 L2 规划师（如还在跑）

- **不需要插入新任务**为多世界观留架构钩子（YAGNI + (a+) 拍板）
- 但所有新代码 / schema / prompt **应避免硬编码单一世界观假设**
- 这与 ADR-004 极简精神同源，不构成额外工作量

### 给阶段 4 L2 规划师（未来起会话时）

- **北极星 = A 完成度**
- **Scope = 10 场景起步 + 阶梯扩张**（10 → 30 → 50 → 100，按需）
- **完成定义 = (b)→(c)→(d) 三档**，目标 itch.io 免费发布
- **工具改进的合法触发条件** = 写内容时遇到瓶颈 + 改进能加速 A
- **跳过 Steam (e)**，除非 itch.io 反响好后再决定
- 不要硬编码 50-100 场景作为完成判定

### 给未来 L1 续接会话

- 警惕"做工具滑回继续做工具"的失败模式（§4 失败模式警示）
- 警惕 Dream State vs 拍板的 Proxy Skepticism 张力（§3）
- 周期性应用 Inversion reflex 自检：什么会让 Forgewright 失败？

---

## 7. 修订记录

- **2026-05-09 v0.1**：初版。基于 2026-05-09 L1 规划讨论（gstack `/plan-ceo-review` 方法论 only-read 引导的 CEO Review）落盘。
- **配套姊妹反思**：同日另有 `2026-05-09_yoroll_and_opensource_design_reflection.md` v0.1（讲外部信息源镜像 + 开源策略论证强化 + AI 时代时间观校准），与本备忘形成姊妹篇。两份独立 PR，归档时序不互相依赖。
- **作者拍板已固化**：§2 Q1.1-Q1.5 + §3 Q1.6 + §4 战略哲学。
- **后续延伸（未跑）**：本会话未跑 0E Temporal Interrogation 深入版（已部分穿插在 Q1.4）+ 11 Review Sections（不适配 L1 战略层），如未来需要可起新会话。

---

## 版本

本文件版本：v0.1
最后更新：2026-05-09
