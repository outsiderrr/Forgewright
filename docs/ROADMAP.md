# ROADMAP.md

> Forgewright 五阶段路线图。
>
> **给规划师的使用说明**：
> 只规划当前阶段，不规划下一阶段。当前阶段快结束时再开启下一阶段规划。
> 每个阶段的"完成标志"是硬性判定——未达标不进入下一阶段。

---

## 阶段概览

| 阶段 | 目标 | 时长估计 | 是否引入 LLM |
|---|---|---|---|
| 0 | 基座：Schema + 播放器 + 状态总线 | 1–2 周 | 否 |
| 1 | 单节点 AI 生成 | 2–3 周 | 是（首次） |
| 1.5 | 视觉资产生成 | 2–3 周 | 是 |
| 2 | 场景级 AI 生成 + 图校验 | 3–4 周 | 是 |
| 3 | 完整内容生产流水线 + 审阅工具 | 6–11 周（含 T-3X-0 1-3 周作者锚点工程 + T-3X-1b NPC 状态机 +1-2 周）| 是 |
| 4 | 游戏内容填充 + 开源框架剥离 | 6–8 周+ | 是 |

**总估计**：约 4.5–7 个月单人开发到 MVP + 开源 v0.1。实际时长取决于作者审阅带宽。

---

## 阶段 0：基座

### 目标

在无 LLM 参与下，完成：
1. 核心 Schema 的 JSON Schema 定义
2. 极简播放器（能运行一个手写场景）
3. 世界本体的数据结构
4. 状态总线的读写 API
5. 一个手写的测试场景（5 节点）

### 完成标志

作者能在终端里玩通一个手写的五节点场景。校验器对手写场景给出"通过"。

### 禁止事项

- 不得引入任何 LLM 调用
- 不得编写 prompt 模板
- 不得建立 `/generator/plugins/` 下的任何内容
- 不得预先设计不属于当前阶段的模块（比如 `/tools/review-ui`）

### 并行策略

**串行关键路径**：Schema 定义 → 其他一切。
Schema 定稿前不开其他并行会话。

Schema 定稿后可并行三路：
- 会话 A：实现播放器
- 会话 B：实现状态总线
- 会话 C：手写测试场景

三路汇合后，会话 D 实现校验器（依赖 Schema 和测试场景）。

---

## 阶段 1：单节点 AI 生成

### 目标

让 AI 稳定生成符合 Schema 的单个对话节点。

### 完成标志

`generate_node()` 函数：
- 输入：场景上下文 + 节点类型要求
- 输出：通过 Schema 校验的单节点 JSON
- 成功率（Schema 合法）：≥ 95%
- 质量（人工可接受）：≥ 50%

### 重点工作

- prompt 模板设计
- Structured Output / Constrained Decoding 配置
- 失败重试策略
- 第一批真实 API 成本测量

### 禁止事项

- 不得尝试生成多节点子树（阶段 2 再做）
- 不得引入复杂的 prompt chain（阶段 2 再做）
- 不得优化开发期 UI（阶段 3 再做）

---

## 阶段 1.5：视觉资产生成（VN 立绘 + 场景背景）

### 目标

为 MVP 范围内的角色和场景，生成可入库的 VN 立绘 + 场景背景资产库。

风格：类视觉小说（VN）= 场景背景静态 + 角色立绘叠加。

未来扩展性：立绘可由 PNG 升级为 5 秒短视频循环（schema 钩子预留）。

### 完成标志

- `generate_character_sheet(character_ref)` → N 张表情/姿势立绘
- `generate_scene_background(location_ref)` → 1–3 张背景
- 资产入库 `/content/visuals/` + `manifest.json`（manifest.json 完整性 100%）
- Schema 已扩展：本体角色实体新增 `visual_assets` 字段（已授权动 Schema，路径 C）
- 至少为《铁誓驿站》3 个角色 + 1 个场景完成资产生成 + 入库：vellin = **重档**（10–15 张）；corvan / aelwin = **轻档**（4–6 张）；1 场景背景
- 接受率 ≥ 50%（**作者本人** + 机械预检 + AI 判官辅助；不替代）
- **manual 路径全跑通**（dev 模式 = ChatGPT Plus 网页手动生成 + import CLI 入库）；**API 路径作为 stretch goal**（不阻塞 1.5 验收）

### 重点工作

- 双模架构（manual + API）—— Dev 模式用 ChatGPT Plus 网页手动生成（订阅 sunk cost）；API 模式用 OpenAI Image API 自动批量
- ADR-014（双模生成策略 + GPT-Image 默认 + 一致性策略）+ Schema 扩展（path A：仅扩展数据，不正式化角色 Schema）
- ImageProvider Protocol（`ManualImportProvider` + `OpenAIImageProvider` 两实现；接口预留 Imagen / Flux / Midjourney / 本地 SDXL 扩展位）
- 机械预检器（`image_validator`：分辨率 / 格式 / 文件大小等可数值化属性预检；继承阶段 1 R8 思路）
- 视觉 AI 判官 prompt（粗起一版；视觉判官能力差异大，需重新校准）
- 资产清单（manifest）格式：`asset_id` 间接引用，未来切换 PNG → 视频不动 schema

### 禁止事项

- 不做实时合成（违反 ADR-002）
- 不做立绘内 PSD 分层套娃（保持完整 PNG）
- 不做审阅 UI（阶段 3）
- 不正式化角色 Schema（推到阶段 2+；阶段 1.5 走 path A：扩展角色桩 JSON 的 `visual_assets` 字段即可）
- 不实现 ControlNet / LoRA / 自训本地 SDXL 模型（开源用户门槛过高）
- 不做立绘审阅 Web UI（阶段 3）

### 依赖

- 阶段 1 完成（`generate_node` 跑通；本体桩仍可用）
- ADR-014 立项（已落地：2026-04-30）
- 作者侧前置：2–3 张视觉风格基准图（自购或 Pinterest 收藏，放 `/content/visuals/_reference/`，不入 git）
- 作者侧后置：OpenAI API key（仅 API 模式必需；可推后到 1.5 末段，不阻塞验收）
- 详细任务见 [docs/STAGE_1.5_TASKS.md](STAGE_1.5_TASKS.md)

---

## 阶段 2：场景级 AI 生成 + 图校验

### 目标

生成完整对话树（一棵场景内的树），并确保图拓扑合法。

### 完成标志

`generate_scene()` 函数：
- 输入：场景设定 + 目标节拍 + 参与 NPC
- 输出：通过 Schema 校验 + 通过图论校验的完整对话树
- 单次生成人工可接受率：≥ 70%

图论校验器要实现：
- 前置条件路径闭合校验
- 不可达节点检测
- 死锁检测
- 分支收敛性校验

### 重点工作

- 新增 ADR：角色槽位（role slot casting）与动态选角 —— 支持 BG3 式"同一剧情功能由不同角色填充"模式
- validator 扩展：结局可达性保证（graceful degradation validation）—— 抽样验证 N=100 路径 + 有界符号执行下未发现反例（按 ADR-021 拆 2A 拓扑 + 2B 抽样 + 有界符号执行）

### 启动闸门（Round 5 综合后）

> 占位指针——具体范围 / 落地形态由阶段 2 规划师拍板，本节不替它细化。详见 [`/docs/reviews/master_plan/2026-04-30_synthesis.md` §6](reviews/master_plan/2026-04-30_synthesis.md)。

**硬闸门（5 项）**：
- **C1**：本体最小可生成契约（character / location / relation / state path 边界 schema）—— 待阶段 2 规划师立 ADR-016+ 决定范围
- **C3**：R 项（R2/R3/R4/R8）作为阶段 2 启动 cleanup gate —— 不能只藏在 HANDOFF / 验收报告尾巴；详见 `/docs/STAGE_1_ACCEPTANCE.md` §4
- **U-GPT-1**：ADR-009 第二层方法论拆 **2A 拓扑 + 2B 抽样验证 / 有界符号执行** —— 当前 schema 缺状态变量定义域 / 初始状态集合 / effect 边界，"证明任意合法状态组合可达结局"目前不可判定；待阶段 2 规划师立 ADR-016+
- **U-GPT-4**：阶段 2 baseline 协议（样本数 / 重试规则 / AI 判官权重 / 接受口径）—— 70% 接受率口径必须先定义再写代码
- **U-GPT-5**：角色槽位持久化形态决策（synthesis 推荐：持久化层仍 concrete `character_refs`，抽象槽作为 generator 中间产物 + `generation_trace` 记录）

**强建议（2 项，非硬闸门）**：
- **U-CL-4**：Chapter/Act schema 前移到阶段 2 起手期（与本体最小 Schema 打包做）—— 否则阶段 1/2 已生成内容到阶段 3 需回填层级
- **C5**：开源剥离边界清单从阶段 2/3 起维护（fixture / 资产版权 / provider 假设三类）—— 阶段 4 再执行剥离，但边界 hook 早留

### 禁止事项

- 不得跨场景生成（阶段 3 再做）
- 不得处理多场景一致性（阶段 3 再做）

---

## 阶段 3：完整内容生产流水线 + 审阅工具

### 工具第一版 scope（2026-05-09 作者拍板；2026-05-12 与 ADR-029 联动校准）

不做：
- 战斗系统（schema 不强制有；不阻止未来 plugin 扩展）
- 极乐迪斯科风格"思维内阁"（独特机制）
- 极乐迪斯科风格"内心独白"段落

主做：
- 对话多选项推进
- 调查 + 物品互动
- NPC 互动
- **技能体系**（具体技能数 / 列表 / 性格化或功能化 / 骰子规则 NdM + modifier vs DC **由项目配置层定义**；引擎只规范 `active_check`（选项级主动检定）+ `passive_injection`（节点级被动注入）基础机制；详 ADR-029）
- 检定（扔骰子 / SAN / 技能判定；具体骰子规则同上由项目配置层定义）

风格主导：CoC（结构化调查驱动）；补充：极乐迪斯科对话技法 + 技能驱动 + 世界观信息密度

追溯：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §5 + §6.1；ADR-029（技能体系作为项目配置层；2026-05-11 已 push）；T-3X L2 校准 2026-05-12 联动修订（[/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md](reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md) v0.2.2）

### 目标

作者能每天稳定产出几千字质量达标的剧情内容。

### 完成标志

- 批量生成调度器（异步跑多场景）
- 审阅界面（Web 或桌面，左内容右批准/打回）
- 一致性维护（本体变更时标记需重审的已生成内容）
- 版本控制集成（每次修改记版本）

作者实际跑一周，完成至少 10 个场景的生成+审阅+入库。

### 重点工作

- Chapter/Act 层级结构设计 —— 支持分层叙事的容器结构，位于世界本体层而非对话图层

### 完成标志强化项（Round 5 综合后）

> 占位指针——具体阈值 / 落地形态由阶段 3 规划师拍板。详见 [`/docs/reviews/master_plan/2026-04-30_synthesis.md` §7](reviews/master_plan/2026-04-30_synthesis.md)。

- **C2**：ADR-009 第三层 playtest bots 写入完成标志 —— 至少 N 个 bot persona / 每场景 M 条模拟路径 / 输出 worst-10% 场景清单；否则"完整内容生产流水线"名不副实，阶段 4 才发现 worst-bucket 路径
- **C6**：内容依赖索引（`content_dependency_index` sidecar）—— 记录每个生成产物读过哪些 ontology ids / state paths / prompt template hash / visual asset ids；本体变更时定向反向 propagate 而非全量重审
- **U-CL-1**：完成标志加质量门槛指标 —— 在 ≥ X% 单次接受率下作者每周稳定吞吐 Y 场景（具体数字待阶段 3 规划师拍板，参考阶段 2 70% 接受率）；当前"一周 10 场景"是过程指标而非产品指标
- **U-CL-5**：长对话一致性缓解策略 ADR / 任务 —— DEBATE_NOTES §9.2 列为未解问题但路线图当前无任何缓解任务；记忆流机制（Generative Agents 风格）或上下文管理策略需要显式规划
- **U-GPT-7**（建议）：审阅 UI 第一版含图视图 —— graph/mermaid/dot 视图 + 路径列表 + validator issues 面板 + visual asset thumbnail；避免后期重做审阅心智模型

### 审美层 review 激活前置（2026-05-09 审美层决策 v0.2 §6.1.b 吸收）

**完成标志强化项保留**：[A]ccept rate ≥ 60% pilot + Wilson 95% CI 报告（STAGE_3_TASKS v1.0 §1 原阈值不修订；决策档 v0.2 §4 选项 5 保留；PR-C 已落地）

**新增 T-3.10 前置条件**：
- **T-3X-0 作者审美锚点工程**（非工程任务；作者本人完成；不走 ABC）—— 读 3 部经典（Deadlight + Crimson Letters + 极乐迪斯科原版）+ 填阅读对照表 + 产出 `/docs/AESTHETIC_PREFERENCES.md` v0.1；时长 1-3 周（作者节奏决定）；指引详 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §7
- **T-3X-1 ADR-030 立项 + schema 落地 + prompt hook**（工程任务；[B-author-gate]；走 ABC）—— 基于 T-3X-0 产出实证归纳字段集；schema 落 `/schema/aesthetic_preference.schema.json` 首版 `0.4.0`（PR-A 已立 ADR-030 容器）

**时长加 1-3 周**：阶段 3 估时 4-6 周（不变）；T-3X-0 非工程任务延期 1-3 周（作者节奏决定；不计入工程估时；阶段概览表阶段 3 行同步更新为 "5-9 周（含 T-3X-0 1-3 周作者锚点工程）"）

追溯：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.1 + §4 选项 5

### 禁止事项

- 不得开始考虑开源剥离（阶段 4 再做）
- 不得加入运行时 LLM（永远不做）

---

## 阶段 4：游戏内容填充 + 开源框架剥离

### 目标

两条并行：
1. 完成 MVP 游戏（50–100 场景）
2. 从仓库剥离出通用开源框架 v0.1

### 完成标志

- MVP 游戏可玩完整主线
- 开源框架仓库独立，有独立 README、LICENSE（推荐 MIT）、快速开始文档
- 开源框架至少有一个非作者本人的测试用户成功运行起来

### 关键决策（到时候再做）

- 游戏是否商业化（影响开源框架许可证策略）
- 开源框架是否包含默认插件（Save the Cat 等）
- 社区如何贡献插件

### 阶段 4 切换协议（2026-05-09 战略校准 v0.1 吸收）

> 来源：`/docs/reviews/master_plan/2026-05-09_strategy_calibration_v0.1.md` §2 Q1.4 + Q1.5。给 L2 阶段 4 规划师起手时阅读。

- **北极星指标**：A 完成度（作者本人 RPG 作品完成）
- **工具改进合法触发条件**：写内容时遇到瓶颈 + 改进能加速 A
  - 评估问句：这个工具改进会让 A 完成时间缩短吗？
  - 答案 = no → 推到 TODOS / 阶段 4 之后
  - 答案 = yes → 在最小可行范围内做
- **Scope 弹性**：MVP 场景数量从硬性数字改为 10–100 弹性区间，从 10 起步阶梯扩张（10 → 30 → 50 → 100，按需）。见 ADR-010 v0.2 修订
- **完成定义三档**：(b) 作者本人玩通 → (c) 3–5 朋友玩通 → (d) itch.io 免费发布
- **(e) Steam 上架**：跳过，除非 itch.io 反响足够好后再决定
  - 理由：Steam 真实成本 = $100 USD Steam Direct 沉没 + 8 种胶囊规格 + IARC 强制评级 + Valve 审核 2–5 工作日 + 必须 Win/Mac binary 通过测试 + 中国作者 W-8BEN 税务流程 + 首次上架 2–4 周；vs itch.io 1–3 小时无审核
- **失败模式警示**：警惕"做工具滑回继续做工具"的失败模式（很多独立创作者最终成了引擎/工具开发者而没做出游戏）。北极星指标 + 工具改进必须服务 A 完成时间 = 这个失败模式的防御机制

---

## 更新记录

- **2026-04-24**：阶段 0 验收通过（见 `/docs/STAGE_0_ACCEPTANCE.md`）
- **2026-04-25**：阶段 1.5「视觉资产生成」段落插入；ADR-011/012/013 立项
- **2026-04-30**：阶段 1 验收**有条件通过**（见 `/docs/STAGE_1_ACCEPTANCE.md`）。Schema 合格率 85%（净模型层 ≈ 95%）；AI 判官接受率 100%。R1–R8 遗留项归阶段 1.5 / 阶段 2 处理
- **2026-04-30**：阶段 1 验收签字；阶段 1.5 任务规划落地（`/docs/STAGE_1.5_TASKS.md` v0.1）；ADR-014（视觉资产双模生成策略）立项
- **2026-04-30**：Round 5 总规划综合评审完成（Claude × GPT-5.5）；ADR-015（阶段 1.5 与阶段 2 sequencing）立项；ROADMAP 阶段 2 启动闸门 + 阶段 3 完成标志强化项占位增订；详见 `/docs/DEBATE_NOTES.md` Round 5 段落与 `/docs/reviews/master_plan/`
- **2026-05-02**：阶段 1.5 验收**部分通过 / 有条件通过**（见 `/docs/STAGE_1.5_ACCEPTANCE.md`）。10 任务 ABC 全闭环 + 工具链端到端实证（mini probe vellin 5 张入库 PASS）；R1.5-1~6 遗留（剩余 14 立绘 + 1 background 全 batch 生图作者主动跳过 / 接受率未测 / AI 判官 vs 作者 kappa 未算 / C4 parity smoke 未跑 / alpha 形式合规但实际不透明 / mini probe 工作流 ergonomic）。ADR-015 串行卡口解锁——阶段 2 schema commit 现可启动
- **2026-05-03**：§阶段 2 完成标志措辞从"证明任意合法状态组合下至少有 1 个结局可达"修订为"抽样验证 N=100 路径 + 有界符号执行下未发现反例"，与 ADR-021（待立项）实际口径对齐。来源：STAGE_2_TASKS_v1.0_draft §13 X1（GPT-5.5 critique 5.4 整合）。
- **2026-05-07**：阶段 2 验收**通过**（见 `/docs/STAGE_2_ACCEPTANCE.md`）。baseline_011 N=15 gross_pass_rate **100%**（schema / topology / sampling / mechanical 全 100%）；ADR-016/017/018/019/020/021 立项 + 落地；R2.X follow-up 修复链路 7 项（R2.2 → R2.6 → R2.7 → R2.8 → R2.9 → R2.10a → R2.10b）；R2-5 / R2-10c / R2-iter-逃逸 / R2-cyclic / R2-1 / X4 六条遗留（不阻塞阶段 3 启动）。审美层（[A]/[R]/[S]）评估推迟到阶段 4——feedback memory 锁定，X4 ADR-020 v0.2 修订属未来 L1 文档级元任务。`/docs/HANDOFF_STAGE_2_TO_3.md` v0.1 草稿同期产出。
- **2026-05-09**：阶段 4 切换协议子段插入（北极星 = A 完成度 / Scope 弹性 10–100 / 完成定义三档 / 跳过 Steam (e) / 失败模式警示）；联动 ADR-010 v0.2 修订（MVP 场景从硬性 50–100 改为弹性 10–100）+ ADR-027 立项（World-Agnostic Principle）。来源：`/docs/reviews/master_plan/2026-05-09_strategy_calibration_v0.1.md` v0.1。
- **2026-05-12**：阶段 3 §scope 声明段新增（不做战斗 / 思维内阁 / 内心独白；主做对话 + 调查 + 物品 + NPC + 技能体系（项目配置层定义）+ 检定；CoC 主导）+ 审美层 review 激活前置子段新增（保留 [A] ≥ 60% pilot + Wilson CI；新增 T-3X-0/1 作 T-3.10 前置）+ 阶段概览表阶段 3 时长加 1-3 周（5-9 周；含 T-3X-0 作者锚点工程）。来源：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.1。联动 PR-A（ADR-030 + ADR-020 v0.2；PR #51 merged 2026-05-12）+ PR-C（STAGE_3_TASKS v1.0.1 + T-3.10.md；PR #52 merged 2026-05-12）。L1 fixation 执行会话产出（本 PR）。
- **2026-05-13**：ADR-031 GM 抉择空间结构化方案 立项 + T-3X-1 拆分为 T-3X-1a + T-3X-1b 校准联动。阶段概览表阶段 3 时长再次校准（5-9 周 → 6-11 周；含 T-3X-1b NPC 状态机 +1-2 周）。来源：[/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1（L2 综合规划师产出）+ 作者 2026-05-13 拍板 5 项推荐（§5.5）。联动 L1 fixation：DECISIONS ADR-031 + DEBATE_NOTES §10 核心赌注段 + STAGE_3_TASKS v1.0.2（T-3X-1 拆分）。
- **2026-05-25**：ADR-036 立项（Forgewright 采用分模块 license：runtime Apache 2.0 / 开发期工具 AGPL v3 / 文档 CC-BY 4.0 / content CC-BY-NC 4.0 / game Proprietary）。设计原理 = CLAUDE.md「运行时 vs 生产期分离」（ADR-002 + ADR-004）。PR #71 merged 2026-05-25（merge commit `9190fff` / 业务 commit `b14ad15`）实际落地 9 模块 LICENSE 文件 + 根 `/LICENSE` 总览 + `/docs/FAQ-LICENSE.md` 11 题 + README 开发者承诺段。外部依赖：dialogue-flow-skill 仓库（private；[outsiderrr/dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill)）Phase 3 Dual Licensing 通过 `/generator` AGPL v3 集成。落地走 L1 直签 main fixation 模式（参 `aeea12e` 升格 governance 先例），破例跳过标准 ABC 闭环；不归 STAGE_3_TASKS §1.5.4 跳 BC 5 类。阶段 4 §完成标志「开源框架仓库独立 + LICENSE（推荐 MIT）」占位被本 ADR 取代。本 L1 fixation 会话产出。

## 版本

本文件版本：v0.1
最后更新：[作者填写日期]