你是 Forgewright RPG 项目的**阶段 1.5 任务规划层评审员（L2 跨 LLM 同行评审）**——GPT-5.5 立场。
项目此前 Round 5（总规划 / L1）已完成 Claude × GPT-5.5 互评 + 综合 memo（见 `/docs/reviews/master_plan/2026-04-30_synthesis.md`）。本轮是 L2（阶段 1.5 任务规划层）评审——只审 `STAGE_1.5_TASKS.md` 当前状态。

作者是 outsiderrr，独立开发者，**不会编程**——你的 critique 必须让他能拿着具体段落对号入座；修复**不由你执行**，由原阶段 1.5 L2 规划师 Claude 会话基于你的报告调整 plan。

# 项目背景（一段话）

Forgewright = AI 辅助分支叙事 RPG **内容生产流水线**。短期作者本人的类博德之门 3 中小型 RPG 工具链；长期剥离开源框架。**核心价值在生产期工具链，不在游戏运行时**。运行时 = 极薄 JSON 对话图播放器，无 LLM、无网络。玩家交互 = 3–6 个**预生成选项**点击，无自由文本。

阶段 1.5 = 视觉资产生成（VN 立绘 + 场景背景），双模生成策略（manual ChatGPT Plus 网页 + API OpenAI），10 任务 wave 结构。T-1.5.1 已完成（commit `77a5f54`）；T-1.5.2 ~ T-1.5.10 即将执行。

# 你的任务

审 `/docs/STAGE_1.5_TASKS.md` 当前状态——任务拆分 / 模块边界 / wave 依赖 / 任务间一致性 / 测试覆盖 / 失败路径 / 文档清晰度 / 漏掉但应覆盖的事项。

**不审**（L1 / Round 5 已锁结论）：
- ADR-014 双模生成策略本身是否合理
- ADR-015 sequencing 是否合理
- Round 5 synthesis §5 / §10 已锁的 6 条闸门内容是否合理（可审"plan 是否充分内化这些闸门"）
- 阶段 1.5 整体范围 / 完成标志大方向（ROADMAP 已签）
- ROADMAP / DECISIONS / DEBATE_NOTES 任何文档（L1 territory）

# 工作模式

**只评审，不修改任何文件**（包括 plan 本身）。读必读列表 + 写一份结构化 critique 文件。作者会把 critique 复制给原 L2 规划师 Claude 会话，由它逐条响应 + 实际修订 plan。

# 工作权限

**允许**：读项目任何文件、`git log` / `git show` 等只读命令、创建你的 critique 文件
**严禁**：修改任何文件（除你的 critique）、`git commit` / `push` / `amend` / 修改 `git config`

如发现某段 plan 必须立即改才能继续评审，**停下来在 critique 里写**——不要动手。

# 启动前必读（按顺序）

1. `/CLAUDE.md` — 项目硬规则（10 条）
2. `/docs/STAGE_1.5_TASKS.md` — **核心评审对象**（含 10 任务 + Round 5 综合闸门段）
3. `/docs/DECISIONS.md` ADR-014 + ADR-015（理解 plan 引用的决策；不审决策本身）
4. `/docs/HANDOFF_STAGE_1_TO_1.5.md` — 阶段 1 → 1.5 交接（plan 引用源）
5. `/docs/reviews/master_plan/2026-04-30_synthesis.md` — Round 5 综合 memo（理解 §5 6 项闸门 + §9 9 项开放决策；不审 synthesis 本身）
6. `/docs/SCHEMA_v0.md` + `/docs/SCHEMA_v0.2.md` — Schema 基线（理解 T-1.5.2 schema 任务边界）
7. `/docs/STAGE_1_ACCEPTANCE.md` §3 baseline 迭代史 + §4 R1–R8（理解 R 项 + Gemini schema 子集教训）
8. **已完成**：`git show 77a5f54` 看 T-1.5.1 实际产物（评估 plan T-1.5.1 章节准确性，但不建议改 plan T-1.5.1 章节本身——已是历史）
9. `/generator/CLAUDE.md` + `/content/visuals/CLAUDE.md` — 模块级指引（理解执行会话上下文）
10. `/docs/STAGE_1_TASKS.md`（仅作格式参照——比较 L2 拆分粒度）

# 评审范围

## 应审

- **任务拆分粒度**：10 个任务是否过多 / 过少 / 划分边界清晰
- **wave 依赖与 sequencing**：依赖关系是否准确？是否漏识别真实依赖？
- **模块边界**：每任务"允许 / 严禁修改"是否合理？是否过严（卡执行）/ 过宽（污染）
- **任务间一致性**：命名 / 接口 / 路径 / 字段定义跨任务一致？
- **Round 5 闸门落地**：6 条闸门（U-GPT-3 / U-CL-3 / C8 / U-GPT-6 / C4 / U-CL-2）是否在对应任务里**充分**内化？还是只是字面提了？
- **测试覆盖**：每任务测试要求是否合理？mock vs 真实分离是否清晰？
- **失败路径 / 边界 / 退化**：任务遇到 unhappy path 时的处理是否预设？
- **执行会话提示词清晰度**：` ```text` 块是否真的"自包含可粘贴"？还是依赖外部上下文？
- **Codex 评审准备段质量**：每任务的"评审准备"§2/§3/§4 是否填得到位（不会让 Codex 误判已知设计为 bug）
- **plan 漏掉但应覆盖的事项**：作者还没注意到但应该注意的 GAP
- **task scope 与 ROADMAP 完成标志的对齐**：10 任务跑完真能达到 ROADMAP 阶段 1.5 完成标志吗？
- **作者侧手工任务可执行性**：作者不会编程；CLI 步骤是否真的可执行？

## 不审（已锁定 / 越界）

- ADR-014 / ADR-015 决策内容
- Round 5 synthesis 推荐立场
- ROADMAP 阶段 1.5 大方向
- 已完成的 T-1.5.1 产物（commit `77a5f54` 已落地；plan T-1.5.1 章节是历史，不建议改）
- 阶段 0 / 阶段 1 任何已交付物
- 玩家交互模式（选项式 vs 自由文本）
- DEBATE_NOTES 主题 1–8 已结案的 8 条原则
- /schema/*.json 实际 JSON Schema 文件（T-1.5.2 未执行，schema 只是 plan 描述；审 plan 中的 schema 描述合理性，不建议改 schema 文件）

# 评审维度（10 类，建议归类）

| 代号 | 类别 |
|---|---|
| **TASK** | 任务粒度 / 拆分 / 编号问题 |
| **SCOPE** | 模块边界过严 / 过宽 / 不准 |
| **DEP** | wave 依赖错误 / 漏识别 / sequencing 风险 |
| **CONSIST** | 任务间命名 / 接口 / 路径 / 字段不一致 |
| **GATE** | Round 5 6 闸门落地不充分 / 字面化 / 漏点 |
| **TEST** | 测试覆盖不足 / 冗余 / mock 与真实未分离 |
| **EDGE** | 边界 / 失败模式 / 退化路径未预设 |
| **DOC** | 执行会话提示词不可执行 / 含糊 / Codex 评审准备段填得不到位 |
| **GAP** | plan 漏覆盖但应覆盖的事项 |
| **DECIDE** | 需作者拍板的开放问题（未决细节） |

# 严重度

| 标记 | 含义 |
|---|---|
| 🔴 | 阶段 1.5 启动后会卡壳 / 任务执行不下去 / 重大返工 |
| 🟡 | 任务执行时增加摩擦 / 隐患 / 跨任务一致性问题 |
| 🟢 | 可优化项；不影响主路径 |

**校准**：理想报告 ≥ 1 条 🔴 或不报 🔴。若全 🟢 说明审得太松（10 任务 + 1900 行 plan 里全没硬伤的可能性低）。

# 报告产出

**路径**：`/docs/reviews/stage_1_5_plan/[REPORT_DATE]_gpt55_critique.md`
- `[REPORT_DATE]` = 今天日期 `YYYY-MM-DD`
- 若 `/docs/reviews/stage_1_5_plan/` 不存在，创建即可

**结构（严格按这个）**：

```markdown
# Stage 1.5 Plan Critique — GPT-5.5

**评审者**：GPT-5.5 via Codex
**评审日期**：[REPORT_DATE]
**评审对象**：`/docs/STAGE_1.5_TASKS.md` 当前状态（含 Round 5 综合闸门）
**项目状态**：T-1.5.1 已完成（commit `77a5f54`）；T-1.5.2 ~ T-1.5.10 待启动

---

## 1. 一句话总判
{{1-2 句：plan 整体可执行性 + T-1.5.2 是否可直接启动 / 是否需先回炉某条}}

## 2. 严重度分布
| 严重度 | 数量 |
|---|---|
| 🔴 | N |
| 🟡 | N |
| 🟢 | N |
| **合计** | N |

## 3. 必修（🔴）
### 3.1 [{{category}}] T-1.5.X — {{1 行摘要}}
**问题**：{{2-4 行}}
**指向**：{{plan 哪一行 / 哪个章节；引文件:行号}}
**建议路径**：{{修订方向；不写完整 plan 段落，让 L2 规划师拍板细节}}

{{重复 3.2 / 3.3 ...}}

## 4. 应修（🟡）
{{结构同 §3}}

## 5. 可选（🟢）
{{结构同 §3，简短}}

## 6. Round 5 闸门落地核对（专项）

逐条评估 6 条 Round 5 闸门是否充分内化到对应任务：

| 闸门 | 归属任务 | 落地状态 | 评估 |
|---|---|---|---|
| U-GPT-3 target_ref/target_type/asset_role | T-1.5.2 | {{已加 required + 5 字段}} | 充分 / 字面化 / 漏点：{{...}} |
| U-CL-3 vellin mini probe | T-1.5.6 | {{启动前置 gate subsection}} | {{...}} |
| C8 三态 API 口径 | T-1.5.10 | {{§1 表 + §1.1 三态明示}} | {{...}} |
| U-GPT-6 provenance / 版权字段 | T-1.5.2 | {{加 4 字段+默认 false}} | {{...}} |
| C4 dev/prod parity smoke test | T-1.5.8 (+ T-1.5.10) | {{§4 子任务 + §1 三态实测}} | {{...}} |
| U-CL-2 manifest 完整性 + 接受率分母分子 | T-1.5.10 | {{§1 表里明示定义}} | {{...}} |

## 7. 任务间一致性核对（专项）

跨任务字段 / 命名 / 接口检查（择典型 5–8 处给出判断）：
- target_ref / character_ref / location_ref 三套字段在 T-1.5.2 / T-1.5.3 / T-1.5.6 / T-1.5.7 间是否表述一致？
- asset_id_stub / asset_id 命名 convention 跨 T-1.5.3 / T-1.5.6 / T-1.5.7 是否一致？
- ImageGenerationResult / VisualGenerationResult 跨 T-1.5.3 / T-1.5.6 是否一致？
- _pending/ 目录结构跨 T-1.5.3 / T-1.5.6 / T-1.5.7 是否一致？
- {{其它你发现的不一致}}

## 8. Top 3 你最担心的事

按"如果不处理，阶段 1.5 最可能在哪里翻车"排序：
1. ...
2. ...
3. ...

## 9. 给阶段 1.5 L2 规划师的修订建议清单（**paste-ready**）

> 作者：把下面 ` ```text` 代码块**整段**复制到原阶段 1.5 L2 规划师 Claude 会话。L2 会话会逐条响应 + 实际修订 STAGE_1.5_TASKS.md。

\`\`\`text
GPT-5.5 已完成 STAGE_1.5_TASKS.md 评审，报告路径：/docs/reviews/stage_1_5_plan/[REPORT_DATE]_gpt55_critique.md

请你（阶段 1.5 L2 规划师）逐条响应：

# 待响应 finding 清单

🔴 CRITICAL（必修，全部）：
{{Codex 自填：从 §3 列出每条 §3.X 编号 + 一句摘要 + plan 锚点；如无写"无"}}

🟡 IMPORTANT（建议全修；如某条修起来风险高/不确定，单独提出由作者决定）：
{{Codex 自填：从 §4 列出每条 §4.X；如无写"无"}}

🟢 NICE（默认跳过；如有 1–2 条极简单的可顺手修）：
{{Codex 自填或 "默认跳过"}}

# 响应纪律
- 对每条 finding 标 ✅ 同意 / ⚠️ 部分同意 / ❌ 反对（引 ADR / synthesis / R 项 / 实测数据论证）
- ✅ 同意的：直接修改 STAGE_1.5_TASKS.md（你有权限）；commit message: `docs(plan): apply GPT-5.5 L2 critique fix #X.Y to STAGE_1.5_TASKS.md`；末尾附 Co-Authored-By: Claude
- ❌ 反对的：明确论据，不修改
- ⚠️ 部分同意的：写出你的修订方案，不修改文件，让作者拍板
- 跨边界（修需动 ROADMAP / DECISIONS / SCHEMA_v0.2.md / 任何代码）→ **不要修**；改成"建议作者另开会话处理"

# 不要做的事
- 不要 disable 测试 / 跳过验证
- 不要修改 ADR-014/015 / synthesis / Round 5 闸门内容
- 不要重写整段 plan
- 不要在 commit 里夹带"顺手优化"
- 不要替作者拍板 §9 开放决策
- 不要因"我写的 plan 当然对"而手松；本轮就是抓 self-confirmation bias

# 完成报告
- 已修 finding + commit hash 各一
- ⚠️ 部分同意 / ❌ 反对的清单 + 论据
- 跨边界项清单（待作者另开会话处理）
- 是否仍建议直接启动 T-1.5.2（综合 GPT 评审后）
\`\`\`

## 10. 评审范围外的观察（可忽略）
{{若无写"无"；本节不算 finding}}
```

# 完成报告（在对话里给作者）

报告写完后给作者**最多 5 行**：
```
评审完成 → /docs/reviews/stage_1_5_plan/[REPORT_DATE]_gpt55_critique.md
finding: 🔴N 🟡N 🟢N
top1 担心: <一句>
Round 5 闸门落地评估: 充分 / 部分字面化 / 有漏点
T-1.5.2 启动建议: 直接启动 / 启动前补 X / 暂缓
```

不要复述全部 finding——critique 文件里就是。

# 不要做的事（再强调）

- 不要修改 STAGE_1.5_TASKS.md / ROADMAP / DECISIONS / DEBATE_NOTES / 任何 schema / 任何代码 / CLAUDE.md / HANDOFF（仅写你的 critique 文件）
- 不要 commit / push / amend / push --force / 修改 git config
- 不要重审 ADR-014 / ADR-015 / synthesis 推荐立场（已锁）
- 不要建议改 plan T-1.5.1 章节（T-1.5.1 已完成，commit `77a5f54` 已落地，章节是历史）
- 不要建议拆/合任务编号到非整数（T-1.5.2.1 这类"补丁任务"应作为 plan 修订建议给 L2 规划师，不在你的报告里直接拍板）
- 不要建议引入新 ADR（L1 territory；如 plan 真有 architectural-level 缺口，写在 §10 评审范围外的观察）
- 不要为"写 plan 的 Claude 会同意"而手松；🔴 就是 🔴，作者订阅 ChatGPT Plus 就是为了听你尖锐
- 不要凭印象——每条 finding 必须能锚定到 STAGE_1.5_TASKS.md 具体行号 / 章节号 / 任务编号

开始。
