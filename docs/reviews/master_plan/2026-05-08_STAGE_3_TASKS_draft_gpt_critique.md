# STAGE_3_TASKS draft v0.1 — GPT-5.5 cross-LLM critique

**日期**：2026-05-08  
**评审对象**：`/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md`（用户指定路径；实际在 main workspace 缺失，本次读取 `.claude/worktrees/sweet-bardeen-863720/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md`）  
**评审者**：Codex GPT-5.5  
**必读策略**：精简版（8 预读 + by-need 增补；上一会话默认完整版触发 auto-compact 失败）

---

## 1. 总体判断（一段话）

v0.1 的前向方向总体健康：ROADMAP 阶段 3 五个完成标志、Round 5 五个强化项、阶段 2 R 项遗留都被纳入了任务图，且 13 槽位规模大体可控。但这份草稿还不宜直接整合为 v1.0：当前最大风险不是“缺任务”，而是若干 completion gate 与执行 prompt 的可证伪性不足，外加真实 repo 结构和任务边界不匹配。红线集中在 4 类：路径/依赖会让执行会话读不到真相源，`prior_scene_summaries` 与 N=3 并发存在隐性冲突，`content_dependency_index` 的“读过什么”目前不可可靠写出，review UI / tools 包依赖在 prompt 边界里无法落地。建议先修 🔴，再进 v1.0；修完后阶段 3 可以启动。

## 2. Finding 清单（按严重度排序）

| # | 严重度 | 议题 | 引用位置（行号 / 段落） | 问题描述 | 建议 |
|---|---|---|---|---|---|
| F1 | 🔴 | v0.1 草稿路径与 prompt 自引用失效 | v0.1 L3, L27, L419, L513, L620 等；本次 main workspace `docs/reviews/master_plan/` 未发现该文件 | 草稿宣称位于 `/docs/reviews/master_plan/2026-05-07...`，13 个 prompt 也让执行会话读这个路径；但实际文件只在 `.claude/worktrees/...` 下。若 v1.0 不改，执行会话会读不到源文件，或者读到历史缺失路径。 | v1.0 整合时统一把所有 “读 v0.1 草稿” 改为读 `/docs/STAGE_3_TASKS.md`；如需保留审计稿，先把 v0.1 归档到 main 或在 §0 明示实际审计路径。 |
| F2 | 🔴 | review_ui / tools 包落地边界与 repo 结构冲突 | v0.1 L1060-L1071；`pyproject.toml` L10-L18, L25-L39 | T-3.6 要新增 FastAPI review UI，但 prompt 只允许 `/tools/review_ui/`，禁止改其他路径；当前 repo 没有 `tools/` 包，`pyproject.toml` 也没有 `fastapi`、`uvicorn`、`tools` package。执行会话若遵守边界，代码不可安装/测试。T-3.7 同样会首次正式化 `/tools`。 | T-3.6 或一个独立 T-3.tools-bootstrap 明确允许修改 `pyproject.toml`，加入 `tools` package 与 FastAPI 依赖；若坚持零依赖，则把 ADR-025 改成 stdlib `http.server` + static API 文件读取，不写 FastAPI。 |
| F3 | 🔴 | T-3.3 修改了错误的 context 类型 | v0.1 L748-L753, L767-L781；现有 `generator/context_assembler.py` L226-L259；`generator/generate_scene.py` L49, L533-L541 | prompt 要求给 `GraphContext` 加 `prior_scene_summaries`，但场景级 `generate_scene` 使用的是 `SceneGraphContext`，`GraphContext` 是节点级 B+ context。按 prompt 执行很可能只改到节点级路径，阶段 3 的 scene-level 生成根本拿不到 prior summaries。 | T-3.3 改为：`SceneGraphContext` 增字段，`_build_scene_context` 接收 summaries，`scene_strategies` 的 skeleton/fill scene prompt 都渲染该段；节点级 `GraphContext` 是否同步加字段作为次要兼容项。 |
| F4 | 🔴 | N=3 并发与跨场景记忆顺序冲突 | v0.1 L118, L220-L223, L981-L985, L1462-L1470 | D4 依赖 “前置场景 summary 注入”，但 D6/T-3.5 把 batch 视为独立 SceneSpec 并发队列。跨 chapter 的 10-15 场景若存在剧情依赖，N=3 并发会在前置 summary 尚未产生时生成后续场景，导致 C 起步长对话一致性失效。 | SceneSpec 增 `depends_on_scene_ids` / `prior_summary_paths` / `sequence_group`；batch_scheduler 做拓扑分层，同层并发，不同层串行。T-3.10 场景集也要声明依赖图，不能只是一组 flat specs。 |
| F5 | 🔴 | `content_dependency_index` 的 “实际读依赖” 不可从输出反推 | v0.1 L186-L208, L1002-L1007 | sidecar 要记录 `ontology_ids_read` / `state_paths_read`，但 T-3.5 的写法是从 scene + ontology 反查。生成时 LLM 看到的是整个 context，不是最终 scene 中出现的字段；从结果反推会漏掉“读过但未写出”的关系、dramatic trigger、location/clock，也可能误报未实际使用的全局数据。C6 的反向 propagate 可靠性会被掏空。 | 在 context assembly 阶段显式产出 `GenerationDependencyTrace`：注入了哪些 character/location/clock/relation/state/prompt 文件就记哪些。先允许 conservative over-approx，宁可误报 stale；不要把 “最终 scene 出现了什么” 当 “生成读过什么”。 |
| F6 | 🔴 | Chapter assignment 与 dep_index 写入顺序会产生 stale `chapter_id` | v0.1 L1005-L1008, L1387-L1390 | T-3.5 写 deps 时从 ontology 查 scene 属于哪个 chapter；T-3.9 又在 deps 写完后才把 scene append 到 chapter.acts。结果 `<scene>.deps.json` 的 `chapter_id` / `act_id` 很容易是 null 或旧值，后续 stale 查询和 review UI chapter 分组都不可信。 | 将 chapter assignment 放到 dep_index 写入前，或 T-3.9 hook 完成后强制重写 deps sidecar。更稳的依赖是 T-3.9 的 assignment helper 先作为库交付，T-3.5 生成流程按 “write scene → assign chapter → write deps → record version” 顺序接入。 |
| F7 | 🔴 | version control gate 与实现方案不一致 | v0.1 L60, L1247-L1250, L1276-L1322 | §1 表写 “每次修改记 git commit + scene 内 version metadata 字段”，T-3.8 实际改为 `<scene>.version.json` sidecar，且明确不自动 git commit、手动编辑后靠作者跑 CLI 追溯。这个方案是审计 metadata，不保证 ROADMAP 的“每次修改记版本”。 | 修改完成标志措辞为 “每个入库 scene 必须有 version sidecar，且 T-3.10 验收审计无缺失”；review_ui 保存 [A]/[R]/[S] 后提示未记录 version 的手动编辑。若坚持“scene 内字段”，另起 schema 决策；否则不要在 §1 写 scene 内。 |
| F8 | 🔴 | D3 完成阈值会允许阶段 2 逻辑层显著回归 | v0.1 L62-L64, L117, L1491；STAGE_2_ACCEPTANCE L64-L75 | 阶段 2 baseline_011 已有 100% gross_pass；阶段 3 若把完成门槛降到 80%，允许 20% schema/topology/mechanical/sampling 失败还过关。另一方面 [A] ≥ 60% 在 10 场景样本上只是 6/10，统计波动很大，不足以声明“稳定吞吐”。 | 拆成两层：logic regression gate 建议 gross_pass ≥ 95% 或 “0 untriaged critical validator failures”；审美层 [A] ≥ 60% 作为 pilot 指标，N<15 时必须报告 Wilson/置信区间，不用单点百分比伪装稳定。 |
| F9 | 🔴 | playtest cost / wall-clock 估算低估数量级 | v0.1 L887-L897, L910-L912, L1470 | v0.1 按 “100 paths/scene × $0.02/path = $2/scene” 估算，但每条 path 不是一次 LLM 调用：每个决策节点都要 persona 选项调用，之后还要 judge 调用。一个 5 步 path 就可能是 4-5 次选择 + 1 次 judge，5 场景完整 playtest 可能从 500 调用变成数千调用。 | ADR-022 先写校准步骤：1 scene × 1 persona × 5 paths 小跑，实测 avg calls/path、tokens/path、seconds/path，再锁 5×20。T-3.4 必须有 `--max-cost-usd`、`--max-calls`、`--max-wall-clock-min` 三重 guard。 |
| F10 | 🔴 | `critical_issue` gate 缺严重度 rubric | v0.1 L173-L174, L896-L898, L1491 | 完成标志要求 worst-10% “0 critical issue 或全部修复”，但 critical 的定义完全交给 LLM-as-judge 自然语言。没有 taxonomy 时，模型可能把风格瑕疵标 critical，也可能漏掉 lore/state 重大矛盾；完成判定不可复核。 | ADR-022 加 severity taxonomy：critical = validator 漏掉的非法路径、状态因果矛盾、角色/本体直接冲突、玩家结果透明度严重误导等；major/minor 分开。critical 必须作者确认，不能只靠 LLM 字段。 |
| F11 | 🟡 | T-3.0 跳 BC 适用性前后矛盾 | v0.1 L369, L403-L405 | 概览表说 T-3.0 “✅ 第 1 类 R3.X follow-up”，prompt 又说 T-3.0 默认完整 ABC、跳 BC 不适用。执行层会不知道是否走完整 review。 | 统一为：T-3.0 主线起手任务默认完整 ABC；后续独立 R3.3+ follow-up 才默认跳 BC。概览表同步改 ❌。 |
| F12 | 🟡 | T-3.8 依赖关系自相矛盾 | v0.1 L319-L323, L377, L1261-L1263 | Wave 0 说 T-3.8 无依赖、不阻塞；prompt 又要求修改 `/generator/batch_scheduler.py` hook，而 batch_scheduler 是 T-3.5 才新建。若先跑 T-3.8，执行会话只能碰不存在文件或越界改未来任务。 | 拆 T-3.8a `version_recorder.py` 独立模块；T-3.5 或 T-3.9 负责 hook 接入。或者把 T-3.8 移到 T-3.5 后。 |
| F13 | 🟡 | T-3.5 不应依赖 T-3.4 playtest | v0.1 L333-L340, L953 | 批量调度器不需要 playtest 框架才能生成场景；把 T-3.4 作为 T-3.5 hard dependency 会把关键路径串长。review_ui 展示 playtest 也可 degrade。 | T-3.5 只依赖 T-3.2/T-3.3；T-3.4 与 T-3.5 并行。T-3.6 对 playtest 视图做 “产物存在则展示，否则隐藏/提示未跑”。 |
| F14 | 🟡 | token bucket 与 sync provider API 的设计边界含糊 | v0.1 L984-L992；`LLMProvider.generate_structured` 为同步协议 | prompt 说在 LLMProvider 调用前 `await acquire`，但 `generate_scene` 和 provider 协议是同步的，T-3.5 又倾向 `asyncio.to_thread(generate_scene)`。若不定义 wrapper 形态，执行者可能在调度层限了 scene 数，却没限住内部 skeleton/fill/judge 调用速率。 | 明确实现 `RateLimitedProvider(LLMProvider)`：同步 `generate_structured` 内用线程安全 bucket 阻塞等待；或正式提供 async provider wrapper。不要只在 scene worker 外层限速。 |
| F15 | 🟡 | dep_index schema 约束太松且 prompt 内自相矛盾 | v0.1 L626-L699 | schema 对 `state_paths_read/write` 没有 ADR-016 五命名空间 pattern，对 id 数组没有 `uniqueItems`，`scene_id` pattern 还比 dialogue_graph.graph_id 更窄。prompt 说 optional 数组 “missing 或 null 合法”，但 schema 只允许数组，不允许 null。 | content_dependency_index schema 至少约束 state path namespace、prompt hash、unique arrays；明确 optional 字段是 “missing only” 还是 “missing/null both ok”。`scene_id` 建议对应 `graph_id` 或 `scene_anchor` 语义，不混用。 |
| F16 | 🟡 | review UI 单任务范围过宽，且浏览器验证设为 optional | v0.1 L1081-L1143 | T-3.6 同时做 FastAPI server、REST API、graph/path/issues/visual/review/stale/playtest/chapter 集成，接近一个小应用；但测试只要求 pytest，浏览器截图可选。对 UI 任务来说，这会让“5 视图齐全”在纸面过关。 | 拆成 T-3.6a MVP（scene list + graph + validator + A/R/S）和 T-3.6b integrations（visual/playtest/stale/chapter）。浏览器 smoke、截图、mermaid 渲染检查应是 mandatory A 完成标志。 |
| F17 | 🟡 | mermaid CDN 作为完成依赖不稳 | v0.1 L241, L1088, L1136, L1569-L1570 | ADR-025 选择 mermaid.js CDN，但 T-3.6 完成标志依赖图渲染；T-3.11 才把 CDN 风险记录到开源剥离清单。若本地网络/CDN 变更失败，review UI 核心视图直接坏。 | T-3.6 就提供 fallback：已有 ASCII/DOT 文件可切换展示；或 vendor 固定版本 mermaid bundle。T-3.11 只记录开源化注意事项，不能替代阶段 3 可用性。 |
| F18 | 🟡 | R2-5 没吸收 “AI judge vs 作者 kappa” 半项 | STAGE_2_ACCEPTANCE L186；HANDOFF L45；v0.1 L425-L435 | handoff 明示 R2-5 阶段 3 起手期应与 AI 判官 vs 作者 kappa 校准合并做；v0.1 只修 dimensions dict parse。阶段 3 又要用 LLM judge 做 playtest worst/critical，这个校准缺口会扩大。 | T-3.0 或 T-3.4 增 mini calibration：用 3-5 个 baseline_011 场景让作者 [A]/[R]/[S] 与 AI judge / playtest judge 对齐，至少报告 disagreement，不必追求正式 kappa。 |
| F19 | 🟡 | T-3.10 强制 “至少 1 次 R3.X follow-up” 会诱导造问题 | v0.1 L1521 | 实测期 A 完成标志要求至少 1 次 R3.X follow-up 实战。若流水线首轮真的平稳，这条会让阶段 3 为了满足流程而制造或放大小修。 | 改为 “如出现 finding，至少 1 个按 R3.X 机制闭环；若 0 finding，记录 no-follow-up justification + raw metrics”。 |
| F20 | 🟡 | playtest 可复现性元数据不足 | v0.1 L887-L898, L905-L912 | persona base 可复现，但选项决策和 judge 都是 LLM 调用；没有要求保存 model_id、temperature、prompt hash、persona hash、option set、seed/trace。worst-10% 后续难复盘。 | 每个 `playtest_NNN` 写 `run_manifest.json`，每条 path 存 persona version、model_id、prompt hash、choice prompt摘要、合法 options、raw choice、judge rubric version。 |
| F21 | 🟡 | worst-10% “路径” 与 ROADMAP “场景清单”口径混用 | ROADMAP L208；v0.1 L173-L174, L64 | ROADMAP 强化项说输出 worst-10% 场景清单；v0.1 ADR-022 主要输出 worst paths。两者都需要，但完成标志口径不同。 | playtest 输出两个层级：`worst_paths.jsonl` 和 `worst_scenes.md/json`，scene 分数由 path 分布、critical count、最低分加权得出。 |
| F22 | 🟢 | SCHEMA_v0.3 / v0.4 文档落点模糊 | v0.1 L371, L608 | 概览说 `/docs/SCHEMA_v0.4.md` 新建视需要，prompt 又说优先追加 `SCHEMA_v0.3.md`，实在塞不下才 v0.4。schema 文档是 L1-ish 文档，执行会话不应现场拍这种版本分叉。 | v1.0 直接拍板：content_dependency_index 是 stage-3 production sidecar，建议追加 `SCHEMA_v0.3.md` 的 “production sidecars” 段；不要让 A 会话决定是否新建 v0.4。 |

严重度定义沿用户要求：🔴 = 阻塞阶段 3 启动 / 与 L1 文档直接冲突 / 阈值错算损害可证伪性；🟡 = 不阻塞但显著影响推进效率 / 工程债务；🟢 = 体例和清晰度优化。

## 3. 与历史阶段经验对照

- 阶段 2 的最大经验是 “completion gate 必须可测且双报”。ADR-021 把不可证明的 reachability 改成 2A/2B 双报；v0.1 在 D3、ADR-022 又引入了未校准的 [A] rate、critical_issue、worst-10% 口径，重复了“看似有数字但口径未固化”的早期风险。
- 阶段 2 的 R2.X follow-up 跳 BC 破例是有效的，但 v0.1 把它写得前后不一：T-3.0 概览说可跳，prompt 又说不跳；T-3.10 也混用 “不走完整 ABC” 与 “默认 ABC 变体”。这会削弱阶段 2 刚跑顺的治理肌肉。
- 阶段 2 v1.0 对 prompt 体例最重要的修订之一是让执行会话读稳定 source-of-truth；v0.1 当前所有 prompt 读一个 main workspace 不存在的 draft 路径，这是阶段 2 已避免过的 “执行上下文悬空”。
- R2-5 被吸收得不完整。阶段 2 验收与 HANDOFF 都说 dimensions 修复应和 AI judge vs 作者校准合并考虑；v0.1 只处理 parse bug，但阶段 3 又让 LLM judge 承担 playtest critical gate，风险比阶段 2 更高。
- R2-10c 的 pre-flight probe 被纳入 T-3.0 是对的，但 playtest 侧没有同级别的 pre-flight/cost calibration；这和 baseline_008 余额闸门教训不一致。

## 4. 决策选择二阶分析（≥ 3 项）

### D1 playtest bots 阈值

| 方案 | 成本 | 风险 | 收益 | 结论 |
|---|---|---|---|---|
| v0.1：5 persona × 20 paths，至少 5 场景完整跑 | 标称 $10，但真实可能是数千 LLM calls | 未校准前可能烧钱/耗时；critical rubric 不稳 | 覆盖 worst-bucket 的方向正确 | 保留目标，但必须先做 calibration run + call/time/cost guard |
| 降级：5 persona × 5 paths 起步，实测后扩到 20 | 首轮低 | 统计弱，可能抓不到低概率路径 | 能先验证 runner/rubric/成本 | 建议作为 T-3.4 A 阶段 mandatory smoke |
| 升级：10 persona × 50 paths | 高 | 阶段 3 起步过重 | 覆盖更强 | 不建议，除非阶段 4 内容填充后再做 |

### D3 完成标志双指标

| 方案 | 成本 | 风险 | 收益 | 结论 |
|---|---|---|---|---|
| v0.1：gross_pass ≥80% + [A] ≥60% + 10 场景/周 | 低 | 允许逻辑层从 100% 回落到 80%；10 样本 [A] 波动大 | 简单、容易判定 | 不建议原样作为完成 gate |
| 分层 gate：logic ≥95% 或 0 untriaged critical；[A] ≥60% pilot | 中 | 稍严格，可能多触发 R3 follow-up | 保护阶段 2 已达成的逻辑层质量 | 推荐 |
| 双阶段：首周 ≥10 场景 pilot，第二波确认 ≥15 scenes | 高 | 多花一轮 | “稳定”更可信 | 若首周数据边缘，作为 fallback |

### D4 长对话一致性 C 起步

| 方案 | 成本 | 风险 | 收益 | 结论 |
|---|---|---|---|---|
| v0.1：≤5 summaries，人工/半自动，A/B hook | 中低 | 与并发调度冲突；无 token 曲线 instrumentation | 符合作者不预防性设计态度 | 方向对，但必须加依赖 DAG + token metrics |
| 纯人工 summaries，无 LLM summary_writer | 低 token 成本 | 作者维护负担高 | 极简、可控 | 可作为 fallback，不应唯一 |
| RAG/memory stream | 高 | 过早架构化 | 自动 retrieve 更强 | 不适合阶段 3 起步，保留 hook 即可 |

### D6 batch scheduler N=3

| 方案 | 成本 | 风险 | 收益 | 结论 |
|---|---|---|---|---|
| v0.1：flat queue N=3 | 工程中等 | 速率限制可能没套住内部 provider calls；依赖场景乱序 | 简单提速 | 只适合独立 scenes |
| DAG 分层 + 层内 N=3 | 工程略高 | 需要 SceneSpec 增字段 | 保住 prior summaries 与吞吐 | 推荐 |
| N=1 串行 | 工程最低 | 10 场景耗时长 | 最稳，便于初期 debug | 用作 fallback/env 降级 |

## 5. 漏抓事项（cross-LLM 增益核心；至少 5 项）

- **U-GPT-01**：v0.1 draft 实际不在它自称的 main workspace 路径，所有 paste-ready prompt 自引用会失效（F1）。
- **U-GPT-02**：`GraphContext` / `SceneGraphContext` 混淆会让长对话一致性改到错误层级（F3）。
- **U-GPT-03**：N=3 并发和 `prior_scene_summaries` 存在剧情依赖顺序冲突，需要 SceneSpec DAG（F4）。
- **U-GPT-04**：dep_index 的 “read dependencies” 不能从最终 scene 反推，必须由 context assembly 产 trace（F5）。
- **U-GPT-05**：chapter assignment 在 dep_index 之后会写出 stale `chapter_id` / `act_id`（F6）。
- **U-GPT-06**：review UI 任务缺 pyproject / dependency / package 边界，执行会话无法合法落地 FastAPI（F2）。
- **U-GPT-07**：playtest 的 call/cost 模型按 “每 path 一次调用” 估算，低估真实 LLM 调用数（F9）。
- **U-GPT-08**：`critical_issue` completion gate 无 severity rubric，不可复核（F10）。

## 6. 直接矛盾 / 严重度分歧

**直接矛盾**

- F1：v0.1 文档位置与 prompt 自引用路径直接矛盾；main workspace 没有该 draft。
- F2：T-3.6 要 FastAPI + tools package，但模块边界不允许修改 `pyproject.toml`，且 repo 当前没有 `tools` package。
- F3：T-3.3 指向 `GraphContext`，但 scene-level 生成实际使用 `SceneGraphContext`。
- F6：T-3.5 先写 deps 读取 chapter，T-3.9 后写 chapter assignment，顺序互相打架。
- F7：§1 写 scene 内 version metadata，T-3.8 写 sidecar；§1 写每次修改记 git commit，T-3.8 明确不自动 commit。
- F11：T-3.0 是否跳 BC，概览表和 prompt 互相否定。
- F12：T-3.8 无依赖 vs 修改未来 T-3.5 才存在的 batch_scheduler。

**严重度分歧**

- v0.1 把 D3 gross_pass ≥80% 当正常阈值，我认为是 🔴：它损害阶段 3 完成判定的可证伪性，并允许阶段 2 已达成的 100% logic-layer baseline 大幅回归。
- v0.1 把 D1 playtest 成本视为约 $10，我认为其估算风险至少 🟡，在未校准 call model 前会影响 T-3.10 可执行性，若直接作为完成 gate 则接近 🔴。
- v0.1 把 review_ui 作为单个 A 任务，我认为至少 🟡：不是方向错，而是可交付粒度和验证要求不足。

## 7. 整合建议（paste-ready instruction）

请作为 Claude L2 整合规划师，基于 `STAGE_3_TASKS_draft_v0.1` 和本 GPT-5.5 critique 产出 v1.0，落到 `/docs/STAGE_3_TASKS.md`（[B-author-gate] 任务）。处理顺序：

1. 先修 🔴：F1-F10。重点修订 v0.1 §0/§8 所有草稿自引用路径为 `/docs/STAGE_3_TASKS.md`；T-3.6/T-3.7 允许 `pyproject.toml` 和 `tools` package bootstrap；T-3.3 改 `SceneGraphContext`；T-3.5 SceneSpec 加 dependency DAG；dep_index 改由 context assembly trace 写入；chapter assignment 与 dep_index 顺序重排；T-3.8 completion gate 改为 version sidecar 审计；D3 阈值改成 logic regression gate + [A] pilot；ADR-022 增 calibration run、cost/call guard、critical severity taxonomy。
2. 再修 🟡：F11-F21。统一跳 BC 文案；拆/移动 T-3.8 hook；移除 T-3.5 对 T-3.4 hard dependency；明确 RateLimitedProvider wrapper；收紧 dep_index schema；拆 review UI MVP / integrations 并强制浏览器 smoke；提供 mermaid fallback；补 R2-5 judge-author calibration；T-3.10 不强制制造 R3.X；playtest 写 run_manifest；输出 worst_paths + worst_scenes 双层报告。
3. 最后修 🟢：F22。直接拍板 `SCHEMA_v0.3.md` 增量落点，不让 A 执行会话现场决定 v0.4。

具体段落修订点：

- v0.1 §2.1 D1/D3/D4/D6：按 F8/F9/F10/F4/F14 重写阈值与 instrumentation。
- v0.1 §2.4：新增 `SceneSpec.depends_on_scene_ids`、`GenerationDependencyTrace`、`playtest run_manifest`、`version sidecar required audit` 字段统一表。
- v0.1 §3 ADR-022：加 calibration run + severity taxonomy + scene-level aggregate。
- v0.1 §3 ADR-023：把 dep_index 写入语义改成 “context trace over-approx”，不是 output reverse inference。
- v0.1 §3 ADR-024：明确 token/prompt metrics hook：每 scene 记录 prompt token estimate、summaries injected count、summary source hashes、truncation reason。
- v0.1 §6 wave 图：T-3.5 不依赖 T-3.4；T-3.8 不在 Wave 0 直接 hook batch_scheduler；chapter assignment 顺序前置或并入 T-3.5。
- v0.1 §7 表：T-3.0 跳 BC 改 ❌；T-3.6/T-3.7 模块边界加 `pyproject.toml`；T-3.8 依赖修正。
- v0.1 §8 prompts：逐条替换读 v0.1 草稿路径；T-3.3/T-3.5/T-3.6/T-3.8/T-3.10 prompt 必须按上述 finding 改写。

整合后请在 `/docs/STAGE_3_TASKS.md` §0 修订记录列出本 critique finding 对照表，至少说明 F1-F10 均已处理或显式拒收并给理由。

## 8. 必读策略复盘（精简版执行情况）

- 8 份预读充分。v0.1 主体、CLAUDE.md、ROADMAP 阶段 3/4、ADR-016~021、DEBATE §9/Round5、STAGE_2_ACCEPTANCE §4/§5/§8、HANDOFF 全文、synthesis §6/§7/§9/§11 足够支撑架构层 critique。
- by-need 实际触发 5 份：`STAGE_2_TASKS.md`（ABC/prompt 体例）、`2026-05-01_review_routine_governance.md`（§10）、`2026-05-02_PZ_design_reflection.md`（§5/§7）、`SCHEMA_v0.3.md`（复合版本语义）、`content/test_scene_v0/scene.json`（gold scene 形态）。
- 未预想但必要的增补：`pyproject.toml`、`generator/context_assembler.py`、`generator/generate_scene.py`、`generator/llm_provider.py`、`generator/scene_review_cli.py`、`schema/dialogue_graph.schema.json`、`schema/chapter.schema.json`。这些不是为了写代码，而是验证 v0.1 prompt 的模块边界是否能在真实 repo 中落地。阶段 4 critique 建议把 “repo structure / dependency manifest / key current modules” 加入 by-need 明示清单，尤其当任务清单包含新工具包或 Web UI 时。
