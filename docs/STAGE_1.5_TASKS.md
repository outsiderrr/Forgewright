# STAGE_1.5_TASKS.md — 阶段 1.5 任务清单与执行会话提示词

> 阶段 1.5 规划师会话的产出物。每个任务的提示词为**可直接复制到新执行会话的自包含输入**。
>
> **使用方式（每个任务的两段式工作流）**：
> 1. 作者按 wave 顺序开 Claude Code 执行会话，从下方对应任务直接复制 ` ```text` 代码块全文作为首条消息
> 2. 任务完成后，执行会话**自动产出** `/docs/reviews/_prompts/T-1.5.X_codex_review.md`——一份**完整的、可一键复制粘贴的** Codex 评审提示词
> 3. 作者打开该文件，复制全部内容到一个新的 Codex（GPT-5.5）会话——Codex **只评审、写报告**，**不修代码**（保持跨 LLM 评审的独立性）
> 4. Codex 写出报告 `/docs/reviews/<date>_T-1.5.X_review.md`，**报告 §9 是一段 paste-ready 的 Claude Code 修复提示词**
> 5. 作者把报告 §9 复制到新 Claude Code 会话——Claude 读评审报告 + 修代码 + commit + push
>
> 工作流分两段保留了 review/author 分离：发现问题的人 ≠ 修问题的人。
>
> **与既有 [docs/REVIEW_PROMPT_CODE_GPT.md](REVIEW_PROMPT_CODE_GPT.md) 的关系**：那份是更早的 stable 模板（无 §9 修复提示词、无任务上下文预填），留给作者**临时性**评审用（如已合入主线代码的事后审）。本阶段任务工作流用的是下方 §通用：Codex 评审 prompt 模板（含 §9 修复提示词产出）。

**日期**：2026-04-30 · **版本**：v0.1 · **产出方**：阶段 1.5 规划师会话

---

## 阶段 1.5 目标回顾

来自 [docs/ROADMAP.md](ROADMAP.md) 阶段 1.5 + [docs/HANDOFF_STAGE_1_TO_1.5.md](HANDOFF_STAGE_1_TO_1.5.md)：

- 函数 `generate_character_sheet(character_ref) -> list[ImageAsset]`：N 张表情/姿势立绘
- 函数 `generate_scene_background(location_ref) -> list[ImageAsset]`：1–3 张背景
- 资产入库 `/content/visuals/` + `manifest.json`
- 本体角色实体新增 `visual_assets` 字段（**首次动 Schema！** 已授权动 Schema，路径 C）
- 至少为《铁誓驿站》3 个角色（vellin / corvan / aelwin）+ 1 个场景完成资产生成 + 入库
- 接受率 ≥ 50%（**作者本人** + 机械预筛 + AI 判官辅助；不替代）

## 锁定的架构决策（在本计划中执行）

| 决策 | 内容 | 来源 |
|---|---|---|
| **生成模式** | 双模并存：Dev = ChatGPT Plus 网页手动生成（订阅 sunk cost）；API = OpenAI Image API 自动 | ADR-014（T-1.5.1 落地） |
| **图像默认提供商** | GPT-Image（OpenAI 系；与 ChatGPT Plus 订阅同源） | ADR-014 |
| **角色一致性策略** | C+B 兜底：容忍细微差异 + prompt 显式描述固定特征（眼睛 / 发色 / 服装） | 本规划 P1.2 |
| **NPC 分级** | vellin = 重档（10–15 张）；corvan / aelwin = 轻档（4–6 张）；1 场景背景 | 本规划 P1.3 |
| **接受率判定者** | 作者本人 + 机械预检 + AI 判官辅助标红 | 本规划 P1.4 |
| **Schema 路径** | Path A：仅扩展数据（不正式化角色 Schema）；新建 `image_asset.schema.json` + 角色桩 JSON 加 `visual_assets`；不动 DialogueGraph / Node / Option / StateEffect / StateCondition | 本规划 P0.1 |
| **schema_version** | 项目首次新增 schema 文件 = MINOR bump 至 0.2.0；**仅新增文件**起步 0.2.0，existing `/schema/*.json` + scene.json 保持 0.1.1（结构未变不联动，沿用阶段 1 T-1.0 先例） | 本规划 P0.2 + P0.5 |
| **Schema 文档** | 新建 `/docs/SCHEMA_v0.2.md`（不污染 v0.md） | 本规划 P0.3 |
| **manual 模式契约** | 两段式：第一段产 prompt 包到 `/content/visuals/_pending/<asset_id>/`；作者人工生成下载；第二段 import CLI 入库；`estimate_cost=0` 仍走 budget 接口 | 本规划 P0.4 |
| **风格参考图** | 放 `/content/visuals/_reference/`；目录在 git 但内容 gitignore（版权风险） | 本规划 P1.1 |
| **OpenAI provider** | 后置：作者准备好 API key 时再开；不阻塞 1.5 验收 | 本规划 P1.5 |
| **cost_log** | 图像独立文件 `/generator/image_cost_log.jsonl`（与文本 `cost_log.jsonl` 分离） | 本规划 P2 |
| **1.5/2 sequencing** | 1.5 manual 主线先启动；阶段 2 schema 可并行起草；阶段 2 任何 schema commit 等 1.5 验收后（串行卡口） | **ADR-015**（Round 5 综合后立项） |

## Round 5 综合闸门（2026-04-30）

> 来自 Round 5 总规划评审（Claude × GPT-5.5）综合 memo `/docs/reviews/master_plan/2026-04-30_synthesis.md` §5。
> 3 项硬闸门 + 3 项软闸门由本会话（L2 阶段 1.5 规划师）纳入对应任务提示词；执行会话从下方任务提示词获取上下文。

| # | 来源 | 内容 | 性质 | 归属任务 |
|---|---|---|---|---|
| **U-GPT-3** | synthesis §5 | ImageAsset schema 必须含 `target_ref` + `target_type` + `asset_role` 字段（背景资产挂载契约；解决 manifest 孤儿资产风险） | 硬闸门 | T-1.5.2 |
| **U-CL-3** | synthesis §5 | T-1.5.6 启动前置 gate：vellin 5 张 mini probe；作者亲检 ≥ 4/5 是同一人；不通过则回炉 prompt 模板 | 硬闸门 | T-1.5.6 |
| **C8** | synthesis §5 | T-1.5.10 验收明示三态口径：manual passed / API implemented / API parity validated；1.5 只要求 manual passed | 硬闸门 | T-1.5.10 |
| **U-GPT-6** | synthesis §5 | ImageAsset 加 provenance / 版权字段：`reference_ids` / `reference_license_note` / `open_source_ok` / `commercial_ok`（阶段 4 商业化合规黑箱预防） | 软闸门 | T-1.5.2 |
| **C4** | synthesis §5 | dev/prod parity smoke test：1.5 验收前至少 3 条 prompt 在 manual + API 双跑对比；未跑则显式 R1.5-* 遗留 | 软闸门 | T-1.5.8 + T-1.5.10 |
| **U-CL-2** | synthesis §5 | T-1.5.10 完成标志可测义补充：manifest 完整性定义 + 接受率分母分子明确 | 软闸门 | T-1.5.10 |

**注**：未列入 §5 但 synthesis §9 仍开放的决策（如 §9.4 location/scene 是否也加 visual_assets 数组 vs manifest 用 target_ref 解决）由作者后续拍板；当前 1.5 任务清单按 synthesis §5 推荐位置（manifest 用 target_ref）落地，若作者改主意再回炉调整。

## 工作 wave 与依赖

```
Wave A (文档):       T-1.5.1
                       │
Wave A.5 (前置补):   T-1.5.1A ← /generator/CLAUDE.md 历史化 + pyproject 包注册（GPT-5.5 L2 critique 3.4/4.5）
                       │
Wave B (关键路径):   T-1.5.2  ← Schema 扩展，串行卡口
                       │
Wave C (并行):       T-1.5.3   T-1.5.4
                       │       │
Wave D (并行):       T-1.5.5   T-1.5.9 (OpenAI provider + parity smoke; 可推后任意时刻)
                       │
Wave E (串行):       T-1.5.6
                       │
Wave F (串行):       T-1.5.7
                       │
Wave G (串行):       T-1.5.8
                       │
              [作者侧：提供风格参考图 + 跑 manual 流程 + 审阅入库 + (可选) parity smoke]
                       │
Wave H (验收):       T-1.5.10
```

**前置作者侧准备**：
- T-1.5.6 启动前需要 **2–3 张视觉风格基准图**放入 `/content/visuals/_reference/`（自购或 Pinterest 收藏；不入 git）
- T-1.5.9 启动前需要 **OpenAI API key**（可推后；不阻塞 1.5 主验收）
- 作者侧手工流程（在 T-1.5.8 落地后）：用 ChatGPT Plus 网页对照 prompt 包逐张生成 + 下载 + 跑 import CLI

**评审节奏**：
- **关键路径任务**（T-1.5.2 / T-1.5.6 / T-1.5.7）评审 🔴 修完前，下游任务不开
- **并行任务**（T-1.5.3 / T-1.5.4；T-1.5.5 / T-1.5.9）可与下游任务并行评审
- 每个 review 报告写入 `/docs/reviews/<date>_<target>_review.md`（由 GPT-5.5 自动产出，见 REVIEW_PROMPT_CODE_GPT.md）

---

## 通用：Codex 评审 prompt 模板

每个执行会话**先做主 commit**，**再做一个跟随 commit** 产出一份完整的 Codex prompt 文件——这份文件本身就是作者一键复制粘贴到 Codex（GPT-5.5）会话的全部内容，作者**不需要再拼装任何东西**。

**路径**：`/docs/reviews/_prompts/T-1.5.X_codex_review.md`

**两 commit 拆分**（**必须**；T-1.5.5 / T-1.5.7 retrospective + 新 4 条自检 Check 2 落地后于 T-1.5.4 / T-1.5.8 双双验证）：

1. **主 commit**：feat / fix / docs(...) — 产出实际任务交付物（不含 codex review prompt）
2. **跟随 commit**：`docs(reviews): add T-1.5.X codex review prompt` — 产出 codex review prompt 文件

**为何两 commit 而非一 commit**：新 4 条自检 Check 2 要求 prompt 内 `**Commit**：` 后必须是真实 7+ 位 hex hash。主 commit 不存在前 hash 不存在；只能先做主 commit、再写真 hash 进 prompt 文件、再做第二个 commit。这是机器约束（不是风格选择），不允许走 amend（违反 CLAUDE.md no-amend 规则）。

**两 commit 必须连续 push**（先主 commit 后跟随 commit；同一次 `git push origin <branch>`），不允许中间夹杂别的 commit。

**Codex 收到这份 prompt 后会**：
1. 读必读列表 + git diff
2. 识别 finding（10 类维度 / 3 级严重度）
3. 写报告到 `/docs/reviews/<date>_T-1.5.X_review.md`
4. **报告 §9 必须含一段 paste-ready 的 Claude Code 修复提示词**——含 finding 清单 + 模块边界 + 修复纪律
5. 在对话里给作者最多 4 行总结

**Codex 不修代码、不 commit、不 push**——只评审 + 写报告 + 生成给 Claude 的修复提示词。修复由作者复制 §9 → 新 Claude Code 会话执行。这样保留 review/author 分离：发现问题的人 ≠ 改代码的人。

执行会话产出本文件时，需替换以下 placeholder：

| Placeholder | 含义 | 数据源 |
|---|---|---|
| `[TASK_ID]` | 任务编号（如 `T-1.5.3`） | 任务提示词标题 |
| `[TASK_TITLE]` | 任务名（一行；含 task id + 标题） | 任务提示词标题 |
| `[REVIEW_COMMIT]` | 主 commit hash | `git log -1 --format=%h` |
| `[REVIEW_STATS]` | 文件/行数统计 | `git diff --stat HEAD~1 HEAD`（取摘要） |
| `[MODULE_BOUNDARIES]` | 重述任务提示词的"模块边界"段（多行块） | 任务提示词 |
| `[KEY_DECISIONS]` | bullet list；本任务"§2 关键设计决策"填充值 | 任务提示词评审准备段 §2 |
| `[KNOWN_CONSTRAINTS]` | bullet list；本任务"§3 已知约束"填充值 | 任务提示词评审准备段 §3 |
| `[EXTRA_READING]` | bullet list；本任务"§4 配套阅读"填充值 | 任务提示词评审准备段 §4 |
| `[REPORT_DATE]` | 报告日期 | **由 Codex 自填**；执行会话保留为字面 `[REPORT_DATE]` |

**强制：每个 T-1.5.X 都要产出**（包括纯文档任务——doc 评审能抓"事实错误 / 规则违反 / 不一致"）。

**执行会话 push 前自检**（避免 placeholder 漏替换 + 漏填 / prose-substitute；T-1.5.1A / T-1.5.5 / T-1.5.7 实测踩过）：

```bash
PROMPT=docs/reviews/_prompts/T-1.5.X_codex_review.md  # 替换为本任务实际路径

# Check 1: 不允许残留字面 [PLACEHOLDER]（除 [REPORT_DATE]）—— 防 T-1.5.1A 风格漏替换
grep -nE '\[(TASK_ID|TASK_TITLE|REVIEW_COMMIT|REVIEW_STATS|MODULE_BOUNDARIES|KEY_DECISIONS|KNOWN_CONSTRAINTS|EXTRA_READING)\]' "$PROMPT"
# 期望：零命中（grep 退出码 1）

# Check 2: Commit 行必须是 7+ 位 hex hash —— 防 T-1.5.5 / T-1.5.7 风格 prose-substitute
#   反例（不通过）：**Commit**：T-1.5.7 实现 commit（作者会在执行修复时给出 hash）
#   正例（通过）：  **Commit**：b460c73
grep -cE '^- \*\*Commit\*\*：[0-9a-f]{7,40}\b' "$PROMPT"
# 期望：输出 1（恰好 1 行匹配）；输出 0 = 散文化或空，需替换为真 hash

# Check 3: Statistics 行必须含 +<数字> 模式 —— 粗略防数值漂移
#   反例（不通过）：**Statistics**：3 业务文件 + 3 测试 + ...（文字描述无数字加号）
#   正例（通过）：  **Statistics**：8 文件 / +2077 行
grep -cE '^- \*\*Statistics\*\*：.*\+[0-9]+' "$PROMPT"
# 期望：输出 1

# Check 4: stats 数值与实际 git diff 一致 —— 防数值写错（如"约 +1300 行" vs 实际 +2077）
git diff --shortstat HEAD~1 HEAD
# 把这行输出（如 "8 files changed, 2077 insertions(+)"）与 prompt 内 **Statistics**：行的数字目视对照；
# 文件数 / 行数任一不匹配 → 修
```

完成报告里需明确**全部 4 条自检通过**——这是与"已 commit + push"同级的 push 前必做。Check 1–3 是机器可验证（grep / git 命令一行 pass/fail），Check 4 是 1 秒目视对照。

**为何不只用 Check 1**：grep 找的是 `[X]` 字面残留；执行会话只要把 `[REVIEW_COMMIT]` 整段删掉换成散文（如"作者会在执行修复时给出 hash"），Check 1 就误判通过。Check 2（hash 正则）+ Check 3（stats 含数字加号）从机器层面拦死这种逃逸。Check 4 兜底数值漂移。

---

### 模板正文

**渲染说明**：以下 4-backtick 围栏内的内容**整段写入** `/docs/reviews/_prompts/T-1.5.X_codex_review.md`——**不要**包含外层 ` ````markdown` 与 ` ```` ` 围栏本身；只写围栏内的纯 markdown。所有 `[XXX]` placeholder 替换为本任务实际值。

````markdown
你是 Forgewright RPG 项目的代码评审员（第二意见）。
项目主代码由 Claude Code 写；你（GPT-5.5 via Codex）担任跨 LLM 交叉评审。
作者是 outsiderrr，独立开发者，**不会编程**——你的报告必须让他能拿着 `file:line` 读懂；修复**不由你执行**，由原 Claude Code 会话基于你的报告完成。

# 工作模式

**你只评审，不修代码**。

1. 读必读列表 + diff
2. 识别 finding（10 类维度 + 3 级严重度，详见下方）
3. 写报告到 `/docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md`
4. **报告 §9 必须含一段 paste-ready 的 Claude Code 修复提示词**——作者会把它复制到新 Claude 会话执行修复
5. 在对话里给作者最多 4 行总结

# 工作权限

**允许**：
- 读项目任何文件（探索代码、git log、运行测试都可以——只要不修改）
- 写你的评审报告到 `/docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md`
- 创建 `/docs/reviews/` 目录（若不存在）

**严禁**：
- 修改任何代码或文档（除你产出的报告）
- `git commit` / `git push` / `git amend` / `git push --force` / 修改 `git config`
- 修改任何 ADR / `CLAUDE.md` / `DECISIONS.md` / `DEBATE_NOTES.md` / `SCHEMA_v0*.md` / `HANDOFF_*.md` / `STAGE_*_ACCEPTANCE.md` / `schema_version` 字段

如发现一个问题需要立即修复才能继续评审，**停下来在报告里写**——不要动手改任何东西。

# 启动前必读（按顺序）

1. `/CLAUDE.md` — 项目硬性规则（10 条）
2. `/docs/ROADMAP.md` — 当前阶段定位
3. `/docs/DECISIONS.md` — 全部 ADR（**特别 ADR-014 双模视觉生成**）
4. `/docs/SCHEMA_v0.md` + `/docs/SCHEMA_v0.2.md` — Schema 设计基线
5. `/docs/HANDOFF_STAGE_1_TO_1.5.md` — 阶段 1.5 启动条件
6. `/docs/STAGE_1.5_TASKS.md` — 阶段 1.5 任务清单（**重点读本任务对应章节**）
7. **被评审代码所在模块的** `/CLAUDE.md`（若存在；如 `/generator/CLAUDE.md` / `/content/CLAUDE.md`）
8. `/docs/STAGE_1_ACCEPTANCE.md` §4 R1–R8 遗留项（很多 finding 可能本就是已知问题，别重复抓）
9. **本任务额外配套阅读**（见下方 §配套阅读）

# 本次评审目标

- **Commit**：[REVIEW_COMMIT]
- **Branch**：main
- **Statistics**：[REVIEW_STATS]
- **任务**：[TASK_TITLE]
- **项目阶段**：阶段 1.5（视觉资产生成）

执行 `git show [REVIEW_COMMIT]` 或 `git diff [REVIEW_COMMIT]^ [REVIEW_COMMIT]` 看变更全貌。

# 模块边界（**给修复阶段 Claude 用的**——你自己不改代码，但识别 finding 时若发现"该问题需跨边界才能修"，必须在报告中显式标注 ⚠️ 跨边界）

[MODULE_BOUNDARIES]

# 本任务关键设计决策（不要当 bug 抓）

[KEY_DECISIONS]

# 已知约束 / 已知遗留 / 不要重复抓

[KNOWN_CONSTRAINTS]

# 配套阅读

[EXTRA_READING]

# 评审维度（10 类）

每条 finding 必须归到下列一类：

| 代号 | 类别 | 说明 |
|---|---|---|
| **ARCH** | 架构合规 | 是否违反 ADR / 模块边界 / 跨模块写入 |
| **SCHEMA** | Schema 来源 | JSON Schema 仍是单一真相之源；Pydantic / TS 不应手写 |
| **RUNTIME** | 运行时纯净 | `/engine` 仍 0 依赖 LLM；`/generator` 不被运行时 import（ADR-002 / 004） |
| **SAFETY** | 安全 | 输入校验、密钥泄露、注入向量、不安全反序列化、路径遍历 |
| **ERR** | 错误处理 | 边界处校验、内部不过度防御、异常 vs return-result 一致 |
| **TEST** | 测试 | 覆盖关键分支与失败路径；不冗余、不重言；mock 与真实分离 |
| **DEAD** | 冗余 | 死代码、未用 import、过度抽象、为未发生需求设计 |
| **DEPS** | 依赖 | 新增依赖必要、锁版本、许可证风险 |
| **STYLE** | 风格 | 注释只解释 WHY 不解释 WHAT；命名清晰；项目约定遵守 |
| **OPEN** | 开源就绪度 | 作者 hard-code、公开接口稳定性、文档可移植性 |

**避免争论**：
- 不要争 if-elif vs match-case 这类风格题
- 不要建议"加一层抽象更优雅"——本项目反对预先抽象（CLAUDE.md "Don't add features...beyond what the task requires"）
- 不要建议拆文件除非真违反 SRP

# 严重度（3 级）

| 标记 | 级别 | 含义 |
|---|---|---|
| 🔴 | CRITICAL | 必修；违反硬规则 / 安全 / 破坏现有测试 |
| 🟡 | IMPORTANT | 应修；技术债 / 隐蔽 bug / 兼容性风险 |
| 🟢 | NICE | 可选改进，作者拍板是否纳入下一轮 |

**校准**：理想报告应有 ≥ 1 条 🔴 或不报 🔴。若 30+ 行新代码全是 🟢，说明审得太松；停下来确认 REVIEW_COMMIT 是否合理。

# 报告产出

**报告路径**：`/docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md`
- `[REPORT_DATE]` = 今天日期 `YYYY-MM-DD`
- 若 `/docs/reviews/` 不存在，创建即可

**报告结构（严格按这个）**：

```markdown
# Code Review — [TASK_TITLE]

**评审者**：GPT-5.5 via Codex
**评审日期**：[REPORT_DATE]
**评审范围**：[REVIEW_COMMIT]（[REVIEW_STATS]）
**项目阶段**：阶段 1.5（视觉资产生成）

---

## 1. 一句话结论
{{1-2 句：质量评价 + 是否阻塞合入}}

## 2. 严重度分布
| 严重度 | 数量 | 边界内可修 | 跨边界 |
|---|---|---|---|
| 🔴 CRITICAL | N | N | N |
| 🟡 IMPORTANT | N | N | N |
| 🟢 NICE | N | N | N |
| **合计** | N | N | N |

## 3. 必修（🔴 CRITICAL）

### 3.1 [{{category}}] {{file}}:{{line}} — {{1 行摘要}}
**问题**：{{2-4 行描述}}
**为什么 CRITICAL**：{{引用 ADR / 规则编号}}
**建议修复**：
\`\`\`python
# 当前
...
# 改为
...
\`\`\`
**模块边界状态**：✅ 在边界内（可修） 或 ⚠️ 跨边界（不要修，记 CLEANUP）

{{重复 3.2 / 3.3 ...}}

## 4. 应修（🟡 IMPORTANT）
{{结构同 §3}}

## 5. 可选改进（🟢 NICE）
{{结构同 §3；建议修复可只给方向不给完整代码}}

## 6. 已知遗留项核对
| Finding | 对应 R 编号 | 出现文件 |
|---|---|---|
{{若无，写"无"}}

## 7. Top 3 行动优先级（按 ROI）
1. {{finding 编号 + 一句理由}}
2. ...
3. ...

## 8. 评审范围外的观察（可忽略）
{{若你看到 REVIEW_COMMIT 之外但值得作者关注的事，写在这里。否则"无"。本节不算 finding}}

## 9. 修复任务指令（**给原 Claude Code 会话**）

> 作者：把下面 ` ```text` 代码块**整段**复制到新 Claude Code 会话作为首条消息。Claude 会读评审报告 + 修代码 + commit + push。

\`\`\`text
你的任务是修复 [TASK_ID] 评审中发现的问题。评审报告在 /docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md，先读它再开始。

# 必读
1. /docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md（评审报告全文；finding 清单 / 建议修复 diff / 边界状态）
2. /CLAUDE.md
3. /docs/STAGE_1.5_TASKS.md 本任务（[TASK_ID]）对应章节
4. /docs/DECISIONS.md（特别本任务相关 ADR）

# 模块边界（与原 [TASK_ID] 任务相同；评审报告 §3/§4/§5 内 ⚠️ 跨边界 项**不要修**）
[MODULE_BOUNDARIES]

# 待修 finding 清单

🔴 CRITICAL（必修，全部边界内的）：
{{Codex 自填：从 §3 列出每条 §3.X，仅边界内的；如无写"无"}}

🟡 IMPORTANT（建议全修；如某条修起来风险高 / 不确定，单独提出由作者决定）：
{{Codex 自填：从 §4 列出每条 §4.X，仅边界内的；如无写"无"}}

🟢 NICE（**默认跳过**；如有极简单的 1 行级修复可顺手做；否则不动）：
{{Codex 自填或 "默认跳过"}}

⚠️ 跨边界 / 与 ADR 冲突的 finding（**不要修**；记入 /docs/CLEANUP.md 如不存在则创建）：
{{Codex 自填：从 §3/§4/§5 列出标 ⚠️ 的项；如无写"无"}}

# 修复纪律
- **最小变更**——只修该 finding；不要顺手重构 / 加抽象 / 优化别的
- **保留或新增测试**覆盖修复——修了 bug 必有 test 锁住
- **跑测试通过**——pytest 必绿；测试不通过**不要 commit**，向作者报告
- **每条 finding 单独 commit**，commit message：
  `fix(<module>): <一行修复内容> (review of [TASK_ID] #<finding 编号>)`
  末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- **全部修完后 push**

# 不要做的事
- 不要 disable / skip 测试来通过
- 不要修改 ADR / CLAUDE.md / 任何 schema_version / SCHEMA_v0*.md
- 不要 amend 既有 commit；每个修复一个新 commit
- 不要 push --force；不要修改 git config
- 不要修改跨边界文件（即使评审报告写了建议修复 diff）
- 不要扩展修复范围到报告未列的问题（如发现新 bug，记入 /docs/CLEANUP.md，**不要**直接修；告知作者）
- 不要试图自己重新评审——你的工作是按报告执行修复

# 完成报告
- 已修 finding 列表 + commit hash 各一
- 未修 finding 列表 + 原因（NICE 跳过 / 跨边界已记 CLEANUP / 测试失败 / 其他）
- push 完成确认（git log --oneline -5 输出）
\`\`\`
```

# 完成报告（在对话里给作者）

报告写完后给作者**最多 4 行**：

```
评审完成 → /docs/reviews/[REPORT_DATE]_[TASK_ID]_review.md
finding: 🔴N 🟡N 🟢N（边界内可修 M / 跨边界 K）
top1: <file:line — 一句话>
下一步：复制报告 §9 ` ```text` 块到新 Claude Code 会话执行修复
```

不要复述全部 finding——报告文件里就是。

# 不要做的事（再强调）

- 不要修改任何代码或文档（除你产出的报告）
- 不要 commit / push / amend / push --force / 修改 git config
- 不要为通过评审手松；CRITICAL 就是 CRITICAL
- 不要把已知 R 项当新 finding
- 不要凭印象——每个 finding 必须能定位到 `file:line`
- §9 的修复提示词必须写完整（含模块边界 + finding 清单 + 修复纪律），让作者 paste 即可，**不要**写"参考报告 §3"之类省略
- 不要在 §9 内嵌套套娃 finding 的完整修复 diff——diff 在 §3/§4/§5 已写，§9 只列 finding 编号 + 摘要 + 边界状态

开始。
````

---

## T-1.5.1 ｜ ADR-014 + ROADMAP 1.5 实质 + SCHEMA_v0.2.md 占位 + visuals/\_reference/ 目录

```text
你的任务是落地阶段 1.5 的所有文档预备工作：新增 ADR-014（双模生成策略）、ROADMAP 1.5 段补实质内容、SCHEMA_v0.2.md 占位、`/content/visuals/_reference/` 目录约定、`.gitignore` 加固。
作者已通过 2026-04-30 阶段 1.5 规划会话明确授权修改 DECISIONS.md（CLAUDE.md 规则 10 例外）。

# 模块边界（硬性）
只允许修改 / 新建：
  - /docs/DECISIONS.md（新增 ADR-014）
  - /docs/ROADMAP.md（更新 1.5 段实质 + 更新记录）
  - /docs/SCHEMA_v0.2.md（**新建** 占位文件，正式内容由 T-1.5.2 填）
  - /content/visuals/_reference/.gitkeep（**新建**目录占位）
  - /content/visuals/CLAUDE.md（**新建**模块级指引）
  - /.gitignore
严禁修改：CLAUDE.md、SCHEMA_v0.md、DEBATE_NOTES.md、HANDOFF_STAGE_1_TO_1.5.md、STAGE_1_ACCEPTANCE.md、任何代码模块、任何 /schema/*.json、/content/test_scene_v0/

# 必读
- /CLAUDE.md（特别是规则 2 / 9 / 10 + 阶段 1.5 路径 C 例外）
- /docs/HANDOFF_STAGE_1_TO_1.5.md（"启动条件"+"⚠️ Schema 扩展警示"两段必读）
- /docs/STAGE_1.5_TASKS.md（本文件，特别"锁定的架构决策"表）
- /docs/DECISIONS.md（参考 ADR-011/012/013 的格式）
- /docs/ROADMAP.md（阶段 1.5 段当前内容）

# 待做

## 1. /docs/DECISIONS.md 新增 ADR-014

格式参照 ADR-011/012/013，必含：

### ADR-014：视觉资产双模生成策略 + GPT-Image 默认 + 一致性策略

**状态**：已接受（2026-04-30）

**背景**：阶段 1.5 引入视觉资产生成。作者订阅 ChatGPT Plus（$20/月，含 GPT-Image 网页生成额度）。直接调 OpenAI Image API 单张 $0.04–$0.17，开源用户无 API 预算时无法跑通流水线。

**决策**：
- **双模并存**：
  - **Dev 模式（主推）**：作者把 prompt 复制到 chatgpt.com 手动生成、人工审、合适的下载入库；摊薄边际成本 ≈ $0/张
  - **API 模式（生产/批量）**：用 OpenAI Image API 自动批量；单张约 $0.04–$0.17
- **图像提供商**：默认 GPT-Image（OpenAI 系；与 ChatGPT Plus 订阅同源；dev/prod 共用一套 prompt）。其他提供商（Imagen / Flux / Midjourney / 本地 SDXL）由 ImageProvider 接口预留扩展位
- **角色一致性策略**：**C + B 兜底**——容忍同一角色不同立绘细微差异（C）；prompt 显式描述固定特征（眼睛颜色 / 发型 / 服装细节）做兜底（B）。GPT-Image 不支持 ControlNet/LoRA；如未来一致性要求极高，可另开本地 SDXL 渠道，但代价是开源用户门槛上升
- **manual 模式契约（两段式）**：第一段 `generate_character_sheet(mode='manual')` 产出 prompt 包到 `/content/visuals/_pending/<asset_id>/`；作者人工生成下载；第二段 `image_import` CLI 扫描 → 校验 → 入库
- **预算治理**：API 部分总盘子 $20–$40；单次硬卡 $1.00；image cost log 独立于文本（`/generator/image_cost_log.jsonl`）；manual 模式 `estimate_cost=0` 仍走 budget 接口（统一）

**替代方案及否决理由**：
- 仅 API 模式：开源用户无 API 预算时无法跑通流水线，违反长期开源目标
- 仅 manual 模式：无法批量；规模化产线不可行
- 强制角色一致性方案 A（GPT-Image character reference 输入）：API 接口稳定性未验证；推到后续 PR
- 自训本地 SDXL：开源用户门槛过高（需 GPU + 模型权重 + ControlNet）

**后果**：
- ImageProvider 接口必须支持两种实现：ManualImportProvider + OpenAIImageProvider
- generate_character_sheet / generate_scene_background 在 manual 模式下变两段式
- 1.5 启动不需立即配 OpenAI API key，作者可马上开始
- 这同样是开源价值点——开源用户没有 API 预算时同样能用 manual 模式跑通流水线
- 一致性策略 C+B 决定 prompt 模板必须包含"角色固定特征描述"段；规划师 T-1.5.6 落地

## 2. /docs/ROADMAP.md 阶段 1.5 段补实质

替换当前阶段 1.5 段的"完成标志 / 重点工作 / 禁止事项 / 依赖"四个子段为更具体的内容（不要删掉这四个标题；只补实质）：

- 完成标志补充：vellin 重档 + corvan/aelwin 轻档 + 1 场景背景；接受率 ≥ 50%（**作者本人** + 机械预检 + AI 判官辅助）；manifest.json 完整性 100%；manual 路径全跑通（API 路径作为 stretch goal）
- 重点工作替换为：双模架构（manual + API）；ADR-014 + Schema 扩展（path A）；ImageProvider Protocol；机械预检器；视觉 AI 判官 prompt（粗起一版）
- 禁止事项补充：不正式化角色 Schema（推到阶段 2+）；不实现 ControlNet / LoRA / 自训模型；不做立绘审阅 Web UI（阶段 3）

更新记录追加一条：
- 2026-04-30：阶段 1 验收签字；阶段 1.5 任务规划落地（STAGE_1.5_TASKS.md v0.1）；ADR-014 立项

## 3. /docs/SCHEMA_v0.2.md（**新建**占位）

只产出**骨架**，正式内容由 T-1.5.2 填：

```markdown
# SCHEMA_v0.2.md — 项目 Schema 设计基线 · v0.2 增量

> 本文件承接 SCHEMA_v0.md（v0.1.x）；记录 v0.2.0 引入的 Schema 增量。
>
> **重要**：v0.2.0 是项目**首次新增 schema 文件**（不是修改 existing schema）。existing `/schema/*.json` + `/content/test_scene_v0/scene.json` 的 schema_version 保持 0.1.1（沿用阶段 1 T-1.0 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例）。仅新增文件 `/schema/image_asset.schema.json` 起步 schema_version=0.2.0。

## 1. 增量摘要（占位 — T-1.5.2 填）

## 2. ImageAsset Schema 定义（占位 — T-1.5.2 填）

## 3. 本体角色实体扩展：visual_assets 字段（占位 — T-1.5.2 填）

## 4. 兼容性约束

- v0.2.0 不破坏 v0.1.x 任何 existing 字段
- v0.1.x 数据加载时 visual_assets 视为空数组（默认）
- DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 在 v0.2.0 内**不变**

## 版本

本文件版本：v0.2.0（占位；T-1.5.2 落地正式内容）
最后更新：2026-04-30
```

## 4. /content/visuals/_reference/.gitkeep（**新建**）

空文件占位。**目录入 git，内容不入 git**（见下方 .gitignore）。

## 5. /content/visuals/CLAUDE.md（**新建**模块级指引）

中文，简短 5–10 行：

- 本目录存放阶段 1.5 视觉资产入库后的产物；不存运行时代码
- 资产在子目录按 character_id 或 location_id 分组：`vellin/<asset_id>.png` / `scene_waystation_of_iron_oath/<asset_id>.png` 等
- 所有资产必须先经 image_validator 机械预检（T-1.5.4）+ 作者审阅
- `manifest.json` 是该目录的索引；由 image_import CLI（T-1.5.7）维护
- `_reference/` 子目录存视觉风格基准图（不入 git）
- `_pending/` 子目录存 manual 模式 prompt 包 + 待入库 PNG（不入 git）

## 6. /.gitignore 加固

新增条目：
```
/content/visuals/_reference/*
!/content/visuals/_reference/.gitkeep
/content/visuals/_pending/
/generator/image_cost_log.jsonl
```

# 不要做的事

- 不要在 SCHEMA_v0.2.md 写 ImageAsset 字段细节（推到 T-1.5.2）
- 不要碰 /schema/*.json 任何 schema_version 字段
- 不要修改 ROADMAP "阶段概览"表格行（1.5 行已存在）
- 不要在 ADR-014 里规划具体任务拆分（那是本文件 STAGE_1.5_TASKS.md 的事）
- 不要新建 /content/visuals/ 下其他子目录（character_id 子目录由 T-1.5.7 入库时建）

# 完成报告

- 各文件 git diff 摘要
- commit + push（commit message: `docs: add ADR-014 (dual-mode visual generation), Stage 1.5 ROADMAP fill, SCHEMA_v0.2 scaffold (T-1.5.1)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.1_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- ADR-014 与已有 ADR-011（Provider 可插拔）保持兼容；ImageProvider 是新接口，不复用 LLMProvider
- SCHEMA_v0.2.md 是占位文件；ImageAsset 字段细节由 T-1.5.2 落地，本任务**不应**包含字段定义
- /content/visuals/_reference/ 内容 gitignore 是版权考量，不是 size 问题

§3 已知约束：
- 本任务不实现任何代码；纯文档
- 本任务不解决阶段 1 R1–R8 任何遗留项（本就不在 1.5 范围）
- ROADMAP "阶段概览"表格行（1.5 行）已存在；不重复添加

§4 配套阅读：
- /docs/HANDOFF_STAGE_1_TO_1.5.md（特别"启动条件"段 + "Schema 扩展警示"段）
- /docs/STAGE_1.5_TASKS.md "锁定的架构决策"表
- ADR-011 / ADR-012（ADR-014 的姊妹决策；格式参照）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.1A ｜ /generator/CLAUDE.md 历史化 + pyproject.toml 包注册（GPT-5.5 L2 critique 3.4 + 4.5 修补）

```text
你的任务是为 T-1.5.2 启动扫清两处 plan-vs-repo 一致性障碍——这是阶段 1.5 GPT-5.5 L2 critique（2026-05-01）抓到的 🔴3.4 + 🟡4.5：
- /generator/CLAUDE.md 仍写"阶段 1 严禁修改 /state/ontology/" + "本模块此阶段不出现视觉资产相关代码"，与阶段 1.5 即将做的事直接冲突
- pyproject.toml 用静态 packages 列表，未含 generator.prompts.visual，T-1.5.6 创建该子包后安装包会丢模板

# 模块边界（硬性）
允许修改：
  - /generator/CLAUDE.md
  - /pyproject.toml
严禁修改：
  - /CLAUDE.md（规则 9）
  - /docs/、/schema/、/state/、/engine/、/validator/、/content/
  - /generator/ 下任何 .py（本任务纯文档/配置）
  - 任何 /schema/*.json
  - 任何 /generator/models/_generated/

# 必读
- /CLAUDE.md（规则 2 + 9 + 1.5 路径 C 例外）
- /generator/CLAUDE.md（当前形态）
- /pyproject.toml（当前 packages 列表）
- /docs/STAGE_1.5_TASKS.md（特别 T-1.5.2 ~ T-1.5.10 任务边界——确认你改的两处规则与所有 1.5 任务相容）
- /docs/DECISIONS.md ADR-014 + ADR-015（核心约束）
- /docs/reviews/stage_1_5_plan/2026-05-01_gpt55_critique.md §3.4 + §4.5（critique 来源）

# 待做

## 1. 修订 /generator/CLAUDE.md

把"阶段 1 严禁修改"语段改成历史化叙述 + 补 1.5 规则。具体改动：

- "**阶段 1 严禁修改 `/state/ontology/`**（沿用桩）。视觉资产生成属阶段 1.5，本模块此阶段不出现任何相关代码。" → 改为：
  - "**阶段 1 历史**：阶段 1（generate_node 单节点生成）期间，本模块严禁修改 /state/ontology/（沿用桩），且不出现任何视觉资产相关代码。该约束已于阶段 1 验收（2026-04-30）后解除。"
  - "**阶段 1.5 授权**：根据 ADR-014（视觉资产双模生成）+ ADR-015（1.5/2 sequencing），本模块在阶段 1.5 期间允许：
    - 新增视觉资产相关代码（image_provider.py / image_budget.py / image_cost_log.py / generate_visual.py / image_import.py / manifest.py / visual_experiment.py / visual_review_cli.py / visual_metrics.py 等）
    - 新增 /generator/prompts/visual/ 子包
    - 新增 /generator/providers/manual_import.py 和 /generator/providers/openai_image.py
    - 通过 image_import CLI 修改 /state/ontology/waystation.json 的 entities[] 中 type=character 项的 visual_assets 数组（仅 visual_assets 字段；不动其它任何字段）"
  - "**阶段 1.5 边界仍在**：
    - 不得直接 import google.genai 或 openai 到业务代码（必须经 ImageProvider 接口；ADR-011 + ADR-014）
    - 任何 image API 调用前必须经 image_budget.check_and_charge()（ADR-012 + ADR-014）
    - 运行时（/engine）严禁依赖本模块（ADR-002 + ADR-004 不变）
    - 不得修改 /state/ontology/waystation.json 的 entities[] 内非 visual_assets 字段（保护本体真相之源 ADR-006）"

- "**不得跨模块改动**：禁止编辑 `/schema/`、`/state/`、`/engine/`、`/validator/`、`/content/`、`/docs/`。需要 Schema 变更时，停下来报告作者（CLAUDE.md 规则 2 / 7）。" → 改为：
  - "**跨模块改动约束**：默认禁止编辑 /schema/、/state/、/engine/、/validator/、/content/、/docs/。需要 Schema 变更时，停下来报告作者（规则 2 / 7）。**阶段 1.5 例外**（已授权）：image_import CLI 经过 image_validator 校验后可写 /state/ontology/waystation.json 的 entities[].visual_assets 字段；T-1.5.7 的模块边界对此显式列出。"

其余规则（提示词模板放 prompts/、自动生成模型不手编辑、提交前 pytest 通过等）保持原文不动。

文件末尾如果有"提交前确认"段，追加一行："- 1.5 阶段：确认未直接 import google.genai / openai；确认所有 image API 调用经过 image_budget。"

## 2. 修订 /pyproject.toml

在 [tool.setuptools] packages 列表中新增一项：
- "generator.prompts.visual"

位置：紧跟现有 "generator.prompts" 之后；保持字母序。

如 pyproject.toml 还包含 [tool.setuptools.package-data] 或 include-package-data 配置，确认 prompts/visual/*.md 模板会被打包；如需新增 package_data 配置项以确保 .md 模板入包，可加：

```toml
[tool.setuptools.package-data]
"generator.prompts.visual" = ["*.md"]
```

但**仅在确认现有配置不会自动包含 .md 时才加**——如 include-package-data = true 已生效，不必加重复配置。

# 不要做的事

- 不要修改 /generator/ 任何 .py
- 不要新增 Pillow / openai 等运行时依赖到 pyproject.toml（这些由 T-1.5.4 / T-1.5.9 各自负责）
- 不要在 /generator/CLAUDE.md 删除任何阶段 1 已建立的硬规则（只是历史化 + 补充 1.5 规则；保持累积，不替换）
- 不要修改 /CLAUDE.md
- 不要 amend 既有 commit；本任务一个新 commit
- 不要 push --force；不要修改 git config

# 完成报告

- /generator/CLAUDE.md diff 摘要（特别新旧规则对照）
- /pyproject.toml diff 摘要
- 边界自检：未触 /generator/ .py 文件 / /docs/ / /schema/ / /state/ / 任何 ADR
- commit + push（commit message: `docs(generator+config): historicize stage-1 ban + add visual prompts package (T-1.5.1A; GPT-5.5 L2 critique 3.4/4.5 fix)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.1A_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- /generator/CLAUDE.md 阶段 1 禁令历史化（不删除）是有意——保留累积式规则演进史；不要建议直接删除阶段 1 段落
- pyproject.toml 静态 packages 列表保留（不切换 setuptools find）是有意——避免 find 模式在边角 case 下的行为不稳定；后续每个新增子包按需在 pyproject 注册即可
- 不在本任务加 Pillow / openai 依赖是有意——这些是 T-1.5.4 / T-1.5.9 的职责，本任务纯属阶段 1 → 1.5 规则切换 + 包注册
- /state/ontology/waystation.json 的 visual_assets 写入授权仅限 image_import CLI（T-1.5.7）经 image_validator 校验后写——不允许任何其它代码路径直接写本体

§3 已知约束：
- 本任务不改任何 .py 文件
- 本任务是 T-1.5.2 启动前置；阻塞 T-1.5.2~T-1.5.10
- 本任务不解决 GPT-5.5 L2 critique 其它 finding（4.4 Pillow / 4.6 parity / 等由对应任务处理）

§4 配套阅读：
- /docs/DECISIONS.md ADR-014 + ADR-015
- /docs/reviews/stage_1_5_plan/2026-05-01_gpt55_critique.md §3.4 + §4.5
- /docs/STAGE_1.5_TASKS.md "Round 5 综合闸门"段

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.2 ｜ Schema 扩展（**串行关键路径**）

```text
你的任务是落地阶段 1.5 唯一一次 Schema 结构性变更：新建 image_asset.schema.json + 在 /state/ontology/waystation.json 的 entities[] 中 type="character" 项加 visual_assets 字段 + 把 SCHEMA_v0.2.md 占位填完整 + 加 schema 层测试。
**这是项目首次动 Schema**。作者已在 ROADMAP 阶段 1.5 段（commit 1d2030f）+ STAGE_1.5_TASKS.md 表格 P0.1/P0.2/P0.3 显式授权。
**严禁**修改任何 existing 字段或 existing 文件的 schema_version。
**前置**：T-1.5.1A 已完成（/generator/CLAUDE.md 历史化 + pyproject 包注册）。

# 模块边界（硬性）
允许新建：
  - /schema/image_asset.schema.json
  - /schema/tests/test_image_asset_schema.py（**GPT-5.5 L2 critique 4.2 修补**——schema 关键路径必须有 schema 层测试，不能等 T-1.5.3 codegen 才发现 schema 错误）
  - /schema/tests/__init__.py（如不存在）
允许修改：
  - /docs/SCHEMA_v0.2.md（填实质内容）
  - /state/ontology/waystation.json（**GPT-5.5 L2 critique 3.1 修补**——仓库实际只有这一个聚合本体文件，非三个角色桩文件；只允许在 entities[] 中 type="character" 的 3 个对象内新增 visual_assets 字段，**严禁修改 id / display_name / type 等任何既有字段**；entities[] 中 type="scene" 项暂不动 —— scene_background 资产挂载方式按 synthesis §9.4 推荐位置走 manifest target_ref，等阶段 2 作者拍板是否反向 location ontology 加 visual_assets[]）
严禁修改：
  - /schema/dialogue_graph.schema.json / dialogue_node.schema.json / option.schema.json / state_effect.schema.json / state_condition.schema.json（任何字段或 schema_version）
  - /content/test_scene_v0/scene.json（任何字段，包括 schema_version）
  - SCHEMA_v0.md（v0.1.x 文档，与本任务无关）
  - /generator/、/engine/、/validator/ 任何代码
  - CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / HANDOFF_STAGE_1_TO_1.5.md
  - /state/ontology/waystation.json 中 entities[] 内**任何**非 visual_assets 字段（包括但不限于 id / display_name / type）
  - /state/ontology/waystation.json 顶层结构（entities[] 数组本身的元素增删）

# 必读
- /CLAUDE.md（规则 2 + 6 + 9 + 10 + 阶段 1.5 例外）
- /docs/HANDOFF_STAGE_1_TO_1.5.md（"Schema 扩展警示"段）
- /docs/STAGE_1.5_TASKS.md（特别"锁定的架构决策"表 P0.1 / P0.2 / P0.3）
- /docs/SCHEMA_v0.md（理解 v0.1.x 字段语义；不要改）
- /docs/SCHEMA_v0.2.md（T-1.5.1 留下的占位骨架）
- /schema/dialogue_graph.schema.json + dialogue_node.schema.json（参考字段命名约定 / $schema URL / schema_version 字段位置）
- /state/ontology/waystation.json（**GPT-5.5 L2 critique 3.1 修补**——确认实际形态：entities[] 聚合数组，含 char_vellin / char_corvan / char_aelwin / scene_waystation_of_iron_oath 4 个对象，每个含 id / display_name / type 字段；**不要预设三个独立桩文件存在**）

# 待做

## 1. 新建 /schema/image_asset.schema.json

JSON Schema 2020-12，schema_version 字段值 = "0.2.0"。结构（最终字段名以你工程实现为准；以下是设计意图）：

- $schema: "https://json-schema.org/draft/2020-12/schema"
- $id: 沿用 existing schema 的命名约定
- schema_version: "0.2.0"（const）
- type: object
- required: [asset_id, asset_kind, source_mode, format, width, height, file_path, created_at, target_ref, target_type, asset_role]
- properties:
  - asset_id: string, pattern (建议 `^img_[a-z0-9_]{1,64}$`)
  - asset_kind: enum ["character_sheet", "scene_background"]（保留向后兼容；与 asset_role 同义但更面向使用场景）
  - **target_ref**: string（**Round 5 U-GPT-3 硬闸门**；通用挂载锚点 ID，如 `char_vellin` / `scene_waystation_of_iron_oath`）
  - **target_type**: enum ["character", "location", "scene"]（**Round 5 U-GPT-3 硬闸门**；锚点类型）
  - **asset_role**: enum ["character_sheet", "scene_background"]（**Round 5 U-GPT-3 硬闸门**；资产在叙事中扮演的角色；与 asset_kind 当前重合，预留未来扩展如 "item_icon" / "ui_portrait"）
  - character_ref: string | null（asset_kind=character_sheet 时 required；与 target_ref + target_type=character 等价；保留向后兼容；**写入时必须与 target_ref/target_type 一致**）
  - location_ref: string | null（asset_kind=scene_background 时 required；与 target_ref + target_type ∈ {location, scene} 等价；保留向后兼容；**写入时必须与 target_ref/target_type 一致**）
  - source_mode: enum ["manual", "api"]
  - format: enum ["png", "webp"]
  - width: integer, minimum 256, maximum 4096
  - height: integer, minimum 256, maximum 4096
  - file_size_bytes: integer, minimum 1
  - has_alpha: boolean（character_sheet 应 true；scene_background 应 false）
  - file_path: string（相对仓库根，如 "content/visuals/vellin/img_vellin_neutral.png"）
  - prompt_hash: string（sha256 hex；用于追溯生成时的 prompt 文本）
  - generation_metadata: object（free dict；含 prompt 文本 / 风格基准引用 / 生成时间戳 / API 调用元数据等；schema 不约束内部结构）
  - style_reference_id: string | null（指向 _reference/ 内的基准图标识；可选）
  - **reference_ids**: array of string, default []（**Round 5 U-GPT-6 软闸门**；本资产生成时引用的 _reference/ 基准图 ID 数组；用于 trace 风格依赖）
  - **reference_license_note**: string, default ""（**Round 5 U-GPT-6 软闸门**；自由文本；作者填写每张引用基准图的来源 + 许可，如 "ref_001: own photograph CC0"）
  - **open_source_ok**: boolean, default false（**Round 5 U-GPT-6 软闸门**；本资产是否能进开源 release dataset；默认 false 安全侧）
  - **commercial_ok**: boolean, default false（**Round 5 U-GPT-6 软闸门**；本资产是否能进商业版；默认 false 安全侧）
  - created_at: string, format date-time
- additionalProperties: false

**注意**：
- 不要包含 character_ref / location_ref 互斥的 oneOf——保持简单 + 让 validator 在语义层校验互斥（避免 datamodel-code-generator 处理 oneOf 的已知坑，沿用阶段 1 baseline_001 教训）
- 不要包含视频字段（短视频是未来钩子，1.5 不实现；schema 字段保留扩展空间即可，不主动加 video_format / video_duration）
- **target_ref / target_type / asset_role** 是 Round 5 U-GPT-3 硬闸门——**必须 required**，不能跳过；synthesis §9.4 仍开放（location/scene 是否也加 visual_assets[] 数组），但 1.5 阶段按推荐方案"manifest 用 target_ref 解决"落地。如阶段 2 作者改主意（决定 location ontology 也持有 visual_assets[]），届时 ImageAsset schema **不动**——只在角色/地点本体侧多加一个嵌入路径
- **reference_ids / reference_license_note / open_source_ok / commercial_ok** 是 Round 5 U-GPT-6 软闸门——开源剥离合规预防（C5 共识）；阶段 4 才需要这些字段被填准确，但 1.5 阶段就在 schema 里预留位置避免后期回填
- **target_ref / character_ref / location_ref 一致性约束**（**GPT-5.5 L2 critique 4.3 修补**）：character_ref / location_ref 是 backward-compatibility 镜像字段，**必须与 target_ref / target_type 一致**：
  - target_type="character" → character_ref **必须 = target_ref**；location_ref 必须 null
  - target_type="location" → location_ref **必须 = target_ref**；character_ref 必须 null
  - target_type="scene" → location_ref **可以 = target_ref**（向后兼容；当前试点 `scene_waystation_of_iron_oath` 即此情况）；character_ref 必须 null
  - 这些一致性约束在 schema 层用 `if/then/else` 或 `oneOf` 表达**会触发 datamodel-code-generator 已知坑**（baseline_001 教训）；**改在 image_validator 语义层校验**——schema 仅声明字段类型，validator 拒收不一致样本

## 2. /state/ontology/waystation.json 扩展 visual_assets 字段（**GPT-5.5 L2 critique 3.1 修补**）

仓库实际本体形态是 `/state/ontology/waystation.json`（**不是**三个独立桩文件）。结构（已验证）：

```json
{
  "entities": [
    {"id": "char_vellin", "display_name": "Vellin", "type": "character"},
    {"id": "char_corvan", "display_name": "Corvan", "type": "character"},
    {"id": "char_aelwin", "display_name": "Aelwin", "type": "character"},
    {"id": "scene_waystation_of_iron_oath", "display_name": "Waystation of the Iron Oath", "type": "scene"}
  ]
}
```

修订动作：在 `entities[]` 中 `type=="character"` 的 3 个对象**末尾**各新增一个 `visual_assets: []` 字段。

修订后形态（示意）：

```json
{
  "entities": [
    {
      "id": "char_vellin",
      "display_name": "Vellin",
      "type": "character",
      "visual_assets": []
    },
    {
      "id": "char_corvan",
      "display_name": "Corvan",
      "type": "character",
      "visual_assets": []
    },
    {
      "id": "char_aelwin",
      "display_name": "Aelwin",
      "type": "character",
      "visual_assets": []
    },
    {
      "id": "scene_waystation_of_iron_oath",
      "display_name": "Waystation of the Iron Oath",
      "type": "scene"
    }
  ]
}
```

注意：

- **scene 项**（`scene_waystation_of_iron_oath`）**暂不加 visual_assets**——按 synthesis §9.4 "manifest 用 target_ref 解决"路线落地；scene_background 资产仅在 manifest.json 有索引，不嵌入本体。等阶段 2 作者拍板是否反向给 scene/location 也加 visual_assets[] 数组，届时再补
- **不要修改 id / display_name / type 等任何既有字段**
- **不要增删 entities[] 任何元素**
- 空数组 `[]` 先落地；T-1.5.7 入库时由 image_import CLI 填充

## 3. /schema/tests/test_image_asset_schema.py（**GPT-5.5 L2 critique 4.2 修补**）

新建 schema 层测试，覆盖：

- test_minimal_valid_character_asset：含全部 required 字段（含 target_ref="char_vellin" / target_type="character" / asset_role="character_sheet" + character_ref=target_ref + location_ref=null）→ 通过
- test_minimal_valid_scene_background：含全部 required（target_type="scene" / asset_role="scene_background" / location_ref=target_ref + character_ref=null）→ 通过
- test_missing_target_ref_fails / test_missing_target_type_fails / test_missing_asset_role_fails → 各自 schema 校验失败
- test_provenance_defaults：reference_ids=[] / reference_license_note="" / open_source_ok=false / commercial_ok=false 默认值合法
- test_additional_properties_rejected：额外字段 → 失败
- test_invalid_target_type_enum：target_type="other" → 失败
- test_resolution_below_min：width=128 → 失败
- test_resolution_above_max：width=8192 → 失败

测试用 jsonschema 库（如阶段 0 已用）；fixture 为最小 dict。**注意**：character_ref / location_ref 与 target_ref / target_type 一致性（§1 中说明）**不在 schema 层校验**——这是 image_validator 语义层职责，本测试不覆盖一致性，只覆盖字段存在/类型/枚举/边界。

如 /schema/tests/__init__.py 不存在，新建空文件。

如 jsonschema 不在 pyproject.toml 依赖中，**停下来在完成报告里说明** —— 不要自行追加依赖（pyproject 修订是 T-1.5.1A / T-1.5.4 / T-1.5.9 的职责，本任务边界不含 pyproject）。

## 4. /docs/SCHEMA_v0.2.md 完整版

在 T-1.5.1 留下的骨架基础上填实质内容。**4 段顺序与编号不可改**：

§1 增量摘要：列出本次 v0.2.0 增量的 1 行 bullet list（new schema 文件 + 角色实体扩展字段）；明确 existing 5 个 schema 不动 + scene.json schema_version 不动

§2 ImageAsset Schema 定义：完整字段表（每行：字段名 / 类型 / 必填 / 约束 / 一句话语义）；附一段完整示例 JSON

§3 本体角色实体扩展：visual_assets 字段语义；为何"路径 A：仅扩展数据，不正式化角色 Schema"（引用 STAGE_1.5_TASKS.md P0.1）；如何引用 ImageAsset（直接嵌入完整对象 vs 引用 asset_id）—— **决策**：直接嵌入完整 ImageAsset 对象（避免引用层次太多；manifest.json 也存全量）

§4 兼容性约束：v0.2.0 不破坏 v0.1.x；v0.1.x 数据加载时 visual_assets 视为空数组；保留为未来短视频扩展点的钩子说明（**仅说明，不实现**）

文末更新版本与最后更新日期。

## 5. /schema/ 与生成模型联动（重要；**GPT-5.5 L2 critique 4.1 修补**）

阶段 1 T-1.3 用 datamodel-code-generator 把 /schema/*.json → /generator/models/_generated/。本任务**不应**直接重生成模型——这会跨越本任务模块边界。

但需要在完成报告里**显式提示 T-1.5.3 注意**：当前 `/generator/scripts/regenerate_models.sh` 是**单 entry**（`dialogue_graph.schema.json`），且开头会 `find $OUT_DIR -delete` **wipe 既有 _generated/*.py**。简单"补一行 image_asset.schema.json"会被 wipe 干掉 dialogue_graph 输出或被 codegen 互覆盖。T-1.5.3 必须采用以下其一：

- **方案 A（推荐）**：把脚本改成**两次 codegen 调用** — 第一次 dialogue_graph → 输出 dialogue_graph 模型；第二次 image_asset → 输出 image_asset.py（用 `--class-name ImageAsset` 显式控制类名）；wipe 步骤只在第一次前执行
- **方案 B**：扩展 _postprocess_models.py 支持多 entry 输入；脚本接受多个 --input

无论选哪种，T-1.5.3 必须验证 dialogue_graph 既有 roundtrip 测试不退化。本任务（T-1.5.2）**仅交付 schema 文件 + schema 层测试**；codegen 联动一律推给 T-1.5.3。

# 不要做的事

- 不要修改 existing /schema/*.json 任何字段或 schema_version
- 不要修改 /content/test_scene_v0/scene.json（任何字段）
- 不要新建 character.schema.json / location.schema.json（路径 A：不正式化角色 Schema）
- 不要在 image_asset.schema.json 加 oneOf / anyOf / allOf 复合形态（沿用 baseline_001 教训）
- 不要重跑 datamodel-code-generator（跨边界；推给 T-1.5.3）
- 不要修改 /generator/、/engine/、/validator/ 任何代码

# 已知坑提醒

- existing /schema/*.json 可能用了 additionalProperties；image_asset.schema.json 也用同样 false（保持一致），但**不要**加 unevaluatedProperties / patternProperties（datamodel-code-generator 已知坑）
- /state/ontology/ 文件可能根本没用 JSON Schema 严格校验（路径 A 的本意）；本任务也**不要**为它们补上 schema 文件

# 完成报告

- 新增文件：/schema/image_asset.schema.json + /docs/SCHEMA_v0.2.md（实质内容）
- 修改文件：三个角色桩 JSON（仅末尾新增 visual_assets: []）
- 显式标注："T-1.5.3 启动时需重跑 regenerate_models.sh"
- commit + push（commit message: `feat(schema): introduce ImageAsset schema and visual_assets character extension (v0.2.0) (T-1.5.2)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.2_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 路径 A 是 STAGE_1.5_TASKS.md P0.1 决策——不正式化角色 Schema；不要建议 reviewer 反过来"新建 character.schema.json"
- schema_version 仅新增文件起步 0.2.0；existing /schema/*.json 保持 0.1.1 是 P0.5 决策（沿用阶段 1 T-1.0 先例）；不要建议反过来联动
- ImageAsset 不用 oneOf/anyOf/allOf 是阶段 1 baseline_001 教训（Gemini schema 子集不接受复合形态；datamodel-code-generator 也有处理坑）
- visual_assets 直接嵌入完整 ImageAsset 对象（不通过 asset_id 引用）是有意——简化 manifest 与本体的结构层次

§3 已知约束：
- 本任务不重跑 datamodel-code-generator（推到 T-1.5.3）
- 本任务不解决 STAGE_1_ACCEPTANCE R5 本体污染（不在 1.5 范围）
- 角色桩文件如不存在，本任务停下来不创造（需作者先定本体桩形态）

§4 配套阅读：
- /docs/SCHEMA_v0.md（v0.1.x 基线；理解字段命名约定）
- /docs/SCHEMA_v0.2.md（本任务产出物）
- /docs/HANDOFF_STAGE_1_TO_1.5.md "Schema 扩展警示"段
- ADR-014（在 /docs/DECISIONS.md 内）
- 阶段 1 STAGE_1_ACCEPTANCE.md §3.1 baseline 迭代史（理解 Gemini schema 子集教训）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.3 ｜ ImageProvider Protocol + ManualImportProvider 实现

```text
你的任务是定义 ImageProvider 接口（与 LLMProvider 同源风格），实现 ManualImportProvider（manual 模式主推），并重跑 datamodel-code-generator 把 ImageAsset 纳入 _generated/。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/image_provider.py（**新建**）
  - /generator/providers/manual_import.py（**新建**）
  - /generator/providers/__init__.py（重导出 ManualImportProvider）
  - /generator/models/_generated/image_asset.py（datamodel-code-generator 自动产物）
  - /generator/models/__init__.py（重导出 ImageAsset）
  - /generator/scripts/regenerate_models.sh（如阶段 1 已存在则不动；如未覆盖 image_asset.schema.json 则补一行）
  - /generator/tests/test_image_provider_contract.py（**新建**）
  - /generator/tests/test_manual_import_provider.py（**新建**）
严禁修改：
  - /schema/、/state/、/engine/、/validator/、/content/
  - /generator/llm_provider.py、/generator/providers/gemini.py、/generator/budget.py、/generator/cost_log.py、/generator/generate_node.py、/generator/experiment.py、/generator/review_cli.py、/generator/metrics.py
  - /docs/

# 必读
- /CLAUDE.md（规则 2 + 6）
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-011 / ADR-013 / **ADR-014**（核心）
- /docs/STAGE_1.5_TASKS.md（特别"锁定的架构决策"表 P0.4 manual 模式契约）
- /docs/SCHEMA_v0.2.md（ImageAsset 字段表）
- /generator/llm_provider.py（参考接口风格）
- /generator/providers/gemini.py（参考实现风格）

# 待做

## 1. 重跑 datamodel-code-generator 让 ImageAsset 入库（**GPT-5.5 L2 critique 4.1 修补**）

T-1.5.2 完成报告会标注："新增 image_asset.schema.json 后需重跑 regenerate_models.sh"。**本任务执行第一步**：

- 当前 `/generator/scripts/regenerate_models.sh` 是**单 entry**（dialogue_graph.schema.json）+ 开头 `find $OUT_DIR -delete` wipe 既有产物。**简单"补一行 image_asset.schema.json"会被 wipe 干掉 dialogue_graph 输出或被 codegen 互覆盖**——必须按以下方案处理：
  - **方案 A（推荐）**：把脚本改成**两次 codegen 调用**——
    - 第一次：dialogue_graph.schema.json → 既有 dialogue_graph 模型（保留 `--class-name DialogueGraph`）
    - 第二次：image_asset.schema.json → image_asset.py（用 `--class-name ImageAsset` 显式控制类名）
    - wipe 步骤（`find ... -delete`）只在第一次 codegen 前执行
    - 保留 _postprocess_models.py 调用，保持类名后处理一致
  - **方案 B**：扩展 _postprocess_models.py 接受多 entry / 多 schema 文件输入
- 选定方案后跑脚本 → 产出 /generator/models/_generated/image_asset.py
- 在 /generator/models/__init__.py 重导出 ImageAsset
- **不要**手写 ImageAsset 类（CLAUDE.md 规则 6）
- **关键回归测试**：跑既有 roundtrip 测试（test_models_roundtrip.py），确认 dialogue_graph 模型字段未退化；扩展该测试加一条 ImageAsset roundtrip（最小合法对象 → load → dump → 字段一致）
- 如 ImageAsset roundtrip 测试发现需要 patch _generated/image_asset.py 的命名/字段（罕见），**不要直接改 _generated/**——回到 _postprocess_models.py 调整规则

## 2. /generator/image_provider.py（**新建**）

定义 Protocol（typing.Protocol，runtime_checkable）：

```python
class ImageProvider(Protocol):
    def generate(
        self,
        *,
        prompt: str,
        ref_images: list[Path] | None = None,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        asset_kind: Literal["character_sheet", "scene_background"],
        # GPT-5.5 L2 critique 3.3 修补：target 三字段必须进入接口（数据流贯穿，否则 manifest 入库阶段只能猜）
        target_ref: str,                                          # 例如 "char_vellin" / "scene_waystation_of_iron_oath"
        target_type: Literal["character", "location", "scene"],   # 与 ImageAsset.target_type 一致
        asset_role: Literal["character_sheet", "scene_background"],  # 与 asset_kind 同义；预留扩展（如 "item_icon"）
        # GPT-5.5 L2 critique 4.9 修补：asset_id_stub 由调用方（T-1.5.6 generate_visual.py）生成 deterministic stub 后传入；provider 不再内部生成
        asset_id_stub: str,
        variant_label: str = "",  # 可选；如 "neutral" / "smiling" / "dusk_interior"；进 meta.json 用于 trace
    ) -> ImageGenerationResult: ...

    def estimate_cost(
        self, *, n: int, size: tuple[int, int]
    ) -> float: ...
```

配套 dataclass：

```python
@dataclass
class ImageGenerationResult:
    mode: Literal["manual", "api"]
    asset_id_stub: str                     # 调用方传入的 stub；plan 决策：stub == final asset_id（**调用方保证 deterministic + 唯一**）
    image_bytes: bytes | None              # manual 模式 None；api 模式真实字节
    prompt_package_path: Path | None       # manual 模式指向 _pending/<asset_id_stub>/；api 模式 None
    cost_usd: float                        # manual 模式 0.0；api 模式按 estimate_cost 落记
    raw_metadata: dict                     # provider 私有元数据；含 target_ref / target_type / asset_role / variant_label 回填便于 trace
```

注意：Protocol 本身不实现 budget；与 LLMProvider 一致——budget.check_and_charge 由更上层的 generate_visual.py（T-1.5.6）拦。

## 3. /generator/providers/manual_import.py（**新建**）

class ManualImportProvider 实现 ImageProvider：

构造接受：
- pending_root: Path（默认 `Path("content/visuals/_pending")`）
- prompt_template_dir: Path（默认 `Path("generator/prompts/visual")`；T-1.5.6 落地 prompt 模板）

generate() 流程：
1. **不再内部生成 asset_id_stub**（**GPT-5.5 L2 critique 4.9 修补**）—— 用调用方传入的 `asset_id_stub`（已是 deterministic 最终 ID）
2. 创建目录 `pending_root / asset_id_stub / `
3. 写入 prompt 包：
   - prompt.md（中英双版本提示词；中文给作者审、英文给 ChatGPT）
   - meta.json（**GPT-5.5 L2 critique 3.3 修补**：必含 `target_ref` / `target_type` / `asset_role` / `variant_label` / `asset_kind` / `size` / `n` / `source_mode="manual"` / `created_at` / `asset_id_stub` / **`prompt_hash`** = sha256 of prompt 英文段；`character_ref` / `location_ref` 镜像字段按 §T-1.5.2 4.3 一致性约束写入：character_ref = target_ref（target_type=character 时）/ location_ref = target_ref（target_type=location/scene 时）/ 反之 null）
   - 占位 README.md 给作者：步骤 1 复制 prompt.md 英文段到 chatgpt.com → 步骤 2 生成 → 步骤 3 下载到本目录命名为 `<asset_id_stub>.png` → 步骤 4 跑 `python -m generator.image_import --asset-id <asset_id_stub>`
4. 返回 ImageGenerationResult(mode="manual", asset_id_stub=<入参>, image_bytes=None, prompt_package_path=..., cost_usd=0.0, raw_metadata={target_ref, target_type, asset_role, variant_label, prompt_hash})

estimate_cost(n, size) → 0.0（manual 模式）

注意：
- **本任务不实现 prompt 模板内容**（推到 T-1.5.6）；本任务只搭好"写 prompt 包到 _pending/"的机制
- 如果 prompt_template_dir 不存在或为空，generate() 写入一个 placeholder prompt（如 `[PLACEHOLDER from T-1.5.3 — T-1.5.6 will fill]`）+ 在日志里 WARN，**不要**抛错（避免阻塞集成测试）

## 4. /generator/providers/__init__.py

重导出 ManualImportProvider；保持 GeminiProvider 重导出不动。

## 5. 测试

### /generator/tests/test_image_provider_contract.py
- 不调真实 API；用一个 FakeImageProvider（写在测试文件内）验证 Protocol 接口契约
- 确保 ManualImportProvider 满足 isinstance check（runtime_checkable）

### /generator/tests/test_manual_import_provider.py
- 用 tmp_path fixture 隔离 pending_root
- 跑 generate() → 验证：
  - 目录创建
  - prompt.md / meta.json / README.md 三个文件存在
  - meta.json 字段完整 + prompt_hash 是 sha256 hex
  - 返回的 ImageGenerationResult 各字段正确
- 跑 estimate_cost() → 必返 0.0

# 不要做的事

- 不要在 ManualImportProvider 内做 budget 检查（那是 T-1.5.5 + T-1.5.6 的职责）
- 不要在 ManualImportProvider 内调任何 LLM / 网络 API
- 不要实现 OpenAIImageProvider（推到 T-1.5.9）
- 不要写 prompt 模板的实质内容（推到 T-1.5.6）
- 不要给 ImageProvider Protocol 加 budget 参数 / retry 参数（按 LLMProvider 同款"接口最小化"）
- 不要 import google.genai 或 openai SDK
- 不要新建 /generator/visuals/ 子模块（保持扁平）

# 完成报告

- 接口签名 + ManualImportProvider 类骨架
- 测试输出（contract + manual_import 全过）
- ImageAsset 模型生成确认（`/generator/models/_generated/image_asset.py` 文件存在 + roundtrip 测试通过）
- commit + push（commit message: `feat(generator): add ImageProvider Protocol and ManualImportProvider (T-1.5.3)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.3_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- ImageProvider Protocol 与 LLMProvider 同源风格——最小接口（generate + estimate_cost），budget 不在 provider 内（ADR-011 + ADR-014）
- ManualImportProvider.estimate_cost = 0.0 是 ADR-014 约定，不是 bug
- 占位 prompt（"[PLACEHOLDER from T-1.5.3 — T-1.5.6 will fill]"）是有意的；T-1.5.6 会替换；不要建议本任务实现 prompt 模板
- prompt_hash = sha256(prompt 英文段) 用于追溯；不是密码学用途，不需要 HMAC

§3 已知约束：
- 本任务不实现 OpenAIImageProvider（T-1.5.9）
- 本任务不实现机械预检（T-1.5.4）
- 本任务不实现 budget 集成（T-1.5.5）
- 本任务不实现 generate_character_sheet 主函数（T-1.5.6）

§4 配套阅读：
- /docs/SCHEMA_v0.2.md（ImageAsset 字段表）
- /docs/DECISIONS.md ADR-014（双模生成策略）
- /generator/llm_provider.py + /generator/providers/gemini.py（接口风格参照）
- /generator/CLAUDE.md

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.4 ｜ image_validator（机械预检器）

```text
你的任务是为视觉资产实现机械预检器：分辨率 / 格式 / 文件大小 / alpha 通道 / 文件元数据 验证。
不做语义判断（如"是否含可识别角色"），那是 T-1.5.8 视觉 AI 判官的事。

# 模块边界（硬性）
允许修改 / 新建：
  - /validator/image_validator.py（**新建**）
  - /validator/__init__.py（重导出新接口）
  - /validator/tests/test_image_validator.py（**新建**）
  - /validator/tests/fixtures/（**新建**目录，存测试用最小图片）
  - /pyproject.toml（**GPT-5.5 L2 critique 4.4 修补**：仅追加 Pillow 依赖；不动其它字段）
严禁修改：
  - /validator/ 已有模块（schema_validator / graph_validator / consistency_validator）
  - /generator/、/schema/、/state/、/engine/、/content/
  - /docs/

# 必读
- /CLAUDE.md
- /validator/CLAUDE.md（如存在）
- /validator/__init__.py + 已有 validator 接口（参考风格）
- /docs/SCHEMA_v0.2.md（ImageAsset 字段约束）
- /docs/STAGE_1.5_TASKS.md（特别"机械预检器"段；维度划分）

# 待做

## 1. /validator/image_validator.py

接口：

```python
@dataclass
class ImageValidationError:
    code: str          # 短代码，如 "RESOLUTION_TOO_LOW" / "FORMAT_NOT_ALLOWED" / "ALPHA_REQUIRED"
    message: str       # 人类可读描述
    severity: Literal["error", "warning"]

def validate_image_asset(
    image_path: Path,
    *,
    asset_kind: Literal["character_sheet", "scene_background"],
    config: ImageValidationConfig | None = None,
) -> list[ImageValidationError]:
    """空列表 = 通过；含 severity=error 项 = 不可入库；severity=warning = 可入库但作者审阅时应注意"""

@dataclass
class ImageValidationConfig:
    min_width: int = 768
    max_width: int = 4096
    min_height: int = 768
    max_height: int = 4096
    allowed_formats: tuple[str, ...] = ("png", "webp")
    max_file_size_bytes: int = 8 * 1024 * 1024  # 8 MB
    require_alpha_for_character: bool = True
    forbid_alpha_for_background: bool = True
    require_aspect_ratio: tuple[float, float] | None = None  # (min_ratio, max_ratio)；None 不校验
```

校验维度（必须实现）：

| code | severity | 含义 |
|---|---|---|
| FILE_NOT_FOUND | error | image_path 不存在 |
| FORMAT_NOT_ALLOWED | error | 文件扩展名 / magic bytes 不在 allowed_formats |
| FILE_SIZE_EXCEEDED | error | > max_file_size_bytes |
| RESOLUTION_TOO_LOW | error | width 或 height < min |
| RESOLUTION_TOO_HIGH | error | width 或 height > max |
| ALPHA_REQUIRED | error | character_sheet 但无 alpha 通道 |
| ALPHA_FORBIDDEN | error | scene_background 但有 alpha 通道 |
| ASPECT_RATIO_OUT_OF_RANGE | warning | 在指定范围之外（仅当 require_aspect_ratio 非 None） |
| EXIF_PRESENT | warning | 含 EXIF / IPTC 元数据（隐私 / 文件膨胀） |

实现要点：
- 用 Pillow（PIL）读图；Pillow 应未在 pyproject.toml 中（T-1.5.1A 不加依赖；本任务负责），**本任务追加** Pillow 到 pyproject.toml dependencies（与阶段 1 加 google-genai 同级别）
- 读 magic bytes 而非依赖扩展名（防伪造）；用 `imghdr` 或自行读前 8 bytes
- alpha 检测：PIL.Image.mode 含 'A' 即有 alpha
- EXIF 检测：PIL.Image.getexif() 不为空即 warning
- 测试 fixture（**GPT-5.5 L2 critique 5.1 修补**）：rename 为更清晰的名字
  - `small_character.png`：512×768 RGBA（**故意**触发 RESOLUTION_TOO_LOW with default min_width=768；之前叫 valid_character.png 命名误导）
  - `perfect_character.png`：1024×1280 RGBA（默认配置下通过的真正"valid character"）
  - `valid_background.png`：1024×1024 RGB（重命名为 `perfect_background.png` 与 character 对称）
  - 其它 fixture（too_small / jpeg_disguised / with_exif / alpha_in_bg）保留

## 2. /validator/__init__.py

加入 `from .image_validator import validate_image_asset, ImageValidationError, ImageValidationConfig`。

## 3. 测试

/validator/tests/fixtures/ 准备最小测试图（脚本生成，不要 commit 大图）：
- valid_character.png：512×768 RGBA（小尺寸故意）
- valid_background.png：1024×1024 RGB
- too_small.png：100×100
- jpeg_disguised.png：JPEG 文件名为 .png（magic bytes 校验）
- with_exif.png：含 EXIF
- alpha_in_bg.png：背景但有 alpha

可以在 conftest.py 或 fixture function 里**用 Pillow 现场生成**测试图，避免把二进制图片提交到 git。

测试覆盖：
- 每个 code 至少一个 case 触发
- 一张完美图 → 空列表
- config 覆盖（如把 min_width 调高，原本通过的图变 RESOLUTION_TOO_LOW）

# 不要做的事

- 不要做语义判断（如"是否含人脸"、"角色是否符合本体卡"）
- 不要调任何 LLM / API
- 不要实现"图像内容相似度"（与基准图对比）—— 那是阶段 2/3 的事
- 不要把 magic bytes 检测放在框架代码外（保持封装）
- 不要把测试图作为二进制文件提交到 git（用 Pillow 现场生成）

# 完成报告

- 接口签名
- 测试输出（pytest -v；每个 code 一个 case）
- 新增依赖（如 Pillow）+ pyproject.toml diff
- commit + push（commit message: `feat(validator): add image_validator with mechanical pre-check (T-1.5.4)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.4_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 仅做可数值化机械预检；语义判断（如"是否含可识别角色"）推到 T-1.5.8 视觉 AI 判官（STAGE_1_ACCEPTANCE R8 教训：机械可检测维度不让 LLM 评）
- magic bytes 校验是为了防文件名伪造，不是过度设计
- 测试图现场用 Pillow 生成，不提交二进制；这是有意，避免 git 仓库膨胀

§3 已知约束：
- 本任务不集成入库流程（推到 T-1.5.7）
- 本任务不评估图像质量 / 美学（推到 T-1.5.8）
- ASPECT_RATIO_OUT_OF_RANGE 默认不开启（require_aspect_ratio=None）；T-1.5.7 入库时按 asset_kind 配置开启

§4 配套阅读：
- /docs/SCHEMA_v0.2.md（ImageAsset 字段约束）
- /docs/STAGE_1_ACCEPTANCE.md §4 R8（机械预检器教训）
- /validator/__init__.py + 已有 validator 接口

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.5 ｜ image_cost_log + image_budget 集成

```text
你的任务是为图像生成实现独立的成本日志 + budget 集成。manual 模式 estimate_cost=0 仍写日志（统计 manual 张数 + 走统一接口）。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/image_cost_log.py（**新建**）
  - /generator/image_budget.py（**新建**；不复用 budget.py，与文本日志分离）
  - /generator/tests/test_image_budget.py（**新建**）
  - /generator/tests/test_image_cost_log.py（**新建**）
严禁修改：
  - /generator/budget.py、/generator/cost_log.py（已为文本调用服务；不动）
  - /generator/llm_provider.py、/generator/providers/gemini.py、/generator/providers/manual_import.py、/generator/image_provider.py、/generator/generate_node.py、/generator/experiment.py、/generator/review_cli.py、/generator/metrics.py
  - /schema/、/state/、/engine/、/validator/、/content/
  - /docs/

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-012（文本预算治理；本任务参照风格）+ ADR-014（双模 + 图像预算）
- /docs/STAGE_1.5_TASKS.md（特别"锁定的架构决策"表 cost_log 行）
- /generator/budget.py + /generator/cost_log.py（参考实现 / 测试结构）

# 待做

## 1. /generator/image_cost_log.py

与阶段 1 cost_log.py 同款接口：

```python
def append(record: dict) -> None: ...  # 一行 JSON，append-only，必须 fsync
def read_today() -> list[dict]: ...  # 扫今天的行
```

写入路径：/generator/image_cost_log.jsonl（已在 .gitignore，T-1.5.1 加固）

字段（每行）：
- timestamp (ISO8601)
- mode ("manual" | "api")
- provider_id ("manual_import" | "openai_image_<model>")
- asset_kind ("character_sheet" | "scene_background")
- asset_id_stub
- n (生成张数，通常 1)
- size_w / size_h
- input_tokens (api 模式才有；manual 模式 null)
- cost_usd (manual 模式 0.0)

## 2. /generator/image_budget.py（**GPT-5.5 L2 critique 4.9 修补：拆分 check 与 log，并改用 asset_id_hint**）

```python
class ImageBudgetExceeded(Exception): ...

# check 阶段：只校验预算 + 抛异常；不写日志（因为此时 provider 还没生成 stub，调用方还在准备阶段）
def check(
    *,
    estimated_cost_usd: float,
    mode: Literal["manual", "api"],
) -> None:
    """raise ImageBudgetExceeded if 单次或当日累计超限"""

# log 阶段：provider 返回 stub 后由调用方写日志；记真实 stub
def log_charge(
    *,
    timestamp: datetime,
    mode: Literal["manual", "api"],
    provider_id: str,
    asset_kind: str,
    asset_id_stub: str,                      # **provider 返回后传入**（不再是 hint；GPT-5.5 4.9 修补）
    n: int,
    size: tuple[int, int],
    cost_usd: float,
    input_tokens: int | None = None,
) -> None:
    """写一行到 image_cost_log.jsonl；fsync"""
```

配置：
- DAILY_IMAGE_BUDGET_USD（默认 5.0；环境变量 `FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD` 覆盖）
- PER_CALL_IMAGE_BUDGET_USD（默认 1.0；环境变量 `FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD` 覆盖；ADR-014 单次硬卡 $1.00）

行为：
- `check()`：estimated_cost > PER_CALL → raise；today_total + estimated_cost > DAILY → raise；manual 模式（cost=0.0）→ **不抛**（永远通过）；本函数**不写日志**
- `log_charge()`：写一行到 image_cost_log.jsonl；记 deterministic stub；manual 模式 cost_usd=0.0 仍写（用于统计 manual 张数）
- 调用顺序由 T-1.5.6 generate_visual.py 编排：先 `check()` → 调 provider.generate() → provider 返回后用真实 stub 调 `log_charge()`

**重要**：原"统一 check_and_charge"接口被废弃，因为 stub 是 provider 创造的，调用方在 check 时还没有 stub（之前 plan 的逻辑链不闭环）。拆分后调用方需要做 try/finally 确保 provider 失败时仍能 log_charge（log_charge 接受 cost=0 + status flag 表示失败 — 由调用方决定）。如想极简，failed 时不调 log_charge 也合理（不写"未发生的 charge"日志），但 budget today_total 计算时不能少一笔。建议**默认行为**：provider 抛异常 → 不调 log_charge（视为"消费未发生"）；后续 retry 重新 check + log。

## 3. 测试

/generator/tests/test_image_budget.py：
- 单次超 PER_CALL → raise
- 累计超 DAILY → raise
- manual 模式（cost=0）→ 永远通过，仍写日志
- api 模式（cost=0.05）→ 通过，写日志
- 跨日重置（mock 时间）

/generator/tests/test_image_cost_log.py：
- append + read_today
- 文件不存在时 read_today 返回 []
- 多行 JSONL 解析

测试用 tmp_path fixture 隔离 log 文件，**不污染真实 image_cost_log.jsonl**。

# 不要做的事

- 不要把 image_cost_log 与 cost_log 合并（独立是 P2 决策）
- 不要在 image_budget.py 里调 LLM / Image API
- 不要在 ImageProvider 实现里调 image_budget（那是 T-1.5.6 主函数的职责）
- 不要做异步写入

# 完成报告

- 接口签名
- 测试输出
- commit + push（commit message: `feat(generator): add image_cost_log and image_budget (T-1.5.5)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.5_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- image_cost_log 与文本 cost_log 分离是 P2 决策；不要建议合并
- manual 模式 cost=0.0 仍走 budget 接口 + 仍写日志是 ADR-014 约定（统计 manual 张数 + 接口统一）；不要建议短路 budget
- 单次硬卡 $1.00 / 日 $5.00 是 ADR-014 数字；不要建议改

§3 已知约束：
- 本任务不在 ImageProvider 内调用 budget（那是 T-1.5.6 主函数的职责）
- 本任务不实现 metrics 聚合（推到 T-1.5.8 visual_experiment）

§4 配套阅读：
- /docs/DECISIONS.md ADR-012 + ADR-014
- /generator/budget.py + /generator/cost_log.py（参考实现）
- /docs/STAGE_1_ACCEPTANCE.md §4 R7（cost_log 高估教训；本任务尚未解决，留给阶段 2）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.6 ｜ generate_character_sheet + generate_scene_background 主函数 + prompt 模板

```text
你的任务是实现阶段 1.5 核心目标函数：generate_character_sheet 和 generate_scene_background，串联 ImageProvider + image_budget + image_cost_log + prompt 模板。本任务**不**实现入库（推到 T-1.5.7）。
作者已通过 STAGE_1.5_TASKS.md 把 vellin / corvan / aelwin / 1 场景作为试点 fixture 锁定。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/generate_visual.py（**新建**；含 generate_character_sheet + generate_scene_background）
  - /generator/visual_context.py（**新建**；视觉版的 context_assembler）
  - /generator/prompts/visual/__init__.py（**新建**）
  - /generator/prompts/visual/system_character.md（**新建**；中英双版本）
  - /generator/prompts/visual/system_background.md（**新建**；中英双版本）
  - /generator/prompts/visual/character_features.py（**新建**；vellin/corvan/aelwin 固定特征 dict）
  - /generator/tests/test_generate_visual.py（**新建**）
**只读**导入：
  - /generator/image_provider.py、/generator/providers/manual_import.py、/generator/image_budget.py、/generator/image_cost_log.py、/generator/models/_generated/image_asset.py
  - /state/ontology/<character>.json、/content/test_scene_v0/scene.json、/content/visuals/_reference/（用于读基准图清单；如目录空则降级）
严禁修改：
  - /schema/、/state/、/engine/、/validator/、/content/、/docs/
  - /generator/llm_provider.py、/generator/providers/gemini.py、/generator/budget.py、/generator/cost_log.py、/generator/generate_node.py、/generator/context_assembler.py、/generator/experiment.py、/generator/review_cli.py、/generator/metrics.py
  - /generator/providers/manual_import.py（已实现；不动）
  - /generator/image_budget.py、/generator/image_cost_log.py（已实现；不动）

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-014（角色一致性 C+B 兜底；manual 两段式契约）
- /docs/STAGE_1.5_TASKS.md（特别 NPC 分级 + 角色一致性策略 + manual 契约）
- /generator/generate_node.py + /generator/context_assembler.py（参考主函数风格 + B+ 上下文模式）
- /content/test_scene_v0/scene.json（场景 + 角色锚点）
- /state/ontology/waystation.json（**GPT-5.5 L2 critique 3.1 修补**：聚合本体文件，含 entities[] 数组——vellin/corvan/aelwin 在 entities[] 中作为 type=character 项；**不要预设三个独立桩文件**）
- /docs/reviews/master_plan/2026-04-30_synthesis.md §5 + §3 U-CL-3（mini probe gate 来源）
- /docs/reviews/stage_1_5_plan/2026-05-01_gpt55_critique.md §3.2 + §3.3（mini probe + 数据流贯穿来源）

# 启动前置 gate（Round 5 U-CL-3 硬闸门；**GPT-5.5 L2 critique 3.2 修补：去 import CLI 依赖**）

**主任务（§待做 §1–§5）开始前必须先跑 vellin mini probe**。

目的：在投入 vellin 重档（10 张）+ corvan/aelwin 轻档（5 + 4 张）之前，先用 5 张验证 prompt 模板 + character_features 的角色一致性能否达到 C+B 兜底承诺（ADR-014）。

mini probe 流程（**prompt-package 级**，不依赖尚未实现的 T-1.5.7 import CLI）：

1. 实现完 generate_character_sheet（§待做 §1–§4）后，**不要立刻跑全量**
2. 用 vellin 的 character_features + 5 个表情/姿势组合（neutral / smiling / wary / tense / looking_distant）
3. 通过 ManualImportProvider 产 5 个 prompt 包到 `/content/visuals/_pending/`
4. 提示作者：复制每个 `_pending/<asset_id>/prompt.md` 英文段到 chatgpt.com → 生成 → 下载到对应 `_pending/<asset_id>/<asset_id>.png`
5. 作者**直接打开 5 个 PNG 并排比较**（finder 多选预览 / Preview app / 任意工具）；**无需 import CLI**——本 gate 仅评估 prompt 一致性，不做入库
6. 作者人工审：5 张里 ≥ 4/5 是同一人（脸特征 / 服装 / 发型一致；允许表情/角度自然差异）
7. 判定结果**写入 T-1.5.6 完成报告**（不写 /docs/CLEANUP.md，因 T-1.5.6 边界禁止 docs 写入）

**通过判定**：
- ≥ 4/5 通过 → 主任务继续（§5 测试 + 全量批次准备）；完成报告写"mini probe pass: X/5"
- < 4/5 通过 → **回炉 prompt 模板**：
  - 检查 character_features.vellin 描述是否够具体（眼睛颜色 / 发色 / 发型 / 服饰细节 / 标志性特征）
  - 检查 system_character.md 英文段的"角色固定特征段"是否优先级够高（建议放 prompt 头部前 3 段）
  - 检查 style_reference_paths 是否注入到 prompt（如 _reference/ 空目录降级时要 WARN）
  - 调整后重跑 mini probe；最多回炉 2 次（共 3 次）
  - 第 3 次仍 < 4/5 → **暂停主任务**；在 T-1.5.6 完成报告里写 "**RD5-U-CL-3 alert**: vellin 一致性未达标 X/5，需作者拍板是降标 / 换 provider / 暂停 1.5"，**告知作者后停下**（不动 docs，由作者另开会话决定 /docs/CLEANUP.md 写入）
- 跳过 mini probe 直接全量 → **不允许**；本闸门为硬闸门

成本：5 张 manual = $0；时间约 30 分钟（作者侧）。
出处：synthesis §5 + Claude critique §4.2（U-CL-3）+ GPT-5.5 L2 critique §3.2 修补。

# 待做

## 1. /generator/visual_context.py

```python
@dataclass
class VisualGenerationContext:
    character_card: dict | None      # asset_kind=character_sheet 时填；从 /state/ontology/waystation.json entities[type=character] 读
    location_card: dict | None       # asset_kind=scene_background 时填；从 scene.json 或 entities[type=scene] 读
    style_reference_paths: list[Path]  # /content/visuals/_reference/ 下的基准图
    character_features: dict | None  # B 兜底：固定特征字典（眼睛颜色/发型/服装；从 character_features.py 取）

# GPT-5.5 L2 critique 4.3 修补：主接口用 target_ref / target_type；character_ref / location_ref 仅作向后兼容镜像
@dataclass
class CharacterSheetRequirement:
    target_ref: str                  # 主键，例如 "char_vellin"
    target_type: Literal["character"] = "character"  # 锁定为 character
    n: int                           # 重档=10; 轻档=5（建议）
    expressions: list[str]           # ["neutral", "smiling", "wary", ...]；至少 n 个
    poses: list[str]                 # ["torso_up", "full_body"]；可选

@dataclass
class SceneBackgroundRequirement:
    target_ref: str                  # 主键，例如 "scene_waystation_of_iron_oath"
    target_type: Literal["location", "scene"]  # 当前试点 fixture 用 "scene"（与 entities[type=scene] 对齐）；后续如有 location-only 资产用 "location"
    n: int                           # 1–3
    times_of_day: list[str]          # ["dusk", "interior_lamplight"]
    weather: list[str] | None        # 可选

def assemble_visual_context_for_character(target_ref: str, ...) -> VisualGenerationContext: ...
def assemble_visual_context_for_location_or_scene(target_ref: str, target_type: Literal["location", "scene"], ...) -> VisualGenerationContext: ...
```

读取本体桩时优雅降级（缺字段不报错）。
**读取路径**：character_card 从 `/state/ontology/waystation.json` 的 `entities[]` 中找 `id == target_ref` AND `type == "character"` 的对象；location/scene_card 从 `entities[]` 中找 `id == target_ref` AND `type` ∈ {"location", "scene"} 的对象（当前试点 fixture 在 entities[] 中是 type="scene"）。如 entities[] 中找不到，从 scene.json 反查 location_ref 字段 + 降级。

## 2. /generator/prompts/visual/character_features.py

```python
# 角色固定特征（B 兜底；ADR-014 一致性策略）
# 阶段 1.5 试点；阶段 2/3 转 YAML 化由作者在工坊维护
CHARACTER_FEATURES: dict[str, dict] = {
    "char_vellin": {
        "build": "lean, late 20s, road-worn",
        "eyes": "amber, narrow",
        "hair": "ash brown, shoulder-length, tied back loosely",
        "scars": "fresh diagonal scar over left brow, ~3cm",
        "outfit": "innkeeper's leather apron over a coarse linen shirt, sleeves rolled",
        "props": "worn copper rings on right hand, faint ink stains on fingers",
        "demeanor": "tense alertness behind a forced smile",
    },
    "char_corvan": {
        # ...由你基于 scene.json 中 corvan 的描述补全
    },
    "char_aelwin": {
        # ...同上
    },
}
```

**注意**：从 [content/test_scene_v0/scene.json](content/test_scene_v0/scene.json) 的 narration 与 /state/ontology/ 中的桩字段反推；不要捏造与 narration 矛盾的特征（如把 vellin 的眉骨伤换成下巴伤）。

## 3. /generator/prompts/visual/system_character.md + system_background.md

每文件含：
- 中文段（# 中文 / 给作者审 / 解释设计意图）
- 英文段（# English / 给 ChatGPT / GPT-Image API）

英文段必含元素（ADR-014 一致性 C+B 兜底）：
- 风格基准描述（半写实 + 油画感 + 戏剧光影；BG3 / Disco Elysium 参考语；不点名具体游戏品牌避免 IP 争议）
- 角色固定特征段（从 character_features dict 注入）
- 场景上下文（情境氛围 / 时间 / 光源；从本体桩读）
- 镜头规格（character_sheet：torso-up portrait，face clearly readable；scene_background：environment shot，no characters visible）
- 输出规格（PNG，含 alpha for character；no alpha for background；1024×1024 default 或更高）
- 否定段（no modern items, no text/typography in image, no signature, no watermark）

中文段直接对应英文段；作者读中文版决定是否调 prompt。

## 4. /generator/generate_visual.py

```python
def generate_character_sheet(
    *,
    requirement: CharacterSheetRequirement,
    provider: ImageProvider,
    mode: Literal["manual", "api"] = "manual",
) -> list[VisualGenerationResult]:
    # GPT-5.5 L2 critique 4.9 修补：deterministic asset_id_stub 在 orchestrator 层生成；budget 拆 check + log_charge 调用顺序确定
    # 1. assemble_visual_context_for_character(target_ref=requirement.target_ref)
    # 2. 加载 system_character.md prompt 模板
    # 3. 渲染 prompt（注入 character_features + ontology card + style reference）
    # 4. for each expression × pose 组合：
    #    a. asset_id_stub = make_deterministic_stub(target_ref, asset_role, variant_label, n_idx)
    #       例: f"img_{target_ref_short}_{variant}_{ts}_{idx:02d}" — 保证唯一 + deterministic
    #    b. estimated_cost = provider.estimate_cost(n=1, size=...)
    #    c. image_budget.check(estimated_cost_usd=estimated_cost, mode=mode)  # 仅校验，不写日志
    #    d. result = provider.generate(prompt=..., asset_kind="character_sheet",
    #                                  target_ref=requirement.target_ref,
    #                                  target_type="character",
    #                                  asset_role="character_sheet",
    #                                  asset_id_stub=asset_id_stub,        # 传入 deterministic stub
    #                                  variant_label=variant)
    #    e. image_budget.log_charge(timestamp=now, ..., asset_id_stub=result.asset_id_stub, cost_usd=result.cost_usd)
    #    f. 把结果包成 VisualGenerationResult
    # 5. 任何阶段抛 ImageBudgetExceeded → 中止剩余 + 返回已成功的部分（带 partial_failure 标记）
    # 6. provider 实现层抛任何错误（manual 模式不会抛；api 模式可能） → 包成 failure_reason 并记 partial_failure；**不调 log_charge**（消费未发生）
    # **不抛异常给调用方**

def generate_scene_background(
    *,
    requirement: SceneBackgroundRequirement,
    provider: ImageProvider,
    mode: Literal["manual", "api"] = "manual",
) -> list[VisualGenerationResult]:
    # 同上结构；调 provider.generate 时:
    #   target_ref=requirement.target_ref
    #   target_type=requirement.target_type  # "scene" 或 "location"
    #   asset_role="scene_background"
    ...

@dataclass
class VisualGenerationResult:
    success: bool
    asset_id_stub: str
    prompt_package_path: Path | None  # manual 模式
    image_bytes: bytes | None         # api 模式
    failure_reason: str | None
    cost_usd: float
    raw_metadata: dict
```

## 5. 测试 /generator/tests/test_generate_visual.py

不调真实 API；用 FakeImageProvider 注入：
- scenario_1: manual 模式 + character_sheet（n=3 表情）→ 3 个 prompt 包写入 _pending（用 tmp_path 隔离）
- scenario_2: manual 模式 + scene_background（n=1）
- scenario_3: api 模式 mock 返回 image_bytes（**不要真调 OpenAI**）
- scenario_4: image_budget.check_and_charge 抛 ImageBudgetExceeded → 返回 partial_failure（成功部分仍返回）
- scenario_5: provider 抛异常 → 单条失败不影响后续条
- scenario_6: 缺 character_features 词条 → 优雅降级（warning + 用 ontology 桩描述兜底）

# 不要做的事

- 不要在本任务实现 import CLI 或入库（推到 T-1.5.7）
- 不要在本任务实现视觉判官（推到 T-1.5.8）
- 不要直接 import openai 或 google.genai SDK（必须经 ImageProvider 接口）
- 不要为 OpenAIImageProvider 写"如果 OpenAI 那就……"分支代码（YAGNI；T-1.5.9）
- 不要把 character_features 硬编码在 generate_visual.py 内（必须独立文件 character_features.py）
- 不要把 prompt 模板的英文段 + 中文段拆到不同文件（一文件双段，便于作者对照）
- 不要把基准图（_reference/）的内容读进 prompt 文本（GPT-Image 接受 reference image 作为输入参数；本任务**只**在 prompt 文本里**引用**基准图路径，由 OpenAIImageProvider T-1.5.9 决定是否实际上传——manual 模式下作者人工对照基准图）

# 完成报告

- generate_character_sheet / generate_scene_background 签名 + 流程图（文字描述）
- 6 个 scenario 测试输出
- character_features.py 三个角色填充情况（vellin 重档 / corvan 轻档 / aelwin 轻档）
- prompt 模板节选（system_character.md 中英文各前 10 行）
- commit + push（commit message: `feat(generator): implement generate_character_sheet and generate_scene_background (T-1.5.6)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.6_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 一致性 C+B 兜底（容忍细微差异 + prompt 描述固定特征）是 ADR-014 决策；不要建议加 ControlNet / LoRA
- character_features.py 是 Python dict 而非 YAML 是有意（阶段 1.5 试点；阶段 2/3 再 YAML 化）
- prompt 模板中英双段一文件是有意（作者对照方便；不要拆文件）
- 基准图（_reference/）只在 prompt 文本里引用路径，不读图片字节—— OpenAIImageProvider（T-1.5.9）决定是否上传
- partial_failure 模式（不抛异常给调用方）沿用阶段 1 generate_node 模式

§3 已知约束：
- 本任务不实现入库（T-1.5.7）
- 本任务不实现视觉判官（T-1.5.8）
- 本任务不实现 OpenAIImageProvider（T-1.5.9）；scenario_3 用 mock
- character_features 不与本体严格 schema 对齐（路径 A：不正式化角色 Schema）

§4 配套阅读：
- /docs/DECISIONS.md ADR-014（一致性策略 + manual 契约）
- /docs/STAGE_1.5_TASKS.md "锁定的架构决策"表
- /generator/generate_node.py + /generator/context_assembler.py（B+ 上下文 / partial_failure 模式参考）
- /content/test_scene_v0/scene.json（角色 narration / location 描述源）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.7 ｜ image_import CLI + manifest.json + 入库流程

```text
你的任务是实现 manual 模式入库 CLI：扫描 _pending/ → image_validator 校验 → 落地到 /content/visuals/<id>/ → 更新 manifest.json + 角色桩 visual_assets。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/image_import.py（**新建**；CLI 入口）
  - /generator/manifest.py（**新建**；manifest.json 读写封装）
  - /generator/import_log.py（**新建**；**GPT-5.5 L2 critique 4.7 修补**——结构化 import 日志，供 visual_metrics 与 1.5 验收复算）
  - /generator/tests/test_image_import.py（**新建**）
  - /generator/tests/test_manifest.py（**新建**）
  - /generator/tests/test_import_log.py（**新建**）
  - /content/visuals/manifest.json（**新建** empty skeleton；**GPT-5.5 L2 critique 4.8 修补**——本任务 commit 含初始 `{"schema_version": "0.2.0", "assets": {}}`，避免首次运行特殊路径）
  - /content/visuals/<character_or_location_id>/（运行时由 CLI 创建；本任务不预建子目录）
  - /state/ontology/waystation.json（**GPT-5.5 L2 critique 3.1 修补**——CLI 修改 entities[] 中 type=character 项的 visual_assets 数组；**严禁修改任何非 visual_assets 字段**）
**只读**导入：
  - /generator/image_provider.py、/generator/models/_generated/image_asset.py、/validator/image_validator.py
严禁修改：
  - /schema/、/engine/、/generator/ 其他模块、/docs/
  - /content/test_scene_v0/、/content/visuals/_reference/、/content/visuals/_pending/（_pending 由 ManualImportProvider 维护）
  - /validator/ 其他模块
  - /state/ontology/waystation.json 中 entities[] 内**任何**非 visual_assets 字段（id / display_name / type 等）
  - /state/ontology/waystation.json 顶层结构（entities[] 元素增删；type=scene 项的 visual_assets——本任务暂不写 scene 项 visual_assets，按 manifest target_ref 路线）

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md + /content/CLAUDE.md
- /docs/SCHEMA_v0.2.md（ImageAsset 字段表）
- /docs/STAGE_1.5_TASKS.md（特别 manual 模式 + manifest.json 形态）
- /generator/providers/manual_import.py（理解 _pending/ 目录结构）
- /validator/image_validator.py（理解校验接口）

# 待做

## 1. /generator/manifest.py

```python
@dataclass
class Manifest:
    schema_version: Literal["0.2.0"]   # GPT-5.5 L2 critique 5.3 修补：与 JSON 字段名统一（之前叫 version 引发命名漂移）
    assets: dict[str, ImageAsset]       # asset_id -> ImageAsset

def load_manifest(path: Path = Path("content/visuals/manifest.json")) -> Manifest: ...
def save_manifest(manifest: Manifest, path: Path = Path("content/visuals/manifest.json")) -> None: ...
def add_asset(manifest: Manifest, asset: ImageAsset) -> Manifest: ...  # 返回新实例（不可变风格）
def remove_asset(manifest: Manifest, asset_id: str) -> Manifest: ...
```

manifest.json 形态（含 target_ref 等 Round 5 U-GPT-3 字段；本任务**首次创建时是 empty skeleton 直接 commit**——见模块边界）：

```json
{
  "schema_version": "0.2.0",
  "assets": {
    "img_vellin_neutral_20260501120000": {
      "asset_id": "img_vellin_neutral_20260501120000",
      "asset_kind": "character_sheet",
      "asset_role": "character_sheet",
      "target_ref": "char_vellin",
      "target_type": "character",
      "character_ref": "char_vellin",
      "location_ref": null,
      "source_mode": "manual",
      "...": "（完整 ImageAsset 对象，含 reference_ids / open_source_ok / commercial_ok 等 provenance 字段）"
    }
  }
}
```

empty skeleton（本任务初始 commit）：
```json
{
  "schema_version": "0.2.0",
  "assets": {}
}
```

文件不存在 → load_manifest 返回 empty Manifest。
save_manifest 必须 fsync。

## 2. /generator/image_import.py（CLI）

```bash
python -m generator.image_import --asset-id <asset_id_stub>
python -m generator.image_import --all-pending
python -m generator.image_import --dry-run --all-pending  # 不落盘，只打印
```

流程（per asset）：
1. 在 /content/visuals/_pending/<asset_id_stub>/ 找 PNG（约定：与 asset_id_stub 同名 .png；如有多个，警告并跳过）
2. 读 meta.json（**必含** target_ref / target_type / asset_role / asset_kind / source_mode / variant_label / prompt_hash 等——T-1.5.3 ManualImportProvider 已写入；如缺这些字段说明上游违约，记错误日志 + 拒收）
3. 调 image_validator.validate_image_asset(png_path, asset_kind=...) → 任何 severity=error → 移到 _pending/_rejected/<asset_id>/ + 写**结构化 import_log**
4. **target_ref / character_ref / location_ref 一致性校验**（**GPT-5.5 L2 critique 4.3 修补**；image_validator 语义层）：
   - target_type=character → meta.character_ref 必 == target_ref；location_ref 必 null
   - target_type=location → meta.location_ref 必 == target_ref；character_ref 必 null
   - target_type=scene → meta.location_ref 可 == target_ref（向后兼容）；character_ref 必 null
   - 不一致 → severity=error → 拒收
5. 通过 → 计算最终路径（按 target_type）：
   - target_type=character → /content/visuals/<character_id>/<asset_id>.png（character_id = target_ref 去 char_ 前缀）
   - target_type=location → /content/visuals/<location_id>/<asset_id>.png（location_id = target_ref）
   - target_type=scene → /content/visuals/<scene_id>/<asset_id>.png（scene_id = target_ref 去 scene_ 前缀，或保留全名——选一种实现，在测试 fixture 中固定）
6. 创建目标目录（如不存在）→ 移动 PNG（用 shutil.move）→ 计算 file_size_bytes / has_alpha 等
7. 构造 ImageAsset 对象（**含 target_ref / target_type / asset_role 必填**——从 meta.json 读取，**严禁猜**）+ manifest.add_asset()
8. **仅在 target_type=character 时**更新 /state/ontology/waystation.json 的 entities[] visual_assets 数组：
   - 读 /state/ontology/waystation.json → JSON
   - 在 entities[] 中找 id == target_ref AND type == "character" 的对象
   - 在该对象的 visual_assets[] 中追加完整 ImageAsset dict（路径 A 决策；P0.1）
   - **不要碰** entities[] 中的非 visual_assets 字段（id / display_name / type）
   - **不要碰** entities[] 中 type=scene 项（按 manifest target_ref 路线，不嵌入本体）
   - 写回，pretty-print 4 空格 + 末尾换行
9. save_manifest()
10. **写 import_log**（**GPT-5.5 L2 critique 4.7 修补**）：每个入库或拒收都写一行 JSONL
11. 删 _pending/<asset_id_stub>/ 整个目录（成功后清理；如要回溯，已在 manifest + import_log）；**校验失败时**目录移到 _pending/_rejected/<asset_id>/ 不删除

dry-run 模式：跳过 5–11，只打印计划的动作 + 写 import_log（with dry_run=true 标记）。

## 2.5 /generator/import_log.py（**GPT-5.5 L2 critique 4.7 修补**）

接口：

```python
def append(record: dict) -> None: ...  # 一行 JSON，append-only，必须 fsync
def read_all(batch_name: str | None = None) -> list[dict]: ...  # 全量或按 batch 过滤
```

写入路径：/generator/import_log.jsonl（gitignore，类比 image_cost_log.jsonl）

字段（每行）：
- timestamp (ISO8601)
- asset_id_stub
- batch_name (来自 visual_experiment 时的 batch；如直接跑 image_import 单个 stub，可为 null)
- target_ref / target_type / asset_role
- status: "imported" | "rejected" | "dry_run"
- validation_errors: list[str] (status=rejected 时填；image_validator 返回的 code 列表)
- rejected_reason: str | null (free-form；如"PNG missing"/"meta.json malformed")
- final_asset_id: str | null (status=imported 时 = asset_id_stub；其它 null)
- final_path: str | null (status=imported 时为相对仓库根的 PNG 路径)
- imported_at: ISO8601 (status=imported 时填)

T-1.5.8 visual_metrics.py + T-1.5.10 验收报告都从 import_log.jsonl 读，不再扫 _rejected/ 目录或回忆。

## 3. 测试 /generator/tests/test_image_import.py

用 tmp_path 隔离整个 /content/visuals/ + /state/ontology/ + /content/visuals/manifest.json：
- test_import_one_character_asset：通过校验 → 落地 + manifest 更新 + visual_assets 更新
- test_import_one_background_asset：同上但 location 路径
- test_import_validation_fail：校验 error → 移到 _rejected/，manifest 不变，visual_assets 不变
- test_dry_run：不落盘任何东西
- test_all_pending_partial_fail：3 个 pending，1 个失败 → 2 个入库 + 1 个 rejected

## 4. 测试 /generator/tests/test_manifest.py

- load 不存在文件 → empty Manifest
- save + load roundtrip
- add_asset / remove_asset 不可变
- schema 版本字段保留

# 不要做的事

- 不要在本任务实现"批量重新生成"功能（YAGNI）
- 不要做 watchdog / 自动监视目录（P2 决策：手动触发）
- 不要把 manifest.json 拆成多文件（单文件足够；scale 时再考虑）
- 不要在校验失败时**删除** PNG（移到 _rejected/ 保留作者复盘；导入流程不可恢复时仍记 import_log status=rejected）
- 不要在入库时**重新校验整个 manifest**（增量更新；正确性靠测试覆盖）
- 不要修改 waystation.json entities[] 的非 visual_assets 字段（边界硬约束）
- 不要修改 entities[] 中 type=scene 项（按 manifest target_ref 路线；本任务不写 scene 项 visual_assets）
- 不要 import target_ref / target_type / asset_role 时去猜（必须从 meta.json 读；缺字段拒收）

# 完成报告

- CLI 用法说明
- 5 个测试 scenario 输出
- manifest.json 初始形态展示
- commit + push（commit message: `feat(generator): add image_import CLI and manifest.json management (T-1.5.7)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.7_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 手动触发不监视目录是 P2 决策（避免 macOS watchdog 边角问题）；不要建议加 watchdog
- 校验失败移到 _rejected/ 而非删除是有意（作者复盘）
- 角色桩 visual_assets 直接嵌入完整 ImageAsset 对象（不通过 asset_id 引用）是 P0.1 决策（路径 A：简化层次）
- manifest.json 是单文件索引，不是分文件；scale 时再考虑
- character_id 去 char_ 前缀是目录命名约定（content/visuals/vellin/...），不是 schema 字段

§3 已知约束：
- 本任务不实现 review CLI / experiment（推到 T-1.5.8）
- 本任务不实现 OpenAIImageProvider 入库路径（T-1.5.9 实现 OpenAI provider 后，**api 模式 result 含 image_bytes** 直接落盘流程也走本 CLI）—— 注意检查接口是否能优雅扩展
- 本任务**修改 /state/ontology/ 角色桩**是合法的（T-1.5.2 留了空数组；本任务填充）

§4 配套阅读：
- /docs/SCHEMA_v0.2.md
- /generator/providers/manual_import.py（理解 _pending/ 目录结构）
- /validator/image_validator.py
- /docs/STAGE_1.5_TASKS.md "manual 模式契约"

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.8 ｜ visual_experiment + review CLI（图像版）+ 视觉 AI 判官 prompt（粗起）

```text
你的任务是为阶段 1.5 验收提供"实验 + 审阅 + 视觉 AI 判官"工具链（图像版），与阶段 1 的 experiment / review_cli / metrics 三件套同源。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/visual_experiment.py（**新建**；类比 experiment.py）
  - /generator/visual_review_cli.py（**新建**；类比 review_cli.py）
  - /generator/visual_metrics.py（**新建**；类比 metrics.py）
  - /generator/prompts/visual/REVIEW_PROMPT_AI_JUDGE_VISUAL.md（**新建**；视觉 AI 判官粗起一版）
  - /generator/tests/test_visual_experiment.py / test_visual_review_cli.py / test_visual_metrics.py
**只读**导入：
  - /generator/generate_visual.py、image_provider.py、manifest.py、image_import.py、image_budget.py、image_cost_log.py
严禁修改：
  - /generator/experiment.py、/generator/review_cli.py、/generator/metrics.py（已为文本服务；不动）
  - /schema/、/state/、/engine/、/validator/、/content/、/docs/
  - /generator/ 其他模块

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/STAGE_1.5_TASKS.md（特别 接受率判定者 = 作者本人 + 机械 + AI 判官辅助）
- /docs/STAGE_1_ACCEPTANCE.md §4 R6 + R8（AI 判官替代教训 / 系统性放水教训）
- /generator/experiment.py + /generator/review_cli.py + /generator/metrics.py（参考结构）
- 阶段 1 21 维度判官 prompt（在 /generator/prompts/ 或 commit 4118b36；理解结构 / 不要直接复用）

# 待做

## 1. /generator/visual_experiment.py

CLI: `python -m generator.visual_experiment --batch-name <name> --target <target_ref> --target-type <character|location|scene> --asset-role <character_sheet|scene_background> --n <N> --mode <manual|api>`（**GPT-5.5 L2 critique 4.3 修补**：用 target_ref + target_type；asset-role 替代 asset-kind 以与 schema 字段名对齐）

流程：
1. 读 batch 配置（fixture 集合：vellin n=10 / corvan n=5 / aelwin n=4 / 1 location n=1，作者可手动跑 4 次 batch）
2. 用 generate_character_sheet / generate_scene_background 生成 → manual 模式产 prompt 包到 _pending/
3. 输出落地：/generator/experiments/<timestamp>_<batch_name>/
   - results.jsonl（每行一个 VisualGenerationResult 序列化）
   - summary.txt（生成数 / 成本 / 成功率 / pending 数）
   - prompt_packages/（**软链或拷贝**到 _pending 的对应目录列表，便于作者后续追踪本 batch）
4. 启动时打印当日剩余 image_budget
5. 抛 ImageBudgetExceeded → 立即停 + 落地已成功部分

manual 模式后**作者侧手工**继续：去 chatgpt.com 生成 → 下载到 _pending/<asset_id>/ → 跑 image_import → 跑 visual_review_cli。

## 2. /generator/visual_review_cli.py

CLI: `python -m generator.visual_review_cli --batch-dir <path> [--web]`（**GPT-5.5 L2 critique 4.10 修补**：模块名与文件名一致 visual_review_cli；不再用 visual_review）

终端默认行为：
- 读 batch 的 results.jsonl + 关联到 manifest.json 中已入库的 ImageAsset
- 依次显示每张图：
  - 元数据（asset_id / target_ref / target_type / 表情 / 姿势 / size / file_path）
  - 调 macOS `open <file_path>`（macOS 原生 Preview；其他平台报错提示用 --web）
- 操作：[A]ccept / [R]eject / [S]kip
- Reject 时输入一行原因（如"角色脸不一致"、"现代物品穿帮"）
- 输出：与 batch-dir 同级的 visual_review_log.jsonl，每行 {asset_id, accepted, reason, reviewed_at, mechanical_check_passed}
- 可中断、可继续

`--web` 选项：起一个最小 HTTP server（http.server）+ 自动打开浏览器看缩略图列表（不强制 React/Vue；纯 HTML + 静态生成的 index.html 即可）

测试要求：在 test_visual_review_cli.py 中至少跑一次 `python -m generator.visual_review_cli --help` 通过（防止模块名漂移导致作者卡死）。

## 3. /generator/visual_metrics.py

```python
def compute_visual_metrics(batch_dir: Path) -> dict:
    """
    返回（GPT-5.5 L2 critique 4.7 修补：从 import_log.jsonl 而非扫目录读）：
    - total_assets_attempted
    - total_pending_packages_generated  # manual 模式 = 这个数
    - total_imported  # 从 import_log status=imported 计数
    - total_rejected  # 从 import_log status=rejected 计数
    - mechanical_check_pass_rate  # imported / (imported + rejected)
    - rejected_reason_top_5  # 从 import_log.rejected_reason / validation_errors 聚类
    - acceptance_rate (作者审阅通过率；read from visual_review_log.jsonl；分母 = imported；分子 = accepted)
    - reject_reason_top_5  # 从 visual_review_log
    - total_cost_usd  # 从 image_cost_log.jsonl 按 batch_name 过滤求和
    """
```

CLI: `python -m generator.visual_metrics --batch-dir <path>`

数据源（**重要**）：
- machanical 通过率 / 拒收原因 → /generator/import_log.jsonl（T-1.5.7 写）
- 作者审阅接受率 → batch-dir/visual_review_log.jsonl（visual_review_cli 写）
- 成本 → /generator/image_cost_log.jsonl（T-1.5.5 写）
- batch 元数据 → batch-dir/results.jsonl（visual_experiment 写）

## 4. dev/prod parity smoke test（Round 5 C4 软闸门）— **GPT-5.5 L2 critique 4.6 修补：实际脚本移到 T-1.5.9**

**目的**：验证 manual 模式（ChatGPT Plus 网页 GPT-Image）与 API 模式（OpenAI Images API gpt-image-1）的 prompt 同源性假设——这是 ADR-014 的核心假设但未实证。

**实施位置**：parity smoke 必须 import OpenAIImageProvider，而 T-1.5.9 是可推后的——本任务（T-1.5.8）**不实施** parity smoke 脚本。**T-1.5.9 OpenAIImageProvider 落地时**同 commit 内附带 visual_parity_smoke.py 脚本 + 测试。

本任务（T-1.5.8）只在 visual_metrics.py 的 metrics 字段里**预留** parity-related 字段（如 `parity_smoke_status: "ran" | "not_ran" | "skipped_no_api_key"`），并在 T-1.5.10 验收报告位置预留 R1.5-* 占位。

**流程描述**（仅供 T-1.5.9 实施时参考；本任务不实施）：

CLI（在 T-1.5.9 内提供）：`python -m generator.visual_parity_smoke --prompts <path> [--n 3]`

1. 读 3 条已审核通过的 prompt 文本（建议从 vellin / corvan / 1 location 各取 1 条）
2. 对每条 prompt 在 manual + API 双模下各产 1 张
   - manual: 走 ManualImportProvider → prompt 包到 _pending/parity/<prompt_id>/manual/
   - api: 走 OpenAIImageProvider（**需 OPENAI_API_KEY**；如无 key 则任务降级为"未跑"）
3. 对每对图作者人工对比：风格漂移评分（0=完全一致；1=轻微差异可忽略；2=显著差异需 prompt 调）
4. 输出 /generator/experiments/parity_smoke_<timestamp>/parity_report.md（含并排对比 + 作者评估；总结 3 对里 ≥ 2 对评分 ≤ 1 = 假设站得住）

**成本**：API 部分 ≈ 3 张 × $0.17 = $0.51（一次性）；manual = $0。

**未跑情况**：
- 作者无 OPENAI_API_KEY 时 → 直接跳过；T-1.5.10 验收报告显式 R1.5-* "C4 parity smoke test 未跑（OpenAI key 不可用）"
- 跑了但失败（≥ 2 对漂移）→ T-1.5.10 验收报告显式 R1.5-* "ADR-014 同源假设需重审"

出处：synthesis §5 + §2 C4 + GPT-5.5 L2 critique 4.6。

## 5. /generator/prompts/visual/REVIEW_PROMPT_AI_JUDGE_VISUAL.md（**粗起一版**）

参考 [docs/REVIEW_PROMPT_CODE_GPT.md](REVIEW_PROMPT_CODE_GPT.md) 的形态（独立 prompt 文件 + 复制粘贴 + 报告产出格式）。

12 维度（每维 0–2 分；总分 24）：

| 代号 | 维度 | 0 / 1 / 2 含义 |
|---|---|---|
| V1 | 角色一致性（同一角色跨张 face/hair/outfit 一致） | 0 完全不像 / 1 大致像 / 2 完全一致 |
| V2 | 服装与本体卡符合 | 0 严重偏离 / 1 略偏 / 2 完全符合 |
| V3 | 风格统一（与基准图比） | 0 风格不匹配 / 1 略漂 / 2 一致 |
| V4 | 解剖正确（手指 / 比例 / 关节） | 0 多手指 / 1 微瑕 / 2 正确 |
| V5 | 表情可读 | 0 表情不明 / 1 可读 / 2 戏剧张力 |
| V6 | 构图（character_sheet：torso-up + face 占比；background：环境层次） | 0 不合规 / 1 普通 / 2 优秀 |
| V7 | 光影方向一致 | 0 光源混乱 / 1 一致 / 2 戏剧光 |
| V8 | 透视正确 | 0 错 / 1 对 / 2 优雅 |
| V9 | 道具与时代符合（无现代元素） | 0 现代穿帮 / 1 一致 / 2 优秀道具 |
| V10 | 表情多样性（仅 character_sheet 同一角色多张时；single 张此项 N/A） | 0 重复 / 1 略异 / 2 多样 |
| V11 | alpha 通道干净（character_sheet）/ 无 alpha（background） | 已由机械校验 → 此维只检查"alpha 边缘是否毛糙" |
| V12 | 整体可用度（作者主观） | 0 重做 / 1 可用 / 2 优秀 |

接受阈值：≥ 14 / 24（约 58%）。

判官**只输出建议分数**，**作者本人是最终裁判**（STAGE_1.5_TASKS.md P1.4 决策）。

注：原小节编号现为 §5（因 §4 插入了 parity smoke test）；后续 §6 测试同步。

prompt 内容必含：
- 角色 = "你是 Forgewright RPG 项目的视觉资产辅助评审员。**你只评分，不替作者决定**"
- 必读列表：本体角色卡（如评 character_sheet）、SCHEMA_v0.2.md、ADR-014（一致性策略）
- 输入（**GPT-5.5 L2 critique 5.2 修补**：明示三种场景，避免作者把本地路径粘到网页端）：
  - **网页端 ChatGPT 评图（主要场景）**：作者上传图片附件（drag&drop 或 attach），ChatGPT 网页能直接读 attached image；prompt 文本里 reference 图时只说 "the attached image"，**不要给本地路径**
  - **CLI / 脚本场景**（API 调用判官）：base64 编码内嵌 prompt 或作为 separate image input；适用于自动化 batch 评分
  - **本地路径**：仅供本机工具（如 Pillow）读取，**不能给 ChatGPT 网页**——网页端无文件系统访问权限
- 输出：JSON 形式 12 维评分 + 文字理由 + 推荐 accept/reject
- 不要：替作者决定、修改图、给"重新生成"建议（这是 prompt 调优的事）

格式参照 REVIEW_PROMPT_CODE_GPT.md 的文档结构（设计前提 + 复制粘贴块 + 说明）。

## 6. 测试

test_visual_experiment.py：用 FakeImageProvider 跑 manual 模式，验证 results.jsonl + summary 生成
test_visual_review_cli.py：mock stdin 跑非交互版 + 验证 visual_review_log.jsonl 写入；至少跑一次 `python -m generator.visual_review_cli --help` 通过
test_visual_metrics.py：单元测试；从 mock import_log.jsonl + visual_review_log.jsonl + image_cost_log.jsonl 计算 metrics（**不要扫目录**）
（test_visual_parity_smoke.py **由 T-1.5.9 提供**——本任务不实施 parity smoke 脚本）

# 不要做的事

- 不要让视觉 AI 判官替代作者审阅（P1.4 决策：辅助标红，不替代）
- 不要写 Web UI 的 React/Vue 前端（最小静态 HTML 即可；阶段 3 再考虑）
- 不要让 visual_experiment 默认烧很多钱（manual 模式 = $0；api 模式默认 N=1，跑前确认）
- 不要在本任务实现 OpenAIImageProvider（T-1.5.9）
- 不要把视觉 AI 判官 prompt 与文本 21 维判官混为一谈（独立文件 / 独立维度）

# 完成报告

- CLI 用法说明 × 3
- 视觉 AI 判官 prompt 路径 + 12 维度表
- 测试输出
- commit + push（commit message: `feat(generator): add visual experiment, review CLI, metrics, and AI-judge prompt scaffold (T-1.5.8)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.8_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 视觉 AI 判官**只辅助标红，不替代作者**（P1.4 决策；STAGE_1_ACCEPTANCE R6 教训）
- 视觉判官 prompt 是粗起一版，跨模型校准在阶段 2/3 做
- macOS open 命令是平台依赖；非 macOS 需 --web；不要建议加 Linux/Windows 原生预览（YAGNI）
- visual_review_cli 的 --web 模式用最小静态 HTML，不引 React / Vue / Tailwind（阶段 3 再考虑工坊化 UI）
- experiments/ 目录已在阶段 1 .gitignore 覆盖（沿用）

§3 已知约束：
- 本任务不实现 OpenAIImageProvider（T-1.5.9）
- 本任务不解决 STAGE_1_ACCEPTANCE R6 / R8（AI 判官系统性放水）；视觉判官能力差异更大，留给阶段 2/3 校准

§4 配套阅读：
- /docs/STAGE_1_ACCEPTANCE.md §4 R6 + R8
- /docs/REVIEW_PROMPT_CODE_GPT.md（参照独立 prompt 文件结构）
- /generator/experiment.py + review_cli.py + metrics.py（文本版参照）
- /docs/STAGE_1.5_TASKS.md "接受率判定者"

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## ⏸ 作者侧手工任务（介于 T-1.5.8 和 T-1.5.10 之间）

```text
T-1.5.8 落地后，由你（作者）执行：

1. 在 /content/visuals/_reference/ 放入 2–3 张视觉风格基准图（自购或 Pinterest 收藏；不入 git）
2. 跑 4 次 batch（manual 模式不需要 OpenAI key）：
   python -m generator.visual_experiment --batch-name s15_vellin_001 --target char_vellin --target-type character --asset-role character_sheet --n 10 --mode manual
   python -m generator.visual_experiment --batch-name s15_corvan_001 --target char_corvan --target-type character --asset-role character_sheet --n 5  --mode manual
   python -m generator.visual_experiment --batch-name s15_aelwin_001 --target char_aelwin --target-type character --asset-role character_sheet --n 4  --mode manual
   python -m generator.visual_experiment --batch-name s15_loc_001    --target scene_waystation_of_iron_oath --target-type scene --asset-role scene_background --n 1 --mode manual
3. 每个 batch 跑完后，去 chatgpt.com 用 ChatGPT Plus 网页版逐条复制 prompt（_pending/<asset_id>/prompt.md 英文段）→ GPT-Image 生成 → 下载到 _pending/<asset_id>/<asset_id>.png
4. 跑 `python -m generator.image_import --all-pending` → 机械校验 + 入库
5. 跑 `python -m generator.visual_review_cli --batch-dir <path>` → 逐张 [A]/[R]，必要时记原因
6. 跑 `python -m generator.visual_metrics --batch-dir <path>`
7. 把 4 次 metrics 输出贴到下一个会话作为 T-1.5.10 验收输入

如果 acceptance_rate < 50% 或机械检查通过率 < 80%：
- 不要立刻判失败
- 反向阅读 visual_review_log 的 reject 原因；常见模式 → 反馈给规划师调 prompt 模板（开新一轮 T-1.5.6.x）
- 调几轮后再跑 T-1.5.10

可选：若 OpenAI API key 已就绪，可平行跑 T-1.5.9 和 OpenAI 模式 batch 验证 dev/prod prompt 同源（HANDOFF 提到的"技术假设需验证"）。
```

---

## T-1.5.9 ｜ OpenAIImageProvider 实现（⏸ **可推后**；不阻塞 1.5 验收）

```text
你的任务是实现 ADR-014 的 OpenAIImageProvider，作为 ImageProvider Protocol 的第二个实现（API 模式）。

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/providers/openai_image.py（**新建**）
  - /generator/providers/__init__.py（重导出 OpenAIImageProvider）
  - /generator/visual_parity_smoke.py（**新建**——**GPT-5.5 L2 critique 4.6 修补**：parity smoke 实施位置）
  - /generator/tests/test_openai_image_smoke.py（**新建**；@pytest.mark.smoke，需 OPENAI_API_KEY）
  - /generator/tests/test_openai_image_unit.py（**新建**；mock SDK）
  - /generator/tests/test_visual_parity_smoke.py（**新建**；mock 双模 + 验证 parity_report.md 生成 + 无 API key 时降级跳过）
  - pyproject.toml（追加 openai 依赖）
  - /.env.example（新增 OPENAI_API_KEY=your-openai-api-key-here）
严禁修改：
  - /schema/、/state/、/engine/、/validator/、/content/、/docs/
  - /generator/ 其他模块（包括 manual_import.py / visual_experiment.py / visual_metrics.py）
  - /generator/image_provider.py（接口已定）

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-014（API 模式 + 单价 $0.04–$0.17）
- /docs/STAGE_1.5_TASKS.md（特别 OpenAI 后置策略）
- /generator/image_provider.py（Protocol）
- /generator/providers/manual_import.py（同款实现风格）
- /generator/providers/gemini.py（参考 LLM provider 写法）

# 待做

## 1. pyproject.toml + .env.example

新增依赖：openai (执行时确认最新稳定版)
.env.example 新增：OPENAI_API_KEY=your-openai-api-key-here

## 2. /generator/providers/openai_image.py

```python
class OpenAIImageProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,  # 默认从 os.environ["OPENAI_API_KEY"]
        model_id: str = "gpt-image-1",  # 执行时让会话先 list models 确认；如不可用让作者拍板
    ): ...

    def generate(self, *, prompt, ref_images=None, n=1, size=(1024,1024),
                 asset_kind, target_ref, target_type, asset_role, asset_id_stub, variant_label="") -> ImageGenerationResult:
        # 接口与 ManualImportProvider 完全一致（GPT-5.5 L2 critique 3.3：target 三字段贯穿）
        # 1. 调 openai.images.generate(...) 或对应 client；捕获网络异常 → 抛 ImageProviderError
        # 2. 解析返回 → image_bytes
        # 3. ref_images 处理：如 SDK 支持 reference image 输入则上传；否则在 prompt 文本里描述基准图（fallback；本任务**实现 fallback 模式**，不强制上传）
        # 4. 计算 cost_usd（estimate_cost）
        # 5. 返回 ImageGenerationResult(mode="api", asset_id_stub=<入参>, image_bytes=..., prompt_package_path=None, cost_usd=..., raw_metadata={openai 返回的全 metadata + target_ref/target_type/asset_role/variant_label 回填})

    def estimate_cost(self, *, n, size) -> float:
        # 硬编码当前公开单价 + 注释来源 URL + 取数日期；如未来调价由后续 PR 更新
        # GPT-Image-1: ~$0.04 (low quality 1024x1024) ~$0.17 (HD)
        # 本任务取保守上限值，避免 budget 高估算
```

## 3. /generator/providers/__init__.py

重导出 OpenAIImageProvider（保持 ManualImportProvider + GeminiProvider 重导出不动）。

## 4. Smoke test（需 OPENAI_API_KEY；@pytest.mark.smoke）

- 跳过条件：无 OPENAI_API_KEY
- 单次最小调用（256×256 character_sheet test prompt）
- 校验：ImageGenerationResult.mode = "api"，image_bytes 非空，cost_usd > 0，raw_metadata 含 OpenAI 返回字段
- 烧不超 $0.20

## 5. 单元测试（mock SDK）

- mock openai.images.generate → 返回固定 image_bytes
- 验证返回的 ImageGenerationResult 字段正确
- 验证 estimate_cost 数值合理

## 6. /generator/visual_parity_smoke.py（**GPT-5.5 L2 critique 4.6 修补——从 T-1.5.8 移到本任务**）

CLI: `python -m generator.visual_parity_smoke --prompts <path> [--n 3]`

流程：
1. 读 3 条已审核通过的 prompt 文本（建议从 vellin / corvan / 1 location 各取 1 条）
2. 对每条 prompt 在 manual + API 双模下各产 1 张
   - manual: 走 ManualImportProvider → prompt 包到 `_pending/parity/<prompt_id>/manual/`
   - api: 走 OpenAIImageProvider（**需 OPENAI_API_KEY**；无 key 时**优雅降级**：写 parity_report.md 标 "skipped: no OPENAI_API_KEY" + 退出 0）
3. 输出 /generator/experiments/parity_smoke_<timestamp>/parity_report.md
   - 含每对的并排对比 + 占位"作者评估区"（作者后续填评分 0/1/2）
   - 总结：3 对里 ≥ 2 对评分 ≤ 1 = ADR-014 同源假设站得住；否则触发回炉
4. 写一行到 image_cost_log.jsonl 记 API 部分成本
5. **不实施 batch metrics 联动**（保持纯一次性脚本）

成本：API 部分 ≈ 3 张 × $0.17 = $0.51（一次性）；manual = $0。

测试 test_visual_parity_smoke.py：
- 用 FakeImageProvider mock 双模 + 验证 parity_report.md 生成
- 无 API key（mock）时降级跳过，退出 0，parity_report.md 标 skipped
- API 调用 mock 抛异常 → parity_report.md 标 partial fail，不抛到上层

## 前置作者侧准备

- 你（执行会话）开始前应假设作者已设置 OPENAI_API_KEY 环境变量（**可能没有**）
- 如果 smoke test 跑不通且原因是 model_id 错误，**不要自己改 model_id 猜**；停下来在完成报告里列出 SDK 列模型输出，由作者拍板
- 如果作者明确说"暂未配 OPENAI_API_KEY"，仅落地代码 + 单元测试 + 文档；smoke test 跳过即可

# 不要做的事

- 不要在 OpenAIImageProvider 内做 budget 检查（与 GeminiProvider 同源——budget 在主函数 generate_character_sheet 拦）
- 不要做 retry / fallback（保持单次调用；与 GeminiProvider 一致）
- 不要假设 OpenAI SDK 接口稳定性（接口可能变；保留 try/except + 记 raw_metadata）
- 不要在 prompt 文本里上传基准图字节（GPT-Image 接受 ref images，但本任务**实现 fallback 模式**：将基准图描述以文本形式注入 prompt——actual upload 由后续 PR 处理）
- 不要把 model_id 默认改为 dall-e-3（ADR-014 默认 GPT-Image）
- 不要碰 ManualImportProvider

# 完成报告

- 接口签名 + 类骨架
- smoke test 输出（含真实 cost / 图片 size 数字；如跳过则说明原因）
- 单元测试输出
- 失败时列出 list_models() 结果
- commit + push（commit message: `feat(generator): add OpenAIImageProvider (T-1.5.9)`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.9_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- estimate_cost 硬编码取上限值（$0.17）是有意保守；避免 baseline_001 那种 0% 成功率烧钱事故
- ref_images 不上传字节（fallback 文本描述）是阶段 1.5 范围决策；阶段 2 再考虑实际上传
- model_id 默认 gpt-image-1 是 ADR-014 决策；不要建议默认 dall-e-3
- 与 GeminiProvider 同源——provider 不做 budget / retry / 重试

§3 已知约束：
- 本任务**可推后**——不阻塞 1.5 验收（manual 主推路径不依赖 OpenAI）
- 本任务不验证 dev/prod prompt 同源（HANDOFF 提到的技术假设；推到作者跑 OpenAI batch 时验证）
- 本任务不实现 ref_image 上传（阶段 2）

§4 配套阅读：
- /docs/DECISIONS.md ADR-014（API 模式约束）
- /generator/providers/manual_import.py + gemini.py（参考实现）
- /generator/image_provider.py（Protocol）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## T-1.5.10 ｜ 阶段 1.5 验收报告

```text
你的任务是写阶段 1.5 验收报告。**仅在作者侧手工任务跑完且 4 次 batch 都有 visual_review_log 后启动**。

# 模块边界（硬性）
允许新建：/docs/STAGE_1.5_ACCEPTANCE.md
允许修改：/docs/ROADMAP.md（更新记录）
严禁修改：其他 docs / 任何代码 / /content/、/state/、/schema/

# 必读
- /docs/STAGE_1_ACCEPTANCE.md（参照格式）
- /docs/STAGE_0_ACCEPTANCE.md（更早的格式参照）
- /docs/ROADMAP.md 阶段 1.5 完成标志
- /docs/STAGE_1.5_TASKS.md（特别"锁定的架构决策"+"接受率判定者"+"完成标志"）
- 4 次 batch 的 results.jsonl + visual_review_log.jsonl + visual_metrics 输出（作者会贴在会话里）
- /content/visuals/manifest.json（最新状态）

# 待做

按 STAGE_1_ACCEPTANCE.md 同款格式写 STAGE_1.5_ACCEPTANCE.md，必含：

## 1. 阶段 1.5 完成判定核对

| 指标 | ROADMAP / TASKS 目标 | 实测 | 判定 |
|---|---|---|---|
| 入库总数（vellin 10 + corvan 5 + aelwin 4 + 1 location = 20） | ≥ 20 | <实测> | <pass/conditional/fail> |
| **接受率**（**Round 5 U-CL-2**：分子 = 作者标 [A]ccept 资产数；分母 = 入库（机械预检通过 + 进入 review_log）资产总数；不计 _rejected/） | ≥ 50% | <实测，明示分子/分母> | <同上> |
| 机械预检通过率（image_validator 输出 0 error） | ≥ 80% | <实测> | <同上> |
| **manifest.json 完整性**（**Round 5 U-CL-2** 定义：每条入库资产含 image_asset.schema.json 全部 required 字段——asset_id / asset_kind / source_mode / format / width / height / file_path / created_at + target_ref / target_type / asset_role；机械校验脚本输出 0 错误） | 100% | <实测> | <同上> |
| manual 路径全跑通 | 是 | <实测> | <同上> |
| **C8 三态 API 验收口径**（**Round 5 硬闸门**） | manual passed = 必须；API implemented + API parity validated = stretch goal | <按下方明示> | <同上> |

### 1.1 C8 API stretch goal 三态明示（Round 5 硬闸门）

| 状态 | 含义 | 1.5 实测 |
|---|---|---|
| **manual passed** | vellin/corvan/aelwin/1 location 全 manual 入库 + 作者审阅接受率 ≥ 50% | <pass/fail> |
| **API implemented** | T-1.5.9 OpenAIImageProvider 落地 + smoke test 通过（**stretch**） | <落地/未落地+原因> |
| **API parity validated** | C4 dev/prod parity smoke test 跑了 + 3 对里 ≥ 2 对漂移评分 ≤ 1（**stretch**） | <跑了+结果/未跑+原因 R1.5-*> |

1.5 验收**只要求 manual passed**；API implemented / API parity validated 未达即记入 §4 R1.5-* 遗留，**不阻塞 1.5 签字**。

整体结论：通过 / 有条件通过 / 未通过。

## 2. 4 次 batch 实验数据

### 2.1 metrics 输出汇总
- batch_s15_vellin_001 / s15_corvan_001 / s15_aelwin_001 / s15_loc_001
- 每个 batch：生成数 / 入库数 / acceptance / 拒绝原因 top 3 / 总成本（manual = $0；API 部分单列）

### 2.2 失败原因分布（reject 原因聚类）
按 visual_review_log.jsonl 的 reject reason 字段聚类，列出 top 5 + 出现频次。

### 2.3 视觉 AI 判官 vs 作者本人评审对比
若作者跑了 AI 判官辅助，列出 12 维评分均值 + 与作者最终决定的 Cohen's kappa（粗算）—— 用于阶段 2 校准判官能力。

## 3. 工作量速览

| 任务 | Commit | 一句话成果 |
|---|---|---|
| T-1.5.1 | <hash> | ADR-014 + ROADMAP 1.5 实质 + SCHEMA_v0.2.md 占位 |
| T-1.5.2 | <hash> | image_asset.schema.json + 角色桩 visual_assets + SCHEMA_v0.2.md 完整 |
| T-1.5.3 | <hash> | ImageProvider Protocol + ManualImportProvider |
| T-1.5.4 | <hash> | image_validator 机械预检 |
| T-1.5.5 | <hash> | image_cost_log + image_budget |
| T-1.5.6 | <hash> | generate_character_sheet + generate_scene_background + prompt 模板 |
| T-1.5.7 | <hash> | image_import CLI + manifest.json |
| T-1.5.8 | <hash> | visual experiment + review CLI + metrics + AI 判官 prompt 粗起 |
| T-1.5.9 | <hash 或 "未实施"> | OpenAIImageProvider（可推后；标注是否在 1.5 内落地） |

## 4. 遗留问题

| # | 项 | 性质 | 处理时机 |
|---|---|---|---|
| **R1.5-1** | <例：角色一致性 V1 平均 1.X，未达 1.8 标准> | 需调 character_features 描述精度 | 阶段 2 prompt 调优 |
| **R1.5-2** | <例：视觉判官 kappa 与作者 < 0.5；判官能力不足> | 需重新校准判官 prompt | 阶段 2/3 |
| **R1.5-3** | <例：dev/prod prompt 同源未验证（OpenAI 未跑）> | 推到 OpenAI key 就绪后跑同 prompt 对比 | 阶段 2 启动期 |
| ... | | | |

如有指标未达标但作者签字接受 → 在此说明 + 下一阶段补齐计划。

## 5. 阶段 2 启动前置条件

由专门规划师产 HANDOFF_STAGE_1.5_TO_2.md，必含：
- 阶段 1.5 产物清单（generator 视觉模块完整接口、experiment / review / metrics 工具链、视觉 AI 判官 prompt 复用方案、manifest 形态）
- R1.5-* 遗留项中哪些需在阶段 2 启动期处理
- 阶段 2 目标函数 generate_scene() 的 ROADMAP 约束摘要 + 与视觉资产的耦合点（生成对话节点时是否引用 visual_assets？）
- ADR-009 评测分层第二层（图论校验）解锁

## 6. 真实费用回顾

| 项 | 估算 | 备注 |
|---|---|---|
| Manual 部分（4 batch × N 张） | $0 | ChatGPT Plus 订阅摊薄 |
| API 部分（如 T-1.5.9 跑） | <数字> | OpenAI 实际账单（去 OpenAI 控制台对账） |
| **1.5 总计** | <数字> | |
| 单次硬卡 $1.00 / 日预算 $5.00 | 触及次数 | <数字> |

## 7. 模块边界自检

```bash
$ grep -RE "from generator|import generator" engine/ state/ schema/ validator/
（应空 — 运行时模块零依赖 /generator/）

$ grep -RE "from openai|import openai" generator/ --include="*.py" | grep -v "providers/"
（应空 — 业务代码无直接 SDK import，必须经 ImageProvider 接口）

$ grep -RE "import openai|from openai" engine/
（应空 — 运行时绝不引入图像 SDK，ADR-002）
```

✅ ADR-002 / ADR-004 / ADR-011 / ADR-014 在阶段 1.5 内坚守。

## 8. 签字

签字行留空（作者填）。

# 不要做的事

- 不要伪造数据；如某指标未达标，如实写
- 不要替作者签字
- 不要规划阶段 2（那是阶段 2 规划师的事）
- 不要在 ROADMAP 中删 T-1.5.9 行（即使未实施，标注"未实施"即可）

# 完成报告

- 文件路径 + 关键指标
- commit + push（commit message: `docs: stage 1.5 acceptance report`）
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# 评审准备（必做）

按 STAGE_1.5_TASKS.md "通用：Codex 评审 + 修复 prompt 模板" 章节产出 /docs/reviews/_prompts/T-1.5.10_codex_review.md。

本任务的填充指引：

§2 关键设计决策：
- 验收报告的接受率指标用作者本人评审（不是 AI 判官替代；P1.4 决策）
- 1.5 是 stretch goal 模式——OpenAI（T-1.5.9）可未实施；不要因此判 fail
- 视觉 AI 判官 vs 作者 Cohen's kappa 是粗算，不要苛求统计严谨

§3 已知约束：
- 本任务不规划阶段 2
- 本任务不修改任何代码 / /content/ / /state/

§4 配套阅读：
- /docs/STAGE_1_ACCEPTANCE.md（格式参照）
- /docs/STAGE_0_ACCEPTANCE.md
- /docs/STAGE_1.5_TASKS.md（完成标志）

（§5 报告 §1 由 Codex 自填，无需执行会话提供。）
```

---

## 版本

本文件版本：v0.1
最后更新：2026-04-30
产出方：阶段 1.5 规划师会话（基于 2026-04-30 与作者的 2 轮校准对话）
