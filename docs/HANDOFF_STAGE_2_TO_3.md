# HANDOFF_STAGE_2_TO_3.md

> 阶段 2 规划师 + 验收会话 → 阶段 3 规划师会话的交接档（草稿）。
> 让下一个规划师不继承阶段 2 上下文也能快速上手。
>
> **本文件是阶段 2 → 3 交接草稿**；阶段 3 L2 规划师启动后由其自定 STAGE_3_TASKS_draft 并按需修订本文。

**日期**：2026-05-07 · **版本**：v0.1 · **产出方**：阶段 2 验收会话（T-2.13）

---

## 项目是什么（三句话；与 HANDOFF_STAGE_1_TO_2 一致）

Forgewright 是一条 AI 辅助的分支叙事 RPG 内容生产流水线。短期用于作者本人一款类 BG3 的中小型 RPG；长期剥离出通用框架开源。核心价值不在游戏运行时，在内容生产期的工具链。

阶段 2 已落地"场景级 AI 生成 + 图校验"——一次生成一棵完整对话树，并保证图拓扑合法 + 抽样可达性 + 有界符号执行下未发现反例。**阶段 3 是完整内容生产流水线 + 审阅工具——作者每天稳定产出几千字质量达标的剧情内容**。

## 玩家交互模式铁律（别重开讨论；与阶段 0/1/1.5/2 一致）

预生成选项式——玩家点 3–6 个预生成选项。**运行时无 LLM 调用**。任何"反欺诈" / "实时生成" / "流式对齐"提议本项目都不适用，见 DEBATE_NOTES §1 已彻底排除。

## 阶段 2 做了什么（别重建）

13 个主任务（T-2.0 ~ T-2.12 + T-2.13 本任务）+ 9 项 R2.X follow-up（其中 7 项已 merged，2 项遗留）。主线：

- **`/generator/generate_scene.py`** 主函数（T-2.6）—— skeleton-first 策略，单次调用生成完整对话树
- **`/validator/dialogue_validator.py`** 机械预检器（T-2.4，R8 落地，ADR-020 §5 M1–M7 七项检查）
- **`/validator/graph_validation/` + `/validator/sampling/`** 图论校验双拆（T-2.7，ADR-021 §2A 拓扑 + §2B 抽样 N=100 + 有界符号执行）
- **`/generator/scene_strategies.py` + `/generator/prompts/scene/`** scene-level prompts + skeleton-first 策略（T-2.5）
- **`/generator/scene_experiment.py` + `/generator/scene_review_cli.py` + `/generator/scene_metrics.py` + `/generator/scene_ai_judge.py`** 四 CLI 模块（T-2.8）
- **`/generator/protocols/STAGE_2_BASELINE_PROTOCOL.md`** baseline 协议 v1（T-2.9，ADR-020 落地）
- **`/generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md`** 场景级 21 维（节点级）+ 10 维（场景级）AI 判官 prompt（T-2.9）
- **`/schema/`** 本体 + clock + chapter + narrative_weight + dramatic_triggers schema（T-2.2）
- **`/generator/providers/`** PoloAIProvider（R2.7）+ 共享 sanitizer（R2.8）+ 共享 retry policy（R2.10b）+ ProviderError 仪表化（R2.9）
- **配套 ADR**：016（state path 命名空间 + state_path_slug）/ 017（时钟）/ 018（关系层 + 角色槽位持久化）/ 019（叙事权重 + 戏剧触发）/ 020（baseline 协议）/ 021（ADR-009 第二层方法论拆 2A/2B）
- **跨 LLM 评审**：13 个主任务全部 ABC 闭环 + 13 个 R2.X follow-up / baseline_NNN finding PR 走作者明示授权跳 BC 破例模式
- **验收**：`/docs/STAGE_2_ACCEPTANCE.md`（通过；baseline_011 N=15 gross_pass_rate **100%**）

## 阶段 2 收尾时的架构遗留（R2-*）

来自 `/docs/STAGE_2_ACCEPTANCE.md` §4。**阶段 3 规划师需要把以下显式纳入阶段 3 任务清单**：

| 编号 | 内容 | 阶段 3 该不该处理 |
|---|---|---|
| **R2-5** | scene_ai_judge dimensions dict 全空（"(no dimensions returned)"）—— prompt 模板与 dimensions schema 不一致 | **是**：阶段 3 起手期与 AI 判官 vs 作者 kappa 校准合并做 |
| **R2-10c** | scene_experiment 预飞 balance/health probe（探测 PoloAI 余额 + 上游可用性）| **是**：阶段 3 工坊化的标准 ergonomic 改进 |
| **R2-iter-逃逸** | iter07 / iter09 / iter11 模型 json 模式逃逸单点（advisory accept）| **是**：阶段 3 起手 prompt 调优 |
| **R2-cyclic** | R2.10a `_schema_sanitizer` 循环替换 `{}` 是 lossy 破例（baseline_011 触发 654 次 0 阻塞）| 视需要：阶段 3 LLM 生成质量明显回归再做 |
| **R2-1** | GeminiProvider 差异化异常体系（DefaultGenerationError 之外细分）| 视需要：R2.9 仪表化已覆盖诊断需求 |
| **X4** | ADR-020 v0.2 修订（"审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy" 写进 ADR）| 否（L1 文档级元任务，作者另起会话）|

**Stage 3 起手清理 PATCH 强烈建议含**：R2-5（判官 dimensions）+ R2-iter-逃逸（prompt 调优）+ R2-10c（预飞 probe）。

## 阶段 3 启动条件（摘自 ROADMAP §阶段 3）

**目标函数**：作者能每天稳定产出几千字质量达标的剧情内容。

**完成标志**：
- 批量生成调度器（异步跑多场景）
- 审阅界面（Web 或桌面，左内容右批准/打回）
- 一致性维护（本体变更时标记需重审的已生成内容）
- 版本控制集成（每次修改记版本）
- **作者实际跑一周，完成至少 10 个场景的生成 + 审阅 + 入库**

**重点工作**：
- Chapter / Act 层级结构设计 —— 支持分层叙事的容器结构（位于世界本体层而非对话图层；阶段 2 已 schema 落地，阶段 3 落地容器结构生成）

**完成标志强化项（Round 5 综合后）**：
- **C2**：ADR-009 第三层 playtest bots 写入完成标志 —— 至少 N 个 bot persona / 每场景 M 条模拟路径 / 输出 worst-10% 场景清单；否则"完整内容生产流水线"名不副实
- **C6**：内容依赖索引（`content_dependency_index` sidecar）—— 记录每个生成产物读过哪些 ontology ids / state paths / prompt template hash / visual asset ids；本体变更时定向反向 propagate 而非全量重审
- **U-CL-1**：完成标志加质量门槛指标 —— 在 ≥ X% 单次接受率下作者每周稳定吞吐 Y 场景
- **U-CL-5**：长对话一致性缓解策略 ADR / 任务 —— DEBATE_NOTES §9.2 列为未解问题但路线图当前无任何缓解任务；记忆流机制（Generative Agents 风格）或上下文管理策略需要显式规划
- **U-GPT-7**：审阅 UI 第一版含图视图 —— graph/mermaid/dot 视图 + 路径列表 + validator issues 面板 + visual asset thumbnail；避免后期重做审阅心智模型

## 阶段 3 审美层 review 激活（重要）

**feedback memory 锁定**：阶段 2 期间跳过 `scene_review_cli` 作者 [A]/[R]/[S] 流程；用 `gross_pass_rate ≥ 70%` 作完成判定 logic-layer proxy；**审美层评估激活在阶段 3** —— 作者那时有具体剧本上下文 + 角色弧线锚点。

**对阶段 3 规划师的影响**：
- 阶段 3 起手必读 `~/.claude/projects/-Users-outsider-Desktop-Forgewright/memory/feedback_acceptance_review_deferred_to_stage_4.md`
- `scene_review_cli` 工具链已落地（T-2.8），阶段 3 复活使用即可（无需重建）
- AI 判官 advisory（每场景 21 维节点 + 10 维场景）已落地（T-2.9）但 dimensions 全空 bug（R2-5）需先修
- 阶段 3 完成标志 U-CL-1 真实接受率（含审美层）阈值由阶段 3 规划师拍板

## ⚠️ Schema 扩展警示（CLAUDE.md 规则 2 + 9 的特殊情况）

**阶段 3 可能动 Schema 的两处**：

1. **Chapter / Act 容器层落地** —— 阶段 2 已 schema 占位（T-2.2 含 chapter）；阶段 3 可能扩展容器结构生成对应 schema 字段
2. **content_dependency_index sidecar**（C6）—— 新建 schema 文件记录依赖关系；推荐独立 schema 不嵌进 dialogue_graph

**未授权改动**（即便阶段 3 内）：
- DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 任何已有字段（阶段 0/2 锁定的核心 schema）
- ADR-016 ~ 021（阶段 2 锁定的架构决策）
- CLAUDE.md / DECISIONS.md（除新增 ADR 外）

**Schema 升级走 MINOR bump**（schema_version 0.2.x → 0.3.0）若有任何字段新增。

## 阶段 3 规划粗想（给下一个规划师做参考，不照抄）

下一个规划师应按阶段 0/1/2 规划师的开场流程：**先读全部元文档 → 给作者理解确认 → 等作者校准 → 再规划**。下面是阶段 2 验收会话对阶段 3 任务拆分的**粗预判**，**未与作者校准过**：

### 关键架构决策（需作者拍板）

1. **批量调度器策略**：
   - **A. 串行**（一次跑一场景）：简单；但单场景 ~5–15 分钟意味着 10 场景 = 1–2.5 小时，作者无法离开
   - **B. 异步并发**（多场景并行）：吞吐高；但需协调 PoloAI 速率限制 + 共享 ontology 写入并发
   - **粗推荐**：B + 速率限制器 + per-iter cost log 同步即可

2. **审阅 UI 形态**：
   - **A. CLI 升级版**（基于 T-2.8 scene_review_cli 加图视图）：投资低；但 graph 可视化效果差
   - **B. Web 单页**（local file server + svelte/vue）：投资高；但 graph 可视化好
   - **C. 桌面应用**（electron / tauri）：投资最高
   - **粗推荐**：B（投入产出比；阶段 3 是产出阶段，审阅效率是关键瓶颈）

3. **content_dependency_index 形态**（C6）：
   - 候选 A：每个生成产物 sidecar `<scene>.deps.json`
   - 候选 B：全局索引 `/content/index/dependencies.json` 一份写
   - 候选 C：SQLite 数据库（read-heavy 场景的标准选择）
   - 这是 C6 落地的核心议题，阶段 3 规划师应给作者列利弊

4. **playtest bots 形态**（C2）：
   - 候选 A：bot persona 写死在 fixture（简单 / 不灵活）
   - 候选 B：bot persona 用 LLM 生成（递归依赖；规模化好）
   - 阶段 3 规划师须确认范围 + 与 R2-5 AI 判官 dimensions 校准合并

### 任务拆分粗预判（阶段 3 估计 8–12 任务）

- T-3.0：起手清理 PATCH（R2-5 dimensions + R2-iter-逃逸 + R2-10c 预飞 probe）
- T-3.1：批量调度器（异步并发 + 速率限制 + 共享 ontology 写入并发安全）
- T-3.2：Chapter / Act 容器层落地
- T-3.3：内容依赖索引 sidecar（C6）
- T-3.4：审阅 UI 第一版（U-GPT-7；含 graph 视图 + 路径列表 + validator issues 面板）
- T-3.5：playtest bots（C2）
- T-3.6：长对话一致性缓解（U-CL-5；ADR + 落地）
- T-3.7：完成标志质量门槛（U-CL-1；阈值拍板）
- T-3.8：版本控制集成（每次修改记版本）
- T-3.9：阶段 3 实证（作者实际跑一周，完成 ≥ 10 场景）
- T-3.10：阶段 3 验收报告

## 与作者协作的风格备忘（继承自阶段 0/1/1.5/2）

- **作者不会编程**。所有代码产出通过执行会话完成；规划师的输出是任务拆解 + 提示词，不写代码
- 作者偏好快速决策：要推荐值让他拍板；不喜欢"每项都分析一遍"——给利弊 + 推荐，由他"全同意"或逐条改
- 作者打字偶尔有错字（GitHub 账号 `outsiderrr`）——以环境探测值为准
- 阶段 2 收官期作者偏好"R2.X follow-up 跳 BC 破例模式"—— A 阶段实测发现 bug 主动修 + 拆 commit + L2 quick check + merge；阶段 3 工程债低于阶段 2，跳 BC 破例频率应自然下降；规划师默认仍按完整 ABC 起草任务
- 作者在阶段 2 收官期形成的 L2 整合规划师 + 阶段验收会话角色（参 memory `feedback_dont_refactor_settled_workflow.md`）—— 阶段 3 同款角色可继承
- 作者明确 **不愿追求"最后 10% 完美主义"**；阶段 2 R2-5 / R2-cyclic / R2-iter-逃逸 等单点遗留留给阶段 3，不必死磕

## 必读顺序（新规划师首轮阅读）

1. `/CLAUDE.md`
2. `/docs/ROADMAP.md`（特别是阶段 3 段 + 阶段 2 完成标志做对比）
3. `/docs/DECISIONS.md`（**全部 21 条**——尤其 ADR-009 / 014 / 015 / 016 / 017 / 018 / 019 / 020 / 021）
4. `/docs/DEBATE_NOTES.md`（至少 §1、§2、§5、§9）
5. `/docs/SCHEMA_v0.md` + `/docs/SCHEMA_v0.2.md` + `/docs/SCHEMA_v0.3.md`（阶段 0/1.5/2 schema 增量；v0.3 = stage 2 ontology 模块）
6. `/docs/STAGE_2_ACCEPTANCE.md`（特别 §4 R2-* 哪些归属阶段 3）
7. `/docs/STAGE_2_TASKS.md`（执行会话提示词的产出格式参考；阶段 2 历史完整记录）
8. `/generator/protocols/STAGE_2_BASELINE_PROTOCOL.md`（baseline 协议口径基准；阶段 3 baseline 形态可能要拆 batch + audit）
9. `/generator/experiments/20260506T113419Z_baseline_011/`（达标 batch 产物——审阅 UI 设计参考）
10. `/validator/` + `/generator/` 现有模块（阶段 2 实质交付物）
11. `~/.claude/projects/-Users-outsider-Desktop-Forgewright/memory/` 目录（特别 feedback memory 系列）
12. 本文件（HANDOFF_STAGE_2_TO_3.md）

## 工作模式（阶段 0/1/2 已跑通，不要改）

- **规划师会话**：产出任务拆分 + 提示词；不写代码；回答架构歧义时给利弊 + 推荐不替作者决定
- **执行会话**：只做单一任务；硬性限定在自己的模块目录；完成后 commit + push（末尾附 Co-Authored-By）
- **并行多会话**：模块互不重叠可并行；push 时 rebase 兜底
- **L2 整合规划师 + 阶段验收角色**：阶段 2 收官期实证有效；阶段 3 可继承（特别是 R 项 follow-up dispatch + baseline 跑批 PR L2 quick check + merge 节奏）
- **Schema 级变更**：阶段 3 可能动 Schema（Chapter/Act 容器 / content_dependency_index），需作者明确授权；变更走 MINOR bump

## 阶段 2 残留的工作流改进建议（阶段 3 规划师可采纳）

- **R2.X follow-up + baseline_NNN finding 跳 BC 破例模式**：阶段 2 收官期形成的合规简化路径，阶段 3 R 项处理可继承；但 L3 主任务（T-3.X）默认仍走完整 ABC
- **L2 整合规划师角色**：阶段 2 收官期有效—— A 阶段会话产出 → L2 quick check + paste-ready prompt 出题 + 作者授权 merge；上下文经济好（不重复加载 main HEAD / R 项序列等）
- **Provider 仪表化习惯**：R2.9 实战验证有效—— ProviderError.from_exception + scene_results.jsonl 含 failure_metadata；阶段 3 多场景并行调度时同款仪表化是必要的
- **抽公共模块的克制粒度**：R2.8 共享 sanitizer + R2.10b 共享 retry policy（但 predicate 各自）—— 阶段 3 多 provider 工作流维持同款抽取风格

## 跨阶段串行 / 并行预判

阶段 3 与之前阶段的关系：
- **阶段 1.5（视觉资产）**：阶段 1.5 部分通过；R1.5-1 ~ 6 遗留——阶段 3 实测内容期会触发是否需要补 14 立绘 + 1 background（取决于阶段 3 实证场景集是否含未生图角色 / 场景）
- **阶段 2（场景生成）**：阶段 2 通过；阶段 3 复用 generate_scene + validator + 仪表化全套
- **阶段 4（开源剥离 + 商业化）**：阶段 4 启动条件含阶段 3 完成 + 至少 10 场景实测产出；阶段 3 收尾后才考虑

阶段 3 规划层与之前阶段无串行卡口（阶段 1.5 / 2 已签字；ADR-015 sequencing 已锁）。

## 总盘子预判

| 项 | 估算 |
|---|---|
| 阶段 3 LLM 成本（批量调度器跑 ~50 场景作 walking skeleton + 审阅过程）| $25–$60 |
| 阶段 3 工具链开发（多次 ABC 任务 token 消耗）| 不计；按月度作者承担 |
| 阶段 3 总盘子 | 约 $25–$60 LLM + dev token |

**阶段 4 内容填充预算单独估**：50–100 场景 ≈ $30–$80 LLM 生成 + 审阅成本。

---

## 跨阶段提醒（X 级长尾）

| 编号 | 内容 | 处理时机 |
|---|---|---|
| **X4** | ADR-020 v0.2 修订（审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy） | 阶段 3 起手期 L1 元任务；作者另起会话立 |
| **X1 衍生** | ROADMAP §阶段 2 「单次生成人工可接受率 ≥ 70%」字面措辞 与 feedback memory（推迟到阶段 4）冲突 | 同 X4，作者另起会话同步修订 |
| **ADR-011 / 013** | "google.genai 是唯一 Gemini 入口"假设随 R2.7 PoloAIProvider 接入实质破裂；待修订 | 阶段 3 / 4 视需要立 X 级元任务 |

---

## 版本

本文件版本：v0.1（阶段 2 → 3 交接草稿）
最后更新：2026-05-07
