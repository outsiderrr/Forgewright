# STAGE_3_TASKS.md — 阶段 3 任务清单（v1.0 正式版）

> 阶段 3 任务清单 v1.0 source-of-truth。整合自 v0.1 草稿 + GPT-5.5 cross-LLM critique 22 finding + Claude round 2 response + 作者 2026-05-08 三议题拍板（F1 / F2 / F8）。
>
> 历史草稿见 [/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md](reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md)；GPT-5.5 critique 见 [/docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md](reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md)；Claude round 2 + 作者拍板见 [/docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md](reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md)。

**日期**：2026-05-08 · **版本**：v1.0 · **产出方**：阶段 3 L2 整合规划师会话（claude/sweet-bardeen-863720 worktree）

---

## 0. 文档说明

本文件 = 阶段 3 任务清单 source-of-truth，与阶段 2 [`/docs/STAGE_2_TASKS.md`](STAGE_2_TASKS.md) 同源体例。所有 L3 执行会话按 §8 paste-ready prompt 启动。

**整合记录**：

- v0.1 草稿（2026-05-07）落 `/docs/reviews/master_plan/`（13 paste-ready prompts + ADR-022~026 候选 + Wave 0-7 依赖图）
- GPT-5.5 cross-LLM critique（2026-05-08）跑出 22 finding（🔴 10 / 🟡 11 / 🟢 1）；含 5 条 Claude 视角漏抓的工程层 🔴 finding（F2 / F3 / F5 / F6 / F12）
- Claude round 2 response（2026-05-08）严守 review/author 分离——不直接吸收 critique；先反应文档 + 作者拍板再整合
- 作者 2026-05-08 拍板：
  - F1 严重度 🔴 → 🟢（v1.0 整合常规步骤）
  - F2 方案 A：FastAPI / uvicorn deps + tools package 注册 pyproject.toml
  - F8 方案 A：0 critical validator failures + [A] ≥ 60% pilot + Wilson CI

### 0.1 v0.1 → v1.0 的 22 finding 处理对照表

| # | Codex | Claude 反应 | v1.0 整合落地 |
|---|---|---|---|
| F1 | 🔴 | 🟢（反驳）| §8 paste-ready prompts 全文路径替换 v0.1 草稿引用 → `/docs/STAGE_3_TASKS.md`（本文件本身） |
| F2 | 🔴 | 🔴（同意；A）| T-3.6a / T-3.6b / T-3.7 模块边界加 `pyproject.toml`（fastapi / uvicorn deps + tools package 注册）|
| F3 | 🔴 | 🔴 | T-3.3：`GraphContext` → `SceneGraphContext`；同步修 `_build_scene_context` + `scene_strategies` skeleton/fill prompt 渲染段；节点级 `GraphContext` 阶段 3 不动（兼容） |
| F4 | 🔴 | 🔴 | `SceneSpec` 加 `depends_on_scene_ids` / `sequence_group`；T-3.5 调度器拓扑分层；T-3.10 实测场景集声明依赖图 |
| F5 | 🔴 | 🔴 | ADR-023 决策核心修订：dep_index 写入语义改 "context assembly over-approx trace"，不是 scene 反查；T-3.5 + T-3.3 prompt 加 `GenerationDependencyTrace` 注入 |
| F6 | 🔴 | 🔴 | T-3.5 + T-3.9 写入顺序：write scene → assign chapter → write deps → record version；T-3.9 改先 helper 库交付，T-3.5 调用 |
| F7 | 🔴 | 🔴 | §1 完成标志措辞改 "每个入库 scene 必须有 version sidecar，T-3.10 验收审计无缺失"；放弃 "scene 内 version 字段"（与 ADR-016 schema 不动一致）；放弃 "自动 git commit"（与 CLAUDE.md 安全约束一致）|
| F8 | 🔴 | 🔴（A）| §1 阈值表改 "0 critical validator failures + warning/minor 在 R3.X 修 + [A] ≥ 60% pilot + Wilson CI" |
| F9 | 🔴 | 🔴 | ADR-022 + T-3.4 加 calibration run（1 scene × 1 persona × 5 paths 实测 avg calls/path / tokens/path / seconds/path）+ `--max-cost-usd` / `--max-calls` / `--max-wall-clock-min` 三重 guard |
| F10 | 🔴 | 🔴 | ADR-022 加 critical / major / minor severity taxonomy；critical 必须作者明示确认 |
| F11 | 🟡 | 🟡 | §7 表格 + T-3.0 prompt 统一为 "默认完整 ABC"（T-3.0 是阶段 3 主线起手任务） |
| F12 | 🟡 | 🟡 | T-3.8 拆 T-3.8a（version_recorder.py 独立模块；Wave 0）+ T-3.8b（batch_scheduler hook 合并入 T-3.5）|
| F13 | 🟡 | 🟡 | T-3.5 仅依赖 T-3.2 + T-3.3；T-3.4 与 T-3.5 并行；T-3.6 review_ui 对 playtest 视图做 "产物存在则展示，否则隐藏" degrade |
| F14 | 🟡 | 🟡 | T-3.5 prompt 加 "实现 RateLimitedProvider(LLMProvider)：同步 generate_structured 内用线程安全 bucket 阻塞等待" |
| F15 | 🟡 | 🟡 | T-3.2 schema 加 ADR-016 五命名空间 pattern + uniqueItems + scene_id pattern 与 dialogue_graph.graph_id 对齐；明示 optional missing-only |
| F16 | 🟡 | 🟡 | T-3.6 拆 T-3.6a (MVP) + T-3.6b (integrations)；浏览器 smoke / 截图 / mermaid 渲染检查改 mandatory |
| F17 | 🟡 | 🟡 | T-3.6a 自带 fallback：可切换 ASCII/DOT 文件展示（T-2.8 已有产物）或 vendor 固定版本 mermaid bundle |
| F18 | 🟡 | 🟡 | T-3.0 或 T-3.4 加 mini calibration（3-5 个 baseline_011 场景作者 [A]/[R]/[S] vs AI judge 对齐 + 报告 disagreement）|
| F19 | 🟡 | 🟡 | T-3.10 改 "如出现 finding，至少 1 个按 R3.X 闭环；若 0 finding，记录 no-follow-up justification + raw metrics" |
| F20 | 🟡 | 🟡 | T-3.4 prompt 加 run_manifest.json：每 playtest_NNN 写 model_id / temperature / prompt hash / persona hash / option set / raw choice / judge rubric version |
| F21 | 🟡 | 🟡 | T-3.4 输出双层 `worst_paths.jsonl` + `worst_scenes.md/json`；scene 分数 = path 分布 / critical count / 最低分加权 |
| F22 | 🟢 | 🟢 | T-3.2 prompt 拍板 SCHEMA_v0.3.md 增量段（与 ontology 模块同 epoch），不让 A 会话现场决定 v0.4 |

### 0.2 任务拆分变化（v0.1 13 槽位 → v1.0 15 槽位）

| v0.1 编号 | v1.0 编号 | 拆/合状态 |
|---|---|---|
| T-3.0 ~ T-3.5 | T-3.0 ~ T-3.5 | 不变 |
| T-3.6 | **T-3.6a + T-3.6b** | 拆（F16）：MVP（scene list + graph + validator + A/R/S）+ integrations（visual/playtest/stale/chapter）|
| T-3.7 | T-3.7 | 不变 |
| T-3.8 | **T-3.8a + T-3.8b** | 拆（F12）：a = version_recorder.py 独立模块；b = batch_scheduler hook（合并入 T-3.5 范围）|
| T-3.9 ~ T-3.12 | T-3.9 ~ T-3.12 | 不变（T-3.9 改先 helper 库交付，由 T-3.5 调用；F6）|

**v1.0 任务总数**：**14 槽位**（13 → 14；T-3.6 拆 a/b 增 1；T-3.8 拆 a / b 但 b 范围合并入 T-3.5 抵消 1；净增 1）。

---

## 1. 阶段 3 目标回顾（含 v1.0 完成标志修订）

来自 [/docs/ROADMAP.md](ROADMAP.md) §阶段 3。

**目标函数**：作者每天稳定产出几千字质量达标的剧情内容；一周完成 ≥ 10 场景生成 + 审阅 + 入库。

**完成标志（v1.0 修订；F7 / F8 / F10 联动）**：

| 指标 | 阈值 | 来源 |
|---|---|---|
| 批量调度器 | asyncio + N=3 concurrent + token bucket + ontology file lock + SceneSpec DAG 拓扑分层 | D6 + F4 |
| 审阅 UI | T-3.6a MVP（scene list + graph + validator + [A]/[R]/[S]）+ T-3.6b integrations（visual/playtest/stale/chapter）；mermaid CDN fallback；浏览器 smoke mandatory | D5 + F2 + F16 + F17 |
| 一致性维护 | content_dependency_index sidecar 写入流水线（**context assembly trace** 不是 scene 反查）+ 反向 propagate 工具 | D2 + F5 |
| 版本控制集成 | **每个入库 scene 必须有 version sidecar，T-3.10 验收审计无缺失**（F7 修订；放弃 scene 内 version 字段 + 放弃自动 git commit）| F7 |
| 实测吞吐 | 1 周 ≥ 10 场景 | ROADMAP 字面 |
| **logic regression gate** | **0 critical validator failures**（schema / topology / sampling / mechanical 任一 critical 级失败 = 阶段 3 不达标）；warning / minor 级失败允许在 R3.X follow-up 闭环修复 | **F8 方案 A** |
| 审美层 [A]ccept rate（pilot）| **≥ 60%（N=10 场景；附 Wilson 95% CI 报告，如 6/10 → CI 27%-86%）；不用单点百分比伪装稳定** | **F8 方案 A** |
| playtest bots 完整性 | 至少 5 场景跑过完整 100 paths/scene；worst-10% 清单产出 + 0 critical issue 或全部修复（critical 定义见 ADR-022 severity taxonomy）| D1 + F9 + F10 |
| 长对话一致性 | C 起步：prompt SceneGraphContext 注入 `prior_scene_summaries` 字段（F3）；A/B hook 留：content_dependency_index.scene_history_referenced + token/prompt metrics hook（每 scene 记 prompt token estimate / summaries injected count / summary source hashes / truncation reason）| D4 + F3 |

**critical / major / minor severity taxonomy（ADR-022 落地；F10）**：

- **critical** = validator 漏掉的非法路径、状态因果矛盾、角色/本体直接冲突、玩家结果透明度严重误导
- **major** = 显著叙事质量问题（节奏 / 风格 / 合理性）
- **minor** = 体例 / 措辞 / 微调
- critical 必须作者明示确认，不能只靠 LLM-as-judge 自动通过 gate

---

## 1.5 ABC 三阶段闭环（治理备忘 v0.3 §10 吸收 + 阶段 2 实证 + v1.0 跳 BC 破例 5 类清单）

### 1.5.1 三阶段定义

- **A 开发阶段**：作者起 Claude Code worktree 会话；按对应 paste-ready prompt 开发 + 测试 + commit + push + 开 PR（base = `main`，head = worktree 分支名）。**A 阶段完成 ≠ L3 通过**。
- **B review 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 [/docs/REVIEW_PROMPT_CODE_GPT.md](REVIEW_PROMPT_CODE_GPT.md)（commit `8842c43`）作 review prompt 模板；review A 阶段 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-3.X_<topic>_review.md`。
- **C 修复阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）。

### 1.5.2 L2 验收

L2 拿 ABC 全部产出判断；过关 → 通知作者 merge PR + 进下一个 L3；打回 → 指定回 C 或回 B 跑二轮。

### 1.5.3 PR merge 硬规则

**A+B+C 全部完成 + L2 验收过关之前，PR 一律不 merge**——v0.3 治理备忘核心约束。

### 1.5.4 跳 BC 破例类型清单（5 类；F11 修订）

> 阶段 2 收官期 13 个 PR 走作者明示授权跳 B/C 直接 merge 模式（参 [/docs/STAGE_2_ACCEPTANCE.md](STAGE_2_ACCEPTANCE.md) §8.2）。阶段 3 起手就**显式枚举可跳 BC 类型**，避免每条都问作者一遍。

**默认授权跳 BC 的 5 类**：

1. **R3.X follow-up**（baseline_NNN / playtest_NNN 反向触发的 generator/validator/provider 修复任务；编号 R3.3+）
2. **baseline_NNN finding**（实证 batch run 暴露的工具链漏洞）
3. **playtest_NNN finding**（playtest bots 实证暴露的内容/工具链漏洞）
4. **审阅 UI 工坊化 ergonomic 改进**（仅前端文案 / 视图调整 / 不动后端 schema 与算法）
5. **阶段 3 验收报告**（T-3.12）

**跳 BC 模式工作流**：A 阶段会话主动修 + 拆 commit 标注 finding（如 `fix: R3.X xxx (baseline_NNN finding)`）+ L2 quick check + 作者授权 merge。

**默认 ABC 闭环**：T-3.0 ~ T-3.11（**含 T-3.6a / T-3.6b / T-3.8a / T-3.8b**）一律走完整 ABC（**T-3.0 是阶段 3 主线起手任务，不是 R3.X follow-up；F11 修订**）；T-3.10 实测期为 ABC 变体（详 T-3.10 prompt）。

### 1.5.5 routine 兼容性

- 所有 L3 一律 ABC 闭环——无论 §7 类型列标 [A-execute] 还是 [B-author-gate]
- routine 仅可用于 A 阶段串联；**不可跨过 B/C/验收闭环**
- 不要尝试搭 git hook / GitHub Action 把 B/C 自动化

---

## 2. 锁定的架构决策（v1.0 整合校准）

### 2.1 决策总表（D1~D10 + critique 修订）

| 决策 | v0.1 内容 | v1.0 修订（critique 整合）| 来源 |
|---|---|---|---|
| **D1 playtest bots 阈值** | N=5 persona / M=20 paths / 至少 5 场景 / worst-10% 输出 | **加 calibration run（1 scene × 1 persona × 5 paths 实测后锁参数）+ 三重 guard（`--max-cost-usd` / `--max-calls` / `--max-wall-clock-min`）+ critical/major/minor severity taxonomy + 双层输出 worst_paths.jsonl + worst_scenes.md/json** | C2 + D1 + F9 + F10 + F21 |
| **D2 content_dependency_index 形态** | per-scene sidecar `<scene>.deps.json`；scene + ontology 反查 | **写入语义改 "context assembly over-approx trace"，不是 scene 反查；schema 字段约束加严（state path namespace pattern + uniqueItems + scene_id pattern 与 dialogue_graph.graph_id 对齐）** | C6 + D2 + F5 + F15 |
| **D3 完成标志双指标** | gross_pass ≥ 80% + [A] ≥ 60% + Y=10 场景/周 | **logic regression gate 改 "0 critical validator failures + warning/minor 在 R3.X 修"；审美层 [A] ≥ 60% pilot + Wilson 95% CI 报告**（F8 方案 A）| U-CL-1 + D3 + F8 |
| **D4 长对话一致性投入度** | C 起步全套；A/B hook 留 | **加 token/prompt metrics hook（每 scene 记 prompt token estimate / summaries injected count / summary source hashes / truncation reason）；prompt 模板改 SceneGraphContext（不是 GraphContext）注入 prior_scene_summaries** | U-CL-5 + D4 + F3 |
| **D5 审阅 UI 形态** | Web 单页（FastAPI + vanilla HTML/JS + mermaid.js CDN）；5 视图 | **拆 T-3.6a (MVP) + T-3.6b (integrations)；模块边界加 pyproject.toml（fastapi / uvicorn deps + tools package 注册）；mermaid CDN fallback（vendor bundle 或 ASCII/DOT 切换）；浏览器 smoke / 截图 / mermaid 渲染检查改 mandatory** | U-GPT-7 + D5 + F2 + F16 + F17 |
| **D6 批量调度器并发模型** | asyncio + N=3 concurrent + token bucket + ontology lock | **SceneSpec 加 depends_on_scene_ids / sequence_group / prior_summary_paths 字段；调度器拓扑分层（同层并发，不同层串行）；RateLimitedProvider(LLMProvider) wrapper（同步 generate_structured 内线程安全 bucket）；T-3.5 不依赖 T-3.4** | D6 + F4 + F13 + F14 |
| **D7 跳 BC 破例 5 类** | 5 类 | **不变** | 阶段 2 实战 + D7 |
| **D8 R3.X follow-up 占位** | R3.0/3.1/3.2 阶段 2 三遗留并入 T-3.0 | **加 R3.3 mini calibration（R2-5 + AI judge vs 作者 kappa；F18 修订并入 T-3.0 或 T-3.4）** | D8 + F18 |
| **D9 双轨命名 baseline_NNN + playtest_NNN** | baseline_NNN / playtest_NNN | **不变；playtest_NNN 加 run_manifest.json（model_id / temperature / prompt hash / persona hash / option set / raw choice / judge rubric version）** | D9 + F20 |
| **D10 ADR-022~026 拆 5 条** | 5 条 ADR 一次性 commit | **不变；决策核心按本表修订** | D10 |

### 2.2 阶段 2 实战吸收（硬背景输入；与 v0.1 §2.2 一致）

- **R2.X follow-up 跳 BC 破例模式**实战 13 个 PR 已验证（参 STAGE_2_ACCEPTANCE.md §8.2）；阶段 3 工程债低，跳 BC 频率应自然下降
- **L2 整合规划师 + 阶段验收角色**实证有效；阶段 3 同款角色继承
- **Provider 仪表化习惯**（R2.9）阶段 3 多场景并行调度时同款必要——T-3.5 调度器对每个并发 worker 仪表化
- **抽公共模块的克制粒度**（R2.8 共享 sanitizer + R2.10b 共享 retry policy）—— 阶段 3 维持同款抽取风格
- **schema 版本号策略**（ADR-016 §schema 版本号）—— 阶段 3 新建 `/schema/content_dependency_index.schema.json` 首版 const `0.3.0`；既有 schema 全部不动

### 2.3 作者态度（PZ §7 硬背景；与 v0.1 §2.3 一致）

- **对 AI 进化能力有信心**——影响 U-CL-5 缓解 ADR 紧迫度（D4 选 C 起步 + A/B hook，不投入 hybrid (A+C) 完整方案）
- **50–100 场景规模可能不撞 §9.2 真墙**——这判断未验证，等阶段 3 实测一周 10 场景的真实 token 累积曲线后才能确认
- **状态文件抽象层"真遇到再说"，不预防性设计**——但 L2 必须保留 hook（D4 中 content_dependency_index.scene_history_referenced 字段即此 hook）

### 2.4 跨任务一致性细节统一（v1.0 整合扩展）

| 字段 / 命名 | 取值 |
|---|---|
| 长对话一致性 prompt context 字段名 | `prior_scene_summaries: list[{scene_id, summary, key_state_paths}]`（**SceneGraphContext** 新增字段；F3 修订；T-3.3 落地） |
| `SceneSpec` DAG 字段（F4） | `depends_on_scene_ids: list[str]` / `sequence_group: str` / `prior_summary_paths: list[Path]`（T-3.5 落地）|
| `GenerationDependencyTrace` 字段（F5） | context assembly 阶段累加：`character_ids` / `location_ids` / `clock_ids` / `relation_ids` / `state_paths_read` / `prompt_template_hash` / `visual_asset_ids`（T-3.3 + T-3.5 共同落地）|
| `RateLimitedProvider` wrapper 形态（F14） | `class RateLimitedProvider(LLMProvider)`：同步 `generate_structured` 内用 threading.Semaphore + 时间窗口（T-3.5 落地）|
| dep_index sidecar 文件名格式 | `<scene>.deps.json`（与 scene.json 同目录）|
| 调度器并发参数 | env `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 `3`），`FORGEWRIGHT_PROVIDER_RPM`（默认 `60`）|
| review UI 端口 | env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 `8765`）|
| playtest bots persona 来源 | `/generator/playtest/personas/<persona_id>.json`（v0.1 hand-write 5 个 + LLM augment description）|
| playtest run_manifest.json 字段（F20） | 每 playtest_NNN 写：`model_id` / `temperature` / `prompt_hash` / `persona_hash` / `option_set` / `raw_choice` / `judge_rubric_version` |
| baseline / playtest cost log 分离 | `/generator/cost_log.jsonl`（generator 主流程）+ `/generator/playtest_cost_log.jsonl`（T-3.4 新建）|
| version sidecar 文件名格式（F7） | `<scene>.version.json`（与 deps.json 同目录平行；T-3.8a 落地）|
| version sidecar required audit gate（F7） | T-3.10 验收期审计每个入库 scene 必须有 version sidecar；缺失 = 阶段 3 不达标 |

---

## 3. 推荐立项的 ADR 清单（候选 ADR-022 ~ ADR-026；v1.0 整合校准）

> L2 不立 ADR；这里只识别"该立哪些"。由作者明示授权后由 T-3.1（[B-author-gate]）一次性立完。

| 候选 | 议题 | v0.1 → v1.0 修订要点 |
|---|---|---|
| **ADR-022** | playtest bots 完成标志阈值 | 加 calibration run + 三重 guard + critical/major/minor severity taxonomy + 双层输出 |
| **ADR-023** | content_dependency_index sidecar 形态 + 字段集 | 改 context assembly trace 语义 + schema 字段约束加严 |
| **ADR-024** | 长对话一致性 C 起步 + A/B hook | 加 token/prompt metrics hook + SceneGraphContext 修正 |
| **ADR-025** | 审阅 UI 架构 | 拆 a/b 子任务 + pyproject.toml 加 deps + mermaid fallback |
| **ADR-026** | 批量调度器并发模型 | SceneSpec DAG + RateLimitedProvider wrapper + 拓扑分层调度 |

> ADR 决策核心全文见 §3.1 ~ §3.5；T-3.1 paste-ready prompt（§8）按本节内容立项。

### 3.1 ADR-022 决策核心 — playtest bots 完成标志阈值（v1.0）

- **bot persona 数 N=5**：cautious / aggressive / completionist / speedrunner / role_player（hand-write 5 个 base + LLM augment description hook 留 null）
- **每场景 paths M=20**：每 persona 跑 20 条路径 = 100 paths/scene；与 ADR-021 §2B 抽样 N=100 数量级一致
- **calibration run 必做（F9）**：T-3.4 A 阶段 mandatory smoke = 1 scene × 1 persona × 5 paths 小跑实测：avg calls/path / tokens/path / seconds/path / cost/path —— 实测后再锁 5×20 参数；如 1 path 平均 5+ calls（每决策节点 + judge），调整 M 上限或 worst-bucket 抽样形态
- **三重 guard（F9）**：T-3.4 必须支持 `--max-cost-usd <amount>` / `--max-calls <n>` / `--max-wall-clock-min <m>` flag；任一触发 = abort batch + log
- **critical/major/minor severity taxonomy（F10）**：
  - **critical** = validator 漏掉的非法路径 / 状态因果矛盾 / 角色 / 本体直接冲突 / 玩家结果透明度严重误导
  - **major** = 显著叙事质量问题（节奏 / 风格 / 合理性）
  - **minor** = 体例 / 措辞 / 微调
  - critical 必须作者明示确认，不能只靠 LLM-as-judge 自动通过 gate
- **双层输出（F21）**：
  - `playtest_NNN/worst_paths.jsonl`（path 级；含 path trace + judge_score + critical_count + severity）
  - `playtest_NNN/worst_scenes.md` + `worst_scenes.json`（scene 级；scene 分数 = path 分布 / critical count / 最低分加权）
- **完成标志**：至少 5 场景跑过完整 playtest（5×20=100 paths/scene），worst-10% 清单产出 + 0 critical issue 或全部修复
- **后果**：T-3.4 落地 `/generator/playtest/`；playtest cost log 独立 `/generator/playtest_cost_log.jsonl`；run_manifest.json 写入元数据

### 3.2 ADR-023 决策核心 — content_dependency_index sidecar 形态（v1.0）

- **形态**：per-scene sidecar `<scene>.deps.json`（与 scene.json 同目录；与 visual manifest 哲学一致）
- **写入语义（F5 修订）**：**context assembly over-approx trace**——不是 scene 反查。`_build_scene_context` 阶段累加 `GenerationDependencyTrace`；记录注入到 LLM prompt 的所有 ontology / state / clock / visual / prompt 引用。Conservative over-approx——宁可误报 stale 也不漏依赖
- **schema 字段约束加严（F15 修订）**：
  - state_paths_read / state_paths_written 必须落入 ADR-016 五命名空间 pattern（`world.*` / `faction.*` / `relationship.*` / `flag.*` / `player.*`）
  - 数组字段加 `uniqueItems: true`
  - `scene_id` pattern 与 dialogue_graph `graph_id` 对齐（`^[a-z0-9_]+$`）
  - optional 字段（chapter_id / act_id / visual_asset_ids_referenced / clock_ids_referenced / scene_history_referenced）明示 missing-only（不允许 null）
- **scene_history_referenced 字段** = D4 长对话一致性 hook：阶段 3 末期如撞墙可基于此字段升级 RAG (B) 或 memory stream (A) 不需重做 schema
- **新建 `/schema/content_dependency_index.schema.json`** 首版 const `0.3.0`（与 character/location/clock/chapter schema 同源演进）
- **写入时机（F6 联动）**：T-3.5 批量调度器写入顺序 = "write scene → assign chapter → write deps → record version"；T-3.7 一致性维护按 sidecar 反向 propagate
- **后果**：schema 落地（T-3.2）+ generate_scene hook（T-3.5）+ 反向 propagate 工具（T-3.7）

### 3.3 ADR-024 决策核心 — 长对话一致性 C 起步 + A/B hook（v1.0）

- **C 起步全套**：
  - prompt 模板 **SceneGraphContext** 注入 `prior_scene_summaries: list[{scene_id, summary, key_state_paths}]` 字段（F3 修订；不是 GraphContext）
  - 摘要来源：作者人工填 OR 半自动 LLM 摘要 + 作者校准（v0.1 起手两条路并存）
  - 上限：每场景 prompt 注入 ≤ 5 条 prior_scene_summaries（避免 prompt 膨胀）
- **token/prompt metrics hook（v1.0 新增）**：每 scene 生成时记录到 dep_index sidecar：
  - `prompt_token_estimate`（注入 prompt 总 token 估算）
  - `summaries_injected_count`（实际注入条数 0-5）
  - `summary_source_hashes`（每条 summary 的 SHA256；溯源用）
  - `truncation_reason`（如超 5 条上限被裁的 reason）
- **A/B hook 留**：content_dependency_index sidecar `scene_history_referenced` 字段；阶段 3 末期撞墙可升级
- **不在阶段 3 落地的 A/B**：A. Generative Agents memory stream / B. RAG over event log
- **后果**：T-3.3 落地 SceneGraphContext + prompt 模板 + scene_summary_writer

### 3.4 ADR-025 决策核心 — 审阅 UI 架构（v1.0；F2 + F16 + F17 修订）

- **形态**：Web 单页（local file server + 前端 vanilla HTML/JS）
- **工具栈（F2 修订）**：FastAPI 静态 server（**新增 deps**）+ uvicorn（**新增 deps**）+ 前端 vanilla HTML/JS（不引入 React/Vue/Svelte）+ mermaid.js（**vendor bundle 或 CDN with fallback；F17**）
- **`pyproject.toml` 修订（F2）**：T-3.6a / T-3.6b / T-3.7 模块边界**允许修改 pyproject.toml**——加 `fastapi` + `uvicorn` deps + `tools` package 注册
- **拆分（F16）**：
  - **T-3.6a MVP**：scene list + graph 视图（mermaid 渲染）+ validator issues 面板（schema/topology/sampling/mechanical 四 tab）+ 审美层 [A]/[R]/[S] 标注 + reason 文本框
  - **T-3.6b integrations**：visual asset thumbnail（manifest 读取）+ playtest worst paths/scenes 视图（**产物存在则展示，否则隐藏 / 提示未跑**；F13）+ stale list（dep_propagate 集成）+ chapter list 分组
- **mermaid CDN fallback（F17）**：T-3.6a 必须自带 fallback：可切换 ASCII/DOT 文件展示（T-2.8 已有产物）OR vendor 固定版本 mermaid bundle（推荐 `mermaid@10.x`）；不依赖 CDN 可用性
- **浏览器 smoke / 截图 / mermaid 渲染检查（F16）**：T-3.6a + T-3.6b A 阶段完成标志改 mandatory（不是 optional）
- **read-only**：不做编辑功能；编辑由作者直接改 JSON + git workflow
- **运行时部署**：仅生产期；env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 8765）；本地 localhost 访问
- **后果**：T-3.6a + T-3.6b 落地 `/tools/review_ui/`（含 server.py + api.py + static/）；复用 T-2.8 graph_views 三件套

### 3.5 ADR-026 决策核心 — 批量调度器并发模型（v1.0；F4 + F13 + F14 修订）

- **并发模型**：asyncio + N=3 concurrent worker（基础数据：baseline_011 单 iter mean 268s）
- **SceneSpec DAG（F4 修订）**：SceneSpec 加 `depends_on_scene_ids: list[str]` / `sequence_group: str` / `prior_summary_paths: list[Path]` 字段；调度器**拓扑分层**——同层并发（N=3 max），不同层串行；T-3.10 实测场景集声明依赖图，不是 flat specs
- **RateLimitedProvider wrapper（F14）**：实现 `class RateLimitedProvider(LLMProvider)`——同步 `generate_structured` 内线程安全 bucket 阻塞等待；包住所有 LLMProvider 调用（不在 scene worker 外层限速）；解决 token bucket 与 sync provider API 设计边界
- **速率限制**：每 provider token bucket 默认 60 RPM（env `FORGEWRIGHT_PROVIDER_RPM`）
- **ontology 写入**：file lock（fcntl on `/state/ontology/<world>.json`）；scene 文件各自独立 path 不冲突
- **写入顺序（F6 联动）**：write scene → assign chapter（T-3.9 helper 调用）→ write deps（T-3.5 含 dep_index trace）→ record version（T-3.8a 调用）
- **依赖关系**（F13 修订）：T-3.5 仅依赖 T-3.2 + T-3.3，**不依赖 T-3.4 playtest**；T-3.4 与 T-3.5 并行
- **失败传播**：单 worker scene 失败不阻塞其他并发场景；每 worker 独立 ProviderError 仪表化（沿用 R2.9）
- **配置**：`FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 `3`） / `FORGEWRIGHT_PROVIDER_RPM`（默认 `60`）

---

## 4. 启动闸门清单

### 4.1 ROADMAP §阶段 3 完成标志强化项映射（5 项）

- ✅ **C2** playtest bots 完成标志 → ADR-022 + T-3.4 落地（阈值 N=5 / M=20 / worst-10%）+ severity taxonomy + calibration
- ✅ **C6** content_dependency_index → ADR-023 + T-3.2 schema + T-3.5 trace 写入 + T-3.7 反向 propagate
- ✅ **U-CL-1** 完成标志质量门槛 → §1 v1.0 阈值表（0 critical validator failures + [A] ≥ 60% pilot + Wilson CI + Y=10 场景/周）
- ✅ **U-CL-5** 长对话一致性缓解 → ADR-024 + T-3.3（C 起步 + token metrics）+ ADR-023 hook（A/B 留）
- ✅ **U-GPT-7** 审阅 UI 含图视图 → ADR-025 + T-3.6a + T-3.6b（5 视图齐全 + mermaid fallback + browser smoke mandatory）

### 4.2 HANDOFF v0.1 + STAGE_2_ACCEPTANCE 引入的额外起手项

- ✅ **C5 OPEN_SOURCE_CARVE_OUT_INDEX v0.2 增量** → T-3.11
- ✅ **R2-5 dimensions schema 修 + AI judge vs 作者 kappa（F18）** → T-3.0 / T-3.4 mini calibration
- ✅ **R2-iter-逃逸 prompt 调优** → T-3.0
- ✅ **R2-10c 预飞 balance/health probe** → T-3.0
- ✅ **审美层 [A]/[R]/[S] 激活** → T-3.10 实测期作者使用 review_ui + scene_review_cli 双轨标
- ⏸ **X4 ADR-020 v0.2 修订** → 未来 X 级元任务（作者另起 L1 修订会话；不阻塞）

---

## 5. R3.X follow-up 候选清单（v1.0 起步）

| 编号 | 内容 | 性质 | 状态 | 来源 |
|---|---|---|---|---|
| **R3.0** | scene_ai_judge dimensions schema 修（阶段 2 R2-5 推进）| prompt + dimensions schema 一致性 | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.1** | iter07/iter09/iter11 模型 json 模式逃逸 prompt 调优（阶段 2 R2-iter-逃逸）| prompt 调优 | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.2** | scene_experiment 预飞 balance/health probe（阶段 2 R2-10c）| 工作流 ergonomic | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.3** | AI judge vs 作者 [A]/[R]/[S] kappa mini calibration（3-5 baseline_011 场景）| 评测对齐 | ⏳ T-3.0 或 T-3.4 起手并入 | F18 + HANDOFF L45 |
| **R3.X** | （阶段 3 实测产生的反向修复任务；编号 R3.4+）| 待定 | （v1.0 留空，阶段 3 跑批生成）| baseline_NNN / playtest_NNN finding |

---

## 6. 工作 wave 与依赖图（v1.0 修订；F12 / F13 / F6 整合）

```
Wave 0（独立可并行；不阻塞下游）:
   T-3.0    [A]   起手清理 PATCH（R3.0/3.1/3.2 阶段 2 三遗留 + R3.3 mini calibration 并入）
   T-3.11   [A]   开源剥离边界清单 v0.2 增量（C5）
   T-3.8a   [A]   version_recorder.py 独立模块（F12 修订；与 batch_scheduler 解耦）
   ↓ 不阻塞下游

Wave 1（串行关键路径起点）:
   T-3.1    [B]   ADR-022 ~ 026 立项（5 条 ADR 一次性 commit）
   ↓ PR merge 后 Wave 2 才能启动 A 阶段

Wave 2（串行关键路径）:
   T-3.2    [B]   content_dependency_index sidecar schema（依赖 T-3.1 ADR-023；F15 schema 字段约束加严）
   ↓ PR merge 后 Wave 3 才能启动

Wave 3（A 类可并行）:
   T-3.3    [A]   长对话一致性 C 起步（SceneGraphContext 注入 prior_scene_summaries；F3 修订）
   T-3.4    [A]   playtest bots 框架（5 persona / 20 paths / worst-10% + calibration run + severity taxonomy + run_manifest）
   T-3.7    [A]   一致性维护（基于 dep_index trace 反向 propagate；依赖 T-3.2）
   T-3.9    [A]   Chapter/Act 容器生成扩展（先 helper 库交付；F6 修订；T-3.5 调用）
   ↓ T-3.3 + T-3.9 PR merge 后 Wave 4 才能启动
   （T-3.4 与 T-3.5 并行；F13 修订 T-3.5 不依赖 T-3.4）

Wave 4（依赖 T-3.2 + T-3.3 + T-3.9）:
   T-3.5    [A]   批量生成调度器（asyncio + N=3 + RateLimitedProvider + SceneSpec DAG + 拓扑分层 + 写入顺序 + dep_index trace + chapter assignment 调用 + version_recorder 调用 = T-3.8b 范围）
   ↓ PR merge 后 Wave 5 才能启动

Wave 5（依赖 T-3.5）:
   T-3.6a   [A]   审阅 UI MVP（FastAPI + vanilla JS；scene list + graph + validator + [A]/[R]/[S]；mermaid fallback；浏览器 smoke mandatory；F2 + F16 + F17）
   ↓ PR merge 后 Wave 6 才能启动

Wave 6（依赖 T-3.5 + T-3.4 + T-3.6a）:
   T-3.6b   [A]   审阅 UI integrations（visual asset / playtest worst / stale / chapter；degrade if absent）
   ↓ PR merge 后 Wave 7 才能启动

Wave 7（实测期；A 阶段实测；不走完整 ABC，只走"实测 + 验收报告"）:
   T-3.10   [A]   完成标志实测（作者跑一周 ≥ 10 场景；0 critical + [A] ≥ 60% + Wilson CI + 场景集声明依赖图；R3.X 不强制）
   ↓ PR merge 后 Wave 8 才能启动

Wave 8（验收）:
   T-3.12   [B]   阶段 3 验收报告（[B-author-gate]；跳 BC 破例第 5 类）
```

**v1.0 修订要点**：

- **T-3.5 不依赖 T-3.4**（F13）：调度器与 playtest 解耦；T-3.4 与 T-3.5 并行
- **T-3.8 拆 a/b**（F12）：T-3.8a version_recorder.py 独立 Wave 0；T-3.8b batch_scheduler hook 合并入 T-3.5（不再独立任务）
- **T-3.6 拆 a/b**（F16）：T-3.6a MVP 在 Wave 5；T-3.6b integrations 在 Wave 6
- **T-3.9 改先 helper 库交付**（F6）：T-3.9 在 Wave 3 与 T-3.3 / T-3.4 / T-3.7 并行；T-3.5 调用 T-3.9 helper（写入顺序 = write scene → assign chapter → write deps → record version）

---

## 7. 任务清单概览（14 槽位 = 11 实施 + 1 schema + 1 ADR 立项 + 1 验收）

| ID | 类型 | 名称 | 模块边界 | 依赖 | 跳 BC 破例适用 |
|---|---|---|---|---|---|
| **T-3.0** | [A-execute] | 起手清理 PATCH（R3.0/3.1/3.2 阶段 2 三遗留 + R3.3 mini calibration 并入）| `/generator/scene_ai_judge.py`、`/generator/prompts/scene/`、`/generator/scene_experiment.py`、`/generator/tests/` | 无 | ❌ 默认 ABC（F11 修订）|
| **T-3.1** | [B-author-gate] | ADR-022 ~ 026 立项（5 条 ADR 一次性 commit）| `/docs/DECISIONS.md` | 无 | ❌ 默认 ABC |
| **T-3.2** | [B-author-gate] | content_dependency_index sidecar schema（F15 字段约束加严）| `/schema/content_dependency_index.schema.json`、`/schema/tests/`、`/docs/SCHEMA_v0.3.md` 增量 | T-3.1 | ❌ 默认 ABC |
| **T-3.3** | [A-execute] | 长对话一致性 C 起步（**SceneGraphContext** 注入 `prior_scene_summaries`；F3 修订）| `/generator/context_assembler.py`（SceneGraphContext）、`/generator/scene_strategies.py`（skeleton/fill prompt 渲染段）、`/generator/prompts/scene/`、`/generator/scene_summary_writer.py`、`/generator/tests/` | T-3.1 | ❌ 默认 ABC |
| **T-3.4** | [A-execute] | playtest bots 框架（5 persona / 20 paths / worst-10% + calibration + severity + run_manifest + 双层输出）| `/generator/playtest/`、`/generator/playtest_cost_log.jsonl`、`/generator/playtest/personas/`、`/generator/tests/` | T-3.1 | ❌ 默认 ABC |
| **T-3.5** | [A-execute] | 批量生成调度器（asyncio + N=3 + RateLimitedProvider + SceneSpec DAG + 拓扑分层 + 写入顺序 + dep_index trace + chapter helper 调用 + version_recorder 调用）**= T-3.8b 范围合并**（F12）| `/generator/batch_scheduler.py`（新建）、`/generator/dep_index_writer.py`（新建）、`/generator/_rate_limit.py`（新建）、`/generator/generate_scene.py` 扩展（trace 注入 + sidecar 写入 hook）、`/generator/tests/` | T-3.2 + T-3.3 + T-3.9 | ❌ 默认 ABC |
| **T-3.6a** | [A-execute] | 审阅 UI MVP（FastAPI + vanilla HTML/JS；scene list + graph + validator + [A]/[R]/[S]；mermaid fallback；browser smoke mandatory）| `/tools/review_ui/`（新建）、`/tools/review_ui/static/`、`/tools/review_ui/tests/`、**`/pyproject.toml`（fastapi + uvicorn deps + tools package 注册；F2）** | T-3.5 | ❌ 默认 ABC（前端 ergonomic 改进跳 BC 适用第 4 类）|
| **T-3.6b** | [A-execute] | 审阅 UI integrations（visual asset / playtest worst / stale / chapter；degrade if absent）| `/tools/review_ui/api.py`、`/tools/review_ui/static/app.js`、`/tools/review_ui/tests/` | T-3.5 + T-3.4 + T-3.6a | ❌ 默认 ABC（同上）|
| **T-3.7** | [A-execute] | 一致性维护（本体变更反向 propagate 基于 dep_index trace）| `/tools/dep_propagate.py`（新建）、`/tools/tests/`、**`/pyproject.toml`（如 T-3.6a 未先注册 tools package 则本任务负责）** | T-3.2 | ❌ 默认 ABC |
| **T-3.8a** | [A-execute] | version_recorder.py 独立模块（F12 修订；与 batch_scheduler 解耦）| `/generator/version_recorder.py`（新建）、`/generator/tests/` | 无（Wave 0 并行）| ❌ 默认 ABC |
| **T-3.9** | [A-execute] | Chapter/Act 容器生成 helper 库（F6 修订；T-3.5 调用）| `/generator/chapter_assembler.py`（新建）、`/generator/tests/` | T-3.1 | ❌ 默认 ABC |
| **T-3.10** | [A-execute] | 完成标志实测（作者跑一周 ≥ 10 场景；0 critical + [A] ≥ 60% Wilson CI；F19 R3.X 不强制）| 跑批次 + 写实测报告（不动代码）；场景集声明依赖图（F4）| T-3.5 + T-3.6a + T-3.6b + T-3.4 | ✅ 第 5 类近亲（实测报告作者签字）|
| **T-3.11** | [A-execute] | 开源剥离边界清单 v0.2 增量（C5）| `/docs/OPEN_SOURCE_CARVE_OUT_INDEX.md` | 无 | ❌ 默认 ABC |
| **T-3.12** | [B-author-gate] | 阶段 3 验收报告 | `/docs/STAGE_3_ACCEPTANCE.md`（新建）、`/docs/HANDOFF_STAGE_3_TO_4.md`（新建）| T-3.10 | ✅ 第 5 类（验收报告）|

**任务总数**：**14 条编号槽位** = 11 个 paste-ready prompt（T-3.0/3.3/3.4/3.5/3.6a/3.6b/3.7/3.8a/3.9/3.10/3.11）+ T-3.1 ADR 立项 + T-3.2 schema + T-3.12 验收报告。

> **注**：T-3.8b 不单独编号——其范围（batch_scheduler hook 写入 version sidecar）合并入 T-3.5（详 §6 wave 4 + §8 T-3.5 prompt）。

---

## 8. T-3.0 ~ T-3.12 paste-ready 执行会话 prompt

> 每条 prompt 是**自包含的可直接复制到新执行会话首条消息**。作者按 wave 顺序开 Claude Code 执行会话，从下方对应任务直接复制 ` ```text` 代码块全文作为首条消息。
>
> **v1.0 注**：所有 prompt 内 "读 v0.1 草稿"自引用全部替换为引用本文件 `/docs/STAGE_3_TASKS.md`（F1 v1.0 整合常规修订）。

### T-3.0 ｜ 起手清理 PATCH（R3.0/3.1/3.2 阶段 2 三遗留 + R3.3 mini calibration 并入）｜ [A-execute]

```text
你的任务是落地阶段 3 起手清理 PATCH，处理阶段 2 收官期遗留的 R2-5 / R2-iter-逃逸 / R2-10c 三项（在 STAGE_3_TASKS §5 已升格为 R3.0 / R3.1 / R3.2），以及加入 R3.3 AI judge vs 作者 [A]/[R]/[S] kappa mini calibration（F18 / HANDOFF_STAGE_2_TO_3 §R2-5 要求）。

# 任务类型：[A-execute]
- 纯执行；改 generator 内 prompt + AI 判官 dimensions schema + 预飞 probe + mini calibration runner；不动 schema / ADR / SCHEMA_v0*.md / L1 文档
- A 阶段：commit + push + 开 PR（base=main，head=本 worktree 分支名）
- routine 串行 OK——本任务不阻塞下游

# 跳 BC 破例适用性
本任务**默认走完整 ABC**（F11 修订；T-3.0 是阶段 3 主线起手任务，不是 R3.X follow-up；§1.5.4 跳 BC 破例 5 类不适用本任务）。

# 模块边界（硬性）
允许修改：
  - /generator/scene_ai_judge.py（R3.0：dimensions schema 修）
  - /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md（R3.0：dimensions 段同步）
  - /generator/prompts/scene/system.py 或对应 prompt 文件（R3.1：iter07/iter09/iter11 json 模式逃逸调优）
  - /generator/scene_experiment.py（R3.2：预飞 balance/health probe）
  - /generator/judge_calibration.py（**新建**；R3.3 mini calibration runner + report）
  - /generator/tests/

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py、/generator/llm_provider.py、/generator/budget.py、任何 ADR / L1 文档

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/STAGE_3_TASKS.md（本文件；§5 R3.X 候选清单）
- /docs/STAGE_2_ACCEPTANCE.md §4（R2-5 / R2-iter-逃逸 / R2-10c 根因 + 实测 finding）
- /docs/HANDOFF_STAGE_2_TO_3.md（§"阶段 2 收尾时的架构遗留 R2-*" 表 — R2-5 与 AI judge vs 作者 kappa 校准合并做要求）
- /generator/scene_ai_judge.py 当前实现
- /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md 当前 prompt
- /generator/scene_review_cli.py（理解 review_log.jsonl 接口；R3.3 mini calibration 复用此接口对齐作者 [A]/[R]/[S]）
- 检查 baseline_011 advisory 报告（generator/experiments/20260506T113419Z_baseline_011/）—— iter07/09/11 json 逃逸单点 + dimensions 全空 bug + AI judge advisory 实测痕迹

# R3.0：scene_ai_judge dimensions dict 全空修复

# 背景
baseline_007~011 全 batch 实测 AI 判官 advisory 报告每场景显示 `(no dimensions returned)`——dimensions dict 全空。root cause 推测是 prompt 模板与 dimensions schema 不一致（prompt 要求模型输出 21 维度 + 6-10 场景级维度，但 dimensions schema / parser 期望的字段名 / 结构不匹配，导致 parse 失败但不报错，dimensions dict 空过）。

# 待落地点
1. 检查 /generator/scene_ai_judge.py 中 dimensions schema 定义（pydantic / typed dict）与 /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md 中 prompt 要求模型输出的字段名 / 结构是否一致——大概率不一致
2. 修 dimensions schema OR 修 prompt（取决于哪个更接近"作者期望的 21+10 维度"）；优先以 prompt 为真相之源
3. 加 strict parse + 失败时 logging.warning（不抛异常）
4. 在 /generator/tests/ 加单元测试：模拟一份 21+10 维度 LLM 响应 → parser 正确返回 dimensions dict 含全部 31 字段
5. 在 baseline_011 任意 1 个 success iter 的 raw judge 响应（如有保留）上做 retro 校验：parser 能正确返回非空 dimensions dict

# R3.1：iter07/iter09/iter11 模型 json 模式逃逸 prompt 调优

# 背景
baseline_010/011 实测 advisory 中部分 iter（07/09/11）出现"模型在 json 模式下输出非 json 内容"现象——schema sanitizer 容忍后过 schema 校验，但 advisory 评分受影响（marginal accept 1 张）。

# 待落地点
6. 检查 /generator/prompts/scene/ 下 fill prompt 的 "你必须只输出 json" 类指令措辞——大概率指令偏弱
7. 加硬指令措辞如："输出必须是 valid json，不得包含任何解释 / 注释 / markdown code fence / 自然语言开场白；输出第一个字符必须是 `{` 或 `[`，最后一个字符必须是 `}` 或 `]`"
8. 不动 fill prompt 的核心生成指令；仅强化 json-only 输出指令
9. 在 /generator/tests/ 加测试：mock prompt rendering → 检查输出含上述硬指令片段

# R3.2：scene_experiment 预飞 balance/health probe

# 背景
baseline_008 实测踩 PoloAI 余额闸门 short-circuit（403 insufficient_user_quota；整个 batch 0% gross_pass，浪费 ~$0.30）。

# 待落地点
10. 在 /generator/scene_experiment.py 启动 batch run 前加预飞 probe：
    - 用 1 次 minimal LLM call 验证 PoloAI / Gemini 账户可用 + 余额非 0
    - 失败时 abort 整个 batch + 清晰错误消息 + exit code != 0
11. 加 env / CLI flag `--skip-probe` 让作者跳过
12. 在 /generator/tests/ 加单元测试：mock provider call → probe 检查行为 / abort 路径正确

# R3.3：AI judge vs 作者 [A]/[R]/[S] kappa mini calibration（v1.0 新增；F18）

# 背景
HANDOFF_STAGE_2_TO_3 §R2-5 明示阶段 3 起手期 R2-5 应与 AI 判官 vs 作者 kappa 校准合并做。阶段 3 又让 LLM judge 承担 playtest worst-10% / critical gate（T-3.4 / ADR-022），这个校准缺口风险更大。本任务做 mini calibration（不追求正式 kappa；目标是报告 disagreement）。

# 待落地点
13. /generator/judge_calibration.py（**新建**）：
    - 输入：3-5 个 baseline_011 success 场景 + 作者已标 [A]/[R]/[S]（通过 scene_review_cli 落 review_log.jsonl）
    - 处理：对相同场景跑 AI judge（21 节点维度 + 10 场景维度），输出 judge_score
    - 对比：判定 AI judge "[A] threshold"（如总分 ≥ 30/42 算 [A]）vs 作者实际 [A]/[R]/[S]
    - 输出：disagreement_report.md（每个场景的 AI 判官 score + 作者标 + 是否一致 + reason）
14. CLI 入口：`python -m generator.judge_calibration --scenes <id1>,<id2>,<id3> [--baseline-dir <path>] [--report <md_path>]`
15. 不必计算正式 Cohen's kappa——目标是产出 disagreement_report.md 让作者了解 AI judge 偏差形态；阶段 3 末期实测后再视需要正式化 kappa
16. /generator/tests/ 加单元测试：mock 3 个场景 + mock judge response → calibration runner 输出 disagreement_report 格式正确

# 不要做的事
- 不要扩展 /schema/（CLAUDE.md 规则 2）
- 不要改 GeminiProvider / PoloAIProvider 内部
- 不要碰 budget.py
- 不要在此任务里实现 R3.X (X≥4) follow-up（playtest_NNN finding 在阶段 3 中段才会产生）
- 不要在此任务里跑 baseline batch（实测在 T-3.10）
- 不要重写 generate_scene 主流程
- **特别**：不要把"AI 判官完全改用 reasoning trace 而非 dimensions JSON"——那是阶段 4 审美层评估范畴

# 测试
- pytest /generator/tests/ 全过
- 必含 R3.0 / R3.1 / R3.2 / R3.3 各自单元测试
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 R3.0 / R3.1 / R3.2 / R3.3 四段分别说明）
- 跑了哪些测试
- commit message: `fix(generator): R3.0 R3.1 R3.2 R3.3 cleanup gate for Stage 3 (T-3.0)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）
- B 阶段：作者另起 Codex 会话；用 /docs/REVIEW_PROMPT_CODE_GPT.md 作模板 review；report 落 /docs/reviews/<ISO_DATE>_T-3.0_<topic>_review.md
- C 阶段：作者另起 Claude Code 会话吃报告改代码 + 追加 commit
- L2 验收过关后 merge
```

### T-3.1 ｜ ADR-022 ~ ADR-026 立项（5 条 ADR 一次性 commit）｜ [B-author-gate]

```text
你的任务是把阶段 3 的 5 条架构决策一次性写入 /docs/DECISIONS.md。
作者已通过 2026-05-08 L2 整合规划师会话 + GPT-5.5 cross-LLM critique round 2 + 三议题拍板（F1 / F2 / F8）明确授权（CLAUDE.md 规则 10 例外）——属"批量立 ADR"先例延续，参考 commit `1d2030f`（ADR-011/012/013 一次性 3 条）+ commit `df05431`（ADR-016 ~ ADR-021 一次性 6 条）。

# 任务类型：[B-author-gate]
- 修改 L1 架构文档；CLAUDE.md 规则 10 例外
- A 阶段：commit + push + 开 PR；B/C 阶段作者会更仔细审 PR diff（毕竟动 ADR）；过 ABC + L2 验收后 merge
- 下游依赖任务（T-3.2 / T-3.3 / T-3.4 / T-3.5 / T-3.6 / T-3.7）的 A 阶段需等本 PR merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——立 ADR 是 [B-author-gate] 高敏感任务。

# 模块边界（硬性）
只允许修改：/docs/DECISIONS.md
严禁修改：CLAUDE.md / SCHEMA_v0*.md / DEBATE_NOTES.md / ROADMAP.md / 任何 /schema/ 文件 / 任何 /state/ 文件 / 任何代码

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md 全 21 条 ADR（理解格式 + 编号约定 + ADR-016~021 阶段 2 一次性立项先例）
- **/docs/STAGE_3_TASKS.md §3.1 ~ §3.5（本文件 ADR-022~026 决策核心 v1.0 全文；本任务直接照此落地，不再重新设计）**
- /docs/STAGE_3_TASKS.md §2.1 D1~D10 决策表（v1.0 修订要点）
- /docs/HANDOFF_STAGE_2_TO_3.md
- /docs/STAGE_2_ACCEPTANCE.md §5
- /docs/reviews/master_plan/2026-04-30_synthesis.md §7
- /docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md §5 + §7
- /docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md（理解 v1.0 修订来源 + 作者拍板逻辑）

# 5 条 ADR 落地清单（v1.0 修订；引用 STAGE_3_TASKS §3）

按 /docs/DECISIONS.md 现有格式（背景 / 决策 / 替代方案及否决理由 / 后果 / 状态）落地。每条 ADR 字数控制在 ≤ 100 行（与 ADR-016~021 体量对齐）。

## ADR-022：playtest bots 完成标志阈值（含 calibration / severity / 双层输出）
- **状态**：已接受（2026-05-XX，按 commit 实际日期填）
- **背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 C2——ADR-009 第三层 playtest bots 必须在阶段 3 完成标志里；GPT-5.5 critique F9 + F10 + F20 + F21 修订要点：calibration run 必做 / critical severity taxonomy / run_manifest / 双层输出
- **决策**：见 [STAGE_3_TASKS.md §3.1](STAGE_3_TASKS.md#31-adr-022-决策核心--playtest-bots-完成标志阈值v10)（N=5 / M=20 / 至少 5 场景 + calibration run + 三重 guard + critical/major/minor severity taxonomy + 双层 worst_paths.jsonl + worst_scenes.md/json + run_manifest.json）
- **替代方案及否决理由**：完全 fixture / 完全 LLM 生成 / N=10×M=50 大体量 / 无 calibration（F9 critique）/ 无 severity rubric（F10 critique）
- **后果**：T-3.4 落地 /generator/playtest/；playtest cost log 独立；阶段 3 末期实测如不足以暴露 worst-bucket 由 ADR-022 v0.2 修订倒推

## ADR-023：content_dependency_index sidecar 形态 + 字段集（含 trace 语义 + schema 约束加严）
- **状态**：已接受（2026-05-XX）
- **背景**：synthesis §7 + ROADMAP §阶段 3 强化项 C6；GPT-5.5 critique F5 修订核心：dep_index 不能从 scene 反推，必须 context assembly trace；F15 修订：schema 字段约束加严
- **决策**：见 [STAGE_3_TASKS.md §3.2](STAGE_3_TASKS.md#32-adr-023-决策核心--content_dependency_index-sidecar-形态v10)（per-scene sidecar `<scene>.deps.json` / **写入语义 = context assembly over-approx trace** / schema 字段约束加严：state path namespace pattern / uniqueItems / scene_id pattern 与 dialogue_graph.graph_id 对齐 / optional missing-only / scene_history_referenced 字段 = D4 hook）
- **替代方案及否决理由**：scene 反查（F5 critique 否决）/ 全局索引 / SQLite / schema 约束太松（F15 critique 否决）
- **后果**：T-3.2 schema 落地；T-3.5 generate_scene hook 写 sidecar（context trace 形态）；T-3.7 一致性维护按 sidecar 反向 propagate

## ADR-024：长对话一致性 C 起步 + A/B hook（含 token metrics + SceneGraphContext）
- **状态**：已接受（2026-05-XX）
- **背景**：DEBATE §9.2 长对话一致性列为未解问题；ROADMAP §阶段 3 强化项 U-CL-5；PZ §7 作者态度（不预防性设计 + 50-100 场景可能不撞真墙）；GPT-5.5 critique F3 修订：必须改 SceneGraphContext 不是 GraphContext
- **决策**：见 [STAGE_3_TASKS.md §3.3](STAGE_3_TASKS.md#33-adr-024-决策核心--长对话一致性-c-起步--ab-hookv10)（C 起步全套：prompt SceneGraphContext 注入 prior_scene_summaries + token/prompt metrics hook 每 scene 记 prompt token estimate / summaries injected count / summary source hashes / truncation reason；A/B hook 留 content_dependency_index.scene_history_referenced 字段；不在阶段 3 落地 A=memory stream / B=RAG event log）
- **替代方案及否决理由**：完整 D hybrid (A+C) / 不立 ADR / 改 GraphContext（F3 critique 否决；GraphContext 是节点级，scene 级生成根本拿不到）
- **后果**：T-3.3 落地 SceneGraphContext + prompt 模板 + scene_summary_writer；阶段 3 实测 token 累积曲线 + 接受率回归是否撞墙作 ADR-024 v0.2 修订依据

## ADR-025：审阅 UI 架构（含 pyproject deps + 拆 a/b + mermaid fallback）
- **状态**：已接受（2026-05-XX）
- **背景**：synthesis §7 + ROADMAP §阶段 3 强化项 U-GPT-7；GPT-5.5 critique F2 + F16 + F17 修订要点：模块边界必须含 pyproject.toml（FastAPI deps + tools package 注册）/ 拆 a (MVP) + b (integrations) / mermaid CDN fallback
- **决策**：见 [STAGE_3_TASKS.md §3.4](STAGE_3_TASKS.md#34-adr-025-决策核心--审阅-ui-架构v10f2--f16--f17-修订)（Web 单页 / FastAPI + uvicorn deps + tools package 注册 pyproject.toml / 前端 vanilla HTML/JS / mermaid.js CDN with vendor bundle fallback / T-3.6a MVP + T-3.6b integrations 拆 / 浏览器 smoke / 截图 / mermaid 渲染检查 mandatory / read-only / env FORGEWRIGHT_REVIEW_UI_PORT 默认 8765）
- **替代方案及否决理由**：CLI 升级 / 桌面应用 / 不动 pyproject（F2 critique 否决；执行会话无法合法落地）/ React/Vue/Svelte（开源门槛上升）/ 单 T-3.6 任务范围过宽（F16 critique 否决；浏览器 smoke 也变 mandatory）/ 仅 CDN 不带 fallback（F17 critique 否决）
- **后果**：T-3.6a + T-3.6b 落地 /tools/review_ui/；复用 T-2.8 graph_views 三件套作 graph 视图数据源

## ADR-026：批量调度器并发模型（含 SceneSpec DAG + RateLimitedProvider）
- **状态**：已接受（2026-05-XX）
- **背景**：ROADMAP §阶段 3 完成标志要求批量生成调度器；阶段 2 baseline_011 单 iter mean 268s 实测；GPT-5.5 critique F4 + F13 + F14 修订要点：N=3 并发与 prior_scene_summaries 顺序冲突 / T-3.5 不应依赖 T-3.4 / RateLimitedProvider wrapper 必须明示
- **决策**：见 [STAGE_3_TASKS.md §3.5](STAGE_3_TASKS.md#35-adr-026-决策核心--批量调度器并发模型v10f4--f13--f14-修订)（asyncio + N=3 concurrent / SceneSpec 加 depends_on_scene_ids / sequence_group / prior_summary_paths / 拓扑分层调度（同层并发，不同层串行）/ RateLimitedProvider(LLMProvider) wrapper / 写入顺序 write scene → assign chapter → write deps → record version / T-3.5 不依赖 T-3.4）
- **替代方案及否决理由**：串行 N=1 / N=10 撞 PoloAI 速率限制 / subprocess fan-out / flat queue 无 DAG（F4 critique 否决）/ T-3.5 hard depend T-3.4（F13 critique 否决；调度器和 playtest 解耦）/ 仅外层限速（F14 critique 否决；内部 provider call 不受限）
- **后果**：T-3.5 落地 /generator/batch_scheduler.py；阶段 3 实测如撞 PoloAI 余额闸门作者降 N=1/2 应急；阶段 3 末期 ADR-026 v0.2 修订倒推真实最优 N

# 立项规则（共通）
- 状态行 = "已接受（2026-05-XX）" — 实际日期填写为本任务 commit 当日
- 后果行明示哪些下游 L3 任务依赖本 ADR（T-3.2 / T-3.3 / T-3.4 / T-3.5 / T-3.6 / T-3.7）
- 末尾在 /docs/DECISIONS.md "变更历史" 段追加：
  ```
  - 2026-05-XX：作者明确授权新增 ADR-022 / 023 / 024 / 025 / 026（阶段 3 五条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_3_TASKS.md v1.0（含 GPT-5.5 cross-LLM critique 22 finding + Claude round 2 response + 作者 2026-05-08 三议题拍板 F1/F2/F8）。L2 整合规划师会话（claude/sweet-bardeen-863720）2026-05-08 L1-L2 校准产物。
  ```

# 不要做的事
- 不要修改 SCHEMA_v0*.md（那是 T-3.2 范围）
- 不要修改任何 /schema/ 文件
- 不要修改任何代码
- 不要碰 ROADMAP.md 阶段 3 完成标志措辞——X7 跨边界（作者另起 L1 修订会话）
- 不要在 ADR 内写"如何实现"的代码细节（ADR 是 what + why + 后果，不是 how）
- 不要超过 5 条 ADR 范围

# A 阶段完成标志
- /docs/DECISIONS.md 的 diff 摘要（按 ADR 分段）
- 5 条 ADR 各自字数（建议每条 ≤ 100 行）
- commit message：`docs: add ADR-022/023/024/025/026 for Stage 3 (T-3.1)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.1_adr_022-026_review.md
- C 阶段：吃报告改 ADR + 追加 commit
- L2 验收过关后 merge；下游依赖任务（T-3.2 / T-3.3 / T-3.4 / T-3.5 / T-3.6 / T-3.7）启动依赖本 PR merge
```

### T-3.2 ｜ content_dependency_index sidecar schema（F15 字段约束加严）｜ [B-author-gate]

```text
你的任务是为 content_dependency_index sidecar 落地正式 JSON Schema，并新增对应文档章节。这是 ADR-023 落地的硬依赖任务——T-3.5 批量调度器会按本 schema 写 sidecar（context assembly trace 形态；F5 修订），T-3.7 一致性维护按 schema 反向 propagate。**v1.0 修订要点**：F15 字段约束加严 — 加 ADR-016 五命名空间 pattern + uniqueItems + scene_id pattern 与 dialogue_graph.graph_id 对齐 + optional missing-only。

# 任务类型：[B-author-gate]
- 动 schema = 高敏感任务；CLAUDE.md 规则 2 + 9 例外（作者已通过 2026-05-08 L2 整合规划师会话明示授权）
- A 阶段：commit + push + 开 PR；B/C 阶段作者会更仔细审 PR diff
- 必须严格依赖 T-3.1 ADR-023 已 merge 后才能启动 A 阶段（schema commit 串行卡口）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——schema 修改 [B-author-gate] 高敏感。

# 模块边界（硬性）
允许修改：
  - /schema/content_dependency_index.schema.json（**新建**；首版 const `schema_version: "0.3.0"`，与 character/location/clock/chapter schema 同源演进语义；详 ADR-016 §schema 版本号策略）
  - /schema/tests/（新建 test_content_dependency_index.py 或加入现有测试套件）
  - /docs/SCHEMA_v0.3.md（追加新章节"content_dependency_index sidecar schema"）— **F22 修订：v1.0 拍板追加 SCHEMA_v0.3.md，不新建 SCHEMA_v0.4.md**

严禁修改：
  - 任何既有 /schema/*.schema.json — ADR-023 不动既有 schema
  - /docs/DECISIONS.md（除 ADR-023 已由 T-3.1 立项；本任务不动 ADR）
  - CLAUDE.md / DEBATE_NOTES.md / ROADMAP.md
  - /state/ontology/（不动现有 ontology 数据；sidecar 是阶段 3 新增机制）
  - /generator/ /validator/ /engine/（任何代码）

# 必读
- /CLAUDE.md（规则 1-10，特别 2/9）
- /docs/DECISIONS.md ADR-023（T-3.1 已立项；本任务依赖；含 context assembly trace 写入语义说明）
- /docs/STAGE_3_TASKS.md §3.2 ADR-023 决策核心 + §2.1 D2 + §2.4 跨任务一致性细节
- /docs/SCHEMA_v0.3.md（阶段 2 ontology 模块文档；理解格式 + 语义；本任务追加章节体例对齐）
- /schema/character.schema.json + /schema/location.schema.json + /schema/clock.schema.json + /schema/chapter.schema.json（参考阶段 2 新建 schema 文件结构格式 + const `0.3.0` 落地方式）
- /schema/dialogue_graph.schema.json（理解 `graph_id` pattern；本任务 scene_id 与之对齐 — F15 修订）
- /docs/DECISIONS.md ADR-016 §state path 命名空间表（五命名空间：world.* / faction.* / relationship.* / flag.* / player.*；本任务 state_paths_read/write 字段加 pattern 约束 — F15 修订）

# Schema 字段集（v1.0 修订；含 F15 字段约束加严）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://forgewright.dev/schema/content_dependency_index.schema.json",
  "title": "ContentDependencyIndex",
  "description": "Sidecar metadata recording content generation dependencies. Per-scene file <scene>.deps.json colocated with scene.json. Written via context assembly over-approx trace (ADR-023; not output reverse inference).",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "0.3.0"
    },
    "scene_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "description": "Aligned with dialogue_graph.graph_id pattern (F15)"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time"
    },
    "ontology_ids_read": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true,
      "description": "All ontology entity ids referenced during generation (char_*, scene_*, loc_*, clk_*, chap_*); from context assembly trace not scene reverse"
    },
    "state_paths_read": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^(world|faction\\.[a-z0-9_]+|relationship\\.[a-z0-9_]+|flag|player)(\\.[a-z0-9_]+)*$",
        "description": "Must fall in ADR-016 namespace (F15)"
      },
      "uniqueItems": true
    },
    "state_paths_written": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^(world|faction\\.[a-z0-9_]+|relationship\\.[a-z0-9_]+|flag|player)(\\.[a-z0-9_]+)*$"
      },
      "uniqueItems": true
    },
    "prompt_template_hash": {
      "type": "string",
      "pattern": "^sha256:[a-f0-9]{64}$"
    },
    "visual_asset_ids_referenced": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "clock_ids_referenced": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "chapter_id": {
      "type": "string",
      "pattern": "^chap_[a-z0-9_]+$",
      "description": "F15: optional missing-only (key absent if scene not assigned to chapter); not null"
    },
    "act_id": {
      "type": "string",
      "pattern": "^act[a-z0-9_]*$"
    },
    "scene_history_referenced": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9_]*$"
      },
      "uniqueItems": true,
      "description": "ADR-024 long-conversation hook: prior scene ids whose summaries were injected into prompt context"
    },
    "prompt_token_estimate": {
      "type": "integer",
      "minimum": 0,
      "description": "ADR-024 token metrics hook (v1.0): estimated total prompt tokens at generation time"
    },
    "summaries_injected_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5,
      "description": "Actual prior_scene_summaries count injected (0-5 per ADR-024 upper bound)"
    },
    "summary_source_hashes": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^sha256:[a-f0-9]{64}$"
      },
      "uniqueItems": true
    },
    "truncation_reason": {
      "type": "string",
      "enum": ["none", "summaries_over_5", "token_budget", "manual_override"]
    }
  },
  "required": [
    "schema_version", "scene_id", "generated_at",
    "ontology_ids_read", "state_paths_read", "state_paths_written",
    "prompt_template_hash"
  ],
  "additionalProperties": false
}
```

# 待落地点
1. 新建 /schema/content_dependency_index.schema.json — 按上述字段集；`additionalProperties: false`；required 段含必填核心字段；optional 字段（chapter_id / act_id / visual_asset_ids_referenced / clock_ids_referenced / scene_history_referenced / prompt_token_estimate / summaries_injected_count / summary_source_hashes / truncation_reason）允许 missing 但**不允许 null**（F15 修订；明示 missing-only）
2. 新建 schema 测试 — 至少 8 case（v1.0 扩展）：
   - 有效 sidecar（全字段填）→ pass
   - 有效 sidecar（仅 required 字段，optional 全省）→ pass
   - schema_version 错（如 "0.4.0"）→ fail
   - prompt_template_hash 格式错（如缺 "sha256:" 前缀）→ fail
   - **state_paths_read 含非五命名空间路径（如 `invalid.foo`）→ fail（F15 新增）**
   - **state_paths_written 含重复元素（uniqueItems 违反）→ fail（F15 新增）**
   - **scene_id pattern 错（如大写字母 `MyScene`）→ fail（F15 新增）**
   - **summaries_injected_count = 6（超 ≤ 5 上限）→ fail（v1.0 新增 token metrics 字段）**
3. 在 /docs/SCHEMA_v0.3.md 追加新章节（**§N. content_dependency_index sidecar schema**）— 含字段语义、context assembly trace 写入语义说明、与 ontology / dialogue_graph schema 的关系、写入时机说明、ADR-023 + ADR-024 引用、token metrics 字段说明（F22 + ADR-024 token hook）；与既有 chapter / clock 章节同 prose 风格
4. 不动既有 schema 文件——验证 /content/test_scene_v0/ 现有 gold scene 仍 pass 全部既有 schema

# 不要做的事
- 不要 bump 既有 schema 文件 const（ADR-016 §schema 版本号策略）
- 不要在 /content/ 下立刻为 gold scene 写 sidecar（sidecar 写入是 T-3.5 调度器范围；本任务仅交付 schema + 文档）
- 不要把 sidecar 字段做成 dialogue_graph schema 的 nested 字段
- 不要做 schema 校验工具 / migrate 脚本（T-3.5 / T-3.7 范围）
- 不要碰 /generator/ /validator/ /engine/

# 测试
- pytest /schema/tests/ 全过（含本任务新增测试）
- 跑 /review skill + validate-all
- 验证 /content/test_scene_v0/scene.json 仍 pass dialogue_graph 0.1.1 schema

# A 阶段完成标志
- /schema/content_dependency_index.schema.json 内容
- /schema/tests/ 新增测试 + pytest 输出
- /docs/SCHEMA_v0.3.md 新增章节 diff
- commit message: `feat(schema): add content_dependency_index sidecar schema (T-3.2; ADR-023 + F15)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.2_sidecar_schema_review.md
- C 阶段：吃报告改 schema + 追加 commit
- L2 验收过关后 merge；下游 T-3.5 / T-3.7 启动依赖本 PR merge
```

### T-3.3 ｜ 长对话一致性 C 起步（SceneGraphContext 注入 prior_scene_summaries；F3 修订）｜ [A-execute]

```text
你的任务是落地 ADR-024 长对话一致性 C 起步——在 generator prompt 模板的 **SceneGraphContext** 中注入 `prior_scene_summaries` 字段（**v1.0 F3 修订**：必须改 SceneGraphContext 而非 GraphContext；后者是节点级 B+ context，scene 级生成不使用），并支持作者人工填 + 半自动 LLM 摘要 + 作者校准两条路并存。

# 任务类型：[A-execute]
- 纯执行；改 SceneGraphContext + scene_strategies + prompt 模板；不动 schema / ADR / L1 文档
- 必须依赖 T-3.1 ADR-024 已 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 prompt 模板 + context 字段扩展不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/context_assembler.py（**SceneGraphContext** dataclass 新增 prior_scene_summaries 字段；不动 GraphContext 节点级 context）
  - /generator/scene_strategies.py（skeleton / fill scene prompt 渲染段加 prior_scene_summaries context section）
  - /generator/prompts/scene/（prompt 模板支持 prior_scene_summaries 注入）
  - /generator/scene_summary_writer.py（**新建**；半自动 LLM 摘要工具）
  - /generator/tests/

严禁修改：
  - /schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）
  - /generator/generate_scene.py（仅可在 SceneGraphContext 实例化时填入字段；不动主流程算法）
  - /generator/llm_provider.py、/generator/budget.py
  - **不动 GraphContext 节点级 context**（F3 修订要点；阶段 3 仅 SceneGraphContext 加字段，节点级保持兼容）

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-024（T-3.1 已立项；本任务依赖）
- /docs/STAGE_3_TASKS.md §3.3 ADR-024 决策核心 + §2.4 字段命名（prior_scene_summaries / token metrics 字段）
- /docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md §5 + §7（U-CL-5 + 作者态度）
- /docs/DEBATE_NOTES.md §9.2（长对话一致性未解问题描述）
- **/generator/context_assembler.py 当前实现（重点：理解 SceneGraphContext dataclass 与 GraphContext 的层级关系；F3 修订核心—SceneGraphContext 是 scene 级，GraphContext 是节点级）**
- /generator/scene_strategies.py 当前实现（scene 级 skeleton / fill 策略）
- /generator/generate_scene.py（理解 SceneGraphContext 何处实例化）
- /generator/prompts/scene/system.py + fill prompt（理解 prompt 注入方式）

# 待落地点

## C-1：SceneGraphContext 加 prior_scene_summaries 字段（F3 修订）

1. /generator/context_assembler.py 的 **SceneGraphContext** dataclass 增加：
   ```python
   prior_scene_summaries: list[PriorSceneSummary] = field(default_factory=list)
   ```
   PriorSceneSummary 是新 dataclass：
   ```python
   @dataclass
   class PriorSceneSummary:
       scene_id: str
       summary: str  # ≤ 200 中文字符 / ≤ 800 英文字符
       key_state_paths: list[str]  # 该场景产生的关键 state_path 写入
   ```
2. 上限：每场景 prompt 注入最多 5 条 prior_scene_summaries（避免 prompt 膨胀；ADR-024 字段定义）；超过时按"最近 5 条 + 关键场景"启发式裁剪（保留 chapter_id / act_id 边界场景）
3. **GraphContext 节点级 context 不动**——F3 修订；如未来需节点级也支持作 v0.2 修订

## C-2：scene_strategies + prompt 模板支持 prior_scene_summaries context 注入

4. /generator/scene_strategies.py 的 skeleton + fill 策略：在调用 prompt 模板 render 时传入 prior_scene_summaries 字段
5. /generator/prompts/scene/system.py（或 fill prompt 文件）加 prior_scene_summaries context section（仅在 list 非空时注入）：
   ```
   # 前置场景概要（按时间顺序）
   - [scene_id_X] {summary}; 关键状态写入：{key_state_paths}
   - ...
   ```
6. fill prompt 不动主算法；仅 context section 增量
7. 测试：模拟 SceneGraphContext 含 3 条 prior_scene_summaries → 渲染后的 prompt 含上述 context section 文本片段

## C-3：半自动 LLM 摘要工具

8. /generator/scene_summary_writer.py（新建）— 接受 scene.json 路径 → 调 LLM 生成 ≤ 200 字摘要 + 提取 key_state_paths（从 scene 的 effect 集合）→ 输出 PriorSceneSummary dataclass
9. CLI 入口：`python -m generator.scene_summary_writer <scene_path>` 输出建议摘要 + 等作者编辑（或 --auto-accept 直接落 sidecar）
10. 摘要存储位置：独立 sidecar `<scene>.summary.json`（与 deps.json 平级；schema 不立，pydantic dataclass JSON 序列化即可）

## C-4：作者人工填路径

11. CLI 接受 `--manual` flag 让作者直接编辑 `<scene>.summary.json`（用 $EDITOR 打开模板）；半自动模式（默认）= LLM 起草 + 作者校准
12. 测试：mock LLM 调用 → 验证 summary_writer 路径 + dataclass 序列化正确

## C-5：token metrics hook（v1.0 新增；ADR-024 要求）

13. SceneGraphContext 实例化时（在 _build_scene_context 内）追加 token_metrics 字段：
    - `prompt_token_estimate`（注入 prompt 总 token 估算；用 tiktoken / 类似工具）
    - `summaries_injected_count`（实际注入条数 0-5）
    - `summary_source_hashes`（每条 summary 的 SHA256）
    - `truncation_reason`（如超 5 条上限被裁的 reason 枚举）
14. **本任务仅在 SceneGraphContext 准备这些字段；写入 dep_index sidecar 由 T-3.5 范围接管**（F5 修订；context assembly trace 写入语义）

# 不要做的事
- 不要扩展 /schema/（CLAUDE.md 规则 2；prior_scene_summaries 是运行时 context，不入持久 schema）
- 不要实现 RAG / embedding / Generative Agents memory stream（ADR-024 明示 A/B 不在阶段 3 落地）
- 不要在 generate_scene 主流程内自动调 summary_writer（保留作者明示触发；避免每次生成都 burn token 成本不可控）
- 不要碰 ontology 数据
- 不要在 prompt 里硬编码 prior_scene_summaries 处理逻辑（应作为 SceneGraphContext 字段，prompt 模板按字段渲染）
- **不要碰 GraphContext 节点级 context**（F3 修订；阶段 3 仅 SceneGraphContext 加字段）

# 测试
- pytest /generator/tests/ 全过
- 必含：SceneGraphContext.prior_scene_summaries 字段单元测试 / prompt 渲染 + context section 测试 / scene_summary_writer mock LLM 路径测试 / token_metrics 估算测试
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 C-1 ~ C-5 五段说明）
- pytest 输出
- commit message: `feat(generator): long-conversation consistency C-tier on SceneGraphContext (T-3.3; ADR-024; F3 fix)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.3_long_conversation_consistency_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.5 批量调度器在 SceneGraphContext 实例化时填 prior_scene_summaries + token metrics 依赖本 PR merge
```

### T-3.4 ｜ playtest bots 框架（5 persona / 20 paths / worst-10% + calibration + severity + run_manifest）｜ [A-execute]

```text
你的任务是落地 ADR-022 playtest bots 框架——为每个生成场景跑 5 个 persona × 20 paths = 100 paths，输出 worst-10% **双层报告**（worst_paths.jsonl + worst_scenes.md/json；F21 修订）+ critical/major/minor severity taxonomy 评分（F10 修订）+ playtest run_manifest 元数据（F20 修订）+ **calibration run 必做**（F9 修订；锁参前 1 scene × 1 persona × 5 paths 小跑实测 cost/calls/time）+ 三重 guard（F9 修订；`--max-cost-usd` / `--max-calls` / `--max-wall-clock-min`）。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/playtest/ 模块；不动 schema / ADR / L1 文档
- 必须依赖 T-3.1 ADR-022 已 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增不在 §1.5.4 跳 BC 破例 5 类内。后续 playtest_NNN finding（实测产生）属第 3 类跳 BC 适用。

# 模块边界（硬性）
允许修改：
  - /generator/playtest/（**新建模块目录**）
    - /generator/playtest/__init__.py
    - /generator/playtest/personas.py（persona dataclass + 库加载）
    - /generator/playtest/personas/（**新建子目录**；5 个 persona JSON）
      - cautious.json / aggressive.json / completionist.json / speedrunner.json / role_player.json
    - /generator/playtest/runner.py（playtest 跑批主流程 + calibration run）
    - /generator/playtest/judge.py（LLM-as-judge worst-10% 排序 + severity taxonomy）
    - /generator/playtest/cli.py（CLI 入口 + 三重 guard）
  - /generator/playtest_cost_log.jsonl（新建）
  - /generator/tests/test_playtest_*.py

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-022（T-3.1 已立项）+ ADR-009（评测三层；playtest bots 是第三层）+ ADR-021（§2B 抽样路径起点 sampling 框架；可复用）
- /docs/STAGE_3_TASKS.md §3.1 ADR-022 决策核心 + §2.4 字段命名 + §2.1 D1
- /validator/sampling.py（理解阶段 2 §2B 抽样路径生成器，复用其"从 entry 出发随机选 option"基础逻辑）
- /generator/scene_ai_judge.py（理解 LLM-as-judge 调用 + dimensions schema 形态；R3.0 修复后版本）
- /generator/judge_calibration.py（T-3.0 R3.3 落地的 mini calibration runner；本任务可参考其 disagreement 报告形态）

# 待落地点

## P-1：5 个 persona 库

1. 5 个 persona JSON 文件。每个文件：
   ```json
   {
     "persona_id": "cautious",
     "display_name": "谨慎玩家",
     "base_traits": ["risk-averse", "reads_all_options", "prefers_diplomacy"],
     "selection_bias": {
       "favors": ["dialogue", "deception_check", "non-violent"],
       "avoids": ["combat", "irreversible_action"]
     },
     "augmented_description": null
   }
   ```
   5 个 persona：cautious / aggressive / completionist / speedrunner / role_player（hand-write base + LLM augment hook 留 null）

## P-2：playtest runner（path 模拟）

2. /generator/playtest/runner.py：核心函数 `run_playtest(scene: DialogueGraph, persona: Persona, n_paths: int) -> list[PlaytestPath]`
   - 每 path = 从 entry_node_id 出发模拟 persona 选项至 end 节点
   - option 选择：调 LLM 让 persona 扮演 + 选 option_id（受 base_traits + selection_bias 影响）
   - 记录每 path：node_ids 序列 + option_ids 序列 + state 演化（复用 /validator/sampling.py state evaluator）
3. **复用 /validator/sampling.py 路径生成器** — 仅替换 option 选择策略（random.choice → LLM persona 决策）
4. async 实现（与 ADR-026 调度器并发模型一致）；每 path 独立一个 LLM 调用

## P-3：calibration run（v1.0 新增；F9 必做）

5. /generator/playtest/cli.py 必须支持 calibration mode：
   - flag `--calibration` 触发 1 scene × 1 persona × 5 paths 小跑
   - 输出：avg calls/path / tokens/path / seconds/path / cost/path
   - 输出 calibration_report.md：实测数据 + 推荐 max_paths（根据 cost budget / wall_clock budget 倒推）
6. **calibration run 是 A 阶段 mandatory smoke test**（不能跳过；除非显式 `--skip-calibration` flag 且作者明示）
7. 每 path 不是单次 LLM 调用——每决策节点 + judge 各一次；calibration 实测真实 calls/path 数（F9 critique 教训：v0.1 估算每 path 一次调用是低估）

## P-4：三重 guard（v1.0 新增；F9）

8. CLI flags（必须实现）：
   - `--max-cost-usd <amount>`（默认 10.0；触发 abort + log）
   - `--max-calls <n>`（默认 1000；触发 abort + log）
   - `--max-wall-clock-min <m>`（默认 30；触发 abort + log）
9. 任一触发 = abort batch + 写当前进度 + clean exit code != 0

## P-5：LLM-as-judge worst-10% 排序 + severity taxonomy（v1.0 修订；F10）

10. /generator/playtest/judge.py：每 path 跑完后调 LLM-as-judge 评估（4 维度：剧情连贯 / persona 体验 / 节奏 / 最终结局合理性）；输出 path_score（0-100）
11. **critical/major/minor severity taxonomy（v1.0 新增；F10）**：每 path 含 `severity_findings: list[{severity, description}]` 字段
    - **critical** = validator 漏掉的非法路径 / 状态因果矛盾 / 角色 / 本体直接冲突 / 玩家结果透明度严重误导
    - **major** = 显著叙事质量问题（节奏 / 风格 / 合理性）
    - **minor** = 体例 / 措辞 / 微调
12. judge prompt 必须明示 severity 定义（写进 prompt 而不是仅靠模型自然语言判断）
13. **critical 必须作者明示确认**——不能只靠 LLM judge 自动通过 gate（v1.0 完成标志要求）

## P-6：双层输出（v1.0 新增；F21）

14. 5×20=100 paths 跑完后按 path_score + critical_count 排序输出**双层**：
    - `playtest_NNN/worst_paths.jsonl`（path 级；100 行；每行含 path trace + judge_score + critical_count + severity_findings）
    - `playtest_NNN/worst_scenes.md` + `worst_scenes.json`（scene 级；scene 分数 = path 分布 / critical count / 最低分加权；含每场景 worst-10% 路径摘要 + critical issue 清单）

## P-7：run_manifest.json（v1.0 新增；F20）

15. 每 playtest_NNN 写 `playtest_NNN/run_manifest.json`：
    ```json
    {
      "playtest_id": "playtest_001",
      "started_at": "...",
      "completed_at": "...",
      "model_id": "gemini-3.1-pro-preview",
      "temperature": 0.7,
      "prompt_template_hash": "sha256:...",
      "persona_hashes": {"cautious": "sha256:...", ...},
      "judge_rubric_version": "v1",
      "calibration_data": {"avg_calls_per_path": 5.2, "avg_seconds_per_path": 13.5, "avg_cost_per_path": 0.018}
    }
    ```
16. 复盘性目标：worst-10% 后续作者 + L2 + Codex 都能基于 manifest 重现单 path

## P-8：CLI 入口

17. /generator/playtest/cli.py：命令 `python -m generator.playtest <scene_path> [--n-paths 20] [--personas all|cautious,aggressive,...] [--calibration | --skip-calibration] [--max-cost-usd 10] [--max-calls 1000] [--max-wall-clock-min 30]`
18. 输出目录：`/generator/experiments/playtest_NNN/`（与 baseline 同源命名空间但 NNN 编号独立）
19. cost_log 写入 /generator/playtest_cost_log.jsonl（独立于 cost_log.jsonl）

## P-9：成本控制 + 仪表化

20. budget 接入：复用 /generator/budget.py（每个 LLM 调用走 budget.check_and_charge）
21. 单 playtest batch 估算（calibration 后实测倒推）：100 paths/scene × ~5 calls/path × ~$0.02/call = ~$10/scene；阶段 3 实测 5 场景 = ~$50（F9 critique 修订；v0.1 估算 $10 是低估）
22. 沿用阶段 2 R2.9 ProviderError 仪表化（path 失败时记录 ProviderError + path_id + persona_id）

# 不要做的事
- 不要在 generate_scene 主流程内自动跑 playtest（playtest 是后处理步骤，作者明示触发）
- 不要硬编码 persona 描述在 Python 代码（必须 JSON 配置）
- 不要在本任务实现 LLM augmented_description 生成逻辑（hook 留 null 即可）
- 不要扩展 /schema/（playtest 是评测产物，不入持久 schema）
- 不要 fail-fast 整个 batch（单 path 失败 → log + 继续）
- 不要碰 ontology 写入（playtest read-only）
- **不要跳过 calibration**（除非作者显式 `--skip-calibration`；v1.0 mandatory）
- **不要让 LLM judge 自动通过 critical gate**（v1.0 critical 必须作者明示确认）

# 测试
- pytest /generator/tests/test_playtest_*.py 全过
- 必含：persona 加载测试 / runner mock LLM 路径测试（不真烧 API）/ judge mock + severity taxonomy 测试 / **calibration run mock 测试** / 三重 guard 触发测试 / **双层输出 + run_manifest 写入测试** / CLI 集成测试（gold scene 跑 1 path）
- 跑 /review skill + validate-all
- **小成本实证**（可选；A 阶段会话里跑 1 个 calibration run = $0.10 实证）—— 需作者明示授权 + 记 cost_log

# A 阶段完成标志
- diff 摘要（按 P-1 ~ P-9 九段说明）
- 5 个 persona JSON 文件清单
- pytest 输出
- commit message: `feat(generator): playtest bots framework with calibration + severity + manifest (T-3.4; ADR-022; F9 + F10 + F20 + F21)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.4_playtest_bots_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6b review_ui 含 playtest 视图依赖本 PR；T-3.10 实测期跑完整 playtest 依赖本 PR
```

### T-3.5 ｜ 批量生成调度器（含 T-3.8b batch_scheduler hook 范围）｜ [A-execute]

```text
你的任务是落地 ADR-026 批量生成调度器——asyncio + N=3 concurrent worker + **SceneSpec DAG 拓扑分层调度**（F4 修订）+ **RateLimitedProvider wrapper**（F14 修订）+ ontology 写入 file lock + content_dependency_index sidecar 写入 hook（**context assembly trace 形态**；F5 修订）+ **写入顺序 write scene → assign chapter → write deps → record version**（F6 修订）+ **T-3.8b 范围合并**（F12 修订；调用 record_version 公共函数）。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/batch_scheduler.py + /generator/dep_index_writer.py + /generator/_rate_limit.py + 扩展 /generator/generate_scene.py（GenerationDependencyTrace 注入 + sidecar 写入 hook 调用 + chapter_assembler 调用 + version_recorder 调用）
- **必须依赖 T-3.2（schema） + T-3.3（SceneGraphContext.prior_scene_summaries） + T-3.9（chapter_assembler helper）三 PR merge；不依赖 T-3.4（playtest 与调度器解耦；F13 修订）+ 不依赖 T-3.8a 必须先 merge 但建议同期就绪（T-3.8a Wave 0 早 merge 期望）**

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增 + generate_scene 扩展，是阶段 3 核心交付。

# 模块边界（硬性）
允许修改：
  - /generator/batch_scheduler.py（**新建**）
  - /generator/dep_index_writer.py（**新建**；context trace sidecar 写入 helper；F5）
  - /generator/_rate_limit.py（**新建**；RateLimitedProvider wrapper；F14）
  - /generator/generate_scene.py（**扩展**：context assembly 阶段累加 GenerationDependencyTrace + 主流程末尾追加写入顺序 hooks 调用——F6 顺序）
  - /generator/context_assembler.py（**扩展 SceneGraphContext + _build_scene_context 接受 trace 参数；GraphContext 节点级不动**）
  - /generator/tests/

严禁修改：/schema/、/state/、/state/ontology/（loader 不动，但调度器内 ontology 写入用 file lock；不动 ontology 数据本身）、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/llm_provider.py、/generator/budget.py、/generator/scene_strategies.py、/generator/prompts/scene/、**/generator/chapter_assembler.py（T-3.9 范围；本任务仅 import 调用）**、**/generator/version_recorder.py（T-3.8a 范围；本任务仅 import 调用 record_version 公共函数）**

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-026（T-3.1 已立项）+ ADR-023（T-3.1 已立项；context assembly trace 写入语义）+ ADR-024（T-3.1 已立项；token metrics hook）
- /docs/STAGE_3_TASKS.md §3.5 ADR-026 + §3.2 ADR-023 + §3.3 ADR-024 决策核心 + §2.4 字段命名（FORGEWRIGHT_BATCH_CONCURRENT_N / FORGEWRIGHT_PROVIDER_RPM / SceneSpec DAG / GenerationDependencyTrace / RateLimitedProvider）
- /generator/scene_experiment.py（理解阶段 2 单 batch run 模式）
- /generator/generate_scene.py（理解主流程 + SceneGraphContext 实例化点）
- /generator/context_assembler.py（理解 SceneGraphContext + _build_scene_context；T-3.3 已扩展 prior_scene_summaries）
- /generator/chapter_assembler.py（T-3.9 已落地；理解 assign_scene_to_chapter 公共函数签名）
- /generator/version_recorder.py（T-3.8a 已落地；理解 record_version 公共函数签名）
- /schema/content_dependency_index.schema.json（T-3.2 已落地）
- /docs/STAGE_2_ACCEPTANCE.md §2.1（baseline_011 单 iter mean 268s 实测数据；ADR-026 N=3 决策依据）

# 待落地点

## BS-1：SceneSpec DAG（v1.0 F4 修订核心）

1. /generator/batch_scheduler.py：SceneSpec dataclass 加字段：
   ```python
   @dataclass
   class SceneSpec:
       scene_setting: str
       target_beats: list[str]
       participating_npcs: list[str]
       chapter_id: str | None = None  # 用于 chapter_assembler 调用
       act_id: str | None = None
       depends_on_scene_ids: list[str] = field(default_factory=list)  # F4: 拓扑 DAG
       sequence_group: str | None = None  # F4: 同 group 内顺序敏感
       prior_summary_paths: list[Path] = field(default_factory=list)  # F4: 注入 prior_scene_summaries 的 sidecar 路径
   ```
2. 拓扑分层算法：基于 depends_on_scene_ids + sequence_group 计算 layer；同层并发（N=3 max），不同层串行
3. 输入 SceneSpec 集合 → 拓扑排序 → 分层 → batch 执行

## BS-2：asyncio worker pool

4. /generator/batch_scheduler.py：核心函数 `async def run_batch(scenes: list[SceneSpec], concurrent_n: int = 3) -> BatchResult`
   - 启动 N 个 asyncio worker 共享一个 asyncio.Queue（pull 模式）
   - 每层 batch 用 worker pool 并发；层间串行（前层完成后才启动下层）
   - 每个 worker：pull SceneSpec → call `await asyncio.to_thread(generate_scene_with_hooks, ...)`（同步主流程包装为 to_thread）
5. concurrent_n 来源：env `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 3）；CLI flag `--concurrent-n N` 覆盖

## BS-3：RateLimitedProvider wrapper（v1.0 F14 修订）

6. /generator/_rate_limit.py：实现 `class RateLimitedProvider(LLMProvider)`：
   ```python
   class RateLimitedProvider:
       def __init__(self, inner: LLMProvider, rpm: int = 60):
           self._inner = inner
           self._bucket = TokenBucket(rate=rpm/60, capacity=rpm)
           self._lock = threading.Lock()
       
       def generate_structured(self, *args, **kwargs):
           with self._lock:
               self._bucket.acquire()  # 阻塞至 token 可用
           return self._inner.generate_structured(*args, **kwargs)
       
       def estimate_cost(self, *args, **kwargs):
           return self._inner.estimate_cost(*args, **kwargs)
   ```
7. **RateLimitedProvider 包住所有 LLMProvider 调用**——不在 scene worker 外层限速（F14 修订要点；外层限速会让内部 skeleton/fill/judge 调用不受限）
8. token bucket 默认 60 RPM（env `FORGEWRIGHT_PROVIDER_RPM`，CLI `--rpm N` 覆盖）
9. 在 batch_scheduler 启动时把 inner provider 包成 RateLimitedProvider 注入 generate_scene 的 LLMProvider 实例

## BS-4：GenerationDependencyTrace 注入（v1.0 F5 修订核心）

10. /generator/context_assembler.py 扩展：`_build_scene_context` 接受 `trace: GenerationDependencyTrace` 参数；在每注入一项（character / location / clock / relation / state / prompt template）时累加 trace
11. GenerationDependencyTrace dataclass：
    ```python
    @dataclass
    class GenerationDependencyTrace:
        ontology_ids_read: set[str] = field(default_factory=set)
        state_paths_read: set[str] = field(default_factory=set)
        state_paths_written: set[str] = field(default_factory=set)
        visual_asset_ids_referenced: set[str] = field(default_factory=set)
        clock_ids_referenced: set[str] = field(default_factory=set)
        prompt_template_files: list[Path] = field(default_factory=list)  # 用于计算 prompt_template_hash
        scene_history_referenced: list[str] = field(default_factory=list)  # ADR-024 hook
    ```
12. /generator/generate_scene.py：在 _build_scene_context 调用前实例化 trace，传入；在 effect 应用阶段（option.effects + node.on_enter_effects）累加 state_paths_written

## BS-5：dep_index sidecar 写入（v1.0 F5 修订）

13. /generator/dep_index_writer.py：核心函数 `def write_sidecar(scene_path: Path, scene: DialogueGraph, trace: GenerationDependencyTrace, prior_scene_summaries: list[PriorSceneSummary], token_metrics: dict, chapter_id: str | None, act_id: str | None) -> Path`
    - 把 trace 的 set/list 转 sorted list
    - 计算 prompt_template_hash = sha256(concat trace.prompt_template_files 内容)
    - 收集 scene_history_referenced = [s.scene_id for s in prior_scene_summaries]
    - 收集 token_metrics（prompt_token_estimate / summaries_injected_count / summary_source_hashes / truncation_reason；T-3.3 已落地）
    - chapter_id / act_id 来自参数（已由 chapter_assembler 调用产出；F6 顺序保证非 stale）
    - 输出 `<scene>.deps.json`（与 scene.json 同目录）；用 jsonschema 库验 ContentDependencyIndex schema

## BS-6：T-3.5 的写入顺序（v1.0 F6 修订核心）

14. /generator/generate_scene.py 主流程末尾**严格按以下顺序**：
    ```python
    # 1. write scene.json (already part of main flow)
    scene_path.write_text(scene.model_dump_json(indent=2))
    
    # 2. assign chapter (call T-3.9 helper)
    from generator.chapter_assembler import assign_scene_to_chapter
    assignment = assign_scene_to_chapter(scene.scene_anchor, ontology_path, chapter_id=spec.chapter_id, act_id=spec.act_id)
    
    # 3. write dep_index sidecar (call dep_index_writer; chapter_id/act_id 已赋值)
    from generator.dep_index_writer import write_sidecar
    write_sidecar(scene_path, scene, trace, prior_scene_summaries, token_metrics, assignment.chapter_id, assignment.act_id)
    
    # 4. record version (call T-3.8a record_version)
    from generator.version_recorder import record_version
    record_version(scene_path, generation_method="batch_scheduler")
    ```
15. **F6 critical**：必须按上述顺序——dep_index 在 chapter assignment 后才写，避免 stale chapter_id 问题

## BS-7：ontology 写入 file lock

16. /state/ontology/<world>.json 写入用 fcntl.flock 加文件锁
17. 多 worker 写不同 scene 文件无冲突；ontology 写入由 chapter_assembler 触发，统一 file lock

## BS-8：失败传播 + 仪表化

18. 单 worker scene 失败：log + 写 ProviderError 仪表化（沿用 R2.9）+ 不阻塞其他并发场景
19. BatchResult 含每 scene 的 status / failure_metadata / scene_path / cost_usd / elapsed
20. 总报告：完成后输出 `<batch_dir>/batch_summary.md` 含 success rate / total cost / mean elapsed / failure distribution / **layer-wise stats**（v1.0 新增；显示拓扑层时序）

## BS-9：CLI 入口

21. CLI：`python -m generator.batch_scheduler <scenes_spec.json> [--concurrent-n 3] [--rpm 60] [--dry-run]`
22. dry-run 模式：仅打印调度计划（拓扑分层 + 每层 SceneSpec 列表）+ 估算成本，不调 LLM

# 不要做的事
- 不要改 LLMProvider Protocol（速率限制在调度层加，不污染 Provider 接口）
- 不要在 batch_scheduler 内重写 generate_scene 主算法（仅做 worker pool + DAG + RateLimitedProvider + sidecar 写入 + chapter/version hook）
- 不要扩展 /schema/（dep_index schema 由 T-3.2 已落地）
- 不要碰 ontology 数据本身（仅加 file lock 写入路径）
- 不要把 prior_scene_summaries 来源 hard-code（SceneSpec 内可选传入；调度器不主动调 scene_summary_writer）
- 不要把 GraphContext.prior_scene_summaries 加字段——SceneGraphContext 字段是 T-3.3 范围
- **不要硬 link T-3.4 playtest**（F13 修订；T-3.5 不依赖 playtest）
- 不要重写 chapter_assembler 或 version_recorder（仅 import + 调用其公共函数；T-3.9 / T-3.8a 范围）

# 测试
- pytest /generator/tests/test_batch_scheduler.py + test_dep_index_writer.py + test_rate_limit.py 全过
- 必含：mock generate_scene + run_batch with 3 SceneSpec → 验证 N=3 并发执行 / RateLimitedProvider 限速正确（mock token bucket）/ ontology lock 写入串行（mock fcntl）/ dep_index sidecar 写入正确（schema 校验过；含 chapter_id/act_id 非 null）/ 单 worker 失败不阻塞 / **拓扑分层正确**（fixture 含 depends_on_scene_ids 测试）/ **写入顺序**（write scene → assign → write deps → record version；F6）
- 跑 /review skill + validate-all
- **可选小成本实证**：用 1 个 scene + concurrent_n=1 跑通端到端（需作者明示授权 + 走 budget 拦截）

# A 阶段完成标志
- diff 摘要（按 BS-1 ~ BS-9 九段说明）
- pytest 输出
- commit message: `feat(generator): batch scheduler with SceneSpec DAG + RateLimitedProvider + dep_index trace + chapter/version hooks (T-3.5; ADR-026 + ADR-023; F4 + F5 + F6 + F12 + F14)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.5_batch_scheduler_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6a/b review_ui / T-3.10 实测期都依赖本 PR
```

### T-3.6a ｜ 审阅 UI MVP（FastAPI + vanilla HTML/JS；F2 + F16 + F17）｜ [A-execute]

```text
你的任务是落地 ADR-025 审阅 UI 第一阶段——**T-3.6a MVP**（v1.0 F16 拆分；T-3.6b integrations 在 Wave 6 单独任务）。MVP 范围 = scene list + graph 视图 + validator issues 面板 + 审美层 [A]/[R]/[S] 标注。**v1.0 关键修订**：
- F2：模块边界**允许修改 pyproject.toml**（加 fastapi / uvicorn deps + tools package 注册；解决"代码不可安装"问题）
- F17：mermaid CDN fallback（vendor 固定版本 bundle 或可切换 ASCII/DOT 显示；不依赖 CDN 可用性）
- F16：浏览器 smoke / 截图 / mermaid 渲染检查改 mandatory（不是 optional）

# 任务类型：[A-execute]
- 纯执行；新建 /tools/review_ui/ + 修订 pyproject.toml；不动 schema / ADR / L1 文档
- 依赖 T-3.5 批量调度器 PR merge（review_ui 展示其产物）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**。后续 review_ui ergonomic 微调（仅前端文案 / 视图样式 / 不动后端 API 与 schema）属 §1.5.4 跳 BC 破例第 4 类。

# 模块边界（硬性）
允许修改：
  - /tools/review_ui/（**新建模块目录**）
    - /tools/review_ui/__init__.py
    - /tools/review_ui/server.py（FastAPI 应用 + 静态 server）
    - /tools/review_ui/api.py（REST endpoints）
    - /tools/review_ui/static/（**新建子目录**；vanilla HTML/CSS/JS）
      - index.html / app.js / styles.css
    - /tools/review_ui/static/vendor/（**新建子目录**；vendor mermaid.js bundle；F17）
    - /tools/review_ui/cli.py（CLI 启动入口）
    - /tools/review_ui/tests/
  - **/pyproject.toml**（v1.0 F2 修订；加 fastapi + uvicorn deps + tools package 注册）

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/generator/、/content/、/docs/（除新增 fixture 文档外）；**T-3.6a 不实现 visual asset / playtest worst / stale / chapter integrations**（那是 T-3.6b 范围）

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md ADR-025（T-3.1 已立项）+ ADR-002（运行时无 LLM）+ ADR-004（运行时与生产期严格分离）
- /docs/STAGE_3_TASKS.md §3.4 ADR-025 决策核心 + §2.1 D5 + §2.4 字段命名（FORGEWRIGHT_REVIEW_UI_PORT）
- /generator/scene_review_cli.py（T-2.8 已落地；理解 review_log.jsonl 接口；本 review_ui 写入兼容此接口）
- /generator/experiments/20260506T113419Z_baseline_011/graph_views/（T-2.8 graph_views 三件套实证产物；本 review_ui 复用 mermaid 文件）
- /generator/scene_metrics.py + /generator/scene_ai_judge.py（T-2.8 已落地；MVP 读取其输出）
- **/pyproject.toml 当前状态**（理解现有 packages + deps 列表，本任务追加 fastapi / uvicorn / tools package）

# 待落地点

## RUI-MVP-1：pyproject.toml 修订（v1.0 F2 修订核心）

1. /pyproject.toml 加：
   - `dependencies` 段加：`fastapi>=0.100`、`uvicorn[standard]>=0.23`
   - `[tool.setuptools.packages.find]` 段（或对应 packages 注册段）加 `tools` package（如尚未注册）
   - 如 pyproject.toml 用 hatchling / poetry 等其他构建后端，相应加 deps + package；本任务起步时检查现有构建后端
2. 验证 `pip install -e .` 安装 tools package + fastapi + uvicorn 成功（A 阶段必跑）

## RUI-MVP-2：FastAPI server

3. /tools/review_ui/server.py：FastAPI 应用 + 静态文件挂载（/static → review_ui/static/）+ REST API 挂载（/api/...）
4. server 启动：env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 8765）；CLI 入口 `python -m tools.review_ui [--port N] [--batch-dir <path>] [--scenes-dir <path>]`
5. 默认 batch_dir = `./generator/experiments/<latest>` 或 CLI 指定；scenes_dir = `./content/`

## RUI-MVP-3：REST API endpoints（MVP 范围）

6. /api/scenes — list scenes in batch_dir + scenes_dir（含 metadata：cost / pass status / dimensions advisory / dep_index sidecar）
7. /api/scene/{scene_id} — 单 scene 完整数据（scene.json + deps.json + judge result + paths from sampling）
8. /api/graph/{scene_id} — 返回 mermaid 文件内容（直接读 batch_dir/graph_views/<scene>.mermaid）
9. /api/review — POST endpoint 写入 review_log.jsonl（[A]/[R]/[S] + reason + timestamp）；与 T-2.8 scene_review_cli 接口兼容
10. **MVP 不实现** /api/playtest, /api/stale, /api/chapter, /api/visual——T-3.6b 范围

## RUI-MVP-4：前端 4 视图（MVP 范围）

11. **视图 1: scene list nav** — 左侧栏列所有 scenes + 简略状态（已审 / 未审 / 失败 / 缺 sidecar）+ 点击切换
12. **视图 2: graph 视图** — mermaid 渲染（fetch /api/graph/<scene_id> → mermaid.js 渲染 SVG）
13. **视图 3: validator issues 面板** — schema / topology / sampling / mechanical 四 tab；分别读 scene_results.jsonl 中相应字段
14. **视图 4: 审美层 [A]/[R]/[S] 标注** — 三按钮 + reason 文本框 → POST /api/review；submit 后自动跳到下一未审场景

## RUI-MVP-5：mermaid CDN fallback（v1.0 F17 修订）

15. /tools/review_ui/static/vendor/mermaid.min.js — vendor 固定版本 mermaid.js bundle（推荐 `mermaid@10.x`，下载入 vendor）
16. /tools/review_ui/static/index.html 优先 load vendor 版本；如 vendor 缺失 fallback CDN（默认顺序 vendor > CDN）
17. **进一步 fallback**：如 mermaid.js 完全不可用（vendor + CDN 都失败）→ 切换显示 batch_dir/graph_views/<scene>.dot 或 <scene>.ascii.txt（T-2.8 graph_views 三件套已就绪）；前端展示纯文本 graph
18. UI 角标显示 graph 渲染来源（"mermaid (vendor)" / "mermaid (CDN)" / "dot fallback" / "ascii fallback"）

## RUI-MVP-6：read-only

19. UI 不提供任何"编辑场景内容"按钮；编辑由作者直接改 JSON + git workflow（与 ADR-006 + ADR-025 决策一致）
20. 仅审美层 [A]/[R]/[S] 标注 + reason 写入 review_log.jsonl（这是 review 元数据写入，不是场景内容编辑）

## RUI-MVP-7：浏览器 smoke / 截图 / mermaid 渲染检查（v1.0 F16 mandatory）

21. **A 阶段 mandatory（不是 optional）**：
    - 启动 review_ui server（`uvicorn` 命令）
    - 用 puppeteer / playwright / selenium-headless 自动化打开 localhost:8765
    - 截图首页 + 1 个场景的 graph 视图 + validator panel + review 标注界面
    - 校验 mermaid 渲染成功（DOM 含 `<svg>` 节点）
    - 如 vendor mermaid 失败 → 校验 fallback 路径（dot / ascii）渲染成功
22. 截图入 PR description（GitHub PR 默认 markdown 支持图片）
23. 浏览器 smoke 失败 = A 阶段不通过

# 不要做的事
- 不要引入 React / Vue / Svelte / Next.js 等前端框架
- 不要做"编辑场景内容"功能（ADR-025 + ADR-006）
- 不要做生产期外的运行时部署
- 不要扩展 /schema/
- 不要硬编码 batch_dir / scenes_dir
- 不要尝试集成 LLM / 自动生成功能
- 不要碰 /generator/ /validator/（仅读其产物）
- **不要在 T-3.6a 实现 playtest / stale / chapter / visual 视图**（T-3.6b 范围；MVP 拆分核心）
- **不要跳过浏览器 smoke**（v1.0 F16 mandatory）

# 测试
- pytest /tools/review_ui/tests/ 全过
- 必含：API endpoints unit test（mock batch_dir + scenes_dir 数据）/ HTML 渲染基本 smoke / review POST endpoint 正确写入 review_log.jsonl 测试 / **浏览器 smoke + 截图 + mermaid 渲染校验（mandatory）**
- 跑 /review skill + validate-all
- 实测：用 baseline_011 batch dir 启动 review_ui localhost:8765 端到端

# A 阶段完成标志
- diff 摘要（按 RUI-MVP-1 ~ RUI-MVP-7 七段说明）
- pytest 输出
- **PR description 含 4 视图截图**（mandatory）
- commit message: `feat(tools): review UI MVP - scene list + graph + validator + A/R/S (T-3.6a; ADR-025; F2 + F16 + F17)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.6a_review_ui_mvp_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6b integrations 启动依赖本 PR；T-3.10 实测期作者使用 review_ui MVP + scene_review_cli 双轨标 [A]/[R]/[S]
```

### T-3.6b ｜ 审阅 UI integrations（visual / playtest / stale / chapter）｜ [A-execute]

```text
你的任务是落地 ADR-025 审阅 UI 第二阶段——**T-3.6b integrations**（v1.0 F16 拆分；T-3.6a MVP 已落地）。Integrations 范围 = visual asset thumbnail + playtest worst paths/scenes + stale list + chapter 分组。**关键设计**：F13 修订 — 对 playtest 视图做"产物存在则展示，否则隐藏 / 提示未跑" degrade（avoid hard depend playtest 框架完全跑过）。

# 任务类型：[A-execute]
- 纯执行；扩展 /tools/review_ui/api.py + static/app.js；不动 schema / ADR / L1 文档
- 依赖 T-3.6a MVP + T-3.5 + T-3.4（playtest）+ T-3.7（dep_propagate）+ T-3.9（chapter）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**。前端 ergonomic 微调（仅 CSS / 文案 / 视图调整）属 §1.5.4 跳 BC 破例第 4 类。

# 模块边界（硬性）
允许修改：
  - /tools/review_ui/api.py（追加 endpoints；不动 T-3.6a MVP endpoints）
  - /tools/review_ui/static/app.js + index.html + styles.css（追加视图；不动 MVP 视图行为）
  - /tools/review_ui/tests/

严禁修改：T-3.6a MVP 已落地的 server.py / cli.py / 现有 endpoints / MVP 视图（按既有契约扩展）；/schema/、/state/、/state/ontology/、/engine/、/validator/、/generator/、/content/

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md ADR-025（T-3.1 已立项）
- /docs/STAGE_3_TASKS.md §3.4 ADR-025 决策核心（5 视图齐全要求）+ §6 wave 图（T-3.6b 在 Wave 6 依赖 T-3.5/3.4/3.6a）
- /tools/review_ui/server.py + api.py（T-3.6a 已落地；理解现有 MVP endpoints 形态）
- /generator/playtest/ 输出格式（T-3.4 已落地；run_manifest.json + worst_paths.jsonl + worst_scenes.md）
- /tools/dep_propagate.py（T-3.7 已落地；JSON 输出格式）
- /generator/chapter_assembler.py（T-3.9 已落地；ontology chapters[].acts[].included_scenes 形态）
- /content/visuals/manifest.json（视觉资产 manifest 格式）

# 待落地点

## RUI-INT-1：Visual asset thumbnail 视图

1. /api/scene/{scene_id}/visuals — 读 scene.character_refs + scene_anchor → 查 manifest.json → 返回 visual_assets 引用（角色立绘 + 场景背景）
2. 前端：scene 视图右栏新增 "出场角色" + "场景背景" 缩略图区域（点击放大）

## RUI-INT-2：Playtest worst paths/scenes 视图（v1.0 F13 degrade 设计）

3. /api/playtest/{scene_id} — 检查 batch_dir/playtest_NNN/ 存在性：
   - 如存在 → 返回 worst_paths.jsonl（filter by scene_id）+ worst_scenes.md/json 摘要
   - 如不存在 → 返回 `{ "playtest_run": null, "reason": "no playtest run for this scene" }`（**degrade**；不报错）
4. 前端：playtest 视图区域：
   - 如有数据：列 worst paths（path trace + judge_score + critical_findings）+ scene 级 worst_scenes 摘要
   - **如无数据：显示提示"该场景未跑 playtest——可运行 `python -m generator.playtest <scene_path>` 后刷新"**（不隐藏视图区域；保留 UI 心智）

## RUI-INT-3：Stale list 视图

5. /api/stale — 调 T-3.7 dep_propagate 工具（lazy 调用，可选缓存）；返回 stale 场景列表（基于 dep_propagate JSON 输出格式）
6. 前端：左侧栏 nav 加 "Stale (N)" 数字角标；点击进入 stale 视图列出每场景 + reasons + suggested 重审优先级
7. 单 scene 视图区域：如 scene 在 stale list 中，**顶部红色横幅** "⚠ 该场景因 X 变更被标记 stale，可能需重审" + reasons 详情

## RUI-INT-4：Chapter 分组视图

8. /api/chapters — 读 ontology chapters[]，返回 chapter[].acts[].included_scenes 列表
9. 前端：左侧栏 scene list 默认按 chapter / act 分组（折叠 / 展开）；保留"全部 scene"线性列表 toggle
10. 单 scene 视图顶部显示 "属 chapter <chapter_id> / act <act_id>" 链接（点击切到 chapter 总览）

## RUI-INT-5：浏览器 smoke + 截图（mandatory；与 T-3.6a 一致）

11. A 阶段 mandatory：
    - 启动 review_ui + 准备 fixture（含 visual manifest / playtest run / stale 触发 / chapter 数据）
    - 自动化截图 5 视图（4 + chapter 分组）
    - 校验 degrade 路径（无 playtest 时显示提示文案而非空白）
12. 截图入 PR description

# 不要做的事
- 不要重写 T-3.6a MVP 的 endpoints / 视图（按既有契约扩展）
- 不要做"编辑 scene 字段"功能（read-only + 标注；ADR-025）
- 不要硬 depend playtest 数据存在（degrade 路径必须实现；F13）
- 不要做后端缓存复杂层（如 Redis）；如需简单 cache 用 in-memory 即可（避免新依赖）
- 不要扩展 /schema/

# 测试
- pytest /tools/review_ui/tests/ 全过（含本任务新增）
- 必含：fixture 含 / 不含 playtest 数据两种情况下 /api/playtest 行为测试 / stale list endpoint 测试 / chapter 分组 endpoint 测试 / **浏览器 smoke + 5 视图截图 mandatory**
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 RUI-INT-1 ~ RUI-INT-5 五段说明）
- pytest 输出
- PR description 含 5 视图（含 chapter 分组）截图 + degrade 路径截图
- commit message: `feat(tools): review UI integrations - visual + playtest + stale + chapter (T-3.6b; ADR-025)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.6b_review_ui_integrations_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.10 实测期完整 review_ui（MVP + integrations）可用
```

### T-3.7 ｜ 一致性维护（基于 dep_index trace 反向 propagate）｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 完成标志要求"一致性维护（本体变更时标记需重审的已生成内容）"——基于 ADR-023 content_dependency_index sidecar（**v1.0 F5 修订**：sidecar 是 context assembly trace 写入而不是 scene 反查；conservative over-approx）实现反向 propagate 工具：本体变更 → 反向查 sidecar trace → 标记 stale 场景 + 输出 report。

# 任务类型：[A-execute]
- 纯执行；新建 /tools/dep_propagate.py；不动 schema / ADR / L1 文档
- 必须依赖 T-3.2 schema 已 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线工具新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /tools/dep_propagate.py（**新建**）
  - /tools/__init__.py（如不存在则新建；**注**：tools/ 历史是占位目录；如 T-3.6a 先于本任务落地，pyproject.toml 已注册 tools package；如本任务先于 T-3.6a，本任务负责 pyproject.toml 加 tools package 注册）
  - /tools/tests/（**新建**测试目录）
  - **/pyproject.toml**（如 tools package 尚未注册；F2 修订；本任务允许加 tools package 注册）

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/generator/、/content/、/docs/（除新增 fixture 文档外）

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md ADR-023（T-3.1 已立项；本任务依赖；含 context assembly trace 写入语义）
- /docs/DECISIONS.md ADR-006（本体真相之源）
- /docs/STAGE_3_TASKS.md §3.2 ADR-023 决策核心 + §2.4 字段命名 + §6 wave 图（理解 T-3.7 与 T-3.5 的关系）
- /schema/content_dependency_index.schema.json（T-3.2 已落地；理解字段集 + F15 字段约束）
- /state/ontology/__init__.py（理解 ontology loader）

# 待落地点

## DP-1：核心反向查询函数

1. /tools/dep_propagate.py：核心函数：
   ```python
   def find_stale_scenes(
       changed_ontology_ids: list[str] = None,
       changed_state_paths: list[str] = None,
       changed_visual_assets: list[str] = None,
       changed_clocks: list[str] = None,
       content_root: Path = Path("content")
   ) -> list[StaleScene]:
       """
       Reverse propagation: scan all <scene>.deps.json sidecars under content/,
       return scenes whose dependency intersects any 'changed' input.
       Conservative over-approx (ADR-023 trace semantics; F5).
       """
   ```
2. StaleScene dataclass：`{scene_id, scene_path, deps_path, reasons: list[str]}`（reasons 含具体哪个 ontology_id / state_path 命中）
3. 实现：scan content/ 下所有 *.deps.json → load → 检查 dependency 字段交集 → 命中加入返回列表
4. **conservative over-approx（F5）**：依赖 trace 是注入 prompt 的所有引用（不是 scene 中实际出现的字段）；查询时按完整 trace 命中，宁可误报 stale 也不漏依赖

## DP-2：本体 diff 检测（可选 helper）

5. helper 函数：`diff_ontology(ontology_path: Path, since_commit: str) -> ChangedOntology`
   - 用 git diff 检测自 since_commit 以来 ontology entities 变更
   - 输出：changed character_ids / location_ids / clock_ids / state_paths（如 narrative_weight 变 / dramatic_triggers 改 / state_path_slug 改）
6. 不必精确——粗粒度即可（"vellin entity 任意字段变 → 标 char_vellin 为 changed"）；生产期 propagate 报告偏宽松好于偏紧

## DP-3：CLI 入口

7. CLI：`python -m tools.dep_propagate [--since <commit>] [--changed-ontology <ids>] [--changed-state-paths <paths>] [--report <markdown_path>] [--json <json_path>]`
8. 输出形态：markdown report 含 stale scenes 列表 + 每场景的 reasons + suggested 重审优先级（按 narrative_weight 排序：core > minor > context_only）
9. 加 `--json <path>` flag 输出 JSON（review_ui 集成）

## DP-4：与 review_ui 的接口

10. JSON 输出形态兼容 review_ui（T-3.6b 范围）展示——T-3.6b stale 标记面板复用本任务输出
11. **不在本任务集成 review_ui**——保留独立 CLI 工具语义

## DP-5：与 git workflow 集成（可选）

12. 提供 git pre-commit hook 模板（不强制安装；放 /tools/dep_propagate_hook_template.sh）：作者修改 ontology 后 pre-commit 自动跑 dep_propagate review
13. 作者明示安装—— 不在本任务自动安装到 .git/hooks/

# 不要做的事
- 不要自动修改 stale 场景内容（仅标记 + report；修复由作者人工或 T-3.5 重新生成）
- 不要扩展 /schema/（本任务读 sidecar，不写新 schema）
- 不要碰 /generator/ /validator/（本任务是工具层；与 generator 解耦）
- 不要碰 ontology 数据（read-only）
- 不要硬编码 ontology 路径（应可配置 content_root + ontology_root）

# 测试
- pytest /tools/tests/ 全过
- 必含：fixture 含 3 个 mock scene + sidecar，1 个改 character_id 触发命中，1 个改 state_path 触发命中，1 个不命中 → find_stale_scenes 返回正确列表 / report 渲染正确 / JSON 输出格式正确
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 DP-1 ~ DP-5 五段说明）
- pytest 输出
- commit message: `feat(tools): consistency maintenance via dep_index reverse propagation (T-3.7; ADR-023)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.7_consistency_maintenance_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6b review_ui stale 面板可在本 PR merge 后启动接入
```

### T-3.8a ｜ version_recorder.py 独立模块（F12 修订）｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 完成标志要求"版本控制集成（每次修改记版本）"的核心模块——/generator/version_recorder.py，记录 version metadata sidecar `<scene>.version.json`。**T-3.8 在 v1.0 拆 a/b**（F12 修订）：本任务（T-3.8a）只做 version_recorder.py 独立模块；batch_scheduler hook 接入由 T-3.5 范围接管（T-3.8b 不再单独编号）。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/version_recorder.py + sidecar 写入 helper；不动 schema / ADR / L1 文档
- **不阻塞下游**（Wave 0 独立任务；与 T-3.0 / T-3.11 并行）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/version_recorder.py（**新建**）
  - /generator/tests/

严禁修改：
  - /schema/（特别 dialogue_graph schema；版本元数据走 sidecar 不污染场景 schema）
  - /generator/batch_scheduler.py（**T-3.8a 范围不接入 hook**——这是 T-3.5 范围；F12 拆分）
  - /generator/generate_scene.py（同上）
  - /state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-016 §schema 版本号策略（既有 schema 不动；新增字段走 optional + additionalProperties 兼容路径——本任务沿用更严格做法：sidecar 形态完全不动 schema）+ ADR-006 单一真相之源（version metadata 是审计元数据，不属真相源；sidecar 适当）
- /docs/STAGE_3_TASKS.md §1（v1.0 完成标志阈值表 "版本控制集成" 行：每个入库 scene 必须有 version sidecar，T-3.10 验收审计无缺失；F7）+ §2.4（version sidecar required audit gate）

# 待落地点

## VR-1：sidecar 数据结构（轻量；不入 /schema/）

1. version_metadata 字段集（dataclass + JSON 序列化）：
   ```python
   @dataclass
   class VersionMetadata:
       scene_id: str
       version: int
       first_generated_at: str  # ISO datetime
       last_modified_at: str
       git_commit_at_generation: str | None  # SHA; None if not in git repo
       git_branch_at_generation: str | None
       generation_method: Literal["batch_scheduler", "manual_edit", "regenerate", "playtest_fix"]
       previous_versions: list[PreviousVersion]
   
   @dataclass
   class PreviousVersion:
       version: int
       commit: str | None
       modified_at: str
       changed_fields: list[str]  # optional; manual edit 时作者填
   ```
2. 不入 /schema/ 文件（保 dialogue_graph schema 不动）；仅作 generator 内 dataclass + JSON 序列化
3. 文件位置：`<scene>.version.json`（与 deps.json / summary.json 同目录平行；§2.4 字段命名一致）

## VR-2：核心写入函数

4. /generator/version_recorder.py：核心函数 `def record_version(scene_path: Path, generation_method: str, changed_fields: list[str] | None = None) -> VersionMetadata`
   - 检测 git HEAD commit + branch（用 subprocess `git rev-parse HEAD` + `git rev-parse --abbrev-ref HEAD`）
   - 如 `<scene>.version.json` 已存在：bump version + append previous_versions
   - 如不存在：version=1 + previous_versions=[]
5. 错误处理：git 不可用（如非 git 仓库 / git 命令找不到）→ git_commit / git_branch 字段写 None + log warning + 继续；不阻塞 scene 写入
6. 不调用 git commit / git push / git add（CLAUDE.md 安全约束 + F7 修订；放弃自动 git commit）

## VR-3：CLI 入口（手动编辑后追溯）

7. CLI：`python -m generator.version_recorder <scene_path> --method manual_edit [--changed-fields field1,field2]`
8. 让作者在手动编辑某场景后追溯 version bump（避免漏记）
9. 默认 method="manual_edit"（CLI 直接调时）；--method 显式覆盖

## VR-4：与 batch_scheduler / chapter_assembler / dep_propagate 的集成接口

10. version_recorder.py **导出 record_version 公共函数**——T-3.5 batch_scheduler 范围会 import + 调用（在 write scene → assign chapter → write deps → record version 顺序的最后一步）
11. T-3.7 dep_propagate 工具（已落地后）可在 stale 报告中引用 version sidecar 数据（如显示 last_modified_at）；但不在本任务集成

## VR-5：测试

12. /generator/tests/test_version_recorder.py 必含：
    - record_version 首次调用测试（version=1 + previous_versions=[]）
    - 重复调用 bump version 测试（version=2 + previous_versions 含 v1）
    - git 不可用 fallback 测试（mock subprocess raise）
    - CLI 集成测试

# 不要做的事
- 不要扩展 /schema/（特别 dialogue_graph schema）
- 不要尝试自动 git commit / git push（仅记录 metadata + 当前 git 状态；commit/push 仍由作者明示）
- 不要把 version metadata 嵌进 scene.json（保 dialogue_graph schema_version 0.1.1 不破）
- 不要用复杂 diff 算法（diff 由 git 提供）
- **不要碰 /generator/batch_scheduler.py / generate_scene.py**（T-3.8a 拆分后 hook 接入由 T-3.5 范围接管；F12）

# 测试
- pytest /generator/tests/test_version_recorder.py 全过
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 VR-1 ~ VR-5 五段说明）
- pytest 输出
- commit message: `feat(generator): version recorder module (T-3.8a)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.8a_version_recorder_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.5 范围会 import record_version 公共函数（T-3.8b 范围）
```

### T-3.9 ｜ Chapter/Act 容器生成 helper 库（F6 修订）｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 重点工作"Chapter/Act 层级结构设计"的 generator 层 helper 库——把生成的场景挂到 chapter.acts.included_scenes 容器下。**v1.0 F6 修订核心**：本任务**先以 helper 库形态交付**（不再是 batch_scheduler hook）；T-3.5 范围会 import + 调用本任务 helper（按 "write scene → assign chapter → write deps → record version" 顺序），避免 v0.1 中 dep_index sidecar 写出 stale chapter_id 的问题。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/chapter_assembler.py 作 helper 库；不动 schema / ADR / L1 文档
- 不阻塞 T-3.5 启动——T-3.5 起步时如本任务未 merge，可暂用 stub 调用；最终集成依赖本任务 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/chapter_assembler.py（**新建**；helper 库形态；导出公共函数供 T-3.5 调用）
  - /generator/tests/

严禁修改：
  - /schema/、/state/ontology/（数据写入由 chapter_assembler 接管；用 file lock 沿用 T-3.5 ontology lock；本任务不动 ontology 数据本身的字段定义）
  - /engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）
  - **/generator/batch_scheduler.py / generate_scene.py**（本任务仅交付 helper；hook 接入由 T-3.5 范围接管；F6 拆分）
  - /generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-016 §Chapter/Act 容器 schema（chapter / acts / included_scenes 字段定义）
- /schema/chapter.schema.json（T-2.2 已落地；理解字段结构）
- /docs/STAGE_3_TASKS.md §1（v1.0 完成标志表）+ §2.1 D10（Chapter/Act 不立新 ADR）+ §6 wave 图（T-3.5 调用顺序）
- /state/ontology/__init__.py（理解 ontology loader + chapter 写入路径）

# 待落地点

## CA-1：核心 propagate 函数（公共 API）

1. /generator/chapter_assembler.py 导出公共函数：
   ```python
   def assign_scene_to_chapter(
       scene_anchor: str,
       ontology_path: Path,
       chapter_id: str | None = None,
       act_id: str | None = None
   ) -> ChapterAssignment:
       """
       Assign scene_anchor to chapter.acts[act_id].included_scenes.
       If chapter_id/act_id None: heuristic match OR fallback "unassigned".
       Idempotent: if scene_anchor already in included_scenes, skip + return success.
       """
   ```
2. ChapterAssignment dataclass：`{success, scene_anchor, chapter_id, act_id, reason}`

## CA-2：ontology 写入（受 file lock 保护）

3. 写入路径：sourceuse T-3.5 已实现的 ontology file lock helper（如未独立 helper，本任务在 T-3.5 lock 模块内复用）；如本任务先于 T-3.5 落地，本任务自带 fcntl wrapper 但接口保留 inject lock 形态
4. 操作：read ontology JSON → modify chapters[chapter_id].acts[act_id].included_scenes append scene_anchor → write back

## CA-3：T-3.5 集成接口（v1.0 F6 修订核心）

5. 公共函数签名设计为可被 T-3.5 调度器 import：
   ```python
   from generator.chapter_assembler import assign_scene_to_chapter
   # T-3.5 batch_scheduler 在 generate_scene 完成 + scene.json 写入后调用
   assignment = assign_scene_to_chapter(scene.scene_anchor, ontology_path, chapter_id=spec.chapter_id, act_id=spec.act_id)
   # 然后 T-3.5 范围才写 dep_index sidecar（含 chapter_id/act_id 字段）
   # 写入顺序: write scene → assign chapter → write deps → record version
   ```
6. **本任务不在 batch_scheduler.py 内 hook**——T-3.5 范围接管 hook 接入（F6 修订；拆分清楚）

## CA-4：CLI 入口（手动 reassign）

7. CLI：`python -m generator.chapter_assembler <scene_anchor> --chapter <chapter_id> --act <act_id>`
8. 让作者在审阅工坊期手动调整某场景归属

## CA-5：验证（不破 ADR-006）

9. 验证：assign 不修改场景 scene.json 内容（仅修改 ontology 容器）；ADR-006 单一真相之源 + ADR-016 chapter 容器位置（state/ontology 顶层 chapters[]）维持
10. 验证：chapter / act schema_version "0.3.0" 维持不动（ADR-016 §schema 版本号策略）

# 不要做的事
- 不要在 generate_scene 主流程内调用 chapter_assembler（保留分离；调用点在 T-3.5 batch_scheduler 范围）
- 不要扩展 chapter.schema.json（schema 不动；本任务仅做数据写入工具）
- 不要立新 ADR（D10 + ADR-016 后果段已涵盖）
- 不要碰 dialogue_graph.schema.json / scene.json schema_version
- 不要尝试自动推断 chapter / act 归属（启发式留 hook 但默认 fallback unassigned）
- **不要在 batch_scheduler.py 内 hook**（F6 修订；T-3.5 范围接管）

# 测试
- pytest /generator/tests/test_chapter_assembler.py 全过
- 必含：fixture ontology with chapters[] + acts[] → assign_scene 测试 / idempotent 测试 / chapter_id 缺失 fallback unassigned 测试 / file lock 测试（mock fcntl）/ T-3.5 集成接口签名测试
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 CA-1 ~ CA-5 五段说明）
- pytest 输出
- commit message: `feat(generator): chapter/act helper library (T-3.9; ADR-016 chapter container; F6 fix)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.9_chapter_helper_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.5 范围 import + 调用本 helper 依赖本 PR
```

### T-3.10 ｜ 完成标志实测（F19 R3.X 不强制 + F4 场景集声明依赖图）｜ [A-execute]

```text
你的任务是阶段 3 完成标志的实证 batch run——作者本人跑一周（5 工作日 + 2 周末），完成 ≥10 场景的生成 + 审阅 + 入库；测量**v1.0 修订完成阈值**（F8 方案 A）：
- logic regression gate：**0 critical validator failures**（schema / topology / sampling / mechanical 任一 critical 级失败 = 阶段 3 不达标）；warning / minor 级失败允许在 R3.X follow-up 闭环修复
- 审美层 [A]ccept rate：**≥ 60% pilot + Wilson 95% CI 报告**（如 6/10 → CI 27%-86%；不用单点百分比伪装稳定）
- 实测吞吐：1 周 ≥ 10 场景

**v1.0 关键修订**：
- F19：R3.X 不强制 — 改"如出现 finding，至少 1 个按 R3.X 闭环；若 0 finding，记录 no-follow-up justification + raw metrics"
- F4：场景集声明依赖图（SceneSpec.depends_on_scene_ids / sequence_group / prior_summary_paths），不是 flat specs

# 任务类型：[A-execute]（实测会话；不开发代码）
- 实测期 ≈ 1 周——非单次会话，是作者跨多日多次会话操作
- A 阶段不写代码；本任务是"用工具链 + 观测 + 记录数据"
- 必须依赖 T-3.5 + T-3.6a + T-3.6b + T-3.4 全部 PR merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——但 ABC 在本任务有变体（实测期 ≈ 1 周）：
- A 阶段 = 作者跨多日跑批 + 审阅 + 写实测报告
- B 阶段 = 作者基于实测 finding 起 Codex review 实测报告 + 流水线整体（不只单 PR diff）
- C 阶段 = 作者基于 review 起 Claude Code 修代码 / 文档（如 finding 含工具链 bug，对应起 R3.X follow-up）

# 模块边界（硬性）
允许修改：
  - /generator/experiments/<batch_dir>/（实测 batch run 产出物入库）
  - /content/<scene_dir>/（实测产出场景 + 全套 sidecar 入库：scene.json + deps.json + version.json + summary.json）
  - /docs/STAGE_3_IMPLEMENTATION_LOG.md（**新建**；实测期日志 + finding；按 STAGE_2 baseline 序列日志风格）
  - 实测期产生的 R3.X follow-up（视需要单独起任务；编号 R3.4+；跳 BC 破例第 1/2/3 类适用）

严禁直接修改（实测期内）：/schema/、/state/、/state/ontology/（loader 不动；ontology 增量由 chapter_assembler 写入受 file lock 保护；无需手动改）、/engine/、/validator/、/docs/DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/STAGE_3_TASKS.md §1（v1.0 完成标志阈值表 — 0 critical / [A] ≥ 60% Wilson CI / Y=10 场景/周）+ §2.4（version sidecar required audit）
- /docs/STAGE_2_ACCEPTANCE.md（实证形态参考；baseline_011 实测格式）
- /docs/HANDOFF_STAGE_2_TO_3.md
- /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md（baseline 协议沿用 + 加 playtest 维度）
- ~/.claude/projects/-Users-outsider-Desktop-Forgewright/memory/feedback_acceptance_review_deferred_to_stage_4.md（feedback memory 锁定 — 阶段 3 激活审美层 [A]/[R]/[S]）

# 待落地点

## IT-1：场景集准备（v1.0 F4 修订核心）

1. 作者准备 10-15 场景 spec — 跨 2-3 个 chapter 范围；含 vellin / corvan / aelwin 主角色 + 阶段 3 实测期可补新角色
2. **场景集必须声明依赖图（F4）**：
   ```json
   [
     {"scene_id": "ch1_arrival", "scene_setting": "...", "depends_on_scene_ids": [], "sequence_group": "act1", "chapter_id": "chap_act1_iron_oath", "act_id": "act1_arrival"},
     {"scene_id": "ch1_betrayal", "scene_setting": "...", "depends_on_scene_ids": ["ch1_arrival"], "sequence_group": "act1", ...},
     ...
   ]
   ```
   不是 flat specs；明示 chapter / act 归属 + 跨 scene 依赖（剧情顺序）
3. 场景集放 /generator/experiments/stage3_implementation_v1/scene_specs.json

## IT-2：第一波跑批（baseline_012; ~5 场景）

4. 用 T-3.5 batch_scheduler 跑首波 5 场景（concurrent_n=3）+ 拓扑分层调度
5. 跑完后：
   - 跑 dep_index 反向 propagate 检查（T-3.7）
   - 跑 playtest 5 persona × 20 paths/scene = 100 paths × 5 = 500 paths（独立编号 playtest_001）
   - **calibration run 先跑（T-3.4 mandatory；F9）**: 1 scene × 1 persona × 5 paths 实测后再扩
6. 启动 T-3.6a + T-3.6b review_ui localhost:8765 → 浏览器审阅 5 场景 → 标 [A]/[R]/[S] + reason
7. 测量首波 logic regression gate（critical count）+ [A] rate + Wilson CI + mean cost + mean elapsed + playtest worst-10%

## IT-3：第二波 / 第三波（按需扩到 10+ 场景）

8. 视首波数据决定第二波范围：
   - 如首波 critical count > 0 → 起 R3.X follow-up 修工具链 / prompt 后再跑
   - 如首波 [A] rate < 60% → 起 R3.X follow-up 调 prompt 后再跑
9. 编号续 baseline_013 / 014 + playtest_002 / 003

## IT-4：实测期日志（每波 batch 必记）

10. /docs/STAGE_3_IMPLEMENTATION_LOG.md 记录每波 batch：
    - 时间 + 编号 + 场景数 + cost + wall clock
    - **logic regression gate**：critical_count / warning_count / minor_count 三层
    - [A] rate + Wilson CI（用 6/10 = 60% / CI 27%-86% 形态）
    - playtest 数据：avg calls/path / avg cost/path（calibration vs 实际）/ worst-10% finding count
    - dep_index 维度数据（avg ontology_ids_read / state_paths_written 数）
    - 长对话一致性观察（prior_scene_summaries 实际作用 + 是否撞 §9.2 真墙；token 累积曲线）
    - chapter assignment 命中率（chapter_id 非 null 比例）
    - version sidecar 完整率（每入库 scene 都有 version.json）
    - **R3.X follow-up 触发列表**（如有）

## IT-5：阶段 3 完成判定（实测末期；v1.0 修订）

11. 末期跑总结，**全部 5 项指标必须 MET**才能进 T-3.12 验收：
    - 实测 N ≥ 10 场景
    - **logic regression gate**：0 critical validator failures（schema / topology / sampling / mechanical 任一 critical 级失败 = 阶段 3 不达标）
    - 审美层 [A] rate ≥ 60% + Wilson 95% CI 报告（不用单点百分比伪装）
    - playtest worst-10% 0 critical issue 或全部修复（critical 必须作者明示确认；ADR-022 severity rubric）
    - dep_index 100% 写入 + chapter 容器分配率（实测）+ version sidecar 100% 完整
12. 数据写入实测期日志末尾段
13. 阶段 3 完成判定：五项指标全 MET → 进 T-3.12 验收；任一未 MET → 起 R3.X 修复 + 二轮跑批

## IT-6：实测期 follow-up dispatch（v1.0 F19 修订）

14. **F19 修订**："如出现 finding，至少 1 个按 R3.X 机制闭环；若 0 finding，记录 no-follow-up justification + raw metrics"——不强制为流程 fabricate R3.X
15. 实测期产生的 finding（baseline_NNN finding / playtest_NNN finding / R3.X follow-up）按 §1.5.4 跳 BC 破例第 1/2/3 类处理：作者起 A 阶段会话主动修 + 拆 commit 标注 finding + L2 quick check + merge

# 阶段 2 sequence 经验吸收

- 阶段 2 baseline_005 v3 → 011 经历 7 次 R2.X 修复链路；阶段 3 实测预期类似 sequence 或更短（工具链阶段 3 起步比阶段 2 起步成熟）
- 阶段 2 baseline_011 100% gross_pass + 0% audit；阶段 3 加审美层 + critical taxonomy 后预期 [A] rate 60-80%（首批 prompt 调优后稳）
- 不要追求"一次跑完 10 场景全过"——按 baseline + R3.X follow-up 迭代节奏推进

# 不要做的事
- 不要在实测期修改 generator / validator 主流程（如发现 bug → 起 R3.X follow-up 单独 ABC 走）
- 不要跳过 review_ui 标 [A]/[R]/[S] 流程（阶段 3 激活审美层是完成标志强化项 U-CL-1 的核心）
- 不要把实测期 R3.X follow-up 搞成大 PR；保持 commit 颗粒度细
- 不要在本任务里写阶段 3 验收报告（那是 T-3.12 范围）
- **不要 fabricate R3.X follow-up**（F19 修订；如 0 finding 则记录 no-follow-up justification 即可）
- **不要把场景集做成 flat specs**（F4 修订；必须声明 depends_on_scene_ids / sequence_group / chapter_id / act_id）
- **不要跳过 calibration run**（F9 修订；T-3.4 calibration mandatory）

# 测试 / 验证

- 实测期产出物 = 数据 + 日志 + 入库场景 + 全套 sidecar（deps/version/summary）+ R3.X follow-up PR；不是单元测试
- 阶段 3 完成判定 5 指标必须全 MET 才能进 T-3.12

# A 阶段完成标志（实测期末）

- /docs/STAGE_3_IMPLEMENTATION_LOG.md 完整（含每波 batch 数据 + 完成判定数据 + Wilson CI 报告）
- /generator/experiments/stage3_implementation_v1/ 入库 + 多个 baseline_NNN / playtest_NNN
- /content/ 含 ≥ 10 场景的实测产出物（scene.json + deps.json + version.json + summary.json 全套 sidecar）
- 实测期 R3.X follow-up 处理记录（如有 finding；F19）OR no-follow-up justification + raw metrics（如 0 finding）
- commit message: `feat(experiments): Stage 3 implementation log + ≥10 scenes via batch_scheduler (T-3.10)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：实测期跨多次会话；最终汇总 commit 集中开 PR

# B / C 阶段（变体；适用于实测后整体 review）

- B 阶段：Codex review STAGE_3_IMPLEMENTATION_LOG + 整体流水线观察（不仅单 PR diff）；report 落 /docs/reviews/<ISO_DATE>_T-3.10_implementation_review.md
- C 阶段：作者起 Claude Code 会话基于 review 起 R3.X 修复（如 finding 仅文档则修文档）
- L2 验收过关后进 T-3.12 验收
```

### T-3.11 ｜ 开源剥离边界清单 v0.2 增量 ｜ [A-execute]

```text
你的任务是为 /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md 加 v0.2 增量——把阶段 3 新引入的私有依赖（playtest 配置 / review_ui 路径 / version_recorder git 假设 / batch_scheduler 默认值 / FastAPI 依赖 / mermaid CDN 风险等）补入清单。这是 synthesis §6/§7 C5 在阶段 3 期间维护边界 hook 的延续工作。

# 任务类型：[A-execute]
- 纯执行；仅修改 /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md；不动 schema / ADR / 其他 L1 文档 / 任何代码
- 不阻塞下游；可与 T-3.5 / T-3.6 / T-3.7 同期推进

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——文档 maintain 任务，但内容增量仍需 review。

# 模块边界（硬性）
只允许修改：/docs/OPEN_SOURCE_CARVE_OUT_INDEX.md
严禁修改：CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md / 任何 /schema/ 文件 / 任何代码

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md v0.1（阶段 2 T-2.10 落地 commit `eef3f3b`）
- /docs/reviews/master_plan/2026-04-30_synthesis.md §C5
- /docs/HANDOFF_STAGE_2_TO_3.md
- /docs/STAGE_3_TASKS.md §4.2（阶段 2 v0.1 已落地，阶段 3 维护增量）

# 待落地点（按 v0.1 已有三类边界 A/B/C 拓展 + 加 D/E/F 新类）

## v0.2-A：fixture / 角色 / 场景内容增量

1. /generator/playtest/personas/*.json（5 个 persona JSON）—— 通用 RPG persona（cautious / aggressive / completionist / speedrunner / role_player），建议保留入开源默认；如 augmented_description 含《铁誓驿站》上下文则需剥离时清理
2. /generator/playtest_cost_log.jsonl + /tools/review_ui/state（review_log.jsonl）—— runtime 产物，剥离时不带

## v0.2-B：资产版权增量

3. visual_assets 引用（如阶段 3 实测期补 14 立绘 + 1 background）—— 沿用 v0.1 §B；阶段 3 末期视实测产出添加具体路径

## v0.2-C：provider 假设增量

4. /generator/batch_scheduler.py 默认 N=3 + RPM=60 + ontology lock fcntl 假设 —— **POSIX file lock 在 Windows 不可用**；v0.2 标记需提供跨平台 fallback（如用 portalocker 库）；阶段 4 剥离时由 framework 仓库实现
5. **/tools/review_ui/server.py FastAPI 依赖 + uvicorn 依赖 + mermaid.js CDN URL 假设（v0.2 critique F2 + F17 修订要点）**：
   - FastAPI / uvicorn 引入了 Python Web 生态依赖（`pip install fastapi uvicorn` 一行；门槛低但破纯 stdlib 假设）
   - mermaid.js CDN URL 可能不可用 / 大版本变化；v0.2 应已含 vendor bundle fallback；剥离时 framework 仓库默认走 vendor，不依赖 CDN
6. /generator/version_recorder.py git subprocess 假设 —— 非 git 用户怎么用；v0.2 标记需提供 fallback path

## v0.2-D：用户配置默认值（新类别）

7. FORGEWRIGHT_BATCH_CONCURRENT_N / FORGEWRIGHT_PROVIDER_RPM / FORGEWRIGHT_REVIEW_UI_PORT 默认值都基于作者环境（PoloAI 速率限制 + 作者带宽）—— 开源用户需在 README 文档化所有 env vars
8. prompt_template_hash 算法（SHA256 of concat 文件）—— 算法假设稳定；剥离时 v0.2 维持

## v0.2-E：阶段 1.5 R1.5-* 遗留对开源剥离的影响

9. R1.5-1（剩余 14 立绘 + 1 background 全 batch 跳过）—— 阶段 4 剥离时如开源 framework 不带任何视觉资产例子，需提供 placeholder + 文档说明
10. R1.5-3（视觉判官 vs 作者 kappa 未算）—— 不影响开源剥离；标记为"作者评测专属，不入框架默认评测路径"

## v0.2-F：阶段 3 cross-LLM critique workflow（新类别）

11. /docs/REVIEW_PROMPT_L2_STAGE_TASKS.md（阶段 3 新建模板）—— 建议入开源框架默认；含 7 个占位符；可复用阶段 4+ 任务清单 critique
12. /docs/reviews/master_plan/* 系列文档（阶段 3 各轮 critique / response / synthesis）—— 治理审计轨迹；阶段 4 剥离时建议保留作"how this project handled cross-LLM review" 的开源案例参考

# 不要做的事
- 不要立新 ADR（D10 明示 C5 OPEN_SOURCE_CARVE_OUT_INDEX 不立新 ADR）
- 不要碰任何 /schema/ /code/ 路径
- 不要修改 CLAUDE.md / ROADMAP.md / DECISIONS.md
- 不要在本任务做实际剥离（阶段 4 范围）
- 不要把 v0.1 段落删掉（增量是 append）

# 文档增量结构

在 v0.1 §2 三类边界（A/B/C）下追加 §3 v0.2 增量段（v0.2-A ~ v0.2-F 六个子类）+ §4 阶段 3 末期 follow-up 段。

末尾在 v0.1 已有 "## 版本" 段更新版本号 v0.2 + 日期。

# 测试
- 跑 /review skill + validate-all（文档校验）
- 不需 pytest（纯文档任务）

# A 阶段完成标志
- /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md v0.2 diff 摘要（按 v0.2-A ~ v0.2-F 六段说明）
- commit message: `docs: OPEN_SOURCE_CARVE_OUT_INDEX v0.2 increment for Stage 3 (T-3.11; C5)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（同 §1.5）
- B 阶段：Codex review；report 落 /docs/reviews/<ISO_DATE>_T-3.11_oss_carve_out_v0.2_review.md
- C 阶段：吃报告改文档 + 追加 commit
- L2 验收过关后 merge
```

### T-3.12 ｜ 阶段 3 验收报告 ｜ [B-author-gate]

```text
你的任务是产出 /docs/STAGE_3_ACCEPTANCE.md——阶段 3 完成判定 + 数据汇总 + R3.X 遗留 + 阶段 4 启动前置条件交接。这是阶段 3 收官 [B-author-gate] 任务，作者最终签字。

# 任务类型：[B-author-gate]
- 修改 L1 架构文档（验收报告归 L1 类）；CLAUDE.md 规则 9/10 例外
- 必须依赖 T-3.10 实测完成 + **完成判定五指标全 MET**（v1.0 F8 + F10 修订）

# 跳 BC 破例适用性
本任务**跳 BC 破例适用第 5 类**（阶段 3 验收报告）—— 沿用阶段 2 T-2.13 验收报告作者明示授权跳 BC 直接 merge 先例。但内容仍需作者最终签字。

# 模块边界（硬性）
允许修改：
  - /docs/STAGE_3_ACCEPTANCE.md（**新建**）
  - /docs/HANDOFF_STAGE_3_TO_4.md（**新建**；草稿；阶段 4 规划师启动后由其修订）

严禁修改：CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md（**注**：ROADMAP §阶段 3 完成标志可能因实测发现需要措辞修订；如需修订属跨边界 X7（v1.0 §9）作者另起 L1 修订会话）/ SCHEMA_v0*.md / 任何 /schema/ 文件 / 任何代码

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/STAGE_2_ACCEPTANCE.md（参考体例 + 数据汇总形态）
- /docs/STAGE_1_ACCEPTANCE.md + /docs/STAGE_1.5_ACCEPTANCE.md（参考遗留项处理形态）
- /docs/HANDOFF_STAGE_2_TO_3.md（参考交接档形态）
- /docs/STAGE_3_IMPLEMENTATION_LOG.md（T-3.10 实测期产出；本任务核心数据源）
- /generator/experiments/stage3_implementation_v1/（实测 batch + playtest 产出物）
- /docs/STAGE_3_TASKS.md（本文件；含 v1.0 完成标志阈值 + 22 finding 处理对照表 + ADR 决策核心 + critical/major/minor severity taxonomy）
- /docs/ROADMAP.md §阶段 3 完成标志（与实测数据对照）
- /docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md（cross-LLM critique round 2 治理证据）

# 待落地点

## VR-1：STAGE_3_ACCEPTANCE.md 主体

参考 STAGE_2_ACCEPTANCE.md 体例：

1. **§1 阶段 3 完成判定核对**：表格列 — 指标 / ROADMAP-ADR 目标 / 实测 / 判定（MET / 部分 / 推迟）
   - generate_scene 主函数（已 T-2.6 落地；阶段 3 沿用 + T-3.5 调度器扩展）
   - 批量生成调度器（T-3.5；含 SceneSpec DAG / RateLimitedProvider / 写入顺序）
   - 审阅界面（T-3.6a MVP + T-3.6b integrations）
   - 一致性维护（T-3.7 + dep_index trace 写入；ADR-023）
   - 版本控制集成（T-3.8a version_recorder + T-3.5 hook 集成；F7）
   - 实测吞吐 ≥ 10 场景/周（T-3.10）
   - **logic regression gate**：0 critical validator failures（实测 critical_count）— **v1.0 F8 修订**
   - 审美层 [A]ccept rate ≥ 60% pilot + **Wilson 95% CI 报告**（实测）— v1.0 F8 修订
   - playtest bots 至少 5 场景跑过完整 100 paths/scene + worst-10% 0 critical issue 或全部修复（critical 作者明示确认；ADR-022）+ calibration run 实测 cost/calls/time 报告
   - 长对话一致性 C 起步落地 + A/B hook + token metrics（T-3.3；F3 SceneGraphContext）
   - 启动闸门 C2 / C6 / U-CL-1 / U-CL-5 / U-GPT-7 全部 MET
   - **GPT-5.5 cross-LLM critique round 2 + Claude response + 作者拍板治理证据**（v1.0 新增；展示 cross-LLM 评审实绩）
2. **§2 实证数据**：baseline_NNN + playtest_NNN 序列汇总；每波 batch 数据；总体指标；calibration run 实测数据
3. **§3 工作量速览**：T-3.0 ~ T-3.12 主任务表（**14 槽位**：T-3.6a/b + T-3.8a + T-3.8b 合并入 T-3.5）+ R3.X follow-up 系列（含跳 BC 破例计数）
4. **§4 遗留问题**（R3.* 表）—— 阶段 3 不解决但阶段 4 必须处理的项
5. **§5 阶段 4 启动前置条件**——闸门清单留给阶段 4 规划师
6. **§6 真实费用回顾**——LLM 成本 / token 用量 / 与 ADR-022 calibration 估算对照
7. **§7 模块边界自检**——grep 验证 ADR-002 / ADR-004 / ADR-006 / ADR-008 + 阶段 3 新增 ADR-022 ~ 026 全部坚守 + tools package 注册（F2 修订）
8. **§8 跨 LLM 评审实绩**——主任务 ABC 闭环率 + 跳 BC 破例计数 + L2 critique cross-LLM 增益数据（22 finding / 漏抓 / 互补 / 严重度分歧）
9. **§9 签字**——作者签字栏 + 接受条件

## VR-2：HANDOFF_STAGE_3_TO_4.md 草稿

参考 HANDOFF_STAGE_2_TO_3.md v0.1 体例：

1. 项目是什么（与历史交接档一致；预生成选项 + 极简运行时铁律）
2. 玩家交互模式铁律（与历史一致）
3. 阶段 3 做了什么（14 主任务 + R3.X follow-up；含 5 ADR-022~026）
4. 阶段 3 收尾时的架构遗留 R3-* 表
5. 阶段 4 启动条件摘自 ROADMAP §阶段 4
6. 阶段 4 规划粗想（给下一规划师参考；未与作者校准）
7. 必读顺序（新规划师首轮阅读）
8. 工作模式（继承 v0.3 治理 §10 + v1.0 跳 BC 破例 5 类清单）
9. 阶段 3 残留的工作流改进建议（含审阅 UI / playtest / dep_index trace / RateLimitedProvider 实战经验）
10. 跨阶段串行 / 并行预判
11. 总盘子预判（阶段 4 LLM 成本估算 + dev token；calibration 实测数据作输入）
12. X 跨阶段提醒（X1-X7 沿用 + 阶段 3 实测产生的新 X 项）
13. **L2 critique 模板复用**（指向 /docs/REVIEW_PROMPT_L2_STAGE_TASKS.md；阶段 4 起草后跑同款 critique）

## VR-3：审美层评估激活后的 feedback memory 处理

3. 阶段 3 实测激活了审美层 [A]/[R]/[S]（feedback memory `feedback_acceptance_review_deferred_to_stage_4.md` 锁定的"推迟到阶段 4"被阶段 3 提前激活）—— 验收报告 §1 注明此点 + 提示作者更新 feedback memory（不在本任务范围；作者另起 memory consolidate）

## VR-4：跨边界事项更新

4. X1（v0.1 路径自引用）→ 已在 v1.0 §9 标 closed（v1.0 整合时全文路径替换完成）
5. X2 / X3 / X4 / X5 / X6 / X7 视实测期是否产生新 X 项更新

# 不要做的事
- 不要碰 CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md（除非作者明示授权 L1 修订）
- 不要尝试在验收报告里立新 ADR
- 不要写"阶段 4 任务清单"（HANDOFF 仅"粗想"段）
- 不要把 STAGE_3_IMPLEMENTATION_LOG 内容直接复制粘贴到 ACCEPTANCE.md（汇总 + 引用即可）

# A 阶段完成标志

- /docs/STAGE_3_ACCEPTANCE.md 完整（≤ 500 行参考阶段 2 体量）
- /docs/HANDOFF_STAGE_3_TO_4.md v0.1 草稿（≤ 300 行参考阶段 2 体量）
- commit message: `docs: Stage 3 acceptance report + Stage 3 → 4 handoff draft (T-3.12)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR

# B / C 阶段（跳 BC 破例第 5 类适用）

- 沿用阶段 2 T-2.13 跳 BC 破例先例 — 作者明示授权跳 B/C 直接 merge
- L2 quick check：核对完成判定五指标 / R3.X 遗留分类 / 阶段 4 启动前置条件
- 作者签字 + merge → 阶段 3 收官；阶段 4 规划师可启动
- 如作者发现实质问题（如完成判定错算 / 遗留项错放）则回 A 阶段重做
```

---

## 9. 跨边界事项（X 系列）

| 编号 | 内容 | 处理时机 | v1.0 状态 |
|---|---|---|---|
| **X1** | ADR-022 ~ 026 立项不在 v1.0 commit 范围 — v1.0 仅识别决策核心；实际立项动作由作者起 T-3.1 paste-ready prompt L3 执行会话落 `/docs/DECISIONS.md` | T-3.1 启动后立 | ⏳ 待 T-3.1 |
| **X2** | ADR-020 v0.2 修订（"审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy" 写进 ADR）—— 未来 X 级元任务（阶段 2 收官遗留 X4）| 阶段 3 起手期作者另起 L1 修订会话；不阻塞 | ⏸ 不阻塞 |
| **X3** | ROADMAP §阶段 2 「单次生成人工可接受率 ≥ 70%」字面措辞与 feedback memory（推迟到阶段 4）冲突 —— 同 X2 | 同 X2 | ⏸ 不阻塞 |
| **X4** | ADR-011 / 013「google.genai 是唯一 Gemini 入口」假设随 R2.7 PoloAIProvider 接入实质破裂 —— 待修订 | 阶段 3 / 4 视需要立 X 级元任务 | ⏸ 不阻塞 |
| **X5** | 阶段 4 启动闸门清单 — 阶段 3 完成后由阶段 4 规划师承接（参 synthesis §9.6 playtest bots 阶段位 / §9.8 开源剥离边界）| 阶段 4 规划师 | ⏸ 不阻塞 |
| **X6** | 阶段 1.5 R1.5-1~6 遗留（剩余 14 立绘 + 1 background 全 batch / acceptance_rate 未测 / 视觉判官 vs 作者 kappa 未算 / C4 parity smoke 未跑 / alpha 不透明 / mini probe ergonomic）—— 阶段 3 实测期触发是否补 14 立绘取决于实测场景集 | 阶段 3 实测期 / 阶段 4 | ⏸ 视需要 |
| **X7** | ROADMAP §阶段 3 完成标志措辞需修订 — "每次修改记 git commit + scene 内 version metadata 字段" 与 v1.0 阈值表（"每个入库 scene 必须有 version sidecar" + 放弃自动 git commit）字面冲突；F7 落地需 ROADMAP 同步修订 | 阶段 3 中段 / 末期作者另起 L1 修订会话 | ⏸ 不阻塞 |

**v1.0 整合关闭的 X 项**：

- **X1（v0.1）路径自引用** → v1.0 §8 paste-ready prompts 全文路径替换完成（F1 关闭）

---

## 10. 修订记录

- **2026-05-08 v1.0**：整合 v0.1 草稿（[`reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md`](reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md)）+ GPT-5.5 cross-LLM critique 22 finding（[`reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md`](reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md)）+ Claude round 2 response（[`reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md`](reviews/master_plan/2026-05-08_STAGE_3_TASKS_round2_claude_response.md)）+ 作者拍板（F1 / F2 / F8）。
  - 22 finding 处理对照表见 §0.1
  - 任务拆分变化（13 → 15 槽位）见 §0.2
  - 决策表 D1 ~ D10 修订见 §2.1
  - ADR 决策核心 ADR-022 ~ ADR-026 修订见 §3.1 ~ §3.5
  - wave 图修订见 §6
  - paste-ready prompts §8 待逐个 Edit 追加（v1.0 分段落盘策略，与 v0.1 草稿同款；规避 ECONNRESET 风险）

---

## 11. 版本

本文件版本：v1.0
最后更新：2026-05-08
产出方：阶段 3 L2 整合规划师会话（claude/sweet-bardeen-863720 worktree）
基于：v0.1 草稿 + GPT-5.5 cross-LLM critique + Claude round 2 response + 作者 2026-05-08 三议题拍板
