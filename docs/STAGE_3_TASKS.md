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
| **审美层 review 激活前置（2026-05-09 v0.2 新增；2026-05-13 v1.0.2 T-3X-1 拆分校准）** | T-3X-0 AESTHETIC_PREFERENCES.md v0.1 已 commit + **T-3X-1a**（ADR-030 字段集 + AestheticPreference schema + prompt hook）已 merge + **T-3X-1b**（ADR-031 NPC 状态机 schema + engine 执行器 + generator + validator）已 merge | 决策档 v0.2 §6.2 + ADR-031 草案 §2 拆分判断 |
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

## 1.7 量化矩阵（2026-05-13 L2 措辞清算后；作者拍板）

| 量化轴 | 拍板值 | 来源 |
|---|---|---|
| 总场景数 | 10-100 | ADR-010 v0.2 |
| 每场景节点数 | 3-6 | 作者 2026-05-13 拍板 |
| 每节点 option 数 | 3-6 | DEBATE §1 |
| 选项 diverge 度 | 每节点 1-3 个 diverge 选项（导向真正独立子树） | 作者 2026-05-13 拍板 |
| 路线分支密度 | 每场景 1-3 个独立入口路线（基于前置 state） | 作者 2026-05-13 拍板 |
| 每场景候选稿数 | 1-3 可设置（默认 1） | 作者 2026-05-13 拍板 |
| 主线 ending 数 | 2-5 | 作者已知 |

**总节点数估算**：10-100 场景 × 3-6 节点 × 1-3 候选稿 × 1-3 路线 = 30-5400 节点（量级跨度大，取决于路线分支密度 × 候选稿数策略）。

**新术语定义**：

- **选项 diverge 度** = 一个节点的 N 个 options 中有多少导向真正独立的子树（vs 收敛回主线）。100% 收敛 = 线性剧情；100% diverge = 每选项独立分支。
- **路线分支密度** = 同一场景在不同前置 state 下打开的独立入口路线数。密度 1 = 所有玩家看到同一段戏；密度 N = N 条完全独立路线。
- **候选稿数** = 同一场景 generator 同时跑几个 candidate dialogue_graph 让作者审稿挑（默认 1 = 不挑稿；2-3 = 关键场景多稿挑选）。

**用法**：generator CLI 后续应支持 `--candidates 1|2|3` 等 flag；audit 时按本矩阵核对内容规模 / token cost / 接受率分母。

**替代措辞**：本矩阵替代 ADR-031 v0.1 + DEBATE §10 中"multi-variant" / "海量预生成" / "伪即兴体验"三个不可检验修辞。

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

**2026-05-09 修订（审美层决策 v0.2 §6.2 §3.1 联动）**：

- ADR-022 决策核心**不动**（playtest bots 完成标志阈值原 gate 保留；决策档 v0.2 §6.6）
- T-3.10 启动前置 T-3X-0/1 落地（AESTHETIC_PREFERENCES.md + ADR-030 schema + prompt hook）；详 [/docs/DECISIONS.md](DECISIONS.md) ADR-030 + ADR-020 v0.2（PR-A 已落地）+ [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2
- 审美层 [A]ccept rate gate（≥ 60% pilot + Wilson CI）基于已结构化 AESTHETIC_PREFERENCES.md + ADR-030 schema 字段集**真作 gate**（不再是"假设作者锚点已建立"的悬空阈值）

**2026-05-13 修订（ADR-031 GM 抉择空间结构化方案 联动）**：

- ADR-022 决策核心**仍不动**（playtest bots 完成标志阈值原 gate 保留）
- ADR-031 新立（GM 抉择空间结构化方案；推荐 D 混合 A+B）—— 详 [/docs/DECISIONS.md](DECISIONS.md) ADR-031 + 草案 [/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1
- T-3X-1 拆分为 **T-3X-1a**（ADR-030 字段集）+ **T-3X-1b**（ADR-031 NPC 状态机机制）—— 详 §6 wave 图 + §7 任务清单
- 核心赌注首次明文承认（详 [/docs/DEBATE_NOTES.md](DEBATE_NOTES.md) §10）+ 4 档回退路径
- playtest bots（ADR-022）实测可包含 NPC 状态机 transition 覆盖率（5 persona × 20 paths 实测时一并测）

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
Wave 0（独立可并行；不阻塞下游工程任务）:
   T-3.0    [A]   起手清理 PATCH（R3.0/3.1/3.2 阶段 2 三遗留 + R3.3 mini calibration 并入）
   T-3.11   [A]   开源剥离边界清单 v0.2 增量（C5）
   T-3.8a   [A]   version_recorder.py 独立模块（F12 修订；与 batch_scheduler 解耦）
   T-3X-0   [非工程] 作者审美锚点工程（2026-05-09 v0.2 新增；不走 ABC；作者本人；时长 1-3 周；不阻塞其他工程任务）
   ↓ 不阻塞下游工程

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
   ↓ PR merge 后 Wave 6.5 才能启动

Wave 6.5a（T-3X-0 完成后启动；与 6.5b 软依赖 / 可并行；T-3.10 前置）:
   T-3X-1a  [B-author-gate]  AestheticPreference schema 字段集实证归纳 + schema 落地 + prompt hook（基于 T-3X-0 产出 AESTHETIC_PREFERENCES.md v0.1；ADR-030 字段集落地）
   ↓ PR merge 后 Wave 7 才能启动（与 6.5b 同步条件）

Wave 6.5b（与 6.5a 可并行；T-3.10 前置）:
   T-3X-1b  [B-author-gate]  NPC 状态机 schema + engine 查表执行器 + generator 增强 + validator 扩展（ADR-031 GM 抉择空间结构化 落地）
   ↓ PR merge 后 Wave 7 才能启动（与 6.5a 同步条件）

Wave 7（实测期；A 阶段实测；变体 ABC）:
   T-3.10   [A]   完成标志实测（依赖 T-3X-1a + T-3X-1b + T-3.5 + T-3.6a + T-3.6b + T-3.4 全部 PR merge；**v1.0.2 新增依赖 T-3X-1b**）
   ↓ PR merge 后 Wave 8 才能启动

Wave 8（验收）:
   T-3.12   [B]   阶段 3 验收报告（[B-author-gate]；跳 BC 破例第 5 类）
```

**v1.0 修订要点**：

- **T-3.5 不依赖 T-3.4**（F13）：调度器与 playtest 解耦；T-3.4 与 T-3.5 并行
- **T-3.8 拆 a/b**（F12）：T-3.8a version_recorder.py 独立 Wave 0；T-3.8b batch_scheduler hook 合并入 T-3.5（不再独立任务）
- **T-3.6 拆 a/b**（F16）：T-3.6a MVP 在 Wave 5；T-3.6b integrations 在 Wave 6
- **T-3.9 改先 helper 库交付**（F6）：T-3.9 在 Wave 3 与 T-3.3 / T-3.4 / T-3.7 并行；T-3.5 调用 T-3.9 helper（写入顺序 = write scene → assign chapter → write deps → record version）

**v1.0.1 修订要点（2026-05-12 审美层决策 v0.2 §6.2 联动）**：

- **Wave 0 加 T-3X-0**：非工程任务（作者审美锚点工程；不走 ABC；时长 1-3 周；不阻塞其他工程任务）
- **新增 Wave 6.5**：T-3X-1 工程（ADR-030 立项 + schema + prompt hook 基于 T-3X-0 实证归纳；走 ABC）
- **Wave 7 T-3.10 依赖追加**：T-3X-1 PR merge + T-3X-0 commit（AESTHETIC_PREFERENCES.md v0.1）；审美层 [A] gate 真作 gate

**v1.0.2 修订要点（2026-05-13 ADR-031 GM 抉择空间结构化方案 联动）**：

- **T-3X-1 拆为 T-3X-1a + T-3X-1b**：a = ADR-030 字段集（轻量）；b = ADR-031 NPC 状态机机制（含 schema + engine + generator + validator）
- **Wave 6.5 拆为 6.5a + 6.5b**：可并行（软依赖，b 可借鉴 a 的字段命名）；同步条件 = 两者都 merge → Wave 7
- **Wave 7 T-3.10 依赖追加**：T-3X-1b PR merge（NPC 状态机机制是审美层 [A] gate 真作 gate 的前提）

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
| **T-3X-0** | **非工程任务**（作者本人；不走 ABC；不需要 L3 执行会话）| 作者审美锚点工程 — 读 3 部经典（Deadlight + Crimson Letters + 极乐迪斯科原版）+ 填阅读对照表 + 产出 /docs/AESTHETIC_PREFERENCES.md v0.1；指引详 决策档 v0.2 §7 | `/docs/AESTHETIC_PREFERENCES.md`（新建）+ `/docs/reviews/aesthetic/T-3X-0_<work>_reading.md`（三份）| 无 | N/A（非工程；不走 ABC）|
| **T-3X-1a** | [B-author-gate] | AestheticPreference schema 字段集实证归纳 + schema 落地 + prompt hook（基于 T-3X-0 产出 AESTHETIC_PREFERENCES.md v0.1；ADR-030 字段集落地）| `/schema/aesthetic_preference.schema.json`（新建首版 0.4.0）+ `/generator/scene_strategies.py`（aesthetic_preference_context 注入段）+ `/generator/prompts/scene/`（注入段）+ `/generator/tests/` + `/docs/AESTHETIC_PREFERENCES.md`（追加 §10 v0.2 字段集归纳段；不重写 v0.1） | T-3X-0 完成（AESTHETIC_PREFERENCES.md v0.1 已 commit）| ❌ 默认 ABC |
| **T-3X-1b** | [B-author-gate] | NPC 状态机 schema + engine 查表执行器 + generator 增强 + validator 扩展（ADR-031 GM 抉择空间结构化 落地）| `/schema/npc_state_machine.schema.json`（新建首版 0.4.0）+ `/engine/npc_state_machine.py`（新建；≤ 80 行；严守 DEBATE §5 极简）+ `/generator/scene_strategies.py`（NPC 状态机生成段；与 T-3X-1a 注入段共存）+ `/generator/prompts/scene/`（NPC 状态机 prompt 模板）+ `/validator/npc_state_machine_validator.py`（新建；闭合性 + 不可达 + 死锁 + 一致性）+ `/generator/tests/` + `/engine/tests/` + `/validator/tests/` + `/schema/tests/` | T-3X-0 完成 + 与 T-3X-1a 软依赖（可并行；b 借鉴 a 字段命名）| ❌ 默认 ABC |

**任务总数**：**14 条编号槽位** = 11 个 paste-ready prompt（T-3.0/3.3/3.4/3.5/3.6a/3.6b/3.7/3.8a/3.9/3.10/3.11）+ T-3.1 ADR 立项 + T-3.2 schema + T-3.12 验收报告。

> **注**：T-3.8b 不单独编号——其范围（batch_scheduler hook 写入 version sidecar）合并入 T-3.5（详 §6 wave 4 + §8 T-3.5 prompt）。

> **T-3X / T-3X 系列（2026-05-09 审美层决策 v0.2 §6.2 新增）**：T-3X-0（非工程；作者本人审美锚点工程）+ T-3X-1（工程；ADR-030 + schema + prompt hook 基于 T-3X-0 实证归纳）共同作为 T-3.10 前置任务。命名 "T-3X" 是 L2 校准会话标签（T-3X L2 校准产出），**并列于 T-3 主线工程任务**（不是 T-3 主线子集；与 T-3.6a / T-3.6b 拆任务的子级语义不同）。详 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §5 关键决策点 8 + §6.2。

> **T-3X-1 拆分（2026-05-13 ADR-031 联动）**：T-3X-1 原计划单任务（ADR-030 字段集 + prompt hook）现拆为 **T-3X-1a**（ADR-030 字段集；轻量）+ **T-3X-1b**（ADR-031 NPC 状态机；含 schema + engine + generator + validator）。理由：a / b 性质完全不同（前者数据字典；后者执行抽象）；可并行（软依赖）；风险解耦；与现有 PR-A/B/C/D 拆 ABC 流程同款体例。详 [/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1 §2 T-3X-1 拆分判断。

---

## 8. T-3.X paste-ready 执行会话 prompt 索引（v0.4 工作流；prompt 文件化）

> **v0.4 工作流**（2026-05-08 起；详见 [/docs/governance.md](governance.md) §11）：每个 L3 任务的 paste-ready prompt 单独存为文件，便于复盘 + 跨阶段对比 + 单文件修订。详见 [/docs/prompts/README.md](prompts/README.md)。
>
> **L3 会话起步标准格式**：
>
> **最简版**：`执行 T-3.X`
>
> **明示版**（推荐；避免歧义）：`请按 /docs/prompts/stage_3/T-3.X.md 的指示执行任务。`

| 任务 | 文件 | Wave | 类型 |
|---|---|---|---|
| T-3.0 起手清理 PATCH（R3.0/3.1/3.2 阶段 2 三遗留 + R3.3 mini calibration） | [T-3.0.md](prompts/stage_3/T-3.0.md) | 0 | [A-execute] |
| T-3.1 ADR-022 ~ ADR-026 立项 | [T-3.1.md](prompts/stage_3/T-3.1.md) | 1 | [B-author-gate] |
| T-3.2 content_dependency_index sidecar schema | [T-3.2.md](prompts/stage_3/T-3.2.md) | 2 | [B-author-gate] |
| T-3.3 长对话一致性 C 起步（SceneGraphContext + token metrics） | [T-3.3.md](prompts/stage_3/T-3.3.md) | 3 | [A-execute] |
| T-3.4 playtest bots 框架（calibration + severity + run_manifest + 双层输出） | [T-3.4.md](prompts/stage_3/T-3.4.md) | 3 | [A-execute] |
| T-3.5 批量生成调度器（含 T-3.8b batch_scheduler hook 范围） | [T-3.5.md](prompts/stage_3/T-3.5.md) | 4 | [A-execute] |
| T-3.6a 审阅 UI MVP | [T-3.6a.md](prompts/stage_3/T-3.6a.md) | 5 | [A-execute] |
| T-3.6b 审阅 UI integrations | [T-3.6b.md](prompts/stage_3/T-3.6b.md) | 6 | [A-execute] |
| T-3.7 一致性维护（dep_index trace 反向 propagate） | [T-3.7.md](prompts/stage_3/T-3.7.md) | 3 | [A-execute] |
| T-3.8a version_recorder.py 独立模块 | [T-3.8a.md](prompts/stage_3/T-3.8a.md) | 0 | [A-execute] |
| T-3.9 Chapter/Act helper 库 | [T-3.9.md](prompts/stage_3/T-3.9.md) | 3 | [A-execute] |
| T-3.10 完成标志实测（实测期 ≈ 1 周） | [T-3.10.md](prompts/stage_3/T-3.10.md) | 7 | [A-execute] |
| T-3.11 开源剥离边界 v0.2 增量 | [T-3.11.md](prompts/stage_3/T-3.11.md) | 0 | [A-execute] |
| T-3.12 阶段 3 验收报告 | [T-3.12.md](prompts/stage_3/T-3.12.md) | 8 | [B-author-gate] |

完整任务清单 / wave 依赖图 / 模块边界详情见 §6 Wave 图 + §7 任务总表。

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
- **2026-05-12 v1.0.1**：审美层决策 v0.2 §6.2 吸收。修订点：§1 完成标志表新增 T-3X-0/1 前置条件行（保留 [A] ≥ 60% pilot + Wilson CI 原阈值）+ §3.1 ADR-022 决策核心追加 2026-05-09 联动修订段（不动 ADR-022 决策核心）+ §6 wave 图新增 Wave 6.5（T-3X-1）+ T-3X-0 进 Wave 0 + §7 任务清单新增 T-3X-0（非工程；不走 ABC）+ T-3X-1（[B-author-gate]；走 ABC）+ T-3.10 paste-ready prompt 修订为基于 AESTHETIC_PREFERENCES.md + ADR-030 跑。来源：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.2。联动 PR-A（已 merge；PR #51 dd82131）+ PR-B（ROADMAP + HANDOFF；后续启动）。L1 fixation 执行会话产出（本 PR）。
- **2026-05-13 v1.0.2**：ADR-031 GM 抉择空间结构化方案 立项 + T-3X-1 拆分校准。修订点：§1 完成标志表"审美层 review 激活前置"行更新为 T-3X-1a + T-3X-1b 依赖 + §3.1 ADR-022 决策核心追加 2026-05-13 联动修订段（ADR-022 仍不动）+ §6 wave 图 Wave 6.5 拆为 6.5a + 6.5b + Wave 7 T-3.10 依赖追加 T-3X-1b + §6 末新增 v1.0.2 修订要点子段 + §7 任务清单 T-3X-1 拆为 T-3X-1a + T-3X-1b 两行 + §7 末追加 T-3X-1 拆分注脚。来源：[/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md](reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md) v0.1 + 作者 2026-05-13 拍板。联动 L1 fixation：DECISIONS ADR-031 + DEBATE_NOTES §10 + ROADMAP §阶段 3 时长（5-9 → 6-11 周）。L1 fixation 执行会话产出（本 PR）。

---

## 11. 版本

本文件版本：v1.0.2
最后更新：2026-05-13
产出方：阶段 3 L2 整合规划师会话（claude/sweet-bardeen-863720 worktree）
v1.0.1 修订产出方：L1 fixation 执行会话（本 PR；T-3X L2 校准产出 paste-ready prompt 落地）
v1.0.2 修订产出方：L1 fixation 执行会话（本 PR；ADR-031 + T-3X-1 拆分校准）
基于：v0.1 草稿 + GPT-5.5 cross-LLM critique + Claude round 2 response + 作者 2026-05-08 三议题拍板
