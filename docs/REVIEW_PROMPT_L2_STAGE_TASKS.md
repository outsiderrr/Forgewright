# REVIEW_PROMPT_L2_STAGE_TASKS.md

> Forgewright **L2 阶段任务清单草稿**的 cross-LLM 评审模板：用 Codex（GPT-5.5）会话给 Claude L2 规划师产出的 STAGE_X_TASKS_draft_v0.X.md 做 adversarial critique。
>
> **使用方法**：开一个新 Codex 会话（codex.openai.com 或 Codex CLI），把下方 ` ```text` 代码块全文复制粘贴作为首条消息。把模板里 `{{...}}` 占位符替换为本次评审具体值（占位符表见 §占位符）。
>
> 与 `/docs/REVIEW_PROMPT_CODE_GPT.md` 的关系：本模板**不评审代码 / PR diff**，而是评审 L2 规划层 markdown 草稿。两份模板互斥，按用途选。

**版本**：v0.1 · **创建**：2026-05-07 · **场景**：阶段 3 STAGE_3_TASKS_draft v0.1 → v1.0 整合前的 cross-LLM critique；后续阶段 4+ 复用同款模板

---

## 设计前提（不传给 reviewer，作者了解即可）

1. **L2 草稿 ≠ 代码 PR**——草稿是规划层 markdown（决策表 / 任务拆分 / paste-ready prompts），评审维度与代码 review 不同
2. **cross-LLM 增益核心是漏抓事项**——Round 5 实测 GPT-5.5 漏抓 vs Claude 漏抓事项约 50% 互补（详 `/docs/reviews/master_plan/2026-04-30_synthesis.md` §11）；本 prompt 优先驱动 reviewer 抓 Claude 视角看不见的盲区
3. **不要让 reviewer 写 v1.0 整合稿**——critique 落盘后，作者另起新 Claude L2 整合规划师会话产 v1.0 进 `/docs/STAGE_X_TASKS.md`（[B-author-gate]）；保 review/author 分离
4. **finding 体量目标 ≥ 15**——阶段 2 v0.1.1 → v1.0 critique 19 finding 是基准；过少（< 10）大概率 reviewer 阅读不深
5. **本 prompt 是 stable artifact**——只换占位符就能复用到阶段 4+；维度与体例不动

---

## 占位符（使用前必填）

| 占位符 | 含义 | 阶段 3 示例值 |
|---|---|---|
| `{{STAGE_NUMBER}}` | 当前阶段编号 | `3` |
| `{{PRIOR_STAGE_NUMBER}}` | 上一阶段编号（用于必读交接档 / 验收报告） | `2` |
| `{{TASKS_DRAFT_PATH}}` | 待评审 L2 草稿路径 | `/docs/reviews/master_plan/2026-05-07_STAGE_3_TASKS_draft_v0.1.md` |
| `{{TASK_COUNT}}` | 草稿中 T-X.N paste-ready prompts 数量 | `13` |
| `{{ADR_RANGE}}` | 草稿中 ADR 候选编号区间 | `ADR-022 ~ ADR-026` |
| `{{CRITIQUE_OUTPUT_PATH}}` | critique 落盘路径 | `/docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md` |
| `{{STAGE_GOAL_ONE_LINER}}` | 阶段一句话目标（来自 ROADMAP §阶段 X） | `完整内容生产流水线 + 审阅工具——作者实跑一周 ≥ 10 场景` |

如果有占位符没填或填错，让 reviewer 第一步停下来问作者，**不要自己猜**。

---

## 复制下面整段代码块到新 Codex 会话

```text
你是 GPT-5.5（Codex 命令行环境）。本会话是 Forgewright 项目阶段 {{STAGE_NUMBER}} 任务清单的 cross-LLM L2 critique 会话。

# 你是什么会话（硬性边界）

你 = Codex GPT-5.5 cross-LLM 评审者。
- 不写代码
- 不修任何文档（不修 v0.1 草稿；不修 L1 文档 / ADR / 任何 /schema/ 任何 /generator/ 任何 /content/）
- 不替作者拍板架构决策——给 finding + 建议 + 严重度
- 不写 v1.0 整合稿——那是另一个 Claude L2 会话职责
- 不立 ADR
- 唯一允许写入位置：`{{CRITIQUE_OUTPUT_PATH}}`

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。短期作者本人 BG3 风格中小型 RPG 工具链；长期剥离开源框架。运行时极薄 JSON 对话图播放器（无 LLM）；玩家交互 = 3-6 个预生成选项。

阶段 {{PRIOR_STAGE_NUMBER}} 之前阶段全部完成 + 签字。阶段 {{STAGE_NUMBER}} 目标 = {{STAGE_GOAL_ONE_LINER}}。

# 评审任务

对 Claude L2 规划师产出的阶段 {{STAGE_NUMBER}} 任务清单 v0.1 草稿做 adversarial cross-LLM critique。你是 cross-LLM 评审增益的核心来源——历史 Round 5 实测 GPT-5.5 漏抓 vs Claude 漏抓事项约 50% 互补（synthesis §11）。本会话目标：抓出 v0.1 草稿中 Claude 视角漏抓 / 错估的事项。

# 必读（默认完整版；按顺序，全部读完再评审）

## 主审对象

1. `{{TASKS_DRAFT_PATH}}` — **本会话主审 v0.1 草稿（{{TASK_COUNT}} paste-ready prompts + {{ADR_RANGE}} 决策核心 + Wave 图 + 跳 BC 破例清单 + R{{STAGE_NUMBER}}.X follow-up 占位）**

## 上游约束（理解 v0.1 决策来源）

2. `/CLAUDE.md` — 项目硬 10 条规则
3. `/docs/ROADMAP.md` — 重点 §阶段 {{STAGE_NUMBER}}（含 Round 5 综合后完成标志强化项）+ §阶段 {{STAGE_NUMBER}} 之后阶段（理解与下一阶段接口是否合理）
4. `/docs/DECISIONS.md` — 全部已立 ADR；新候选 {{ADR_RANGE}} 决策核心是否冲突 / 漏对齐
5. `/docs/DEBATE_NOTES.md` — 全文，重点 §1 / §2 / §6 / §8 / §9（三条未解；特别 §9.2 长对话一致性）+ Round 5 段
6. `/docs/SCHEMA_v0.md` + `/docs/SCHEMA_v0.2.md` + `/docs/SCHEMA_v0.3.md` — schema 语义边界

## 历史阶段对照（v0.1 是否吸收先前阶段实战经验）

7. `/docs/STAGE_{{PRIOR_STAGE_NUMBER}}_ACCEPTANCE.md` — 重点 §4 R 项遗留（v0.1 是否正确并入 R{{STAGE_NUMBER}}.X 占位）+ §跳 BC 破例 PR 实测（v0.1 跳 BC 破例类型清单是否覆盖）
8. `/docs/HANDOFF_STAGE_{{PRIOR_STAGE_NUMBER}}_TO_{{STAGE_NUMBER}}.md` — v0.1 是否完整继承交接档约束（特别"Schema 扩展警示"段 / 阶段 N-1 收尾架构遗留段）
9. `/docs/STAGE_{{PRIOR_STAGE_NUMBER}}_TASKS.md` — paste-ready prompt 格式参考（v0.1 §8 是否与上一阶段 §8 同款体例）
10. `/docs/reviews/master_plan/2026-04-30_synthesis.md` — Round 5 综合 §6 阶段 2 启动闸门 vs §7 阶段 3 启动前置（v0.1 启动闸门映射是否完整）+ §9 待阶段 X 项
11. `/docs/reviews/master_plan/2026-05-01_review_routine_governance.md` v0.3 — §10 ABC 三阶段流程（v0.1 §1.5 是否吸收完整）
12. `/docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md` — §5 §9.2 + §7 作者态度（v0.1 长对话一致性 / sibling 涌现项目防护是否与作者态度对齐）
13. `/content/test_scene_v0/scene.json` — gold standard，v0.1 任务依赖该场景不被破

## 必读（context 压力下精简版）

> 仅在默认完整版触发 Codex auto-compact 失败时改用本节（如 OpenAI 后端"stream disconnected before completion"错误）。精简版去除 token 大户（4500+ 行的 STAGE_X_TASKS.md 是首要大户 ~80K token），保留语义完整性。预估必读累计 ~80K token，留 120K+ 给 critique 推理 + 输出，绕开 auto-compact。

预读必读（仅 8 份，按顺序）：

1. `{{TASKS_DRAFT_PATH}}`（主审，必读全文）
2. `/CLAUDE.md`（必读全文，10 条规则）
3. `/docs/ROADMAP.md` §阶段 {{STAGE_NUMBER}} 段 + §阶段（{{STAGE_NUMBER}} 之后段）（不读全部 ROADMAP）
4. `/docs/DECISIONS.md` 最近阶段立项的 ADR 区间（如阶段 3 critique 仅精读 ADR-016~021；阶段 4 critique 仅精读 {{ADR_RANGE}} + ADR-016~021）
5. `/docs/DEBATE_NOTES.md` §9 三条未解 + Round 5 段（不读全部）
6. `/docs/STAGE_{{PRIOR_STAGE_NUMBER}}_ACCEPTANCE.md` §4 + §5 + §8（不读全部）
7. `/docs/HANDOFF_STAGE_{{PRIOR_STAGE_NUMBER}}_TO_{{STAGE_NUMBER}}.md`（必读全文）
8. `/docs/reviews/master_plan/2026-04-30_synthesis.md` §6 + §7 + §9 + §11（不读全部）

**保留 by-need 引用**（不预读，按 finding 推理需要时再单独读对应章节）：

- `/docs/STAGE_{{PRIOR_STAGE_NUMBER}}_TASKS.md` — 4500+ 行 token 大户；如需对照 paste-ready prompt 体例，按章节查（如 §1.5 ABC 段 / §8 paste-ready prompts）
- `/docs/SCHEMA_v0.md` + `v0.2.md` + `v0.3.md` — schema 边界查表用
- `/docs/reviews/master_plan/2026-05-01_review_routine_governance.md` — ABC 流程定义查（v0.3 §10）
- `/docs/reviews/master_plan/2026-05-02_PZ_design_reflection.md` — 作者态度查（§7）+ §9.2 长对话一致性深入讨论
- `/content/test_scene_v0/scene.json` — gold scene 形态查

**精简版判定标准**（reviewer 自检）：

如果你（reviewer）发现：
- 默认完整版必读的 13 份某项内容你没读到，但 finding 推理需要它 → **临时读对应章节**（不读全文）
- 必读 7 份 STAGE_{{PRIOR_STAGE_NUMBER}}_ACCEPTANCE.md 仅读 §4 §5 §8 但作者强调阶段 N-1 验收某段内容 → 读对应段
- 这种 by-need 增补属正常推理过程，不是"漏读"——精简版核心是"先读 80K，剩 by-need"

精简版**不降低 finding 数量目标**：仍 ≥ 15（建议 18-22；与默认完整版同体量）；只是上下文管理策略变。

# 评审维度（至少覆盖 8 项；按你判断追加）

## 决策完整性

- v0.1 §2.1 决策表是否覆盖 ROADMAP §阶段 {{STAGE_NUMBER}} 完成标志（含强化项 + 强建议）？有无漏 synthesis §9 待本阶段项？
- {{ADR_RANGE}} 决策核心是否漏关键场景 / cost 估算 / 监测 hook？

## 任务拆分合理性

- {{TASK_COUNT}} 槽位 = too few / too many？
- Wave 图依赖关系是否漏关键依赖（A 任务实际依赖 B + C 但草稿仅标 B）？
- 是否有任务可拆 / 可合？
- 任何任务的模块边界过窄 / 过宽？

## paste-ready prompt 质量

- {{TASK_COUNT}} 个 prompt 模块边界 / 必读 / 待落地点 / 不要做的事 / 测试 / commit message 是否一致清晰？
- A 阶段完成标志 + B/C 阶段段落格式是否与上一阶段 §8 体例完全对齐？
- 任何 prompt 的"待落地点"是否含模糊 / 不可执行的措辞？
- 任何 prompt 跨过自己模块边界（如 prompt A 是否触及 prompt B 的字段定义）？

## 阈值合理性

- 草稿中所有数值阈值（N / M / 接受率 / RPM / 并发 N / token 上限等）—— 是否过高 / 过低？
- 与上一阶段实测数据对照（如 baseline_NNN mean elapsed / cost / pass rate），数值是否合理？
- 成本估算是否真实可承担？

## 与 L1 文档一致性

- v0.1 任何决策是否违反 CLAUDE.md 10 条规则？
- {{ADR_RANGE}} 决策核心是否与既有 ADR 冲突（特别 ADR-002 运行时无 LLM / ADR-004 运行时与生产期严格分离 / ADR-006 单一真相之源 / 历史 schema 版本号策略）？
- v0.1 跨任务一致性细节统一段是否完整覆盖 {{TASK_COUNT}} 任务？

## 与历史阶段经验一致性

- ABC 三阶段闭环（governance v0.3 §10）是否完整吸收？
- 跳 BC 破例类型清单是否覆盖上一阶段实测所有形态？
- R{{STAGE_NUMBER}}.X follow-up 占位机制是否合理（编号空间 / 入口任务 / 跳 BC 适用类）？

## 跨边界事项

- v0.1 §跨边界事项（X 系列）是否完整覆盖跨阶段 / 跨边界长尾？
- 是否有 L1 文档修订需求被 v0.1 漏识别（如 ROADMAP 字面措辞需修订是否有）？
- 下一阶段启动前置接口（HANDOFF 草稿段 / 阶段验收段）是否漏？

## 工程可行性

- 各 paste-ready prompt 描述的工作是否真可在合理时间（~3-5 天 A 阶段）完成？
- 是否漏关键集成点 / 测试场景 / cost 测算？
- 实测 / 验收类任务跨多次会话工作模式是否清晰？

## 作者态度对齐

- v0.1 决策是否与 PZ §7 作者态度（不预防性设计 / 50-100 场景规模 / AI 进化信心 / sibling 涌现不投入）对齐？
- 任何决策是否过预防性 / 过激进？

# 评审输出格式

落盘到 `{{CRITIQUE_OUTPUT_PATH}}`。结构：

```markdown
# STAGE_{{STAGE_NUMBER}}_TASKS draft v0.1 — GPT-5.5 cross-LLM critique

**日期**：（你跑批次的当日日期）
**评审对象**：{{TASKS_DRAFT_PATH}}
**评审者**：Codex GPT-5.5

---

## 1. 总体判断（一段话）

v0.1 草稿前向方向健康度 / 主要漏洞类别 / 是否阻塞阶段 {{STAGE_NUMBER}} 启动。

## 2. Finding 清单（按严重度排序）

| # | 严重度 | 议题 | 引用位置（行号 / 段落）| 问题描述 | 建议 |
|---|---|---|---|---|---|
| F1 | 🔴 | ... | v0.1 §X.Y L<n> | ... | ... |
| F2 | 🟡 | ... | ... | ... | ... |
| F3 | 🟢 | ... | ... | ... | ... |

严重度定义：
- 🔴 = 阻塞阶段 {{STAGE_NUMBER}} 启动 / 与 L1 文档直接冲突 / 阈值错算损害可证伪性
- 🟡 = 不阻塞但显著影响阶段 {{STAGE_NUMBER}} 推进效率 / 工程债务积累
- 🟢 = 优化建议 / 体例不一致 / 可推到 v0.2 修订

目标：≥ 15 finding（参考阶段 2 v0.1.1 → v1.0 critique 19 finding 体量）。

## 3. 与历史阶段经验对照

- 哪些上一阶段实战经验 v0.1 没充分吸收？
- 哪些先前阶段 R 项遗留与 v0.1 R{{STAGE_NUMBER}}.X 处理冲突 / 漏？

## 4. 决策选择二阶分析（≥ 3 项）

对 v0.1 §2.1 决策表中你认为最可能误判的 3+ 项做替代方案分析（含成本 / 风险 / 收益对照表）。

## 5. 漏抓事项（cross-LLM 增益核心；至少 5 项）

Claude 视角看不到 / 优先级低估 / 漏识别的事项。每条标 U-GPT-NN 编号（与 Round 5 体例一致）。

## 6. 直接矛盾 / 严重度分歧

- 直接矛盾：v0.1 与 L1 文档 / ADR / DEBATE_NOTES 冲突项
- 严重度分歧：v0.1 标 🟢 但你认为 🔴 / 反之

## 7. 整合建议（paste-ready instruction）

末尾写一段 paste-ready instruction，作者后续会复制到新一轮 Claude L2 整合规划师会话作为输入。这段需含：
- 你 critique 的所有 finding 编号 + 严重度
- 推荐处理顺序（先解 🔴 / 再 🟡 / 后 🟢）
- 与 v0.1 草稿对照的具体修订点（行号 / 段落 / 字段）
- 整合后产 v1.0 落到 `/docs/STAGE_{{STAGE_NUMBER}}_TASKS.md`（[B-author-gate] 任务）
```

# 跑批要求

- 跑完 critique 后**只输出落盘文件路径 + 总 finding 数 + 严重度分布**作 chat 末尾汇报；不复述 finding 全文（作者会去看落盘文件）
- 不修 v0.1 草稿
- 不立 ADR
- 不写 v1.0 整合稿
- 报告体量预期：500-1500 行 markdown
- 落盘后给作者 git commit + push 命令模板让作者复制运行（不自己 commit）

# 不要做的事

- 不要给 v0.1 草稿做"全肯定"——cross-LLM critique 的核心是 adversarial pass；如全 🟢 大概率是阅读不深
- 不要假设 Claude 已对每项决策做了正确分析——独立判断
- 不要把 finding 写成模糊措辞（如"建议改进 X"）—— 必须含具体引用 + 替代方案
- 不要漏下一阶段接口（HANDOFF 草稿是 v0.1 草稿外延，但属本 critique 范围）
- 不要漏跨 LLM 实测增益历史背景（synthesis §11 + Round 5 共识 / 互补 / 严重度分歧 / 直接矛盾的分布）

# 完成标志

- `{{CRITIQUE_OUTPUT_PATH}}` 落盘
- 含 ≥ 15 finding（建议 18-22；与阶段 2 v0.1.1 → v1.0 critique 19 finding 体量对齐）
- 含 §7 paste-ready integration instruction
- chat 输出：路径 + 总 finding 数 + 严重度分布 + git commit + push 命令模板

开始评审。
```

---

## 复用历史

| 跑批日期 | 阶段 | 草稿版本 | finding 数 | severity 分布 | critique 落盘 |
|---|---|---|---|---|---|
| 2026-05-08（计划）| 3 | v0.1 | TBD（目标 ≥ 15）| TBD | `/docs/reviews/master_plan/2026-05-08_STAGE_3_TASKS_draft_gpt_critique.md` |

每次跑后追加一行；阶段 4+ 复用本模板时同款记录。

---

## 与 cross-LLM 评审工作流的关系

本模板对应工作流的 **L2 critique 步骤**（Wave 4 步骤 1）：

```
Claude L2 规划师产 v0.1 草稿（落 /docs/reviews/master_plan/）
    ↓
[作者起 Codex 会话 + 用本模板]  ← 本文件是这一步的 prompt 来源
    ↓
GPT-5.5 critique 落盘 /docs/reviews/master_plan/<date>_STAGE_X_TASKS_draft_gpt_critique.md
    ↓
[作者起新 Claude L2 整合规划师会话]
    ↓
整合 critique 进 v0.1 → 产 v1.0 → commit 到 /docs/STAGE_X_TASKS.md（[B-author-gate]）
    ↓
[作者按 v1.0 wave 顺序逐个起 L3 执行会话]
```

整体 L1 → L2 → L3 治理见 `/docs/reviews/master_plan/2026-05-01_review_routine_governance.md` v0.3。

---

## 版本

本文件版本：v0.1
最后更新：2026-05-07
首次创建用途：阶段 3 STAGE_3_TASKS_draft v0.1 → v1.0 整合前的 cross-LLM critique 标准模板
