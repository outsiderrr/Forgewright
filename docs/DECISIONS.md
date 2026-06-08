# DECISIONS.md

> Architectural Decision Records (ADR) for Forgewright.
>
> 每条决策是独立的、有编号的、原子的。
> 格式：背景 / 决策 / 替代方案 / 后果 / 状态。
> 决策一旦标记为"已接受"，修改需要作者明确批准并记录在下方"变更历史"。

---

## ADR-001：玩家交互采用预生成选项式，不是自由文本对话

**状态**：已接受

**背景**：项目初期讨论未明确玩家交互模式，导致架构讨论向"实时 AI 叙事引擎"方向发散。

**决策**：玩家交互模式是博德之门 3 式的，每个场景玩家从 3–6 个预生成选项中选择。所有对白由开发期生成，运行时无 LLM 调用。

**替代方案及否决理由**：
- 自由文本对话（如 AI Dungeon）：运行时成本高、玩家欺诈面大、内容失控
- 混合模式（选项 + 偶尔开放输入）：架构复杂度翻倍，边际价值低

**后果**：
- 运行时极简，无延迟压力
- 不存在玩家欺诈防御问题
- 内容规模受作者审阅带宽限制
- 开发期内容生成成为主要工程挑战

---

## ADR-002：运行时不调用 LLM

**状态**：已接受

**背景**：见 ADR-001。

**决策**：游戏运行时（`/engine`）是一个纯确定性 JSON 对话图播放器，不包含任何 LLM 调用、不依赖任何 AI 服务。

**替代方案及否决理由**：
- 运行时做"智能对白微调"：引入网络依赖、延迟、成本、一致性风险，收益不足
- 运行时做"实时 NPC 记忆总结"：同上

**后果**：
- 游戏可完全离线运行
- 运行时代码量可控制在 500 行以内
- 玩家体验无网络依赖
- 所有智能在开发期完成，运行时是"播放机"

---

## ADR-003：数据格式采用 JSON-native

**状态**：已接受

**背景**：候选格式包括 Articy、Ink、Fountain、FDX、Yarn Spinner、自定义 JSON。

**决策**：所有核心数据结构由 JSON Schema 定义，文件为 JSON/YAML。Ink/Fountain 等格式仅作为可选的导入/导出 adapter。

**替代方案及否决理由**：见 DEBATE_NOTES 主题 3。

**后果**：
- 开源门槛低，任何语言可读写
- 无需训练 Claude 理解专门 DSL
- 可直接使用 JSON Schema 生态（constrained decoding、结构化输出）
- 放弃了某些 DSL 的人性化语法糖

---

## ADR-004：运行时与生产期严格分离

**状态**：已接受

**背景**：避免"智能慢慢渗透到运行时"的架构腐烂。

**决策**：仓库分为两条相互独立的代码路径：
- **运行时路径**：`/engine` + `/state` 的读部分
- **生产期路径**：`/generator` + `/validator` + `/tools` + `/state` 的写部分

**替代方案及否决理由**：
- 统一架构（运行时和生产期共享 LLM 调度层）：诱使在运行时引入 LLM，违反 ADR-002

**后果**：
- 生产期可使用重工具链（LangChain、复杂 prompt 链、审阅界面）
- 运行时可独立部署到任何设备
- 两条路径可独立演进

---

## ADR-005：编剧理论作为可替换插件，不是核心

**状态**：已接受

**背景**：初始调研覆盖十七个编剧学派。若把任何一个硬编码进核心，开源框架就失去了中立性。

**决策**：编剧理论全部作为 `/generator/plugins/<theory_name>/` 目录下的插件存在。核心生成管线对理论选型保持中立。开发者可启用多个、任选一个、或全部禁用。

**替代方案及否决理由**：
- 硬编码 Save the Cat 作为默认：对非好莱坞风格项目不友好
- 硬编码 Egri Premise 作为校验器：评审者指出的"系统暴政"风险

**后果**：
- 插件接口成为关键设计（未来会有 ADR 专门讨论）
- 默认插件包需要自带 2–3 个代表性理论（推荐 Save the Cat、起承转结、Story Circle）
- 不同作者的游戏可能用截然不同的插件组合

---

## ADR-006：世界本体是真相之源（Single Source of Truth）

**状态**：已接受

**背景**：AI 生成内容的事实一致性需要锚点。

**决策**：世界本体（`/state/ontology/`）存储所有确定性事实：世界地理、角色花名册、物品清单、派系关系、时间线、核心设定。它由作者（人类）主编维护。**LLM 不能直接写本体**。AI 生成的内容必须能追溯到本体中的实体，违反本体的内容被校验器拒收。

**替代方案及否决理由**：
- LLM 可写本体：AI 幻觉会永久污染世界设定

**后果**：
- 作者承担本体主编责任
- 生成内容的事实校验有硬性锚点
- 本体的 Schema 设计是早期关键任务

---

## ADR-007：框架核心是生成 Runtime，不是理论 Parser

**状态**：已接受

**背景**：评审者的第三轮钩子（见 DEBATE_NOTES 主题 4）。

**决策**：开源框架的核心价值在工程基础设施（上下文管理、状态持久化、LLM 调度、评测回归、错误恢复、版本控制、审阅工具），不在编剧理论的参数化。后者是插件层，开发者可选。

**替代方案及否决理由**：见 DEBATE_NOTES 主题 4。

**后果**：
- 仓库结构以基础设施模块为主（`/engine` `/state` `/generator` `/validator` `/tools`），而不是以理论模块为主
- 理论插件是附加价值，不是卖点

---

## ADR-008：LLM 不能直接修改状态

**状态**：已接受

**背景**：AI 幻觉会污染状态。

**决策**：所有状态变更必须通过白名单化的 function-calling 触发，由确定性代码执行。LLM 只能输出候选 intent tag，tag 必须经过 Schema 校验 + 前置条件校验才能被执行。

**替代方案及否决理由**：
- LLM 直接写状态：世界幻觉级污染
- LLM 生成 SQL/代码执行：代码注入风险 + 一致性风险

**后果**：
- 开发期每次生成后有校验步骤
- function 白名单的设计是关键任务
- LLM 输出被限制在"提议"而非"执行"

---

## ADR-009：评测分三层（路径 / 拓扑 / 模拟）

**状态**：已接受

**背景**：见 DEBATE_NOTES 主题 8。

**决策**：评测体系分三层：
1. **路径层**：每条采样路径的节拍、人物、因果合规（story-bench 风格）
2. **拓扑层**：图论方法检查覆盖率、不可达、死锁、关键路径
3. **模拟层**：LLM-as-judge + 模拟玩家路径，抽样评分找出最差内容

**替代方案及否决理由**：
- 只做路径层：无法发现分支耦合问题
- 只做人工评测：不规模化

**后果**：
- 校验器模块（`/validator`）要实现第二层
- 第三层需要单独的 playtest bot 框架
- 评测数据本身成为可开源资产

---

## ADR-010：开发规模控制在 50–100 场景的 MVP

**状态**：已接受

**背景**：本项目短期目标是作者单人可完成的中小型 RPG，避开"谁写几千节点的图"这一未解问题。

**决策**：MVP 游戏规模控制在 50–100 个场景（每个场景约 5–15 个节点）。骨架由作者手工定义，子树由 AI 生成，人工审阅。

**替代方案及否决理由**：
- 野心扩大到 BG3 规模（几千场景）：撞上未解研究问题，单人不可行
- 极小规模（10 场景）：无法验证流水线价值

**后果**：
- 工作负载可控（按每天审阅 2–5 场景估算，50–100 场景需 1–3 个月审阅时间）
- 避开规模化研究难题
- 规模扩张是未来决策，不在当前阶段范围

### v0.2（2026-05-09 战略校准 v0.1 吸收）

**修订内容**：MVP 场景数量从硬性 "50–100 场景" 修订为 **10–100 弹性区间**，从 10 起步阶梯扩张（10 → 30 → 50 → 100，按需）。

**理由**：来自 2026-05-09 战略校准 v0.1 §2 Q1.4 / Q1.5：

- 快速 end-to-end 反馈优先于一次性达成上限
- 10 场景版本能验证全流水线 + 给作者快速反馈
- 阶梯扩张允许根据实际审阅节奏调整
- 不预先承诺 100 场景

**追溯**：见 `/docs/reviews/master_plan/2026-05-09_strategy_calibration_v0.1.md` §2

**对 ROADMAP 的影响**：阶段 4 切换协议明确北极星 = A 完成度，scope 弹性是其落地工具

---

## ADR-011：LLM 提供商默认 Gemini 3.1 Pro + LLMProvider 可插拔接口

**状态**：已接受（2026-04-25）

**背景**：阶段 1 首次引入 LLM。项目长期目标是开源框架，开源用户必须能换模型，不能把仓库绑死在单一供应商上。

**决策**：默认提供商 = Google Gemini 3.1 Pro。`/generator/` 内部定义最小 `LLMProvider` Protocol，包含两个方法：`generate_structured` 与 `estimate_cost`。阶段 1 实现 `GeminiProvider`；OpenAI / Anthropic / 本地模型由后续或社区实现。

**替代方案及否决理由**：
- 直接绑定单一 SDK（无 Protocol）：阻碍开源用户换模型，违反长期目标
- 引入 LangChain / LiteLLM 等重抽象层：违反 ADR-004 的极简精神

**后果**：
- `/generator/llm_provider.py` 是新关键接口
- 阶段 1 任务清单含一条专门的"接口设计"工作

---

## ADR-012：成本治理与密钥管理

**状态**：已接受（2026-04-25）

**背景**：阶段 1 首次产生 API 调用成本，需要早期防失控（避免凌晨耗尽预算之类的事故）。

**决策**：
- **密钥**：环境变量 `GEMINI_API_KEY`；开发期通过 `.env` 文件加载（gitignore），仓库提供 `.env.example` 模板
- **硬卡**：`/generator/budget.py` 模块；默认每日 $10、单次调用 $0.50，可由配置覆盖；超额抛 `BudgetExceeded` 异常
- **落地日志**：`/generator/cost_log.jsonl`（gitignore），每次调用一行，含 `timestamp` / `model` / `input_tokens` / `output_tokens` / `cost_usd`
- **阶段 1 总盘子建议**：$30

**替代方案及否决理由**：
- 不做硬卡、靠云控制台预警：反应慢、可能凌晨耗尽预算
- 把密钥写入仓库（即便加密）：开源后社区无法自行替换

**后果**：
- 每个 LLM 调用必须经 `budget.check_and_charge()` 拦一次

---

## ADR-013：Structured Output 策略

**状态**：已接受（2026-04-25）

**背景**：阶段 1 目标 Schema 合格率 ≥ 95%，不能靠重试堆 token 来达成。

**决策**：
- **主策略**：Gemini `response_mime_type="application/json"` + `response_schema=<DialogueNode JSON Schema>`
- **重试**：最多 2 次（共 3 次），失败时把 validator 错误回喂模型
- **重试不换 prompt**（保持可重现）；3 次都失败 → 标记 `generation_failed`，写日志，**不抛异常**
- **其他 provider**：实现 `LLMProvider` 时各自映射本平台的结构化输出能力（OpenAI `json_schema` / Anthropic tool use / 本地模型 free-text + 校验）

**替代方案及否决理由**：
- 自由文本 + 校验重试为主：烧 token，不可预测
- 不重试：阶段 1 95% 合格率难达标

**后果**：
- `generate_node` 有清晰的"3 次试错预算"语义
- 超时由调用方决定是否人工介入

---

## ADR-014：视觉资产双模生成策略 + GPT-Image 默认 + 一致性策略

**状态**：已接受（2026-04-30）

**背景**：阶段 1.5 引入视觉资产生成。作者订阅 ChatGPT Plus（$20/月，含 GPT-Image 网页生成额度）。直接调 OpenAI Image API 单张 $0.04–$0.17，开源用户无 API 预算时无法跑通流水线。需要一种既能让作者立即开工（无需先配 API key）、又能让开源用户在零 API 预算下走通流水线、还保留批量自动化能力的策略。

**决策**：

- **双模并存**：
  - **Dev 模式（主推）**：作者把 prompt 复制到 chatgpt.com 手动生成、人工审、合适的下载入库；摊薄边际成本 ≈ $0/张（订阅是 sunk cost）
  - **API 模式（生产/批量）**：用 OpenAI Image API 自动批量；单张约 $0.04–$0.17
- **图像提供商**：默认 GPT-Image（OpenAI 系；与 ChatGPT Plus 订阅同源；dev/prod 共用一套 prompt）。其他提供商（Imagen / Flux / Midjourney / 本地 SDXL）由 ImageProvider 接口预留扩展位
- **角色一致性策略**：**C + B 兜底**——容忍同一角色不同立绘细微差异（C）；prompt 显式描述固定特征（眼睛颜色 / 发型 / 服装细节）做兜底（B）。GPT-Image 不支持 ControlNet/LoRA；如未来一致性要求极高，可另开本地 SDXL 渠道，但代价是开源用户门槛上升
- **manual 模式契约（两段式）**：第一段 `generate_character_sheet(mode='manual')` 产出 prompt 包到 `/content/visuals/_pending/<asset_id>/`；作者人工生成下载；第二段 `image_import` CLI 扫描 → 校验 → 入库
- **预算治理**：API 部分总盘子 $20–$40；单次硬卡 $1.00；image cost log 独立于文本（`/generator/image_cost_log.jsonl`）；manual 模式 `estimate_cost=0` 仍走 budget 接口（统一）

**替代方案及否决理由**：

- 仅 API 模式：开源用户无 API 预算时无法跑通流水线，违反长期开源目标
- 仅 manual 模式：无法批量；规模化产线不可行
- 强制角色一致性方案 A（GPT-Image character reference 输入）：API 接口稳定性未验证；推到后续 PR
- 自训本地 SDXL：开源用户门槛过高（需 GPU + 模型权重 + ControlNet）

**后果**：

- ImageProvider 接口必须支持两种实现：`ManualImportProvider` + `OpenAIImageProvider`
- `generate_character_sheet` / `generate_scene_background` 在 manual 模式下变两段式
- 1.5 启动不需立即配 OpenAI API key，作者可马上开始
- 这同样是开源价值点——开源用户没有 API 预算时同样能用 manual 模式跑通流水线
- 一致性策略 C+B 决定 prompt 模板必须包含"角色固定特征描述"段；规划师 T-1.5.6 落地

---

## ADR-015：阶段 1.5 与阶段 2 sequencing — 1.5 主线先启动 / 阶段 2 schema 可并行起草 / commit 串行

**状态**：已接受（2026-04-30）

**背景**：Round 5 总规划评审（Claude × GPT-5.5）综合 memo §10 + §9.1 关闭了 1.5 与阶段 2 的启动顺序问题。ADR-014 manual 模式消除了 1.5 的资金阻塞（无需先配 OpenAI API key 即可开工）后，1.5 与阶段 2 的相对启动顺序变得不明确——`HANDOFF_STAGE_1_TO_2.md` 仍写"阶段 1.5 已推迟"过期叙述（U-GPT-2），与 ADR-014 现状冲突，会让后续执行会话误读。同时阶段 2 启动需要一系列前置工作（本体最小可生成契约 / R 项 cleanup gate / baseline 协议——见 synthesis §6），这些可在 1.5 进行期间并行起草，但实际 schema commit 应等 1.5 验收以避免 Schema 漂移（遵守阶段 0/1.5 串行卡口先例）。

**决策**：

- **阶段 1.5 manual 主线先启动**——manual 路径不依赖 OpenAI key，可立即开跑；为 forward 主线
- **阶段 2 本体 / 角色槽位 schema 设计可并行起草**——规划层文档（草拟 ADR / 范围讨论 / 任务拆分）不阻塞 1.5；可由阶段 2 规划师在 1.5 启动后立刻开始
- **阶段 2 任何 schema 文件实际 commit 等 1.5 验收后**——遵守阶段 0/1.5 串行卡口先例；schema 变更串行
- **阶段 2 启动具体闸门清单**（本体最小契约范围 / R 项处理 / baseline 协议 / 角色槽位持久化形态等）由阶段 2 规划师基于 synthesis §6 + §9 开放决策落地，本 ADR 不替它拍板

**替代方案及否决理由**：

- **1.5 与 2 串行**（必须 1.5 验收后才能起草 stage 2 schema）：浪费 1.5 期间的规划带宽；阶段 2 规划层工作可与 1.5 实施工作天然解耦
- **1.5 与 2 完全并行**（schema 实际 commit 也并行）：违反 ADR-006 + 阶段 0/1.5 串行卡口先例；schema 漂移风险高，1.5 的 `visual_assets` 字段与阶段 2 的 `slot_tags` / 本体最小 schema 同时进 git 会撞车

**后果**：

- 阶段 2 规划师可在阶段 1.5 启动后立刻开始（写 ADR 草拟 / synthesis §6 闸门细化 / 任务拆分预想）
- 阶段 2 任何 commit 进 `/schema/*` 必须验证阶段 1.5 已签字
- Round 5 synthesis §9 开放决策清单（9 项中除 §9.1 已闭环外）大部分由阶段 2 规划师承担拍板
- `HANDOFF_STAGE_1_TO_2.md` "1.5 已推迟"叙述同期修订（U-GPT-2 闭环）

---

## ADR-016：阶段 2 本体最小可生成契约

**状态**：已接受（2026-05-03）

**背景**：阶段 0/1 本体桩态启动阶段 2 = R4/R5 在多节点指数化放大成场景级污染（Round 5 synthesis §3.3 + GPT §3.1 共识）。阶段 2 起手必须一次性落地正式本体最小契约 schema，否则下游 prompt 模板（T-2.5）/ 场景生成（T-2.6）/ validator 扩展（T-2.7）全部建立在不可锚定的事实空间上。

**决策**：阶段 2 起手期一次性落地正式本体最小契约 schema，范围如下：

- **character 实体**：`id`（pattern `^char_[a-z0-9_]+$`，envelope 字段名；不引入 `character_id` 冗余名）/ `display_name` / `description` / `state_path_slug`（默认 = `id` 去 `char_` 前缀；`pattern: "^[a-z0-9_]+$"`；作者可校准）/ `character_features`（描述性特征数组，含如 vellin "stoic mercenary"）/ `dramatic_triggers`（戏剧义务字段，结构 `[{trait, when, how, priority?, cooldown_scenes?}]`；后两项 optional）/ `relations: []`（嵌入式，含 `narrative_weight`，详 ADR-018）/ `visual_assets`（已由阶段 1.5 加，保留）
- **location 实体**：`id`（pattern `^(scene_|loc_)[a-z0-9_]+$`）/ `display_name` / `description` / `location_type: enum["scene","sublocation"]` / `parent_location_ref`（场景层级）
- **state path 命名空间表**（阶段 2 起 path 命名必须落入这五个命名空间之一，否则 validator 拒收）：
  - `world.*`（含 `world.scene_count` / `world.long_rest_count` 系统时间双轨）
  - `faction.<faction_id>.*`
  - `relationship.<state_path_slug>.*`（`<state_path_slug>` = character entity 的 `state_path_slug` 字段值，不是 `<character_id>`；保 gold scene `relationship.vellin.trust` 不动）
  - `flag.*`
  - `player.*`
- **Chapter/Act 容器 schema**：`chapter_id`（pattern `^chap_[a-z0-9_]+$`）/ `display_name` / `acts: [{act_id, display_name, included_scenes: [scene_anchor]}]`；本体新增顶层 `chapters: []` 数组（U-CL-4 强建议前移到阶段 2，避免阶段 1/2 已生成内容到阶段 3 需回填层级）
- **系统时间双轨**：`world.scene_count`（每场景 +1，被动节奏）+ `world.long_rest_count`（玩家长休 +1，玩家节奏控制感）；不做实时计时器（违反 ADR-002 极简运行时）
- **schema 版本号策略**：新建 character / location / clock / chapter schema 文件首版即 const `"0.3.0"`；既有 dialogue_graph / node / option / state_effect / state_condition 的 `schema_version` const 保持 `"0.1.1"` 不动；新增字段（如 `generation_trace.slot_assignments`，详 ADR-019）走 optional + `additionalProperties` 兼容路径

**替代方案及否决理由**：

- 推到阶段 3：synthesis §3.3 + GPT §3.1 已共识阶段 2 启动需要本体最小契约
- 仅 character + location 不加 Chapter/Act：阶段 1/2 已生成内容到阶段 3 需回填层级（U-CL-4）
- 加 Sibling 涌现项目接口预留：premature abstraction，PZ 反思 §6 已强约束
- state path 用 `<character_id>` 全名：会让 gold scene `relationship.vellin.trust` 失败；改 gold 风险高于加 slug 字段
- 新增字段 bump 既有 schema_version 至 0.3.0：会破 gold scene 与所有阶段 0/1 测试；按 SCHEMA_v0.2 "非结构性变更不联动 schema_version" 先例，optional 字段走兼容路径

**后果**：

- 阶段 2 schema commit 全部串行卡口在本 ADR 落地后启动（T-2.2）
- 机械预检器（T-2.4）必须按五个 state path 命名空间 + `state_path_slug` 反查执行 path 前缀 / `BOND_ID_UNKNOWN` 检查
- validator 扩展（T-2.7）必须支持本体引用闭合 + state path 命名空间合法性 + state_path_slug 反查
- prompt 模板（T-2.5）必须把 character_features / dramatic_triggers / Chapter/Act / 系统时间双轨纳入 context

### v0.4（2026-05-18 ADR-034 + ADR-034.1 落地承接）

**修订内容**：

1. **新增第 6 个 state path 命名空间** `knowledge.*`（玩家知识 / fact-level player knowledge）：
   - pattern：`^knowledge\.[a-z0-9_]+(\.[a-z0-9_]+)*$`
   - 用途：跟踪玩家在游戏过程中获得的离散事实（如 `knowledge.npc_is_killer` / `knowledge.crime_motive` / `knowledge.<reveal_id>.stage_<n>` for progressive disclosure）
   - 对应 Ink LIST + Articy Glossary 业界主流（ADR-034 §2 调研结论）

2. **Monotonic 命名空间清单**（ADR-034 D11 落地）：
   - `flag.player_*` — LLM 生成内容只能 `set` / `inc` / `add`，禁止 `dec` / `remove`（玩家不忘行为历史）
   - `knowledge.*` — 同上（玩家不忘事实知识）
   - 其他命名空间（`world.*` / `faction.<id>.*` / `relationship.<slug>.*` / `flag.*`（非 `player_`）/ `player.*`）允许双向；详 ADR-034 D11
   - 作者手填内容（`generation_trace.source == "human"`）不受此规则约束

**理由**：T-3Y 进展报告 §5.2 拍板"不模拟玩家遗忘"——schema 层补防御。T-3Y player_known_info 设计需要 `knowledge.*` 命名空间作为 first-class primitive，对齐 Ink LIST + Articy Glossary 业界主流（ADR-034 §2 调研）。作者 2026-05-18 拍板（5 个争议点全部接受 Agent A 倾向，含 Gap 8 + Gap 9）。

**追溯**：见 [/docs/reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md](reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md) v0.2 §6.3 D3 + D11 + §7.4 拍板表。

**对工程的影响**：
- validator（`/validator/`）必须扩展支持第 6 命名空间 + monotonic 规则
- 机械预检器（T-2.4 后续修订）的命名空间清单更新至 6 条
- T-3Y-1 工程会话**硬依赖**此 v0.4 修订；必须先落地 `knowledge.*` 命名空间
- schema 文件如需 pattern 校验，加入第 6 命名空间

---

## ADR-017：时钟系统

**状态**：已接受（2026-05-03）

**背景**：PbtA Faction Clocks（DEBATE_NOTES §6.1）作为 ADR-006 真相之源的一部分，需要正式 schema；PZ 反思 §3.2 给出草图。阻塞下游 prompt 模板（T-2.5）context 注入与 validator 第二层（T-2.7）状态空间推理。

**决策**：

- **时钟分类三类**：`world` / `faction` / `environmental`
- **`Clock` schema 字段**：`id` / `name` / `scope: enum["world","faction","environmental"]` / `ticks_total: int`（schema maximum 20）/ `ticks_filled: int`（PbtA 术语；非 ticks_current）/ `advance_rule: {type, params}` / `tick_effects: [{at_tick, effect_op, path, value}]`
- **advance_rule.type 默认范围**：仅 `event_based` 子类（`every_n_scenes` / `on_long_rest` / `on_faction_action` / `on_player_choice`）；不做 time-based（运行时无真时间，违反 ADR-002）；SCHEMA_v0.3.md §4 明示"不存在 time_based 子类"
- **边界软上限**：单 clock `ticks_total ≤ 20`（schema maximum 落地）；同时活跃 clocks `≤ 10` 由 T-2.7 sampling/validator 出 warning 级检查（schema 层不加；T-2.7 落地后由实测倒推真实上限，本 ADR v0.2 修订）
- **`tick_effects.effect_op` 与 `StateEffect.op` 映射**：`effect_op` 枚举值与现有 `StateEffect.op`（`set` / `inc` / `dec` / `add` / `remove`）一致；T-2.7 effect 应用器用统一映射函数
- **时钟存储位置**：`/state/ontology/<world_name>.json` 顶层 `clocks: []` 数组

**替代方案及否决理由**：

- 不立时钟 schema：阻塞 prompt 模板（T-2.5）context 注入；扩 ADR-006 而不分立 = 单条 ADR 太大
- 含 time-based 步进：违反 ADR-002 + ADR-004 极简精神；运行时是 JSON 播放器无真时间
- 同时活跃 ≤ 10 写进 schema：定义域随阶段演进；T-2.7 实测倒推后由 ADR-017 v0.2 修订，比硬写 schema 灵活

**后果**：

- schema 落地（T-2.2）必须新建 clock schema，使用 `ticks_filled` / `ticks_total` maximum 20 / `event_based` advance_rule 契约
- prompt 模板必须在 GraphContext 注入当前活跃 clocks 状态（字段名统一为 `active_clocks`）
- validator 必须校验 `tick_effects.path` 落入合法 state path 命名空间（ADR-016）
- T-2.7 第二层 2B 抽样验证可推理时钟状态空间（`ticks_total` × clocks 数 = 抽样维度）

---

## ADR-018：关系层 narrative_weight

**状态**：已接受（2026-05-03）

**背景**：PZ 反思 §3.3——LLM 倾向把所有关系都写进每场对白，污染节奏；作者需控制"哪些关系真的进戏"。无权重字段时多角色场景下 LLM 写"全员问候"式对白，阶段 2 70% 接受率难达。

**决策**：

- character entity 加 `relations: []` 字段（嵌入式，不引入全局关系表）
- 每项结构：`{target_character_ref, relation_type, narrative_weight: enum["core","minor","context_only"]}`
- 三档语义：
  - `core` = 必须显性体现
  - `minor` = 可选体现
  - `context_only` = 仅作 prompt 一致性 anchor，不出现在玩家可见对白
- prompt 模板（T-2.5）按 `narrative_weight` 决定 context 注入：`core` / `minor` 进 prompt，`context_only` 仅作合法性约束

**替代方案及否决理由**：

- 不加权重字段：LLM 在多角色场景下会写"全员问候"式对白；阶段 2 70% 接受率难达
- 加 numeric weight（0-100）：作者难校准；离散三档对作者审阅心智更友好
- `mandatory / optional / background` 字面：与 BG3 任务系统术语易混淆；core/minor/context_only 偏向叙事理论术语
- 全局关系表：会破 ADR-006 单一真相之源（同一关系在 from / to 两端冗余）；嵌入到 character envelope 内更自然

**后果**：

- 角色花名册更新工作量：T-2.2 落地 vellin / corvan / aelwin 关系矩阵
- prompt 模板必须按 `narrative_weight` 决定注入逻辑

---

## ADR-019：角色槽位持久化形态

**状态**：已接受（2026-05-03）

**背景**：U-GPT-5——ROADMAP 阶段 2 重点工作"角色槽位（role slot casting）与动态选角"持久化决策点未拆开。需明确"抽象槽是 generator 中间产物还是持久化层一等公民"。

**决策**：

- 持久化层（`/state/ontology/` + `/content/<scene>/scene.json`）仍 concrete `character_refs`——不破 ADR-006 单一真相之源
- 抽象槽（如 "the betrayer"、"the witness"、"the broken oath-keeper"）作为 generator 中间产物
- 落到节点级 `generation_trace.slot_assignments` 字段，走 optional + `additionalProperties` 兼容路径，不 bump dialogue_graph schema_version（详 ADR-016 schema 版本号策略）；结构：`slot_assignments: {<slot_id>: {character_ref, assigned_at, source_prompt_hash}}`
- 后续场景生成可读取此 trace 维持槽位一致性（跨场景同槽 → 同 character）
- 阶段 2 不实现"动态换角"逻辑——那是阶段 3 跨场景一致性范畴

**替代方案及否决理由**：

- 持久化层引入 `slot_tags` 字段双轨：违反 ADR-006 单一真相；schema 复杂度大
- 完全只靠 generator 中间产物 + 不写 trace：跨场景重生成不可重现
- generation_trace bump dialogue_graph schema_version 至 0.3.0：会破 gold scene + 阶段 0/1 测试；按 SCHEMA_v0.2 先例 optional 字段走兼容路径更稳

**后果**：

- schema 落地（T-2.2）必须以 optional + `additionalProperties` 兼容路径追加 `generation_trace.slot_assignments`，dialogue_graph / node `schema_version` 保持 `0.1.1`
- `generate_scene`（T-2.6）必须在节点产物里写 `slot_assignments`
- validator 不强制 `slot_assignments` 必填（trace 仍 optional）

---

## ADR-020：阶段 2 baseline 协议

**状态**：已接受（2026-05-03）

**背景**：U-GPT-4 硬闸门——70% 接受率口径必须先定义再写代码（ROADMAP 启动闸门）。模糊定义将下游统计一致性废，阶段 2 验收不可判定。

**决策**：

- **样本数 N**：15 场景（场景级单次成本高于节点级；N=20 太烧；N=10 统计弱）
- **重试规则**：复用 ADR-013 max_retries=2（共 3 次）；schema 失败 + 图论失败回喂模型
- **AI 判官权重**：节点级 21 维度 × 节点数 + 场景级新增 6–10 维度（图拓扑健康 / 节奏 / 角色弧线 / 决策意义 / 收束 / 长度合理 / context 一致性 / 关系层一致性 / 时钟一致性 / ID 命名规范）；具体维度由 T-2.9 落地
- **机械失败口径**：option 长度（≤ 25 汉字）+ path 前缀（落入 ADR-016 五个命名空间）+ bond ID 白名单（state_path_slug 反查）+ target_node_id 闭合 + `unavailable_behavior` 枚举合法性 + state path 命名空间合法性 + StateCondition 形态互斥
- **接受率分母**：通过机械预检 + 进入 review_log 的场景数
- **接受率分子**：作者标 [A]ccept 的场景数（不是 AI 判官打分）
- **报告同时给 gross pass rate 和人工接受率**：gross pass = 通过机械预检的场景数 / 总尝试场景数；接受率（作者签字）作为最终判定
- **AI 判官与作者关系**：AI 判官是辅助参考分（21 维 + 场景级新增），作者最终标 [A]/[R]/[S]——与阶段 1 R6 一致
- **成本估算口径统一**：每场景估 ~$0.5–$1.0；N=15 总 $7–$15；N=20 总 $10–$20

**替代方案及否决理由**：

- N=20 场景：成本 $10–$20，烧；N=15 平衡
- 接受率分子用 AI 判官：阶段 1 R6 已锁"作者最终签字"
- 不定义机械失败口径：U-GPT-4 漏抓的核心点；模糊定义将下游统计一致性废

**后果**：

- T-2.4 R8 机械预检器要按本协议落地
- T-2.9 AI 判官 prompt 按本协议设计权重
- T-2.12 实证 batch run 按 N=15 跑

### v0.2（2026-05-09 审美层决策 v0.2 §6.5 吸收；X4 闭环）

**修订内容**：接受率分子 + 完成判定阶段口径细化为**阶段 2 / 阶段 3 / 阶段 4 三阶段**：

- **阶段 2 期间**：完成判定 = `gross_pass_rate ≥ 70%` 作 logic-layer proxy（合规化阶段 2 验收已有破例；feedback_acceptance_review_deferred_to_stage_4 memory 真实建议正面吸收）
- **阶段 3 期间**：T-3X-0（作者审美锚点工程）+ T-3X-1（ADR-030 立项 + schema + prompt hook）落地后激活 [A]ccept rate 标注；T-3.10 实测期 [A] ≥ 60% pilot + Wilson 95% CI（STAGE_3_TASKS v1.0 §1 阈值不动）
- **阶段 4 期间**：完整 [A]/[R]/[S] 流程（基于 50-100 场景实测反馈迭代 AESTHETIC_PREFERENCES.md v0.2+ 与 ADR-030 v0.2+）

**理由**：

- 阶段 2 收官期实证 baseline_011 N=15 gross_pass_rate 100%（logic-layer 工程层完美），审美层完全跳过——`gross_pass_rate` 作 logic-layer proxy 已被实证认可
- 审美层决策 v0.2 选项 5 通过精选 3 部经典剧本压缩"作者锚点工程"时长，使阶段 3 内激活可行；不需推到阶段 4 全量
- 与 ADR-022 保持兼容（ADR-022 不修订；playtest bots 完成标志阈值原 gate 保留）

**追溯**：见 /docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md（v0.2 同日修订）§6.5 + §8 兼容性表

**对 STAGE_3_TASKS / ROADMAP / HANDOFF 的影响**：见 PR-B（ROADMAP + HANDOFF）+ PR-C（STAGE_3_TASKS）

---

## ADR-021：ADR-009 第二层方法论拆 2A 拓扑 + 2B 抽样验证 + 有界符号执行

**状态**：已接受（2026-05-03）

**背景**：U-GPT-1 🔴——当前 schema 缺状态变量定义域 / 初始状态集合 / effect 边界，"证明任意合法状态组合可达结局"目前不可判定；ROADMAP 阶段 2 完成标志措辞需修订。把启发式包装成"condition-aware 已完成"会误导阶段 2 验收。

**决策**：

- **2A 纯拓扑校验**（图遍历层）：结构拓扑 + condition 引用形态合法性（仅检查 path 命名空间 / op 枚举 / 字段结构）/ 前置条件路径闭合（option.condition 字段格式合法）/ 不可达节点 / 死锁（非 end 节点入度可达但 option 集合中无任何 condition=null option）/ 分支收敛性。**condition satisfiability 不在 2A 内**——避免把启发式包装成 condition-aware 已完成
- **2B 抽样验证 + 有界符号执行**：
  - 抽样 N=100 路径起步（从 entry 出发随机选 option，记录 state 演化，检查能否到 end 节点）
  - 有界符号执行：在 ADR-016 命名空间内枚举 effect 链产生的 state 组合（边界由 ADR-017 时钟数 × `ticks_total` + flag 离散值集决定）
  - condition satisfiability 全部走 2B
- **完成标志措辞修订**（ROADMAP §阶段 2 完成标志，跨边界 X1，由作者另起 L1 doc 修订会话）：从"证明任意合法状态组合下至少有 1 个结局可达"改为"抽样验证 N=100 路径 + 有界符号执行下未发现反例"
- **N 值首版**：N=100；经验阈值，不暗示充分证明；阶段 2 实测后由 ADR-021 v0.2 倒推合理 N
- **完成标志拆双报**：T-2.7 完成标志分别报告（a）2A 纯拓扑 pass（gold scene 全过 + 0 error）；（b）condition-aware（2B 抽样 + 有界符号执行）pass（gold scene 抽样 N=100 全 reach end + 0 反例）

**替代方案及否决理由**：

- 严格证明：当前 schema 不支持，强行写完成标志会造成"过线假象"
- 仅抽样模拟不做有界符号执行：U-GPT-1 推荐双路径——抽样找显式反例，符号执行覆盖低概率组合
- 2A 内含 condition-aware：A2 自承"复杂；起步用启发式"；启发式包装成 condition-aware "已完成"会误导阶段 2 验收
- 给 2A 加有限 state evaluator：state evaluator 复杂度高、超阶段 2 起步范围；拆双报清晰显示边界

**后果**：

- validator 第二层（T-2.7）按 2A + 2B 拆分实现
- T-2.7 完成标志拆双报；T-2.13 验收报告引用双报数据
- ROADMAP 完成标志措辞由作者另起 L1 修订会话同步（不在本任务范围；跨边界 X1）

---

## ADR-022：playtest bots 完成标志阈值

**状态**：已接受（2026-05-08）

**背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 C2——ADR-009 第三层 playtest bots 必须在阶段 3 完成标志里写入，否则"完整内容生产流水线"名不副实。GPT-5.5 critique F9 + F10 + F20 + F21 修订要点：calibration run 必做（避免 N=5×M=20 直接烧穿预算）/ critical / major / minor severity taxonomy / run_manifest.json / 双层输出（path 级 + scene 级）。

**决策**：见 [STAGE_3_TASKS.md §3.1](STAGE_3_TASKS.md)（v1.0 决策核心全文）。要点：

- **bot persona 数 N=5**：cautious / aggressive / completionist / speedrunner / role_player（hand-write 5 个 base + LLM augment description hook 留 null）
- **每场景 paths M=20**：5 persona × 20 paths = 100 paths/scene；与 ADR-021 §2B 抽样 N=100 数量级一致
- **calibration run 必做（F9）**：T-3.4 A 阶段 mandatory smoke = 1 scene × 1 persona × 5 paths 实测 avg calls/path / tokens/path / seconds/path / cost/path；实测后再锁 5×20 参数；如 1 path 平均 5+ calls（每决策节点 + judge），调整 M 上限或 worst-bucket 抽样形态
- **三重 guard（F9）**：`--max-cost-usd <amount>` / `--max-calls <n>` / `--max-wall-clock-min <m>`；任一触发 = abort batch + log
- **critical / major / minor severity taxonomy（F10）**：critical = validator 漏掉的非法路径 / 状态因果矛盾 / 角色或本体直接冲突 / 玩家结果透明度严重误导；major = 显著叙事质量问题；minor = 体例 / 措辞；critical 必须作者明示确认，不能只靠 LLM-as-judge 自动通过 gate
- **双层输出（F21）**：
  - `playtest_NNN/worst_paths.jsonl`（path 级；含 path trace + judge_score + critical_count + severity）
  - `playtest_NNN/worst_scenes.md` + `worst_scenes.json`（scene 级；scene 分数 = path 分布 / critical count / 最低分加权）
- **run_manifest.json（F20）**：每 playtest_NNN 写 model_id / temperature / prompt_hash / persona_hash / option_set / raw_choice / judge_rubric_version
- **完成标志**：至少 5 场景跑过完整 playtest（5×20=100 paths/scene）；worst-10% 清单产出 + 0 critical issue 或全部修复

**替代方案及否决理由**：

- 完全 fixture persona / 完全 LLM 生成 persona：前者缺多样性、后者递归依赖且不可重现
- N=10 × M=50 大体量：撞 PoloAI 余额闸门 + 单 batch 时长爆炸；calibration 后再校准更稳
- 无 calibration（F9 否决）：5×M=20 直接跑 5 场景 = 500 paths，预算靠拍脑袋；先 calibration 再锁参数才对得起 ADR-012 budget governance
- 无 severity rubric（F10 否决）：critical / major / minor 不分会导致 LLM judge 误判轻 / 漏报重；critical 必须作者签字

**后果**：

- T-3.4 落地 `/generator/playtest/`（含 personas/ + run_manifest.json + worst_paths.jsonl + worst_scenes.md/json）
- playtest cost log 独立 `/generator/playtest_cost_log.jsonl`（与 generator 主流程 cost log 解耦；ADR-012 同款形态）
- 阶段 3 末期实测如不足以暴露 worst-bucket，由 ADR-022 v0.2 修订倒推 M 提升 / persona 扩 / sampling strategy 改

---

## ADR-023：content_dependency_index sidecar 形态 + 字段集

**状态**：已接受（2026-05-08）

**背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 C6——本体变更时定向反向 propagate 而非全量重审，必须有依赖索引承载。GPT-5.5 critique F5 修订核心：dep_index 不能从 scene 反推（scene 内容已 lossy；prompt 注入的 ontology / state / clock 引用不全部能从生成产物倒推），必须在 context assembly 阶段以 over-approx trace 形式写入。F15 修订：schema 字段约束加严（state path namespace pattern + uniqueItems + scene_id pattern 与 dialogue_graph.graph_id 对齐 + optional 字段明示 missing-only）。

**决策**：见 [STAGE_3_TASKS.md §3.2](STAGE_3_TASKS.md)（v1.0 决策核心全文）。要点：

- **形态**：per-scene sidecar `<scene>.deps.json`（与 scene.json 同目录；与 visual manifest 哲学一致）
- **写入语义（F5 修订）**：**context assembly over-approx trace**——不是 scene 反查。`_build_scene_context` 阶段累加 `GenerationDependencyTrace`，记录注入到 LLM prompt 的所有 ontology / state / clock / visual / prompt 引用。Conservative over-approx——宁可误报 stale 也不漏依赖
- **schema 字段约束加严（F15）**：
  - state_paths_read / state_paths_written 必须落入 ADR-016 五命名空间 pattern（`world.*` / `faction.*` / `relationship.*` / `flag.*` / `player.*`）
  - 数组字段加 `uniqueItems: true`
  - `scene_id` pattern 与 dialogue_graph `graph_id` 对齐（`^[a-z0-9_]+$`）
  - optional 字段（chapter_id / act_id / visual_asset_ids_referenced / clock_ids_referenced / scene_history_referenced）明示 missing-only（不允许 null）
- **scene_history_referenced 字段** = ADR-024 长对话一致性 A/B hook：阶段 3 末期撞墙可基于此字段升级 RAG (B) 或 memory stream (A)，不需重做 schema
- **新建 `/schema/content_dependency_index.schema.json`** 首版 const `0.3.0`（与 character / location / clock / chapter schema 同源演进；ADR-016 §schema 版本号策略一致）
- **写入时机（与 ADR-026 联动）**：T-3.5 批量调度器写入顺序 = "write scene → assign chapter → write deps → record version"；T-3.7 一致性维护按 sidecar 反向 propagate

**替代方案及否决理由**：

- scene 反查（F5 critique 否决）：scene JSON 不含 prompt 注入 trace；从产物反推丢失"哪些 ontology 引用其实进了 prompt 但没显形在最终 scene"
- 全局索引 `/content/index/dependencies.json`：单文件并发写竞争；不利分布式生成
- SQLite：read-heavy 场景标准选择，但增加运行时依赖；与 ADR-003 JSON-native + 极简精神冲突
- schema 约束太松（F15 critique 否决）：state_paths_read 不限五命名空间会让 dep_index 自身可能引非法 path，让 propagate 工具语义紊乱

**后果**：

- T-3.2 落地 `/schema/content_dependency_index.schema.json`（schema_version = `0.3.0`）+ schema test
- T-3.3 SceneGraphContext 实例化时启动 `GenerationDependencyTrace` 累加（与 ADR-024 联动）
- T-3.5 generate_scene hook 写 sidecar（context trace 形态；与 scene.json 平行落盘）
- T-3.7 一致性维护按 sidecar 反向 propagate（本体变更时定向 mark stale）

---

## ADR-024：长对话一致性 C 起步 + A/B hook

**状态**：已接受（2026-05-08）

**背景**：DEBATE §9.2 长对话一致性列为未解问题（Generative Agents 2023 / RAG-based memory 2024 / Westworld 类项目 / CK 系列均部分缓解，无根治）。ROADMAP §阶段 3 完成标志强化项 U-CL-5。PZ §5 + §7：作者对 AI 进化能力有信心；50–100 场景规模可能不撞 §9.2 真墙；状态文件抽象层"真遇到再说"不预防性设计——但 L2 必须保留 hook 避免阶段 3 中段才发现要重做。GPT-5.5 critique F3 修订：必须改 SceneGraphContext 不是 GraphContext——节点级 GraphContext 阶段 3 不动，scene 级生成根本拿不到节点级 context。

**决策**：见 [STAGE_3_TASKS.md §3.3](STAGE_3_TASKS.md)（v1.0 决策核心全文）。要点：

- **C 起步全套**：
  - prompt 模板 **SceneGraphContext** 注入 `prior_scene_summaries: list[{scene_id, summary, key_state_paths}]` 字段（F3 修订；不是 GraphContext）
  - 摘要来源：作者人工填 OR 半自动 LLM 摘要 + 作者校准（v0.1 起手两条路并存）
  - 上限：每场景 prompt 注入 ≤ 5 条 prior_scene_summaries（避免 prompt 膨胀）
- **token / prompt metrics hook（v1.0 新增）**：每 scene 生成时记录到 dep_index sidecar：
  - `prompt_token_estimate`（注入 prompt 总 token 估算）
  - `summaries_injected_count`（实际注入条数 0-5）
  - `summary_source_hashes`（每条 summary 的 SHA256；溯源用）
  - `truncation_reason`（如超 5 条上限被裁的 reason）
- **A/B hook 留**：content_dependency_index sidecar `scene_history_referenced` 字段（ADR-023 字段集）；阶段 3 末期撞墙可升级
- **不在阶段 3 落地的 A/B**：
  - A. Generative Agents memory stream（Park 2023 风格 episodic / semantic / reflective 多层级）
  - B. RAG over event log（所有过往场景 embed + 按相关性 retrieve）

**替代方案及否决理由**：

- 完整 D hybrid (A + C)：超阶段 3 投资范围；Park 2023 memory stream 实操开放问题（多层 memory 提炼漂移；维护成本高）
- 不立 ADR：阶段 3 实测撞墙时无 schema hook 可升级；属"出问题再做整改"的反式
- 改 GraphContext（F3 critique 否决）：GraphContext 是节点级（`/generator/context_assembler.py:_build_node_context`），scene 级生成根本拿不到；必须改 SceneGraphContext（`_build_scene_context`）

**后果**：

- T-3.3 落地 SceneGraphContext + prompt 模板（skeleton/fill 渲染段加 prior_scene_summaries 字段）+ scene_summary_writer 工具（半自动 LLM 摘要 + 作者校准）
- T-3.5 批量调度器在 SceneSpec.prior_summary_paths 字段（ADR-026）指向预先写好的 summary 文件
- 阶段 3 实测 token 累积曲线 + 接受率回归是否撞墙作 ADR-024 v0.2 修订依据；如撞墙基于 ADR-023 scene_history_referenced 字段升级 RAG (B) 或 memory stream (A)

---

## ADR-025：审阅 UI 架构

**状态**：已接受（2026-05-08）

**背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 U-GPT-7——审阅 UI 第一版必须含图视图（mermaid/dot），避免后期重做审阅心智模型。GPT-5.5 critique F2 + F16 + F17 修订要点：模块边界必须含 pyproject.toml（FastAPI + uvicorn deps + tools package 注册——执行会话否则无法合法落地，CLAUDE.md 规则 2 模块边界严管）/ 拆 a (MVP) + b (integrations)（单任务范围过宽；MVP 浏览器 smoke / 截图 / mermaid 渲染检查也变 mandatory）/ mermaid CDN fallback（ASCII / DOT 文件展示或 vendor 固定版本 bundle，不依赖 CDN 可用性）。

**决策**：见 [STAGE_3_TASKS.md §3.4](STAGE_3_TASKS.md)（v1.0 决策核心全文）。要点：

- **形态**：Web 单页（local file server + 前端 vanilla HTML/JS）
- **工具栈（F2）**：FastAPI 静态 server + uvicorn（**新增 deps**）+ 前端 vanilla HTML/JS（不引入 React / Vue / Svelte，开源门槛低）+ mermaid.js（**vendor bundle 或 CDN with fallback；F17**）
- **`pyproject.toml` 修订（F2）**：T-3.6a / T-3.6b / T-3.7 模块边界**允许修改 pyproject.toml**——加 `fastapi` + `uvicorn` deps + `tools` package 注册
- **拆分（F16）**：
  - **T-3.6a MVP**：scene list + graph 视图（mermaid 渲染）+ validator issues 面板（schema / topology / sampling / mechanical 四 tab）+ 审美层 [A]/[R]/[S] 标注 + reason 文本框
  - **T-3.6b integrations**：visual asset thumbnail（manifest 读取）+ playtest worst paths/scenes 视图（**产物存在则展示，否则隐藏 / 提示未跑**；F13）+ stale list（dep_propagate 集成）+ chapter list 分组
- **mermaid CDN fallback（F17）**：T-3.6a 必须自带 fallback：可切换 ASCII/DOT 文件展示（T-2.8 已有 graph_views 三件套）OR vendor 固定版本 mermaid bundle（推荐 `mermaid@10.x`）；不依赖 CDN 可用性
- **浏览器 smoke / 截图 / mermaid 渲染检查（F16）**：T-3.6a + T-3.6b A 阶段完成标志改 mandatory（不是 optional）
- **read-only**：不做编辑功能；编辑由作者直接改 JSON + git workflow（ADR-008 LLM 不能直接修改状态精神延伸到 UI）
- **运行时部署**：仅生产期；env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 `8765`）；本地 localhost 访问

**替代方案及否决理由**：

- CLI 升级（基于 T-2.8 scene_review_cli 加图视图）：投资低；但 graph 可视化效果差；阶段 3 是产出阶段，审阅效率是关键瓶颈
- 桌面应用（electron / tauri）：投资最高；开源用户额外打包负担
- 不动 pyproject（F2 critique 否决）：执行会话无法合法落地——FastAPI / uvicorn 不在 pyproject deps 即引入失败
- React / Vue / Svelte：开源门槛上升（构建链 + node_modules）；与 ADR-003 JSON-native + 开源极简精神冲突
- 单 T-3.6 任务范围过宽（F16 critique 否决）：浏览器 smoke 也变 mandatory，单任务难做；拆 a / b 后 MVP 先稳，integrations 后跟
- 仅 CDN 不带 fallback（F17 critique 否决）：CDN 不可用时审阅 UI 全瘫；review_ui 是阶段 3 关键瓶颈，可用性优先

**后果**：

- T-3.6a + T-3.6b 落地 `/tools/review_ui/`（含 server.py + api.py + static/ + tests/）
- 复用 T-2.8 graph_views 三件套（mermaid / dot / ascii）作 graph 视图数据源
- pyproject.toml 修订加 fastapi / uvicorn deps + tools package 注册（T-3.6a 或 T-3.7 先到先做）

---

## ADR-026：批量调度器并发模型

**状态**：已接受（2026-05-08）

**背景**：ROADMAP §阶段 3 完成标志要求批量生成调度器（异步跑多场景）。阶段 2 baseline_011 单 iter mean 268s 实测——串行 N=1 跑 10 场景 ≈ 45 分钟，作者无法离开；并发 N=3 ≈ 15 分钟。GPT-5.5 critique F4 + F13 + F14 修订要点：N=3 并发与 prior_scene_summaries 顺序冲突（场景间因果依赖 → 必须 SceneSpec DAG）/ T-3.5 不应依赖 T-3.4（调度器和 playtest 解耦）/ RateLimitedProvider wrapper 必须明示（不在 scene worker 外层限速；同步 generate_structured 内线程安全 bucket 阻塞等待）。

**决策**：见 [STAGE_3_TASKS.md §3.5](STAGE_3_TASKS.md)（v1.0 决策核心全文）。要点：

- **并发模型**：asyncio + N=3 concurrent worker（基础数据：baseline_011 单 iter mean 268s）
- **SceneSpec DAG（F4）**：SceneSpec 加 `depends_on_scene_ids: list[str]` / `sequence_group: str` / `prior_summary_paths: list[Path]` 字段；调度器**拓扑分层**——同层并发（N=3 max），不同层串行；T-3.10 实测场景集声明依赖图，不是 flat specs
- **RateLimitedProvider wrapper（F14）**：实现 `class RateLimitedProvider(LLMProvider)`——同步 `generate_structured` 内线程安全 bucket 阻塞等待；包住所有 LLMProvider 调用（不在 scene worker 外层限速）；解决 token bucket 与 sync provider API 设计边界
- **速率限制**：每 provider token bucket 默认 60 RPM（env `FORGEWRIGHT_PROVIDER_RPM`）
- **ontology 写入**：file lock（fcntl on `/state/ontology/<world>.json`）；scene 文件各自独立 path 不冲突
- **写入顺序（与 ADR-023 联动）**：write scene → assign chapter（T-3.9 helper 调用）→ write deps（T-3.5 含 dep_index trace）→ record version（T-3.8a 调用）
- **依赖关系（F13）**：T-3.5 仅依赖 T-3.2 + T-3.3，**不依赖 T-3.4 playtest**；T-3.4 与 T-3.5 并行
- **失败传播**：单 worker scene 失败不阻塞其他并发场景；每 worker 独立 ProviderError 仪表化（沿用 R2.9）
- **配置**：`FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 `3`） / `FORGEWRIGHT_PROVIDER_RPM`（默认 `60`）

**替代方案及否决理由**：

- 串行 N=1：作者无法离开 45 分钟；不达 ROADMAP "一周 ≥ 10 场景"目标
- N=10 大并发：撞 PoloAI 速率限制 + 余额闸门；token bucket 撑不住
- subprocess fan-out：进程间共享 ontology lock + cost log 复杂度高
- flat queue 无 DAG（F4 critique 否决）：无法处理 prior_scene_summaries 顺序约束（场景 B 依赖场景 A 的 summary，必须 A 先完）；T-3.10 实测场景集会撞这个
- T-3.5 hard depend T-3.4（F13 critique 否决）：调度器和 playtest 解耦更清晰；T-3.4 + T-3.5 并行可加速 Wave 3-4
- 仅外层限速（F14 critique 否决）：内部 provider call 不受限；多 worker 同时 burst 调用会触发 PoloAI 限流；wrapper 内同步阻塞才稳

**后果**：

- T-3.5 落地 `/generator/batch_scheduler.py`（asyncio 拓扑分层）+ `/generator/dep_index_writer.py` + `/generator/_rate_limit.py`（RateLimitedProvider）
- generate_scene 扩展 GenerationDependencyTrace 注入 + dep_index sidecar 写入 hook（T-3.5 范围）
- 阶段 3 实测如撞 PoloAI 余额闸门，作者降 N=1/2 应急；阶段 3 末期 ADR-026 v0.2 修订倒推真实最优 N

---

## ADR-027：世界观不可知性原则（World-Agnostic Principle）

**状态**：已接受（2026-05-09）

**背景**：来源 `/docs/reviews/master_plan/2026-05-09_strategy_calibration_v0.1.md` §3 Q1.6。战略校准 v0.1 §2 Q1.3 拍板"B（独立作者群体被赋能）不作为目标，可遇而不可求"。但 §3 Dream State Mapping 描述的 12 个月愿景包含"工具核心点 2：多世界观兼容性 + 社区开源世界规则模块"——这是 B 的具体形态。§3 Q1.6 拍板调和方案：**(a+) "美好但不主动追求 + 不主动排除"**——行动不主动追求 B（不投正向资源）/ 工程阶段不主动排除 B（保持 two-way doors，不做让 B 永远不可能的硬编码）。本 ADR 把"不主动排除 B"硬约束化，确保后续 L2/L3 规划师设计新模块时遵守。

**决策**：所有 schema / prompt / 代码**不引入硬编码单一世界观假设**。具体禁忌：

- **字段名禁忌**：不带特定 RPG 系统标识。禁：`dnd_class` / `coc_sanity` / `cyberpunk_humanity` / `vampire_blood_pool` 等；允许：`role` / `attribute` / `resource` 等中性命名
- **Prompt 模板禁忌**：system 段不写绑定单一世界的措辞。禁："DND-style fantasy" / "克苏鲁神话风格" / "赛博朋克 2077 设定" 等硬编码；允许：从 ontology 注入具体世界设定（由作者本人定义）
- **战斗系统**：当前不实现，未来设计为 plugin 接口。阶段 4 之前不实现具体战斗；真要实现时通过 plugin 注册机制（参考 ADR-005 编剧理论插件位）
- **Ontology 内容例外**：作者本人创作的具体世界 ontology 内容（如 vellin 角色 / 铁誓驿站地点）可带具体设定，但**框架代码不能假设**任何特定世界

**替代方案及否决理由**：

- 完全不留架构钩子（原版 YAGNI）：未来真要做多世界观时硬编码假设已四处蔓延，重构成本极高
- 主动追求 B（投正向资源做 plugin 注册 / 多世界文档 / 社区贡献流程）：与战略校准 v0.1 §2 Q1.3 "B 不作目标"冲突，且阶段 0–3 增 3–5x 工程量
- 留架构钩子但不立 ADR：缺乏硬约束，后续规划师可能无意识引入世界绑定假设

**后果**：

- 当前架构已天然满足（见战略校准 v0.1 §3 零额外工程量诊断），零工程改动
- 给后续 L2/L3 规划师一条硬约束，避免无意识引入世界绑定
- 保留 Dream State 长期实现可能性（即便不主动追求）
- 与 ADR-004（极简）+ ADR-005（编剧理论作为可替换插件）+ ADR-006（本体 SOT）+ ADR-018（narrative_weight）同源；本 ADR 是 ADR-005 的推广（从"编剧理论可替换"扩展到"世界观可不知"）
- 后续 L2/L3 规划师在审 PR 时多一项检查（"字段名 / prompt / 代码是否硬编码单一世界观"）
- **例外审查机制**：任何"必须硬编码单一世界假设"的提案需要明示理由 + L1 续接会话评审 + 作者明示授权 + ADR 修订
- 已存在的 ADR-022（playtest bots）/ ADR-023（content_dependency_index）/ ADR-024（长对话一致性）/ ADR-025（审阅 UI）/ ADR-026（批量调度）等阶段 2/3 工程 ADR 已天然 world-agnostic，本 ADR 立项不要求修订其他 ADR

---

## ADR-028：引擎与宿主分离原则

**状态**：已接受（2026-05-10）

**背景**：项目讨论中浮现一个具体场景——未来可能存在多种叙事呈现形态（单人桌面游戏、直播互动游戏、VR 体验、群聊文字互动、AI 自玩等）。如果引擎为某一种形态做特化设计，会牺牲其他形态的适配性。

**决策**：Forgewright 引擎核心不实现任何具体的输入输出形态。具体规定：

1. **输入接口**只接受**离散标识符**（option_id、调查目标 ID 等），对输入来源不做任何假设。引擎不知道也不关心 option_id 是来自鼠标点击、键盘输入、直播弹幕、语音转写、群聊指令、AI 模拟玩家、API 调用还是其他任何方式。

2. **输出接口**只产出**结构化的叙事块**（包含本轮叙事文本、新的可选项列表、状态变更摘要、本轮触发的事件标签等），对呈现形态不做任何假设。引擎不知道也不关心叙事块会被渲染成终端文字、Web UI、2D 等距视角、OBS 直播画面、语音合成、AR/VR 显示还是其他任何形态。

3. **宿主程序**（Host Application）是引擎与具体输入输出形态之间的适配层。宿主程序负责采集输入、转换为引擎接受的标识符、调用引擎接口、接收引擎输出、渲染为具体呈现。宿主程序不属于 Forgewright 引擎核心，可以由不同开发者针对不同场景独立开发。

**替代方案及否决理由**：

- **为单人桌面游戏特化设计**：会让未来的直播/VR/语音等形态需要修改引擎核心才能适配，违反开源框架的通用性目标
- **在引擎里实现多种宿主形态作为内置选项**：扩大引擎边界，引入大量与叙事核心无关的代码（直播平台 SDK、VR 渲染、语音处理等），违反 ADR-007（核心是 Runtime 不是 Parser）的精神

**后果**：

- 引擎核心保持极简，专注叙事推进逻辑、状态管理、内容数据
- 第一款游戏需要附带一个"参考宿主程序"作为引擎使用示例（最简形态：Web 或 Electron 文字界面）
- 未来形态扩展（直播、VR 等）通过新写宿主程序实现，不修改引擎核心
- 这条原则与 ADR-002（运行时无 LLM）、ADR-004（运行时与生产期分离）一致——引擎是核心，外围都可以替换

**关联讨论**：本次讨论由"直播互动叙事形态"这一具体场景触发，但原则的应用范围远超直播形态，覆盖所有可能的输入输出适配场景。具体的"直播形态适配"作为 future-extension note 记录，不进 ROADMAP。

---

## ADR-029：技能体系作为项目配置层，不在引擎硬编码

**状态**：已接受（2026-05-11）

**背景**：

讨论中浮现一个核心架构问题：Forgewright 引擎要支持"调查叙事游戏"这一玩法品类，但该品类下存在多种风格各异的技能体系——

- **性格化技能体系**（极乐迪斯科 Disco Elysium 风格）：技能等于"内心声音"，有性格、会主动跳出来评论世界、通过被动注入呈现独白
- **功能化技能体系**（Call of Cthulhu 桌游 + Baldur's Gate 3 风格）：技能等于"行动成功率"，无人格，玩家主动声明使用、用于判定行动成败
- **混合体系**：核心技能性格化（提供内心声音），辅助技能功能化（仅做主动检定）

如果引擎硬编码某一种技能体系（比如把"极乐迪斯科 8 技能"或"CoC 60 技能"写死），就丧失了通用性，违反 ADR-005（编剧理论作为可替换插件，不是核心）的精神。

但这三种体系在"技能在场景中的交互机制"层面其实只有**两种底层模式**——选项级主动检定、节点级被动注入。只要引擎支持这两种底层模式，三种风格都能在其上实现。

**决策**：

Forgewright 引擎核心不预设任何技能列表、不预设任何技能数量、不预设任何骰子规则。引擎层只规范以下三件事：

**第一，引擎核心提供两种技能交互的基础机制**：

1. **选项级主动检定（active_check）**：一个选项（Option）可以挂载一个技能引用 + 难度等级（DC）。玩家选中该选项时引擎触发掷骰，根据成功/失败进入不同的目标节点。

2. **节点级被动注入（passive_injection）**：一个节点（Node）可以挂载若干"被动技能介入"，每个介入声明所用技能 + 难度 + 通过时显示的文本（独白片段）。节点加载时引擎对每个被动介入掷骰，通过的注入文本，未通过的不显示任何内容（玩家不知道错过了什么）。

**第二，技能体系由项目配置层定义**：

每个使用 Forgewright 的游戏项目维护一份独立的技能配置（建议形态为 `/state/ontology/skills.json` 或类似位置，具体路径由工程后续决策）。该配置至少包含：

- 技能列表（id、显示名、归属属性、数值范围）
- 每个技能是否支持被动注入（`supports_passive_injection`）
- 每个技能是否带"性格化声音"（`voice_personality` 字段——若有，描述该技能作为内心声音的人格倾向；若为 null，该技能为纯功能化技能）
- 每个技能的写作风格指南（`voice_style`，供生成器和作者审阅参考）

**第三，骰子规则作为项目配置的一部分**：

引擎核心不绑定 d20 / 2d6 / d100 等任何具体骰子规则。检定机制抽象为参数化形式：`NdM + modifier vs DC`，其中 N、M、modifier 来源（属性 / 技能值 / 装备加值等）由项目配置声明。第一款游戏的具体骰子规则由作者在维度 5（场景列表）落地前决定，作为配置项写入项目。

**替代方案及否决理由**：

- **硬编码极乐迪斯科的 24 技能 + 2d6 系统**：会让做"CoC 风格调查游戏"的开发者必须重新实现一套替代机制，违反通用性目标
- **硬编码 CoC 的 60+ 技能 + d100 系统**：会让做"极乐迪斯科 spiritual successor"的开发者无法获得"性格化技能"作为核心特色
- **预设三种风格作为内置模板让作者选**：增加引擎边界，引入大量与叙事核心无关的内置数据；且无法覆盖未来出现的新风格（比如带 GOAP NPC 行为的混合系统）

**后果**：

- 引擎核心保持精简，只实现两种技能交互的底层机制
- 不同游戏项目可以承载完全不同的技能体系，无需修改引擎
- 同一引擎可支持的玩法谱系扩大：极乐迪斯科风格、CoC 跑团风格、BG3 风格、自定义风格
- 第一款克苏鲁游戏的具体技能体系（数量、性格化/功能化比例、骰子规则）**留到维度 3-5 场景设计阶段决策**——本 ADR 不预设答案
- 写作约定层（作者团队的写作规范）成为重要工程产物——决定"在此项目里如何使用引擎能力"，应作为 STORY_BIBLE.md 的一部分维护

**关联讨论**：

- 与 ADR-005（编剧理论作为可替换插件）一致——技能体系是另一种"可替换插件"
- 与 ADR-028（引擎与宿主分离原则）一致——技能体系是项目配置层，不是引擎核心层
- 触发本 ADR 的讨论起点是"克苏鲁是否应直接照搬极乐迪斯科 8 技能映射"。讨论结论：第一款游戏的具体技能体系延后决定，先在引擎层把抽象层做好

---

## ADR-030：AestheticPreference schema（字段集预留）

**状态**：已接受（2026-05-12）

**背景**：审美层决策 v0.2 §6.4 落地。T-3.10 实测期前作者反思三 gap：作者审美锚点未建立 + 结构化审美偏好档 0 进度 + AI 多维审美能力未验证；v0.2 选项 5 用 3 部经典剧本（Deadlight + Crimson Letters + 极乐迪斯科原版）反向归纳抽象层 + 同步建立锚点（T-3X-0 非工程任务），落地 ADR-030 schema 容器 + prompt hook（T-3X-1 工程任务）。本 ADR **不预定**字段集——字段集**待 T-3X-1 L3 基于 T-3X-0 实证归纳**，避免 v0.1 凭直觉立 schema → 阶段 4 起手必然 v0.2 修订的失败模式。

**决策**：

- **schema 文件**：`/schema/aesthetic_preference.schema.json` 首版 `0.4.0`（与 ADR-016 §schema 版本号策略一致；阶段 3 schema 增量同源）
- **字段集 MVP（v0.1）**：**留空预留** — 待 T-3X-0（作者读 3 部经典 + 填阅读对照表 + 产出 AESTHETIC_PREFERENCES.md v0.1）完成后由 T-3X-1 L3 实证归纳字段集
  - **候选起点**（**T-3X-0 归纳产出可推翻**；不预定）：四维 `temperature` / `pacing` / `character_arc` / `value_judgment` + `reference_works` + `enabled` + `schema_version`
  - **实际字段集**：取决于 T-3X-0 阅读对照表 §5 新发现维度 + §6 总结归纳产出
- **prompt 注入**：`/generator/scene_strategies.py`（skeleton + fill prompt 渲染段）+ 节点级 prompt 加 `aesthetic_preference_context` 注入段（由 T-3X-1 落地）
- **激活时机**：T-3X-1 落地后 T-3.10 实测期 [A]ccept rate gate 真可兑现（基于已结构化 AESTHETIC_PREFERENCES.md + ADR-030 schema 字段）

**替代方案及否决理由**：

- 不立 schema：Gap 1 + Gap 3 推阶段 4 起手期集中爆发（决策档 v0.2 §2 + §4 选项 1 否决）
- 凭直觉立 schema 字段集（v0.1 选项 4）：字段集质量不可控，几乎必然 v0.2 修订（决策档 v0.2 §4.5 优点 1）
- ADR-030 含进阶 schema v0.2+（如新发现维度 / 子字段拆分）：推到阶段 4 基于 50-100 场景实测反馈迭代（决策档 v0.2 §4 选项 5 "阶段 3 不做"段）

**后果**：

- T-3X-1 L3 执行会话基于 T-3X-0 产出 `/docs/AESTHETIC_PREFERENCES.md` v0.1 落地 schema 文件 + prompt hook
- T-3.10 实测期 [A]ccept rate gate（≥ 60% pilot + Wilson 95% CI）真可兑现，**不需降级** STAGE_3_TASKS v1.0 §1 原阈值（决策档 v0.2 §3 + §4 选项 5）
- 字段集仍可能阶段 4 起手期 v0.2 修订（基于 50-100 场景实测反馈），但首版质量已远超凭直觉立项
- 与 ADR-005（编剧理论可替换插件）+ ADR-027（World-Agnostic Principle）+ ADR-028（引擎与宿主分离原则）+ ADR-029（技能体系作为项目配置层）同源——AestheticPreference 偏好档作用于**生成期**（不在引擎运行时强制注入；引擎不感知偏好档），与 ADR-028 引擎与宿主分离不冲突；偏好档不绑定具体世界观（World-Agnostic；ADR-027）；偏好档不绑定具体技能体系（不在 ADR-029 项目配置层影响范围；偏好维度独立于 active_check / passive_injection 基础机制）；偏好档作为"作者审美维度词汇库"不是"编剧理论硬编码"，符合 ADR-005 插件精神

---

## ADR-031：GM 抉择空间结构化方案

**状态**：已接受（2026-05-13）

**背景**：

T-3X-0 阅读伴侣会话（2026-05-13；PR #55 merged）作者本人听完 Crimson Letters（CoC 模组）后识别一个核心架构问题：

**CoC 模组（骨架式作品）是为守秘人（GM）跑团时即兴用，留白大量"GM 抉择空间"；而 Forgewright 引擎要求确定性 JSON 对话图（ADR-002 + ADR-004 极简运行时）——所有"GM 抉择"必须预先压成数据或由确定性代码即时生成。两者之间存在结构鸿沟。**

无论是 (场景一) 改编已有 CoC 模组 还是 (场景二) 原创，核心都是同一个工作流："叙事意图（人脑 / 模组）→ 确定性 JSON 对话图（引擎可执行）"的转换。差别只在输入端（场景一 = 已有材料库；场景二 = 作者已有的半成品：世界观文档 + 章节大纲 + 人物本体 + 场景需求 → 流水线产出 dialogue_graph）；输出端共用同一份 schema——所以抽象层一旦立起来，两种场景都能复用。

T-3X-0 对照表 §5 反向归纳出 7 种 GM 抉择空间形式：(F1) 真凶选择 / (F2) NPC 反应（多套行为按玩家行为切换）/ (F3) 威胁显现节奏 / (F4) 多解决路径 / (F5) 场景扩展 / (F6) 难度调整 / (F7) 即兴（⚠️ 不可完全结构化）。

本 ADR 立"GM 抉择空间结构化方案"——决定如何把 GM 留白结构化为引擎可执行数据。详见草案 [/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1（4 候选方案对比 + 推荐 D 混合 A+B + 6 维评分 + 与 ADR-001~030 关系陈述）。

**决策**：

采用**混合方案 D（A 基础层 + B 增强层）**——5 种 GM 抉择空间形式（F1/F3/F4/F5/F6）完全复用现有 schema 零工程成本；F2 NPC 反应引入 NPC 状态机新抽象；F7 即兴显式不结构化（核心赌注）。

具体覆盖矩阵：

| 形式 | D 覆盖方式 |
|---|---|
| F1 真凶选择 | state path `world.culprit_id` + option 路由 |
| F2 NPC 反应 | **NPC 状态机**（新建 `/schema/npc_state_machine.schema.json` 首版 `0.4.0`）+ character.dramatic_triggers（保留 ADR-019）|
| F3 威胁节奏 | ADR-017 clock + tick_effects（复用）|
| F4 多解决路径 | dialogue_graph end nodes + state_paths_written（复用）|
| F5 场景扩展 | 多 dialogue_graph 拼接 + chapter.acts.included_scenes（复用）|
| F6 难度调整 | state path `world.difficulty` + active_check.dc + NPC 状态机的"警觉度" state |
| F7 即兴 | 不结构化；按 STAGE_3_TASKS §1.7 量化矩阵预生成（每节点 3-6 options 中 1-3 个 diverge 选项导向真正独立子树 + 每场景 1-3 个独立入口路线 + 每场景候选稿 1-3 可设置默认 1）|

**NPC 状态机 schema 字段集（草案；具体由 T-3X-1b 实证落地，本 ADR 不预定）**：

- `character_ref` (string; pattern `^char_[a-z0-9_]{1,64}$`)
- `initial_state` (string)
- `states` (object; additionalProperties = state 定义对象)
  - 每 state: `narration_variants` (array) + `transitions` (array)
  - 每 transition: `event` + `condition`（$ref state_condition）+ `target_state` + `effects`（$ref state_effect）
- `additionalProperties: false`；schema_version const `0.4.0`

**项目级可测目标（首次明文承认；详 DEBATE §10）**：

> Forgewright 工具一期 = 在 STAGE_3_TASKS §1.7 量化矩阵规模下产出作者审阅接受率 ≥ 60% 内容（阶段 3 T-3.10 实测；附 Wilson 95% CI）+ 阶段 4 实测玩家完成主线率 ≥ X%（具体 X 数字推到阶段 4 起手期）。如目标不达标，工具一期定位需重新审视。

4 档回退路径（轻 / 中 / 重 / 致命）+ 实测验证时机详 DEBATE_NOTES.md §10。

**与 ADR-019 dramatic_triggers 协同语义**：

- ADR-019 dramatic_triggers = **触发器**（一次性事件按优先级排序；常态写作期 prompt 提示）
- 本 ADR-031 NPC 状态机 = **持续状态**（多 event 路由 + 持久 state；运行时执行）
- 协同关系：dramatic_triggers 触发后可写入 NPC 状态机的 event 队列；前者是事件发生器，后者是状态持久化器。两者协同，不替代。

**与极简运行时严守**（ADR-002 + ADR-004 + DEBATE §5）：

NPC 状态机运行时执行 = 查表（state × event → next_state + response）+ 应用 state effect + 切换 state；**不调 LLM**。运行时代码增量 ≤ 80 行（DEBATE §5 "500 行"上限充裕）。

**替代方案及否决理由**：

- **纯方案 A（纯枚举 + 元参数化）**：F2 NPC 反应表达力弱——CoC 模组"NPC 多层伪装"在节点级 narration 路由层笨重；全押 F7 核心赌注上失败模式可控性差
- **纯方案 B（7 形式都用 NPC 状态机）**：F3/F4/F5 现有机制已足够；过度工程化；作者审阅负担 +50%；状态空间爆炸风险大
- **纯方案 C（场景模板）**：模板"完整度陷阱"——原创流水线被模板约束；scenario_kind 枚举爆炸风险；模板 → dialogue_graph 转换器是新增大模块；与 ADR-027 World-Agnostic 有张力
- **完全不立 ADR**：T-3X-0 已明示 "GM 抉择空间结构化是 T-3X-1 真正阻塞点"——不立等于把工程债推到 T-3X-1 工程会话现场拍板（违反 CLAUDE.md 规则 8）
- **整合进 ADR-030 v0.2 修订**：ADR-030 = 字段集；本 ADR = 机制契约；范围不重叠；决策颗粒度独立；项目级赌注应独立 ADR 承载

**后果**：

- **新增 1 个 schema 文件**：`/schema/npc_state_machine.schema.json`（首版 const `0.4.0`；与 ADR-030 schema 同 epoch；由 T-3X-1b 落地）
- **新增 engine 模块**：`/engine/npc_state_machine.py`（运行时查表执行器；预估 50-80 行；严守 DEBATE §5 极简；不调 LLM；由 T-3X-1b 落地）
- **generator 增强**：prompt 模板新增 NPC 状态机生成段；skeleton-first 策略增强；generation_trace 新增 npc_state_machine_refs 字段（由 T-3X-1b 落地）
- **validator 扩展**：NPC 状态机闭合性 + 不可达 state + 死锁检测 + 与 dialogue_graph 引用一致性（约 100-130 行；由 T-3X-1b 落地）
- **不动既有 schema**：dialogue_graph / node / option / state_effect / state_condition / character / location / clock / chapter / image_asset / content_dependency_index / aesthetic_preference 全部不动
- **content_dependency_index sidecar 可能扩展**（optional 字段 `npc_state_machine_ids_referenced`；missing-only；由 T-3X-1b 拍板是否落地）
- **STAGE_3_TASKS 修订**：T-3X-1 拆分为 T-3X-1a（ADR-030 字段集）+ T-3X-1b（ADR-031 NPC 状态机）；详 v1.0.2
- **ROADMAP §阶段 3 时长**：5-9 周 → 6-11 周（含 T-3X-1b NPC 状态机引入估时 +1-2 周）
- **DEBATE_NOTES §10 核心赌注段同期立**：本 ADR 立项 + DEBATE §10 同期生效；首次明文承认项目级赌注 + 4 档回退路径

**关联讨论**：

- 与 ADR-001 玩家交互预生成选项式：✓ 强化（F7 即兴正是按 STAGE_3_TASKS §1.7 量化矩阵预生成的实证）
- 与 ADR-002 运行时无 LLM + ADR-004 运行时与生产期分离：✓ 严守（NPC 状态机运行时查表，不调 LLM）
- 与 ADR-005 编剧理论可替换插件：✓ 兼容（本 ADR 是叙事**结构**契约，不是叙事**理论**）
- 与 ADR-006 世界本体 SOT + ADR-008 LLM 不能直接写状态：✓ 严守（NPC 状态机 transition 通过 state effect 改 state path）
- 与 ADR-009 评测分三层 + ADR-021 第二层 2A 拓扑 + 2B 抽样：✓ 增强（NPC 状态机闭合性 / 不可达 / 死锁 = 拓扑层新增校验维度）
- 与 ADR-017 时钟系统：✓ 复用（F3 威胁节奏直接用现有 clock + tick_effects）
- 与 ADR-018 关系层 narrative_weight：✓ 协同（character.relations 与 NPC 状态机正交；前者跨场景，后者场景内）
- 与 ADR-019 角色槽位持久化 + dramatic_triggers：✓ 协同（详上方"协同语义"段）
- 与 ADR-022 playtest bots：✓ 协同（5 persona × 20 paths 实测可包含 NPC 状态机 transition 覆盖率）
- 与 ADR-023 content_dependency_index：✓ 可能扩展 optional 字段
- 与 ADR-024 长对话一致性：✓ 不冲突（NPC 状态机 state 持久化天然有助跨场景一致性；但不替代长对话上下文管理）
- 与 ADR-027 World-Agnostic + ADR-028 引擎与宿主分离 + ADR-029 项目配置层：✓ 严守（schema 字段命名中性；本 ADR 不引入宿主层字段；F6 难度调整复用 active_check + passive_injection）
- 与 ADR-030 AestheticPreference schema 字段集预留：✓ 正交（ADR-030 = 质感词汇库；本 ADR = 结构契约）
- 与 DEBATE §2 plot-centric 骨架 + character-centric 肌肉：✓ NPC 状态机正是 character-centric 肌肉的工程实现
- 与 DEBATE §5 极简运行时：✓ 严守 500 行上限（NPC 状态机查表 ~50-80 行）
- 与 DEBATE §6.1 PbtA 阵营时钟：F3 威胁节奏直接用 clock
- 与 DEBATE §6.5 关系图谱：NPC 状态机 state 持久化到 character.relations 命名空间
- 与 DEBATE §9.1 "谁来写那张图"：本 ADR F1-F7 抽象层是回答"AI 生成时按什么结构生成"的核心；解决"AI 生成几千节点无法保证没有逻辑死锁"的部分
- 与 DEBATE §10 核心赌注（本 PR 同期立）：本 ADR 是核心赌注的工程落地体现；赌注成败决定本 ADR 价值
- 与战略校准 v0.1 北极星 = A 完成度：✓ 工具改进合法性自检通过（F1-F5 用现有机制让 A 立即可写；F2 NPC 状态机避免未来"散落 NPC 反应"债务爆炸）

---

## ADR-034：Schema 主体 AI 生成路线 + 局部对齐主流原语 + 阶段 4 单向导出 shims（v_incremental）

**状态**：已接受（2026-05-18）

**背景**：

2026-05-15 T-3Y L2 综合规划师会话识别一个架构层级风险——Forgewright dialogue_graph schema 凭直觉自设计，未对标业界事实标准（Ink / Articy / Twine / Dialogic），未来集成 / 迁移 / 用户群扩展可能撞兼容性壁。本 ADR 通过 4 工具调研 + 7 维度评分 + 3 distinct 立场候选评估，确定 Forgewright schema 与业界工具生态的关系。

详细调研（4 工具 per-tool 机制清单 + 3 distinct 候选方案 + 7 维度评分 + 5 个 T-3Y 设计争议点作者拍板）见 [/docs/reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md](reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md) v0.2。

**调研核心发现**：

1. **架构层不可调和**：4 工具中没有一个采用 Forgewright "JSON-native（源 = 运行时）"模式。3 个用 DSL 源 + 编译产物（Ink / Twine / Dialogic），1 个用私有编辑期格式 + JSON 导出（Articy）。
2. **T-3Y capability surplus 领先业界**：T-3Y 4 个待答设计问题（scene_metaparams / progressive disclosure / coverage_strategy / scene pre-post）在 4 工具中 0 个原生支持。
3. **真实 v0.3 落后业界点**：3 处（行内条件文本 / 一次性选项标记 / 信息揭露原语）。

**决策**：选 **v_incremental** 路线——Schema 主体 AI 生成路线 + 局部对齐主流原语 + 阶段 4 单向导出 shims，**不立格式中立 IR**。

11 个子决策（D1-D11）：

**D1 · Schema 定位措辞**：`/docs/SCHEMA_v0.3.md`（或后续）开篇正式定位为"AI-generation-aware schema that selectively aligns with industry primitives where they fit; NOT a format-neutral intermediate representation."

**D2 · 接受 T-3Y 草案核心结构**：scene_metaparams / scene_reveals / scene_seeds / scene_static_inputs/outputs / player_known_info / foreground_goal / background_seeds 等字段作为 Forgewright 差异化优势 documented。

**D3 · 立项 ADR-034.1 · `knowledge.*` state path 第 6 命名空间**：直接对标 Ink LIST + Articy Glossary 主流做法。具体语义 + pattern + 与 T-3Y player_known_info 的耦合关系由 **ADR-016 v0.4 修订**承接（本 PR 同步落地）。

**D4 · scene_metaparams 字段形态**：`dict[str, JSON]` 自由形态 + 项目配置层定义字段名 enum（参考 ADR-029 模式）；保 ADR-027 世界观不可知性原则。**作者 2026-05-18 拍板接受**。

**D5 · scene_reveals 多路径语义**：用 ordered flag set 模式。每 trigger_node 触发时 set `knowledge.<reveal_id>.stage_<n>` flag；completion_node 入口检查 `required_stages ⊆ set_stages`。参考 Ink LIST 主流。**作者 2026-05-18 拍板接受**。

**D6 · scene_seeds.coverage_strategy validator**：v0.1 接受弱保证（场景退出时 flag set 检查；无 path enumeration）；强保证推迟到未来 ADR 修订。参考 Articy fallback() 工程节奏。**作者 2026-05-18 拍板接受**。

**D7 · 立 4 个 follow-up ADR 候选清单**：

- ADR-034.1：`knowledge.*` 命名空间落地（**ADR-016 v0.4 修订承接**，本 PR 同步落地）— **高优先级**
- ADR-034.2：`Option.choice_visibility` 字段（once / sticky / disabled enum，对齐 Ink `*`/`+` + Articy seen/unseen）— 中优先级，阶段 3-4
- ADR-034.3：`node.narration` inline conditional text 微语言（对齐 Ink `{cond: A|B}`）— 低优先级，阶段 4 前后
- ADR-034.4：`chapter.ifid` 字段（UUID v4，对齐 Twine StoryData）— 低优先级，阶段 4 开源剥离

**D8 · 阶段 4 开源剥离时加单向导出适配器**：`forgewright-to-twine.py`（输出 .twee）+ `forgewright-to-dialogic.py`（输出 .dtl）。承认 lossy；Ink / Articy 不在 v0.1 适配器范围（架构异构性大、价值低）。

**D9 · ADR-034 本身不修改任何现有 schema 或代码**：仅做立项决定 + 措辞修订；具体 schema 字段变更由 follow-up ADR 各自承接。本 PR 例外只动 ADR-016 v0.4 修订（D3 配套）。

**D10 · 明示停止条件（v_incremental 独有）**：当某次对齐候选识别为"为对齐而对齐"（即业界原语与 Forgewright 哲学冲突或 capability surplus 必然受损）时立即停止；每候选 follow-up ADR 必须明示哲学冲突检查（ADR-004 / 006 / 027 合规审查 + capability surplus 影响评估）。这是 v_incremental 对"滑坡到 v_full_ir"的核心防御。

**D11 · Player-monotonic 原则**（Gap 9 落地，作者 2026-05-18 拍板）：

Schema 层强制——LLM 生成的 state effects 在以下 **monotonic 命名空间**下，只允许 `set` / `inc` / `add`，禁止 `dec` / `remove`：

- `flag.player_*` — 玩家见证 / 行为 flag
- `knowledge.*`（ADR-034.1 新增）— 玩家知识

**不在 monotonic 清单内**（允许双向变化）：

- `player.traits` / `player.bonds`（性格特征 / 羁绊可被剧情移除：背叛 → 羁绊消失；喝酒 → 观察能力下降）
- `relationship.<slug>.*`（关系状态值自然波动，含 trust / fear / affinity 等）
- `faction.<id>.*` / `world.*` / `player.gold` / `player.health` 等

作者手填内容（`generation_trace.source == "human"`）不受此规则约束。详 ADR-016 v0.4 修订。

**5 个 T-3Y 设计争议点 · 作者 2026-05-18 拍板结果**：全部接受 Agent A 倾向（Gap 5 dict 形态 / Gap 6 ordered flag set / Gap 7 v0.1 弱保证 / Gap 9 player-monotonic 原则落地为 D11 / Gap 10 player_known_info 拆分）。

**替代方案及否决理由**：

- **A1 v_full_ir（格式中立 IR + 4 个双向适配器）**：Schema 体积爆炸违反 ADR-004 极简；T-3Y capability surplus 在导出路径必然降级（progressive disclosure → flatten；coverage strategy → 丢弃）；工程量 17-21 周阻塞主线；4 适配器永续 maintenance
- **A2 v_thin_export（不立 IR + 仅 2 单向 shim + 不立 follow-up）**：违反"主流能实现相同效果则推主流"原则——明知 Ink LIST、Twine ifid 等有借鉴价值仍不学；社区采纳门槛过高（中文社区评分 4）；阶段 4 后悔升级成本 12-17 周
- **A3 缓议**：T-3Y 4 个待答设计问题阻塞 T-3Y-1 工程会话；缓议延迟主线
- **A4 完全闭门**：失去阶段 4 工具生态价值；用户群扩张被永久封顶

**后果**：

1. Schema 文档措辞修订（`/docs/SCHEMA_v0.3.md` 或后续；D1）
2. **ADR-016 v0.4 修订**承接 D3 + D11（本 PR 同步落地）
3. T-3Y-1 工程会话按 D4 / D5 / D6 / D11 实现 schema 字段；硬依赖 ADR-016 v0.4 = ADR-034.1
4. 4 个 follow-up ADR（D7）独立排期；不阻塞 ADR-034 合入
5. 阶段 4 开源剥离阶段加 2 个单向导出适配器（D8）
6. validator 扩展支持 6 命名空间 + monotonic 规则（D11 + ADR-016 v0.4 配套）
7. 5 个 T-3Y 设计争议点（Gap 5 / 6 / 7 / 9 / 10）作者拍板已落档（详调研报告 §7.4）；Gap 5/6/7/10 进入 T-3Y-1 工程会话实现

**关联讨论**：

- ADR-004（极简）：D1 + 否决 A1 论证基础
- ADR-006（SOT）：本 ADR 不触动 SOT 哲学
- ADR-007（核心是 Runtime 不是 Parser）：D1 措辞一致
- **ADR-016（state path 命名空间）**：**v0.4 修订承接 D3 + D11**（本 PR 同步）
- ADR-027（世界观不可知）：D4 的核心约束
- ADR-028（引擎与宿主分离）：D8 适配器的归属层（host adapter，非 engine）
- ADR-029（技能体系项目配置层）：D4 的模式参考
- T-3Y 进展报告（[2026-05-15_T-3Y_design_progress.md](reviews/master_plan/2026-05-15_T-3Y_design_progress.md)）：被本 ADR 解锁；T-3Y-1 工程会话承接
- 调研报告（[2026-05-15_ADR-034_schema_ir_research.md](reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md) v0.2）：本 ADR 详细论证 + 4 工具调研 + 7 维度评分 + 5 拍板结果

---

## ADR-035：第一款游戏 L3 宿主程序选型

**状态**：已接受（2026-05-18）

**背景**：

ADR-028（引擎与宿主分离原则；2026-05-10 立）规定 Forgewright 引擎不实现任何具体 IO 形态；宿主是适配层。本 ADR-035 是 ADR-028 的首次具体化——为**第一款游戏**（克苏鲁版极乐迪斯科 spiritual successor）选定一个具体 L3 宿主程序。

调研详细分析见 [/docs/reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md](reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md) v0.4：§2 4 候选能力清单（Godot 4.x / Ren'Py 8.5.x / Dialogic 2.x / 自研）+ §3 3 distinct 立场方案（v_godot_custom / v_renpy / v_godot_dialogic）+ §4 7 维度评分表（21 评分 + 21 理由）+ §5 推荐 + §6 ADR 草案 + §8.4 Godot demo 实测（5 分钟跑通；估时高度可信）。

作者拍板路径（2026-05-15 ~ 2026-05-18）：

1. 2026-05-15 T-3Y L2 会话推荐 v_renpy（主推荐）→ 作者明示偏好 Godot
2. 2026-05-18 v3 提示词 + 3 distinct 方案对比 → 报告 v0.3 主推荐切换 v_godot_custom
3. 2026-05-18 作者明示"保留可扩展性"硬约束（克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定，不是纯 VN）
4. 2026-05-18 Godot demo 5 分钟跑通 → 估时校准 + 可行性验证
5. 2026-05-18 作者明示授权立 ADR-035

**决策**：

第一款游戏 L3 宿主 = **Godot 4.6 + 自写最小 Control nodes**（方案 v_godot_custom；不使用任何 dialogue 插件）。

具体规定：

1. Godot 4.6.2（2026-04-01 发布）或更高版本作为第一款游戏的 L3 宿主程序
2. 新建 `/host/godot_first_game/` 子目录（与 `/engine` 平行；不在 ADR-004 极薄运行时约束内；与 ROADMAP 阶段 4 "游戏内容填充" 同期落地）
3. 5-7 个 GDScript 文件（~500-700 行总）：`main.gd` + `main.tscn` 入口 / `dialogue_player.gd` 节点渲染 + 选项 / `world_state.gd` state 引擎（移植自 `/engine/state/`） / `ontology_resolver.gd` 本体引用解析 / `scene_router.gd` T-3Y scene_branches + scene_metaparams + actual_inputs/outputs / `font_loader.gd` 中文字体打包
4. **不使用 Dialogic 插件**（详否决理由见调研报告 §3.3 + §5.4）；如阶段 4 实测发现需要 dialogue 插件辅助，候选为 Dialogue Manager 4 (nathanhoad) 作 hybrid 形态
5. T-3Y 字段集（scene_branches / scene_metaparams / scene_actual_inputs/outputs / included_node_ids）映射由自写代码实现；与 ADR-034 v_incremental 路线 + ADR-016 v0.4 `knowledge.*` 命名空间协同（具体字段在 T-3Y-1 工程会话落地时统一）
6. Godot 项目内承担：富文本渲染（RichTextLabel + BBCode）/ 选项呈现（VBoxContainer + Button）/ state 内部表达 / 多平台导出（itch.io HTML5 + macOS + Windows binary + 可选 iOS/Android）
7. 第一款游戏的"参考宿主"地位明确——开源框架剥离时（阶段 4 后期），Godot 宿主作为 Forgewright 的**第一个参考适配实现**
8. **可扩展性预留**：自写代码完全可控；未来扩展物品系统 / 技能 UI / DND 风格库存装备槽 / 探索范式时无插件锁定阻碍——这是作者明示"保留可扩展性"硬约束的工程层落地

**`/engine/` 模块命运**：

`/engine/player.py` **(a) + (b) 合并保留**——不删；同时承担两个角色：

- **(a) Reference player 参考实现**：Forgewright JSON 规范的"最小可执行说明书"；v_godot_custom 实施时 GDScript 1:1 翻译参照；开源剥离时第三方宿主的"对照黄金参考"
- **(b) Generator 期 dry-run 工具**：生产期 generator / validator / scene_review_cli / T-3.6 审阅 UI 调用的底层 dry-run 后端；`python -m engine /path/to/scene.json` 不需开 Godot 项目即可玩通

ADR-004 极薄运行时约束（≤ 500 行）继续生效；`/engine/` 仍是 Forgewright 的极薄运行时定义。但它**不是第一款游戏的真实运行时**——真实运行时是 `/host/godot_first_game/`。

**替代方案及否决理由**：

- **v_renpy（Ren'Py 8.5.x）**：22 年成熟 + 工程量最低（demo 实测后 1-2 天估时高度可信 vs Ren'Py 应该更快）+ multi-platform 最强；但 Ren'Py 主打 VN 范式，复杂 UI（DND 风格库存 / 装备槽 / 自由探索）偏弱；作者明示"保留可扩展性"硬约束。**次决策备选退路**:如阶段 4 起手期 v_godot_custom 进度严重卡了（2 周内未达 50%）+ 复杂 UI 短期不需要 → 可切换 v_renpy
- **v_godot_dialogic（Godot 4.6 + Dialogic 2.x 插件 / 原 T-3Y L2 推荐）**：Dialogic 16 月发版停滞（最新 Alpha 19 = 2025-01-12）+ 28 个月全程 Alpha 未发 Beta + 80% 功能 Forgewright 用不到 + 数据格式 `.dtl` 不兼容 + 存档系统重写预告。**明确否决**
- **Godot + Dialogue Manager 4 (nathanhoad)**：可行 hybrid 形态（活跃维护 + stateless branching + 与 Forgewright 哲学同源）；保留作 v_godot_custom 的 plugin-assisted 补充选项（如未来需要 dialogue 插件辅助）
- **保留现有 Python CLI 播放器作唯一运行时**：分发难（朋友 3-5 玩通 + itch.io 发布均做不到）—— 但 `/engine/player.py` 以 (a)+(b) 合并保留作 reference + dry-run 工具角色继续存在
- **自研 Web / Electron**：性价比低于 Godot 自写

**后果**：

- 新建 `/host/godot_first_game/` 子目录（阶段 4 起手期落地）
- `/engine/` 保留 (a)+(b) 双角色；不 deprecated；ADR-004 极薄运行时约束继续生效
- 阶段 4 起手期工程任务（推到阶段 3 → 4 切换会话拆解；本 ADR 不立刻拆 T-x.y）：
  - T-4.1 Godot 项目骨架 + 中文字体打包
  - T-4.2 dialogue_player.gd + world_state.gd + ontology_resolver.gd
  - T-4.3 scene_router.gd（T-3Y 字段集消费；ADR-034 协同）
  - T-4.4 多平台导出 + itch.io HTML5 跑通
- 工程量预算：**1-2 天作者经验估时**（Godot demo 实测 5 分钟跑通验证；详调研报告 §8.4）
- 阶段 4 完成定义 (d) itch.io 发布：Godot HTML5 export 路径
- **ROADMAP / HANDOFF_STAGE_3_TO_4 / STAGE_4_TASKS 修订推到阶段 3 → 4 切换会话**（本 ADR 不动这些 L1 文档）
- 调研物证保留：`/docs/reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md` v0.4 + `/docs/reviews/master_plan/2026-05-18_godot_demo/`

**关联讨论**：

- 与 ADR-002（运行时无 LLM）协同 —— Godot 自写代码不引入 LLM 调用
- 与 ADR-004（运行时与生产期分离）协同 —— L3 宿主属运行时；如未来加 forgewright_to_godot_resource.py 转换器属生产期
- 与 ADR-028（引擎与宿主分离原则）协同 —— **本 ADR 是 ADR-028 的首次具体化**
- 与 ADR-027（World-Agnostic Principle）协同 —— Godot 框架本身世界无关；具体游戏 instance 绑特定世界
- 与 ADR-029（技能体系作为项目配置层）协同 —— Godot 宿主消费项目 skills.json；不内置技能列表
- 与 ADR-031（GM 抉择空间结构化）协同 —— L3 宿主消费"预编排完的"dialogue_graph；NPC 状态机执行由 `/engine/` 层或宿主内嵌的等价代码完成
- 与 **ADR-034（Schema 主体 AI 生成路线；同日 2026-05-18 立）协同** —— v_godot_custom 路径下 Godot 偏好 Resource/JSON 结构；ADR-034 D8 阶段 4 单向导出 shims (forgewright-to-twine / forgewright-to-dialogic) 与本 ADR 共存（Godot 是主宿主；shims 是次级开源剥离物）；scene_router.gd 消费 ADR-016 v0.4 `knowledge.*` 命名空间
- 与 ROADMAP 阶段 4 切换协议协同 —— 北极星 = A 完成度；本 ADR 选 v_godot_custom 是可扩展性 + AI 加速工时双约束下的最优解
- 与 ROADMAP 阶段 4 失败模式警示（"造工具滑回"）的平衡 —— v_godot_custom 自写代码 < 1000 行；不构成"造工具"；自写不依赖插件 = 避免 Dialogic 类的"插件适配滑回"

**编号说明**：

ADR-034 同日（2026-05-18）立 schema IR 路线（v_incremental）；本 ADR 编号 ADR-035 顺延。ADR-032 / 033 编号仍预留给其他平行任务（ADR-032 拟立节点级文本生成抽象总契约；ADR-033 拟立技能体系最小可启动定义）。

---

## ADR-036：Forgewright 采用分模块 license

**状态**：已接受（2026-05-25）

**背景**：

Forgewright 长期目标是开源框架供独立 RPG 开发者复用（CLAUDE.md 项目愿景）；同时支持 dialogue-flow-skill 集成（外部独立仓库 [outsiderrr/dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill) Phase 3 Dual Licensing AGPL v3 + Commercial）。

整体单一 license 不足：

- **整体 AGPL v3**：用户的商业 RPG 游戏 link `/engine` runtime → AGPL 传染 → 与"独立 RPG 开发者可做闭源商业游戏"设计初衷冲突
- **整体 Apache 2.0 / MIT**（ROADMAP 阶段 4 §完成标志原占位）：失去 `/generator` 等开发期工具的 AGPL 防 SaaS 滥用能力

按 CLAUDE.md 架构共识第 4 条「运行时和生产期分离」（含 ADR-002 + ADR-004 落地），分模块 license 可同时满足两类需求。

**决策**：

各模块 license 分配：

| 模块 | License | 角色 |
|---|---|---|
| `/engine` | Apache 2.0 | 运行时 JSON 对话图播放器 |
| `/state` | Apache 2.0 | 状态总线（运行时也用）|
| `/schema` | Apache 2.0 | 数据格式定义 |
| `/generator` | AGPL v3 | AI 生成管线（开发期）|
| `/validator` | AGPL v3 | 校验器（开发期）|
| `/tools` | AGPL v3 | 作家工坊（开发期）|
| `/docs` | CC-BY 4.0 | 项目文档 |
| `/content` | CC-BY-NC 4.0 | 作者私人创作内容（克苏鲁世界）|
| `/game` | Proprietary | 作者本人游戏实例（私有）|

根目录 `/LICENSE` 为 multi-module 总览；`/docs/FAQ-LICENSE.md` 11 题作用户答疑（PR #71 落地）。

**设计原理 — 运行时 vs 生产期分离**：

- **运行时模块**（`/engine` / `/state` / `/schema`）= **Apache 2.0** → 用户的商业游戏 binary 只 link 这些模块 → 可闭源商业销售
- **开发期工具**（`/generator` / `/validator` / `/tools`）= **AGPL v3** → 防止他人 fork 做闭源 AI 服务；不进入玩家 binary，所以用户的商业游戏不被传染
- **文档 / 内容 / 游戏实例**走单独 CC / Proprietary license

**替代方案及否决理由**：

- **整体 AGPL v3**：传染用户游戏；违反"独立 RPG 开发者可做闭源商业游戏"设计初衷；否决
- **整体 Apache 2.0**：失去 `/generator` AGPL 防 SaaS 滥用能力；否决
- **整体 MIT**（ROADMAP 阶段 4 §完成标志原占位）：同 Apache 2.0 缺点；过宽松；否决

**后果**：

- 用户 export 的 game binary 只含 runtime 模块（Apache 2.0）+ content → 可闭源商业销售
- 他人 fork `/generator` 做 SaaS → 被 AGPL v3 强制开源
- dialogue-flow-skill (AGPL v3 / Commercial Dual) 在 `/generator` (AGPL v3) 中集成 → license-compatible（详 dialogue-flow-skill 仓库 LICENSING.md §3.3）
- 同一仓库 mixed license 模式:每模块独立 LICENSE 文件 + 根 `/LICENSE` 总览 + `/docs/FAQ-LICENSE.md` 答疑（已 PR #71 落地）

**关联讨论**：

- 与 **ADR-002**（运行时无 LLM）协同 —— runtime 模块严格独立，license 边界清晰
- 与 **ADR-004**（运行时与生产期分离）协同 —— **本 ADR 是 ADR-004 的 license 层具体化**
- 与 **ADR-027**（World-Agnostic Principle）协同 —— `/content` CC-BY-NC 4.0 防作者私人世界设定被商用 fork
- 与 ROADMAP 阶段 4 §完成标志「开源框架仓库独立 + LICENSE（推荐 MIT）」协同 —— 分模块 license 是开源剥离的法律基础设施；MIT 原占位被本 ADR 取代

**外部依赖**：

- dialogue-flow-skill 仓库（private）：[outsiderrr/dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill) —— Phase 3 Dual Licensing（AGPL v3 + Commercial）；通过 `/generator` (AGPL v3) 集成 license-compatible

**编号说明 + 落地破例**：

ADR-035 后顺延为 ADR-036（ADR-032 / 033 编号仍预留给平行任务）。

**落地破例**（参 brief 2026-05-25 + governance v0.4.1）：

- PR #71（merge commit `9190fff` / 业务 commit `b14ad15`）走 **L1 直签 main 的 fixation 模式**（参 `aeea12e docs(L1): 升格 governance` 先例），跳过标准 ABC 闭环
- 破例理由:
  - 决策在外部讨论中已充分完成（A 阶段隐含完成）
  - 任务低风险（仅文件创建 / 不动业务代码）
  - L3 自己 over-reach 完成 C 阶段（结果 acceptable）
- 不归 STAGE_3_TASKS.md §1.5.4 跳 BC 破例 5 类；属"L1 fixation 直签 main"特殊模式（参 aeea12e 先例）

**Follow-up（不阻塞）**：

- 阶段 4 itch.io 发布前:法律 review LICENSE 文件 + per-module README 标注 license 边界
- 开源剥离时（阶段 4 末）:分模块 license 兼容性最终验证 + per-directory README 加 license header

---

## ADR-037：ABC 阶段层级化 + 设计先于施工（含软地基）

**状态**：已接受（2026-06-08）

**背景**：

现行治理（governance §10）把完整 ABC 三阶段（A=Claude 开发 / B=cross-LLM 独立评审 / C=Claude 吃反馈修 / L2 验收）钉死在每一个工程 L3 任务上。项目真瓶颈是作者审阅带宽（governance §1 第 4 条）；把 ABC 钉在最碎的 L3 层 = 为"没有单独规划的小任务"凑全套仪式，花掉稀缺带宽。需解两件事：(1) 低风险小任务的仪式成本；(2) 在"还会变的地基"上施工的风险。

**如实认知（收益边界，不可夸大）**：

- 攒批省的是**会话管理开销**（少起会话、少重复交代背景），**不省作者审阅的内容量**；改为一次性大块审，整批认知负荷反而更重。
- "错了 AI 返工、不耗作者带宽"**只对普通施工成立**；对"给别人定规矩"的任务不成立——那种错会埋进整批、被一致性掩盖、溜过评审进成品（见决策二软地基 carve-out）。
- "设计先于施工"原本只覆盖**硬地基**（数据格式/schema、L1 文档）；**软地基**（共享函数行为、校验器语义、生成器输出契约等）同样是"别人遵守的规矩"，必须一并前置。

**决策**：

**一、ABC 粒度跟随规划粒度**
- ABC 放在最具体且有规划的层级跑。"算不算有独立规划"按**实质**判定（是否有独立规格需求），**不以"有没有 prompt 文件"为唯一标准**（防止"为攒批而故意不写文件"绕过评审）。
- L2 有规划、底下若干子任务无独立规格需求 → L2 跑一次攒批 ABC（一次 A→B→C→L2 验收）。**B 保留（攒批，非跳过）。**
- L3 有独立规格 → L3 跑 ABC（现状）。
- 粒度由 L2 规划师**规划时一次性决定**，执行中不重判。
- **仅适用工程/代码任务**；内容生成创作会话仍每单元一个新会话。

**二、设计先于施工（含硬地基 + 软地基）**
- **硬地基**（数据格式/schema、共享状态、L1 文档）上提设计/规划层，专门 schema-only ABC 先浇好、按 ADR-015 串行 commit 原则（本 ADR 一般化为常驻规则）串行落定，先于依赖它的施工批。
- **软地基 carve-out**：子任务触及下列任一项，单独先审/先落定（独立 ABC 或 foundation 子批），不得混进攒批——① 改数据格式（schema）；② 改校验器语义；③ 改共享函数行为（public helper 契约）；④ 改生成器输出 / 生成 trace 语义；⑤ 需迁移已有内容。（校准：仅当该契约被批内其它子任务或后续工作依赖时触发；纯内部、无人依赖的小函数不算。）
- **foundation 子批不是 schema-only**：须含保持 main 绿的最小 validator/model/fixture 适配。

**三、安全阀 = 硬闸（不靠会话自觉）**
- 施工批禁止触碰 `/schema`、`/docs/DECISIONS.md`、`/docs/governance.md`、共享 state 契约。
- 施工批 diff 若出现这些路径或等价语义变更 → B 阶段直接 🔴 + 停批 → 上提回设计层 → 专门 ABC 浇好 → 再回来施工。
- 如实成本：安全阀不便宜（全停 + 一个地基 ABC + 上下文切回）；大幅降低"在流动地基上施工"的频率，但**不宣称从根上消除**——残余非零、由本硬闸 + 软地基 carve-out 承接。

**四、攒批护栏**
- (a) 批量上限 ≤ 8 个子任务；软地基 carve-out 任一项触发、或跨多个核心模块、或需迁移老内容 → 不到 8 也拆。
- (b) 回滚单位 = 依赖闭包（不声称"每子任务一个 commit 即可单独 revert"）：批计划写明依赖图；若 T2 依赖 T1，回滚单位 = T1+T2。强依赖链超过 3 个子任务建议拆批。
- (c) 集成评审：B 扇出（并行评审各子任务）时，至少一个评审者看整合后整批 diff。
- (d) 模式标签：每批 / 每 PR 加一行——`mode = batch-ABC / skip-BC / L1-fixation` + B 是否保留 + 授权来源。
- 依赖性不作一刀切约束：普通环环相扣的活可攒批；唯"给别人定规矩"的活按决策二前置。

**五、不变的护城河**：B 阶段 cross-LLM 独立评审（评审者 ≠ 构建者，攒批 ≠ 跳过）；L2 验收 gate；动地基/L1 文档需作者授权（CLAUDE.md 规则 2/9/10）；B 报告 push 到 main 独立 commit。

**六、与既有两种破例模式的区分**（由决策四(d) 模式标签显式标注）：
- **跳 BC**（STAGE_3_TASKS §1.5.4）：A→直接 merge，B 和 C 全丢。用于反向修复 / ergonomic / 验收报告。
- **L1 直签 main fixation**（ADR-036 / `aeea12e` 先例）：作者直接把 L1 文档/license 提交进 main，跳过 ABC。**仅用于已在外部完成决策的 L1 record keeping**，不是普通文档捷径。
- **攒批 ABC**（本 ADR 新增）：一次 A→B→C→L2 验收，**B 保留**。用于一个 L2 计划下若干工程子任务。

**替代方案及否决理由**：

- **替代①：扩"跳 BC"清单代替新增模式**。否决：跳 BC 丢独立评审（护城河）；需评审的活该攒批（保留 B），不需的活跳 BC 已覆盖。
- **替代②：维持 per-L3、把 B/C 做便宜**（B/C prompt 文件化 + L2 验收自动化，governance §12 gap #1 暂缓项）。否决：另一杠杆可并存，但不解决低风险 L3 的仪式成本。
- **替代③：要求"只攒互不依赖的活"**（更严版本）。否决：暗含"作者肉眼早期纠错"，对非程序员作者不成立；返工由 AI 承担。但其合理内核由决策二**软地基 carve-out** 以更窄形态承接（只前置"给别人定规矩"的活，不禁止普通依赖攒批）。

**后果**：

- 变易：攒批低风险工程活少起会话；地基（硬+软）改动集中、前置评审；模式标签使三模式可审计。
- 变难/成本（如实）：作者审阅阅读量不减、整批认知更重；安全阀触发是昂贵中断；治理比"单一 ≤8"略复杂（代价基本是补真洞，非镀金）。
- 回滚：批内有依赖时回滚单位是依赖闭包、非单 commit。
- follow-up：L2 计划的 cross-LLM critique 增一项粒度检查（切得对吗 / ≤8 吗 / 软地基拉出去了吗 / 集成评审安排了吗 / 模式标签对吗）。
- 落地：本 ADR + governance v0.5 + 三处既有文档债修复，走 L1 直签 main fixation 模式 + 作者 2026-06-08 明示授权。

**编号说明**：ADR-036 后顺延为 ADR-037（ADR-032 / 033 编号仍预留给平行任务：节点级文本生成抽象 / 技能体系最小可启动定义）。

**追溯**：vault 提案 2026-06-08（《ABC 阶段层级化 + 设计先于施工》）；本 L1 治理会话；cross-LLM critique（GPT-5.5/Codex）8 finding 已消化（finding 1/2/4/5/7/8 接受并入，3 合并进决策四(a)，6 精简为模式标签，1 的链长上限降为建议）。

---

## 变更历史

- 2026-04-25：作者明确授权新增 ADR-011 / ADR-012 / ADR-013（阶段 1 三条架构决策），属 CLAUDE.md 规则 10 的明示例外。
- 2026-04-30：作者明确授权新增 ADR-014（视觉资产双模生成策略），属 CLAUDE.md 规则 10 的明示例外（阶段 1.5 路径 C 例外）。
- 2026-04-30：作者授权新增 ADR-015（Round 5 综合后第一条已锁结论），属 CLAUDE.md 规则 10 的明示例外。
- 2026-05-03：作者明确授权新增 ADR-016 / 017 / 018 / 019 / 020 / 021（阶段 2 六条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_2_TASKS_v1.0_draft（含 GPT-5.5 critique 校准）。L2 整合规划师会话（claude/musing-fermi-f6bfd3）2026-05-03 L1-L2 校准产物。
- 2026-05-08：作者明确授权新增 ADR-022 / 023 / 024 / 025 / 026（阶段 3 五条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_3_TASKS.md v1.0（含 GPT-5.5 cross-LLM critique 22 finding + Claude round 2 response + 作者 2026-05-08 三议题拍板 F1/F2/F8）。L2 整合规划师会话（claude/sweet-bardeen-863720）2026-05-08 L1-L2 校准产物。
- 2026-05-09：作者明确授权新增 ADR-027（World-Agnostic Principle）+ 修订 ADR-010 v0.2（MVP 场景数量 50–100 → 10–100 弹性区间），属 CLAUDE.md 规则 10 的明示例外。整合自 2026-05-09 战略校准 v0.1（CEO Review 产物，gstack /plan-ceo-review 方法论 only-read 引导）+ §5 三条 L1 升格路径全部落实（含 ROADMAP §阶段 4 切换协议子段）。L1 续接执行会话产出。
- 2026-05-10：作者明确授权新增 ADR-028（引擎与宿主分离原则），属 CLAUDE.md 规则 10 的明示例外。原稿编号 ADR-011 与既有 ADR-011（LLM 提供商）撞号，落地时改为下一个空闲编号 ADR-028。
- 2026-05-11：作者明确授权新增 ADR-029（技能体系作为项目配置层），属 CLAUDE.md 规则 10 的明示例外。落地时按 ADR-028 风格统一删除原稿底部"版本/引入时间"两行；"关联讨论"段"ADR-011 / ADR-028（引擎与宿主分离原则）"占位修正为"ADR-028"（ADR-011 实为 LLM 提供商，非引擎与宿主分离）。
- 2026-05-12：作者明确授权新增 ADR-030（AestheticPreference schema；字段集留空预留，待 T-3X-1 实证归纳）+ 修订 ADR-020 v0.2（X4 闭环；阶段 2/3/4 三阶段口径），属 CLAUDE.md 规则 10 的明示例外。审美层决策于 2026-05-09 签字（v0.2）；ADR-028 + ADR-029 同期由产品线讨论起草并于 2026-05-10/11 push 到 main，占用编号 028/029；本 ADR 顺延为 ADR-030。整合自 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.4 + §6.5。T-3X L2 校准会话起草 L3 fixation PR paste-ready prompt（[/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md](reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md) v0.2.2 修订包含产品线 ADR-028/029 联动校准）→ L1 fixation 执行会话（本 PR）落地。
- 2026-05-13：作者明确授权新增 ADR-031（GM 抉择空间结构化方案；混合方案 D = A 基础层 + B NPC 状态机增强层），属 CLAUDE.md 规则 10 的明示例外。整合自 [/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1（L2 综合规划师产出）+ 作者 2026-05-13 拍板 5 项推荐（5.1 立 ADR-031 / 5.2 T-3X-1 拆 a+b / 5.3 跳 critique / 5.4 DEBATE §10 同期立 / 5.5 ROADMAP 时长 5-9 → 6-11 周）。同期落地：DEBATE_NOTES.md §10 核心赌注段 + STAGE_3_TASKS.md v1.0.2（T-3X-1 拆分）+ ROADMAP §阶段 3 时长校准。后续 T-3X-1a / T-3X-1b L3 工程会话基于本 ADR 启动。
- 2026-05-18：作者明确授权新增 ADR-034（Schema 主体 AI 生成路线 + 局部对齐主流原语 + 阶段 4 单向导出 shims；v_incremental 路线）+ 修订 ADR-016 v0.4（新增第 6 个 state path 命名空间 `knowledge.*` + monotonic 命名空间清单），属 CLAUDE.md 规则 10 的明示例外。整合自 ADR-034 调研报告 [/docs/reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md](reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md) v0.2（4 工具 per-tool 机制清单 + 3 distinct 候选评估 + 7 维度评分 + 5 个 T-3Y 设计争议点作者拍板）+ 作者 2026-05-18 拍板（5 争议点全部接受 Agent A 倾向：Gap 5 dict 形态 / Gap 6 ordered flag set / Gap 7 v0.1 弱保证 / Gap 9 player-monotonic 原则落地为 D11 / Gap 10 player_known_info 拆分）。ADR-034 调研会话（claude/wonderful-proskuriakova-e68be2）产出 + 同会话落地。
- 2026-05-18：作者明确授权新增 ADR-035（第一款游戏 L3 宿主程序选型；方案 v_godot_custom = Godot 4.6 + 自写最小 Control nodes / 不用 Dialogic 插件），属 CLAUDE.md 规则 10 的明示例外。整合自 [/docs/reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md](reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md) v0.4（L3 宿主调研会话产出；含 §2 4 候选能力清单 + §3 3 distinct 方案 + §4 7 维评分表 + §5 推荐 + §6 ADR 草案 + §8.4 Godot demo 实测）+ 作者 2026-05-18 拍板路径（v0.2 主推荐 v_renpy → v0.3 切换 v_godot_custom 基于"保留可扩展性"硬约束 → v0.4 demo 5 分钟跑通验证 → 立项）。ADR-034 同日立项（编号 ADR-032 / 033 仍预留给平行任务：节点级文本生成抽象 / 技能体系最小可启动定义）；本 ADR 编号顺延 ADR-035。同期落地：`/engine/player.py` (a)+(b) 合并保留判定（reference player + dry-run 工具双重角色；不 deprecated）。**ROADMAP / HANDOFF_STAGE_3_TO_4 / STAGE_4_TASKS 修订推到阶段 3 → 4 切换会话**（本 fixation 范围仅含 DECISIONS.md + 调研报告 v0.4 + Godot demo 物证）。ADR-035 调研会话（claude/vigorous-varahamihira-f6f2f6）产出 + 同会话落地。
- 2026-05-25：作者明确授权新增 ADR-036（Forgewright 采用分模块 license：runtime Apache 2.0 / 开发期工具 AGPL v3 / 文档 CC-BY 4.0 / content CC-BY-NC 4.0 / game Proprietary），属 CLAUDE.md 规则 10 的明示例外。设计原理 = ADR-002 + ADR-004 运行时 vs 生产期分离的 license 层具体化。落地走 **L1 直签 main fixation 模式**（参 `aeea12e docs(L1): 升格 governance` 先例），破例跳过标准 ABC 闭环；不归 STAGE_3_TASKS.md §1.5.4 跳 BC 破例 5 类。PR #71 merged 2026-05-25（merge commit `9190fff` / 业务 commit `b14ad15`）实际落地 9 模块 LICENSE 文件 + 根 `/LICENSE` 总览 + `/docs/FAQ-LICENSE.md` 11 题 + README 开发者承诺段。外部依赖：dialogue-flow-skill 仓库（private；[outsiderrr/dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill)）Phase 3 Dual Licensing 通过 `/generator` AGPL v3 集成。本 fixation 会话仅做 governance record keeping（DECISIONS / ROADMAP / CLAUDE.md），不改业务代码。
- 2026-06-08：作者明确授权新增 ADR-037（ABC 阶段层级化 + 设计先于施工（含软地基）），属 CLAUDE.md 规则 10 的明示例外。整合自 vault 提案《ABC 阶段层级化 + 设计先于施工》（2026-06-08）+ 本 L1 治理会话 cross-LLM critique（GPT-5.5/Codex 8 finding）消化。同期 governance v0.4.2 → v0.5（§1/§2/§3 + 新增 §10.6/§10.7 + §11 兼容注）+ 三处既有文档债修复（STAGE_3_TASKS §1.5.4 加"攒批≠跳BC"注 + §1.5.1 C 阶段措辞 / prompts README C 阶段措辞 / REVIEW_PROMPT_CODE_GPT.md "不要 commit/push" vs "报告 push 到 main"自相矛盾理顺）。落地走 L1 直签 main fixation 模式（作者明示授权 + 本 PR merge）。

## 版本

本文件版本：v0.1
最后更新：[作者填写日期]