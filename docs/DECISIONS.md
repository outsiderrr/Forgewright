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
- validator 扩展（T-2.7）必须支持本体引用闭合 + state path 命名空间合法性 + state_path_slug 反查
- prompt 模板（T-2.5）必须把 character_features / dramatic_triggers / Chapter/Act / 系统时间双轨纳入 context

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

- generation_trace 字段表追加 slot_assignments 子字段（dialogue_graph + node `schema_version` 不动）
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

## 变更历史

- 2026-04-25：作者明确授权新增 ADR-011 / ADR-012 / ADR-013（阶段 1 三条架构决策），属 CLAUDE.md 规则 10 的明示例外。
- 2026-04-30：作者明确授权新增 ADR-014（视觉资产双模生成策略），属 CLAUDE.md 规则 10 的明示例外（阶段 1.5 路径 C 例外）。
- 2026-04-30：作者授权新增 ADR-015（Round 5 综合后第一条已锁结论），属 CLAUDE.md 规则 10 的明示例外。
- 2026-05-03：作者明确授权新增 ADR-016 / 017 / 018 / 019 / 020 / 021（阶段 2 六条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_2_TASKS_v1.0_draft（含 GPT-5.5 critique 校准）。L2 整合规划师会话（claude/musing-fermi-f6bfd3）2026-05-03 L1-L2 校准产物。

## 版本

本文件版本：v0.1
最后更新：[作者填写日期]