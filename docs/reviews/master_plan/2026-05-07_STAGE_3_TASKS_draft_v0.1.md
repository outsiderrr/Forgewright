# STAGE_3_TASKS_draft_v0.1.md — 阶段 3 任务清单 L2 草稿

> 本文件是阶段 3 任务清单 v0.1 草稿。**不是** `/docs/STAGE_3_TASKS.md` 正式版——v0.1 经作者另起 cross-LLM critique 会话评审 + 整合 → v1.0 后才进 `/docs/STAGE_3_TASKS.md`，那是另一个 [B-author-gate] 任务。

**日期**：2026-05-07 · **版本**：v0.1 · **产出方**：阶段 3 L2 规划师会话（claude/sweet-bardeen-863720 worktree）

---

## 0. 文档说明

本文件 = 阶段 3 任务清单 L2 草稿。整合自：

- `/docs/HANDOFF_STAGE_2_TO_3.md` v0.1（阶段 2 验收会话 T-2.13 产出）
- `/docs/ROADMAP.md` §阶段 3（含 Round 5 综合后完成标志强化项 5 项 + 强建议 2 项）
- `/docs/reviews/master_plan/2026-04-30_synthesis.md` §7 阶段 3 启动前置 + §9 综合开放决策
- `/docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md` §5 + §7（U-CL-5 长对话一致性 + 作者态度记录）
- `/docs/reviews/master_plan/2026-05-01_review_routine_governance.md` v0.3 §10（ABC 三阶段流程）
- `/docs/STAGE_2_ACCEPTANCE.md` §4 R2.X 遗留 + §5 阶段 3 启动闸门
- 阶段 2 实战经验（13 主任务 ABC 闭环 + 13 跳 BC 破例 PR）

**Wave 校准记录**：

- Wave 1（2026-05-07）：阅读 12 份必读 + 上下文确认报告
- Wave 2（2026-05-07）：与作者校准 10 项决策——D1 playtest 阈值 / D2 dep_index sidecar / D3 完成标志双指标 / D4 长对话 C 起步 + A/B hook / D5 审阅 UI Web 单页 + 5 视图 / D6 调度器 asyncio N=3 / D7 跳 BC 破例类型枚举 / D8 R3.X follow-up 占位机制 / D9 双轨命名 baseline_NNN + playtest_NNN / D10 拆 5 条 ADR
- Wave 3（2026-05-07）：本草稿落盘

**Wave 4**（不在本会话）：作者另起 GPT-5.5 / Codex 跑 cross-LLM critique → `/docs/reviews/master_plan/2026-05-XX_STAGE_3_TASKS_draft_gpt_critique.md`；作者再起新一轮 L2 整合会话产 v1.0 → `/docs/STAGE_3_TASKS.md`（[B-author-gate]）。

---

## 1. 阶段 3 目标回顾

来自 [/docs/ROADMAP.md](../../ROADMAP.md) §阶段 3：

**目标函数**：作者能每天稳定产出几千字质量达标的剧情内容。

**完成标志（ROADMAP 字面）**：

- 批量生成调度器（异步跑多场景）
- 审阅界面（Web 或桌面，左内容右批准/打回）
- 一致性维护（本体变更时标记需重审的已生成内容）
- 版本控制集成（每次修改记版本）
- 作者实际跑一周，完成至少 10 个场景的生成 + 审阅 + 入库

**完成标志强化项（Round 5 综合后 — synthesis §7）**：

- **C2** ADR-009 第三层 playtest bots 写入完成标志 — 至少 N 个 bot persona / 每场景 M 条模拟路径 / 输出 worst-10% 场景清单
- **C6** 内容依赖索引（`content_dependency_index` sidecar）—— 本体变更时定向反向 propagate
- **U-CL-1** 完成标志加质量门槛指标 — 在 ≥X% 单次接受率下作者每周稳定吞吐 Y 场景
- **U-CL-5** 长对话一致性缓解策略 ADR / 任务 — DEBATE_NOTES §9.2 落地
- **U-GPT-7** 审阅 UI 第一版含图视图 — graph/mermaid/dot + 路径列表 + validator issues + visual asset thumbnail

**v0.1 拍板的完成标志**（§2.1 D1/D3/D5 阈值化）：

| 指标 | 阈值 | 来源 |
|---|---|---|
| 批量调度器 | asyncio + N=3 concurrent + token bucket + ontology file lock 落地 | D6 |
| 审阅 UI | Web 单页（FastAPI + vanilla JS）+ 5 视图齐全 + 复用 T-2.8 graph_views 三件套 | D5 |
| 一致性维护 | content_dependency_index sidecar 写入流水线 + 反向 propagate 工具 | D2 |
| 版本控制集成 | 每次修改记 git commit + scene 内 version metadata 字段 | T-3.8 |
| 实测吞吐 | 1 周 ≥10 场景 | ROADMAP 字面 |
| **gross_pass_rate** | **≥ 80%**（继承阶段 2 logic-layer proxy；阶段 3 prompt 调优后应保持高位） | D3 / U-CL-1 |
| **审美层 [A]ccept rate** | **≥ 60%**（阶段 3 激活 [A]/[R]/[S] feedback memory） | D3 / U-CL-1 |
| playtest bots 完整性 | 至少 5 场景跑过 5×20=100 paths/scene；worst-10% 清单产出 + 0 critical issue 或全部修复 | D1 / C2 |
| 长对话一致性 | C 起步：prompt GraphContext 注入 `prior_scene_summaries` 字段；A/B hook 留 `content_dependency_index.scene_history_referenced` 不实现 | D4 / U-CL-5 |

---

## 1.5 ABC 三阶段闭环（治理备忘 v0.3 §10 吸收 + 阶段 2 实证 + 跳 BC 破例清单）

### 1.5.1 三阶段定义（与阶段 2 STAGE_2_TASKS.md §1.5 一致）

- **A 开发阶段**：作者起 Claude Code worktree 会话；按对应 paste-ready prompt 开发 + 测试 + commit + push + 开 PR（base = `main`，head = worktree 分支名）。**A 阶段完成 ≠ L3 通过**。
- **B review 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作 review prompt 模板；review A 阶段 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-3.X_<topic>_review.md`。
- **C 修复阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）。

### 1.5.2 L2 验收

L2 拿 ABC 全部产出判断；过关 → 通知作者 merge PR + 进下一个 L3；打回 → 指定回 C 或回 B 跑二轮。

### 1.5.3 PR merge 硬规则

**A+B+C 全部完成 + L2 验收过关之前，PR 一律不 merge**——v0.3 治理备忘核心约束。

### 1.5.4 跳 BC 破例类型清单（v0.1 新增；D7）

> 阶段 2 收官期 13 个 PR 走作者明示授权跳 B/C 直接 merge 模式（参 `/docs/STAGE_2_ACCEPTANCE.md` §8.2）。阶段 3 在 v0.1 起手就**显式枚举可跳 BC 类型**，避免每条都问作者一遍。

**默认授权跳 BC 的 5 类**：

1. **R3.X follow-up**（baseline_NNN / playtest_NNN 反向触发的 generator/validator/provider 修复任务）
2. **baseline_NNN finding**（实证 batch run 暴露的工具链漏洞）
3. **playtest_NNN finding**（playtest bots 实证暴露的内容/工具链漏洞）
4. **审阅 UI 工坊化 ergonomic 改进**（仅前端文案 / 视图调整 / 不动后端 schema 与算法）
5. **阶段 3 验收报告**（T-3.12）

**跳 BC 模式工作流**：A 阶段会话主动修 + 拆 commit 标注 finding（如 `fix: R2.X xxx (baseline_NNN finding)`）+ L2 quick check + 作者授权 merge。

**默认 ABC 闭环**：T-3.X 主线（T-3.0 ~ T-3.11，除 T-3.10 实测）一律走完整 ABC。

### 1.5.5 routine 兼容性

- 所有 L3 一律 ABC 闭环——无论 §7 类型列标 [A-execute] 还是 [B-author-gate]
- routine 仅可用于 A 阶段串联（一个 L3 A 阶段完成后自动进下一个 L3 A 阶段）；**不可跨过 B/C/验收闭环**
- 不要尝试搭 git hook / GitHub Action 把 B/C 自动化——按 v0.3 governance §5，按当前频率手动跑性价比更高

---

## 2. 锁定的架构决策（Wave 2 校准 2026-05-07 闭环）

### 2.1 决策总表

| 决策 | 内容 | 来源 |
|---|---|---|
| **D1 playtest bots 阈值** | N=5 persona / M=20 paths/persona = 100 paths/scene；worst-10% 输出（按 LLM-as-judge 综合分数排序最低 10%）；持久化 persona 描述用 LLM 生成但调度路径决策仍 LLM 跑（避免硬编码不灵活、避免完全 fixture 不规模化）；**至少 5 场景跑过完整 playtest** 作完成标志 | C2 + D1 |
| **D2 content_dependency_index 形态** | per-scene sidecar `<scene>.deps.json`（与 visual manifest 哲学一致；扫盘 O(N) 起步）；新建 `/schema/content_dependency_index.schema.json` 首版 const `0.3.0`；阶段 3 末期实测如全扫成本不可接受再 v0.2 升级双写 | C6 + D2 |
| **D3 完成标志双指标** | gross_pass_rate ≥ 80%（继承阶段 2 logic-layer proxy）+ 审美层 [A]ccept rate ≥ 60%（阶段 3 激活）+ 1 周 ≥10 场景吞吐 | U-CL-1 + D3 |
| **D4 长对话一致性投入度** | C 起步全套：prompt 模板 GraphContext 注入 `prior_scene_summaries` 字段（作者人工填或半自动 LLM 摘要 + 作者校准）；A/B hook 留：content_dependency_index sidecar 含 `scene_history_referenced` 字段，阶段 3 末期实测撞墙时可基于此升级到 RAG (B) 或 memory stream (A) 不需重做 schema | U-CL-5 + D4 + PZ §7 作者态度 |
| **D5 审阅 UI 形态** | Web 单页（FastAPI 静态 server + 前端 vanilla HTML/JS + mermaid.js CDN；不引入 React/Vue/Svelte 框架降低开源门槛）；5 视图：(1) graph 视图（渲染 T-2.8 mermaid 文件）/ (2) 路径列表（entry → end 路径列举 + 高亮）/ (3) validator issues 面板（schema/topology/sampling/mechanical 四 tab）/ (4) visual asset thumbnail（读 manifest 显示出场角色立绘 + 场景背景）/ (5) 审美层 [A]/[R]/[S] 三按钮 + reason 文本框（写入 review_log.jsonl 兼容 T-2.8 接口）；read-only + 标注，不做编辑功能（编辑由作者直接改 JSON + git workflow） | U-GPT-7 + D5 |
| **D6 批量调度器并发模型** | asyncio + N=3 concurrent（基于 baseline_011 单 iter 268s 实测，N=3 → 10 场景总耗时 ≈18 分钟）+ 每 provider token bucket 速率限制（默认 60 RPM，env 可配）+ ontology 写入 file lock（fcntl）；scene 文件各自独立 path 不冲突 | D6 |
| **D7 跳 BC 破例类型枚举** | 5 类：R3.X follow-up / baseline_NNN finding / playtest_NNN finding / 审阅 UI ergonomic 改进 / 阶段 3 验收报告（详 §1.5.4） | 阶段 2 实战经验 + D7 |
| **D8 R3.X follow-up 占位机制** | §5 设独立"R3.X follow-up 候选清单"段，初始空但留模板；阶段 2 R2-5 / R2-10c / R2-iter-逃逸 三项作为 R3.0 起步固化，并入 T-3.0 起手清理 PATCH | D8 |
| **D9 双轨命名 baseline_NNN + playtest_NNN** | `baseline_NNN` 续延（阶段 2 终止 baseline_011；阶段 3 续编号 baseline_012+，仅 generator 工具链回归测试）+ `playtest_NNN` 新建（阶段 3 起步编号 playtest_001，仅 playtest bots 跑批）；两者各自 cost log 独立 | D9 |
| **D10 ADR-022~026 拆 5 条** | ADR-022 playtest bots / ADR-023 content_dependency_index / ADR-024 长对话一致性 C 起步 + A/B hook / ADR-025 审阅 UI 架构 / ADR-026 批量调度器并发模型；T-3.1 一次性 commit（与 T-2.1 同款先例 commit `df05431`）；Chapter/Act 不立新 ADR（T-2.2 schema 已落地，ADR-016 后果段已涵盖）；C5 OPEN_SOURCE_CARVE_OUT_INDEX 不立新 ADR（T-2.10 v0.1 已落地，阶段 3 维护增量） | D10 |

### 2.2 阶段 2 实战吸收（硬背景输入）

- **R2.X follow-up 跳 BC 破例模式**实战 13 个 PR 已验证有效（参 STAGE_2_ACCEPTANCE.md §8.2）；阶段 3 工程债低于阶段 2，跳 BC 频率应自然下降，但 §1.5.4 显式枚举降低协商成本
- **L2 整合规划师 + 阶段验收角色**实证有效（阶段 2 收官期形成）；阶段 3 同款角色继承
- **Provider 仪表化习惯**（R2.9 ProviderError.from_exception + scene_results.jsonl failure_metadata）阶段 3 多场景并行调度时同款必要——T-3.5 调度器必须对每个并发 worker 仪表化
- **抽公共模块的克制粒度**（R2.8 共享 sanitizer + R2.10b 共享 retry policy 但 predicate 各自）—— 阶段 3 多 provider 工作流维持同款抽取风格
- **schema 版本号策略**（ADR-016 §schema 版本号；阶段 2 §2.4 实战）—— 阶段 3 新建 `/schema/content_dependency_index.schema.json` 首版 const `0.3.0`；既有 dialogue_graph / node / character / location / clock / chapter 等 schema 全部不动

### 2.3 作者态度（PZ §7 硬背景输入 — U-CL-5 投入度边界）

- **对 AI 进化能力有信心**——尤其"判断已有上下文 + 逻辑自洽"——影响 U-CL-5 缓解 ADR 紧迫度（D4 选 C 起步 + A/B hook，不投入 hybrid (A+C) 完整方案）
- **50–100 场景规模可能不撞 §9.2 真墙**——ADR-010 锁定的 MVP 规模未必积累到 84K token 状态量级；这判断**未验证**，等阶段 3 实测一周 10 场景的真实 token 累积曲线后才能确认
- **状态文件抽象层"真遇到再说"，不预防性设计**——但 L2 必须保留 hook（D4 中 content_dependency_index.scene_history_referenced 字段即此 hook）
- **与 ADR-004 极简精神一致**

### 2.4 跨任务一致性细节统一

| 字段 / 命名 | 取值 |
|---|---|
| 长对话一致性 prompt context 字段名 | `prior_scene_summaries: list[{scene_id, summary, key_state_paths}]`（GraphContext 新增字段；T-3.3 落地） |
| dep_index sidecar 文件名格式 | `<scene>.deps.json`（与 scene.json 同目录） |
| 调度器并发参数 | env `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 `3`），`FORGEWRIGHT_PROVIDER_RPM`（默认 `60`） |
| review UI 端口 | env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 `8765`） |
| playtest bots persona 来源 | `/generator/playtest/personas/<persona_id>.json`（v0.1 先 hand-write 5 个 + LLM augment description） |
| baseline / playtest cost log 分离 | `/generator/cost_log.jsonl`（generator 主流程）+ `/generator/playtest_cost_log.jsonl`（T-3.4 新建） |

---

## 3. 推荐立项的 ADR 清单（候选 ADR-022 ~ ADR-026；v0.1 整合）

> L2 不立 ADR；这里只识别"该立哪些"。由作者明示授权后由 T-3.1（[B-author-gate]）一次性立完。参考 ADR-011/012/013 一次性立 3 条先例（commit `1d2030f`）+ ADR-016~021 一次性立 6 条先例（commit `df05431`）。
>
> **跨边界提醒（X1）**：5 条 ADR 立项**不在 v0.1 草稿范围**——v0.1 仅识别 + 描述决策核心；实际立项动作由 v1.0 commit 后作者另起 L3 执行会话跑 T-3.1 paste-ready prompt 落 `/docs/DECISIONS.md`。详 §9 X1。

| 候选 | 议题 | 决策核心 |
|---|---|---|
| **ADR-022** | playtest bots 完成标志阈值 | 详下 |
| **ADR-023** | content_dependency_index sidecar 形态 + 字段集 | 详下 |
| **ADR-024** | 长对话一致性 C 起步 + A/B hook | 详下 |
| **ADR-025** | 审阅 UI 架构 | 详下 |
| **ADR-026** | 批量调度器并发模型 | 详下 |

### ADR-022 决策核心 — playtest bots 完成标志阈值

- **bot persona 数 N=5**：cautious / aggressive / completionist / speedrunner / role-player（v0.1 hand-write 5 个 persona 描述 + LLM augment 细节；未来 N 由阶段 3 实测倒推 v0.2 修订）
- **每场景 paths M=20**：每 persona 跑 20 条路径 = 100 paths/scene；与 ADR-021 §2B 抽样 N=100 数量级一致，复用 sampling 框架
- **persona 描述**：hand-write base + LLM augment（避免硬编码不灵活）；**调度路径决策仍 LLM 跑**（每 path 让 LLM 扮演 persona 在 entry → end 之间真实选项）
- **worst-10% 输出**：每场景按 LLM-as-judge 综合分数排序最低 10%；输出 `playtest_NNN/worst_paths.jsonl`（含 path trace + judge score + critical issue）
- **完成标志**：至少 5 场景跑过完整 playtest（5×20=100 paths/scene），worst-10% 清单产出 + 作者审阅 0 critical issue 或 critical issue 全部修复
- **替代方案及否决理由**：
  - 完全 fixture persona：不灵活；规模化时手写 persona 库爆炸
  - 完全 LLM 生成 persona：递归依赖 + 不可重现
  - N=10 persona / M=50 paths：成本爆炸（500 paths/scene × 5 场景 = 2500 LLM 调用）；阶段 3 起步 5×20=100 已与 ADR-021 §2B 数量级一致
- **后果**：
  - T-3.4 落地 `/generator/playtest/`（playtest bots 框架 + persona 库 + 跑批 CLI）
  - playtest cost log 独立 `/generator/playtest_cost_log.jsonl`
  - 阶段 3 末期实测如 5 persona 不足以暴露 worst-bucket，由 ADR-022 v0.2 修订倒推

### ADR-023 决策核心 — content_dependency_index sidecar 形态

- **形态**：per-scene sidecar `<scene>.deps.json`（与 scene.json 同目录；与 visual manifest 哲学一致）
- **schema 字段集**：

```json
{
  "schema_version": "0.3.0",
  "scene_id": "...",
  "generated_at": "...",
  "ontology_ids_read": ["char_vellin", "scene_waystation_of_iron_oath", ...],
  "state_paths_read": ["relationship.vellin.trust", "world.scene_count", ...],
  "state_paths_written": ["flag.player_saw_blood_letter", ...],
  "prompt_template_hash": "sha256:...",
  "visual_asset_ids_referenced": ["img_vellin_neutral_torso_up_01", ...],
  "clock_ids_referenced": ["clk_iron_oath_decay", ...],
  "chapter_id": "chap_act1_iron_oath",
  "act_id": "act1_arrival",
  "scene_history_referenced": ["<scene_id>", ...]
}
```

- **新建 `/schema/content_dependency_index.schema.json`** 首版 const `0.3.0`（与 character/location/clock/chapter schema 同源演进）
- **写入时机**：T-3.5 批量调度器在 generate_scene 完成后同步写 sidecar；T-3.7 一致性维护工具按 sidecar 反向 propagate
- **`scene_history_referenced` 字段** = D4 长对话一致性 hook：阶段 3 末期如撞墙，可基于此字段升级到 RAG (B) 或 memory stream (A) 不需重做 schema
- **替代方案及否决理由**：
  - 全局索引 `/content/index/dependencies.json`：单文件查询 O(1)；但写并发风险高（multiple generator 实例同时跑必须加 lock，与 sidecar 等价）；改主真相之源破 ADR-006 单一真相之源
  - SQLite 数据库：read-heavy 标准选择；但引入运行时 DB 依赖（哪怕只生产期）破 ADR-002/004 极简精神 + 开源用户门槛上升
  - sidecar：扫盘 O(N) 起步，10-50 场景规模完全可接受；阶段 3 末期实测如全扫成本不可接受再 v0.2 双写
- **后果**：
  - schema 落地（T-3.2）必须新建 content_dependency_index schema
  - generate_scene（T-3.5）落地后立刻 hook 写 sidecar
  - 一致性维护工具（T-3.7）实现 ontology 变更 → 反向查 sidecar → 标记 stale 场景流程

### ADR-024 决策核心 — 长对话一致性 C 起步 + A/B hook

- **C 起步全套**（author-side discipline）：
  - prompt 模板 GraphContext 注入 `prior_scene_summaries: list[{scene_id, summary, key_state_paths}]` 字段（T-3.3 落地）
  - 摘要来源：作者人工填 OR 半自动 LLM 摘要 + 作者校准（v0.1 起手两条路并存，看作者实际 ergonomic 偏好）
  - 上限：每场景 prompt 注入 ≤5 条 prior_scene_summaries（避免 prompt 膨胀）
- **A/B hook 留**：
  - content_dependency_index sidecar 含 `scene_history_referenced` 字段（ADR-023）
  - 阶段 3 末期实测如撞 §9.2 真墙，可基于此字段升级到 RAG (B) 或 memory stream (A) 不需重做 schema
- **不在阶段 3 落地的 A/B 方案**：
  - A. Generative Agents memory stream（Park 2023）—— 工程量极大 + 引入 embedding 依赖 + 与作者"不预防性设计"态度冲突
  - B. RAG over event log —— 与 ADR-006 单一真相之源紧密耦合，event log 形态需新立 schema
- **替代方案及否决理由**：
  - 完整 D hybrid (A+C)：synthesis 推荐，但工程量与 A 接近；与 PZ §7 作者态度（不预防性设计）冲突
  - 不立 ADR：DEBATE §9.2 列为未解问题但路线图无任何缓解任务（U-CL-5）—— 必须显式落地
- **后果**：
  - prompt 模板（T-3.3）必须支持 prior_scene_summaries context 注入
  - 阶段 3 实测一周 10 场景后，token 累积曲线 + 接受率回归是否撞墙作 ADR-024 v0.2 修订依据
  - PZ §7 作者态度记录（"50-100 场景可能不撞墙"）作为不升级 A/B 的兜底依据

### ADR-025 决策核心 — 审阅 UI 架构

- **形态**：Web 单页（local file server + 前端 vanilla HTML/JS）
- **工具栈**：FastAPI 静态 server（沿用现有 Python 生态）+ 前端 vanilla HTML/JS（不引入 React/Vue/Svelte 框架）+ mermaid.js CDN（渲染 graph 视图）
- **5 视图**：
  1. **graph 视图**：直接渲染 T-2.8 已生成的 mermaid 文件（`<batch_dir>/graph_views/<scene>.mermaid`）；mermaid.js CDN 客户端渲染
  2. **路径列表**：所有 entry → end 路径列举（复用 validator/sampling 输出）+ 点击高亮 graph
  3. **validator issues 面板**：schema / topology / sampling / mechanical 四 tab；展示 T-2.7 + T-2.4 校验结果
  4. **visual asset thumbnail**：读 manifest 显示出场角色立绘 + 场景背景
  5. **审美层标注**：[A]/[R]/[S] 三按钮 + reason 文本框；写入 `review_log.jsonl` 兼容 T-2.8 接口
- **read-only**：不做编辑功能；编辑由作者直接改 JSON + git workflow（与 ADR-006 真相之源 + 极简精神一致）
- **运行时部署**：仅生产期；env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 8765）；本地 localhost 访问
- **替代方案及否决理由**：
  - CLI 升级（T-2.8 scene_review_cli + graph_views）：投入最低；但 graph 可视化看 ASCII / mermaid 源码体验差
  - 桌面应用（electron / tauri）：投入最高；与作者单人开发节奏不匹配
  - React/Vue/Svelte 前端框架：开源用户门槛上升；vanilla HTML/JS 可读性高 + 零依赖
- **后果**：
  - T-3.6 落地 `/tools/review_ui/`（FastAPI server + 前端静态资源）
  - 复用 T-2.8 graph_views 三件套（mermaid + dot + ASCII）作为 graph 视图数据源
  - 不阻塞 T-3.10 实测——T-3.10 可同时用 scene_review_cli（CLI）和 review_ui（Web）

### ADR-026 决策核心 — 批量调度器并发模型

- **并发模型**：asyncio（Python 3.11+）+ N=3 concurrent worker
- **基础数据**：baseline_011 单 iter mean 268s（max 476s）→ N=3 时 10 场景总耗时 ≈18 分钟（10/3 × 268s ≈ 893s）
- **速率限制**：每 provider 加 token bucket（默认 60 RPM；env `FORGEWRIGHT_PROVIDER_RPM`）
- **ontology 写入并发安全**：file lock（fcntl）on `/state/ontology/<world>.json`；scene 文件各自独立 path 不冲突
- **失败传播**：单场景失败不阻塞其他并发场景（与阶段 2 R2.10b 退避策略一致）；每个并发 worker 独立 ProviderError 仪表化（沿用 R2.9）
- **配置**：
  - `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 `3`，env 可配）
  - `FORGEWRIGHT_PROVIDER_RPM`（默认 `60`，env 可配）
- **替代方案及否决理由**：
  - 串行（N=1）：10 场景 = 1–2.5 小时作者必须守着；ergonomic 差
  - asyncio + N=10 concurrent：撞 PoloAI 速率限制（baseline_008 教训：余额闸门 + 上游 Gemini 抖动）；并发越高 ROI 反而下降
  - subprocess fan-out（进程级隔离 N=3）：避免 Python GIL；但进程间 ontology 写入 file lock 同上需要 + 复杂度更高
- **后果**：
  - T-3.5 落地 `/generator/batch_scheduler.py`（asyncio worker pool + token bucket + ontology lock）
  - 阶段 3 实测如撞 PoloAI 余额闸门，作者可降 N=1/2 应急（env 配置即时生效）
  - 阶段 3 末期 ADR-026 v0.2 修订倒推真实最优 N

---

## 4. 启动闸门清单

### 4.1 ROADMAP §阶段 3 完成标志强化项映射（5 项）

- ✅ **C2** playtest bots 完成标志 → ADR-022 + T-3.4 落地（阈值 N=5 / M=20 / worst-10%）
- ✅ **C6** content_dependency_index → ADR-023 + T-3.2 schema + T-3.5 writer hook + T-3.7 反向 propagate
- ✅ **U-CL-1** 完成标志质量门槛 → §1 v0.1 阈值表（gross_pass_rate ≥ 80% + [A] rate ≥ 60% + Y=10 场景/周）
- ✅ **U-CL-5** 长对话一致性缓解 → ADR-024 + T-3.3（C 起步）+ ADR-023 hook（A/B 留）
- ✅ **U-GPT-7** 审阅 UI 含图视图 → ADR-025 + T-3.6（5 视图齐全）

### 4.2 HANDOFF v0.1 + STAGE_2_ACCEPTANCE 引入的额外起手项

- ✅ **C5 OPEN_SOURCE_CARVE_OUT_INDEX v0.2 增量** → T-3.11（阶段 2 v0.1 已 commit `eef3f3b`，阶段 3 维护增量；非新建）
- ✅ **R2-5 dimensions schema 修** → T-3.0 起手清理 PATCH（与 R2.X follow-up dispatch 合并）
- ✅ **R2-iter-逃逸 prompt 调优** → T-3.0 起手清理 PATCH
- ✅ **R2-10c 预飞 balance/health probe** → T-3.0 起手清理 PATCH
- ✅ **审美层 [A]/[R]/[S] 激活** → T-3.10 实测期作者使用 review_ui + scene_review_cli 双轨标 [A]/[R]/[S]；feedback memory `feedback_acceptance_review_deferred_to_stage_4.md` 作 background 输入
- ⏸ **X4 ADR-020 v0.2 修订**（"审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy" 写进 ADR）—— **未来 X 级元任务**（作者另起 L1 修订会话；阶段 3 内不阻塞）；详 §9 X2

---

## 5. R3.X follow-up 候选清单（v0.1 起步）

> 阶段 2 收官期 R2.X follow-up 系列（9 项；7 merged + 2 遗留）实证有效。阶段 3 v0.1 起步保留同款机制，初始空但 R3.0/R3.1/R3.2 由阶段 2 遗留固化（已并入 T-3.0）。

| 编号 | 内容 | 性质 | 状态 | 来源 |
|---|---|---|---|---|
| **R3.0** | scene_ai_judge dimensions schema 修（阶段 2 R2-5 推进） | prompt + dimensions schema 一致性 | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.1** | iter07/iter09/iter11 模型 json 模式逃逸 prompt 调优（阶段 2 R2-iter-逃逸 推进） | prompt 调优 | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.2** | scene_experiment 预飞 balance/health probe（阶段 2 R2-10c 推进） | 工作流 ergonomic | ⏳ T-3.0 起手并入 | STAGE_2_ACCEPTANCE §4 |
| **R3.X** | （阶段 3 实测产生的反向修复任务） | 待定 | （v0.1 留空，阶段 3 跑批生成） | baseline_NNN / playtest_NNN finding |

**编号规则**：从 R3.0 起；阶段 2 已用 R2.X 避免冲突；阶段 3 末期产生的 baseline_NNN finding / playtest_NNN finding / 反向修复 = R3.3+。

---

## 6. 工作 wave 与依赖图

```
Wave 0（独立可并行；不阻塞下游）:
   T-3.0  [A]   起手清理 PATCH（R3.0/R3.1/R3.2 并入；阶段 2 三遗留）
   T-3.11 [A]   开源剥离边界清单 v0.2 增量（C5）
   T-3.8  [A]   版本控制集成
   ↓ 不阻塞下游

Wave 1（串行关键路径起点）:
   T-3.1  [B]   ADR-022 ~ 026 立项（5 条 ADR 一次性 commit）
   ↓ PR merge 后 Wave 2 才能启动 A 阶段

Wave 2（串行关键路径）:
   T-3.2  [B]   content_dependency_index sidecar schema + writer hook（依赖 T-3.1 ADR-023）
   ↓ PR merge 后 Wave 3 才能启动

Wave 3（A 类可并行；T-3.3 / T-3.4 / T-3.7 三任务并行）:
   T-3.3  [A]   长对话一致性 C 起步（prompt GraphContext 注入 prior_scene_summaries；依赖 T-3.1 ADR-024）
   T-3.4  [A]   playtest bots 框架（5 persona / 20 paths / worst-10% 输出；依赖 T-3.1 ADR-022）
   T-3.7  [A]   一致性维护（基于 dep_index 反向 propagate；依赖 T-3.2）
   ↓ T-3.3 + T-3.4 PR merge 后 Wave 4 才能启动

Wave 4（依赖 T-3.3 + T-3.2 + T-3.4）:
   T-3.5  [A]   批量生成调度器（asyncio + N=3 + token bucket + ontology lock + dep_index writer 集成）
   T-3.9  [A]   Chapter/Act 容器生成扩展（generator 层 + scene_anchor 写入 chapter.acts）
   ↓ PR merge 后 Wave 5 才能启动

Wave 5（依赖 T-3.5 + T-3.4）:
   T-3.6  [A]   审阅 UI Web 单页（FastAPI + vanilla JS + 5 视图）
   ↓ PR merge 后 Wave 6 才能启动

Wave 6（实测期；A 阶段实测；不走完整 ABC，只走"实测 + 验收报告"）:
   T-3.10 [A]   完成标志实测（作者跑一周 ≥10 场景；gross_pass ≥ 80% + [A] ≥ 60%）
   ↓ PR merge 后 Wave 7 才能启动

Wave 7（验收）:
   T-3.12 [B]   阶段 3 验收报告（[B-author-gate]；跳 BC 破例第 5 类）
```

**routine 兼容性**（v0.3 治理修订；与阶段 2 一致）：

- 所有 L3 一律 ABC 闭环（§1.5），与本表 [A]/[B] 列无关——类型列仅作概念参考
- routine 仅可串联 **A 阶段**：一个 L3 A 阶段 commit + push + 开 PR 后，可自动跑下一个不冲突 L3 的 A 阶段
- routine **不可跨过 B/C/验收闭环**——任何 L3 PR 在 A+B+C 全部完成 + L2 验收过关前一律不 merge
- 实际并行度 = Wave 内 L3 的 A 阶段可同时跑；但 Wave 间依赖（如 T-3.5 依赖 T-3.2 的 schema 落地）必须 PR merge 后才能消解

---

## 7. 任务清单概览（13 槽位 = 12 实施 + 1 验收）

| ID | 类型 | 名称 | 模块边界 | 依赖 | 跳 BC 破例适用 |
|---|---|---|---|---|---|
| **T-3.0** | [A-execute] | 起手清理 PATCH（R3.0/R3.1/R3.2 阶段 2 三遗留并入） | `/generator/scene_ai_judge.py`、`/generator/prompts/scene/`、`/generator/scene_experiment.py` | 无 | ✅ 第 1 类（R3.X follow-up） |
| **T-3.1** | [B-author-gate] | ADR-022 ~ 026 立项（5 条 ADR 一次性 commit） | `/docs/DECISIONS.md` | 无 | ❌ 默认 ABC |
| **T-3.2** | [B-author-gate] | content_dependency_index sidecar schema | `/schema/content_dependency_index.schema.json`、`/schema/tests/`、`/docs/SCHEMA_v0.4.md` 新建（视需要） | T-3.1 | ❌ 默认 ABC |
| **T-3.3** | [A-execute] | 长对话一致性 C 起步（prompt GraphContext 注入 `prior_scene_summaries`） | `/generator/context_assembler.py`、`/generator/prompts/scene/`、`/generator/tests/` | T-3.1 | ❌ 默认 ABC |
| **T-3.4** | [A-execute] | playtest bots 框架（5 persona / 20 paths / worst-10% 输出） | `/generator/playtest/`、`/generator/playtest_cost_log.jsonl`、`/generator/playtest/personas/`、`/generator/tests/` | T-3.1 | ❌ 默认 ABC |
| **T-3.5** | [A-execute] | 批量生成调度器（asyncio + N=3 + token bucket + ontology lock + dep_index writer 集成） | `/generator/batch_scheduler.py`、`/generator/generate_scene.py` 扩展（dep_index sidecar 写入）、`/generator/tests/` | T-3.2 + T-3.3 + T-3.4 | ❌ 默认 ABC |
| **T-3.6** | [A-execute] | 审阅 UI Web 单页（FastAPI + vanilla JS + 5 视图） | `/tools/review_ui/`、`/tools/review_ui/tests/` | T-3.5 + T-3.4 | ❌ 默认 ABC（前端文案微调跳 BC 适用第 4 类） |
| **T-3.7** | [A-execute] | 一致性维护（本体变更反向 propagate） | `/tools/dep_propagate.py`、`/tools/tests/` | T-3.2 | ❌ 默认 ABC |
| **T-3.8** | [A-execute] | 版本控制集成（每次修改记 git commit + scene 内 version metadata） | `/generator/version_recorder.py`、`/schema/`（视需要 scene.json 加 optional `version_metadata` 字段；不动 schema_version const） | 无 | ❌ 默认 ABC |
| **T-3.9** | [A-execute] | Chapter/Act 容器生成扩展（generator 层 + scene_anchor 写入 chapter.acts） | `/generator/chapter_assembler.py`、`/state/ontology/` 扩展（chapter 容器写入）、`/generator/tests/` | T-3.5 | ❌ 默认 ABC |
| **T-3.10** | [A-execute] | 完成标志实测（作者跑一周 ≥10 场景；gross_pass ≥ 80% + [A] ≥ 60%） | 跑批次 + 写实测报告（不动代码） | T-3.5 + T-3.6 + T-3.4 | ✅ 第 5 类近亲（实测报告作者签字） |
| **T-3.11** | [A-execute] | 开源剥离边界清单 v0.2 增量（C5） | `/docs/OPEN_SOURCE_CARVE_OUT_INDEX.md` | 无 | ❌ 默认 ABC |
| **T-3.12** | [B-author-gate] | 阶段 3 验收报告 | `/docs/STAGE_3_ACCEPTANCE.md` 新建 | T-3.10 | ✅ 第 5 类（验收报告） |

**任务总数**：13 条编号槽位 = 12 个 paste-ready prompt + T-3.12 验收报告（与阶段 2 13 槽位规模一致）。

---

## 8. T-3.0 ~ T-3.12 paste-ready 执行会话 prompt

> 每条 prompt 是**自包含的可直接复制到新执行会话首条消息**。作者按 wave 顺序开 Claude Code 执行会话，从下方对应任务直接复制 ` ```text` 代码块全文作为首条消息。
>
> **v0.1 草稿状态**：本节 paste-ready prompts 由 Wave 3 后续 Edit 追加；首版会含完整 13 个任务的 prompt 但本草稿采用**分段落盘策略**（§0 文档说明）—— 骨架先行，prompts 逐次 Edit 追加规避 ECONNRESET 大消息风险。

### T-3.0 ｜ 起手清理 PATCH（R3.0/R3.1/R3.2 阶段 2 三遗留并入）｜ [A-execute]

```text
你的任务是落地阶段 3 起手清理 PATCH，处理阶段 2 收官期遗留的 R2-5 / R2-iter-逃逸 / R2-10c 三项（在 STAGE_3_TASKS §5 已升格为 R3.0 / R3.1 / R3.2）。

# 任务类型：[A-execute]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 纯执行；改 generator 内 prompt + AI 判官 dimensions schema + 预飞 probe；不动 schema / ADR / SCHEMA_v0*.md / L1 文档
- A 阶段：commit + push + 开 PR（base=main，head=本 worktree 分支名）
- routine 串行 OK——本任务不阻塞下游

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——虽然 R3.0/R3.1/R3.2 内容来自阶段 2 R2.X follow-up，但 T-3.0 本身是阶段 3 主线起手任务（不是 R3.X follow-up 编号）。`/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md` §1.5.4 跳 BC 破例 5 类不适用本任务。

# 模块边界（硬性）
允许修改：
  - /generator/scene_ai_judge.py（R3.0：dimensions schema 修）
  - /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md（R3.0：dimensions 段同步）
  - /generator/prompts/scene/system.py 或对应 prompt 文件（R3.1：iter07/iter09/iter11 json 模式逃逸调优）
  - /generator/scene_experiment.py（R3.2：预飞 balance/health probe）
  - /generator/tests/

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py、/generator/llm_provider.py、/generator/budget.py、任何 ADR / L1 文档

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md（本草稿；§5 R3.0/R3.1/R3.2 描述）
- /docs/STAGE_2_ACCEPTANCE.md §4（R2-5 / R2-iter-逃逸 / R2-10c 根因 + 实测 finding）
- /generator/scene_ai_judge.py 当前实现
- /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md 当前 prompt
- 检查 baseline_011 advisory 报告（generator/experiments/20260506T113419Z_baseline_011/）—— iter07/09/11 json 逃逸单点 + dimensions 全空 bug 实测痕迹

# R3.0：scene_ai_judge dimensions dict 全空修复

# 背景
baseline_007~011 全 batch 实测 AI 判官 advisory 报告每场景显示 `(no dimensions returned)`——dimensions dict 全空。root cause 推测是 prompt 模板与 dimensions schema 不一致（prompt 要求模型输出 21 维度 + 6-10 场景级维度，但 dimensions schema / parser 期望的字段名 / 结构不匹配，导致 parse 失败但不报错，dimensions dict 空过）。

# 待落地点
1. 检查 /generator/scene_ai_judge.py 中 dimensions schema 定义（pydantic / typed dict）与 /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md 中 prompt 要求模型输出的字段名 / 结构是否一致——大概率不一致（字段名 / nested 结构 / 缺 strict 校验）
2. 修 dimensions schema OR 修 prompt（取决于哪个更接近"作者期望的 21+10 维度"）；优先以 prompt 为真相之源（作者定义维度，schema 跟随）
3. 加 strict parse + 失败时 logging.warning（不抛异常，与现有 advisory 不阻断 baseline 流的语义一致）
4. 在 /generator/tests/ 加单元测试：模拟一份 21+10 维度 LLM 响应 → parser 正确返回 dimensions dict 含全部 31 字段 + 每字段类型正确
5. 在 baseline_011 任意 1 个 success iter 的 raw judge 响应（如有保留）上做 retro 校验：parser 能正确返回非空 dimensions dict

# R3.1：iter07/iter09/iter11 模型 json 模式逃逸 prompt 调优

# 背景
baseline_010/011 实测 advisory 中部分 iter（07/09/11）出现"模型在 json 模式下输出非 json 内容"现象——schema sanitizer 容忍后过 schema 校验，但 advisory 评分受影响（marginal accept 1 张）。属 prompt 层面 transient 问题，不阻塞 100% gross_pass 但影响 advisory 质量。

# 待落地点
6. 检查 /generator/prompts/scene/ 下 fill prompt（场景填充阶段使用）的 "你必须只输出 json" 类指令措辞——大概率指令偏弱，模型在 reasoning chain 中被诱导输出额外说明文字
7. 加硬指令措辞如："输出必须是 valid json，不得包含任何解释 / 注释 / markdown code fence / 自然语言开场白；输出第一个字符必须是 `{` 或 `[`，最后一个字符必须是 `}` 或 `]`"
8. 不动 fill prompt 的核心生成指令（角色 / 节奏 / 戏剧约束等）—— 仅强化 json-only 输出指令
9. 在 /generator/tests/ 加测试：mock prompt rendering → 检查输出含上述硬指令片段

# R3.2：scene_experiment 预飞 balance/health probe

# 背景
baseline_008 实测踩 PoloAI 余额闸门 short-circuit（403 insufficient_user_quota；整个 batch 0% gross_pass，浪费 ~$0.30）。R2-10c 在 baseline_009 起作者会话已实战手动跑 curl 探测 PoloAI 余额——可工具化避免人手。

# 待落地点
10. 在 /generator/scene_experiment.py 启动 batch run 前加预飞 probe：
    - 用 1 次 minimal LLM call（最小 token 输出，如 "ok" 1 token 任务）验证 PoloAI / Gemini 账户可用 + 余额非 0
    - 失败时 abort 整个 batch + 清晰错误消息（"PoloAI account balance insufficient or upstream unavailable"）+ exit code != 0
    - 成功时 logging.info（不污染 stdout 主流程输出）
11. 加 env / CLI flag `--skip-probe` 让作者跳过（如已知账户健康想直接跑）
12. 在 /generator/tests/ 加单元测试：mock provider call → probe 检查行为 / abort 路径正确

# 不要做的事
- 不要扩展 /schema/（CLAUDE.md 规则 2）
- 不要改 GeminiProvider / PoloAIProvider 内部
- 不要碰 budget.py（成本核算与本任务无关）
- 不要在此任务里实现 R3.X 之外的 follow-up（playtest_NNN finding 在阶段 3 中段才会产生）
- 不要在此任务里跑 baseline batch（实测在 T-3.10）
- 不要重写 generate_scene 主流程
- **特别**：不要把"AI 判官完全改用 reasoning trace 而非 dimensions JSON"——那是阶段 4 审美层评估范畴；本任务仅修 dimensions parse bug 不重设计判官范式

# 测试
- pytest /generator/tests/ 全过
- 必含 R3.0 / R3.1 / R3.2 各自单元测试
- 跑 /review skill + validate-all（本地 schema 校验 + lint）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- diff 摘要（按 R3.0 / R3.1 / R3.2 三段分别说明）
- 跑了哪些测试（pytest 输出 / validate-all 输出）
- commit message: `fix(generator): R3.0 R3.1 R3.2 cleanup gate for Stage 3 (T-3.0)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-3.0_<topic>_review.md`
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

### T-3.1 ｜ ADR-022 ~ ADR-026 立项（5 条 ADR 一次性 commit）｜ [B-author-gate]

```text
你的任务是把阶段 3 的 5 条架构决策一次性写入 /docs/DECISIONS.md。
作者已通过 2026-05-07 L2 规划师会话明确授权（CLAUDE.md 规则 10 例外）——属"批量立 ADR"先例延续，参考 commit `1d2030f`（ADR-011/012/013 一次性 3 条）+ commit `df05431`（ADR-016 ~ ADR-021 一次性 6 条）。

# 任务类型：[B-author-gate]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 修改 L1 架构文档；CLAUDE.md 规则 10 例外（作者已在 2026-05-07 L1-L2 校准会话明确授权立 ADR-022~026）
- A 阶段：commit + push + 开 PR（base=main，head=本 worktree 分支名）
- B/C 阶段：作者会更仔细审 PR diff（毕竟动 ADR）；过 ABC + L2 验收后 merge
- routine：A 阶段完成 push + 开 PR 后 routine 可继续；但 PR 在 B/C/L2 验收闭环前不 merge，下游依赖任务（T-3.2 / T-3.3 / T-3.4 等）的 A 阶段需等本 PR merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——立 ADR 是 [B-author-gate] 高敏感任务，不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
只允许修改：/docs/DECISIONS.md
严禁修改：CLAUDE.md / SCHEMA_v0*.md / DEBATE_NOTES.md / ROADMAP.md / 任何 /schema/ 文件 / 任何 /state/ 文件 / 任何代码

# 必读（按顺序）
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md 全部 21 条 ADR（理解格式 + 编号约定 + ADR-016~021 阶段 2 立项先例）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3（推荐立项的 ADR 清单 — 本任务来源；含 ADR-022 ~ 026 决策核心）+ §2（锁定的架构决策）
- /docs/HANDOFF_STAGE_2_TO_3.md
- /docs/STAGE_2_ACCEPTANCE.md §5
- /docs/reviews/master_plan/2026-04-30_synthesis.md §7 阶段 3 启动前置
- /docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md §5 + §7（U-CL-5 + 作者态度）

# 5 条 ADR 落地清单

引用 STAGE_3_TASKS_draft_v0.1.md §3 各 ADR 决策核心段落，按 /docs/DECISIONS.md 现有格式（背景 / 决策 / 替代方案及否决理由 / 后果 / 状态）落地。每条 ADR 字数控制在 ≤ 100 行（与 ADR-016~021 体量对齐）。

## ADR-022：playtest bots 完成标志阈值
- **状态**：已接受（2026-05-XX，按 commit 实际日期填）
- **背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 C2——ADR-009 第三层 playtest bots 必须在阶段 3 完成标志里；否则阶段 4 才发现 50–100 场景里有 worst-bucket 路径
- **决策**：见 STAGE_3_TASKS_draft_v0.1.md §3 ADR-022 决策核心（N=5 persona / M=20 paths/persona = 100 paths/scene / worst-10% 输出 / 至少 5 场景跑过完整 playtest）
- **替代方案及否决理由**：完全 fixture / 完全 LLM 生成 / N=10×M=50 大体量
- **后果**：T-3.4 落地 /generator/playtest/ 框架；playtest cost log 独立；阶段 3 末期实测如不足以暴露 worst-bucket 由 ADR-022 v0.2 修订倒推

## ADR-023：content_dependency_index sidecar 形态 + 字段集
- **状态**：已接受（2026-05-XX）
- **背景**：synthesis §7 + ROADMAP §阶段 3 完成标志强化项 C6——一致性维护需要内容依赖索引；本体变更如何反向 propagate 到生成产物当前没有设计
- **决策**：见 §3 ADR-023 决策核心（per-scene sidecar `<scene>.deps.json` / 新建 `/schema/content_dependency_index.schema.json` const "0.3.0" / 字段集含 ontology_ids_read / state_paths_read / state_paths_written / prompt_template_hash / visual_asset_ids_referenced / clock_ids_referenced / chapter_id / act_id / scene_history_referenced）
- **替代方案及否决理由**：全局索引 / SQLite / sidecar 三选一对照
- **后果**：T-3.2 schema 落地；T-3.5 generate_scene hook 写 sidecar；T-3.7 一致性维护工具按 sidecar 反向 propagate；scene_history_referenced 字段是 ADR-024 长对话一致性 hook

## ADR-024：长对话一致性 C 起步 + A/B hook
- **状态**：已接受（2026-05-XX）
- **背景**：DEBATE §9.2 长对话一致性列为未解问题；ROADMAP §阶段 3 强化项 U-CL-5 要求 ADR / 任务落地；PZ §7 作者态度（不预防性设计 + 50-100 场景可能不撞真墙）影响投入度
- **决策**：见 §3 ADR-024 决策核心（C 起步全套：prompt GraphContext 注入 prior_scene_summaries 字段 / 摘要来源人工或半自动 LLM + 作者校准 / 上限 ≤ 5 条；A/B hook 留：content_dependency_index.scene_history_referenced 字段；不在阶段 3 落地 A=Generative Agents memory stream / B=RAG over event log）
- **替代方案及否决理由**：完整 D hybrid (A+C) / 不立 ADR（U-CL-5 显式要求）
- **后果**：prompt 模板（T-3.3）必须支持 prior_scene_summaries context 注入；阶段 3 实测一周 10 场景后 token 累积曲线 + 接受率回归是否撞墙作 ADR-024 v0.2 修订依据

## ADR-025：审阅 UI 架构
- **状态**：已接受（2026-05-XX）
- **背景**：synthesis §7 + ROADMAP §阶段 3 强化项 U-GPT-7——审阅 UI 第一版含图视图（graph/mermaid/dot + 路径列表 + validator issues + visual asset thumbnail）；避免后期重做审阅心智模型
- **决策**：见 §3 ADR-025 决策核心（Web 单页 / FastAPI + vanilla HTML/JS / mermaid.js CDN / 5 视图：graph + 路径列表 + validator issues + visual asset thumbnail + [A]/[R]/[S] 标注 / read-only 不做编辑功能 / 仅生产期 / env FORGEWRIGHT_REVIEW_UI_PORT 默认 8765）
- **替代方案及否决理由**：CLI 升级（投入低但 graph 体验差）/ 桌面应用（投入最高） / React/Vue/Svelte 框架（开源门槛上升）
- **后果**：T-3.6 落地 /tools/review_ui/；复用 T-2.8 graph_views 三件套作为 graph 视图数据源；不阻塞 T-3.10 实测——T-3.10 可同时用 scene_review_cli（CLI）和 review_ui（Web）

## ADR-026：批量调度器并发模型
- **状态**：已接受（2026-05-XX）
- **背景**：ROADMAP §阶段 3 完成标志要求批量生成调度器（异步跑多场景）；阶段 2 baseline_011 单 iter mean 268s 实测——串行 N=1 时 10 场景 1-2.5 小时作者必须守着，ergonomic 差
- **决策**：见 §3 ADR-026 决策核心（asyncio + N=3 concurrent / 每 provider token bucket 速率限制 默认 60 RPM / ontology 写入 file lock fcntl / 单场景失败不阻塞其他并发场景 / env FORGEWRIGHT_BATCH_CONCURRENT_N 默认 3 / FORGEWRIGHT_PROVIDER_RPM 默认 60）
- **替代方案及否决理由**：串行 N=1 / N=10 撞 PoloAI 速率限制 / subprocess fan-out 复杂度高
- **后果**：T-3.5 落地 /generator/batch_scheduler.py；阶段 3 实测如撞 PoloAI 余额闸门作者降 N=1/2 应急；阶段 3 末期 ADR-026 v0.2 修订倒推真实最优 N

# 立项规则（共通）
- 状态行 = "已接受（2026-05-XX）" — 实际日期填写为本任务 commit 当日
- 后果行明示哪些下游 L3 任务依赖本 ADR（T-3.2 / T-3.3 / T-3.4 / T-3.5 / T-3.6 / T-3.7）
- 末尾在 /docs/DECISIONS.md "变更历史" 段追加：
  ```
  - 2026-05-XX：作者明确授权新增 ADR-022 / 023 / 024 / 025 / 026（阶段 3 五条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_3_TASKS_v1.0_draft（含 GPT-5.5 critique 校准）。L2 整合规划师会话（claude/sweet-bardeen-863720）2026-05-07 L1-L2 校准产物。
  ```
- 注意"L2 整合规划师会话产物"句子在 v0.1 → v1.0 经 critique 后 commit，应写 v1.0 产出会话名，但 worktree 名同源（claude/sweet-bardeen-863720）—— 由作者起 T-3.1 时确认实际 worktree 名

# 不要做的事
- 不要修改 SCHEMA_v0*.md（那是 T-3.2 范围）
- 不要修改任何 /schema/ 文件
- 不要修改任何代码
- 不要碰 ROADMAP.md 阶段 3 完成标志措辞——X1 / X2 跨边界（作者另起 L1 修订会话）
- 不要在 ADR 内写"如何实现"的代码细节（ADR 是 what + why + 后果，不是 how）
- 不要超过 5 条 ADR 范围（Chapter/Act 不立新 ADR——T-2.2 schema 已落地，ADR-016 后果段已涵盖；C5 OPEN_SOURCE_CARVE_OUT_INDEX 不立新 ADR——T-2.10 v0.1 已落地）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- /docs/DECISIONS.md 的 diff 摘要（按 ADR 分段）
- 5 条 ADR 各自字数（建议每条 ≤ 100 行）
- commit message：`docs: add ADR-022/023/024/025/026 for Stage 3 (T-3.1)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-3.1_<topic>_review.md`
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

### T-3.2 ｜ content_dependency_index sidecar schema ｜ [B-author-gate]

```text
你的任务是为 content_dependency_index sidecar 落地正式 JSON Schema，并新增对应文档章节。这是 ADR-023 落地的硬依赖任务——T-3.5 批量调度器会按本 schema 写 sidecar，T-3.7 一致性维护按 schema 反向 propagate。

# 任务类型：[B-author-gate]
- 动 schema = 高敏感任务；CLAUDE.md 规则 2 + 9 例外（作者已通过 2026-05-07 L2 规划师会话明示授权阶段 3 schema 扩展两处之一：content_dependency_index sidecar）
- A 阶段：commit + push + 开 PR；B/C 阶段作者会更仔细审 PR diff
- 必须严格依赖 T-3.1 的 ADR-023 已 merge 后才能启动 A 阶段（schema commit 串行卡口；ADR-015 / ADR-016 §schema 版本号策略）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——schema 修改 [B-author-gate] 高敏感，不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /schema/content_dependency_index.schema.json（**新建**；首版 const `schema_version: "0.3.0"`，与 character/location/clock/chapter schema 同源演进语义——新建 schema 文件首版即 0.3.0；详 ADR-016 §schema 版本号策略）
  - /schema/tests/（新建 test_content_dependency_index.py 或加入现有测试套件）
  - /docs/SCHEMA_v0.3.md（追加新章节，与 character/location/clock/chapter 同文档；不新建 SCHEMA_v0.4.md，避免文档膨胀）— 视章节结构需要，如不合适可新建 /docs/SCHEMA_v0.4.md（仅在 SCHEMA_v0.3.md 实在塞不下时；A 阶段会话拍板）

严禁修改：
  - 任何既有 /schema/*.schema.json（dialogue_graph / node / option / state_effect / state_condition / character / location / clock / chapter / image_asset）—— ADR-023 不动既有 schema
  - /docs/DECISIONS.md（除 ADR-023 已由 T-3.1 立项；本任务不动 ADR）
  - CLAUDE.md / DEBATE_NOTES.md / ROADMAP.md
  - /state/ontology/（不动现有 ontology 数据；sidecar 是阶段 3 新增机制）
  - /generator/ /validator/ /engine/（任何代码）

# 必读
- /CLAUDE.md（规则 1-10，特别 2/9）
- /docs/DECISIONS.md ADR-023（T-3.1 已立项，本任务依赖）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-023 决策核心 + §2.1 D2 + §2.4 跨任务一致性细节
- /docs/SCHEMA_v0.3.md（阶段 2 ontology 模块文档；理解格式 + 语义）
- /schema/character.schema.json + /schema/location.schema.json + /schema/clock.schema.json + /schema/chapter.schema.json（参考阶段 2 新建 schema 文件结构格式 + const `0.3.0` 落地方式）
- /schema/tests/ 阶段 2 测试套件（参考 fixture 写法）
- /docs/reviews/master_plan/2026-04-30_synthesis.md §7（C6 内容依赖索引概念来源）

# Schema 字段集（依据 ADR-023）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://forgewright.dev/schema/content_dependency_index.schema.json",
  "title": "ContentDependencyIndex",
  "description": "Sidecar metadata recording content generation dependencies. Per-scene file <scene>.deps.json colocated with scene.json.",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "0.3.0"
    },
    "scene_id": {
      "type": "string",
      "pattern": "^[a-z0-9_]+$"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time"
    },
    "ontology_ids_read": {
      "type": "array",
      "items": { "type": "string" },
      "description": "All ontology entity ids referenced during generation (char_*, scene_*, loc_*, clk_*, chap_*)"
    },
    "state_paths_read": {
      "type": "array",
      "items": { "type": "string" },
      "description": "State paths read in conditions / context"
    },
    "state_paths_written": {
      "type": "array",
      "items": { "type": "string" },
      "description": "State paths in option.effects + node.on_enter_effects"
    },
    "prompt_template_hash": {
      "type": "string",
      "pattern": "^sha256:[a-f0-9]{64}$",
      "description": "SHA256 of concatenated prompt files (skeleton + fill + system) at generation time"
    },
    "visual_asset_ids_referenced": {
      "type": "array",
      "items": { "type": "string" }
    },
    "clock_ids_referenced": {
      "type": "array",
      "items": { "type": "string" }
    },
    "chapter_id": {
      "type": ["string", "null"],
      "description": "Chapter container; null if scene not yet assigned to chapter"
    },
    "act_id": {
      "type": ["string", "null"]
    },
    "scene_history_referenced": {
      "type": "array",
      "items": { "type": "string" },
      "description": "ADR-024 long-conversation hook: prior scene ids whose summaries were injected into prompt context"
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
1. 新建 /schema/content_dependency_index.schema.json — 按上述字段集；`additionalProperties: false`；required 段含必填核心字段；optional 字段 `chapter_id` / `act_id` / `visual_asset_ids_referenced` / `clock_ids_referenced` / `scene_history_referenced` 允许 missing 或 null（场景未分配 chapter / 没有视觉资产引用 / 不在长对话窗口等情况合法）
2. 新建 schema 测试 — 至少 4 case：
   - 有效 sidecar（全字段填）→ pass
   - 有效 sidecar（仅 required 字段，optional 全省）→ pass
   - schema_version 错（如 "0.4.0"）→ fail
   - prompt_template_hash 格式错（如缺 "sha256:" 前缀）→ fail
3. 在 /docs/SCHEMA_v0.3.md 追加新章节（**§N. content_dependency_index sidecar schema**）— 含字段语义、与 ontology / dialogue_graph schema 的关系、写入时机说明、ADR-023 引用；与既有 chapter / clock 章节同 prose 风格
4. 不动既有 schema 文件——验证 /content/test_scene_v0/ 现有 gold scene 仍 pass 全部既有 schema（schema_version 0.1.1 / 0.3.0 各自维持）

# 不要做的事
- 不要 bump 既有 schema 文件 const（ADR-016 / ADR-019 §schema 版本号策略：既有文件不动）
- 不要在 /content/ 下立刻为 gold scene 写 sidecar（sidecar 写入是 T-3.5 调度器 hook 范围；本任务仅交付 schema + 文档）
- 不要把 sidecar 字段做成 dialogue_graph schema 的 nested 字段（破独立性 + 增加 dialogue_graph 体量）
- 不要做 schema 校验工具 / migrate 脚本（T-3.5 / T-3.7 范围）
- 不要碰 /generator/ /validator/ /engine/（schema-only 任务）

# 测试
- pytest /schema/tests/ 全过（含本任务新增测试）
- 跑 /review skill + validate-all（schema 自校验 + lint）
- 验证 /content/test_scene_v0/scene.json 仍 pass dialogue_graph 0.1.1 schema（防 sidecar 引入意外影响）

# A 阶段完成标志
- /schema/content_dependency_index.schema.json 内容
- /schema/tests/ 新增测试 + pytest 输出
- /docs/SCHEMA_v0.3.md 新增章节 diff
- commit message: `feat(schema): add content_dependency_index sidecar schema (T-3.2; ADR-023)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；A 阶段产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex GPT-5.5 review；report 落 /docs/reviews/<ISO_DATE>_T-3.2_sidecar_schema_review.md
- C 阶段：吃 B 报告 + 追加 commit
- L2 验收过关后 merge；下游 T-3.5 / T-3.7 启动依赖本 PR merge
```

### T-3.3 ｜ 长对话一致性 C 起步（prompt GraphContext 注入 prior_scene_summaries）｜ [A-execute]

```text
你的任务是落地 ADR-024 长对话一致性 C 起步——在 generator prompt 模板的 GraphContext 中注入 `prior_scene_summaries` 字段，并支持作者人工填 + 半自动 LLM 摘要 + 作者校准两条路并存。这是阶段 3 内容产线"记忆缓解"的核心 hook。

# 任务类型：[A-execute]
- 纯执行；改 prompt + context_assembler；不动 schema / ADR / L1 文档
- 必须依赖 T-3.1 ADR-024 已 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 prompt 模板 + context 字段扩展不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/context_assembler.py（GraphContext dataclass 新增 prior_scene_summaries 字段）
  - /generator/prompts/scene/（prompt 模板支持 prior_scene_summaries context 注入）
  - /generator/scene_summary_writer.py（**新建**；半自动 LLM 摘要工具，作者可一键摘要 + 校准）
  - /generator/tests/

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py（仅可在 GraphContext 实例化时填入 prior_scene_summaries 字段；不动主流程算法）、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-024（T-3.1 已立项；本任务依赖）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-024 决策核心 + §2.4 字段命名
- /docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md §5 + §7（U-CL-5 + 作者态度）
- /docs/DEBATE_NOTES.md §9.2（长对话一致性未解问题描述）
- /generator/context_assembler.py 当前实现（理解 GraphContext 现有字段）
- /generator/prompts/scene/system.py + fill prompt（理解 prompt 注入方式）

# 待落地点

## C-1：GraphContext 加 prior_scene_summaries 字段

1. /generator/context_assembler.py 的 GraphContext dataclass 增加：
   ```python
   prior_scene_summaries: list[PriorSceneSummary] = field(default_factory=list)
   ```
   其中 PriorSceneSummary 是新 dataclass：
   ```python
   @dataclass
   class PriorSceneSummary:
       scene_id: str
       summary: str  # ≤ 200 中文字符；或 ≤ 800 英文字符
       key_state_paths: list[str]  # 该场景产生的关键 state_path 写入
   ```
2. 上限：每场景 prompt 注入最多 5 条 prior_scene_summaries（避免 prompt 膨胀；与 ADR-024 字段定义一致）；超过时按"最近 5 条 + 关键场景"启发式裁剪（保留 chapter_id / act_id 边界场景）

## C-2：prompt 模板支持 prior_scene_summaries context 注入

3. /generator/prompts/scene/system.py 加 prior_scene_summaries context section（仅在 list 非空时注入）：
   ```
   # 前置场景概要（按时间顺序）
   - [scene_id_X] {summary}; 关键状态写入：{key_state_paths}
   - ...
   ```
4. fill prompt 不动主算法；仅 context section 增量
5. 测试：模拟 GraphContext 含 3 条 prior_scene_summaries → 渲染后的 prompt 含上述 context section 文本片段

## C-3：半自动 LLM 摘要工具

6. /generator/scene_summary_writer.py（新建）— 接受 scene.json 路径 → 调 LLM 生成 ≤ 200 字摘要 + 提取 key_state_paths（从 scene 的 effect 集合）→ 输出 PriorSceneSummary dataclass
7. CLI 入口（参 T-2.8 scene_review_cli 风格）：`python -m generator.scene_summary_writer <scene_path>` 输出建议摘要 + 等作者编辑（或 --auto-accept 直接落 sidecar）
8. 摘要存储位置：与 content_dependency_index sidecar **不同**——摘要属生成期 metadata，建议落 `<scene>.summary.json`（与 deps.json 平级；schema 不立，pydantic dataclass JSON 序列化即可）。或者并入 deps.json 的 "summary" 字段—— 由 A 阶段会话权衡（理由 commit message 写明）；**但不动 ADR-023 schema**——如选并入需 T-3.2 schema 在本任务前新增 optional summary 字段，触发 schema 修订属跨任务依赖，不推荐。**A 阶段倾向：独立 sidecar `<scene>.summary.json`**

## C-4：作者人工填路径

9. CLI 接受 `--manual` flag 让作者直接编辑 `<scene>.summary.json`（用 $EDITOR 打开模板）；半自动模式（默认）= LLM 起草 + 作者校准
10. 测试：mock LLM 调用 → 验证 summary_writer 路径 + dataclass 序列化正确

# 不要做的事
- 不要扩展 /schema/（CLAUDE.md 规则 2；prior_scene_summaries 是运行时 context，不入持久 schema）
- 不要实现 RAG / embedding / Generative Agents memory stream（ADR-024 明示 A/B 不在阶段 3 落地）
- 不要在 generate_scene 主流程内自动调 summary_writer（保留作者明示触发；避免每次生成都 burn token 成本不可控）
- 不要碰 ontology 数据（与本任务正交）
- 不要在 prompt 里硬编码 prior_scene_summaries 处理逻辑（应作为 GraphContext 字段，prompt 模板按字段渲染）

# 测试
- pytest /generator/tests/ 全过
- 必含：GraphContext.prior_scene_summaries 字段单元测试 / prompt 渲染 + context section 测试 / scene_summary_writer mock LLM 路径测试
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 C-1 / C-2 / C-3 / C-4 四段说明）
- pytest 输出
- commit message: `feat(generator): long-conversation consistency C-tier (T-3.3; ADR-024)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.3_long_conversation_consistency_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.5 批量调度器在 GraphContext 实例化时填 prior_scene_summaries 依赖本 PR merge
```

### T-3.4 ｜ playtest bots 框架（5 persona / 20 paths / worst-10% 输出）｜ [A-execute]

```text
你的任务是落地 ADR-022 playtest bots 框架——为每个生成场景跑 5 个 persona × 20 paths = 100 paths，输出 worst-10% 路径清单 + LLM-as-judge 综合分数。这是 ROADMAP §阶段 3 完成标志强化项 C2 的核心交付物。

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
    - /generator/playtest/personas/（**新建子目录**；5 个 persona JSON 文件）
      - cautious.json / aggressive.json / completionist.json / speedrunner.json / role_player.json
    - /generator/playtest/runner.py（playtest 跑批主流程）
    - /generator/playtest/judge.py（LLM-as-judge worst-10% 排序）
    - /generator/playtest/cli.py（CLI 入口）
  - /generator/playtest_cost_log.jsonl（**新建**；与 cost_log.jsonl 分离；D9 + §2.4）
  - /generator/tests/test_playtest_*.py（新增）

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-022（T-3.1 已立项；本任务依赖）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-022 决策核心 + §2.4 字段命名 + §2.1 D1
- /docs/DECISIONS.md ADR-009（评测三层；playtest bots 是第三层）+ ADR-021（§2B 抽样路径起点 sampling 框架；可复用）
- /validator/sampling.py（理解阶段 2 §2B 抽样路径生成器，复用其"从 entry 出发随机选 option"基础逻辑）
- /generator/scene_ai_judge.py（理解 LLM-as-judge 调用 + dimensions schema 形态）

# 待落地点

## P-1：5 个 persona 库（hand-write base + LLM augment hook）

1. 5 个 persona JSON 文件（/generator/playtest/personas/）。每个文件结构：
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
   5 个 persona：cautious / aggressive / completionist / speedrunner / role_player——hand-write base_traits + selection_bias，augmented_description = null（保留 LLM augment hook，不在本任务实现 augment 逻辑）

## P-2：playtest runner（path 模拟）

2. /generator/playtest/runner.py：核心函数 `run_playtest(scene: DialogueGraph, persona: Persona, n_paths: int) -> list[PlaytestPath]`
   - 每 path = 从 entry_node_id 出发，模拟 persona 在每个 dialogue 节点的 option 选择直到 end 节点
   - option 选择：调 LLM 让 persona 扮演 + 选 option_id（受 base_traits + selection_bias 影响）
   - 记录每 path：node_ids 序列 + option_ids 序列 + state 演化（复用 /validator/sampling.py state evaluator）
3. **复用 /validator/sampling.py 路径生成器**——不重写"从 entry 出发选 option"基础逻辑，仅替换 option 选择策略（从 random.choice → LLM persona 决策）
4. async 实现（与 ADR-026 调度器并发模型一致）；每 path 独立一个 LLM 调用

## P-3：LLM-as-judge worst-10% 排序

5. /generator/playtest/judge.py：每 path 跑完后调 LLM-as-judge 评估（剧情连贯 / persona 体验 / 节奏 / 最终结局合理性 4 维度）；输出 path_score（0-100）
6. 5×20=100 paths 跑完后按 path_score 排序最低 10%（即 worst 10 paths）→ 输出 `<batch_dir>/playtest_NNN/worst_paths.jsonl`
7. 每条 worst path 记录：path trace + judge_score + critical_issue（LLM 判官给出的关键问题描述）

## P-4：CLI 入口

8. /generator/playtest/cli.py：命令 `python -m generator.playtest <scene_path> [--n-paths 20] [--personas all|cautious,aggressive,...]`
9. CLI 行为：
   - load scene + load personas → 跑 N persona × M paths → 输出 worst paths + 报告
   - 输出目录：`/generator/experiments/playtest_NNN/`（与 baseline 同源命名空间但 NNN 编号独立）
   - cost_log 写入 /generator/playtest_cost_log.jsonl（独立于 cost_log.jsonl）

## P-5：成本控制

10. budget 接入：复用 /generator/budget.py（每个 LLM 调用走 budget.check_and_charge）
11. 单 playtest batch 估算：100 paths/scene × ~$0.02/path（短 LLM 调用）= ~$2/scene；阶段 3 实测 5 场景 = ~$10
12. 加 `--max-cost-usd <amount>` flag 让作者预防失控

## P-6：仪表化

13. 沿用阶段 2 R2.9 ProviderError 仪表化（path 失败时记录 ProviderError 元数据 + path_id + persona_id）

# 不要做的事
- 不要在 generate_scene 主流程内自动跑 playtest（playtest 是后处理步骤，作者明示触发）
- 不要硬编码 persona 描述在 Python 代码（必须 JSON 配置 + 易扩展）
- 不要在本任务实现 LLM augmented_description 生成逻辑（hook 留 null 即可；阶段 3 末期视需要落地）
- 不要扩展 /schema/（playtest 是评测产物，不入持久 schema）
- 不要 fail-fast 整个 batch（单 path 失败 → log + 继续；与 ADR-026 失败传播一致）
- 不要碰 ontology 写入（playtest 是 read-only，不影响本体）

# 测试
- pytest /generator/tests/test_playtest_*.py 全过
- 必含：persona 加载测试 / runner mock LLM 路径测试（不真烧 API）/ judge mock LLM 测试 / CLI 集成测试（gold scene 跑 1 path）
- 跑 /review skill + validate-all
- **小成本实证**（可选；作者可在 A 阶段会话里跑 1 个 playtest 1 persona × 5 paths = $0.10 实证）—— 需作者明示授权 + 记 cost_log

# A 阶段完成标志
- diff 摘要（按 P-1 ~ P-6 六段说明）
- 5 个 persona JSON 文件清单
- pytest 输出
- commit message: `feat(generator): playtest bots framework (T-3.4; ADR-022)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.4_playtest_bots_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6 审阅 UI 含 playtest 视图依赖本 PR；T-3.10 实测期跑完整 playtest 依赖本 PR
```

### T-3.5 ｜ 批量生成调度器（asyncio + N=3 + token bucket + ontology lock + dep_index writer 集成）｜ [A-execute]

```text
你的任务是落地 ADR-026 批量生成调度器——asyncio + N=3 concurrent worker + 每 provider token bucket 速率限制 + ontology 写入 file lock + content_dependency_index sidecar 写入 hook。这是阶段 3 内容产线的核心引擎；ROADMAP §阶段 3 完成标志"批量生成调度器（异步跑多场景）"的硬交付。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/batch_scheduler.py + 扩展 /generator/generate_scene.py（仅 dep_index sidecar 写入 hook，不动主算法）
- 必须依赖 T-3.2（schema） + T-3.3（GraphContext.prior_scene_summaries） + T-3.4（playtest 不阻塞但建议同期就绪）三 PR merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增 + generate_scene 扩展，是阶段 3 核心交付，必须严格 review。

# 模块边界（硬性）
允许修改：
  - /generator/batch_scheduler.py（**新建**）
  - /generator/dep_index_writer.py（**新建**；sidecar 写入 helper）
  - /generator/generate_scene.py（仅在主流程末尾追加 dep_index sidecar 写入 hook 调用；不动 skeleton-first / fill / retry / 机械预检整合主算法）
  - /generator/tests/

严禁修改：/schema/、/state/、/state/ontology/（loader 不动，但调度器内 ontology 写入用 file lock；不动 ontology 数据本身）、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/llm_provider.py、/generator/budget.py、/generator/context_assembler.py（GraphContext 已由 T-3.3 扩展）、/generator/scene_strategies.py、/generator/prompts/scene/

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-026（T-3.1 已立项；本任务依赖）+ ADR-023（T-3.1 已立项；sidecar 写入依赖）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-026 + ADR-023 决策核心 + §2.4 字段命名（FORGEWRIGHT_BATCH_CONCURRENT_N / FORGEWRIGHT_PROVIDER_RPM）
- /generator/scene_experiment.py（理解阶段 2 单 batch run 模式，本任务是其 N=3 异步并发版本）
- /generator/generate_scene.py（理解主流程；本任务仅 hook，不动算法）
- /schema/content_dependency_index.schema.json（T-3.2 已落地）
- /docs/STAGE_2_ACCEPTANCE.md §2.1（baseline_011 单 iter mean 268s 实测数据；ADR-026 N=3 决策依据）

# 待落地点

## BS-1：asyncio worker pool

1. /generator/batch_scheduler.py：核心函数 `async def run_batch(scenes: list[SceneSpec], concurrent_n: int = 3) -> BatchResult`
   - SceneSpec dataclass：scene_setting / target_beats / participating_npcs（与现有 generate_scene 主参数对齐）
   - 启动 N 个 asyncio worker 共享一个 asyncio.Queue（pull 模式）
   - 每个 worker：pull SceneSpec → call `await asyncio.to_thread(generate_scene, ...)` 或 native async `await generate_scene_async(...)`（视 generate_scene 当前 API；如非 async，用 to_thread 包装）
2. concurrent_n 来源：env `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 3）；CLI flag `--concurrent-n N` 覆盖

## BS-2：token bucket 速率限制

3. 每 provider 一个 token bucket（aiolimiter 库 OR 手写 asyncio.Semaphore + 时间窗口）
4. 默认 60 RPM（env `FORGEWRIGHT_PROVIDER_RPM`，CLI `--rpm N` 覆盖）
5. token bucket 注入位置：在 LLMProvider 调用前 await acquire；不动 LLMProvider Protocol（保持其简洁性，速率限制在调度层加）—— 通过装饰器 / context manager 形态注入
6. 多 provider 实测可能不同上限（PoloAI vs Gemini）：v0.1 起步全 provider 共享同一 bucket（保守）；阶段 3 末期视实测 v0.2 修订

## BS-3：ontology 写入 file lock

7. /state/ontology/<world>.json 写入用 fcntl.flock 加文件锁
8. 写入路径：调度器在 generate_scene 完成后如有 ontology 增量（如新加场景 anchor），获取 lock → read-modify-write → release lock
9. scene 文件各自独立 path 不冲突——不需要 lock；多个 worker 写不同 scene 文件无冲突

## BS-4：dep_index sidecar 写入 hook

10. /generator/dep_index_writer.py（新建）：核心函数 `def write_sidecar(scene_path: Path, scene: DialogueGraph, generation_trace: dict, prior_scene_summaries: list, prompt_files: list[Path]) -> Path`
    - 收集 ontology_ids_read / state_paths_read / state_paths_written / visual_asset_ids_referenced / clock_ids_referenced（从 scene + ontology 反查）
    - 计算 prompt_template_hash = sha256(concat 所有 prompt_files 内容)
    - chapter_id / act_id：从 ontology chapters[] 找含该 scene_anchor 的 chapter（如未分配则 null）
    - scene_history_referenced：从 prior_scene_summaries 提取 scene_id list
    - 输出 `<scene>.deps.json`（与 scene.json 同目录）；用 jsonschema 库验 ContentDependencyIndex schema
11. /generator/generate_scene.py 主流程末尾追加调用 write_sidecar（在 scene.json 写入后立即写 sidecar；事务性：sidecar 写失败 → log warning + 继续，不回滚 scene.json）

## BS-5：失败传播 + 仪表化

12. 单 worker scene 失败：log + 写 ProviderError 仪表化（沿用 R2.9）+ 不阻塞其他 worker
13. BatchResult 含每 scene 的 status / failure_metadata / scene_path / cost_usd / elapsed
14. 总报告：完成后输出 `<batch_dir>/batch_summary.md` 含 success rate / total cost / mean elapsed / failure distribution

## BS-6：CLI 入口

15. CLI：`python -m generator.batch_scheduler <scenes_spec.json> [--concurrent-n 3] [--rpm 60] [--dry-run]`
16. dry-run 模式：仅打印调度计划 + 估算成本，不调 LLM

# 不要做的事
- 不要改 LLMProvider Protocol（速率限制在调度层加，不污染 Provider 接口）
- 不要在 batch_scheduler 内重写 generate_scene 主算法（仅做 worker pool + 速率 + lock + sidecar 写入；主流程算法不动）
- 不要扩展 /schema/（dep_index schema 由 T-3.2 已落地；批量调度产物 batch_summary.md 不入 schema）
- 不要碰 ontology 数据本身（仅加 file lock 写入路径；现有 ontology 读路径不动）
- 不要把 prior_scene_summaries 来源 hard-code（sceneSpec 内可选传入；调度器不主动调 scene_summary_writer）
- 不要把 GraphContext.prior_scene_summaries 作为必填——空数组合法（早期场景没有前置）

# 测试
- pytest /generator/tests/test_batch_scheduler.py 全过
- 必含：mock generate_scene + run_batch with 3 SceneSpec → 验证 N=3 并发执行 / token bucket 限速正确 / ontology lock 写入串行（mock fcntl）/ dep_index sidecar 写入正确（schema 校验过）/ 单 worker 失败不阻塞其他 worker
- 跑 /review skill + validate-all
- **可选小成本实证**：用 1 个 scene + concurrent_n=1 跑通端到端（需作者明示授权 + 走 budget 拦截）

# A 阶段完成标志
- diff 摘要（按 BS-1 ~ BS-6 六段说明）
- pytest 输出
- commit message: `feat(generator): batch scheduler with asyncio + dep_index writer (T-3.5; ADR-026 + ADR-023)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.5_batch_scheduler_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6 review_ui / T-3.9 chapter 容器生成 / T-3.10 实测期都依赖本 PR
```

### T-3.6 ｜ 审阅 UI Web 单页（FastAPI + vanilla JS + 5 视图）｜ [A-execute]

```text
你的任务是落地 ADR-025 审阅 UI Web 单页——FastAPI 静态 server + 前端 vanilla HTML/JS + mermaid.js CDN，5 视图齐全（graph / 路径列表 / validator issues / visual asset thumbnail / 审美层 [A]/[R]/[S]）。这是 ROADMAP §阶段 3 完成标志强化项 U-GPT-7 的核心交付。

# 任务类型：[A-execute]
- 纯执行；新建 /tools/review_ui/；不动 schema / ADR / L1 文档
- 依赖 T-3.5 批量调度器 + T-3.4 playtest bots PR merge（review_ui 展示其产物）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**。但 review_ui ergonomic 微调（仅前端文案 / 视图样式 / 不动后端 API 与 schema）属 §1.5.4 跳 BC 破例第 4 类——后续 R3.X follow-up PR 可走跳 BC 模式。

# 模块边界（硬性）
允许修改：
  - /tools/review_ui/（**新建模块目录**）
    - /tools/review_ui/__init__.py
    - /tools/review_ui/server.py（FastAPI 应用）
    - /tools/review_ui/api.py（REST endpoints）
    - /tools/review_ui/static/（**新建子目录**；vanilla HTML/CSS/JS）
      - index.html / app.js / styles.css
    - /tools/review_ui/cli.py（CLI 启动入口）
    - /tools/review_ui/tests/

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/generator/、/content/、/docs/（除新增 fixture 文档外）

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md ADR-025（T-3.1 已立项；本任务依赖）+ ADR-002（运行时无 LLM；review_ui 是生产期工具，不违反）+ ADR-004（运行时与生产期严格分离）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-025 决策核心 + §2.1 D5 + §2.4 字段命名（FORGEWRIGHT_REVIEW_UI_PORT 默认 8765）
- /generator/scene_review_cli.py（T-2.8 已落地；理解 review_log.jsonl 接口；本 review_ui 写入兼容此接口）
- /generator/experiments/20260506T113419Z_baseline_011/graph_views/（T-2.8 graph_views 三件套实证产物；本 review_ui 复用 mermaid 文件）
- /generator/scene_metrics.py + /generator/scene_ai_judge.py（T-2.8 已落地；review_ui 读取其输出）

# 待落地点

## RUI-1：FastAPI server

1. /tools/review_ui/server.py：FastAPI 应用 + 静态文件挂载（/static → review_ui/static/）+ REST API 挂载（/api/...）
2. server 启动：env `FORGEWRIGHT_REVIEW_UI_PORT`（默认 8765）；CLI 入口 `python -m tools.review_ui [--port N] [--batch-dir <path>] [--scenes-dir <path>]`
3. 默认 batch_dir = `./generator/experiments/<latest>` 或 CLI 指定；scenes_dir = `./content/`
4. 不引入 React/Vue/Svelte 框架——纯 vanilla HTML/JS（mermaid.js 走 CDN script tag）

## RUI-2：REST API endpoints

5. /api/scenes — list scenes in batch_dir + scenes_dir（含 metadata：cost / pass status / dimensions advisory / dep_index sidecar）
6. /api/scene/{scene_id} — 单 scene 完整数据（scene.json + deps.json + judge result + paths from sampling）
7. /api/graph/{scene_id} — 返回 mermaid 文件内容（直接读 batch_dir/graph_views/<scene>.mermaid）
8. /api/playtest/{scene_id} — 返回 playtest worst paths（如 T-3.4 已跑过）
9. /api/review — POST endpoint 写入 review_log.jsonl（[A]/[R]/[S] + reason + timestamp）；与 T-2.8 scene_review_cli 接口兼容
10. /api/stale — 调 T-3.7 dep_propagate 生成 stale 场景列表（lazy 调用，缓存可选）

## RUI-3：前端 5 视图

11. **视图 1: graph 视图** — 渲染 T-2.8 mermaid 文件（fetch /api/graph/<scene_id> → mermaid.js 渲染 SVG）
12. **视图 2: 路径列表** — fetch sampling 路径数据 → 列出所有 entry → end paths + 点击高亮 graph 节点
13. **视图 3: validator issues** — schema / topology / sampling / mechanical 四 tab；分别读 scene_results.jsonl 中相应字段
14. **视图 4: visual asset thumbnail** — fetch /api/scene/<id>.character_refs → 读 manifest.json → 显示出场角色立绘 + 场景背景图
15. **视图 5: 审美层 [A]/[R]/[S] 标注** — 三按钮（accept / reject / skip）+ reason 文本框 → POST /api/review

## RUI-4：审美层 review 接口（feedback memory 锁定）

16. 阶段 3 激活审美层：审美层 review_ui [A]/[R]/[S] 写入 `<batch_dir>/review_log.jsonl` —— 与 T-2.8 scene_review_cli 兼容（共享同一 jsonl 文件）
17. UI 设计：突出显示 [A]ccept / [R]eject / [S]kip 三按钮 + reason 文本框 + 提交按钮；submit 后自动跳到下一未审场景
18. 已 review 场景显示标记（绿/红/灰角标）

## RUI-5：与 dep_propagate / chapter / playtest 的整合

19. 上方 nav bar 含：scene list / chapter list（按 chapter.acts 分组）/ stale list（命中 dep_index）/ playtest worst paths list
20. stale 场景 nav 显示标红；点击进入 review 视图，读 sidecar reasons 提示作者

## RUI-6：read-only + 不做编辑

21. UI 不提供任何"编辑场景内容"按钮；编辑由作者直接改 JSON + git workflow（与 ADR-006 + ADR-025 决策一致）
22. 仅审美层 [A]/[R]/[S] 标注 + reason 写入 review_log.jsonl（这是 review 的元数据写入，不是场景内容编辑）

# 不要做的事
- 不要引入 React / Vue / Svelte / Next.js 等前端框架（开源门槛上升；vanilla HTML/JS 可读性高 + 零依赖）
- 不要做"编辑场景内容"功能（ADR-025 + ADR-006）
- 不要做生产期外的运行时部署（review_ui 仅 localhost；不打包成 Docker / 不上 CDN）
- 不要扩展 /schema/（review_ui 只读已有数据）
- 不要硬编码 batch_dir / scenes_dir（CLI flag 可配）
- 不要尝试集成 LLM / 自动生成功能（仅 review 工具）
- 不要碰 /generator/ /validator/（仅读其产物，不改其代码）

# 测试
- pytest /tools/review_ui/tests/ 全过
- 必含：API endpoints unit test（mock batch_dir + scenes_dir 数据）/ HTML 渲染基本 smoke / review POST endpoint 正确写入 review_log.jsonl 测试
- 跑 /review skill + validate-all
- **可选实测**：用 baseline_011 batch dir 启动 review_ui localhost:8765 跑端到端（作者可手动浏览器打开看 5 视图渲染）

# A 阶段完成标志
- diff 摘要（按 RUI-1 ~ RUI-6 六段说明）
- pytest 输出
- commit message: `feat(tools): review UI web single-page (T-3.6; ADR-025)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出 + 启动后浏览器截图（可选）

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.6_review_ui_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.10 实测期作者使用 review_ui + scene_review_cli 双轨标 [A]/[R]/[S]
```

### T-3.7 ｜ 一致性维护（本体变更反向 propagate）｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 完成标志要求"一致性维护（本体变更时标记需重审的已生成内容）"——基于 ADR-023 content_dependency_index sidecar 实现反向 propagate 工具：本体变更 → 反向查 sidecar → 标记 stale 场景 + 输出 report。

# 任务类型：[A-execute]
- 纯执行；新建 /tools/dep_propagate.py；不动 schema / ADR / L1 文档
- 必须依赖 T-3.2 schema 已 merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线工具新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /tools/dep_propagate.py（**新建**）
  - /tools/__init__.py（如不存在则新建；**注**：tools/ 历史是占位目录，本任务首次正式化）
  - /tools/tests/（**新建**测试目录 + 测试文件）

严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/generator/、/content/、/docs/（除新增 fixture 文档外）

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md ADR-023（T-3.1 已立项；本任务依赖）
- /docs/DECISIONS.md ADR-006（本体真相之源；理解为何反向 propagate 在生产期是必需）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §3 ADR-023 决策核心 + §2.4 字段命名 + §6 wave 图（理解 T-3.7 与 T-3.5 的关系）
- /schema/content_dependency_index.schema.json（T-3.2 已落地；理解字段集）
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
       """
   ```
2. StaleScene dataclass：`{scene_id, scene_path, deps_path, reasons: list[str]}`（reasons 含具体哪个 ontology_id / state_path 命中）
3. 实现：scan content/ 下所有 *.deps.json → load → 检查 dependency 字段交集 → 命中加入返回列表

## DP-2：本体 diff 检测（可选 helper）

4. helper 函数：`diff_ontology(ontology_path: Path, since_commit: str) -> ChangedOntology`
   - 用 git diff 检测自 since_commit 以来 ontology entities 变更
   - 输出：changed character_ids / location_ids / clock_ids / state_paths（如 narrative_weight 变 / dramatic_triggers 改 / state_path_slug 改）
5. 不必精确——粗粒度即可（"vellin entity 任意字段变 → 标 char_vellin 为 changed"），生产期 propagate 报告偏宽松好于偏紧（漏报代价 > 误报代价）

## DP-3：CLI 入口

6. CLI：`python -m tools.dep_propagate [--since <commit>] [--changed-ontology <ids>] [--changed-state-paths <paths>] [--report <markdown_path>]`
7. 输出形态：markdown report 含 stale scenes 列表 + 每场景的 reasons + suggested 重审优先级（按 narrative_weight 排序：core > minor > context_only）

## DP-4：与 review_ui 的接口

8. JSON 输出形态（除 markdown 外）：`<output>.json` 兼容 review_ui（T-3.6 范围）展示——T-3.6 启动后 review_ui 加 stale 标记面板时复用本任务输出
9. CLI 加 `--json <path>` flag 输出 JSON

## DP-5：与 git workflow 集成（可选）

10. 提供 git pre-commit hook 模板（不强制安装；放 /tools/dep_propagate_hook_template.sh）：作者修改 ontology 后 pre-commit 自动跑 dep_propagate 并 review stale 场景列表
11. 作者明示安装—— 由作者起会话决定，不在本任务自动安装到 .git/hooks/

# 不要做的事
- 不要自动修改 stale 场景内容（仅标记 + report；修复由作者人工或 T-3.5 重新生成）
- 不要扩展 /schema/（本任务读 sidecar，不写新 schema）
- 不要碰 /generator/ /validator/（本任务是工具层；与 generator 解耦）
- 不要碰 ontology 数据（read-only）
- 不要硬编码 ontology 路径（应可配置 content_root + ontology_root）

# 测试
- pytest /tools/tests/ 全过
- 必含：fixture 含 3 个 mock scene + sidecar，1 个改 character_id 触发命中，1 个改 state_path 触发命中，1 个不命中 → find_stale_scenes 返回正确列表 / report 渲染正确
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 DP-1 ~ DP-5 五段说明）
- pytest 输出
- commit message: `feat(tools): consistency maintenance via dep_index reverse propagation (T-3.7; ADR-023)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.7_consistency_maintenance_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge；T-3.6 review_ui stale 面板可在本 PR merge 后启动接入
```

### T-3.8 ｜ 版本控制集成 ｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 完成标志要求"版本控制集成（每次修改记版本）"——为每个生成场景记录 version metadata sidecar `<scene>.version.json`，关联 git commit + 生成时间 + 上次修改人。**走 sidecar 形态不入 dialogue_graph schema**（保 ADR-016 schema 版本号策略：既有 schema 不动）。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/version_recorder.py + sidecar 写入；不动 schema / ADR / L1 文档
- 不阻塞下游；可与 T-3.5 / T-3.7 / T-3.9 同期推进

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/version_recorder.py（**新建**）
  - /generator/batch_scheduler.py（**仅添加 version_recorder hook 调用**；如 T-3.5 已 merge 则在其后追加 hook；不动主流程）
  - /generator/tests/

严禁修改：/schema/（特别是 dialogue_graph schema；版本元数据走 sidecar 不污染场景 schema）、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py（仅可在 batch_scheduler hook 接入；不动主算法）、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-016 §schema 版本号策略（既有 schema 不动；新增字段走 optional + additionalProperties 兼容路径——本任务沿用更严格做法：sidecar 形态完全不动 schema）+ ADR-006 单一真相之源（version metadata 是审计元数据，不属真相源；sidecar 适当）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §1（v0.1 完成标志表 "版本控制集成" 行）
- /generator/dep_index_writer.py（T-3.5 已落地；理解 sidecar 写入模式；本任务参考其形态）

# 待落地点

## VR-1：sidecar schema（轻量；不入 /schema/）

1. version_metadata 字段集（dataclass + JSON 序列化）：
   ```json
   {
     "scene_id": "...",
     "version": 1,
     "first_generated_at": "2026-05-XX...",
     "last_modified_at": "2026-05-XX...",
     "git_commit_at_generation": "<sha>",
     "git_branch_at_generation": "<branch>",
     "generation_method": "batch_scheduler" | "manual_edit" | "regenerate" | "playtest_fix",
     "previous_versions": [
       {"version": 0, "commit": "<sha>", "modified_at": "...", "changed_fields": [...]}
     ]
   }
   ```
2. 不入 /schema/ 文件（保 dialogue_graph schema 不动）；仅作 generator 内 dataclass + JSON 序列化
3. 文件位置：`<scene>.version.json`（与 deps.json / summary.json 同目录平行）

## VR-2：核心写入函数

4. /generator/version_recorder.py：核心函数 `def record_version(scene_path: Path, generation_method: str, changed_fields: list[str] | None = None) -> VersionMetadata`
   - 检测 git HEAD commit + branch（用 subprocess git rev-parse）
   - 如 `<scene>.version.json` 已存在：bump version + append previous_versions
   - 如不存在：version=1 + previous_versions=[]
5. 错误处理：git 不可用（如非 git 仓库）→ git_commit / git_branch 字段写 null + log warning + 继续；不阻塞 scene 写入

## VR-3：调度器 hook

6. /generator/batch_scheduler.py：在 generate_scene 完成 + dep_index sidecar 写入后追加 record_version 调用（generation_method="batch_scheduler"）
7. 失败传播：record_version 失败 → log warning + 继续；与 T-3.5 BS-5 一致

## VR-4：CLI 入口（手动编辑后追溯）

8. CLI：`python -m generator.version_recorder <scene_path> --method manual_edit [--changed-fields field1,field2]`
9. 让作者在手动编辑某场景后追溯 version bump（避免漏记）

## VR-5：与 chapter_assembler / dep_propagate 的协同

10. T-3.7 dep_propagate 标记 stale 场景时，可同时检查 version 是否需 bump（视需要在 propagate 报告中提示作者）
11. 不在本任务硬集成——只提供 hook，由作者后续决定

# 不要做的事
- 不要扩展 /schema/（特别 dialogue_graph schema；版本元数据走 sidecar）
- 不要尝试自动 git commit / git push（仅记录 metadata + 当前 git 状态；commit/push 仍由作者明示）
- 不要把 version metadata 嵌进 scene.json（保 dialogue_graph schema_version 0.1.1 不破）
- 不要用复杂 diff 算法（本任务记录的是元数据，不是场景内容 diff；diff 由 git 提供）
- 不要碰 /generator/generate_scene.py 主算法

# 测试
- pytest /generator/tests/test_version_recorder.py 全过
- 必含：record_version 首次调用测试 / 重复调用 bump version 测试 / git 不可用 fallback 测试 / CLI 集成测试
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 VR-1 ~ VR-5 五段说明）
- pytest 输出
- commit message: `feat(generator): version control integration via sidecar (T-3.8)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.8_version_recorder_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge
```

### T-3.9 ｜ Chapter/Act 容器生成扩展 ｜ [A-execute]

```text
你的任务是落地 ROADMAP §阶段 3 重点工作"Chapter/Act 层级结构设计"的 generator 层——把生成的场景自动挂到 chapter.acts.included_scenes 容器下。Chapter/Act schema 已在阶段 2 T-2.2 落地（ADR-016 §Chapter/Act 容器 schema），本任务仅落地 generator 自动 propagate 工具。

# 任务类型：[A-execute]
- 纯执行；新建 /generator/chapter_assembler.py + 调度器 hook 接入；不动 schema / ADR / L1 文档
- 必须依赖 T-3.5 批量调度器 PR merge（chapter_assembler 在调度器写完 scene 后调用）

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——主线 generator 模块新增不在 §1.5.4 跳 BC 破例 5 类内。

# 模块边界（硬性）
允许修改：
  - /generator/chapter_assembler.py（**新建**）
  - /generator/batch_scheduler.py（**仅添加 chapter_assembler hook 调用**；不动 worker pool / token bucket / lock 逻辑）
  - /generator/tests/

严禁修改：/schema/、/state/ontology/（数据写入由 chapter_assembler 接管；用 file lock 沿用 T-3.5 ontology lock）、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_scene.py、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-016 §Chapter/Act 容器 schema（chapter / acts / included_scenes 字段定义）
- /schema/chapter.schema.json（T-2.2 已落地；理解字段结构）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §1（v0.1 完成标志表）+ §2.1 D10（Chapter/Act 不立新 ADR 说明）
- /generator/batch_scheduler.py（T-3.5 已落地；理解 hook 接入位置）
- /state/ontology/__init__.py（理解 ontology loader + chapter 写入路径）

# 待落地点

## CA-1：核心 propagate 函数

1. /generator/chapter_assembler.py：核心函数 `def assign_scene_to_chapter(scene_anchor: str, ontology_path: Path, chapter_id: str | None = None, act_id: str | None = None) -> ChapterAssignment`
   - 如 chapter_id / act_id 显式给：直接挂到 chapter.acts[act_id].included_scenes
   - 如未给：scene_anchor 解析 + 启发式查（如按 ontology 现有 chapters 已有的 act 范围匹配）OR 落"unassigned" buffer（return ChapterAssignment(success=False, reason="no chapter target specified")）
2. ChapterAssignment dataclass：`{success, scene_anchor, chapter_id, act_id, reason}`

## CA-2：ontology 写入（受 file lock 保护）

3. 写入路径：sourceuse T-3.5 已实现的 ontology file lock helper（如未独立 helper，本任务在 T-3.5 lock 模块内复用）
4. 操作：read ontology JSON → modify chapters[chapter_id].acts[act_id].included_scenes append scene_anchor → write back（保持 idempotent；scene_anchor 已在 included_scenes 中则不重复 append）

## CA-3：调度器 hook

5. /generator/batch_scheduler.py：在 generate_scene 完成 + dep_index sidecar 写入后追加调用 chapter_assembler.assign_scene_to_chapter
6. 失败传播：assign 失败 → log warning + 继续；不回滚 scene.json（与 T-3.5 BS-5 一致）

## CA-4：CLI 入口（手动 reassign）

7. CLI：`python -m generator.chapter_assembler <scene_anchor> --chapter <chapter_id> --act <act_id>`
8. 让作者在审阅工坊期手动调整某场景归属（如发现起初挂错 chapter）

## CA-5：验证（不破 ADR-006）

9. 验证：assign 不修改场景 scene.json 内容（仅修改 ontology 容器）；ADR-006 单一真相之源 + ADR-016 chapter 容器位置（state/ontology 顶层 chapters[]）维持
10. 验证：chapter / act schema_version "0.3.0" 维持不动（ADR-016 §schema 版本号策略）

# 不要做的事
- 不要在 generate_scene 主流程内调用 chapter_assembler（保留分离；调用点在 batch_scheduler hook，非 generate_scene 主算法）
- 不要扩展 chapter.schema.json（schema 不动；本任务仅做数据写入工具）
- 不要立新 ADR（D10 明示 Chapter/Act 不立新 ADR；ADR-016 后果段已涵盖）
- 不要碰 dialogue_graph.schema.json / scene.json schema_version
- 不要尝试自动推断 chapter / act 归属（启发式留 hook 但默认 fallback 是 unassigned；自动推断由作者人工或 LLM 补齐，不在本任务范围）

# 测试
- pytest /generator/tests/test_chapter_assembler.py 全过
- 必含：fixture ontology with chapters[] + acts[] → assign_scene 测试 / idempotent 测试 / chapter_id 缺失 fallback "unassigned" 测试 / file lock 测试（mock fcntl）
- 跑 /review skill + validate-all

# A 阶段完成标志
- diff 摘要（按 CA-1 ~ CA-5 五段说明）
- pytest 输出
- commit message: `feat(generator): chapter/act container auto-assignment (T-3.9; ADR-016 chapter container layer)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash + 测试输出

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.9_chapter_assembler_review.md
- C 阶段：吃报告改代码 + 追加 commit
- L2 验收过关后 merge
```

### T-3.10 ｜ 完成标志实测（作者跑一周 ≥10 场景）｜ [A-execute]

```text
你的任务是阶段 3 完成标志的实证 batch run——作者本人跑一周（5 工作日 + 2 周末），完成 ≥10 场景的生成 + 审阅 + 入库；测量 gross_pass_rate ≥ 80% + 审美层 [A]ccept rate ≥ 60% 双指标。

# 任务类型：[A-execute]（实测会话；不开发代码）
- **实测期 ≈ 1 周**——非单次会话，是作者跨多日多次会话操作
- A 阶段不写代码；本任务是"用工具链 + 观测 + 记录数据"
- 必须依赖 T-3.5 + T-3.6 + T-3.4 全部 PR merge

# 跳 BC 破例适用性
本任务**默认走完整 ABC**——但 ABC 在本任务有变体：
- A 阶段 = 作者跨多日跑批 + 审阅 + 写实测报告
- B 阶段 = 作者基于实测 finding 起 Codex review 实测报告 + 流水线整体（不只是单 PR diff）
- C 阶段 = 作者基于 review 起 Claude Code 修代码 / 文档（如 finding 含工具链 bug，对应起 R3.X follow-up；如 finding 仅文档级则修文档）

# 模块边界（硬性）
允许修改：
  - /generator/experiments/<batch_dir>/（实测 batch run 产出物入库）
  - /content/<scene_dir>/（实测产出场景 + sidecar 入库）
  - /docs/STAGE_3_IMPLEMENTATION_LOG.md（**新建**；实测期日志 + finding；按 STAGE_2 baseline 序列日志风格）
  - 实测期产生的 R3.X follow-up（视需要单独起任务）

严禁直接修改（实测期内）：/schema/、/state/、/state/ontology/（实测期 ontology 增量由 chapter_assembler 写入，受 file lock 保护；无需手动改）、/engine/、/validator/、/docs/DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §1 v0.1 完成标志阈值表（gross_pass ≥ 80% + [A] ≥ 60% + Y=10 场景/周）
- /docs/STAGE_2_ACCEPTANCE.md（实证形态参考；baseline_011 实测格式）
- /docs/HANDOFF_STAGE_2_TO_3.md
- /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md（baseline 协议；实测期沿用 + 加 playtest 维度）
- ~/.claude/projects/-Users-outsider-Desktop-Forgewright/memory/feedback_acceptance_review_deferred_to_stage_4.md（feedback memory 锁定；阶段 3 激活审美层 [A]/[R]/[S]）

# 待落地点

## IT-1：场景集准备

1. 作者准备 10-15 场景 spec（scene_setting + target_beats + participating_npcs）— 跨 2-3 个 chapter 范围；含 vellin / corvan / aelwin 主角色 + 阶段 3 实测期可补新角色（如 chap_act1 / chap_act2 不同章节）
2. 场景集放 /generator/experiments/stage3_implementation_v1/scene_specs.json

## IT-2：第一波跑批（baseline_012; ~5 场景）

3. 用 T-3.5 batch_scheduler 跑首波 5 场景（concurrent_n=3）
4. 跑完后：跑 dep_index 反向 propagate 检查 / 跑 playtest 5 persona × 20 paths/scene = 100 paths × 5 = 500 paths（独立编号 playtest_001）
5. 用 T-3.6 review_ui 启动 localhost:8765 → 浏览器访问审阅 5 场景 → 标 [A]/[R]/[S] + reason
6. 测量首波 gross_pass / [A] rate / mean cost / mean elapsed / playtest worst-10%

## IT-3：第二波 / 第三波（按需扩到 10+ 场景）

7. 视首波数据决定第二波范围（如首波 [A] rate < 60% 则起 R3.X follow-up 修 prompt 后再跑）
8. 编号续 baseline_013 / 014 + playtest_002 / 003

## IT-4：实测期日志

9. /docs/STAGE_3_IMPLEMENTATION_LOG.md 记录每波 batch：
   - 时间 + 编号 + 场景数 + cost
   - gross_pass_rate / [A] rate / [R] reasons
   - playtest worst-10% finding
   - dep_index 维度数据（avg ontology_ids_read / state_paths_written 数）
   - 长对话一致性观察（prior_scene_summaries 实际作用 + 是否撞 §9.2 真墙）
   - R3.X follow-up 触发列表

## IT-5：阶段 3 完成判定（实测末期）

10. 末期跑总结：实测 N≥10 场景；gross_pass_rate ≥ 80% + [A] rate ≥ 60% + Y=10 场景/周吞吐 + playtest worst-10% 0 critical issue 或全部修复 + dep_index 100% 写入 + chapter 容器分配率（实测）
11. 数据写入实测期日志末尾段
12. 阶段 3 完成判定：四项指标全 MET → 进 T-3.12 验收；任一未 MET → 起 R3.X 修复 + 二轮跑批

## IT-6：实测期 follow-up dispatch（**跳 BC 破例适用**）

13. 实测过程中遇 finding（baseline_NNN finding / playtest_NNN finding / R3.X follow-up）按 §1.5.4 跳 BC 破例第 1/2/3 类处理：作者起 A 阶段会话主动修 + 拆 commit 标注 finding + L2 quick check + merge

# 阶段 2 sequence 经验吸收

- 阶段 2 baseline_005 v3 → 011 经历 7 次 R2.X 修复链路；阶段 3 实测预期类似 sequence（或更短，因工具链阶段 3 起步比阶段 2 起步成熟）
- 阶段 2 baseline_011 100% gross_pass + 0% audit；阶段 3 加审美层后预期 [A] rate 60-80%（首批 prompt 调优后稳）
- 实测期不要追求"一次跑完 10 场景全过"——按 baseline + R3.X follow-up 迭代节奏推进

# 不要做的事
- 不要在实测期修改 generator / validator 主流程（如发现 bug → 起 R3.X follow-up 单独 ABC 走）
- 不要跳过 review_ui 标 [A]/[R]/[S] 流程（阶段 3 激活审美层是完成标志强化项 U-CL-1 的核心）
- 不要把实测期 R3.X follow-up 搞成大 PR；保持 commit 颗粒度细
- 不要在本任务里写阶段 3 验收报告（那是 T-3.12 范围）

# 测试 / 验证

- 实测期产出物 = 数据 + 日志 + 入库场景 + R3.X follow-up PR；不是单元测试
- 阶段 3 完成判定四指标必须全 MET 才能进 T-3.12

# A 阶段完成标志（实测期末）

- /docs/STAGE_3_IMPLEMENTATION_LOG.md 完整（含每波 batch 数据 + 完成判定数据）
- /generator/experiments/stage3_implementation_v1/ 入库 + 多个 baseline_NNN / playtest_NNN
- /content/ 含 ≥10 场景的实测产出物（scene.json + deps.json + version.json + summary.json）
- 至少 1 次 R3.X follow-up 实战（实测期发现 + 修 + merge）
- commit message: `feat(experiments): Stage 3 implementation log + ≥10 scenes via batch_scheduler (T-3.10)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：实测期跨多次会话；最终汇总 commit 集中开 PR

# B / C 阶段（变体；适用于实测后整体 review）

- B 阶段：Codex 会话 review STAGE_3_IMPLEMENTATION_LOG + 整体流水线观察（不仅单 PR diff）；report 落 /docs/reviews/<ISO_DATE>_T-3.10_implementation_review.md
- C 阶段：作者起 Claude Code 会话基于 review 起 R3.X 修复（如 finding 仅文档则修文档）
- L2 验收过关后进 T-3.12 验收
```

### T-3.11 ｜ 开源剥离边界清单 v0.2 增量 ｜ [A-execute]

```text
你的任务是为 /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md 加 v0.2 增量——把阶段 3 新引入的私有依赖（playtest 配置 / review_ui 路径 / version_recorder git 假设 / batch_scheduler 默认值等）补入清单。这是 synthesis §6/§7 C5 在阶段 3 期间维护边界 hook 的延续工作。

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
- /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md v0.1（阶段 2 T-2.10 落地 commit `eef3f3b`；理解三类边界 A/B/C 形态）
- /docs/reviews/master_plan/2026-04-30_synthesis.md §C5（开源剥离边界清单维护要求）
- /docs/HANDOFF_STAGE_2_TO_3.md
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md §4.2（阶段 2 v0.1 已落地，阶段 3 维护增量）

# 待落地点（按 v0.1 已有三类边界 A/B/C 拓展）

## v0.2-A：fixture / 角色 / 场景内容增量

1. /generator/playtest/personas/*.json（5 个 persona JSON）—— **作者通用 persona，建议保留入开源默认**（cautious / aggressive / completionist / speedrunner / role_player 是泛用 RPG persona，无作者私有特征）；如有 augmented_description 含《铁誓驿站》上下文则需剥离时清理
2. /generator/playtest_cost_log.jsonl + /tools/review_ui/state（review_log.jsonl）—— runtime 产物，剥离时不带（沿用 v0.1 §B 的 cost_log 处理方式）

## v0.2-B：资产版权增量

3. visual_assets 引用（如阶段 3 实测期补 14 立绘 + 1 background）—— 沿用 v0.1 §B；阶段 3 末期视实测产出添加具体路径

## v0.2-C：provider 假设增量

4. /generator/batch_scheduler.py 默认 N=3 + RPM=60 + ontology lock fcntl 假设 —— **POSIX file lock 在 Windows 不可用**；v0.2 标记需提供跨平台 fallback（如用 portalocker 库）；阶段 4 剥离时由 framework 仓库实现
5. /tools/review_ui/server.py FastAPI 依赖 + mermaid.js CDN URL 假设 —— **CDN URL 可能不可用 / mermaid.js 大版本变化**；v0.2 标记需提供 vendored mermaid.js fallback OR 让用户配置 CDN
6. /generator/version_recorder.py git subprocess 假设 —— **非 git 用户怎么用**；v0.2 标记需提供 fallback path

## v0.2-D：阶段 3 新增类别（可选）

7. **D 类（新）**：用户配置默认值
   - FORGEWRIGHT_BATCH_CONCURRENT_N / FORGEWRIGHT_PROVIDER_RPM / FORGEWRIGHT_REVIEW_UI_PORT 默认值都基于作者环境（PoloAI 速率限制 + 作者带宽）—— 开源用户需在 README 文档化所有 env vars
   - prompt_template_hash 算法（SHA256 of concat 文件）—— 算法假设稳定；剥离时 v0.2 维持

## v0.2-E：阶段 1.5 R1.5-* 遗留对开源剥离的影响

8. R1.5-1（剩余 14 立绘 + 1 background 全 batch 跳过）—— 阶段 4 剥离时如开源 framework 不带任何视觉资产例子，需 framework 仓库提供 placeholder + 文档说明用户如何按双模流程生成自己的资产
9. R1.5-3（视觉判官 vs 作者 kappa 未算）—— 不影响开源剥离；标记为"作者评测专属，不入框架默认评测路径"

# 不要做的事
- 不要立新 ADR（D10 明示 C5 OPEN_SOURCE_CARVE_OUT_INDEX 不立新 ADR；维护增量即可）
- 不要碰任何 /schema/ /code/ 路径
- 不要修改 CLAUDE.md / ROADMAP.md / DECISIONS.md
- 不要在本任务做实际剥离（剥离动作在阶段 4）
- 不要把 v0.1 段落删掉（增量是 append，不是重写）

# 文档增量结构

在 v0.1 现有 §2 三类边界（A/B/C）下追加：

```markdown
## §3 v0.2 增量（阶段 3）

### v0.2-A：fixture / 角色 / 场景内容（阶段 3 新增）

- ...（按上述 1-2 落地）

### v0.2-B：资产版权（阶段 3 增量）

- ...（按上述 3 落地）

### v0.2-C：provider 假设（阶段 3 增量）

- ...（按上述 4-6 落地）

### v0.2-D：用户配置默认值（新类别）

- ...（按上述 7 落地）

### v0.2-E：阶段 1.5 / 阶段 2 遗留对剥离的影响

- ...（按上述 8-9 落地）

## §4 阶段 3 末期 follow-up

- 阶段 3 末期（实测后）回顾：哪些假设实测验证了 / 哪些反向触发新条目
- 阶段 4 剥离 checklist（v0.2 起步罗列；阶段 4 详化）
```

末尾在 v0.1 已有"## 版本"段更新版本号 v0.2 + 日期。

# 测试
- 跑 /review skill + validate-all（文档校验）
- 不需 pytest（纯文档任务）

# A 阶段完成标志
- /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md v0.2 diff 摘要（按 v0.2-A ~ v0.2-E 五段说明）
- commit message: `docs: OPEN_SOURCE_CARVE_OUT_INDEX v0.2 increment for Stage 3 (T-3.11; C5)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash

# B / C 阶段（同 §1.5）
- B 阶段：Codex 会话 review；report 落 /docs/reviews/<ISO_DATE>_T-3.11_oss_carve_out_v0.2_review.md
- C 阶段：吃报告改文档 + 追加 commit
- L2 验收过关后 merge
```

### T-3.12 ｜ 阶段 3 验收报告 ｜ [B-author-gate]

```text
你的任务是产出 /docs/STAGE_3_ACCEPTANCE.md——阶段 3 完成判定 + 数据汇总 + R3.X 遗留 + 阶段 4 启动前置条件交接。这是阶段 3 收官 [B-author-gate] 任务，作者最终签字。

# 任务类型：[B-author-gate]
- 修改 L1 架构文档（验收报告归 L1 类）；CLAUDE.md 规则 9/10 例外（作者已通过 L2 规划师 / 阶段验收会话明确授权）
- 必须依赖 T-3.10 实测完成 + 完成判定四指标全 MET

# 跳 BC 破例适用性
本任务**跳 BC 破例适用第 5 类**（阶段 3 验收报告）—— 沿用阶段 2 T-2.13 验收报告作者明示授权跳 BC 直接 merge 先例。但内容仍需作者最终签字。

# 模块边界（硬性）
允许修改：
  - /docs/STAGE_3_ACCEPTANCE.md（**新建**）
  - /docs/HANDOFF_STAGE_3_TO_4.md（**新建**；草稿；阶段 4 规划师启动后由其修订）

严禁修改：CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md（**注**：ROADMAP §阶段 3 完成标志可能因实测发现需要措辞修订；如需修订属跨边界 X 级元任务，作者另起 L1 修订会话）/ SCHEMA_v0*.md / 任何 /schema/ 文件 / 任何代码

# 必读
- /CLAUDE.md（规则 1-10）
- /docs/STAGE_2_ACCEPTANCE.md（参考体例 + 数据汇总形态）
- /docs/STAGE_1_ACCEPTANCE.md + /docs/STAGE_1.5_ACCEPTANCE.md（参考遗留项处理形态）
- /docs/HANDOFF_STAGE_2_TO_3.md（参考交接档形态）
- /docs/STAGE_3_IMPLEMENTATION_LOG.md（T-3.10 实测期产出；本任务核心数据源）
- /generator/experiments/stage3_implementation_v1/（实测 batch + playtest 产出物）
- /docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md（含完成标志阈值表）
- /docs/ROADMAP.md §阶段 3 完成标志（与实测数据对照）

# 待落地点

## VR-1：STAGE_3_ACCEPTANCE.md 主体

参考 STAGE_2_ACCEPTANCE.md 体例：

1. **§1 阶段 3 完成判定核对**：表格列 — 指标 / ROADMAP-ADR 目标 / 实测 / 判定（MET / 部分 / 推迟）
   - generate_scene 主函数（已 T-2.6 落地；阶段 3 沿用）
   - 批量生成调度器（T-3.5）
   - 审阅界面（T-3.6）
   - 一致性维护（T-3.7）
   - 版本控制集成（T-3.8）
   - 实测吞吐 ≥ 10 场景/周（T-3.10）
   - gross_pass_rate ≥ 80%（实测）
   - 审美层 [A]ccept rate ≥ 60%（实测）
   - playtest bots 至少 5 场景跑过完整 100 paths/scene + worst-10% 0 critical issue 或全部修复（T-3.4 + T-3.10）
   - 长对话一致性 C 起步落地 + A/B hook（T-3.3）
   - 启动闸门 C2 / C6 / U-CL-1 / U-CL-5 / U-GPT-7 全部 MET
2. **§2 实证数据**：baseline_NNN + playtest_NNN 序列汇总；每波 batch 数据；总体指标
3. **§3 工作量速览**：T-3.0 ~ T-3.12 主任务表 + R3.X follow-up 系列（含跳 BC 破例计数）
4. **§4 遗留问题**（R3.* 表）—— 阶段 3 不解决但阶段 4 必须处理的项
5. **§5 阶段 4 启动前置条件**——闸门清单留给阶段 4 规划师
6. **§6 真实费用回顾**——LLM 成本 / token 用量 / 与协议估算对照
7. **§7 模块边界自检**——grep 验证 ADR-002 / ADR-004 / ADR-006 / ADR-008 + 阶段 3 新增 ADR-022 ~ 026 全部坚守
8. **§8 跨 LLM 评审实绩**——主任务 ABC 闭环率 + 跳 BC 破例计数 + 跨 LLM 评审 prompt 演进
9. **§9 签字**——作者签字栏 + 接受条件

## VR-2：HANDOFF_STAGE_3_TO_4.md 草稿

参考 HANDOFF_STAGE_2_TO_3.md v0.1 体例：

1. 项目是什么（与历史交接档一致）
2. 玩家交互模式铁律（铁律段；与历史一致）
3. 阶段 3 做了什么（13 主任务 + R3.X follow-up）
4. 阶段 3 收尾时的架构遗留 R3-* 表
5. 阶段 4 启动条件摘自 ROADMAP §阶段 4
6. 阶段 4 规划粗想（给下一规划师参考；未与作者校准）
7. 必读顺序（新规划师首轮阅读）
8. 工作模式（继承 v0.3 治理 §10）
9. 阶段 3 残留的工作流改进建议（含审阅 UI / playtest / dep_index 实战经验）
10. 跨阶段串行 / 并行预判
11. 总盘子预判（阶段 4 LLM 成本估算 + dev token）
12. X 跨阶段提醒（X1-X6 沿用 + 阶段 3 实测产生的新 X 项）

## VR-3：审美层评估激活后的 feedback memory 处理

3. 阶段 3 实测激活了审美层 [A]/[R]/[S]（feedback memory `feedback_acceptance_review_deferred_to_stage_4.md` 锁定的"推迟到阶段 4"被阶段 3 提前激活）—— 验收报告 §1 注明此点 + 提示作者更新 feedback memory（不在本任务范围；作者另起 memory consolidate）

## VR-4：跨边界事项更新

4. X1（ADR-022~026 立项已在 T-3.1 完成）→ 标 closed
5. X2 / X3 / X4 / X5 / X6 视实测期是否产生新 X 项更新

# 不要做的事
- 不要碰 CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md（除非作者明示授权 L1 修订）
- 不要尝试在验收报告里立新 ADR（ADR 走 T-3.1 + 阶段 4 规划师范围）
- 不要写"阶段 4 任务清单"（HANDOFF 仅"粗想"段；阶段 4 规划师启动后自定 STAGE_4_TASKS）
- 不要把 STAGE_3_IMPLEMENTATION_LOG 内容直接复制粘贴到 ACCEPTANCE.md（汇总 + 引用即可，不要膨胀）

# A 阶段完成标志

- /docs/STAGE_3_ACCEPTANCE.md 完整（≤ 500 行参考阶段 2 体量）
- /docs/HANDOFF_STAGE_3_TO_4.md v0.1 草稿（≤ 300 行参考阶段 2 体量）
- commit message: `docs: Stage 3 acceptance report + Stage 3 → 4 handoff draft (T-3.12)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR；产出 = PR URL + commit hash

# B / C 阶段（跳 BC 破例第 5 类适用）

- 沿用阶段 2 T-2.13 跳 BC 破例先例 — 作者明示授权跳 B/C 直接 merge
- L2 quick check：核对完成判定四指标 / R3.X 遗留分类 / 阶段 4 启动前置条件
- 作者签字 + merge → 阶段 3 收官；阶段 4 规划师可启动
- 如作者发现实质问题（如完成判定错算 / 遗留项错放）则回 A 阶段重做
```

---

## 9. 跨边界事项（X 系列）

> 跨阶段 / 跨边界长尾。L2 草稿仅识别，不直接落地。

| 编号 | 内容 | 处理时机 |
|---|---|---|
| **X1** | ADR-022 ~ 026 立项不在 v0.1 草稿范围 — v0.1 仅识别决策核心；实际立项动作由 v1.0 commit 后作者另起 L3 执行会话跑 T-3.1 paste-ready prompt 落 `/docs/DECISIONS.md` | v1.0 后立 |
| **X2** | ADR-020 v0.2 修订（"审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy" 写进 ADR）—— 未来 X 级元任务（阶段 2 收官遗留 X4） | 阶段 3 起手期作者另起 L1 修订会话；不阻塞 |
| **X3** | ROADMAP §阶段 2 「单次生成人工可接受率 ≥ 70%」字面措辞与 feedback memory（推迟到阶段 4）冲突 —— 同 X2 | 同 X2 |
| **X4** | ADR-011 / 013「google.genai 是唯一 Gemini 入口」假设随 R2.7 PoloAIProvider 接入实质破裂 —— 待修订 | 阶段 3 / 4 视需要立 X 级元任务 |
| **X5** | 阶段 4 启动闸门清单 — 阶段 3 完成后由阶段 4 规划师承接（参 synthesis §9.6 playtest bots 阶段位 / §9.8 开源剥离边界） | 阶段 4 规划师 |
| **X6** | 阶段 1.5 R1.5-1~6 遗留（剩余 14 立绘 + 1 background 全 batch / acceptance_rate 未测 / 视觉判官 vs 作者 kappa 未算 / C4 parity smoke 未跑 / alpha 不透明 / mini probe ergonomic）—— 阶段 3 实测期触发是否补 14 立绘取决于实测场景集 | 阶段 3 实测期 / 阶段 4 |

---

## 10. 修订记录

- **2026-05-07 v0.1**：初版 L2 草稿。Wave 1 上下文确认 + Wave 2 与作者校准 10 项决策（D1~D10）+ Wave 3 草稿落盘。**分段落盘策略**：§0~§7 + §9~§11 骨架单次 Write 落盘（本次）；§8 paste-ready prompts 13 个由后续 Edit 逐次追加（规避 ECONNRESET 大消息风险）。

---

## 11. 版本

本文件版本：v0.1（阶段 3 任务清单 L2 草稿；分段落盘策略）
最后更新：2026-05-07
产出方：阶段 3 L2 规划师会话（claude/sweet-bardeen-863720 worktree）
