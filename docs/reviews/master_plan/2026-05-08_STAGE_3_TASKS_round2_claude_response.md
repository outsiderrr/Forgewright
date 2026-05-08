# STAGE_3_TASKS draft v0.1 — Claude round 2 response

**日期**：2026-05-08
**对应 critique**：[`2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md`](2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md)（GPT-5.5 22 finding：🔴 10 / 🟡 11 / 🟢 1）
**评审对象**：[`2026-05-07_STAGE_3_TASKS_draft_v0.1.md`](2026-05-07_STAGE_3_TASKS_draft_v0.1.md)
**Claude 反应者**：阶段 3 L2 规划师会话（claude/sweet-bardeen-863720 worktree）
**作者拍板**：outsiderrr（2026-05-08）

> 仿 Round 5 `2026-04-30_round2_claude_response.md` 体例。L2 级 critique 严守 review/author 分离——Claude 不直接吸收 Codex 全部意见整合 v1.0；先写本反应文档（含 Claude 独立判断 + 与 Codex 严重度争议 + 作者拍板），再整合 v1.0 进 `/docs/STAGE_3_TASKS.md`。

---

## 1. 总体回应

Codex critique 整体质量高——22 条 finding 中 19 条直接命中 v0.1 真问题，**Claude 视角因为没去读 repo 现状（`pyproject.toml` / `context_assembler.py` / `generate_scene.py`）漏抓了 5 条工程层 🔴 finding（F2 / F3 / F5 / F6 / F12）**。这正是 cross-LLM 评审在 Round 5 验证过的 ~50% 增益形态（synthesis §11）。

Claude 与 Codex 的严重度分歧仅 1 条（F1）；其余 21 条 Claude 同意 Codex 严重度判定（F8 阈值数值需作者拍板，但严重度 🔴 同意）。

| 类别 | 数量 | finding 编号 |
|---|---|---|
| Claude 完全同意 🔴 | 8 | F2 / F3 / F4 / F5 / F6 / F7 / F9 / F10 |
| Claude 严重度反驳 🔴 → 🟢 | 1 | **F1**（详 §3）|
| Claude 同意 🔴 但需作者拍板阈值 | 1 | **F8**（详 §3）|
| Claude 同意 🟡 | 11 | F11 ~ F21 |
| Claude 同意 🟢 | 1 | F22 |

cross-LLM 评审增益形态对照：

| 阶段 / 方向 | 共识 | 互补 / 漏抓 | 严重度分歧 | 直接矛盾 |
|---|---|---|---|---|
| Round 5（Claude × GPT-5.5）路线图层 | 8 | 12（Claude 漏 7 / GPT 漏 5）| 1（C7）| 0 |
| 阶段 3 L2 critique（本次）| ~3（v0.1 已抓的）| **19（Claude 漏抓为主）**| 1（F1）| **7（F1 + F2 + F3 + F6 + F7 + F11 + F12）**|

阶段 3 L2 critique 直接矛盾 7 条占比 32%，远高于 Round 5（0 条）—— 这是 v0.1 草稿内**前后表述不一致**（如 §1 表 vs §8 prompt vs §7 概览三者口径漂移）的实证。Codex 抓得很准。v1.0 整合时这 7 条直接矛盾必须**逐条对齐**。

---

## 2. 作者拍板记录（2026-05-08）

> 作者就 v0.1 → v1.0 整合的 3 个开放议题给 Claude 明示授权。

| 议题 | 候选方案 | 作者拍板 |
|---|---|---|
| **F1 严重度** | A. 接 Codex 标 🔴（v1.0 整合时 main commit 工作量计入闸门）/ B. Claude 反驳降 🟢（v1.0 整合常规步骤；不阻塞 v0.1 起手） | **B 同意 Claude（降 🟢）** |
| **F2 review_ui 依赖方向** | A. 加 FastAPI / uvicorn deps + tools package 注册 pyproject.toml / B. 改 stdlib `http.server`（守"零依赖"但破 ADR-025 极简精神） | **A 加 FastAPI deps + 修 pyproject.toml** |
| **F8 logic regression gate 阈值** | A. "0 critical validator failures + warning/minor 允许在 R3.X 修"（最严最清晰；与 F10 severity rubric 联动）/ B. gross_pass ≥ 95%（数值化；阶段 2 体例一致）/ C. 保留 v0.1 80%（Codex 反对） | **A "0 critical validator failures + warning/minor 在 R3.X 修"** |

---

## 3. F1 严重度反驳（Claude 独立判断）

> Codex 把 F1 标 🔴 阻塞，Claude 反驳应为 🟢 体例优化。这是本轮 cross-LLM critique 唯一严重度分歧。

### Codex 论据（critique F1）

> "草稿宣称位于 `/docs/reviews/master_plan/2026-05-07...`，13 个 prompt 也让执行会话读这个路径；但实际文件只在 `.claude/worktrees/...` 下。若 v1.0 不改，执行会话会读不到源文件。"

### Claude 反驳

**1. v0.1 草稿是 L2 规划层产物，不是 L3 执行入口**

参考阶段 2 同款先例 [`2026-05-03_STAGE_2_TASKS_v1.0_draft.md`](2026-05-03_STAGE_2_TASKS_v1.0_draft.md)（172 KB / 4500+ 行）—— 阶段 2 v1.0 草稿落 `/docs/reviews/master_plan/` 路径，与本草稿位置同源。**v1.0 进 main commit 后才是 L3 执行入口**（`/docs/STAGE_3_TASKS.md`），那时所有 paste-ready prompts 内"读 v0.1 草稿"自引用全局替换为 `/docs/STAGE_3_TASKS.md` 路径——这是 v0.1 → v1.0 整合的常规修订动作，与阶段 2 实测一致（参 `/docs/STAGE_2_TASKS.md` 现存路径引用）。

**2. v0.1 草稿当前阶段不会被 L3 执行会话读取**

v0.1 草稿当前用途仅 = (a) 作者审阅 / (b) Codex critique 输入 / (c) Claude L2 整合输入；不存在任何 L3 执行会话以 v0.1 草稿为输入的场景。所以"路径自引用失效"对 v0.1 草稿当前阶段**无实际工程影响**。

**3. v1.0 整合时全局路径替换是必做项，与阶段 2 一致**

v1.0 整合工作清单中已包含"§8 paste-ready prompts 逐个替换 v0.1 草稿引用为 `/docs/STAGE_3_TASKS.md`"——这是 v0.1 → v1.0 整合的标准动作（同阶段 2 v0.1.1 → v1.0 修订）。Codex 的"建议"等同于 v1.0 整合本身就要做的事，但严重度标 🔴（阻塞 v0.1 起手）混淆了 v0.1 草稿状态 vs v1.0 commit 状态。

### Claude 严重度修订建议

**F1 🔴 → 🟢**：v0.1 草稿当前阶段不阻塞，v1.0 整合时常规修订；与阶段 2 同款实证一致。

### 作者拍板

✅ 接受 Claude 反驳——F1 降 🟢。

### v1.0 整合该 finding 处理动作

v1.0 整合 prompt 全文 sed 替换 `/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md` → `/docs/STAGE_3_TASKS.md`（除草稿位置自身的元描述段保留外）。落 `/docs/STAGE_3_TASKS.md` §0 修订记录注明此次替换。

---

## 4. F8 阈值方案 A 落地（作者拍板 A 后的具体语言）

> 作者拍板 F8 选方案 A "0 critical validator failures + warning/minor 在 R3.X 修"。Claude 把 v1.0 §1 完成标志表 + ADR-022 / ADR-026 决策核心相应段落落到这个口径。

### 修订前（v0.1 §1 完成标志阈值表）

```
| gross_pass_rate | ≥ 80% |
| 审美层 [A]ccept rate | ≥ 60% |
| 实测吞吐 | 1 周 ≥10 场景 |
```

### 修订后（v1.0 §1 完成标志阈值表）

```
| logic regression gate | 0 critical validator failures（schema / topology / sampling / mechanical 任一 critical 级失败 = 阶段 3 不达标） |
| logic warning / minor 容忍 | warning / minor 级失败允许在 R3.X follow-up 闭环修复（不阻塞 T-3.10 当周吞吐统计）|
| 审美层 [A]ccept rate（pilot） | ≥ 60%（N=10 场景；附 Wilson 95% CI 报告，如 6/10 → CI 27%-86%；不用单点百分比伪装稳定）|
| 实测吞吐 | 1 周 ≥ 10 场景 |
| playtest worst-10% gate | 0 critical issue 或全部修复（critical 定义见 ADR-022 severity taxonomy）|
```

### F10 联动（critical severity taxonomy）

ADR-022 决策核心 + T-3.4 prompt 必须含 critical / major / minor 分级（详 v1.0 §3 ADR-022 修订段）：

- **critical** = validator 漏掉的非法路径、状态因果矛盾、角色 / 本体直接冲突、玩家结果透明度严重误导
- **major** = 显著叙事质量问题（节奏 / 风格 / 合理性）
- **minor** = 体例 / 措辞 / 微调

critical 必须作者明示确认，不能只靠 LLM-as-judge 自动通过 gate。

---

## 5. 22 finding 处理决议表（v1.0 整合输入）

| # | Codex 严重度 | Claude 反应 | v1.0 整合修订点（精要） |
|---|---|---|---|
| **F1** | 🔴 | 🟢（反驳 → 作者接受降级）| §0 修订记录注明全局路径替换；§8 prompts 全文 sed 替换 v0.1 草稿引用 → `/docs/STAGE_3_TASKS.md` |
| **F2** | 🔴 | 🔴（同意；作者拍板 A 加 FastAPI deps）| T-3.6 + T-3.7 模块边界加 `pyproject.toml`（fastapi/uvicorn deps + tools package 注册）；§7 模块边界列同步修订 |
| **F3** | 🔴 | 🔴（同意） | T-3.3 prompt：GraphContext → SceneGraphContext；同步修 `_build_scene_context` + `scene_strategies` skeleton/fill prompt 渲染段；节点级 GraphContext 阶段 3 不动 |
| **F4** | 🔴 | 🔴（同意） | T-3.5 SceneSpec 加 `depends_on_scene_ids` / `sequence_group`；调度器拓扑分层（同层并发，不同层串行）；T-3.10 实测场景集声明依赖图 |
| **F5** | 🔴 | 🔴（同意；作为 v0.1 最关键 finding）| ADR-023 决策核心修订：dep_index 写入语义改"context assembly over-approx trace"，不是 scene 反查；T-3.5 + T-3.3 prompt 都加 `GenerationDependencyTrace` 注入 |
| **F6** | 🔴 | 🔴（同意） | T-3.5 + T-3.9 写入顺序：write scene → assign chapter → write deps → record version；T-3.9 改为先 helper 库交付，T-3.5 调用 |
| **F7** | 🔴 | 🔴（同意） | §1 完成标志措辞修订为 "每个入库 scene 必须有 version sidecar，T-3.10 验收审计无缺失"；放弃 "scene 内 version 字段"（与 ADR-016 schema 不动一致）；放弃 "自动 git commit"（与 CLAUDE.md 一致）|
| **F8** | 🔴 | 🔴（同意；作者拍板方案 A）| §1 阈值表改 "0 critical validator failures + warning/minor 在 R3.X 修 + [A] ≥ 60% pilot + Wilson CI"；详 §4 |
| **F9** | 🔴 | 🔴（同意） | ADR-022 + T-3.4 加 calibration run（1 scene × 1 persona × 5 paths 实测 avg calls/path / tokens/path / seconds/path）+ `--max-cost-usd` / `--max-calls` / `--max-wall-clock-min` 三重 guard |
| **F10** | 🔴 | 🔴（同意；与 F8 联动）| ADR-022 加 critical/major/minor severity taxonomy；critical 必须作者明示确认，不靠 LLM judge 自动通过 |
| **F11** | 🟡 | 🟡（同意） | §7 表格 + T-3.0 prompt 统一为 "默认完整 ABC"（T-3.0 是阶段 3 主线起手任务，不是 R3.X follow-up）|
| **F12** | 🟡 | 🟡（同意） | T-3.8 拆 (a) version_recorder.py 独立模块（无依赖；Wave 0）+ (b) batch_scheduler hook 合并入 T-3.5；§6 wave 图 + §7 表格同步 |
| **F13** | 🟡 | 🟡（同意） | T-3.5 仅依赖 T-3.2 + T-3.3；T-3.4 与 T-3.5 并行；T-3.6 review_ui 对 playtest 视图做 "产物存在则展示，否则隐藏" degrade |
| **F14** | 🟡 | 🟡（同意） | T-3.5 prompt 加 "实现 RateLimitedProvider(LLMProvider)：同步 generate_structured 内用线程安全 bucket 阻塞等待"；不在 scene worker 外层限速 |
| **F15** | 🟡 | 🟡（同意） | T-3.2 schema 加 ADR-016 五命名空间 pattern 约束 + uniqueItems + scene_id pattern 与 dialogue_graph.graph_id 对齐；明示 optional missing-only |
| **F16** | 🟡 | 🟡（同意） | T-3.6 拆 T-3.6a (MVP) + T-3.6b (integrations) 子任务；浏览器 smoke / 截图 / mermaid 渲染检查改 mandatory |
| **F17** | 🟡 | 🟡（同意） | T-3.6 自带 fallback：可切换 ASCII/DOT 文件展示（T-2.8 已有产物）或 vendor 固定版本 mermaid bundle；不依赖 CDN 可用性 |
| **F18** | 🟡 | 🟡（同意） | T-3.0 或 T-3.4 加 mini calibration（3-5 个 baseline_011 场景作者 [A]/[R]/[S] vs AI judge 对齐 + 报告 disagreement）|
| **F19** | 🟡 | 🟡（同意） | T-3.10 改 "如出现 finding，至少 1 个按 R3.X 闭环；若 0 finding，记录 no-follow-up justification + raw metrics" |
| **F20** | 🟡 | 🟡（同意） | T-3.4 prompt 加 run_manifest.json：每 playtest_NNN 写 model_id / temperature / prompt hash / persona hash / option set / raw choice / judge rubric version |
| **F21** | 🟡 | 🟡（同意） | T-3.4 输出双层 `worst_paths.jsonl` + `worst_scenes.md/json`；scene 分数 = path 分布 / critical count / 最低分加权 |
| **F22** | 🟢 | 🟢（同意） | T-3.2 prompt 拍板 SCHEMA_v0.3.md 增量段（与 ontology 模块同 epoch），不让 A 会话现场决定 v0.4 |

---

## 6. 任务拆分变化（v0.1 → v1.0）

基于 F12 + F16 拆分决议：

| v0.1 编号 | v1.0 编号 | 状态 |
|---|---|---|
| T-3.0 | T-3.0 | 不动（含 R3.0/3.1/3.2 阶段 2 三遗留 + R2-5/F18 mini calibration）|
| T-3.1 | T-3.1 | 不动（ADR-022~026 立项；ADR 决策核心按 §5 修订）|
| T-3.2 | T-3.2 | schema 字段约束加严（F15）|
| T-3.3 | T-3.3 | GraphContext → SceneGraphContext（F3）|
| T-3.4 | T-3.4 | playtest 框架 + calibration run + run_manifest + worst paths/scenes 双层 + severity rubric（F9 / F10 / F20 / F21）|
| T-3.5 | T-3.5 | SceneSpec DAG + 写入顺序 + dep_index trace 集成 + RateLimitedProvider（F4 / F5 / F6 / F14）|
| T-3.6 | **T-3.6a + T-3.6b** | 拆 MVP + integrations 两子任务（F16）|
| T-3.7 | T-3.7 | 不动（一致性维护反向 propagate）|
| T-3.8 | **T-3.8a + T-3.8b** | 拆 version_recorder 独立 + batch_scheduler hook 合并入 T-3.5（F12）|
| T-3.9 | T-3.9 | 改先 helper 库交付，T-3.5 调用（F6）|
| T-3.10 | T-3.10 | 实测 + R3.X 不强制 + 场景集声明依赖图（F4 / F19）|
| T-3.11 | T-3.11 | 不动（开源剥离边界 v0.2）|
| T-3.12 | T-3.12 | 不动（验收报告）|

**v1.0 任务总数**：13 → **15 槽位**（T-3.6 拆 a/b；T-3.8 拆 a/b；其余 11 槽位编号保留）。

---

## 7. v1.0 整合工作流（Wave 4 step 2-3）

> 仿 v0.1 草稿的"分段落盘策略"（§0 文档说明）—— 避免单次 Write 大消息撞 ECONNRESET。

1. **Step 1 已完成**：本反应文档落盘（治理审计 + 拍板记录）
2. **Step 2 即将做**：v1.0 骨架 Write 进 `/docs/STAGE_3_TASKS.md`（§0 ~ §7 + §9 ~ §11；含 22 finding 修订对照表）
3. **Step 3 后续**：15 个 paste-ready prompts 逐个 Edit 追加（每次 1-2 个）

预估 v1.0 总体量 ~2200 行（v0.1 1773 行 + 修订增量 + 拆 2 任务）。落 `/docs/STAGE_3_TASKS.md`（main 路径，与阶段 2 `STAGE_2_TASKS.md` 同源）。

---

## 8. 与 cross-LLM 评审历史的对照

阶段 3 L2 critique 是 Forgewright 项目第 6 轮 cross-LLM 评审（前 5 轮含 Round 1-4 Claude × Gemini + Round 5 Claude × GPT-5.5 路线图层）。本轮特点：

- **直接矛盾占比异常高**（7/22 = 32%）：v0.1 草稿内部前后表述漂移是主因；阶段 4 L2 草稿应在起草时多做内部 self-consistency check
- **Claude 漏抓集中在工程层**（F2/F3/F5/F6/F12 = 5 条 🔴）：Claude L2 规划师未现场 grep `pyproject.toml` / `context_assembler.py` 等真实 repo 文件，纯依赖 v0.1 prompt 模板设计；阶段 4 起草时应先做 5-10 分钟 repo grep / structure check 再写 paste-ready prompt
- **GPT-5.5 增益形态稳定**：必读策略复盘（critique §8）显示精简版 8 预读 + 5 by-need 增补完全足够支撑架构层 critique；阶段 4 复用 `/docs/REVIEW_PROMPT_L2_STAGE_TASKS.md` 模板 + 精简策略

阶段 4 L2 草稿起草前应吸收：

- 起草前 grep repo 真实结构（pyproject.toml / 主要模块 import 关系 / 现有 schema 文件清单）
- v0.1 草稿内 self-consistency check（§1 完成标志 vs §8 prompts vs §7 概览三者口径必须一致）
- 不在 paste-ready prompt 内嵌 "尚未存在文件 / 包" 的硬性边界（如 v0.1 T-3.6 T-3.7 模块边界包含 `/tools/` 但 repo 没这个包）

---

## 9. 版本

本文件版本：v0.1
最后更新：2026-05-08
关联文档：
- [`2026-05-07_STAGE_3_TASKS_draft_v0.1.md`](2026-05-07_STAGE_3_TASKS_draft_v0.1.md)（评审对象）
- [`2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md`](2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md)（Codex critique）
- [`/docs/STAGE_3_TASKS.md`](../../STAGE_3_TASKS.md)（v1.0 整合产物；待落盘）
