你的任务是把 Round 5 总规划评审（Claude × GPT-5.5）的**已锁结论**落地到 L1 文档。
作者已通过 2026-04-30 阶段 1.5 规划师会话（本对话之前）明确授权本会话修改 `DECISIONS.md` / `DEBATE_NOTES.md` / `ROADMAP.md` / `HANDOFF_STAGE_1_TO_2.md`（CLAUDE.md 规则 9/10 例外）。

本会话定位：**L1 实施会话**——只把综合 memo 中**真正已锁**的决策落地到 L1 文档；**绝不替作者拍板**任何 synthesis §9 标为"开放决策"的项。把开放决策原样登记到 `DEBATE_NOTES.md` Round 5 段落，留给阶段 2 规划师 / 作者后续处理。

# 模块边界（硬性）

允许修改 / 新建：
  - `/docs/DECISIONS.md`（新增 ADR-015；不动既有 ADR-001~014）
  - `/docs/ROADMAP.md`（更新阶段 2/3 重点工作 + 更新记录；阶段概览总估算**不动**——C7 仍在 §9 开放决策中）
  - `/docs/DEBATE_NOTES.md`（追加 Round 5 段落 + 综合开放决策清单 subsection）
  - `/docs/HANDOFF_STAGE_1_TO_2.md`（U-GPT-2 修过期叙述）

严禁修改：
  - `/CLAUDE.md`（规则 9）
  - `/docs/SCHEMA_v0.md` / `/docs/SCHEMA_v0.2.md`（Schema territory；阶段 2 规划师管）
  - `/docs/STAGE_*_ACCEPTANCE.md`（已签字）
  - `/docs/STAGE_*_TASKS.md`（L2 territory；阶段 1.5 规划师在另一会话处理）
  - `/docs/HANDOFF_STAGE_1_TO_1.5.md`（L2 territory）
  - 任何代码（`/generator/`、`/engine/`、`/state/`、`/validator/`）
  - 任何 `/schema/*.json`
  - `/content/`（除 `/docs/reviews/` 下你自己产出的 commit message / push 确认外）
  - **既有 ADR-001 ~ ADR-014**（只允许新增 ADR-015；不允许编辑 / supersede 既有 ADR——任何"修订既有 ADR"提议必须改成"新增 ADR-016+ 给阶段 2 规划师拍板"）

# 启动前必读（按顺序）

1. `/CLAUDE.md` — 规则 9/10 + 阶段 1.5 路径 C 例外背景
2. `/docs/reviews/master_plan/2026-04-30_synthesis.md` — **核心输入**（综合 memo，188 行）
3. `/docs/reviews/master_plan/2026-04-30_claude_critique.md` — Claude 上轮 critique（论据回查）
4. `/docs/reviews/master_plan/2026-04-30_gpt55_critique.md` — GPT-5.5 上轮 critique（论据回查）
5. `/docs/ROADMAP.md` — 当前路线图全文
6. `/docs/DECISIONS.md` — 既有 14 条 ADR（理解格式 + 编号顺序）
7. `/docs/DEBATE_NOTES.md` — 既有 4 轮辩论结案（理解 Round 5 段落应承接的语气）
8. `/docs/HANDOFF_STAGE_1_TO_2.md` — 待修文档（U-GPT-2）
9. `/docs/STAGE_1_ACCEPTANCE.md` §4 R1–R8 — 理解共识 C3 "R 项 cleanup gate" 实质
10. `/docs/STAGE_1.5_TASKS.md` —— **只读** 看一眼了解 L2 plan 长什么样；本会话**不改它**

# 待做（4 项任务，建议按顺序）

## 任务 1：新增 ADR-015（DECISIONS.md）

**唯一新增 ADR**——其它综合 §6/§7 的"立项候选"全部留给阶段 2 规划师，**本会话不立**。

### ADR-015：阶段 1.5 与阶段 2 sequencing — 1.5 主线先启动 / 阶段 2 schema 可并行起草 / commit 串行

格式参照 ADR-011/012/013/014（背景 / 决策 / 替代方案及否决理由 / 后果 / 状态），含：

**状态**：已接受（2026-04-30）

**背景**：综合 §10 + §9.1 关闭了 1.5 与阶段 2 启动顺序问题。ADR-014 manual 模式消除了 1.5 资金阻塞后，1.5 与阶段 2 的相对启动顺序变得不明确——原 `HANDOFF_STAGE_1_TO_2.md` 仍写"1.5 已推迟"过期叙述（U-GPT-2）。同时阶段 2 启动需要一系列前置工作（本体最小契约 / R 项 cleanup gate / baseline 协议——见 synthesis §6），这些可在 1.5 进行期间并行起草，但实际 commit 应等 1.5 验收以避免 Schema 漂移。

**决策**：
- **阶段 1.5 manual 主线先启动**——manual 路径不依赖 OpenAI key，可立即开跑
- **阶段 2 本体 / 角色槽位 schema 设计可并行起草**——规划层文档（草拟 ADR / 范围讨论 / 任务拆分）不阻塞 1.5
- **阶段 2 任何 schema 文件实际 commit 等 1.5 验收后**——遵守阶段 0/1.5 串行卡口先例（schema 变更串行）
- **阶段 2 启动具体闸门清单**（本体最小契约范围 / R 项处理 / baseline 协议 / 角色槽位持久化形态等）由阶段 2 规划师基于 synthesis §6 + §9 开放决策落地，**本 ADR 不替它拍板**

**替代方案及否决理由**：
- 1.5 与 2 串行（必须 1.5 验收后才能起草 stage 2 schema）：浪费 1.5 期间的规划带宽
- 1.5 与 2 完全并行（schema 实际 commit 也并行）：违反 ADR-006 + 阶段 0/1.5 串行卡口先例；schema 漂移风险高

**后果**：
- 阶段 2 规划师可在阶段 1.5 启动后立刻开始（写 ADR 草拟 / synthesis §6 闸门细化）
- 阶段 2 任何 commit 进 /schema/* 必须验证阶段 1.5 已签字
- Round 5 synthesis §9 开放决策清单（9 项）大部分由阶段 2 规划师承担拍板

**变更历史追加**（在 DECISIONS.md 末尾的"变更历史"段）：
- 2026-04-30：作者授权新增 ADR-015（Round 5 综合后第一条已锁结论），属 CLAUDE.md 规则 10 的明示例外。

## 任务 2：修 HANDOFF_STAGE_1_TO_2.md（U-GPT-2）

读全文（173 行）→ 找"1.5 已推迟" / "1.5 deferred" / 类似过期叙述 → 改写：

- 删除"1.5 已推迟"语义
- 改写为："1.5 已通过 ADR-014 双模生成策略（manual 主线 + API 后置）解除资金阻塞，按 ADR-015 sequencing 与阶段 2 并行（1.5 实施在前，2 schema 起草并行，2 commit 串行）"
- 引 ADR-014 + ADR-015 + synthesis 路径
- 不删 HANDOFF 任何**仍有效**的内容（例如阶段 1 → 2 的产物清单 / 评测分层指引）；只局部澄清 sequencing
- 顶部 "**日期**" / "**版本**" 升 v0.2 + 注明本次修订原因

## 任务 3：ROADMAP.md 局部更新

**不要重写整段路线图**。只做 3 处局部增量：

### 3a. 阶段 2 段（在"重点工作"小节后追加一个新小节）

新增子小节 "**启动闸门（Round 5 综合后）**"，列出 synthesis §6 的 5 项硬闸门 + 2 项强建议**作为占位指针**——不替阶段 2 规划师细化：

- C1：本体最小可生成契约（character / location / relation / state path 边界 schema）— 待 ADR-016 立项 by 阶段 2 规划师
- C3：R 项（R2/R3/R4/R8）作为阶段 2 启动 cleanup gate
- U-GPT-1：ADR-009 第二层方法论拆 2A 拓扑 + 2B 抽样验证 — 待 ADR-016+ 立项
- U-GPT-4：阶段 2 baseline 协议（样本数 / 重试 / 判官权重 / 接受口径）
- U-GPT-5：角色槽位持久化形态决策（推荐：持久化 concrete refs；抽象槽作为 generator 中间产物）
- U-CL-4（强建议）：Chapter/Act schema 前移到阶段 2 起手期
- C5（强建议）：开源剥离边界清单从阶段 2/3 起维护

每条加一行简短描述 + 指向 `/docs/reviews/master_plan/2026-04-30_synthesis.md §6`。

### 3b. 阶段 3 段（在"重点工作"小节后追加一个新小节）

新增子小节 "**完成标志强化项（Round 5 综合后）**"，列出 synthesis §7：

- C2：ADR-009 第三层 playtest bots 写入完成标志
- C6：内容依赖索引（content_dependency_index sidecar）
- U-CL-1：完成标志加质量门槛指标（X% 接受率 / Y 场景吞吐 — 具体数字待阶段 3 规划师拍板）
- U-CL-5：长对话一致性缓解策略（DEBATE §9.2 未解问题）
- U-GPT-7（建议）：审阅 UI 第一版含图视图

每条加一行 + 指向 synthesis §7。

### 3c. 更新记录段（在文件末尾）

追加一行：
- 2026-04-30：Round 5 总规划综合评审完成（Claude × GPT-5.5）；ADR-015 立项；ROADMAP 阶段 2/3 启动闸门 + 完成标志强化项占位增订；详见 `/docs/DEBATE_NOTES.md` Round 5 段落

**不动**：阶段概览总估算（C7 时长拆估在 §9 开放决策中，阶段 4 处理）；阶段 1.5 段（L2 会话处理 startup gates）；阶段 0/1 任何内容。

## 任务 4：DEBATE_NOTES.md 追加 Round 5 段落

在文件结尾"## 版本"段**之前**追加新段落 "## Round 5：Claude × GPT-5.5（2026-04-30）"，结构：

```markdown
## Round 5：Claude × GPT-5.5（2026-04-30）

> 前 4 轮均为 Claude × Gemini。Round 5 是 Claude × GPT-5.5 第一次交手——双方独立 critique 同一份路线图，作者综合后产出锁定 + 开放决策清单。完整记录在 `/docs/reviews/master_plan/`：
> - [`2026-04-30_claude_critique.md`](reviews/master_plan/2026-04-30_claude_critique.md) — Claude (cold-start)
> - [`2026-04-30_gpt55_critique.md`](reviews/master_plan/2026-04-30_gpt55_critique.md) — GPT-5.5 via Codex
> - [`2026-04-30_round2_claude_response.md`](reviews/master_plan/2026-04-30_round2_claude_response.md) — Claude 应答 GPT
> - [`2026-04-30_synthesis.md`](reviews/master_plan/2026-04-30_synthesis.md) — 综合 memo

### 共识 8 条（双方独立得出相同结论 — 高 confidence）

简介每条 + 当前状态（已落地 / 待阶段 X 处理）：

- **C1** 阶段 2 启动前需"本体最小可生成契约"（角色 / 地点 / 关系 / 状态路径事实卡）→ 阶段 2 启动闸门，待阶段 2 规划师拍板范围 + 立 ADR
- **C2** ADR-009 第三层 playtest bots 写入阶段 3 完成标志 → 待阶段 3 规划师
- **C3** R 项升级为阶段 2 启动 cleanup gate（R2/R3/R4/R8）→ 待阶段 2 规划师
- **C4** dev/prod prompt 同源是假设不是事实，1.5 验收前跑 3 条 prompt smoke test → 阶段 1.5 软闸门，由 L2 规划师纳入 STAGE_1.5_TASKS.md
- **C5** 开源剥离边界 hook 从阶段 2/3 起维护清单 → 待阶段 2 规划师建立机制
- **C6** 阶段 3 一致性维护需内容依赖索引（`content_dependency_index` sidecar）→ 待阶段 3 规划师
- **C7** 总时长偏乐观，建议拆估为"工程 4.5–7 月 + 内容/开源另 6–10 月" → §综合开放决策 9.9 待作者拍板
- **C8** 阶段 1.5 API stretch goal 验收三态口径（manual passed / API implemented / API parity validated）→ 阶段 1.5 硬闸门，由 L2 规划师纳入 STAGE_1.5_TASKS.md

### 互补 12 条（跨 LLM 评审实际增益）

- **Claude 漏抓 7 条（GPT 独家）**：U-GPT-1 ~ U-GPT-7。其中 U-GPT-1 是 🔴（"证明状态可达"不可判定 / ADR-009 第二层拆 2A/2B），其余 🟡/🟢
- **GPT 漏抓 5 条（Claude 独家）**：U-CL-1 ~ U-CL-5。其中 U-CL-1 是 🔴（阶段 3 完成标志缺质量门槛），其余 🟡

完整列表见 synthesis `/docs/reviews/master_plan/2026-04-30_synthesis.md §3 + §4`。

### 严重度分歧 1 条 + 综合修正

- **C7 总时长偏乐观**：Claude 🔴，GPT 🟡 → 综合后修正为 🟡（GPT 拆估法更建设性，问题指向相同）

### 直接矛盾 0 条

双方未在任何议题上"一边说 X 另一边说非 X"——这是 Round 5 健康度的强信号。

### 综合后 Top 3 担心（按"如不处理 project 最可能在哪里翻车"）

1. **阶段 2 在本体桩态启动 → 场景级污染 + 校验"通过"假象**（C1）
2. **ADR-009 第三层缺位 → 阶段 4 才发现 worst-bucket 路径**（C2）
3. **阶段 3 审阅 UI / 一致性维护 / 内容依赖索引一起被低估 → 阶段 3 时间黑洞**（U-CL-5 + GPT §4.9 + §5.2 复合风险）

### 综合开放决策清单（9 项 — 待作者 / 后续阶段规划师拍板）

按 synthesis §9 顺序：

1. ✅ **已落地**：阶段 1.5 vs 阶段 2 sequencing 口径（ADR-015 闭环）
2. ⏳ **待阶段 2 规划师**：阶段 2 是否必须先落地正式本体最小 Schema？范围到角色 / 地点 / 关系 / 状态路径哪一级？（C1）
3. ⏳ **待阶段 2 规划师**：角色槽位是否进入持久化 JSON？还是只作为 generator 中间产物？（U-GPT-5；synthesis 推荐 concrete refs）
4. ⏳ **待阶段 1.5 L2 规划师**：背景资产挂载 — location/scene 加 visual_assets 还是 manifest 用 target_ref/target_type/asset_role？（U-GPT-3；synthesis 推荐 manifest 含 target_ref）
5. ⏳ **待阶段 2 规划师**："任意合法状态组合可达结局"真实义 — 严格证明 / 有界符号执行 / 抽样模拟？直接影响完成标志措辞（U-GPT-1；synthesis 推荐拆 2A/2B）
6. ⏳ **待阶段 3 规划师**：playtest bots 阶段位 — 阶段 3 / 阶段 4 / 推到开源剥离后？（C2；synthesis 推荐阶段 3 完成标志）
7. ⏳ **待阶段 2 规划师**：Chapter/Act schema 时机 — 阶段 2 起手期 / 保持阶段 3？（U-CL-4；synthesis 推荐前移到阶段 2）
8. ⏳ **待阶段 2 规划师**：开源剥离边界清单何时开始维护？（C5；synthesis 推荐阶段 2/3 起）
9. ⏳ **待作者拍板**：总时长拆估 — 采纳 GPT "工程 4.5–7 月 + 内容/开源另 6–10 月"？（C7；synthesis 推荐采纳）

### 跨 LLM 评审元增益数据

- 共识 8 条（33%）= 单方评审就能抓到的事项
- 互补 12 条（50%）= 跨模型增益，单独一份评审会漏抓一半
- 严重度分歧 1 条（4%）+ 综合修正
- 直接矛盾 0 条（0%）

**结论**：跨 LLM 评审在 Round 5 体现 ~50% 事项增益，不是冗余开销。建议在阶段 2/3 关键决策点继续保留这一工作流（master_plan_battle_*.md prompt 已 stable，复用即可）。

### 这 8 条原则总览仍然有效（Round 5 未推翻 Round 1-4 任一）

DEBATE_NOTES "原则总览"段的 8 条原则在 Round 5 未被任何 critique 翻案。Round 5 全部 finding 都是 forward stages 的 sequencing / scope / risk / gap，不涉及原则层。
```

# ADR-015 编号 + 格式约束

- 编号必须是 `ADR-015`（既有 ADR-014 后顺延）；不要跳号
- 格式严格仿照 ADR-011/012/013/014：4 段 + 加粗段落标题
- 状态值用"已接受"（中文，与既有 ADR 一致）
- 日期格式 `2026-04-30`
- 不要加 emoji / 装饰

# DEBATE_NOTES Round 5 段落约束

- 不要复述 critique 全文——指向 `/docs/reviews/master_plan/` 即可
- 不要替作者拍板任何 §9 开放决策
- "✅ 已落地" 标记仅限 §9.1（ADR-015 sequencing）；其它 9 项必须 "⏳ 待 X 处理"
- 不要新增"原则"层条目（原 8 条 + 顺序保持不变）

# ROADMAP 修订约束

- 阶段 1.5 段**不动**（除了通过 ADR-015 自动获得的 sequencing 含义）
- 阶段概览总估算**不动**（C7 §9.9 待拍板）
- 阶段 0/1 任何内容**不动**（已结案）
- 任务 3a / 3b 新增的子小节用"占位"语气：列议题 + 指向 synthesis；**不写完整方案**

# 不要做的事

- 不要修改 ADR-001 ~ ADR-014 任何字段（即使你认为 Round 5 找到了 issue；那也只能新增 ADR 提案给阶段 2 规划师拍板，本会话不立）
- 不要在 ADR-015 之外立任何 ADR
- 不要修改 STAGE_1.5_TASKS.md / STAGE_1_TASKS.md / STAGE_*_ACCEPTANCE.md / SCHEMA_v0*.md / HANDOFF_STAGE_1_TO_1.5.md
- 不要重写 DEBATE_NOTES 既有 8 主题段；只追加 Round 5 章节
- 不要写完整 ADR-016/017/018 草案（即使你觉得有用）；其它新 ADR 留给阶段 2 规划师
- 不要替阶段 2 规划师细化 synthesis §6 闸门（你只放占位指针）
- 不要替阶段 3 规划师细化 synthesis §7 强化项（你只放占位指针）
- 不要做任何代码 / schema / 测试 / fixture 修改
- 不要 amend 既有 commit
- 不要 push --force / 修改 git config
- 不要 disable 测试

# 完成报告

- 4 文件 git diff 摘要（DECISIONS / ROADMAP / DEBATE_NOTES / HANDOFF_STAGE_1_TO_2）
- 边界自检：未触 STAGE_*_TASKS.md / SCHEMA_v0*.md / 任何代码 / CLAUDE.md / STAGE_*_ACCEPTANCE.md
- ADR-015 段落简介（确认编号正确 + 格式 4 段齐 + 状态行 + 日期）
- DEBATE_NOTES Round 5 段落字数 / subsection 数 / 9 开放决策核对（§9.1 ✅ 其它 ⏳）
- HANDOFF_STAGE_1_TO_2 修订点定位（哪几行 / 旧叙述 → 新叙述）
- commit + push（commit message 用 HEREDOC 传入）：

```
docs: implement Round 5 master plan synthesis to L1 docs (ADR-015, ROADMAP gates, DEBATE Round 5, HANDOFF_1_TO_2 fix)

Round 5 (Claude × GPT-5.5) synthesis 已锁定 1 条 ADR (1.5/2 sequencing) + 4 处 L1 文档增订:
- ADR-015: 阶段 1.5 manual 先启动 / 阶段 2 schema 并行起草 / commit 串行
- ROADMAP 阶段 2 启动闸门 + 阶段 3 完成标志强化项占位（指向 synthesis §6/§7）
- DEBATE_NOTES Round 5 段落（共识 8 + 互补 12 + 综合开放决策清单 9 项）
- HANDOFF_STAGE_1_TO_2 修过期"1.5 已推迟"叙述（U-GPT-2）

8 项 §9 开放决策中 §9.1 已闭环；其它 8 项标"待 X 规划师"留待阶段 2/3 处理。
本会话定位 L1 实施，未触 L2 (STAGE_*_TASKS.md) / Schema / 代码。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

- push 完成确认（git log --oneline -3 输出）

开始。
