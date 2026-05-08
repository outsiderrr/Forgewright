# Yoroll 案例镜像 + 开源策略论证 + 时间观校准 设计反思

> 2026-05-09 L1 规划讨论结论。给阶段 4 规划师 / 未来 L1 续接会话起手时阅读，作为 Round 5 synthesis §6/§7 占位指针 + memory [opensource_strategy] 的具体延伸输入。
>
> **本备忘不修改 L1 文档**（CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md / STAGE_*_TASKS.md）。备忘内任何条目要落地为 ADR / ROADMAP 修订须由作者明示授权 + 走专门执行会话。

**日期**：2026-05-09 · **版本**：v0.1 · **产出方**：L1 规划讨论会话（master plan 续接）
**触发问题**：作者引入两个外部信息源（MIT CMS.608 Game Design 课程 + Yoroll.ai 平台）反思 Forgewright 架构 / 商业模式 / 时间观

---

## 1. 背景与讨论范围

2026-05-09 L1 规划讨论会话延续 2026-05-02 PZ 反思 v0.1 + Round 5 总规划综合后的项目级反思工作。作者引入两个外部信息源对 Forgewright 架构 / 商业模式 / 时间观做反思：

1. **MIT CMS.608 Game Design (Spring 2014)** —— Philip B. Tan + Richard Eberhardt 教授的桌游设计研讨课。MDA framework + Aesthetics-as-Goal + Meaningful Decisions + Frasca Simulation vs Representation 等概念框架
2. **Yoroll.ai (LinearGame 公司)** —— 新加坡 + 旧金山初创，pre-seed 阶段（multi-million-dollar，HT Opportunity Fund 领投，2025-12-09 公告），主打 AI 视频原生游戏，三层架构（Expression / Judgment / State）

讨论中**严格守住**已有架构约束：ADR-001 / 002 / 006 / 008 / DEBATE §1 / DEBATE §2。

讨论引出三条项目级深度反思：
- §2 Yoroll 案例镜像（架构验证 + 翻译层概念 + 商业模式不可持续诊断）
- §3 开源策略论证强化（5 论证 + Yarn Spinner / Unity 失败案例）
- §4 AI 时代时间观校准（实际开发节奏 vs ROADMAP v0.1 估计差距）

**MIT CMS.608 课程的深入讨论被作者主动打断转向 Yoroll**，本反思中只做课程概要落盘 + 已讨论 1 条（Frasca）+ 6 条占位，留待后续 L1 续接会话延伸（§5）。

---

## 2. Yoroll.ai 案例镜像

### 2.1 Yoroll 三层架构事实

- **Expression Layer（表现层）**：generative video（Genie 3 等模型）实时生成
- **Judgment Layer（判定层）**：VLM（Vision-Language Model）视觉理解 + 翻译为事件 token
- **State Layer（状态层）**：传统确定性数据库 + 游戏逻辑

关键观察：**双向数据流**。
- 上行（理解方向）：视觉 + 操作 → 事件 → 状态。VLM 做的事
- 下行（生成方向）：状态 → prompt → 视频。提示词工程

### 2.2 与 Forgewright 的架构对照

**核心同源点**：双方都识别到"LLM 不能直接写状态、需要中间翻译/判定层"是必经之路。

| 维度 | Forgewright | Yoroll |
|---|---|---|
| 玩家交互 | 3-6 预生成选项（ADR-001） | 选项 + QTE + 触控混合 |
| 状态管理 | 状态总线 / 本体（ADR-006） | State Layer 确定性数据库 |
| LLM 写状态 | 禁止（ADR-008） | 禁止（VLM 只翻译） |
| 翻译层（Judgment Layer 等价） | Schema 校验 + Structured Output + function calling 白名单 + AI 判官 | VLM 视觉识别 → event token |
| 主要表达载体 | JSON 对话图 | 生成视频流 |
| 运行时 LLM | 无（ADR-002） | 有（每场跑 video gen + VLM） |

**最关键差异**：
- Forgewright = pure representation 路线（Frasca 学术语，详 §5.2）
- Yoroll = 混合 representation（State）+ simulation（Expression）

**翻译层成本分布的工程权衡**：
- Forgewright = 重开发期翻译 + 极简运行时
- Yoroll = 轻开发期翻译 + 重运行时翻译

### 2.3 翻译层概念（架构命名层启发）

Yoroll 把所有翻译/判定逻辑命名为单一"Judgment Layer"是好的命名习惯。Forgewright 当前是分散叙述（ADR-008 / ADR-013 / ADR-020 / ADR-021 各管一块），缺统一伞概念。

**阶段 4 开源框架 README "design philosophy" 段**可借鉴 Yoroll 命名法把这些统一描述为 "Validation Layer / Judgment Layer" 伞概念。这一条是文档/命名层借鉴，不影响代码、不立 ADR、不进当前阶段任务。

### 2.4 玩法决定 Judgment Layer 复杂度

不同玩法对应不同 Judgment Layer 工程复杂度：
- 自由文本意图识别 = 极复杂
- 自由动作识别 / QTE 时机识别 = 中-高复杂
- 选项点击 / 骰子读数 = 低复杂

**Forgewright ADR-001（3-6 预生成选项）实际上是把 Judgment Layer 运行时复杂度压到最低的设计选择** —— 玩家点选项 = 直接事件 ID 映射，连"翻译"都不需要。

### 2.5 商业模式不可持续诊断

按当前公开 AI 视频生成 API 估值（Sora / Runway Gen-3 / Pika 等中位 $0.10/秒视频 + VLM $0.01-0.03/秒）：

- 完全运行时生成假设：单次游玩约 $470（≈ 3300 人民币）
- 关键场景预生成 + 过渡运行时假设：约 $190（≈ 1300 人民币）
- 极致优化假设：约 $50（≈ 350 人民币）

vs 玩家可接受娱乐定价（约 $3，20 人民币）= **10-100 倍差距**。

**结构性问题**：
- 玩家直接付 token 费 → 心理抵触
- 游戏售价含 token → 越好玩越亏，反向激励
- 抖音爆款分成 → 不可持续，依赖 VC 钱
- 创作者订阅 ToB 模式 → 退化回 Forgewright 模式（运行时实时生成是伪命题）

### 2.6 融资阶段事实

- Pre-seed multi-million-dollar（具体金额未披露）
- 领投：HT Opportunity Fund（非顶级 VC，无 a16z Games 等行业领头基金参与是值得注意的信号）
- 当前阶段：closed beta，不开放公开自助入驻
- 时间线：2025-12 融资 → 2026-04 GDC/GTC PR + 6 款游戏宣传 → 2026 H1 闭测启动 → 大概率为 seed/Series A 融资准备 demo

无任何公开开发者政策 / 定价 / token 费用承担机制（搜索 + 官网 + 中文站 + 主流报道全部缺失）。

### 2.7 ADR-002 的商业模式论证强化

ADR-002（运行时不调用 LLM）不只是技术架构选择，**同时是商业模式根基**：

- 传统游戏经济学（边际成本 = 0）能成立的根本原因 = 运行时无可变成本
- Yoroll 打破了这个 → 把游戏从"软件商品"变成"SaaS 服务"
- SaaS 商业模式适合企业工具，不适合娱乐消费品（用户对单次娱乐成本敏感度极高）
- **Forgewright 走 ADR-002 = 保留了"软件商品"商业模式的所有红利**

### 2.8 作者主权（Authorship Sovereignty）

Yoroll 现状（无公开开发者政策 / 无定价 / 闭测制 / 平台兜底 token）反向印证 Forgewright 的"作者主权"价值：

| 维度 | Yoroll 上的开发者 | Forgewright 上的作者 |
|---|---|---|
| 作品所有权 | 依赖平台运行时（平台关闭 = 作品消失） | 完全本地（JSON + 极简播放器） |
| 定价权 | 受平台政策约束 | 自主 |
| 运行时依赖 | 平台云服务 + 持续 token 费 | 零 |
| 政策风险 | 平台改规则 / 涨价 / 下架 | 不存在 |
| 后向兼容 | 由平台决定 | 永久（JSON + Schema 任意工具可读） |

这是 ADR-001 + 002 + 003（JSON-native）+ 004（运行时/生产期分离）合力产出的**作者主权**——作者拥有作品的全部，永远。

### 2.9 Yoroll 对 Forgewright 的实用价值（极简）

**唯一保留**：未来 Forgewright 融资 / 公开传播时的反向对标素材——

- 我们：representation + 重开发期 + 作者主权 + 离线可玩 + 边际成本零
- 对标他们：simulation + 重运行时 + 平台依赖 + 必须联网 + 边际成本不可持续

**作者明示（2026-05-09）**：本反思**不归档** Yoroll 商业模式被收购 / 套现讨论部分（仅作 L1 讨论会话内部参考，不进开源仓库）。

### 2.10 项目级洞察：AI 时代工程不构成商业壁垒

> 在当前 AI 时代，**纯工程能力没有商业壁垒**——有创意就能用 AI 实现工程产品；而创意本身不被法律保护。**所以"工程能力 = 护城河"的传统创业逻辑失效**。

**对 Forgewright 长期开源策略的影响**：

- 强化"剥离开源"路径的必要性（既然工程不构成壁垒，开源反而是更好的传播 + 占位策略，类似 React 之于 Facebook）
- 弱化"独占核心代码"的诱惑——保密反而是劣势
- 给 ROADMAP §阶段 4"开源框架剥离"目标增加了一条**底层逻辑论证**（不只是"为开源社区贡献"的理想主义，是**理性的护城河选择**）
- 作者真护城河应该在：**作品本身 + 作者审美 + 内容质量 + 玩家社区**——这些是工程之外的东西

---

## 3. 开源策略论证强化

> 沿用 memory [opensource_strategy.md] 已有的两公开仓库规划（Forgewright 全过程仓库 + 未来 forgewright-framework 仅工具核心仓库），本节加强其论证基础。

### 3.1 核心论证（5 条）

**1. 作者真正的核心资产不是工程代码**

| 资产类型 | AI 时代是否能被复制 | 在 Forgewright 里 |
|---|---|---|
| 工程框架代码 | AI 时代可被快速复刻 | 是 |
| 创意/故事大纲 | 不被法律保护，但深层风格难抄 | 在作者头脑里 |
| 作品本身 | 有著作权保护 | 是 |
| 作者审美 + 世界观投入 + 信誉 + 社区 | 不可复制 | 在作者本人 |

闭源在保护"最容易被 AI 复刻的工程层"，对真正护城河零防护、对销售零帮助。

**2. 视觉小说 / 文字 RPG 细分市场的事实标准全是开源**

Ren'Py（MIT）/ Twine（开源）/ Inform 7（开源）/ Ink (Inkle, MIT)/ TyranoScript（开源）全部开源。该细分市场用 20 年时间投票出结论：**闭源工具在这个细分里没赢家**。

**3. 作者商业模式和工具链天然分离**

作者真正想赚钱的是作品销售，不是工具。两者互不影响 + 工具开源还提升作品 visibility（"用 Forgewright 做的"成为标签）。类比：Pixar/RenderMan、Re-Logic/Terraria modding、Klei/Don't Starve modding。

**4. 一个人维护 = 闭源死亡螺旋；开源 = 社区加速**

| | 闭源 | 开源 |
|---|---|---|
| Bug 修复 | 一人 + AI（慢） | 社区 PR + 作者审 |
| 新功能 | 一人决策 + AI 实现 | 社区贡献 + 作者保留 maintainer |
| 文档 | 作者写不动 | 社区帮写教程 / 博客 / 视频 |
| 边缘 case 测试 | 作者一人测 | 数百用户帮测 |
| 长期延续 | 作者退出 = 项目死 | 作者退出 = 社区 fork |

最后一条对作者本人尤其重要——闭源 = 作者是单点故障；开源 = 作者随时可退出而不背负"用 Forgewright 做的所有作品都失去支持"的道德负担。

**5. 防御性：抗"平台垄断 / 平台收割"的盾牌**

- 闭源 = 作者改协议 / 涨价 / 卖给大厂 → 用工具的所有作者作品受影响 → 选工具时绕开
- 开源（MIT/Apache）= 用户永远有 fork 权 → 选用心理负担极低 → 采用率自然上升

### 3.2 反对开源声音 + 反驳

**论点 A**：开源会被竞争对手白嫖 + 包装成商业产品
→ **反驳**：竞争对手有自己技术路线，不会真用 Forgewright 内核；即被 fork，作者本人作品销售零影响。

**论点 B**：开源会暴露作者"不会编程"事实
→ **反驳**：恰恰相反——展示"一个不会编程的作者靠 AI 做出完整 RPG"对独立开发者社区有教育价值，是叙事资产不是劣势。

**论点 C**：开源后社区贡献质量难控制
→ **反驳**：作者保留主仓库 maintainer 权力 + PR 必须审；社区贡献是加速器不是决策者。

**论点 D**：开源会失去未来融资机会
→ **反驳**：开源公司也能融资（Supabase / GitLab / Vercel / HashiCorp / Hugging Face / Confluent / MongoDB / Elastic 全部都是）；但 Forgewright 当前根本不需要融资——独立作者商业模式 ≠ 创业公司商业模式。

### 3.3 失败案例：Yarn Spinner YSPL 事件

**事件事实**（已校准本会话讨论中初稿措辞）：

- Yarn Spinner 项目协议拆分：核心库 + Unity 子项目仍 MIT；Godot (GDScript) + Unreal 子项目改用 YSPL（Yarn Spinner Public License）
- YSPL 限制两条：禁止用代码训练生成式 AI 模型；禁止重打包成竞争性商业对话工具
- 团队官方动机：反 AI 训练抓取 + 反 fork 后商业化
- 社区反应：**不是大规模出走**（之前讨论中初稿措辞过强需校准），但 YSPL 部分被广泛归类为"伪开源"（source-available 而非 OSI 认证 open-source），与 SSPL / Commons Clause / BUSL 同类
- Godot/Unreal 用户社区有强烈担忧 + 部分人开始评估替代方案（Dialogic 等）但未发生大规模迁移

**对 Forgewright 启示**：

- CLAUDE.md 第 4 条 ban "Yarn Spinner 新版（YSPL 许可证）"判断合理：YSPL "禁止竞争"条款会限制 Forgewright 未来的"叙事生成框架"演化空间
- 协议家族有进一步收紧的历史先例（Elastic / MongoDB 都从开源逐步收紧到完全闭源）

### 3.4 失败案例：Unity 2023 Runtime Fee 事件

**事件时间线**：

| 日期 | 事件 |
|---|---|
| 2023-09-12 | Unity 公告 Runtime Fee（每安装 $0.20，门槛 年收入 > $200K + 总安装 > 200K，追溯生效） |
| 2023-09-22（10 天后） | 大幅回撤 |
| 2024 年某月 | CEO John Riccitiello 离职 |
| 2024 年新 CEO 上任 | 完全取消 Runtime Fee |
| 2025-01-01 替代方案生效 | Unity Pro 涨 8%、Enterprise 涨 25% |

**核心问题**：

- "安装"作为计费单位 = 惩罚病毒式传播 + 多设备玩家的游戏（越成功越亏）
- 追溯生效 = 包括已发布多年的游戏

**社区反应**：

- 大规模愤怒 + 抵制威胁（Innersloth《Among Us》/ Massive Monster《Cult of the Lamb》）
- 死亡威胁导致 Unity 总部办公室疏散
- Godot 项目下载量爆炸式增长，加星数月内翻倍

**长期影响**：

- Unity 信誉重创——即便完全取消政策，**信任不可逆恢复**
- 大量独立开发者永久迁移到 Godot；新独立开发者优先选 Godot
- Unity 营收 2024 年下滑 + 大规模裁员

**对 Forgewright 启示**：

- 单一 maintainer / 公司控制的工具，永远存在"政策可能改变"的悬挂式风险
- 即便事后回撤，**信任成本是不可逆的**
- 强化 §3.1 第 5 条"防御性盾牌"论证

### 3.5 推荐策略（沿用并强化 [opensource_strategy] memory）

**阶段 0-3 当前**：

- Forgewright 全程公开仓库 = 全开放（开发过程 + 工具 + 内容）
- 价值定位："在野记录" + 教育资产 + 个人品牌建设
- 不强求"框架成熟" + "社区活跃"，重点是作者自己用得爽

**阶段 4 剥离时**：

- forgewright-framework 独立仓库 = 工具核心剥离
- **协议明确选 MIT 或 Apache 2.0**（最宽松，不要 GPL —— GPL 限制采用率，且 Forgewright 不靠 framework 本身赚钱所以不需要 GPL 强制保护）
- 绝对不要 SSPL / YSPL / Commons Clause / BUSL 等"伪开源"协议（CLAUDE.md 已 ban Yarn Spinner 新版）

**长期可能性（不强求）**：

- 如果作品成功 + 框架社区活跃 → 可接受捐赠 / 成立基金会（如 Godot Foundation 模式）
- 这些都是自然演化，不是必须
- 独立作者不需要把开源等同于商业组织化

---

## 4. AI 时代时间观校准

### 4.1 实际开发节奏（事实）

| 阶段 | 完成日期 | 用时 | ROADMAP v0.1 估计 |
|---|---|---|---|
| 阶段 0 完成 | 2026-04-24 | 起点 | 1-2 周 |
| 阶段 1 完成（条件通过） | 2026-04-30 | **6 天** | 2-3 周 |
| 阶段 1.5 完成（部分通过） | 2026-05-02 | **2 天** | 2-3 周 |
| 阶段 2 进行中 | 2026-05-09 当前 | 7 天进入了 | 3-4 周 |

ROADMAP v0.1 总估计"4.5-7 个月"严重低估了 AI 辅助开发的加速效应。

### 4.2 估计偏差诊断

为什么 L1/L2 规划师都给出过长估计：

1. **训练数据偏差** —— LLM 训练数据里"独立游戏开发周期"普遍是 6 个月-3 年（预 AI 时代基线）
2. **没充分内化"工程时间由 AI 承担"** —— 一人 + AI 编码 ≠ 传统一人独立开发者，瓶颈完全不同
3. **混淆两个时间维度**：
   - 工具完成（阶段 0-3）= 工程主导，AI 加速明显
   - 完整 MVP 含游戏内容（阶段 4）= 作者审阅主导，AI 加速有限

### 4.3 修正后时间预测

按当前节奏外推：

- **第一步：工具完成（阶段 0-3）** = 未来 4-8 周内（约 2026-06 ~ 7 月）
- **第二步：自己做小游戏（阶段 4 内容填充部分）** = 1-3 个月（取决于作者审阅节奏）
- **整个项目（含游戏作品）** = **2026 年内可全部完成**

### 4.4 给未来 L1/L2/L3 规划师的提醒

- 在估算阶段 / 任务用时时，**默认下修 5-10 倍**预 AI 时代基线
- 区分"工程时间"（AI 加速明显）vs"作者审阅时间"（AI 加速有限）
- 主要瓶颈在作者审阅带宽，**不在工程编写**
- 任务拆分按"作者审阅工时"而不是"代码行数"作为单位
- ROADMAP v0.1 时间表需要在某次专门修订会话中更新（本反思不修改 ROADMAP，需作者授权 + 专门执行会话）

### 4.5 项目 meta 验证

Forgewright 项目本身就是"AI 辅助开发"的样本——它的快速迭代节奏 + 一人 + AI 协作模式 + 审阅带宽瓶颈 = 给未来用 Forgewright 的独立 RPG 作者提供"实证参考"。这本身就是 §3 第 3 条"商业模式天然分离"的延伸——作者作品 + 项目过程都成为可公开的资产。

---

## 5. 触及但未深入 / 待后续会话延伸

### 5.1 MIT CMS.608 Game Design (Spring 2014) 课程概要

**课程基本信息**：
- 课程编号：CMS.608
- 教师：Philip B. Tan + Richard Eberhardt
- 院系：Comparative Media Studies/Writing
- 形式：每周 2 次课每次 3 小时；研讨 + Game Lab + 团队项目
- 主题：教非数字游戏（桌游、卡牌、运动、角色扮演）的设计与分析
- 结构：三个团队项目，每个跑完整迭代-测试-反馈循环
- **评分哲学**：不评 fun，只评迭代严谨度 + 规则书清晰度 + 对反馈响应

**完整目录（session 级别）**：

- L1：What is a Game?
- L2：Meaningful Decisions, Visibility
- L3：Prototyping
- L4：MDA Framework
- L5：Imperfect Information and Dice
- L6：Constraints and Usability
- L7：Aesthetics and Player Experience
- L8：Game Design Atoms
- L9：Randomness and Player Choice
- L10：History of American Board Games
- L11：Game, Play, Sport — Definitions
- L12：Games as Systems of Information
- L13：Cybernetics and Multiplayer (3-player problem)
- L14：Adding and Cutting Mechanics
- L15：Assignment 3 启动 + 案例
- L16：Simulation vs Representation (Frasca)
- L17-18：Guest Lectures
- L19：Space Control
- L20：Cooperative Games
- L21：Social Play
- L22-23：Changing Rules I/II（Cosmic Encounter / Well-Played Game）
- L24：Indie Games (Jesper Juul 客座)
- L25-26：Final Work / Presentations

**关键概念 / 框架**：MDA Framework / Meaningful Decisions / Iteration / Playtesting / Game Design Atoms / Imperfect Information & Randomness / Constraints / Usability / Affordance / Cybernetics & 3-Player Problem / Simulation vs Representation (Frasca) / Aesthetics-as-Goal。

### 5.2 已讨论 1 条：L16 Simulation vs Representation (Frasca 2003)

**理论核心**：

- **Representation**：固定状态用符号呈现（小说/电影/预生成对话树）
- **Simulation**：能按规则演化的系统，输入不同行为得到不同结果
- Frasca 主张：simulation 的"作者性"通过"允许什么 + 不允许什么"表达

**Forgewright 映射**：

- 运行时（/engine JSON 播放器）= **pure representation**
- 开发期（LLM 在 schema/本体约束下生成）= **半 simulation**
- PZ + 未来 sibling 涌现项目 = **pure simulation**

**作者拍板（2026-05-09）**：作为概念锚点保留，不立 ADR、不修 schema、不进当前阶段任务。落地形式：

- 阶段 4 开源框架 v0.1 README "design philosophy" 段引文锚点
- 未来 sibling 涌现项目立项时 README 第一句引文

### 5.3 待后续 L1 续接会话延伸的 6 条（占位）

- **L4 MDA Framework + L7 Aesthetics-as-Goal** —— 对阶段 2 prompt 模板 T-2.5 / 阶段 3 AI 判官的可能输入（aesthetics-first prompt 框架 + 8 类 aesthetics 裁剪到适合 RPG 的 4-5 类）
- **L2 Meaningful Decisions** —— 对 ADR-001 选项设计质量判定 / AI 判官维度的可能输入（信息可见性 + 可预期后果差异 + 不可回退三档）
- **课程评分哲学（不评 fun 只评迭代严谨度）** —— 对 ADR-020 v0.2 修订（X4 待立）的外部学术背书
- **L8 Game Design Atoms + L14 Adding/Cutting Mechanics** —— 对阶段 4 开源剥离边界清单（C5）的"砍而非加"指导原则
- **L13 Cybernetics + 3-Player Problem** —— 弱对接，可能更属 sibling 项目
- **L22-23 Changing Rules / Well-Played Game / Fair Isn't Funny** —— 单人叙事 RPG 不适用，sibling 候选

后续 L1 续接会话（作者起新会话时）可参考本反思 §5.2 + §5.3 继续讨论，按 PZ 反思 §3 的"对阶段 X 规划师可执行输入"格式落地。

---

## 6. 与现有 L1 文档的兼容性

本备忘不与任何 L1 文档冲突：

- **CLAUDE.md 第 4 条**（ban Yarn Spinner 新版 YSPL）：本备忘 §3.3 给出事件细节背书
- **ADR-001 / 002**（玩家交互预生成选项 + 运行时无 LLM）：本备忘 §2 + §3 显式守住，且 §2.7 给 ADR-002 增加商业模式论证维度
- **ADR-005**（编剧理论作为可替换插件）：本备忘 §3.1 第 2 条延伸（细分市场标准全开源 = 强化 ADR-005 选 MIT 协议方向）
- **ADR-006 / 008**（本体 SOT + LLM 不写状态）：本备忘 §2.2 + §2.4 显式守住
- **ROADMAP §阶段 4 开源剥离**：本备忘 §3 给 5 论证强化 + §3.5 给推荐策略
- **PZ 反思 v0.1（2026-05-02）§6 sibling 项目**：本备忘 §2.2 + §5.2 延伸（Yoroll 是涌现叙事 sibling 项目的活样本）
- **memory [opensource_strategy.md]**：本备忘 §3 给该 memory 的论证强化 + 延伸（不修改 memory 本身，需作者授权）

**潜在 L1 升格路径**：本备忘任何条目升格为 ADR / ROADMAP 修订须由作者明示授权 + 专门执行会话执行（参考 ADR-011/012/013/014/015/016~021 合入先例）。

特别需要后续考虑的：

- ROADMAP v0.1 时间表修订（§4.4）—— 待作者授权 + 专门修订会话
- ADR-002 商业模式论证扩展（§2.7）—— 是否扩到 ADR-002 正文需作者拍板

---

## 7. 修订记录

- **2026-05-09 v0.1**：初版。基于 2026-05-09 L1 规划讨论（MIT 课程 + Yoroll 案例引出三层项目级反思）落盘。讨论中作者拍板的内容（§3.5 推荐策略 / §4 时间观校准 / §5.2 Frasca 概念锚点保留）已固化。其余条目作为给阶段 4 规划师 / 未来 L1 续接会话起手时的输入参考，最终落地由对应规划师 / 修订会话立 ADR / 修订 ROADMAP。
- **作者明示**：本反思**不归档** Yoroll 商业模式被收购 / 套现讨论部分（仅作 L1 讨论会话内部参考，不进开源仓库）。

---

## 版本

本文件版本：v0.1
最后更新：2026-05-09
