# Review / Routine 治理备忘

> 2026-05-01/03 L1 规划讨论结论。后续 L2 规划师与执行会话起手前必读。
>
> **本备忘不修改 L1 文档**（CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md），只是把讨论共识落盘，作为下游会话的工作前提。如未来要把任何条目升格为 ADR / ROADMAP 修订，需作者明示授权 + 走专门执行会话。

**日期**：2026-05-01（v0.1）/ 2026-05-01 v0.2 同日修订 / 2026-05-03 v0.3 修订 / 2026-05-08 v0.4 修订 / 2026-05-08 v0.4.1 修订 · **版本**：v0.4.1 · **产出方**：L1 规划讨论会话（master plan 续接）
**触发问题**：作者询问能否用 Claude Code 桌面端 routines（定时任务）自动驱动 L1 → L2 → L3 整条链路

---

## 1. 核心结论

**routines 不接 L1→L2→L3 主链；只跑仓库维护层（validate-all 日跑 + memory consolidate 周跑）。ABC 三阶段（见 §10）的运行粒度跟随规划粒度——放在"最具体且有规划"的层级（§10.6，ADR-037）；同一层级内不按任务类型差异化。需独立评审的工程任务，B 阶段 cross-LLM 评审一律保留——攒批也只是"一次审一批"，绝不跳过。**

四个理由（详见对话记录，此处略）：

1. L2 不是 L1 的机械展开——每次都伴随新 ADR / 架构决策（ADR-014 / ADR-015 即此类）
2. L3 内部有 schema commit 串行卡口（CLAUDE.md 规则 2 + ADR-015）
3. L3 commit 经常反向触发 L2/L1 修订（阶段 1 R1–R8 即此类）
4. 作者是单点 reviewer + 不会编程，审阅带宽稀缺，错向自动跑代价大

---

## 2. L3 任务分类（**v0.3 状态：保留作为概念参考；实操不依赖**）

> v0.2 修订（2026-05-01）：从"硬性必须"降级为"软建议"。
> v0.3 修订（2026-05-03）：分类**保留作为认知概念**，但**实操不依赖分类**——所有 L3 一律跑 §10 ABC 三阶段流程；routines 不再尝试按分类串行跑 L3。L2 规划师写 STAGE_X_TASKS.md 时**可以**标也**可以**不标，不影响后续工作流。

### 三类描述（保留为概念）

#### `[A-execute]` 类：纯执行

- 写代码 / 写测试 / 写 docstring / 重构 / 修 bug
- 不动 `/schema/*` / `/docs/DECISIONS.md` / `/docs/ROADMAP.md` / `/docs/CLAUDE.md` / 其他 L1 文档
- 阶段 1 例：T-1.2 / T-1.3 / T-1.4 / T-1.5 / T-1.7

#### `[B-author-gate]` 类：架构级，需作者明示授权

- 动 schema 文件 / 新增或修订 ADR / 修订 SCHEMA_v0*.md / 验收报告
- 触发 CLAUDE.md 规则 9/10 例外条款，需作者明示授权
- 阶段 1 例：T-1.0（动 SCHEMA_v0.md）/ T-1.1（ADR-011/012/013 立项）/ T-1.8（验收）
- 阶段 1.5 已知例：T-1.5.1（ADR-014，已 commit `77a5f54`）/ T-1.5.2（image_asset schema + visual_assets 字段）/ T-1.5.10（验收）

#### 隐藏第三类：反向回退 / 修复任务

- 不在原 L3 清单里，由前置 L3 跑出问题反向冒出
- 阶段 1 例：commit `10017b7` / `54e0920` / `db06af5`（baseline 迭代修 bug）
- 由 §10 ABC 流程的 B 阶段或 C 阶段反向触发，纳入下一轮迭代

### v0.3 后分类怎么用

- **可用于 L2 规划师在 TASKS.md 里加注释**——比如某 L3 标 `[B-author-gate]` 提醒"这个动 schema 需作者审"，纯文档辅助
- **不用于 routine 调度**——routine 不再"串行跑 A 类、跳过 B 类"
- **不用于改变 review 流程**——A 类 / B 类 L3 一律走 §10 ABC 三阶段，不区分

### 设计先于施工（v0.5 新增，ADR-037）

`[B-author-gate]` 类里的**地基改动**不再散在各 L3 各自串行处理，而是**上提到设计/规划层先落定**：

- **硬地基**（数据格式/schema、共享状态、L1 文档）：设计层用专门 schema-only ABC 先浇好，按 ADR-015 串行 commit 原则串行落定，先于依赖它的施工批。
- **软地基 carve-out**：子任务触及下列任一项，单独先审/先落定（独立 ABC 或 foundation 子批），不得混进攒批——① 改数据格式（schema）；② 改校验器语义；③ 改共享函数行为（public helper 契约）；④ 改生成器输出 / 生成 trace 语义；⑤ 需迁移已有内容。（校准：仅当该契约被批内其它子任务或后续工作依赖时触发；纯内部、无人依赖的小函数不算。）
- 施工中意外挖出地基需求 → 安全阀（停批 → 上提 → 浇好 → 回来）。详 §10.7。

---

## 3. Review tier 分层（v0.3 修订）

| 层级 | 评审对象 | 评审者 | 触发 | 频率估计 |
|---|---|---|---|---|
| **L1** | 路线图 / 跨阶段 sequencing / 整体架构 | cross-LLM（Claude × GPT-5.5） | 作者主动起会话 | 项目周期共 1–3 次（Round 5 已 1 次） |
| **L2** | `STAGE_X_TASKS.md` 草稿 | cross-LLM 手动跑 | L2 规划师草稿合入前必经 | 每阶段 1 次（5–6 次） |
| **L3 / 攒批** | 最具体且有规划的层级（单个 L3 PR，或一个 L2 计划下 ≤8 个无独立规格需求子任务的一批；ADR-037 §10.6）| ABC 三阶段（见 §10）：A = Claude Code 开发；B = Codex GPT review（攒批时可扇出 + 集成评审）；C = Claude Code 吃反馈改代码 | L2 规划师**规划时定粒度** | 每阶段 5–15 次（攒批后作者触点下降）|

**v0.3 关键变更**：

- 去掉 v0.2 的"A 类 L3 不上 cross-LLM / B 类升级到 L2 标准"区分——所有 L3 一律走 ABC 三阶段
- 阶段 1.5 实操确认所有 L3 都跑过 GPT review（commit `33611cd` "backfill 9 codex review reports"），与统一流程一致
- 三阶段闭环全部完成才算该 L3 通过

---

## 4. Routines 启用清单（v0.3 修订说明）

### 当下启用（3 项）

| ID | Routine | 频率 | 说明 |
|---|---|---|---|
| **5a** | `make validate-all` 日跑 | 每天 1 次（凌晨） | schema 校验 + 单元测试 + lint；早抓 silent breakage |
| **5b** | `cost_log` 对账 | 每周 1 次 | 阶段 1 R7 已知 cost_log 高估（验收 §6：估 $2.14 vs 真实 $0.7–1.2）；周对账校准 |
| **5c** | `anthropic-skills:consolidate-memory` 跑 | 每周 1 次 | 现有 skill 直接调用；防 memory 文件腐烂 |

### 推到阶段 2/3 再启用

- 长跑 baseline 实验过夜跑（阶段 2 baseline_005+ 才需要；按需手动启动，不严格 routine）
- dependency drift scan（synthesis §6 `content_dependency_index` 雏形；阶段 3+ 才有意义）
- GitHub PR 状态扫描（阶段 4 开源剥离后）

### 不启用 + v0.3 明示

- **routine 串行跑 L3 任务**（v0.2 设想，v0.3 废弃）——原本设想 routine 跑 [A-execute] 类 L3 串行、遇 [B-author-gate] 硬停。v0.3 后废弃，理由：结构复杂化没带来效率提升，作者审阅带宽是真瓶颈而不是任务调度
- 事件触发 git hook / GitHub Action 跑 GPT critique——L2 + L3 critique 全部手动跑性价比更高

**v0.3 后 routines 的边界明确**：只跑**仓库维护层**（5a / 5b / 5c），**不参与** L3 任务调度。L3 全部由作者手动起新会话跑（§10）。

---

## 5. L2 规划师工作约束（v0.3 修订）

### 产 `STAGE_X_TASKS.md` 时必做

1. 每个 L3 paste-ready prompt **必须含 §10 ABC 三阶段闭环要求**——A 阶段开发 + B 阶段 GPT review 报告 + C 阶段吃反馈改代码合入 PR
2. 任务分类（[A-execute] / [B-author-gate] / 反向回退）**可标可不标**——标了纯文档参考，不影响流程
3. 草稿落地后**手动**起 cross-LLM critique 会话（GPT-5.5 / Codex），跑 stable critique prompt（Round 5 `master_plan_battle_*` 系列已验证可复用），结果落 `/docs/reviews/master_plan/2026-XX-XX_STAGE_X_TASKS_draft_gpt_critique.md`
4. critique 消化后形成最终版本 TASKS.md，作者明示授权后才进入 L3 执行
5. **L3 验收**：拿 ABC 全部产出（A 阶段 PR + B 阶段 review 报告 + C 阶段修复 commit）判断过关 / 打回；通过才进下一个 L3

### 不要做

- 不要尝试搭 git hook / GitHub Action 自动化 critique——按当前频率手动跑性价比更高
- 不要尝试让 routine 跑 L3 任务——routine 只跑仓库维护层（§4）
- 不要把 L1 文档改进 L3 任务——任何 L1 文档变更需作者明示授权（CLAUDE.md 规则 9/10）
- 不要让 L3 任务**只跑 A 阶段就过**——B + C 阶段必须闭环（§10）

---

## 6. 待办（按时机）

| 时机 | 事项 | 责任方 |
|---|---|---|
| 立刻 | 起草 routines 5a/5c 的 settings.json hook 配置 prompt（用 update-config / schedule skill） | 作者起执行会话 |
| 阶段 1.5 启动 | (已完成) 起草 STAGE_1.5_TASKS.md；草稿合入前手动跑 cross-LLM critique；每个 L3 跑 ABC 三阶段（commit `33611cd` 9 份 codex review 是 B 阶段产物） | 阶段 1.5 L2 规划师 |
| R7 想真修时 | 实现 cost_log 反向对账脚本（5b 启用前置） | 阶段 2 起手期某个 L3 |
| 阶段 2 启动 | 同 §5 流程；每个 L3 含 ABC 三阶段闭环 | 阶段 2 L2 规划师 |

---

## 7. 决策表

- ✓ **1**：L1→L2→L3 主链不接 routines，保持人在环路
- ✓ **2**：L2 review = cross-LLM 强制 gate
- ✓ **3a**：每个 L3 commit 之前本地跑 `/review` skill + validate-all 仍可作工程基本盘
- ✓ **3b**（v0.3 修订）：~~分类是软建议——能分时 [A-execute] 可 routine 串行 / [B-author-gate] 硬停~~ → **分类作为概念保留，实操不依赖；所有 L3 一律走 §10 ABC 三阶段**
- ✓ **4**（v0.3 修订）：~~B 类 L3（动 schema / ADR / provider 接口）升级到 L2 review 标准~~ → **所有 L3 commit 后跑 §10 B 阶段 cross-LLM review，不区分类型**
- ✓ **5a / 5b / 5c**：启用 validate-all 日跑 + cost_log 周对账（推到 R7 想真修时）+ memory consolidate 周跑
- ✓ **5d/e/f 推迟**：长跑实验 / drift scan / PR 扫描推到阶段 2/3
- ✓ **6-A**：L2 critique 走手动模式（不引入事件触发自动化）
- ✓ **v0.3 新增**：L3 全部走 ABC 三阶段流程（§10），不按分类差异化；routines 不参与 L3 调度

---

## 8. 与现有 L1 文档的兼容性

本备忘不与任何 L1 文档冲突：

- **CLAUDE.md 规则 2 + 9 + 10**：动 schema / L1 文档需作者明示授权——分类制度概念里的 [B-author-gate] 类自然继承（即使不依赖分类，规则仍然守住）
- **ADR-015**：1.5 schema commit 串行 + 阶段 2 schema commit 等 1.5 验收 = 跨 L3 任务的串行卡口，与 §10 ABC 流程兼容（每个 schema commit L3 走完 ABC 后才进下一个）
- **ROADMAP §阶段 2 启动闸门 / §阶段 3 完成标志强化项**：占位指针待 L2 规划师落地，本备忘明确"L2 规划师必须先跑 cross-LLM critique 才能进 L3"
- **HANDOFF_STAGE_1_TO_1.5.md / HANDOFF_STAGE_1_TO_2.md**：未来交接档应在"工作模式"段补一行指向本备忘 v0.3

如未来需要把本备忘任何条目升格为 ADR-016+ / ROADMAP 修订，由作者明示授权 + 专门执行会话执行（参考 ADR-011/012/013/014/015 合入先例：commit `1d2030f` / `77a5f54` / `9851419`）。

---

## 9. 修订记录

- **2026-06-08 v0.5**：作者拍板 ABC 阶段层级化 + 设计先于施工（含软地基）（ADR-037 落地承接，经 cross-LLM critique 消化）。修订点：§1 核心结论 ABC 句 / §2 新增"设计先于施工"段 / §3 review tier 表 L3 行 / **新增 §10.6（ABC 粒度跟随规划 + 攒批护栏 + 三模式区分）+ §10.7（设计先于施工 + 安全阀硬闸）** / §11 新增"与攒批 ABC 的兼容" / §10 B 报告路径 `_targets/` → `<ISO_DATE>` 统一 + C 阶段措辞"新会话"→"默认回原会话"。同期顺手修既有文档债：STAGE_3_TASKS §1.5.4 加"攒批 ABC ≠ 跳 BC"区分注 + §1.5.1 C 阶段措辞；prompts/README.md C 阶段措辞；REVIEW_PROMPT_CODE_GPT.md "不要 commit/push" vs "报告 push 到 main"自相矛盾理顺。**默认行为**：工程类 ABC 粒度跟随规划、≤8 子任务可攒批（B 保留）、地基（硬+软）改动设计层先落定、安全阀硬闸。落地走 L1 直签 main fixation 模式（作者 2026-06-08 明示授权 + 本 PR merge）。
- **2026-06-08 v0.4.2**：作者授权同步 §11 目录定位——`/docs/prompts/` 从「仅 L3 paste-ready prompt」broaden 为「项目所有 AI 生成提示词归档」（详 `/docs/prompts/README.md` v0.2）。§11 明确仅约束 `stage_N/` L3 prompt；根目录新增 L1/治理类起手 prompt（首个 `L1_KICKOFF_ABC_PROPOSAL.md` = ABC 阶段层级化提案的 L1 会话起手 prompt，提案未拍板/未应用）。**破例说明**：本次在 dev 对话会话内经作者明示授权直接修订，未走专门 L1 会话——因属目录定位"措辞同步"级、非 ABC 工作流实质变更；ABC 层级化提案本身仍走专门 L1 会话（见 `L1_KICKOFF_ABC_PROPOSAL.md`）。**默认行为**：prompt 归档目录定位 broaden 即时生效。
- **2026-05-08 v0.4.1**：作者拍板 gap #2 + gap #3 修补 patch（v0.5 完整 B/C prompt 文件化升级暂缓决策的 interim solution）。修订点：`/docs/REVIEW_PROMPT_CODE_GPT.md` v0.1 → v0.2（末尾加 "报告 push 到 main 独立 commit" 段 + `{{REVIEW_TARGET}}` 段加 "可附 L2 视角补充上下文"）+ governance §10 加第 7 条 + 新增 §12 v0.4.1 patch 段。**默认行为**：B 阶段 Codex 自动 commit + push；作者填 REVIEW_TARGET 时可附 L2 视角补充上下文。详 §12。
- **2026-05-08 v0.4**：作者拍板把 L3 paste-ready prompt 从 `STAGE_X_TASKS.md` §8 内嵌的 ` ```text` 代码块拆出，每个 L3 任务单独存为 `/docs/prompts/stage_N/T-N.X.md` 文件。L3 会话起步标准格式从"复制粘贴 paste-ready prompt 块"改为"读 prompt 文件"。触发：阶段 3 起手期（PR #33 merge 后）作者发现复制粘贴 14 长 prompt 块辛苦 + 复盘困难。修订点：**新增 §11 L3 prompt 文件化工作流（v0.4 新增）**；§3 / §5 引用文件路径形态调整；§10 ABC 流程图 A 阶段首条消息形态改"读 prompt 文件 OR 直接说执行 T-N.X"。**默认行为**：阶段 3 起手新规范——所有 L3 prompt 单独文件；阶段 0/1/1.5/2 历史 prompts 不回填；阶段 4+ 复用同款规范（modifier `/docs/prompts/stage_N/`）。Meta task 落地：`claude/meta-prompt-extract` 分支整合（含 14 个 stage_3 prompt 文件 + STAGE_3_TASKS.md §8 改表格引用 + governance v0.4 修订；详见 PR）。
- **2026-05-03 v0.3**：作者拍板（1）任务分类制度保留作为概念参考，但实操不依赖分类——routines 不再尝试串行跑 L3 任务；（2）所有 L3 一律跑统一 §10 ABC 三阶段流程，不按 [A-execute] / [B-author-gate] 差异化。触发：阶段 1.5 实操（commit `33611cd` 9 份 codex review backfill）确认 9 个 L3 都跑了同一 ABC 流程，与 v0.2 "A 类省 cross-LLM" 矛盾；作者认为按分类调度 routine 是结构复杂化没带来效率提升。修订点：§1 核心结论 / §2 状态 / §3 review tier 表格 / §4 routines 边界明示 / §5 L2 规划师约束 / §6 待办时机 / §7 决策表 3b/4 + 新增项 / **新增 §10 L3 ABC 三阶段流程**。**默认行为**：所有 L3 PR 都必须跑完 ABC 三阶段才算闭环。
- **2026-05-01 v0.2**：作者拍板把 §2 任务分类制度从"硬性必须"降级为"软建议"。触发：阶段 1.5 已在执行中（T-1.5.1 commit `77a5f54` 已完成 / T-1.5.1a 已完成 / 后续 L2 规划层在路上），实际推进观察到 L3 大半涉及 schema / image / ADR / provider 接口，B 类居多，强制分类边际收益低。修订点：§2 引言语气 + §5 第 1 条 + §7 3b。**默认行为不变**：未分类的 L3 走 `[B-author-gate]`（作者每个 commit 看一眼），保持安全。其余条款（§3 review tier / §4 routines 启用清单 / §6 待办 / §8 与 L1 兼容性）未变。
- **2026-05-01 v0.1**：初版。L1 规划讨论"能否用桌面端 routines 自动驱动 L1→L2→L3"问题落盘，含核心结论 / 任务分类制度（硬性版）/ review tier 分层 / routines 启用清单 / L2 规划师约束。

---

## 10. L3 ABC 三阶段流程（v0.3 新增）

> 阶段 1.5 期间 9 个 L3 实际跑通的工作模式（commit `33611cd` 9 份 codex review 报告是 B 阶段产物）。v0.3 把它明文化为所有 L3 的统一流程。

### 流程图

```
L2 规划师产 STAGE_X_TASKS.md → 每个 L3 paste-ready prompt
              │
              ▼
        ┌─────────────┐
        │ A 阶段：开发 │  Claude Code 新会话（worktree）
        └─────────────┘
              │ 产出：commit + push + PR
              ▼
        ┌─────────────┐
        │ B 阶段：review │  Codex 会话（GPT-5.5）
        └─────────────┘
              │ 产出：review 报告（finding 清单 red/yellow/green）
              ▼
        ┌─────────────┐
        │ C 阶段：修复 │  默认回 A 原会话（吃 B 反馈）
        └─────────────┘
              │ 产出：追加 commit 到原 PR / 新 PR
              ▼
        ┌─────────────┐
        │ L2 验收 L3  │  L2 规划师拿 ABC 全部产出判断
        └─────────────┘
              │
              ├── 过关 → 下一个 L3 进 A 阶段
              └── 打回 → 回 C 重做 / 回 B 跑二轮
```

### A 阶段：开发

| 项 | 内容 |
|---|---|
| **谁做** | 作者起 Claude Code 新会话（自动新建 worktree + claude/* 分支） |
| **首条消息** | L2 给的 paste-ready prompt（来自 STAGE_X_TASKS.md 该 L3 段） |
| **会话工作** | 按 prompt 开发 + 写测试 + 跑本地 `/review` skill + validate-all + commit + push 到 worktree 分支 + 开 PR（base = main，head = 当前 worktree 分支） |
| **产出** | commit hash + PR URL + 工程产物（代码 / 测试 / 文档） |
| **完成判定** | PR open + validate-all 过 + 测试过 |

### B 阶段：cross-LLM review（GPT-5.5 / Codex）

| 项 | 内容 |
|---|---|
| **谁做** | 作者起 Codex 会话（OpenAI GPT-5.5 命令行） |
| **review prompt 来源** | 当前已落盘的 cross-LLM code review prompt（commit `8842c43`，`/docs/REVIEW_PROMPT_CODE_GPT.md`）；如有版本更新参考最新版 |
| **review 输入** | A 阶段 PR 的 diff + 相关代码上下文 + 该 L3 任务的原 paste-ready prompt（让 GPT 知道目标） |
| **review 报告落盘** | `/docs/reviews/<ISO_DATE>_T-X.X_<topic>_review.md`（与 STAGE_3_TASKS §1.5.1 + REVIEW_PROMPT_CODE_GPT.md 统一；旧 `_targets/` 写法 v0.5 废止）|
| **报告内容** | finding 清单（red / yellow / green 严重度）+ 建议改动 |
| **完成判定** | 报告落盘 + 作者扫一眼总结 |

### C 阶段：修复

| 项 | 内容 |
|---|---|
| **谁做** | 默认回 A 原会话/原分支（吃 B 反馈续做）；必要时新会话同分支 |
| **首条消息** | "吃 `/docs/reviews/<ISO_DATE>_T-X.X_<topic>_review.md` 的 review 报告，按 finding 清单修代码"+ 相关上下文 |
| **会话工作** | 按 review 反馈修代码 + 跑测试 + commit + push（追加到原 PR）|
| **产出** | C 阶段 commit hash + PR 已更新 |
| **完成判定** | 所有 red finding 修复 + 重要 yellow finding 修复或显式拒收（带理由）|

### L2 验收 L3

| 项 | 内容 |
|---|---|
| **谁做** | 阶段 X L2 规划师会话（不是作者本人，是 L2 会话）|
| **输入** | A 阶段 PR + B 阶段 review 报告 + C 阶段修复 commit |
| **判定** | 过关 → 通知作者可 merge PR + 进下一个 L3；打回 → 指定回 C 重做 / 或回 B 跑二轮 |
| **作者动作** | 过关后去 GitHub 网页 merge PR（main 历史变更属作者明示） |

### 几个细节

1. **A 阶段 prompt 不需要写"完成后自动进 B 阶段"**——A 阶段会话只管开发；作者跑完 A 后手动起 B 阶段会话
2. **B 阶段 review prompt 复用**——不为每个 L3 重写，用 `/docs/REVIEW_PROMPT_CODE_GPT.md` 作模板，套上当前 L3 上下文
3. **C 阶段允许多轮**——如 review 报告修完仍有问题，作者可起第二轮 B（跑二次 review）+ 第二轮 C（再修）
4. **B 阶段红黄绿可拒收**——不是所有 finding 都必须接受；C 阶段修不修由作者 + L2 共同拍板
5. **L3 包含 schema commit / ADR 立项** 等仍走相同 ABC 流程——A 阶段 commit 后 B 阶段 review 看一致性 / 设计；不需要因为是"架构级"就走不同流程
6. **反向回退（隐藏第三类）**：如某 L3 跑完 ABC 才发现前面 L3 有 bug，开新 L3 修复，新 L3 同样走 ABC
7. **B 阶段 review 报告必须 commit + push 到 main 独立 commit**（不是 PR 分支；不是仅在 Codex 工作目录）—— L2 验收 first step = `gh api repos/.../contents/docs/reviews?ref=main` 验证报告物理位置；commit message 模板：`docs(review): T-X.X cross-LLM review report (B-phase output for PR #N)`。`/docs/REVIEW_PROMPT_CODE_GPT.md` v0.2 已在末尾加 explicit 段；Codex 评审完成后自动执行。

---

## 10.6 ABC 粒度跟随规划（v0.5 新增，ADR-037）

ABC 放在**最具体且有规划**的层级跑，不再一律钉死每个 L3。**仅适用工程/代码任务**；内容生成创作会话仍每单元一个新会话。

- **判定"算不算有独立规划"按实质**（是否有独立规格需求），**不以"有没有 prompt 文件"为唯一标准**——prompt 文件只是证据之一，防止"为攒批而故意不写 prompt 文件"绕过应有评审。下列一律视为有独立规格需求、必须单审：改 schema / 改 validator 语义 / 改共享函数行为 / 改生成器输出契约 / 迁移已有内容 / 需作者签字的决策（见 §10.7 软地基 carve-out）。
- **L3 有独立规格** → 在 L3 跑 ABC（现状）。
- **L2 有规划、底下若干子任务无独立规格需求** → 在 L2 跑**一次攒批 ABC**（一次 A→一次 B→一次 C→一次 L2 验收）。**B 保留（攒批，非跳过）。**
- **粒度由 L2 规划师规划时一次性决定**，执行中不重判；L2 计划的 cross-LLM critique 增一项粒度检查（切得对吗 / ≤8 吗 / 软地基拉出去了吗 / 集成评审安排了吗 / 模式标签对吗）。

**攒批护栏**：

1. **批量上限 ≤ 8 个子任务**；且软地基 carve-out 任一项触发、或跨多个核心模块、或需迁移老内容 → 不到 8 也拆。
2. **回滚单位 = 依赖闭包**（不声称"每子任务一个 commit 即可单独 revert"）：批计划写明子任务依赖图；若 T2 依赖 T1，回滚单位 = T1+T2。强依赖链超过 3 个子任务建议拆批。
3. **集成评审**：B 扇出（并行评审各子任务）时，至少一个评审者看整合后整批 diff。
4. **模式标签**：每批 / 每 PR 加一行——`mode = batch-ABC / skip-BC / L1-fixation` + B 是否保留 + 授权来源。

**依赖性不作一刀切约束**：普通环环相扣的活可攒批（返工由 AI 承担、不耗作者带宽）；唯"给别人定规矩"的活按 §10.7 前置。

**三模式区分**（由模式标签显式标注，便于审计）：

- **攒批 ABC**（本节）：一次 A→B→C→L2 验收，**B 保留**；用于一个 L2 计划下若干工程子任务。
- **跳 BC**（STAGE_3_TASKS §1.5.4）：A→直接 merge，**B 和 C 全丢**；用于反向修复 / ergonomic / 验收报告。
- **L1 直签 main fixation**（ADR-036 / `aeea12e` 先例）：作者直接把 L1 文档提交进 main，跳过 ABC；**仅用于已在外部完成决策的 L1 record keeping**，不是普通文档捷径。

---

## 10.7 设计先于施工 + 安全阀（v0.5 新增，ADR-037）

把"地基"改动挡在施工之前，从根上**降低**"在流动地基上施工"的频率（**注意：是大幅降频，不是结构性消除**——残余由本节安全阀 + 软地基 carve-out 承接）。

- **硬地基**（数据格式/schema、共享状态、L1 文档）→ 上提设计/规划层，用专门 schema-only ABC 先浇好，按 ADR-015 串行 commit 原则（v0.5 一般化为常驻规则）串行落定，先于依赖它的施工批。
- **软地基 carve-out**（§2 + §10.6）→ 改 validator 语义 / 共享函数行为 / 生成器输出契约 / 生成 trace 语义 / 迁移已有内容，同样前置单审。
- **foundation 子批不是 schema-only**：必须含保持 main 绿的最小 validator / model / fixture 适配。
- **安全阀 = 硬闸（不靠会话自觉）**：施工批**禁止触碰** `/schema`、`/docs/DECISIONS.md`、`/docs/governance.md`、共享 state 契约。施工批 diff 若出现这些路径或等价语义变更 → **B 阶段直接 🔴 + 停批** → 把地基改动上提回设计层 → 专门 ABC 浇好 → 再回来施工。
- **如实成本**：安全阀不便宜（全停 + 一个地基 ABC + 上下文切回）；触发频率取决于设计层预见质量。schema 的仪式因此被**集中强化**（自己的完整 ABC），不是削弱——把评审搬到风险最高处。

---

## 11. L3 prompt 文件化工作流（v0.4 新增）

> 阶段 3 起手期（2026-05-08 PR #33 merge 后）作者拍板：每个 L3 任务的 paste-ready prompt 单独存为文件，便于复盘 + 跨阶段对比 + 单文件修订。本节明文化 v0.4 工作流。
>
> **v0.2 目录定位 broaden（2026-06-08，作者授权）**：`/docs/prompts/` 已从「仅 L3 paste-ready prompt」扩为「项目所有 AI 生成提示词归档」（详 `/docs/prompts/README.md` v0.2）。**本 §11 工作流仅约束 `stage_N/` 下的 L3 任务 prompt**；根目录的 L1/治理类 prompt（如 `L1_KICKOFF_ABC_PROPOSAL.md`）不走本节的 T-N.X / STAGE_N_TASKS / ABC 流程。

### 目录结构

```
/docs/prompts/
├── README.md                    # 通用说明 + 命名规范 + L3 起步模板
├── stage_3/                     # 阶段 3 paste-ready prompts (14 个文件)
│   ├── T-3.0.md
│   ├── T-3.1.md
│   ├── ...
│   └── T-3.12.md
└── stage_4/                     # 阶段 4 起手时由 L2 整合规划师落地
```

### L3 会话起步标准格式（v0.4）

作者新会话首条消息（替代 v0.3 复制粘贴 paste-ready prompt 块）：

**最简版**：
```
执行 T-3.0
```

**明示版**（推荐；避免歧义）：
```
请按 /docs/prompts/stage_3/T-3.0.md 的指示执行任务。
```

会话识别后第一步 Read 对应 prompt 文件 → 按内容开发 + 测试 + commit + push + 开 PR → A 阶段完成。

### v0.3 → v0.4 工作流变化对照

| 项 | v0.3（2026-05-03 起）| v0.4（2026-05-08 起）|
|---|---|---|
| L3 paste-ready prompt 存放 | `STAGE_X_TASKS.md` §8 内嵌 ` ```text` 代码块 | 单独文件 `/docs/prompts/stage_N/T-N.X.md` |
| L3 会话起步首条消息 | 复制粘贴整块 ` ```text` 代码（~150 行）| `执行 T-N.X` 或 `请按 ... 执行任务。` |
| §8 在 STAGE_X_TASKS.md 内 | 14 个 ` ```text` 代码块（~1700 行）| 表格引用（~25 行）+ 链接到 `/docs/prompts/stage_N/T-N.X.md` |
| L3 prompt 修订 | Edit `STAGE_X_TASKS.md` §8 内对应段（污染大文件 git log）| Edit 对应 `/docs/prompts/stage_N/T-N.X.md` 单文件（git log 独立追踪）|

### 命名规范

- 阶段 N 任务编号：`T-N.X`（N = 阶段编号；X = 任务编号）
- 拆分子任务：`T-N.Xa` / `T-N.Xb`（如 T-3.6a / T-3.6b 拆审阅 UI MVP / integrations）
- 文件名：`T-N.X.md`（直接用任务编号）
- 路径：`/docs/prompts/stage_N/T-N.X.md`

### 历史阶段不回填

阶段 0 / 1 / 1.5 / 2 已完成；旧 paste-ready prompts 仍存在 `STAGE_X_TASKS.md` §8 ` ```text` 代码块内。**不回填**——历史阶段已 audit 完成；阶段 3 起新规范即可。

### 与 §10 ABC 三阶段闭环的关系

§10 ABC 流程**不变**——仅 A 阶段首条消息形态从"复制粘贴 prompt 块"改为"读 prompt 文件"。B/C/L2 验收阶段流程完全继承 v0.3。

### 与攒批 ABC 的兼容（v0.5 新增，ADR-037）

L2 规划师**可以**故意不为某批低风险工程子任务各拆 prompt 文件，而写**一个 batch-level 规格**（涵盖 ≤8 子任务）→ 该批走 §10.6 攒批 ABC。**"有没有自己的 prompt 文件 / 规格"是"算不算有独立规划"的证据之一，不是唯一标准**——§10.6 + §10.7 列的软地基 carve-out 类任务，无论有没有 prompt 文件，一律单审。

### 与跳 BC 破例 5 类的关系（详 STAGE_3_TASKS.md §1.5.4）

- prompt 文件本身的 ergonomic 微调（措辞 / 引用路径 / 示例补充）属"审阅 UI 工坊化 ergonomic 改进"延伸 → 跳 BC 破例第 4 类
- prompt 文件的实质性修订（任务范围 / 模块边界变化）默认走完整 ABC

### 修订流程

修订单个 prompt 文件：直接 Edit `/docs/prompts/stage_N/T-N.X.md` + 走 ABC 闭环（§10）。

prompt 文件 commit message 模板：

- `docs(prompt): T-N.X v1.1 — <修订要点>`（小修订）
- `docs(prompt): T-N.X v2.0 — <重写说明>`（大改）

### 阶段 4+ 复用

阶段 4 L2 整合规划师产 `STAGE_4_TASKS.md` 时，自动按 v0.4 规范落 prompt 文件到 `/docs/prompts/stage_4/`。`STAGE_4_TASKS.md` §8 直接用表格引用形态。

阶段 4 复用 [/docs/REVIEW_PROMPT_L2_STAGE_TASKS.md](../../REVIEW_PROMPT_L2_STAGE_TASKS.md) 模板跑 cross-LLM critique 时，可在 critique prompt 内补一句："本草稿同时检查 §8 paste-ready prompt 是否已按 v0.4 规范拆为 `/docs/prompts/stage_4/T-4.X.md` 文件"。

---

## 12. v0.4.1 patch（gap #2 + gap #3 修补；2026-05-08）

v0.5 完整 B/C prompt 文件化升级暂缓决策的 interim solution。

### gap #2 闭合（B 报告 push 到 main）

B 阶段 review 报告必须 commit + push 到 main 独立 commit（详 §10 第 7 条）；[/docs/REVIEW_PROMPT_CODE_GPT.md](../../REVIEW_PROMPT_CODE_GPT.md) v0.2 末尾"报告 push 到 main 独立 commit"段。

### gap #3 闭合（L2 视角拼进 B prompt 系统化）

L2 视角补 B prompt 上下文成为默认操作；[/docs/REVIEW_PROMPT_CODE_GPT.md](../../REVIEW_PROMPT_CODE_GPT.md) v0.2 `{{REVIEW_TARGET}}` 段加 explicit 提示。

### gap #1 不动（B/C prompt 文件化）

B/C 阶段 prompt 文件化 + L2 验收自动化仍属 v0.5 完整范围；暂缓决策保持。

### 触发

T-3.11 L2 验收（2026-05-08）第一次踩到 gap #2（B 报告全网 0 命中）+ gap #3（L2 视角拼进 prompt 非默认）。详 [2026-05-08_T-3.11_L2_acceptance.md](2026-05-08_T-3.11_L2_acceptance.md)。

### 不动

- §10 ABC 三阶段流程图 / §11 v0.4 prompt 文件化工作流（不动）
- /docs/STAGE_3_TASKS.md §1.5.1 → X8 留作者另起 L1 会话

### 默认行为（v0.4.1 起）

- B 阶段 Codex 评审完成后**自动执行** commit + push（REVIEW_PROMPT v0.2 末尾段已含命令）
- 作者填 `{{REVIEW_TARGET}}` 时**可附 L2 视角补充上下文**（如 L2 会话已起 + 给了 audit checklist）

---

## 版本

本文件版本：v0.5
最后更新：2026-06-08
