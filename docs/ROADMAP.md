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
| 3 | 完整内容生产流水线 + 审阅工具 | 4–6 周 | 是 |
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
- validator 扩展：结局可达性保证（graceful degradation validation）—— 证明任意合法状态组合下至少有 1 个结局可达

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

---

## 更新记录

- **2026-04-24**：阶段 0 验收通过（见 `/docs/STAGE_0_ACCEPTANCE.md`）
- **2026-04-25**：阶段 1.5「视觉资产生成」段落插入；ADR-011/012/013 立项
- **2026-04-30**：阶段 1 验收**有条件通过**（见 `/docs/STAGE_1_ACCEPTANCE.md`）。Schema 合格率 85%（净模型层 ≈ 95%）；AI 判官接受率 100%。R1–R8 遗留项归阶段 1.5 / 阶段 2 处理
- **2026-04-30**：阶段 1 验收签字；阶段 1.5 任务规划落地（`/docs/STAGE_1.5_TASKS.md` v0.1）；ADR-014（视觉资产双模生成策略）立项
- **2026-04-30**：Round 5 总规划综合评审完成（Claude × GPT-5.5）；ADR-015（阶段 1.5 与阶段 2 sequencing）立项；ROADMAP 阶段 2 启动闸门 + 阶段 3 完成标志强化项占位增订；详见 `/docs/DEBATE_NOTES.md` Round 5 段落与 `/docs/reviews/master_plan/`

## 版本

本文件版本：v0.1
最后更新：[作者填写日期]