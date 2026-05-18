# T-3X L2 校准 — 审美层决策 v0.2 L3 fixation PR paste-ready prompts

> 2026-05-09 T-3X L2 校准产物。基于 [审美层决策 v0.2](2026-05-09_aesthetic_layer_decision_v0.1.md)（同日 v0.1 → v0.2）§6 修订清单 5 项，起草 L3 fixation PR paste-ready prompts，供作者复制粘贴启动 L3 执行会话。
>
> **本备忘不修改 L1 文档**（DECISIONS / ROADMAP / STAGE_3_TASKS / HANDOFF / SCHEMA_v0*.md / CLAUDE.md 等）；本备忘也**不复述** §7 T-3X-0 指引模板（已归决策档 v0.2 §7，L1 直接出，T-3X 不重复）。
>
> **任务性质**：T-3X 是 L2 校准（与 T-3 主线并列；不是 T-3 主线子任务）。**T-3X 校准本身跳过 cross-LLM critique + 跳过 ABC**（作者明示授权），但 T-3X 起草的下游 L3 fixation PR prompt **仍含 ABC 闭环要求**——是否跳 BC 由作者后续按 PR 个例拍板。

**日期**：2026-05-09 · **版本**：v0.1 · **产出方**：T-3X L2 校准会话（claude/jovial-elion-c8d60c worktree）

---

## 1. 背景

阶段 3 工程层 2026-05-08~09 完成（Wave 0~6；12 工程任务 merged；main HEAD `8587025`）。T-3.10 实测期启动前作者反思发现三个根本 gap → L1 规划讨论产出 [审美层决策 v0.2](2026-05-09_aesthetic_layer_decision_v0.1.md)（同日 v0.1 → v0.2）→ 作者拍板选项 5（CC 经典剧本反向归纳抽象层 + 同步建立锚点）。决策档 v0.2 §6 列出待落地的 L1 文档修订清单 5 项；T-3X L2 校准（本会话）起草 L3 fixation PR paste-ready prompts；下游 L3 执行会话按本备忘的 prompt 落地修订。

---

## 2. 拆法说明（3 个 PR；推荐串行；理由）

### 2.1 推荐拆法

| PR | 修订 L1 文档 | 决策档 v0.2 锚点 | ABC 推荐 |
|---|---|---|---|
| **PR-A** | `/docs/DECISIONS.md`（新立 ADR-030 + 同步立 ADR-020 v0.2） | §6.4 + §6.5 | **默认完整 ABC** |
| **PR-B** | `/docs/ROADMAP.md` §阶段 3 + `/docs/HANDOFF_STAGE_2_TO_3.md` §审美层 review 激活 | §6.1 + §6.3 | **默认完整 ABC**（作者可破例跳 BC，参 PR #50 模式） |
| **PR-C** | `/docs/STAGE_3_TASKS.md` v1.0 §1 + §3.1 + §7 + `/docs/prompts/stage_3/T-3.10.md` | §6.2 | **默认完整 ABC** |

### 2.2 为什么拆 3 个 PR（不是 1 个或 2 个）

**对比 1 个大 PR（如 PR #50 模式）**：
- ✓ PR #50 同时改 ROADMAP + DECISIONS 两份 L1（+63 行）合并为 1 个 PR——简洁
- ✗ 本次 §6 修订量更大：5 项修订涉及 4 份 L1 文档 + 1 份 prompt 文件；如全合 1 个 PR，diff 量预估 ≥ 200 行（4 份文档 + 1 份 prompt 文件），单 review 会话审阅负担过高
- ✗ ADR-030 是**新立 ADR**（高风险动作），与 ROADMAP / HANDOFF / STAGE_3_TASKS 措辞修订（中等风险）混在一起，B 阶段 review 焦点会被稀释

**对比 2 个 PR**：
- 候选 A：PR-AB（DECISIONS + ROADMAP + HANDOFF）+ PR-C（STAGE_3_TASKS）—— PR-AB 仍含两类风险（新立 ADR + 路径校准）混合
- 候选 B：PR-A（DECISIONS）+ PR-BC（ROADMAP + HANDOFF + STAGE_3_TASKS）—— PR-BC 三份文档措辞需保持一致，审阅复杂度高

**3 个 PR 的优势**：
- 每个 PR 风险类型同源（PR-A 立新 ADR / PR-B 路径校准 + 措辞统一 / PR-C 任务清单结构修订）
- 每个 PR diff 量可控（约 50-80 行）
- B 阶段 review 焦点集中，单个 review 报告质量更高
- 与 PR #50 模式不冲突——PR #50 实际只改两份文档（ROADMAP + DECISIONS），本次量级是 PR #50 的 2x，拆 3 个匹配 PR #50 同款单文档复杂度

### 2.3 依赖关系 + 推荐执行顺序

**串行推荐顺序**：

```
PR-A（DECISIONS）→ merge → PR-C（STAGE_3_TASKS）→ merge → PR-B（ROADMAP + HANDOFF）
```

**为什么这个顺序**：

- **PR-A 必须先**：STAGE_3_TASKS §3.1 ADR-022 决策核心修订段需引用 ADR-030（新立）+ ADR-020 v0.2（同步立）；ADR 未落地，引用链断裂
- **PR-C 在 PR-A 之后**：STAGE_3_TASKS §7 新增 T-3X-0 + T-3X-1 任务；§1 完成标志新增前置条件；§3.1 引用 ADR-030
- **PR-B 可放最后**（或与 PR-A 并行）：ROADMAP §阶段 3 新增 scope 段 + 时长加 1-3 周 + 完成标志强化项；与 STAGE_3_TASKS 内容互不直接依赖（ROADMAP 只引用决策档 + STAGE_3_TASKS 编号 T-3X-0/X1，编号本身不需要 STAGE_3_TASKS 已 merge）

**并行可选**：PR-A 与 PR-B 可并行起步（独立 worktree），等两者都 merge 后再起 PR-C。但作者审阅带宽是真瓶颈，串行更稳。

---

## 3. PR-A paste-ready prompt — DECISIONS 修订

> 修订位置：`/docs/DECISIONS.md` 新增 ADR-030 + 修订 ADR-020 v0.2。决策档 v0.2 锚点：§6.4 + §6.5。

```text
你是 Forgewright 项目 L1 fixation 执行会话——审美层决策 v0.2 §6.4 + §6.5 落地 PR-A。

# 你的任务（一句话）

在 /docs/DECISIONS.md 内**新立 ADR-030**（AestheticPreference schema；字段集**留空预留**）+ **修订 ADR-020 v0.2**（X4 闭环；阶段 2/3/4 三阶段口径）。不动其他 L1 文档。

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。阶段 3 工程层已完成；T-3.10 实测期前作者反思三 gap → 审美层决策 v0.2 主推荐选项 5（CC 经典剧本反向归纳抽象层）→ §6 修订清单 5 项；本 PR 落地 §6.4 + §6.5 两项。

# 必读（按顺序）

1. /CLAUDE.md — 项目硬规则 10 条（特别规则 2 不跨模块 / 规则 9-10 不修 CLAUDE / DECISIONS 除非作者授权）
2. /docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md（v0.2；**主输入**，特别 §6.4 + §6.5 + §10 修订记录）
3. /docs/DECISIONS.md（特别 ADR-020 现状段 + ADR-010 v0.2 修订段作为格式参考 + 变更历史段；**行号现读现取**——main 现含 ADR-028/029，旧行号已漂移）
4. /docs/governance.md v0.4.1（特别 §10 ABC 流程）
5. /docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md v0.2.2（**T-3X L2 校准产出本备忘**；本 prompt 即来自 §3；含产品线 ADR-028/029 联动校准说明）
6. 参考 PR #50（L1 fixation of strategy calibration v0.1）：`gh pr view 50 --json title,body,commits,files` 看模式

# 模块边界（硬性）

允许修改：
- /docs/DECISIONS.md（新增 ADR-030 段 + 修订 ADR-020 v0.2 段 + §变更历史追加 2026-05-12 授权记录）

**严禁修改**：
- CLAUDE.md / DEBATE_NOTES.md
- ROADMAP.md（PR-B 负责）
- STAGE_3_TASKS.md（PR-C 负责）
- HANDOFF_STAGE_2_TO_3.md（PR-B 负责）
- SCHEMA_v0*.md / 任何 /schema/* 文件
- /docs/prompts/stage_3/* （PR-C 负责）
- 任何代码 / 测试 / fixture

# 待落地点

## 落地点 1：新立 ADR-030（在 ADR-029 后追加；DECISIONS.md 现状最大 ADR-029）

**段位**：在 ADR-029（main 现状最大 ADR；2026-05-11 已 push）末段 `---` 分隔符之后、`## 变更历史` 段之前追加 `---` + ADR-030 段。**行号由执行会话现读现取**（main HEAD 行号随 ADR-028/029 已 push 而漂移；不写死行号）。

**关键背景**：main 现已落地 ADR-028（引擎与宿主分离原则；2026-05-10）+ ADR-029（技能体系作为项目配置层；2026-05-11）—— 来源产品线对话讨论 + 作者带回工程线 push。T-3X L2 校准期（2026-05-12）确认此两条 ADR 在 main 上有效；**本 PR-A 立新 ADR 顺延至 ADR-030**（编号 028/029 已被产品线 ADR 占用）。

**ADR-030 内容草拟**（**字段集留空预留**——明示由 T-3X-1 L3 基于 T-3X-0 实证归纳）：

```markdown
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
```

## 落地点 2：修订 ADR-020 v0.2（X4 闭环；阶段 2/3/4 三阶段口径）

**段位**：在 ADR-020 "**后果**" 末段后追加 `### v0.2（2026-05-09 审美层决策 v0.2 §6.5 吸收）` 子段。格式参考 ADR-010 v0.2 段。**行号由执行会话现读现取**（main HEAD 已漂移）。

**ADR-020 v0.2 修订段内容草拟**：

```markdown
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
```

## 落地点 3：§变更历史追加 2026-05-12 授权记录

**段位**：DECISIONS.md `## 变更历史` 段现有 2026-05-11（ADR-029）授权记录后追加一行。**行号由执行会话现读现取**（main HEAD 已漂移）。

**条目内容草拟**：

```markdown
- 2026-05-12：作者明确授权新增 ADR-030（AestheticPreference schema；字段集留空预留，待 T-3X-1 实证归纳）+ 修订 ADR-020 v0.2（X4 闭环；阶段 2/3/4 三阶段口径），属 CLAUDE.md 规则 10 的明示例外。审美层决策于 2026-05-09 签字（v0.2）；ADR-028 + ADR-029 同期由产品线讨论起草并于 2026-05-10/11 push 到 main，占用编号 028/029；本 ADR 顺延为 ADR-030。整合自 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.4 + §6.5。T-3X L2 校准会话起草 L3 fixation PR paste-ready prompt（[/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md](reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md) v0.2 修订包含产品线 ADR-028/029 联动校准）→ L1 fixation 执行会话（本 PR）落地。
```

# ABC 闭环要求

**默认走完整 ABC**（不跳 BC）：

- **A 阶段（本会话）**：write + commit + push + 开 PR；commit 后**等作者明示** B 阶段是否起 Codex review
- **B 阶段**：作者另起 Codex 会话（GPT-5.5）；review prompt 复用 [/docs/REVIEW_PROMPT_CODE_GPT.md](../../REVIEW_PROMPT_CODE_GPT.md) v0.2；review 报告 push 到 main 独立 commit（治理 v0.3 §10 第 7 条 + v0.4.1 patch §12 gap #2 闭合）
- **C 阶段**：吃 B 阶段 review 报告 → 追加 commit 到原 PR（memory feedback_abc_c_phase_same_session：C 阶段可在 A 阶段原会话进行；治理文档措辞作者实操弃用）

**跳 BC 破例可能性**（参 PR #50 模式注脚）：作者可拍板"B 阶段自行决定"（如 ADR-030 + ADR-020 v0.2 表述与决策档 v0.2 § 直接 1:1 复制，B 阶段 review 边际价值低）；但**默认起草 ABC**，破例由作者后续明示。

# A 阶段执行步骤

1. 读必读清单（6 项）
2. 按"落地点 1/2/3"分别 Edit `/docs/DECISIONS.md`
3. 跑本地 `/review` skill（如可用）+ 检查 markdown 渲染（特别 ADR-030 嵌套代码块）
4. 提交：

   ```bash
   git add /docs/DECISIONS.md
   git commit -m "$(cat <<'EOF'
   docs: L1 fixation of aesthetic layer decision v0.2 — PR-A (ADR-030 + ADR-020 v0.2)

   落实审美层决策 v0.2 §6.4 + §6.5：

   - 新立 ADR-030（AestheticPreference schema；字段集留空预留，待 T-3X-1 实证归纳）
   - 修订 ADR-020 v0.2（X4 闭环；阶段 2/3/4 三阶段口径）
   - §变更历史追加 2026-05-12 授权记录

   追溯：/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md (v0.2)
   T-3X L2 校准产出：/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md v0.2.2

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   git push -u origin <current-branch>
   ```

5. 开 PR（base=main，head=当前 worktree 分支）；PR title + body 参 PR #50 模式：

   - title：`docs: L1 fixation of aesthetic layer decision v0.2 — PR-A (ADR-030 + ADR-020 v0.2)`
   - body 段：Summary / 改动（按落地点 1/2/3 分列）/ 不冲突（列出未动的 L1 文档：ROADMAP / STAGE_3_TASKS / HANDOFF / SCHEMA_v0* / CLAUDE.md 由 PR-B / PR-C 负责）/ ABC 流程（A ✅ + B 待作者拍板 + C 视 B 反馈）/ 追溯（链接决策档 v0.2 + T-3X L2 备忘 v0.2.2）/ Test plan（核对清单）

# 完成判定

- DECISIONS.md 落地 3 个修订点（ADR-030 + ADR-020 v0.2 + §变更历史）
- PR open + commit + push 完成
- PR body 含 ABC 流程段（明示 A 已完成 + B/C 待作者拍板）
- 回报作者：PR URL + 是否发现遗漏 / 需作者拍板的细节
```

---

## 4. PR-B paste-ready prompt — ROADMAP + HANDOFF 校准

> 修订位置：`/docs/ROADMAP.md` §阶段 3 + `/docs/HANDOFF_STAGE_2_TO_3.md` §审美层 review 激活。决策档 v0.2 锚点：§6.1 + §6.3。

```text
你是 Forgewright 项目 L1 fixation 执行会话——审美层决策 v0.2 §6.1 + §6.3 落地 PR-B。

# 你的任务（一句话）

在 /docs/ROADMAP.md §阶段 3 **新增 scope 声明段 + 完成标志强化项保留 [A] gate + 新增 T-3X-0/X1 前置任务 + 时长加 1-3 周**；在 /docs/HANDOFF_STAGE_2_TO_3.md §审美层 review 激活段**校准措辞为"T-3X-0+X1 落地后激活"**。不动其他 L1 文档。

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。阶段 3 工程层已完成；T-3.10 实测期前作者反思三 gap → 审美层决策 v0.2 主推荐选项 5 → §6 修订清单 5 项；本 PR 落地 §6.1 + §6.3 两项（路径校准 + 措辞统一）。

# 必读（按顺序）

1. /CLAUDE.md — 项目硬规则 10 条（特别规则 2 不跨模块 / 规则 9-10 不修 CLAUDE / DECISIONS 除非作者授权）
2. /docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md（v0.2；**主输入**，特别 §6.1 + §6.3 + §5 关键决策点 3-7）
3. /docs/ROADMAP.md（特别 §阶段 3 L185-L218 + 阶段 4 切换协议 L241-L255 + 更新记录 L260-L268）
4. /docs/HANDOFF_STAGE_2_TO_3.md（特别 §阶段 3 审美层 review 激活 L75-L83 + 跨阶段提醒 X4 L205-L207）
5. /docs/governance.md v0.4.1（特别 §10 ABC 流程）
6. 参考 PR #50（L1 fixation of strategy calibration v0.1）：`gh pr view 50 --json title,body,commits,files` 看模式

# 模块边界（硬性）

允许修改：
- /docs/ROADMAP.md（§阶段 3 段 + §更新记录追加 2026-05-09 条目）
- /docs/HANDOFF_STAGE_2_TO_3.md（§阶段 3 审美层 review 激活段 + §版本时间戳更新）

**严禁修改**：
- CLAUDE.md / DEBATE_NOTES.md
- DECISIONS.md（PR-A 负责）
- STAGE_3_TASKS.md（PR-C 负责）
- /docs/prompts/stage_3/* （PR-C 负责）
- SCHEMA_v0*.md / 任何 /schema/* 文件
- 任何代码 / 测试 / fixture

# 待落地点

## 落地点 1：ROADMAP §阶段 3 新增 scope 声明段（决策档 v0.2 §6.1.a）

**段位**：ROADMAP.md L186（"## 阶段 3：完整内容生产流水线 + 审阅工具"）后、L188（"### 目标"）前，**新增 ### 子段**。

**段落内容草拟**（基于决策档 v0.2 §6.1.a；**技能系统措辞经 T-3X L2 校准与产品线 ADR-029 联动校准**——决策档 v0.2 §6.1.a 原写"技能系统"，T-3X L2 校准期 2026-05-12 联动产品线 ADR-029（技能体系作为项目配置层；2026-05-11 已 push）细化为更准措辞，避免与 ADR-029 引擎不预设技能体系的硬约束产生张力）：

```markdown
### 工具第一版 scope（2026-05-09 作者拍板；2026-05-12 与 ADR-029 联动校准）

不做：
- 战斗系统（schema 不强制有；不阻止未来 plugin 扩展）
- 极乐迪斯科风格"思维内阁"（独特机制）
- 极乐迪斯科风格"内心独白"段落

主做：
- 对话多选项推进
- 调查 + 物品互动
- NPC 互动
- **技能体系**（具体技能数 / 列表 / 性格化或功能化 / 骰子规则 NdM + modifier vs DC **由项目配置层定义**；引擎只规范 `active_check`（选项级主动检定）+ `passive_injection`（节点级被动注入）基础机制；详 ADR-029）
- 检定（扔骰子 / SAN / 技能判定；具体骰子规则同上由项目配置层定义）

风格主导：CoC（结构化调查驱动）；补充：极乐迪斯科对话技法 + 技能驱动 + 世界观信息密度

追溯：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §5 + §6.1；ADR-029（技能体系作为项目配置层；2026-05-11 已 push）；T-3X L2 校准 2026-05-12 联动修订（[/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md](reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md) v0.2）
```

## 落地点 2：ROADMAP §阶段 3 完成标志强化项段补充 + 时长加 1-3 周（决策档 v0.2 §6.1.b）

**段位**：ROADMAP.md §阶段 3 现有 "### 完成标志强化项（Round 5 综合后）" 段末（L218 后）追加新段；以及阶段概览表（L18 阶段 3 行）时长更新。

**完成标志强化项段后追加新段**（**保留** [A] gate，**新增** T-3X-0/X1 前置）：

```markdown
### 审美层 review 激活前置（2026-05-09 审美层决策 v0.2 §6.1.b 吸收）

**完成标志强化项保留**：[A]ccept rate ≥ 60% pilot + Wilson 95% CI 报告（STAGE_3_TASKS v1.0 §1 原阈值不修订；决策档 v0.2 §4 选项 5 保留）

**新增 T-3.10 前置条件**：
- **T-3X-0 作者审美锚点工程**（非工程任务；作者本人完成；不走 ABC）—— 读 3 部经典（Deadlight + Crimson Letters + 极乐迪斯科原版）+ 填阅读对照表 + 产出 `/docs/AESTHETIC_PREFERENCES.md` v0.1；时长 1-3 周（作者节奏决定）；指引详 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §7
- **T-3X-1 ADR-030 立项 + schema 落地 + prompt hook**（工程任务；[B-author-gate]；走 ABC）—— 基于 T-3X-0 产出实证归纳字段集；schema 落 `/schema/aesthetic_preference.schema.json` 首版 `0.4.0`

**时长加 1-3 周**：阶段 3 估时 4-6 周（不变）；T-3X-0 非工程任务延期 1-3 周（作者节奏决定；不计入工程估时；阶段概览表阶段 3 行同步更新为 "5-9 周（含 T-3X-0 1-3 周作者锚点工程）"）

追溯：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.1 + §4 选项 5
```

**阶段概览表更新**（L18 阶段 3 行）：

- 当前：`| 3 | 完整内容生产流水线 + 审阅工具 | 4–6 周 | 是 |`
- 修订后：`| 3 | 完整内容生产流水线 + 审阅工具 | 5–9 周（含 T-3X-0 1-3 周作者锚点工程） | 是 |`

## 落地点 3：HANDOFF §审美层 review 激活段措辞校准（决策档 v0.2 §6.3）

**段位**：HANDOFF_STAGE_2_TO_3.md L75（"## 阶段 3 审美层 review 激活（重要）"）整段。

**当前文字**（L77）："**审美层评估激活在阶段 3** —— 作者那时有具体剧本上下文 + 角色弧线锚点。"

**校准为**（决策档 v0.2 §6.3 1:1 引用）：

```markdown
## 阶段 3 审美层 review 激活（重要；2026-05-09 审美层决策 v0.2 §6.3 校准）

**feedback memory 真实建议被正面吸收 + 阶段 3 内压缩锚点工程时长**：阶段 2 期间跳过 `scene_review_cli` 作者 [A]/[R]/[S] 流程；用 `gross_pass_rate ≥ 70%` 作完成判定 logic-layer proxy（ADR-020 v0.2 阶段 2 期间口径，参 PR-A）；**审美层 review 激活路径**：T-3X-0（作者读 3 部经典 + 反向归纳抽象层 → AESTHETIC_PREFERENCES.md v0.1）+ T-3X-1（ADR-030 立项 + schema + prompt hook）落地后激活 T-3.10 [A]ccept rate gate。

**与 feedback memory 真实建议关系**：feedback memory 推荐"推迟阶段 4"被 v0.2 选项 5 部分前置——经典剧本反向归纳压缩了"作者锚点工程"时长（从读 30 本经典 1-3 个月压缩到读 3 部经典 1-3 周），使阶段 3 内激活可行；阶段 4 仍可基于 50-100 场景实测迭代 AESTHETIC_PREFERENCES.md v0.2+ 与 ADR-030 v0.2+（ADR-020 v0.2 阶段 4 期间完整 [A]/[R]/[S] 流程，参 PR-A）。

**对阶段 3 规划师的影响**：
- 阶段 3 起手必读 `~/.claude/projects/-Users-outsider-Desktop-Forgewright/memory/feedback_acceptance_review_deferred_to_stage_4.md` + 本节校准
- `scene_review_cli` 工具链已落地（T-2.8），阶段 3 复活使用即可（无需重建）
- AI 判官 advisory（每场景 21 维节点 + 10 维场景）已落地（T-2.9）但 dimensions 全空 bug（R2-5）需先修
- 阶段 3 完成标志 U-CL-1 真实接受率（含审美层）阈值由 STAGE_3_TASKS v1.0 §1 拍板（[A] ≥ 60% pilot + Wilson 95% CI；不修订）

**追溯**：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.3
```

## 落地点 4：HANDOFF §跨阶段提醒 X4 行同步更新（与 PR-A 联动）

**段位**：HANDOFF_STAGE_2_TO_3.md L205（"| **X4** | ADR-020 v0.2 修订..."）行。

**当前文字**（L205）：

```
| **X4** | ADR-020 v0.2 修订（审美层推迟到阶段 4 + gross_pass_rate 作 logic-layer proxy） | 阶段 3 起手期 L1 元任务；作者另起会话立 |
```

**校准为**（X4 已通过审美层决策 v0.2 §6.5 同步立项落地；状态从"待处理"→"已闭合"）：

```
| **X4** | ADR-020 v0.2 修订（阶段 2/3/4 三阶段口径）| ✅ 2026-05-09 已闭合（PR-A 落地，参 ADR-020 v0.2 + /docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md v0.2 §6.5） |
```

## 落地点 5：ROADMAP + HANDOFF 版本时间戳更新

- ROADMAP.md L268（更新记录）追加 2026-05-09 条目（审美层决策 v0.2 吸收）
- HANDOFF_STAGE_2_TO_3.md L213（版本）：将 "v0.1（阶段 2 → 3 交接草稿）/ 最后更新：2026-05-07" 更新为 "v0.2（2026-05-09 审美层决策 v0.2 §6.3 校准）/ 最后更新：2026-05-09"；并在文件顶部 L8 时间戳同步更新

**ROADMAP 更新记录条目内容草拟**：

```markdown
- **2026-05-09**：阶段 3 §scope 声明段新增（不做战斗 / 思维内阁 / 内心独白；主做对话 + 调查 + 物品 + NPC + 技能 + 检定；CoC 主导）+ 审美层 review 激活前置子段新增（保留 [A] ≥ 60% pilot + Wilson CI；新增 T-3X-0/X1 作 T-3.10 前置）+ 阶段概览表阶段 3 时长加 1-3 周（5-9 周；含 T-3X-0 作者锚点工程）。来源：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.1。联动 PR-A（ADR-030 + ADR-020 v0.2）+ PR-C（STAGE_3_TASKS §1 + §3.1 + §7）。
```

# ABC 闭环要求

**默认走完整 ABC**（不跳 BC）：

- **A 阶段（本会话）**：write + commit + push + 开 PR；commit 后**等作者明示** B 阶段是否起 Codex review
- **B 阶段**：作者另起 Codex 会话（GPT-5.5）；review prompt 复用 [/docs/REVIEW_PROMPT_CODE_GPT.md](../../REVIEW_PROMPT_CODE_GPT.md) v0.2；review 报告 push 到 main 独立 commit（治理 v0.3 §10 第 7 条 + v0.4.1 patch §12 gap #2 闭合）
- **C 阶段**：吃 B 阶段 review 报告 → 追加 commit 到原 PR

**跳 BC 破例可能性**（参 PR #50 模式注脚）：本 PR 为 L1 文档措辞校准（非新立 ADR / 非任务清单结构修订），可能为低风险候选；作者可拍板"B 阶段自行决定起 / 不起"。但**默认起草 ABC**。

# A 阶段执行步骤

1. 读必读清单（6 项）
2. 按"落地点 1-5"分别 Edit `/docs/ROADMAP.md` + `/docs/HANDOFF_STAGE_2_TO_3.md`
3. 跑本地 `/review` skill（如可用）+ 检查 markdown 渲染
4. 提交：

   ```bash
   git add /docs/ROADMAP.md /docs/HANDOFF_STAGE_2_TO_3.md
   git commit -m "$(cat <<'EOF'
   docs: L1 fixation of aesthetic layer decision v0.2 — PR-B (ROADMAP §阶段 3 + HANDOFF)

   落实审美层决策 v0.2 §6.1 + §6.3：

   - ROADMAP §阶段 3 新增 scope 声明段（不做战斗 / 思维内阁 / 内心独白；主做对话 + 调查 + 物品 + NPC + 技能 + 检定；CoC 主导）
   - ROADMAP §阶段 3 完成标志强化项保留 [A] gate + 新增 T-3X-0/X1 前置 + 时长加 1-3 周
   - ROADMAP §阶段概览表阶段 3 行更新为 5-9 周
   - HANDOFF §审美层 review 激活段措辞校准为"T-3X-0+X1 落地后激活"
   - HANDOFF §跨阶段提醒 X4 行同步更新为已闭合状态（与 PR-A ADR-020 v0.2 联动）

   追溯：/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md (v0.2)
   T-3X L2 校准产出：/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   git push -u origin <current-branch>
   ```

5. 开 PR；title + body 参 PR #50 模式：
   - title：`docs: L1 fixation of aesthetic layer decision v0.2 — PR-B (ROADMAP + HANDOFF)`
   - body 段：Summary / 改动（按落地点 1-5 分列）/ 不冲突（DECISIONS 由 PR-A 落地 / STAGE_3_TASKS 由 PR-C 落地）/ ABC 流程 / 追溯 / Test plan

# 完成判定

- ROADMAP §阶段 3 落地 3 个修订点（scope 段 + 审美层激活前置子段 + 阶段概览表时长）+ §更新记录
- HANDOFF 落地 2 个修订点（§审美层 review 激活校准 + §X4 行同步更新）+ §版本时间戳
- PR open + commit + push 完成
- PR body 含 ABC 流程段
- 回报作者：PR URL + 是否发现遗漏 / 需作者拍板的细节
```

---

## 5. PR-C paste-ready prompt — STAGE_3_TASKS v1.0 修订

> 修订位置：`/docs/STAGE_3_TASKS.md` §1 + §3.1 + §7 + `/docs/prompts/stage_3/T-3.10.md`。决策档 v0.2 锚点：§6.2。

```text
你是 Forgewright 项目 L1 fixation 执行会话——审美层决策 v0.2 §6.2 落地 PR-C。

# 你的任务（一句话）

在 /docs/STAGE_3_TASKS.md v1.0 **§1 完成标志保留 [A] gate + 新增 T-3X-0/X1 前置 + §3.1 ADR-022 决策核心新增 2026-05-09 修订段 + §7 任务清单新增 T-3X-0/X1 槽位 + 修订 T-3.10 paste-ready prompt 文件**。不动其他 L1 文档。

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。阶段 3 工程层已完成；T-3.10 实测期前作者反思三 gap → 审美层决策 v0.2 主推荐选项 5 → §6 修订清单 5 项；本 PR 落地 §6.2（最大修订量；任务清单结构修订）。

# 前置依赖

- **PR-A（ADR-030 + ADR-020 v0.2）应已 merge**——本 PR §3.1 修订段引用 ADR-030；如 PR-A 未 merge，本 PR 引用链断裂
- **PR-B（ROADMAP + HANDOFF）可并行 / 可在 PR-C 之后**——无直接引用依赖

如 PR-A 未 merge：暂停 PR-C 启动；先合入 PR-A。

# 必读（按顺序）

1. /CLAUDE.md — 项目硬规则 10 条（特别规则 2 不跨模块 / 规则 9-10 不修 CLAUDE / DECISIONS 除非作者授权）
2. /docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md（v0.2；**主输入**，特别 §6.2 全文 + §7 T-3X-0 指引模板 + §5 关键决策点 1-9）
3. /docs/STAGE_3_TASKS.md（v1.0；特别 §1 完成标志阈值表 L66-L92 + §3.1 ADR-022 决策核心 L199-L213 + §7 任务清单 L360-L381 + §6 wave 图 L306-L356）
4. /docs/prompts/stage_3/T-3.10.md（现状全文；待修订）
5. /docs/DECISIONS.md（PR-A 已落地的 ADR-030 + ADR-020 v0.2；引用源）
6. /docs/governance.md v0.4.1（特别 §10 ABC 流程 + §11 v0.4 prompt 文件化）
7. 参考 PR #50（L1 fixation of strategy calibration v0.1）：`gh pr view 50 --json title,body,commits,files` 看模式

# 模块边界（硬性）

允许修改：
- /docs/STAGE_3_TASKS.md（§1 完成标志表 + §3.1 ADR-022 决策核心 + §7 任务清单 + §10 修订记录追加 2026-05-09 v1.0.1 条目 + §11 版本时间戳）
- /docs/prompts/stage_3/T-3.10.md（修订前置 + 审美层 [A] gate 表述 + AESTHETIC_PREFERENCES.md 引用）

**严禁修改**：
- CLAUDE.md / DEBATE_NOTES.md
- DECISIONS.md（PR-A 负责）
- ROADMAP.md（PR-B 负责）
- HANDOFF_STAGE_2_TO_3.md（PR-B 负责）
- SCHEMA_v0*.md / 任何 /schema/* 文件
- /docs/prompts/stage_3/T-3.0.md ~ T-3.12.md（除 T-3.10.md 外）
- 任何代码 / 测试 / fixture
- /docs/AESTHETIC_PREFERENCES.md（不存在；T-3X-0 作者本人产出，本 PR **不**创建）

# 待落地点

## 落地点 1：§1 完成标志表保留 [A] gate + 新增 T-3X-0/X1 前置条件（决策档 v0.2 §6.2 §1 改动）

**段位**：STAGE_3_TASKS.md L72-L84（"完成标志（v1.0 修订；F7 / F8 / F10 联动）"表格段）。

**改动**：

- **保留**当前"审美层 [A]ccept rate（pilot）"行（L82）阈值"≥ 60%（N=10 场景；附 Wilson 95% CI 报告）"——**不修订** v1.0 §1 原阈值
- **新增**一行 T-3X-0/X1 前置条件：

```markdown
| **审美层 review 激活前置（2026-05-09 v0.2 新增）** | T-3X-0 AESTHETIC_PREFERENCES.md v0.1 已 commit + T-3X-1 ADR-030 立项 + schema + prompt hook 已 merge | 决策档 v0.2 §6.2 |
```

**位置**：放在"审美层 [A]ccept rate（pilot）"行（L82）的**上方一行**，强调"前置条件"概念。

## 落地点 2：§3.1 ADR-022 决策核心新增 2026-05-09 修订段（决策档 v0.2 §6.2 §3.1 改动）

**段位**：STAGE_3_TASKS.md L214（"**后果**：T-3.4 落地 `/generator/playtest/`..."）之后追加新段。

**改动**：**不动 ADR-022 决策核心**（保留原 gate；决策档 v0.2 §6.6 "不动的"明示），**新增**一段说明 2026-05-09 联动修订：

```markdown
**2026-05-09 修订（审美层决策 v0.2 §6.2 §3.1 联动）**：

- ADR-022 决策核心**不动**（playtest bots 完成标志阈值原 gate 保留；决策档 v0.2 §6.6）
- T-3.10 启动前置 T-3X-0/X1 落地（AESTHETIC_PREFERENCES.md + ADR-030 schema + prompt hook）；详 [/docs/DECISIONS.md](DECISIONS.md) ADR-030 + ADR-020 v0.2（PR-A 已落地）+ [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2
- 审美层 [A]ccept rate gate（≥ 60% pilot + Wilson CI）基于已结构化 AESTHETIC_PREFERENCES.md + ADR-030 schema 字段集**真作 gate**（不再是"假设作者锚点已建立"的悬空阈值）
```

## 落地点 3：§7 任务清单新增 T-3X-0 + T-3X-1 槽位（决策档 v0.2 §6.2 §7 改动）

**段位**：STAGE_3_TASKS.md L360-L381（"## 7. 任务清单概览"表格 + 表后注脚）。

**改动**：在表格末（T-3.12 行 L377 之后）新增 2 行 + 表后注脚补充。

**新增任务行**：

```markdown
| **T-3X-0** | **非工程任务**（作者本人；不走 ABC；不需要 L3 执行会话）| 作者审美锚点工程 — 读 3 部经典（Deadlight + Crimson Letters + 极乐迪斯科原版）+ 填阅读对照表 + 产出 /docs/AESTHETIC_PREFERENCES.md v0.1；指引详 决策档 v0.2 §7 | /docs/AESTHETIC_PREFERENCES.md（新建）+ /docs/reviews/aesthetic/T-3X-0_<work>_reading.md（三份） | 无 | N/A（非工程；不走 ABC）|
| **T-3X-1** | [B-author-gate] | ADR-030 立项 + AestheticPreference schema 落地 + prompt hook（基于 T-3X-0 实证归纳字段集；不预定）| /schema/aesthetic_preference.schema.json（新建首版 0.4.0）+ /generator/scene_strategies.py（aesthetic_preference_context 注入段）+ /generator/prompts/scene/（注入段）+ /generator/tests/ | T-3X-0 完成（AESTHETIC_PREFERENCES.md v0.1 已 commit）| ❌ 默认 ABC |
```

**表后注脚补充**（L379-L381 之间追加）：

```markdown
> **T-3X / T-3X 系列（2026-05-09 审美层决策 v0.2 §6.2 新增；2026-05-12 v0.2.3 命名校准）**：T-3X-0（非工程；作者本人审美锚点工程）+ T-3X-1（工程；ADR-030 + schema + prompt hook 基于 T-3X-0 实证归纳）共同作为 T-3.10 前置任务。命名 "T-3X" 是 L2 校准会话标签（T-3X L2 校准产出；**三和 X 之间无点，与中划线后缀 -0 / -1 连接**），**并列于 T-3 主线工程任务**（不是 T-3 主线子集；与 T-3.6a / T-3.6b 拆任务的子级语义不同；T-3.X 仍保留作 T-3 主线通配符语义）。详 [/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §5 关键决策点 8 + §6.2。
```

## 落地点 4：§6 wave 图同步更新（与 §7 联动）

**段位**：STAGE_3_TASKS.md L308-L349（"## 6. 工作 wave 与依赖图"代码块）。

**改动**：在 Wave 0 段新增 T-3X-0 启动节点（非工程；作者本人；不阻塞下游工程任务）；在 Wave 7（T-3.10）前新增 T-3X-1 节点（工程；走 ABC；阻塞 T-3.10）。

**新增/修订 Wave 段示意**（具体位置由执行会话拍板；建议**在 Wave 6 后、Wave 7 前**插入新 Wave 6.5）：

```text
Wave 0（独立可并行；不阻塞下游工程任务）:
   T-3.0    [A]   起手清理 PATCH
   T-3.11   [A]   开源剥离边界清单 v0.2 增量
   T-3.8a   [A]   version_recorder.py 独立模块
   T-3X-0   [非工程] 作者审美锚点工程（不走 ABC；作者本人；时长 1-3 周；不阻塞其他工程任务）
   ↓ 不阻塞下游工程

[Wave 1-6 不动；T-3X-0 在作者节奏内同步进行]

Wave 6.5（T-3X-0 完成后启动；T-3.10 前置）:
   T-3X-1   [B]   ADR-030 立项 + schema 落地 + prompt hook（依赖 T-3X-0 产出 AESTHETIC_PREFERENCES.md v0.1）
   ↓ PR merge 后 Wave 7 才能启动

Wave 7（实测期；A 阶段实测；变体 ABC）:
   T-3.10   [A]   完成标志实测（依赖 T-3X-1 + T-3.5 + T-3.6a + T-3.6b + T-3.4 全部 PR merge）
   [...]
```

## 落地点 5：修订 /docs/prompts/stage_3/T-3.10.md（决策档 v0.2 §6.2 末尾改动）

**段位**：T-3.10.md 全文（L1 简介段 + L10 依赖段 + L18-L26 任务目标段 + L33-L36 跳 BC 适用性段 + L48-L50 必读段）。

**改动**：

- **L10 依赖段**：当前 "T-3.5 + T-3.6a + T-3.6b + T-3.4 全部 PR merge" → **追加** "+ T-3X-1（ADR-030 + schema + prompt hook） PR merge + T-3X-0 AESTHETIC_PREFERENCES.md v0.1 已 commit"
- **L18-L26 任务目标段**：审美层 [A] gate 表述**追加** "基于已结构化 AESTHETIC_PREFERENCES.md（T-3X-0 产出）+ ADR-030 schema 字段集（T-3X-1 落地）；真作 gate（不再悬空阈值）"
- **L48-L50 必读段**：追加 `/docs/AESTHETIC_PREFERENCES.md` + `/docs/DECISIONS.md` ADR-030 + ADR-020 v0.2 + 决策档 v0.2 §6.2

**具体改动文字**（执行会话按 markdown 风格落地）：

- L10 → `> | 依赖 | T-3.5 + T-3.6a + T-3.6b + T-3.4 全部 PR merge **+ T-3X-1（ADR-030 + schema + prompt hook）PR merge + T-3X-0（AESTHETIC_PREFERENCES.md v0.1）已 commit**（2026-05-09 v0.2 新增）|`
- L20 → `- 审美层 [A]ccept rate：**≥ 60% pilot + Wilson 95% CI 报告**（基于已结构化 /docs/AESTHETIC_PREFERENCES.md + /schema/aesthetic_preference.schema.json 字段集真作 gate；2026-05-09 v0.2 新增）`

## 落地点 6：§10 修订记录追加 2026-05-09 v1.0.1 条目 + §11 版本时间戳

**段位**：STAGE_3_TASKS.md L434-L443（"## 10. 修订记录"）+ L446-L451（"## 11. 版本"）。

**修订记录新增条目内容草拟**：

```markdown
- **2026-05-09 v1.0.1**：审美层决策 v0.2 §6.2 吸收。修订点：§1 完成标志表新增 T-3X-0/X1 前置条件行（保留 [A] ≥ 60% pilot + Wilson CI 原阈值）+ §3.1 ADR-022 决策核心追加 2026-05-09 联动修订段（不动 ADR-022 决策核心）+ §6 wave 图新增 Wave 6.5（T-3X-1）+ T-3X-0 进 Wave 0 + §7 任务清单新增 T-3X-0（非工程；不走 ABC）+ T-3X-1（[B-author-gate]；走 ABC）+ T-3.10 paste-ready prompt 修订为基于 AESTHETIC_PREFERENCES.md + ADR-030 跑。来源：[/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md](reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md) v0.2 §6.2。联动 PR-A（ADR-030 + ADR-020 v0.2）+ PR-B（ROADMAP + HANDOFF）。L1 fixation 执行会话产出。
```

**版本段更新**：

- L447 `本文件版本：v1.0` → `本文件版本：v1.0.1`
- L448 `最后更新：2026-05-08` → `最后更新：2026-05-09`
- L449 `产出方：阶段 3 L2 整合规划师会话（claude/sweet-bardeen-863720 worktree）` → 保留 + 追加 "v1.0.1 修订产出方：L1 fixation 执行会话（本 PR；T-3X L2 校准产出 paste-ready prompt 落地）"

# ABC 闭环要求

**默认走完整 ABC**（不跳 BC）：

- **A 阶段（本会话）**：write + commit + push + 开 PR；commit 后**等作者明示** B 阶段是否起 Codex review
- **B 阶段**：作者另起 Codex 会话（GPT-5.5）；review prompt 复用 [/docs/REVIEW_PROMPT_CODE_GPT.md](../../REVIEW_PROMPT_CODE_GPT.md) v0.2；review 报告 push 到 main 独立 commit（治理 v0.3 §10 第 7 条 + v0.4.1 patch §12 gap #2 闭合）；**特别关注**：B 阶段 review 重点 = §1 阈值表新增行的语义一致性 + §6 wave 图新增 Wave 6.5 拓扑合理性 + §7 任务清单新增 T-3X-0/X1 描述一致性 + T-3.10.md 修订与 §1 阈值表对齐
- **C 阶段**：吃 B 阶段 review 报告 → 追加 commit 到原 PR

**跳 BC 破例可能性**：本 PR 修订量最大（最复杂；4 个 L1 文档段位 + 1 个 prompt 文件）；**强烈不建议**跳 BC——B 阶段 review 边际价值高。

# A 阶段执行步骤

1. **首步：验证 PR-A 已 merge**：`gh api repos/outsiderrr/Forgewright/commits/main --jq '.commit.message'` 看是否含 "ADR-030" 或类似关键字；如未 merge，停止本 PR 启动
2. 读必读清单（7 项）
3. 按"落地点 1-6"分别 Edit `/docs/STAGE_3_TASKS.md` + `/docs/prompts/stage_3/T-3.10.md`
4. 跑本地 `/review` skill（如可用）+ 检查 markdown 表格渲染（特别 §1 阈值表 + §7 任务清单 + §6 wave 图代码块）
5. 提交：

   ```bash
   git add /docs/STAGE_3_TASKS.md /docs/prompts/stage_3/T-3.10.md
   git commit -m "$(cat <<'EOF'
   docs: L1 fixation of aesthetic layer decision v0.2 — PR-C (STAGE_3_TASKS v1.0.1 + T-3.10 prompt)

   落实审美层决策 v0.2 §6.2：

   - §1 完成标志表新增 T-3X-0/X1 前置条件行（保留 [A] ≥ 60% pilot + Wilson CI 原阈值；不修订）
   - §3.1 ADR-022 决策核心追加 2026-05-09 联动修订段（不动 ADR-022 决策核心）
   - §6 wave 图新增 Wave 6.5（T-3X-1）+ T-3X-0 进 Wave 0
   - §7 任务清单新增 T-3X-0（非工程任务；不走 ABC）+ T-3X-1（[B-author-gate]；走 ABC）
   - /docs/prompts/stage_3/T-3.10.md 修订前置 + [A] gate 表述基于 AESTHETIC_PREFERENCES.md + ADR-030
   - §10 修订记录追加 2026-05-09 v1.0.1 条目 + §11 版本时间戳更新

   追溯：/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md (v0.2)
   T-3X L2 校准产出：/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md
   依赖：PR-A（ADR-030 + ADR-020 v0.2）已 merge

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   git push -u origin <current-branch>
   ```

6. 开 PR；title + body 参 PR #50 模式：
   - title：`docs: L1 fixation of aesthetic layer decision v0.2 — PR-C (STAGE_3_TASKS v1.0.1 + T-3.10 prompt)`
   - body 段：Summary / 改动（按落地点 1-6 分列）/ 不冲突（DECISIONS 由 PR-A 落地 / ROADMAP + HANDOFF 由 PR-B 落地 / SCHEMA / AESTHETIC_PREFERENCES.md 由 T-3X-0 + T-3X-1 后续落地）/ 依赖（PR-A 已 merge 前置）/ ABC 流程 / 追溯 / Test plan

# 完成判定

- STAGE_3_TASKS.md 落地 6 个修订点（§1 + §3.1 + §6 + §7 + §10 + §11）
- T-3.10.md 落地 3 个修订点（依赖段 + 目标段 + 必读段）
- PR open + commit + push 完成
- PR body 含 ABC 流程段 + 依赖 PR-A 已 merge 的明示
- 回报作者：PR URL + 是否发现遗漏 / 需作者拍板的细节
```

---

## 6. 修订追踪表

> 决策档 v0.2 §6 全部 5 项修订对应到 3 个 PR；本表用于 L2 验收期核对完整性。

| 决策档 v0.2 锚点 | 修订内容摘要 | 对应 PR | 待落地文件 |
|---|---|---|---|
| **§6.1.a** | ROADMAP §阶段 3 新增工具第一版 scope 声明段（不做战斗 / 思维内阁 / 内心独白；主做对话 + 调查 + 物品 + NPC + 技能 + 检定；CoC 主导 + 极乐迪斯科补充） | **PR-B** | `/docs/ROADMAP.md` |
| **§6.1.b** | ROADMAP §阶段 3 完成标志强化项保留 [A] gate + 新增 T-3X-0/X1 前置 + 时长 +1-3 周 + 阶段概览表更新 | **PR-B** | `/docs/ROADMAP.md` |
| **§6.2 §1** | STAGE_3_TASKS §1 完成标志保留 [A] ≥ 60% Wilson CI + 新增 T-3X-0/X1 前置条件行 | **PR-C** | `/docs/STAGE_3_TASKS.md` |
| **§6.2 §3.1** | STAGE_3_TASKS §3.1 ADR-022 决策核心不动 + 追加 2026-05-09 联动修订段 | **PR-C** | `/docs/STAGE_3_TASKS.md` |
| **§6.2 §7** | STAGE_3_TASKS §7 任务清单新增 T-3X-0（非工程）+ T-3X-1（[B-author-gate]）+ §6 wave 图同步 | **PR-C** | `/docs/STAGE_3_TASKS.md` |
| **§6.2 T-3.10 修订** | T-3.10 paste-ready prompt 文件修订依赖 + [A] gate 表述基于 AESTHETIC_PREFERENCES.md + ADR-030 | **PR-C** | `/docs/prompts/stage_3/T-3.10.md` |
| **§6.3** | HANDOFF §审美层 review 激活段措辞校准为 "T-3X-0+X1 落地后激活"；与 feedback memory 真实建议关系明示；X4 行同步更新 | **PR-B** | `/docs/HANDOFF_STAGE_2_TO_3.md` |
| **§6.4** | 新立 ADR-030 AestheticPreference schema（字段集留空预留；待 T-3X-1 实证归纳；候选起点不预定）+ §变更历史追加 2026-05-09 授权记录 | **PR-A** | `/docs/DECISIONS.md` |
| **§6.5** | 同步立 ADR-020 v0.2（X4 闭环；阶段 2/3/4 三阶段口径）；保持与 ADR-022 兼容（ADR-022 不修订） | **PR-A** | `/docs/DECISIONS.md` |
| **§6.6 "不动的"** | 不动 feedback memory / strategy_calibration v0.1 / ADR-022 / DEBATE_NOTES / 阶段 4 ROADMAP 起手周 | 无（明示不修订） | N/A |
| **§7 T-3X-0 指引模板** | L1 已直接出（归决策档 v0.2 §7）；T-3X 不重复出 | 无（不重复） | N/A（决策档 v0.2 §7） |

**总计**：决策档 v0.2 §6 5 项修订（§6.1-6.5）+ §6.6 "不动的" 明示 + §7 指引模板（L1 已出）= **3 个 L3 fixation PR 完整覆盖**。

---

## 7. 给作者的下一步指示

### 7.1 拍板项

1. **拆 3 个 PR 是否接受**？候选拆法：
   - 推荐：3 个 PR（PR-A / PR-B / PR-C；本备忘起草版）
   - 备选：2 个 PR（合并 PR-A + PR-B 为单 PR；PR-C 独立）—— diff 量略大但减少 1 个 PR 启动开销
   - 备选：1 个大 PR（参 PR #50 模式同款单 PR）—— 不推荐（diff 量过大；review 焦点稀释）

2. **执行顺序拍板**：
   - 推荐：**串行** PR-A → PR-C → PR-B（PR-A 必须先；PR-B 可放最后或与 PR-A 并行）
   - 备选：**部分并行** PR-A + PR-B 并行起步（独立 worktree）→ 两者 merge 后 → PR-C 启动
   - 备选：**全部并行**（不推荐；STAGE_3_TASKS §3.1 + §7 引用 ADR-030，PR-A 未 merge 会引用断裂）

3. **每个 PR 的 ABC vs 跳 BC 拍板**：

| PR | T-3X L2 推荐 | 作者可破例方向 |
|---|---|---|
| **PR-A**（DECISIONS） | **默认完整 ABC**——新立 ADR 是架构级；B 阶段 review 价值高（检查 ADR-030 表述与决策档 v0.2 §6.4 + ADR-020 v0.2 与 ADR-022 兼容性） | 不推荐跳 BC |
| **PR-B**（ROADMAP + HANDOFF） | **默认完整 ABC**——但可跳 BC（参 PR #50 模式 "B 阶段由作者自行决定"；本 PR 为措辞校准，1:1 引用决策档 v0.2 §6.1 + §6.3） | 可破例跳 BC（低风险） |
| **PR-C**（STAGE_3_TASKS） | **强烈推荐完整 ABC**——修订量最大（4 个 L1 段位 + 1 个 prompt 文件）；B 阶段 review 边际价值高 | 不推荐跳 BC |

### 7.2 启动每个 PR 的方式

按治理 v0.4 §11 + memory feedback_abc_c_phase_same_session：

- **新会话起步首条消息**：将本备忘 §3 / §4 / §5 对应 PR 的 ```text 围栏内全部内容复制粘贴到新 Claude Code 会话
- **OR 简短引用**：`请按 /docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md §3 PR-A 的内容执行任务`

### 7.3 T-3X L2 校准发现的潜在遗漏 / 拍板项

T-3X L2 校准期未发现实质遗漏；但有几个细节作者可后续拍板：

1. **ROADMAP §阶段概览表时长**：5-9 周（含 T-3X-0 1-3 周）—— 是否在表内同时显示工程估时 4-6 周 + 作者锚点工程 1-3 周两个数？还是合并为 5-9 周单值？本备忘 §4 PR-B 草拟为 "5-9 周（含 T-3X-0 1-3 周作者锚点工程）" 合并单值
2. **STAGE_3_TASKS §6 wave 图 T-3X-1 位置**：草拟为 Wave 6.5（Wave 6 后、Wave 7 前；与 T-3.10 强串行）；备选可放 Wave 7 起步同 step（与 T-3.10 并行）—— **不推荐并行**因为 T-3.10 [A] gate 真作 gate 必须依赖 T-3X-1 schema + prompt hook
3. **T-3X-1 任务编号是否进 §7 任务清单表**：草拟为加入（编号 T-3X-1）；备选可单独表 / 注脚标 —— **推荐加入** §7 主表，方便 L3 paste-ready prompt 后续生成（v0.4 prompt 文件化兼容）
4. **T-3X-1 paste-ready prompt 文件路径**：本备忘未涉及；T-3X-1 启动时由 L2 整合规划师另起会话产 `/docs/prompts/stage_3/T-3X-1.md`（不属本备忘范围）
5. **PR-C 是否需同步更新 STAGE_3_TASKS §8 paste-ready prompt 索引表**（L395-L410）：草拟不动（T-3X-1 prompt 文件后续单独由 L2 整合规划师起会话产；本 PR 不创建）—— 作者可拍板是否在 §8 表内预留 T-3X-1 占位行

### 7.4 T-3X L2 校准本身的合规性自检

- ✅ 跳过 cross-LLM critique（作者明示授权）
- ✅ 跳过 ABC（作者明示授权——T-3X 校准本身跳；但起草的 L3 fixation PR prompt 仍含 ABC 闭环要求）
- ✅ 不写代码 / 不修 L1 文档 / 不立 ADR
- ✅ 不重复出 §7 T-3X-0 指引模板（L1 已出归决策档 v0.2 §7）
- ✅ 不预定 ADR-030 schema 字段集（明示由 T-3X-1 实证归纳；候选起点列了但不预定）
- ✅ 唯一允许写入位置 = `/docs/reviews/master_plan/2026-05-09_T-3X_aesthetic_pre_fixation_prompts.md`（本文件）

### 7.5 作者拍板记录（2026-05-12；产品线背景同步后）

T-3X L2 校准期作者主动同步产品线（Claude 网页对话；产品/审美/脑暴主线）最新决策；T-3X 识别 4 项真矛盾 + 1 项待协调项；作者 2026-05-12 拍板如下：

| 矛盾点 | 作者拍板 | T-3X 修订动作 |
|---|---|---|
| **1 阅读清单** | 作者实际把 3 部经典放到 `/Users/outsider/Desktop/剧本/`：Crimson Letters 提取 + Dead Light and Other Dark Turns 合集 PDF + Disco Elysium Final Cut PDF —— 与决策档 v0.2 §6.1.a 措辞兼容（Deadlight ≈ Dead Light；极乐迪斯科原版 ≈ Final Cut） | **不修引用**（保留 v0.2 措辞；具体读模组选择由作者 T-3X-0 实际阅读期决定）|
| **2 内心独白 scope** | 思维内阁不做 + 内心独白硬不做（v0.2 §6.1.a 措辞硬性保留）| **保留 v0.2 §6.1.a 硬"不做"列表**（战斗 / 思维内阁 / 内心独白）|
| **3 ADR 编号顺序** | 作者已 push ADR-028（Engine-Host Split；2026-05-10）+ ADR-029（技能体系配置层；2026-05-11）到 main；本备忘起草的 AestheticPreference 顺延为 **ADR-030** | **批量替换** ADR-028 → ADR-030（全文 60+ 处；grep 确认所有引用都指 AestheticPreference，安全） + PR-A 段位说明从"在 ADR-027 后追加"改为"在 ADR-029 后追加" + ADR-030 关联讨论段补 ADR-028/029 兼容性条款 + §变更历史授权记录时间戳改 2026-05-12（落地日；与 main 现有授权记录格式一致） |
| **4 技能系统措辞** | 选 B（细化）| PR-B ROADMAP scope 段"主做：技能系统"改为"主做：技能体系（具体技能数 / 列表 / 性格化或功能化 / 骰子规则 NdM + modifier vs DC 由项目配置层定义；引擎只规范 active_check + passive_injection 基础机制；详 ADR-029）"；并加 T-3X L2 校准 2026-05-12 联动 ADR-029 修订追溯注 |
| **5 题材切换** | 选 C（不纳入本次 L3 fixation）| **不修**（题材切换 + CLAUDE.md 修订属更高层议题；超 T-3X 校准范围；作者后续另起 L1 修订会话处理）|

### 7.6 T-3X L2 校准遗留 / 给作者后续会话的提醒

1. **内心独白 scope 已闭合（作者 2026-05-12 拍板）**：保留 v0.2 §6.1.a 硬"不做：战斗 / 思维内阁 / 内心独白"原措辞作为最终结论。L3 fixation 任何 PR 不引入与此重叠的替代措辞
2. **题材"D&D → 克苏鲁"切换的 L1 文档清理（作者 2026-05-12 表态会让 L1 处理）**：超 T-3X 范围；作者明示会另起 L1 修订会话扫 CLAUDE.md（L9"类博德之门 3"暗示 D&D）+ ROADMAP 全文 + STAGE_X_TASKS 历史 + DEBATE_NOTES，识别 D&D 残留措辞 + 更新为克苏鲁；建议时机：T-3X-0 启动前或同期；不阻塞 T-3X L3 fixation 三 PR

> **作者 2026-05-12 同时表态**：产品线 ADR-028/029（已 push）对 STAGE_3_TASKS 既有 T-3.0~T-3.12 任务的影响**不需单独评估**——T-3X L3 fixation 三 PR 落地过程中如执行会话碰到联动校准需求，就地调整即可（不另起 L2 整合会话扫描）

---

## 8. 版本

本文件版本：**v0.2.3**
最后更新：2026-05-12
产出方：T-3X L2 校准会话（claude/jovial-elion-c8d60c worktree）
基于：审美层决策 v0.2 §6 + PR #50 L1 fixation 模式 + 治理备忘 v0.4.1 §10 ABC 流程

### 修订记录

- **v0.2.3（2026-05-12 四次微调；T-3X 命名校准）**：作者明示 T-3X 系列任务命名校准为 **T-3X-0 / T-3X-1**（**三和 X 之间无点；以中划线连接后缀**），与之前误用的 "T-3.X0 / T-3.X1"（点分隔）作区分。理由：T-3.X 在阶段 3 工作流里已是 T-3 主线通配符（T-3.0/T-3.1/.../T-3.6a/T-3.12 等任意主线任务）；T-3X 系列是**与 T-3 主线并列**的另一 namespace；用 "T-3.X0" 措辞视觉上易混淆为 "T-3 主线下的 X0 子任务"，与并列语义冲突。修订点：T-3X 备忘全文 65 处批量替换（T-3.X0 → T-3X-0；T-3.X1 → T-3X-1；T-3.X 系列 → T-3X 系列）+ §5 注脚加命名校准说明 + L7 任务性质段措辞校准。**main 上 5 个 L1 文档**（DECISIONS / ROADMAP / STAGE_3_TASKS / HANDOFF / T-3.10.md；PR-A/B/C 已落地）**32 处命名 inconsistency 仍待 L3 fixation PR-D 修订**（本备忘 §8 修订记录里增列 PR-D 起草指引）。
- **v0.2.2（2026-05-12 三次微调）**：作者明示 v0.2.1 中曾搁置的"内心独白"替代措辞作废（概念冗余）。修订点：§7.5 矛盾 2 行表头改为"内心独白 scope"+ 内容仅保留 v0.2 措辞结论；§7.6 第 1 点重写为"已闭合"状态；活内容里所有被作废措辞的引用一并删除。v0.2 / v0.2.1 历史修订记录条目保留作 archival 追溯（不动以免破坏修订记录一致性）。
- **v0.2.1（2026-05-12 二次微调）**：作者追加 2 项 §7.6 简化拍板：(1) "内心独白 vs 内心剧场"歧义**搁置**——保留 v0.2 §6.1.a 硬"不做"原措辞；产品线"内心剧场"措辞不进任何 L3 PR 起草内容；(2) 产品线 ADR-028/029 对 STAGE_3_TASKS 既有 T-3.0~T-3.12 任务的影响**不需单独评估**——T-3X L3 fixation 三 PR 落地过程中如执行会话碰到联动校准需求就地调整。修订点：§7.5 矛盾 2 行措辞校准 + §7.6 第 1 点改为"已搁置"状态 + §7.6 第 2 点（产品线 ADR-028/029 影响）从主列表删除转为脚注作者表态记录 + §7.6 第 3 点（题材切换）加注"作者表态会让 L1 处理"。
- **v0.2（2026-05-12）**：产品线背景同步后作者 5 项拍板（详 §7.5）落实。修订点：(1) 全文 ADR-028 → ADR-030 批量替换（产品线 ADR-028/029 已占用编号 028/029）；(2) PR-A 落地点 1 段位说明改"在 ADR-029 后追加"+ 加产品线 ADR-028/029 已落地的关键背景；(3) ADR-030 关联讨论段补 ADR-005/027/028/029 同源兼容性条款；(4) §变更历史授权记录时间戳改 2026-05-12 + 加 ADR 编号顺延理由；(5) PR-B 落地点 1 ROADMAP scope 段"主做：技能系统"细化为"技能体系 + ADR-029 项目配置层"措辞；(6) 新增 §7.5 作者拍板记录 + §7.6 T-3X 遗留提醒（"内心独白 vs 内心剧场" + 产品线 ADR-028/029 对 STAGE_3_TASKS 既有任务的潜在影响 + 题材切换 L1 清理建议）。
- **v0.1（2026-05-09）**：初版。基于审美层决策 v0.2 §6 起草 3 个 L3 fixation PR paste-ready prompts（PR-A DECISIONS / PR-B ROADMAP + HANDOFF / PR-C STAGE_3_TASKS + T-3.10 prompt）+ 修订追踪表 + 拍板请求 5 项。
