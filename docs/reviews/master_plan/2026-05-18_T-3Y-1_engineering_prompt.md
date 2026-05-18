# T-3Y-1 工程会话 paste-ready prompt（节点级文本生成 mini prototype）

> **来源**：2026-05-18 T-3Y L2 综合规划师会话产出
> **用途**：L3 工程会话起手 prompt；含 /goal 拆解 + ABC 闭环衔接
> **任务定位**：T-3Y 模块的 mini prototype（最小可执行原型）；**不是产品级**；目的 = 实证文本生成机制层的可行性 + 给 [A] 率提供第一份数据点

---

## 给作者的使用说明（不属于 L3 提示词本体）

### paste 步骤

1. **起新 Conductor worktree 会话**（推荐分支名含 "t-3y-1"；如 `claude/t-3y-1-prototype-XXX`）
2. **会话起手第一条消息** = **本文档下方"# L3 提示词本体"段整段复制**
3. 会话会先 Read 关键文档 → 输出 goal 条件草案 + 工作计划 → 等你说"开" → 开始 /goal 子任务串行
4. **前置必做**：会话开始前确认（a）已开 auto mode；（b）trust dialog 已接受；（c）`git pull origin main` 确保 main 最新

### 预计工时

3-5 天 wall-clock（含 3 个 /goal 子任务 + A 阶段 PR + B/C 阶段 review/修复）

### 注意

T-3Y-1 是 **mini prototype**，scope 严守：
- 仅跑 1 个节点（node_3_info_offer）端到端
- 不集成到 T-3.5 批量调度器
- 不动 T-3.6a/b 审阅 UI
- 不动 T-3.4 playtest bots
- 不动 L1 文档

---

# L3 提示词本体（以下整段复制到新 worktree 会话起手）

---

## 1. 任务背景

你是 T-3Y-1 工程会话的执行者（L3 工程层）。任务 = **节点级文本生成 mini prototype**（最小可执行原型）—— 实证 T-3Y 设计层（[2026-05-15_T-3Y_design_progress.md](docs/reviews/master_plan/2026-05-15_T-3Y_design_progress.md)）在工程上的可行性。

### 项目背景（高度浓缩）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。第一款游戏 = "克苏鲁版极乐迪斯科 spiritual successor"。运行时无 LLM（确定性 JSON 播放器）；LLM 只在生产期介入批量生成对话内容。

### T-3Y-1 的位置

- T-3Y 设计层（6 阶段工作流 + Forward Planner + 23 决策点）已完成（[T-3Y 进展报告](docs/reviews/master_plan/2026-05-15_T-3Y_design_progress.md)）
- ADR-034 + ADR-016 v0.4（knowledge.* 命名空间）+ ADR-035 全部落地（main HEAD `72d81a7`；2026-05-18）
- 5 个 T-3Y 设计争议点作者拍板（详 ADR-034 调研报告 v0.2）
- **T-3Y-1 = 设计层 → 工程层的第一步实证**

---

## 2. 必读资料（**先 Read 全部，再开 goal**）

### L1 硬约束

- `/CLAUDE.md`（项目硬规则 10 条；特别第 2 条不跨模块边界 / 第 10 条不修 DECISIONS.md）
- `/docs/DECISIONS.md` ADR-016（含 v0.4 修订；knowledge.* 命名空间）+ ADR-034（D1-D11 schema 决策；特别 D4/D5/D6/D11）+ ADR-029（技能体系项目配置层）+ ADR-002 + ADR-004（运行时无 LLM + 生产期分离）

### T-3Y 设计层

- `/docs/reviews/master_plan/2026-05-15_T-3Y_design_progress.md`（必读全档；6 阶段 + 场景/节点字段草案 + Forward Planner 3 子模块 + 4 个设计问题 + 跨 ADR 协同）
- `/docs/reviews/master_plan/2026-05-15_ADR-034_schema_ir_research.md` v0.2（必读 §3 D1-D11 决策 + 5 争议点拍板）
- `/docs/reviews/master_plan/2026-05-14_A1_text_review_feedback_v0.1.md`（10 条 anti-pattern + 3 分类角色守则）

### 工程参考

- `/schema/*.schema.json`（当前 v0.3 + ADR-016 v0.4 修订后的字段；需检查 knowledge.* 命名空间落地状态）
- `/content/test_scene_v0/scene.json`（gold standard scene 范例）
- `/generator/` 现有目录结构（你将在 `/generator/node_text_gen/` 或类似位置新建模块）
- `/validator/` 现有结构（anti-pattern detector 可能加到这里）

### A1 dry-run 目标节点

- `/docs/reviews/master_plan/2026-05-13_A1_dry_run_crimson_letters.md` §3.7.3 `node_3_info_offer` 骨架（你将用此节点作 mini prototype 目标）

### 治理

- `/docs/governance.md` v0.4.1（ABC 闭环 / 跳 BC 破例清单 / commit 模板 / Codex review 自动化）
- `/docs/REVIEW_PROMPT_CODE_GPT.md` v0.2（B 阶段 review 模板；T-3Y-1 完成后由 Codex 跑）

---

## 3. 任务核心：mini prototype 工程交付物

实现"读节点骨架 → Forward Planner 算输入契约 → 调 LLM 生成 narration + options → 校验 anti-pattern → 评估 rubric → 落档"端到端流水线，跑通 1 个节点（`node_3_info_offer`）。

### 3.1 工程交付物清单

| # | 交付物 | 位置（建议；可自决定） | 备注 |
|---|---|---|---|
| 1 | Schema 字段扩展 | `/schema/dialogue_graph.schema.json` 等 | 落地 ADR-034 D4/D5/D6/D11：scene_metaparams / scene_reveals (ordered flag set) / scene_seeds (with coverage_strategy) / player_known_info (schema list) |
| 2 | knowledge.* validator | `/validator/state_path_validator.py` 加段 | 落地 ADR-016 v0.4 第 6 命名空间 + D11 player-monotonic 校验 |
| 3 | Forward Planner MVP | `/generator/forward_planner/` 新建 | 3 子模块 stub（intent 剧本意图层 / state_summary 状态摘要层 / reconcile 协调层）|
| 4 | 节点级 generator prompt 模板 | `/generator/prompts/node/` 新建 | 含 player_known_info / foreground_goal / background_seeds / 3 分类角色守则 / anti-pattern blacklist inject 段 |
| 5 | Generator render + 集成 | `/generator/node_text_gen/` 新建 | 调用 baimiao-rpg-node skill（外部 GitHub 仓库；可 fork 到本地 / inline 必要 prompt）|
| 6 | Anti-pattern detector | `/validator/anti_pattern_detector.py` 新建 | 落地 A1 反馈 v0.1 10 条；至少 AP-7/AP-8/AP-10 程序化检测；AP-1~6/AP-9 标 LLM-as-judge 待办 |
| 7 | 评估 rubric scorer | `/validator/node_rubric_scorer.py` 新建 | 最简 1-2 维度（如"信息密度" + "白描合规度"）；不要求全维度完美 |
| 8 | 端到端 dry-run 脚本 | `/generator/scripts/t_3y_1_dry_run.py` 或 CLI | 跑 1 次 node_3_info_offer → 输出文件 + 评估报告 |
| 9 | 单元测试 + 集成测试 | 各模块 `tests/` | pytest 通过；含 Forward Planner / detector / scorer / 端到端 happy path |
| 10 | 落档：实测报告 | `/docs/reviews/master_plan/2026-05-XX_T-3Y-1_dry_run_report.md` | 含生成的 narration + options + rubric 评分 + anti-pattern flag + 实测 token / 耗时 / 待人工 [A]/[R]/[S] 审 |

### 3.2 工程边界（不要碰）

- ❌ 不修 L1 文档（CLAUDE.md / DECISIONS.md / ROADMAP.md / SCHEMA_v0\*.md / STAGE_3_TASKS.md / DEBATE_NOTES.md / AESTHETIC_PREFERENCES.md / OPEN_SOURCE_CARVE_OUT_INDEX.md）
- ❌ 不集成到 T-3.5 批量调度器（mini prototype 不要扩 scope）
- ❌ 不动 T-3.6a/b 审阅 UI（虽然实测报告未来要在 UI 显示，但本会话不集成）
- ❌ 不动 T-3.4 playtest bots
- ❌ 不动 NPC 状态机 schema / engine（T-3X-1b 独立任务）
- ❌ 不在运行时引入 LLM 调用（ADR-002 严守；运行时 = JSON 播放器）
- ❌ 不实现完整 baimiao-rpg-node skill 逻辑（用 prompt 直接 inject 即可；skill 仓库的能力先 minimal 使用）

### 3.3 工程边界（可以碰）

- ✓ `/schema/`（扩展字段；与 ADR-034 D1-D11 同步）
- ✓ `/generator/`（新建 node_text_gen + forward_planner + prompts/node/ 子模块）
- ✓ `/validator/`（加 anti_pattern_detector + node_rubric_scorer + state_path_validator 扩段）
- ✓ `/content/`（如需新增测试数据）

---

## 4. /goal 命令使用指南

你将用 Claude Code v2.1.139+ 的 `/goal` 命令拆解推进。

### 4.1 关键背景（评估器是"瞎子"；critical）

`/goal` 评估器（默认 Haiku）**不调用工具、不读文件**。只能基于你 surface 到对话的内容判断。意味着：

- 每轮工作完成后**主动跑测试 / lint / dry-run** + **把完整输出 paste 到对话**
- 否则评估器看不到证据，goal 永远跑不完

### 4.2 前置检查

- **必须开启 auto mode**（自动模式）；不开 auto mode 用 /goal 无意义
- **已接受 trust dialog**
- `git pull origin main` 拉到最新（main HEAD `72d81a7` 或更新）

### 4.3 4 要素

每个 /goal 条件含：
- **可测量终态**（二值判定）
- **明确证明方式**（具体命令 + 输出 paste 要求）
- **不变量约束**（不能动什么）
- **边界子句**（N 轮 / X 分钟兜底）

---

## 5. /goal 拆解（3 个串行子 goal）

### 子 goal 1：Schema 字段 + Forward Planner MVP + 单元测试

```
/goal T-3Y-1 子 goal 1 完成判定：
  - 落地 schema 字段（按 ADR-034 D4/D5/D6/D11）：scene.schema.json 含 scene_metaparams (dict[str,JSON]) / scene_reveals (ordered flag set list) / scene_seeds (含 coverage_strategy enum) / player_known_info (schema list)
  - dialogue_graph.schema.json 或 node 子 schema 含 player_known_info（生成层 summary 在 prompt 里组装，不进 schema）
  - state_path_validator 含 knowledge.* 命名空间（ADR-016 v0.4 第 6 命名空间）+ player-monotonic 校验（flag.player_* + knowledge.* 只增不减）
  - /generator/forward_planner/ 含 3 个子模块（intent.py / state_summary.py / reconcile.py）+ 每模块至少 1 个 stub 函数 + 单元测试
  - 每轮工作结束后运行 `pytest schema/tests/ validator/tests/ generator/forward_planner/tests/ -v` 把完整输出 paste 到对话
  - 当 pytest 输出 'passed' 且 fail = 0 + 4 个交付物文件都存在（运行 `ls -la <每个文件路径>` paste 输出）时视为达成
  - 不要修改 L1 文档（CLAUDE.md / DECISIONS.md / ROADMAP.md 等）
  - 不要修改现有 generator/validator 已有模块（仅新增）
  - 或 15 轮后停止
```

### 子 goal 2：Generator prompt + Anti-pattern detector + Rubric scorer + 测试

```
/goal T-3Y-1 子 goal 2 完成判定：
  - /generator/prompts/node/ 含节点级 generator prompt 模板（含 player_known_info 注入段 / foreground_goal 段 / background_seeds 段 / 3 分类角色守则 inject / anti-pattern blacklist inject）
  - /generator/node_text_gen/ 含 render + LLM call 入口（mock provider 支持单元测试）
  - /validator/anti_pattern_detector.py 含 10 条 anti-pattern；至少 AP-7/AP-8/AP-10 程序化检测（其他可标 LLM-as-judge 待办）
  - /validator/node_rubric_scorer.py 含至少 1-2 个评分维度（如 information_density 信息密度 + baimiao_compliance 白描合规度）
  - 每轮工作结束后运行 `pytest generator/node_text_gen/tests/ generator/prompts/node/tests/ validator/tests/test_anti_pattern_detector.py validator/tests/test_node_rubric_scorer.py -v` 把完整输出 paste 到对话
  - 当 pytest 输出 'passed' 且 fail = 0 + 4 个交付物存在时视为达成
  - 不要修改 L1 文档
  - 不要集成到 T-3.5 批量调度器或 T-3.6a/b 审阅 UI
  - 或 15 轮后停止
```

### 子 goal 3：端到端 dry-run + 实测报告落档

```
/goal T-3Y-1 子 goal 3 完成判定：
  - /generator/scripts/t_3y_1_dry_run.py 或 CLI 入口可独立运行
  - 跑 1 次完整流水线：读 /content/test_scene_v0/scene.json + node_3_info_offer 骨架（或参考 A1 dry-run §3.7.3 露西对话节点）→ Forward Planner 算 player_known_info / foreground_goal / background_seeds → 调 LLM 生成 narration + options → anti-pattern detector flag → rubric scorer 评分 → 写输出 JSON + markdown 报告
  - 实测报告落档到 /docs/reviews/master_plan/2026-05-XX_T-3Y-1_dry_run_report.md（XX = 当天日期）
  - 报告含：生成的 narration + options 全文 / 评估元数据（rubric 评分 / anti-pattern flag）/ 实测 token 数 / wall-clock 耗时 / 待人工 [A]/[R]/[S] 段
  - 每轮工作结束后运行 dry-run 把输出 paste 到对话 + 运行 `ls -la /docs/reviews/master_plan/2026-05-*_T-3Y-1_dry_run_report.md` 验证落档
  - 当报告文件存在 + 含 generated narration（≥ 100 字）+ 至少 3 个 options + 评分 + anti-pattern flag 段时视为达成
  - 不要修改 L1 文档
  - 不要 production-deploy（仅 dry-run）
  - 或 10 轮后停止
```

### 子 goal 4（非 /goal；手动）：A 阶段提交 + 开 PR

3 个 /goal 全部达成后：
- 合并所有 commit（如不必要可保留多 commit）
- `git push -u origin <branch>`
- `gh pr create --title "feat(generator): T-3Y-1 A 阶段（节点级文本生成 mini prototype；ADR-034 D4-D11 + ADR-016 v0.4 落地）" --body "..."`
- 通知作者 A 阶段完成 → 等 Codex B 阶段 review

---

## 6. ABC 闭环衔接（治理 v0.4.1）

T-3Y-1 走完整 ABC 闭环（不在跳 BC 破例 5 类清单内）。

### A 阶段（你执行）

= 3 个 /goal 子任务 + 开 PR

### B 阶段（作者起 Codex 会话执行）

作者会用 `/docs/REVIEW_PROMPT_CODE_GPT.md` v0.2 跑 Codex review；Codex 自动 commit + push 报告到 main。你不参与 B 阶段。

### C 阶段（你回原会话执行）

- 作者会带 Codex review 报告（位于 `/docs/reviews/2026-05-XX_T-3Y-1_<topic>_review.md`）+ 让你修
- 你按报告改代码 + 追加 commit 到原 PR（不开新 PR；ABC C 阶段在原会话；feedback_abc_c_phase_same_session memory）
- 每个 finding 修复后跑 pytest 验证 + commit message 标注 finding 编号
- 完成后通知作者 → L2 验收 → merge

### L2 验收（作者主导；你协助）

L2 拿 ABC 全部产出判断；过关 → merge → 进 T-3.10 实测期或下一步任务

---

## 7. 关键纪律（critical；不要违反）

- **每轮主动跑测试 + paste 输出**（评估器是瞎子；§4.1 critical）
- **3 个子 goal 严格串行**；不要并行；每个完成后**先向用户简短报告**再开下一个
- **scope 不扩**：mini prototype；不集成到 T-3.5 / T-3.6 / T-3.4
- **严守 L1 边界**：不修 L1 文档；schema 修订**仅在 ADR-034 D1-D11 已授权范围内**
- **不在运行时引入 LLM 调用**（ADR-002）
- **遇到不确定的先问，不要猜**（CLAUDE.md 第 7 条）—— 特别是 schema 字段具体形态如果 ADR-034 D4/D5/D6/D11 描述不够清晰，**停下来报告作者**，不要自决
- **任一 /goal 边界触发但未达成** → 向作者报告现状 + 阻塞点 + 提议（拆细任务 / 调整条件 / 中止）+ 等作者决定

---

## 8. 完成判定（T-3Y-1 整体）

- 3 个 /goal 全部达成 + 子 goal 4 手动开 PR 完成 = A 阶段完成
- B 阶段（Codex review）+ C 阶段（finding 全修）+ L2 验收过关 + merge = T-3Y-1 工程完成
- T-3Y-1 工程完成 + 作者人工审阅 dry-run 报告（[A]/[R]/[S]）= T-3Y-1 实证完成
- T-3Y-1 实证完成 → 进 T-3.10 实测期 batch（Wave 7）或 T-3Y v0.2 内部 ST 子任务

---

## 9. 起手动作

1. **Read 必读资料**（§2 全部）
2. **Read /docs/reviews/master_plan/2026-05-18_vision_and_roadmap.md**（理解项目整体定位）
3. **检查 schema 状态**：运行 `ls /schema/ && grep -l 'knowledge\.' /schema/*.schema.json` 看 ADR-016 v0.4 + ADR-034 schema 字段在哪些文件已落地、哪些还要你做
4. **向作者输出**：
   - 调研发现（schema 状态 / 已有模块 / 缺什么）
   - 3 个 /goal 条件草案（含 4 要素；放代码块）
   - 工作计划（每轮做什么）
   - 预算预估（轮数 / 时间 / token）
   - 风险点（哪里可能失控）
5. **等作者口头同意**（"开" / "调整 xxx"）
6. **立即执行子 goal 1**

---

**任务完成后向作者汇报**：

- 3 个 /goal 状态（达成 / 边界触发 / 中止）
- A 阶段 PR 链接
- 实测报告链接（落档路径）
- token 实测消耗
- wall-clock 总耗时
- 待人工审稿点（[A]/[R]/[S] 需作者标）
- 下一步建议（B 阶段 / 修正 / 中止）

祝顺利。任何 architectural（架构层）疑问，**停下来问作者**，不要自决。
