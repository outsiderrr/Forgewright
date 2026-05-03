# STAGE_2_TASKS_v1.0_draft.md — 阶段 2 任务清单草稿

> **L2 整合规划师产出物**。这是 v1.0 草稿（基于 GPT-5.5 cross-LLM critique 整合 v0.1.1 而成），**不是** `/docs/STAGE_2_TASKS.md`——后者是 v1.0 commit 才进的位置（作者明示授权后另起 L3 执行会话落，走 ABC 闭环）。
>
> **下一步**：作者审 v1.0 + 修订记录章节（§12）+ 跨边界清单（§13）；明示授权后另起 L3 执行会话把 v1.0 commit 进 `/docs/STAGE_2_TASKS.md`。该 commit 完成后，Wave 0 三 L3（T-2.0 / T-2.10 / T-2.11）即可启动 A 阶段。

**日期**：2026-05-03 · **版本**：v1.0（GPT-5.5 critique 整合版） · **产出方**：阶段 2 L2 整合规划师会话（claude/musing-fermi-f6bfd3 worktree） · **基于**：v0.1.1 草稿（claude/ecstatic-lewin-6aee3c worktree） + 2026-05-03 GPT-5.5 critique（main:`/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_gpt_critique.md`） + 2026-05-03 L1 Wave 2 校准（"全选推荐"）

---

## 0. v1.0 整合说明

v0.1.1 草稿（commit 待补；当前在 `claude/ecstatic-lewin-6aee3c` worktree）由 L2 规划师会话产出后送 GPT-5.5 cross-LLM critique 评审，得 19 条 finding（🔴 5 / 🟡 10 / 🟢 4）。本 v1.0 草稿 = v0.1.1 + critique 整合，整合规则：

- **✅ 直接吸收 12 条**（5 条 🔴 中除 3.1/3.2 + 多数 🟡 中除 4.2/4.7/4.10）：进 v1.0 各章节
- **⚠️ 部分同意 6 条 + 全选推荐方案**（Q1/Q2/Q3/Q4/Q5/Q7 全选 A，Q6 选 B）：进 v1.0
- **❌ 反对 1 条**（R1 = §10 弱点 5）：v1.0 §10 删除该条
- **跨边界 3 项**（X1 / X2 / X3）：进 §13 跨边界清单，由作者另起会话处理

详细修订对照表见 §12 修订记录章节。

**与 v0.1.1 的章节级差异**：

| 章节 | 差异 |
|---|---|
| §0 | 新增本节（v1.0 整合说明）；v0.1.1 的"v0.1.1 修订说明"段移入 §11 变更历史 |
| §1.5 | B 阶段报告路径修订为 `/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`（跟 REVIEW_PROMPT_CODE_GPT.md commit `8842c43` 模板）；删 `_targets/` 子目录约定（critique 4.3 / Q4） |
| §2 | 新增 §2.4（schema_version 复合版本号语义，Q2/critique 3.2）+ §2.5（character/location envelope 契约，Q3/critique 4.2）+ §2.6（state_path_slug 字段，Q1/critique 3.1）+ §2.7（validator 模块命名，Q7/critique §9）+ §2.8（一致性细节统一） |
| §3 | ADR-016 state path 表改用 `relationship.<state_path_slug>.*`；ADR-016 system_time 双轨明示落 `world.*` 命名空间；ADR-019 generation_trace.slot_assignments 改走 optional + additionalProperties 兼容路径（不 bump dialogue_graph schema_version）；ADR-020 完整成本口径统一；ADR-021 完成标志拆"纯拓扑 / condition-aware"双报 |
| §6 | wave 图与 v0.1.1 一致（已正确）；增补依赖说明文字 |
| §7 | 任务概览表修依赖列（T-2.6 = T-2.5+T-2.4；T-2.8 = T-2.6+T-2.4+T-2.7）；T-2.0 / T-2.11 模块边界列扩充 |
| §8 | 13 个 paste-ready prompt 全部按 critique 修订（详见 §12） |
| §9 | 跨任务一致性表更新（active_clocks / scene_review_cli / effect_op 映射等） |
| §10 | 删除原弱点 5（R1）；新增 4 条更尖锐弱点（schema_version 后向兼容 / state path slug 口径 / AI judge runner 缺位 / 真实 wave 依赖） |
| §11 | 变更历史段加 v1.0 行 |
| §12 | **新增**：完整修订记录（每条 critique finding ✅/⚠️/❌ → v1.0 修改） |
| §13 | **新增**：跨边界清单（X1 / X2 / X3） |

---

## 1. 阶段 2 目标回顾

来自 `/docs/ROADMAP.md` §阶段 2：

- 函数 `generate_scene(scene_setting, target_beats, participating_npcs) -> DialogueGraph`
- 输出：通过 Schema 校验 + 通过图论校验的完整对话树
- **单次生成人工可接受率：≥ 70%**（高于阶段 1 的 50%）
- 图论校验器实现：前置闭合 / 不可达 / 死锁 / 收敛性 + ADR-009 第二层（拆 2A 拓扑 + 2B 抽样验证 + 有界符号执行）
- 重点工作：本体最小契约 + 角色槽位 + 时钟系统 + 关系层 narrative_weight + dramatic_triggers + Chapter/Act schema 一次性打包

阶段 2 完成标志（含 Round 5 + PZ 反思综合后）：

- `generate_scene()` 在 N=15 场景 batch 上接受率 ≥ 70%（U-GPT-4 baseline 协议口径；ADR-020）
- validator 扩展通过《铁誓驿站》gold standard 全部 2A 拓扑检查 + 2B 抽样 N=100 路径无反例 + 有界符号执行无反例（ADR-021；2A 完成标志与 2B 完成标志**双报**，不混淆）
- 阶段 2 schema commit 全部进 git（**新建** schema 文件 character / location / clock / chapter 首版即 const "0.3.0"；**已有** schema dialogue_graph / node 保持 const "0.1.1"，新增字段走 optional + additionalProperties 兼容路径——详 §2.4 + ADR-019）
- C5 开源剥离边界清单 v0.1 起步（含 scene prompt 子包 + scene fixtures 标注）

> **跨边界提醒（X1）**：ROADMAP §阶段 2 当前完成标志措辞含"证明任意合法状态组合可达结局"——此措辞已被 ADR-021 修订为"抽样 N=100 + 有界符号执行下未发现反例"。ROADMAP 文本同步修订**不在 v1.0 草稿范围**，由作者另起 L1 doc 修订会话处理；T-2.13 验收报告引用 ADR-021 实际口径，不引用旧 ROADMAP 文本。详 §13 X1。

---

## 1.5 ABC 三阶段闭环（治理备忘 v0.3 §10；v1.0 修订 B 报告路径）

> 本节是治理备忘 v0.3 §10 全文吸收 + v1.0 对 B 阶段报告路径的修订。每个 L3 任务一律走以下三阶段；任何 L3 paste-ready prompt（§8）的末尾标志段都引用本节。

### 1.5.1 三阶段定义

- **A 开发阶段**：作者起 Claude Code worktree 会话；按对应 paste-ready prompt 开发 + 测试 + commit + push + 开 PR（base = `main`，head = worktree 分支名）。A 阶段产出物全部 push 到 PR。**A 阶段完成 ≠ L3 通过**。
- **B review 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作 review prompt 模板；review A 阶段 PR diff；report 落 **`/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`**（跟模板 line 92-95 默认路径；阶段 1.5 commit `33611cd` 9 份 backfill 实证此路径）
- **C 修复阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）

> **v1.0 修订**：v0.1.1 §1.5 + 各 L3 段写 B 报告落 `/docs/reviews/_targets/<task>_review_<topic>.md`，与 REVIEW_PROMPT_CODE_GPT.md 模板的 `/docs/reviews/{ISO_DATE}_{REVIEW_TARGET_SHORT}_review.md` 路径冲突（critique 4.3）。v1.0 统一跟模板路径，删除 `_targets/` 子目录约定。理由：模板 commit `8842c43` 已稳定（阶段 1.5 9 份 backfill 实证），`_targets/` 是 v0.1.1 引入的新概念，未在 main 立稳。

### 1.5.2 L2 验收

L2 拿 ABC 全部产出判断；过关 → 通知作者 merge PR + 进下一个 L3；打回 → 指定回 C 或回 B 跑二轮。

### 1.5.3 PR merge 硬规则

**A+B+C 全部完成 + L2 验收过关之前，PR 一律不 merge**。这是 v0.3 治理备忘核心约束——之前作者侧观察到"A 阶段 push 后 routine 抢跑 merge"问题，v0.3 升级硬卡。

### 1.5.4 routine 兼容性

- 所有 L3 一律 ABC 闭环——无论本草稿 §7 类型列标 [A-execute] 还是 [B-author-gate]
- routine 仅可用于 A 阶段串联（一个 L3 A 阶段完成后自动进下一个 L3 A 阶段）；**不可跨过 B/C/验收闭环**——这是 routine 与 ABC 闭环的硬边界
- 不要尝试搭 git hook / GitHub Action 把 B/C 自动化——按 v0.3 governance §5，按当前频率手动跑性价比更高

---

## 2. 锁定的架构决策（Wave 2 校准 2026-05-03 闭环 + v1.0 整合校准）

### 2.1 决策总表（"全同意默认"路径 + critique 整合后扩充）

| 决策 | 内容 | 来源 |
|---|---|---|
| **D1 C1 范围** | 本体最小契约 = character + location + relation + state path + clocks + 系统时间双轨 + Chapter/Act 一次性打包 | synthesis §6 + PZ §3.1 + U-CL-4 |
| **D2 角色槽位** | 持久化层 concrete `character_refs`；抽象槽走 generator 中间产物 + `generation_trace` 记录（**走 optional + additionalProperties 兼容路径，不 bump dialogue_graph schema_version**——详 §2.4） | U-GPT-5（synthesis 推荐） + critique 3.2/Q2 |
| **D3 ADR-009 第二层** | 拆 2A 纯拓扑 + 2B 抽样验证（**N=100 起步**）+ 有界符号执行；完成标志措辞从"证明"改为"抽样验证 + 有界符号执行下未发现反例"；**完成标志拆"纯拓扑 pass / condition-aware（2B）pass"双报** | U-GPT-1 + critique 4.7/Q5 |
| **D4 baseline 协议** | N=15 场景 / max_retries=2 / AI 判官 = 节点级 21 维 × 节点 + 场景级新增 6–10 维 / 机械失败口径 = option 长度 + path 前缀 + bond ID 白名单 + target_node_id 闭合 + unavailable_behavior 枚举 / 接受率分母 = 机械预检通过 + 进入 review_log；分子 = 作者标 [A]ccept；**报告同时给 gross pass rate 和人工接受率**（critique §10 weakness 2 补强） | U-GPT-4 + critique §10 |
| **D5 Chapter/Act 时机** | 与 D1 同期（阶段 2 起手期一次性打包） | U-CL-4 |
| **D6 C5 起步时机** | 阶段 2 起手期建 sidecar `OPEN_SOURCE_CARVE_OUT_INDEX.md`；**首版加 scene prompt 子包 + scene fixtures 标注**（critique 4.6 后果） | C5 + critique 4.6 |
| **D7 时钟 schema 字段名** | PZ §3.2 草图 + 加 `scope: enum["world","faction","environmental"]` + `ticks_current` 重命名为 `ticks_filled`（PbtA 术语） | PZ §3.2 |
| **D8 narrative_weight 枚举** | `core` / `minor` / `context_only` 三档（字面）；**关系作为 character entity 的 `relations: []` 子字段嵌入**，不引入全局关系表（critique §9 / Q3） | PZ §3.3 + critique §9/Q3 |
| **D9 时钟边界** | 软上限 `ticks_total ≤ 20` / 同时活跃 clocks `≤ 10`；**"同时活跃 ≤ 10" 由 T-2.7 sampling/validator 出 warning 级检查**（schema 不加，由 T-2.7 实测倒推；PZ §3.4 + critique §6） | PZ §3.4 + critique §6 |
| **D10 dramatic_triggers** | `[{trait, when, how, priority?, cooldown_scenes?}]`；后两项 optional 保留 hook 不强制；**T-2.2 落地时给 1-2 个 seed 示例**（如 vellin 的 trigger）防 prompt 测试空转 | PZ §4 + critique §10 weakness 4 |
| **D11 state path slug**（v1.0 新增） | character entity 加 `state_path_slug` 字段（默认 = `id` 去 `char_` 前缀；如 `char_vellin` → `vellin`）；ADR-016 state path 表语义改为 `relationship.<state_path_slug>.*`（保 gold scene `relationship.vellin.trust` 不动；详 §2.6） | critique 3.1 / Q1 |

### 2.2 PZ 反思拍板项（直接吸收）

- **系统时间双轨**：`world.scene_count`（每场景 +1，被动节奏）+ `world.long_rest_count`（玩家长休 +1，玩家节奏控制感）；不做实时计时器；**两字段为合法 state path，落入 `world.*` 命名空间**（critique §6）
- **时钟分类三类**：world / faction / environmental
- **advance_rule 默认范围**：仅 event_based（场景跳转 / 长休 / 玩家选择 / 派系行动）；不做 time-based；**SCHEMA_v0.3.md §4 明示"不存在 time_based 子类"**（critique §7）
- **关系层加权重字段**：`narrative_weight` 让作者控制"哪些关系真的进戏"
- **特性升级戏剧义务**：character `dramatic_triggers` 把特性从 descriptive 转成 prescriptive obligation
- **Sibling 涌现项目**：不在阶段 2 schema 里"预留"涌现接口；不预防性设计

### 2.3 作者态度（PZ §7，硬背景输入）

- 对 AI 进化能力有信心，尤其"判断已有上下文 + 逻辑自洽"——影响阶段 3 §9.2 缓解 ADR 紧迫度
- 50–100 场景规模可能不撞 §9.2 真墙；ADR-010 锁定的 MVP 规模未必积累到 84K token 状态
- 状态文件抽象层"真遇到再说"，不预防性设计——但 L2 必须保留 hook，避免阶段 3 中段才发现要重做
- 与 ADR-004 极简精神一致

### 2.4 schema_version 复合版本号语义（v1.0 新增；critique 3.2 / Q2）

**问题**：T-2.2 草拟把 dialogue_graph.schema.json / node.schema.json 的 `schema_version` const 升至 0.3.0，但 `/content/test_scene_v0/scene.json` 必须保 0.1.1 + 必过 gold standard。两条要求互否。

**v1.0 决策**（Q2 选 A）：

- **既有 schema 不动 const**：`/schema/dialogue_graph.schema.json` + `/schema/node.schema.json` + `/schema/option.schema.json` + `/schema/state_effect.schema.json` + `/schema/state_condition.schema.json` 的 `schema_version` const 保持 `0.1.1`（与 SCHEMA_v0.2 "非结构性变更不联动 schema_version" 先例一致——v0.1.1 草稿 line 554 已自引此先例）
- **新增字段走兼容路径**：`generation_trace.slot_assignments`（ADR-019）等 v0.3 新增字段以 **optional + additionalProperties** 形式追加到 v0.1.1 const 下；不破现有 gold scene + 阶段 0/1 测试
- **新建 schema 首版即 0.3.0**：`/schema/character.schema.json` + `/schema/location.schema.json` + `/schema/clock.schema.json` + `/schema/chapter.schema.json` 首版 `schema_version` const 为 `0.3.0`（独立版本号，与 dialogue_graph 解耦）
- **SCHEMA_v0.3.md 显式说明复合版本号语义**：阶段 2 的"v0.3"是 ontology 模块的 MINOR bump，不是 dialogue_graph schema 模块的 bump；两组 schema 文件版本号独立演进
- **测试要求**：T-2.2 测试套件必须同时验证（a）gold scene `/content/test_scene_v0/scene.json` 仍 pass v0.1.1 dialogue_graph schema；（b）新建 character / location / clock / chapter schema 在 sample 上 pass v0.3.0；（c）generation_trace.slot_assignments optional 字段在 dialogue_graph schema 下被接受

### 2.5 character/location envelope 契约（v1.0 新增；critique 4.2 / Q3）

**问题**：现 ontology entities[] 用 `{id, type, display_name, ...}` envelope；T-2.2 草拟 character.schema.json 要求 `character_id` + `additionalProperties: false`，与 envelope 字段名 `id` 冲突；现有 loader（[state/ontology/__init__.py:16-35](state/ontology/__init__.py:16)）按 `entity["id"]` 索引会破。

**v1.0 决策**（Q3 选 A）：

- **保留 entity envelope 字段名**：character / location entity 内字段就叫 `id`（不引入 `character_id` / `location_id` 冗余字段名）
- **character.schema.json 校验 entity 全对象**（含 envelope 的 `id` + `type` + `display_name` 等 + payload 字段 character_features / dramatic_triggers / relations / visual_assets）
  - `properties.id.pattern: "^char_[a-z0-9_]+$"`
  - `properties.type.const: "character"`
  - `additionalProperties: false`
- **location.schema.json 同**：`properties.id.pattern: "^(scene_|loc_)[a-z0-9_]+$"`
- **关系作为 character entity 子字段嵌入**：`relations: []` 字段嵌在 character envelope 内（`from = entity.id` 隐含），不引入全局关系表
- **state/tests 兼容**：T-2.2 测试套件验证现有 loader（按 `entity["id"]` 索引）在新 schema 下仍 pass；不破阶段 0/1 既有测试

### 2.6 state_path_slug 字段（v1.0 新增；critique 3.1 / Q1）

**问题**：ADR-016 草稿 state path 表写 `relationship.<character_id>.*`（`character_id` = `char_vellin`），但《铁誓驿站》gold scene（[scene.json:44](content/test_scene_v0/scene.json:44)）现有路径是 `relationship.vellin.trust` / `relationship.corvan.trust`。机械预检（T-2.4）按 ADR-016 严格实现会拒收 gold standard，与 T-2.4/T-2.7 "gold 必过" 要求冲突。

**v1.0 决策**（Q1 选 A）：

- **state path 命名空间继续用短 slug**：`relationship.<state_path_slug>.*`（不破 gold scene）
- **character entity 显式加 `state_path_slug` 字段**（character.schema.json）
  - 默认值 = `id` 去 `char_` 前缀（如 `char_vellin` → `vellin`）
  - 作者可校准（如冲突 / 短称偏好）
  - schema 层 `properties.state_path_slug.pattern: "^[a-z0-9_]+$"`
- **ADR-016 state path 表修订语义**（详 §3 ADR-016）：
  - `world.*` / `faction.<faction_id>.*` / `relationship.<state_path_slug>.*` / `flag.*` / `player.*`
  - `<state_path_slug>` 必须为本体某 character entity 的 `state_path_slug` 字段值，否则 validator 拒收
- **理由**：gold scene 已 commit（commit `9be7a3e` 阶段 1.5 验收实测产物），改 gold 风险更高；ADR-006 单一真相之源不破（state path 仍唯一可解析回 entity.id）；slug 字段让作者拥有 path 短称校准权
- **后果**：T-2.4 BOND_ID_UNKNOWN 检查需用 `state_path_slug` 反查 entity.id；T-2.5 prompt 模板 GraphContext 注入时输出 slug 给 LLM

### 2.7 validator 模块命名（v1.0 新增；critique §9 / Q7）

**问题**：现有 `/validator/graph_check.py` 已存在（阶段 0/1 产物，由 `validator/__init__.py` 导出）；T-2.7 草稿新建 `/validator/graph_validation.py` 与之命名近似，未明示替代/包装/并存关系。

**v1.0 决策**（Q7 选 A）：

- **`graph_validation.py` 包装现有 `graph_check.py`**：import 现有函数 + 在其上叠加 2A 拓扑新逻辑（NEVER_REACHED / DEAD_END_NODE / CONDITION_NEVER_SATISFIED / CONVERGENCE）
- **`graph_check.py` 保留向后兼容**：现有测试不动；`graph_validation.py` 视作 `graph_check.py` 的扩展层
- **`/validator/__init__.py` 导出策略**：`graph_check` 现有导出保留 + 新增 `validate_graph_topology` / `TopologyResult` 等从 `graph_validation` 导出
- **理由**：不破现有测试 / ADR-002 极简运行时 + ADR-004 极简精神 / 阶段 2 是扩展不是重写

### 2.8 跨任务一致性细节统一（v1.0 新增；critique §9）

| 不一致点 | v0.1.1 措辞 | v1.0 修订 |
|---|---|---|
| SceneGraphContext 时钟字段名 | T-2.5 prompt 写 `faction_clocks`；T-2.6 dataclass 写 `active_clocks` | 统一为 `active_clocks`（含 world / faction / environmental 三类） |
| location 字段名 | T-2.0 R4 写 `location_candidates`；T-2.6 SceneGraphContext 写 `location_card` | 统一为 `location_candidates: list[dict]`；如需主地点用 `primary_location_ref`（critique 4.1） |
| scene review CLI 命令 | T-2.8 文件名 `scene_review_cli.py`；T-2.12 命令 `python -m generator.scene_review` | 统一为 `python -m generator.scene_review_cli`；T-2.8 加 `--help` smoke test（critique §9） |
| tick_effects.effect_op vs StateEffect.op | T-2.7 effect 应用器未明示与现有 StateEffect.op 字段映射 | T-2.7 模块明示：`tick_effects.effect_op` 等价 StateEffect.op 枚举（set/inc/dec/add/remove）；effect 应用器用统一映射函数（critique §9） |

---

## 3. 推荐立项的 ADR 清单（候选 ADR-016 ~ ADR-021；v1.0 整合校准）

> L2 不立 ADR；这里只识别"该立哪些"。由作者明示授权后由 T-2.1（[B-author-gate]）一次性立完。参考 ADR-011/012/013 一次性立 3 条先例（commit `1d2030f`）+ ADR-015 一次性 implement Round 5 synthesis 先例（commit `9851419`）。
>
> **跨边界提醒（X2）**：6 条 ADR 立项**不在 v1.0 草稿范围**——v1.0 仅识别 + 描述决策核心；实际立项动作由 v1.0 commit 后作者另起 L3 执行会话跑 T-2.1 paste-ready prompt 落 `/docs/DECISIONS.md`。详 §13 X2。

| 候选 | 议题 | 决策核心（v1.0 修订） |
|---|---|---|
| **ADR-016** | 本体最小契约（character / location / state path / Chapter/Act / 系统时间双轨） | 详下 |
| **ADR-017** | 时钟系统 | 详下 |
| **ADR-018** | 关系层 narrative_weight | 详下 |
| **ADR-019** | 角色槽位持久化形态 | 详下 |
| **ADR-020** | 阶段 2 baseline 协议 | 详下 |
| **ADR-021** | ADR-009 第二层拆 2A/2B + 有界符号执行 | 详下 |

### ADR-016 决策核心（v1.0 修订）

- **character 实体**：`id`（pattern `^char_[a-z0-9_]+$`，envelope 字段；不引入 `character_id` 冗余名——§2.5）/ `display_name` / `description` / **`state_path_slug`**（v1.0 新增；默认 = `id` 去 `char_` 前缀；详 §2.6）/ `character_features`（描述性数组）/ `dramatic_triggers`（PZ §4 戏剧义务字段，详 ADR-019）/ `relations: []`（含 `narrative_weight`，详 ADR-018）/ `visual_assets`（已由阶段 1.5 加，保留）
- **location 实体**：`id`（pattern `^(scene_|loc_)[a-z0-9_]+$`）/ `display_name` / `description` / `location_type: enum[scene, sublocation]` / `parent_location_ref`
- **state path 命名空间表**（v1.0 修订）：
  - `world.*`（**含 `world.scene_count` / `world.long_rest_count` 系统时间双轨**——§2.2）
  - `faction.<faction_id>.*`
  - `relationship.<state_path_slug>.*`（**v1.0 修订**：`<state_path_slug>` = character entity 的 `state_path_slug` 字段值，不是 `<character_id>`；详 §2.6）
  - `flag.*`
  - `player.*`
  - 阶段 2 起 path 命名必须落入这五个命名空间之一，否则 validator 拒收
- **Chapter/Act 容器 schema**：`chapter_id`（pattern `^chap_[a-z0-9_]+$`）/ `display_name` / `acts: [{act_id, display_name, included_scenes: [scene_anchor]}]`；本体新增顶层 `chapters: []` 数组（U-CL-4 强建议前移到阶段 2）
- **系统时间双轨**（PZ §3.1）：`world.scene_count` + `world.long_rest_count`；不做实时计时器（违反 ADR-002 极简运行时）
- **新建 schema 文件 const "0.3.0"**：character / location / clock / chapter（§2.4）；既有 dialogue_graph / node / option / state_effect / state_condition 的 const 保持 "0.1.1"
- 替代方案及否决理由：
  - 推到阶段 3：synthesis §3.3 + GPT §3.1 已共识阶段 2 启动需要本体最小契约
  - 仅 character + location 不加 Chapter/Act：阶段 1/2 已生成内容到阶段 3 需回填层级（U-CL-4）
  - 加 Sibling 涌现项目接口预留：premature abstraction，PZ §6 已强约束
  - **state path 用 `<character_id>` 全名**（v1.0 新增）：会让 gold scene `relationship.vellin.trust` 失败；改 gold 风险高于加 slug 字段
  - **新增字段 bump 既有 schema_version 至 0.3.0**（v1.0 新增）：会破 gold scene 与所有阶段 0/1 测试；按 SCHEMA_v0.2 先例新字段走 optional 兼容路径
- 后果：
  - 阶段 2 schema commit 全部串行卡口在本 ADR 落地后启动（T-2.2）
  - validator 扩展（T-2.7）必须支持本体引用闭合 + state path 命名空间合法性 + state_path_slug 反查
  - prompt 模板（T-2.5）必须把 character_features / dramatic_triggers / Chapter/Act / 系统时间双轨纳入 context

### ADR-017 决策核心（与 v0.1.1 一致 + critique §6 / §7 补强）

- 时钟分类三类：`world` / `faction` / `environmental`
- `Clock` schema：`id` / `name` / `scope: enum["world","faction","environmental"]` / `ticks_total: int` / `ticks_filled: int`（PbtA 术语；非 ticks_current）/ `advance_rule: {type, params}` / `tick_effects: [{at_tick, effect_op, path, value}]`
- **advance_rule.type 默认范围**：仅 `event_based` 子类（`every_n_scenes` / `on_long_rest` / `on_faction_action` / `on_player_choice`）；不做 time-based（运行时无真时间，违反 ADR-002）；**SCHEMA_v0.3.md §4 明示"不存在 time_based 子类"**（critique §7）
- **边界软上限**（PZ §3.4 + critique §6）：单 clock `ticks_total ≤ 20`（schema maximum 落地）；同时活跃 clocks `≤ 10` **由 T-2.7 sampling/validator 出 warning 级检查**（schema 层不加；T-2.7 落地后由实测倒推真实上限，本 ADR v0.2 修订）
- **tick_effects.effect_op 与 StateEffect.op 映射**（v1.0 新增；critique §9）：`effect_op` 枚举值与现有 `StateEffect.op`（set / inc / dec / add / remove）一致；T-2.7 effect 应用器用统一映射函数
- 时钟存储位置：`/state/ontology/<world_name>.json` 顶层 `clocks: []` 数组
- 替代方案及否决理由：
  - 不立时钟 schema：阻塞 prompt 模板（T-2.5）context 注入；扩 ADR-006 而不分立 = 单条 ADR 太大
  - 含 time-based 步进：违反 ADR-002 + ADR-004 极简精神；运行时是 JSON 播放器无真时间
  - **同时活跃 ≤ 10 写进 schema**：定义域随阶段演进；T-2.7 实测倒推后由 ADR-017 v0.2 修订，比硬写 schema 灵活
- 后果：
  - prompt 模板必须在 GraphContext 注入当前活跃 clocks 状态（v1.0 字段名 `active_clocks`，§2.8）
  - validator 必须校验 tick_effects.path 落入合法 state path 命名空间（ADR-016）
  - T-2.7 第二层 2B 抽样验证可推理时钟状态空间（ticks_total × clocks 数 = 抽样维度）

### ADR-018 决策核心（与 v0.1.1 一致 + Q3 / critique §9 补强）

- character entity 加 `relations: []` 字段（**嵌入式**，不引入全局关系表——§2.5/Q3）
  - 每项 `{target_character_ref, relation_type, narrative_weight: enum["core","minor","context_only"]}`
- 语义：`core` = 必须显性体现；`minor` = 可选体现；`context_only` = 仅作 prompt 一致性 anchor，不出现在玩家可见对白
- prompt 模板（T-2.5）按 narrative_weight 决定 context 注入：core / minor 进 prompt，context_only 仅作合法性约束
- 替代方案及否决理由：
  - 不加权重字段：LLM 在多角色场景下会写"全员问候"式对白；阶段 2 70% 接受率难达
  - 加 numeric weight（0-100）：作者难校准；离散三档对作者审阅心智更友好
  - `mandatory / optional / background` 字面：与 BG3 任务系统术语易混淆
  - **全局关系表**（v1.0 新增）：会破 ADR-006 单一真相之源（同一关系在 from / to 两端冗余）；嵌入到 character envelope 内更自然
- 后果：
  - 角色花名册更新工作量：T-2.2 落地 vellin / corvan / aelwin 关系矩阵
  - prompt 模板必须按 narrative_weight 决定注入逻辑

### ADR-019 决策核心（v1.0 修订；critique 3.2 / Q2）

- 持久化层（`/state/ontology/` + `/content/<scene>/scene.json`）仍 concrete `character_refs`——不破 ADR-006 单一真相之源
- 抽象槽（如 "the betrayer", "the witness", "the broken oath-keeper"）作为 generator 中间产物
- 落到节点级 `generation_trace.slot_assignments` 字段（**走 optional + additionalProperties 兼容路径，不 bump dialogue_graph schema_version**——§2.4）
  - 结构：`slot_assignments: {<slot_id>: {character_ref, assigned_at, source_prompt_hash}}`
- 后续场景生成可读取此 trace 维持槽位一致性（跨场景同槽 → 同 character）
- 阶段 2 不实现"动态换角"逻辑——那是阶段 3 跨场景一致性范畴
- 替代方案及否决理由：
  - 持久化层引入 `slot_tags` 字段双轨：违反 ADR-006 单一真相；schema 复杂度大
  - 完全只靠 generator 中间产物 + 不写 trace：跨场景重生成不可重现
  - **generation_trace bump dialogue_graph schema_version 至 0.3.0**（v1.0 修订）：会破 gold scene + 阶段 0/1 测试；按 SCHEMA_v0.2 先例 optional 字段走兼容路径更稳（§2.4）
- 后果：
  - generation_trace 字段表追加 slot_assignments 子字段（**dialogue_graph + node schema_version 不动**）
  - generate_scene（T-2.6）必须在节点产物里写 slot_assignments
  - validator 不强制 slot_assignments 必填（trace 仍 optional）

### ADR-020 决策核心（v1.0 修订；critique 5.2 / §10）

- **样本数 N**：15 场景（场景级单次成本高于节点级；N=20 太烧；N=10 统计弱）
- **重试规则**：复用 ADR-013 max_retries=2（共 3 次）；schema 失败 + 图论失败回喂模型
- **AI 判官权重**：节点级 21 维度 × 节点数 + 场景级新增 6–10 维度（图拓扑健康 / 节奏 / 角色弧线 / 决策意义 / 收束 / 长度合理 / context 一致性 / 关系层一致性 / 时钟一致性 / ID 命名规范）；具体维度由 T-2.9 落地
- **机械失败口径**：option 长度（≤ 25 汉字）+ path 前缀（落入 ADR-016 五个命名空间）+ bond ID 白名单（state_path_slug 反查；§2.6）+ target_node_id 闭合 + unavailable_behavior 枚举合法性 + StateCondition 形态互斥
- **接受率分母**：通过机械预检 + 进入 review_log 的场景数
- **接受率分子**：作者标 [A]ccept 的场景数（不是 AI 判官打分）
- **报告同时给 gross pass rate 和人工接受率**（v1.0 新增；critique §10 weakness 2 补强）：gross pass = 通过机械预检的场景数 / 总尝试场景数；接受率（作者签字）作为最终判定
- **AI 判官与作者关系**：AI 判官是辅助参考分（21 维 + 场景级新增），作者最终标 [A]/[R]/[S]——与阶段 1 R6 一致
- **成本估算口径统一**（v1.0 修订；critique 5.2）：每场景估 ~$0.5–$1.0；N=15 总 $7–$15；N=20 总 $10–$20
- 替代方案及否决理由：
  - N=20 场景：成本 $10–$20，烧；N=15 平衡
  - 接受率分子用 AI 判官：阶段 1 R6 已锁"作者最终签字"
  - 不定义机械失败口径：U-GPT-4 漏抓的核心点；模糊定义将下游统计一致性废
- 后果：
  - T-2.4 R8 机械预检器要按本协议落地
  - T-2.9 AI 判官 prompt 按本协议设计权重
  - T-2.12 实证 batch run 按 N=15 跑

### ADR-021 决策核心（v1.0 修订；critique 4.7 / Q5 / §10 weakness 3）

- **2A 纯拓扑校验**（v1.0 修订）：图遍历层 — **结构拓扑 + condition 引用形态合法性**（仅检查 path 命名空间 / op 枚举 / 字段结构）/ 前置闭合 / 不可达节点 / 死锁（非 end 节点入度可达但 option 集合中无任何 condition=null option）/ 分支收敛性。**condition satisfiability 不在 2A 内**——避免把纯拓扑检查包装成 condition-aware 已完成。
- **2B 抽样验证 + 有界符号执行**：
  - 抽样 N=100 路径起步（从 entry 出发随机选 option，记录 state 演化，检查能否到 end 节点）
  - 有界符号执行：在 ADR-016 命名空间内枚举 effect 链产生的 state 组合（边界由 ADR-017 时钟数 × ticks_total + flag 离散值集决定）
  - **condition satisfiability 全部走 2B**（v1.0 修订）
  - **完成标志措辞修订**（ROADMAP §阶段 2 完成标志，跨边界 X1）：从"证明任意合法状态组合下至少有 1 个结局可达"改为"**抽样验证 N=100 路径 + 有界符号执行下未发现反例**"
- **N 值首版**：N=100；**经验阈值，不暗示充分证明**（v1.0 新增；critique §10 weakness 3）；阶段 2 实测后由 ADR-021 v0.2 倒推合理 N
- **完成标志拆双报**（v1.0 新增；critique 4.7 / Q5）：T-2.7 完成标志分别报告（a）2A 纯拓扑 pass（gold scene 全过 + 0 error）；（b）condition-aware（2B 抽样 + 有界符号执行）pass（gold scene 抽样 N=100 全 reach end + 0 反例）
- 替代方案及否决理由：
  - 严格证明：当前 schema 不支持，强行写完成标志会造成"过线假象"
  - 仅抽样模拟不做有界符号执行：U-GPT-1 推荐双路径——抽样找显式反例，符号执行覆盖低概率组合
  - **2A 内含 condition-aware**（v1.0 修订）：A2 自承"复杂；起步用启发式"；启发式包装成 condition-aware "已完成"会误导阶段 2 验收
  - **给 2A 加有限 state evaluator**（Q5 替代方案 B）：state evaluator 复杂度高、阶段 2 起步范围；拆双报清晰显示边界
- 后果：
  - validator 第二层（T-2.7）按 2A + 2B 拆分实现
  - T-2.7 完成标志拆双报；T-2.13 验收报告引用双报数据
  - ROADMAP 完成标志措辞由作者另起 L1 修订会话同步（不在本任务范围；详 §13 X1）

---

## 4. 启动闸门清单（Round 5 综合后 + 当前会话锁定）

### 4.1 硬闸门（5 项 — synthesis §6）

- ✅ **C1** 本体最小契约范围已锁定（D1 + D11 + §2.4/§2.5/§2.6）→ 由 ADR-016+T-2.2 落地
- ⏳ **C3** R 项 cleanup gate（R2/R3/R4 进 T-2.0；R8 进 T-2.4；R7 进 T-2.11）→ T-2.0 与 T-2.1 可并行
- ⏳ **U-GPT-1** ADR-009 第二层拆 2A/2B（拆双报，§2.4 §2.5 §2.6 + ADR-021）→ 由 ADR-021 + T-2.7 落地
- ⏳ **U-GPT-4** baseline 协议 → 由 ADR-020 + T-2.9 落地（**先于 T-2.12 实证 batch run**）
- ⏳ **U-GPT-5** 角色槽位持久化形态 → 由 ADR-019 + T-2.2 落地

### 4.2 强建议（2 项 — synthesis §6）

- ⏳ **U-CL-4** Chapter/Act schema → 已与 D1 打包，由 ADR-016 + T-2.2 落地
- ⏳ **C5** 开源剥离边界清单 → 由 T-2.10 起步建 sidecar（首版加 scene prompt 子包 + scene fixtures 标注，D6 修订）

### 4.3 STAGE_1.5_ACCEPTANCE §5 启动闸门（与上述映射，无冲突；若冲突以 acceptance 为准）

acceptance §5 列的 5 项硬闸门（C1 / C3 / U-GPT-1 / U-GPT-4 / U-GPT-5）+ 2 项强建议（U-CL-4 / C5）= 上述 4.1+4.2 完全一致。

---

## 5. R 项处理表（来自 STAGE_1_ACCEPTANCE.md §4 + STAGE_1.5_ACCEPTANCE.md §4）

| 编号 | 阶段 1 R 项 | 阶段 2 处理任务 |
|---|---|---|
| R1 | Schema 合格率 85%（目标 95%） | 不单独处理；R2/R3/R4 修了 R1 自然过线 |
| R2 | 复合 condition few-shot 缺失 | T-2.0 |
| R3 | 选项过长（5/13 节点 ≥ 27 字） | T-2.0 |
| R4 | location_ref 错配 | T-2.0（**v1.0 修订**：location_candidates 字段贯穿到 scene context / prompt / few-shot / generate_scene；不仅节点级修——§2.8 + critique 4.1） |
| R5 | 本体污染 D1 | 强相关；T-2.2 本体落地后自然改善 |
| R6 | AI 判官替代人工 | 不在阶段 2 范围（阶段 4） |
| R7 | cost_log 高估 | T-2.11（**v1.0 修订**：record_id 串联 + 三态 refund；provider 异常分类作 R2.* follow-up——critique 4.10 / Q6） |
| R8 | 机械预检器 | T-2.4（**v1.0 修订**：BOND_ID_UNKNOWN 检查用 state_path_slug 反查 entity.id——§2.6） |

| 编号 | 阶段 1.5 R1.5-* | 阶段 2 处理时机 |
|---|---|---|
| R1.5-1 | 14 立绘 + 1 background 全 batch 未跑 | 阶段 3 工坊期；阶段 2 不做 |
| R1.5-2 | acceptance_rate 未测 | 同 R1.5-1 |
| R1.5-3 | 视觉判官 vs 作者 kappa 未算 | 阶段 2/3 真实 batch 后 |
| R1.5-4 | C4 dev/prod parity smoke | 作者拿 OPENAI_API_KEY 后单独跑（非阶段 2 任务）|
| R1.5-5 | alpha 通道形式合规但实际不透明 | 阶段 2/3 任一 |
| R1.5-6 | mini probe ergonomic 工具 | 阶段 3 工坊化 |

阶段 2 范围内 R 项处理：**R2 / R3 / R4 / R7 / R8 共 5 条**。

---

## 6. 工作 wave 与依赖图（v1.0 整合校准；critique 3.4）

```
Wave 0（独立可并行）:
   T-2.0 [A] R 项 cleanup PATCH (R2/R3/R4)         ← C3 闸门
   T-2.10 [A] sidecar OPEN_SOURCE_CARVE_OUT v0.1   ← C5 起步
   T-2.11 [A] cost_log 反向校准 (R7) + record_id 串联
   ↓ 不阻塞下游

Wave 1（串行关键路径起点；ADR-015 已解锁）:
   T-2.1 [B] ADR-016~021 立项（6 条 ADR 一次性 commit）
   ↓ PR merge 后 Wave 2 才能启动 A 阶段

Wave 2（串行关键路径）:
   T-2.2 [B] schema 落地（依赖 T-2.1）
   ↓ PR merge 后 Wave 3 才能启动

Wave 3（A 类可并行；T-2.4 / T-2.5 / T-2.7 三任务并行）:
   T-2.4 [A] R8 机械预检器扩展（dialogue node）  ← T-2.6/T-2.8 隐含依赖
   T-2.5 [A] scene 级 prompt 模板 + skeleton-first 生成策略
   T-2.7 [A] validator 扩展 2A 拓扑 + 2B 抽样验证 + 有界符号执行  ← T-2.6/T-2.8 隐含依赖
   ↓ T-2.4 + T-2.5 PR merge 后 Wave 4 才能启动

Wave 4（依赖 T-2.5 + T-2.4）:
   T-2.6 [A] generate_scene 主函数（**v1.0 修订**：依赖 T-2.5 + T-2.4，不仅 T-2.5）
   ↓ PR merge 后 Wave 5 才能启动

Wave 5（依赖 T-2.6 + T-2.4 + T-2.7）:
   T-2.8 [A] scene experiment + review CLI 扩展（含图视图 + scene_ai_judge runner）
        （**v1.0 修订**：依赖 T-2.6 + T-2.4 + T-2.7，不仅 T-2.6）
   ↓ PR merge 后 Wave 6 才能启动

Wave 6（[B-author-gate] 协议先行）:
   T-2.9 [B] baseline 协议 + 场景级 AI 判官 prompt v1
   ↓ PR merge 后 Wave 7 才能启动

Wave 7（依赖 T-2.4 + T-2.7 + T-2.8 + T-2.9）:
   T-2.12 [A] 实证 batch run + 接受率统计（≥ 70%）
   ↓ PR merge 后 Wave 8 才能启动

Wave 8（验收）:
   T-2.13 [B] 阶段 2 验收报告
```

**v1.0 修订要点**（critique 3.4）：

- T-2.6 真实代码依赖含 T-2.4 的 `validate_graph_mechanical`（generate_scene 主流程整合机械预检 + 重试），**v1.0 任务概览（§7）依赖列从"T-2.5"改为"T-2.5 + T-2.4"**
- T-2.8 真实代码依赖含 T-2.4 + T-2.7（scene_review CLI 展示机械预检 / 拓扑 / 抽样三类 summary），**v1.0 任务概览（§7）依赖列从"T-2.6"改为"T-2.6 + T-2.4 + T-2.7"**
- Wave 图本身正确（v0.1.1 已是 Wave 3 = {T-2.4, T-2.5, T-2.7} / Wave 4 = T-2.6 / Wave 5 = T-2.8），但任务依赖列与 wave 图不一致——v1.0 修依赖列对齐 wave 图

**routine 兼容性（v0.3 治理修订后；与 v0.1.1 一致）**：
- 所有 L3 一律 ABC 闭环（§1.5），与本表 [A]/[B] 列无关——**类型列仅作概念参考**
- routine 仅可串联 **A 阶段**：一个 L3 A 阶段 commit + push + 开 PR 后，可自动跑下一个不冲突 L3 的 A 阶段
- routine **不可跨过 B/C/验收闭环**——任何 L3 PR 在 A+B+C 全部完成 + L2 验收过关前一律不 merge
- 实际并行度 = Wave 内 L3 的 A 阶段可同时跑；但 Wave 间依赖（如 T-2.6 依赖 T-2.2 的 schema 落地）必须 PR merge 后才能消解

---

## 7. 任务清单概览（v1.0 整合校准）

| ID | 类型 | 名称 | 模块边界（v1.0 修订） | 依赖（v1.0 修订） |
|---|---|---|---|---|
| **T-2.0** | [A-execute] | R 项 cleanup PATCH（R2/R3/R4） | `/generator/prompts/`、`/generator/tests/`、fixture、**`/generator/context_assembler.py`（仅 GraphContext.location_card → location_candidates 字段，critique 3.3）** | 无 |
| **T-2.1** | [B-author-gate] | ADR-016~021 立项（6 条 ADR） | `/docs/DECISIONS.md` | 无 |
| **T-2.2** | [B-author-gate] | schema 落地：本体扩展 + 时钟 + Chapter/Act + dramatic_triggers + narrative_weight | `/schema/`、`/state/ontology/`、`/docs/SCHEMA_v0.3.md` 新建、**`/schema/tests/`（critique 4.5）**、**`/state/tests/`（critique 4.5）** | T-2.1 |
| **T-2.3** | [B-author-gate] | （已并入 T-2.1） | — | — |
| **T-2.4** | [A-execute] | R8 机械预检器扩展（dialogue node） | `/validator/`、`/generator/tests/` | T-2.2 |
| **T-2.5** | [A-execute] | scene 级 prompt 模板 + skeleton-first 生成策略 | `/generator/prompts/scene/`（**含 `__init__.py`，critique 4.6**）、`/generator/scene_strategies.py`、**`/pyproject.toml` packages 加 `generator.prompts.scene`（critique 4.6）** | T-2.2 |
| **T-2.6** | [A-execute] | generate_scene 主函数 | `/generator/generate_scene.py`、`/generator/context_assembler.py` 扩展 | **T-2.5 + T-2.4**（v1.0 修订；critique 3.4） |
| **T-2.7** | [A-execute] | validator 扩展 2A 拓扑 + 2B 抽样验证 + 有界符号执行 | `/validator/graph_validation.py`（**包装现有 `graph_check.py`，§2.7**）、`/validator/sampling.py` | T-2.2 |
| **T-2.8** | [A-execute] | scene experiment + review CLI 扩展（含图视图 + **scene_ai_judge runner，critique 4.8**） | `/generator/scene_experiment.py`、`/generator/scene_review_cli.py`、`/generator/scene_metrics.py`、`/generator/graph_view.py`、**`/generator/scene_ai_judge.py`（critique 4.8）** | **T-2.6 + T-2.4 + T-2.7**（v1.0 修订；critique 3.4） |
| **T-2.9** | [B-author-gate] | baseline 协议正式定义 + 场景级 AI 判官 prompt v1 | `/generator/protocols/STAGE_2_BASELINE_PROTOCOL.md`、`/generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md`、**`/pyproject.toml` package-data 加 `"generator.prompts.scene" = ["*.md"]`（critique 4.6）** | T-2.6 |
| **T-2.10** | [A-execute] | sidecar OPEN_SOURCE_CARVE_OUT_INDEX.md v0.1 | `/docs/OPEN_SOURCE_CARVE_OUT_INDEX.md` | 无 |
| **T-2.11** | [A-execute] | cost_log 反向校准（R7）+ usage_metadata 接入 + record_id 串联 + 三态 refund | `/generator/budget.py`、`/generator/providers/gemini.py`、`/generator/cost_log.py`、**`/generator/generate_node.py`（仅 reconcile/refund hook，critique 3.3）** | 无 |
| **T-2.12** | [A-execute] | 实证 batch run（N=15 场景）+ 接受率统计 | 跑批次 + 写实验报告 | T-2.4 + T-2.7 + T-2.8 + T-2.9 |
| **T-2.13** | [B-author-gate] | 阶段 2 验收报告 | `/docs/STAGE_2_ACCEPTANCE.md` 新建 | T-2.12 |

**任务总数**：13 条编号槽位 = 12 个 paste-ready prompt + T-2.3 placeholder（critique 5.1）。

---

---

## 8. T-2.0 ~ T-2.13 paste-ready 执行会话 prompt（v1.0 整合版）

> 每条 prompt 是**自包含的可直接复制到新执行会话首条消息**。作者按 wave 顺序开 Claude Code 执行会话，从下方对应任务直接复制 ` ```text` 代码块全文作为首条消息。
>
> **v1.0 修订要点**：
> - 所有 L3 prompt 引用自身决策章节时统一改为 `/docs/STAGE_2_TASKS.md` 对应章节（v1.0 commit 后该路径生效；commit 前可临时引用本草稿，但不应作为执行源——critique 4.4）
> - B 阶段报告路径统一改为 `/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`（跟 REVIEW_PROMPT_CODE_GPT.md commit `8842c43` 模板，§1.5 修订）
> - T-2.1 删 v0.1.1 line 471 "等作者明示 commit it"（critique 3.5）
> - 各 L3 模块边界 / 测试范围 / 字段命名按 §2-§7 修订对齐

---

### T-2.0 ｜ R 项 cleanup PATCH（R2/R3/R4）｜ [A-execute]

```text
你的任务是落地阶段 2 起手 cleanup gate（C3 硬闸门），处理阶段 1 验收遗留的 R2 / R3 / R4。

# 任务类型：[A-execute]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 纯执行；改 prompt 模板 + fixture + 测试 + GraphContext.location_candidates 字段；不动 schema / ADR / SCHEMA_v0*.md / L1 文档
- A 阶段：commit + push + 开 PR（base=main，head=本 worktree 分支名）
- routine 串行 OK——本任务不阻塞下游

# 模块边界（硬性；v1.0 修订）
允许修改：
  - /generator/prompts/system.py
  - /generator/prompts/few_shot.py
  - /generator/tests/
  - /generator/fixtures/（如不存在则新建）
  - /generator/context_assembler.py（**仅 GraphContext.location_card 字段 → location_candidates；不动其他字段**——v1.0 critique 3.3）
严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/（除新增 fixture 文档外）、/generator/generate_node.py、/generator/llm_provider.py、/generator/budget.py

# 必读
- /CLAUDE.md（规则 1-10）
- /generator/CLAUDE.md
- /docs/STAGE_2_TASKS.md §2.8（一致性统一表 — location_candidates 字段贯穿）+ §5（R 项处理表 R4 v1.0 修订）
- /docs/STAGE_1_ACCEPTANCE.md §4 R1–R8（理解三条 R 的根因）
- /generator/prompts/system.py（当前 system prompt）
- /generator/prompts/few_shot.py（当前 few-shot 来源 = 《铁誓驿站》5 节点）
- 检查 baseline_004 三条失败的 raw_text（在 generator/experiments/20260427T081515Z_baseline_004/results.jsonl）

# R2：StateCondition 复合形态（all_of / any_of / not）few-shot 缺失

# 待落地点
1. 在 /generator/prompts/few_shot.py 增补 1-2 个手写复合 condition 示例：
   - 示例 A（all_of + not 嵌套）：参考《铁誓驿站》opt_read_the_room（all_of[has, not eq]）
   - 示例 B（any_of）：参考 patrol_arrives.opt_invoke_old_bond（any_of[gte, has]）
   两个示例的 (input_context, expected_node) 对要明确标注复合 condition 的语义
2. system.py 的"输出必须符合 schema"段落补一句明示：
   "StateCondition 有两种形态——叶条件（op+path+value）和复合条件（all_of / any_of / not 三选一）；不可混用；复合条件的子节点本身也是 StateCondition"
3. 不动 schema / 不动 fixture 路径

# R3：选项过长（5/13 节点 ≥ 27 字）—— 改硬约束

# 待落地点
4. system.py 加硬约束："Option.text 长度严格 ≤ 25 汉字（中文计数；英文按 word 等价）；超长 = schema_invalid"——比之前"≤ 25 优先"硬一档
5. 这条仅是 prompt 层硬约束；JSON Schema 层不加 maxLength（Schema 已锁定，不动）
6. 后续 T-2.4（R8 机械预检器扩展）会在 dialogue node 级别再做一次确定性校验

# R4：location_ref 错配（fixture 给单 location 模型乱猜本体外地点）

# 待落地点（v1.0 修订；critique 4.1）
7. 修改 /generator/fixtures/（或当前 fixture 来源处）：把 location_card 单值升级为 location_candidates 数组形态——给模型 2-3 个本体已定义的 location_ref 候选，让它选一个而不是猜
8. /generator/context_assembler.py 的 GraphContext 字段：
   - location_card: dict → location_candidates: list[dict]（**v1.0 修订**：字段名也变更，不只是结构；与 T-2.5 / T-2.6 SceneGraphContext 字段名统一——critique 4.1 / §2.8）
   - 如需"主地点"语义，新增 primary_location_ref: str | None 字段（默认 None）
   - 这一步**不动 schema 文件**，仅改 Python dataclass + prompt 模板
9. 同步更新 system.py + few_shot.py 中所有 location_card 引用为 location_candidates

# 不要做的事
- 不要扩展 JSON Schema（CLAUDE.md 规则 2）
- 不要改 GeminiProvider 内部
- 不要碰 budget.py
- 不要在此任务里实现 R8 机械预检器（那是 T-2.4）
- 不要在此任务里跑 baseline batch（那是 T-2.12）
- **不要保留"如果 dataclass 改动太大就停"的模糊兜底**（v0.1.1 line 289）——location_candidates 字段是本任务核心，必须改完；如有跨边界硬阻塞（如必须改 schema 才能完成）才停下来报告

# 测试
- 在 /generator/tests/test_few_shot.py 增加单元测试：复合 condition 示例可被 Pydantic _generated 模型解析
- 新增 /generator/tests/test_context_assembler_location.py：验证 location_candidates 字段格式 + primary_location_ref 默认 None
- 跑 pytest，必须全过

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- diff 摘要
- 跑了哪些测试
- commit message: `fix(generator): R2 R3 R4 cleanup gate for Stage 2 (T-2.0)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.0_<topic>_review.md`（**v1.0 修订**：跟模板默认路径，参考阶段 1.5 commit `33611cd` 9 份 backfill 落盘格式）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.1 ｜ ADR-016 ~ ADR-021 立项（6 条 ADR 一次性 commit）｜ [B-author-gate]

```text
你的任务是把阶段 2 的 6 条架构决策一次性写入 /docs/DECISIONS.md。
作者已通过 2026-05-03 L2 规划师会话明确授权（CLAUDE.md 规则 10 例外）——属"批量立 ADR"先例延续，参考 commit `1d2030f`（ADR-011/012/013 一次性 3 条）+ commit `9851419`（ADR-015 implement Round 5 synthesis）。

# 任务类型：[B-author-gate]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 修改 L1 架构文档；CLAUDE.md 规则 10 例外（作者已在 2026-05-03 L1-L2 校准会话明确授权立 ADR-016~021）
- A 阶段：按 ABC 闭环 commit + push + 开 PR（base=main，head=本 worktree 分支名）；**v0.3 起统一 commit + 开 PR，不再"等作者明示 commit it"**（v1.0 修订：删 v0.1.1 line 471 旧流程残留——critique 3.5）
- B/C 阶段：作者会更仔细审 PR diff（毕竟动 ADR）；过 ABC + L2 验收后 merge
- routine：A 阶段完成 push + 开 PR 后 routine 可继续；但 PR 在 B/C/L2 验收闭环前不 merge，下游依赖任务的 A 阶段需等 PR merge

# 模块边界（硬性）
只允许修改：/docs/DECISIONS.md
严禁修改：CLAUDE.md / SCHEMA_v0*.md / DEBATE_NOTES.md / ROADMAP.md / 任何 /schema/ 文件 / 任何 /state/ 文件 / 任何代码

# 必读（按顺序）
- /CLAUDE.md（规则 1-10）
- /docs/DECISIONS.md 全部 15 条 ADR（理解格式 + 编号约定）
- /docs/STAGE_2_TASKS.md §3（推荐立项的 ADR 清单 — 本任务来源）+ §2（锁定的架构决策，含 §2.4/§2.5/§2.6 等 v1.0 整合校准）
- /docs/reviews/master_plan/2026-04-30_synthesis.md §6 阶段 2 启动 checklist
- /docs/HANDOFF_STAGE_1_TO_2.md
- /docs/STAGE_1.5_ACCEPTANCE.md §5

# 6 条 ADR 落地清单（v1.0 修订）

## ADR-016：阶段 2 本体最小可生成契约
- 状态：已接受（2026-05-03）
- 背景：阶段 0/1 本体桩态启动阶段 2 = R4/R5 在多节点指数化放大成场景级污染（synthesis §3.3 + GPT §3.1 共识）
- 决策：阶段 2 起手期一次性落地正式本体最小契约 schema；范围：
  - **character 实体**（v1.0 修订）：`id`（pattern `^char_[a-z0-9_]+$`，envelope 字段名；不引入 `character_id` 冗余名）/ `display_name` / `description` / **`state_path_slug`**（v1.0 新增；默认 = `id` 去 `char_` 前缀；`pattern: "^[a-z0-9_]+$"`；作者可校准）/ `character_features`（描述性特征数组，含 vellin "stoic mercenary"等）/ `dramatic_triggers`（PZ §4 戏剧义务字段，详见 ADR-019）/ `relations: []`（含 narrative_weight，详 ADR-018）/ `visual_assets`（已由阶段 1.5 加，保留）
  - **location 实体**：`id`（pattern `^(scene_|loc_)[a-z0-9_]+$`）/ `display_name` / `description` / `location_type: enum[scene, sublocation]` / `parent_location_ref`（场景层级）
  - **state path 命名空间表**（v1.0 修订）：`world.*`（**含 `world.scene_count` / `world.long_rest_count` 系统时间双轨**）/ `faction.<faction_id>.*` / `relationship.<state_path_slug>.*`（**v1.0 修订**：`<state_path_slug>` = character entity 的 `state_path_slug` 字段值，不是 `<character_id>`；保 gold scene `relationship.vellin.trust` 不动）/ `flag.*` / `player.*`；阶段 2 起 path 命名必须落入这五个命名空间之一，否则 validator 拒收
  - **Chapter/Act 容器 schema**：`chapter_id`（pattern `^chap_[a-z0-9_]+$`）/ `display_name` / `acts: [{act_id, display_name, included_scenes: [scene_anchor]}]`；本体新增顶层 `chapters: []` 数组（U-CL-4 强建议前移到阶段 2）
  - **系统时间双轨**（PZ §3.1）：`world.scene_count`（每场景 +1，被动节奏）+ `world.long_rest_count`（玩家长休 +1，玩家节奏控制感）；不做实时计时器（违反 ADR-002 极简运行时）
  - **schema 版本号策略**（v1.0 新增；详 STAGE_2_TASKS §2.4）：新建 character / location / clock / chapter schema 文件首版即 const "0.3.0"；既有 dialogue_graph / node / option / state_effect / state_condition 的 schema_version const **保持 "0.1.1" 不动**；新增字段（如 generation_trace.slot_assignments）走 optional + additionalProperties 兼容路径
- 替代方案及否决理由：
  - 推到阶段 3：synthesis §3.3 + GPT §3.1 已共识阶段 2 启动需要本体最小契约
  - 仅 character + location 不加 Chapter/Act：阶段 1/2 已生成内容到阶段 3 需回填层级（U-CL-4）
  - 加 Sibling 涌现项目接口预留：premature abstraction，PZ §6 已强约束
  - **state path 用 `<character_id>` 全名**（v1.0 新增）：会让 gold scene `relationship.vellin.trust` 失败；改 gold 风险高于加 slug 字段
  - **新增字段 bump 既有 schema_version 至 0.3.0**（v1.0 新增）：会破 gold scene 与所有阶段 0/1 测试；按 SCHEMA_v0.2 先例 optional 字段走兼容路径
- 后果：
  - 阶段 2 schema commit 全部串行卡口在本 ADR 落地后启动（T-2.2）
  - validator 扩展（T-2.7）必须支持本体引用闭合 + state path 命名空间合法性 + state_path_slug 反查
  - prompt 模板（T-2.5）必须把 character_features / dramatic_triggers / Chapter/Act / 系统时间双轨纳入 context

## ADR-017：时钟系统
- 状态：已接受（2026-05-03）
- 背景：PbtA Faction Clocks（DEBATE §6.1）作为 ADR-006 真相之源的一部分，需要正式 schema；PZ 反思 §3.2 给出草图
- 决策：
  - 时钟分类三类：`world` / `faction` / `environmental`
  - `Clock` schema：`id` / `name` / `scope: enum["world","faction","environmental"]` / `ticks_total: int`（schema maximum 20）/ `ticks_filled: int`（PbtA 术语；非 ticks_current）/ `advance_rule: {type, params}` / `tick_effects: [{at_tick, effect_op, path, value}]`
  - **advance_rule.type 默认范围**：仅 `event_based` 子类（`every_n_scenes` / `on_long_rest` / `on_faction_action` / `on_player_choice`）；不做 time-based（运行时无真时间，违反 ADR-002）；**SCHEMA_v0.3.md §4 明示"不存在 time_based 子类"**（v1.0 新增；critique §7）
  - **边界软上限**（PZ §3.4 + v1.0 critique §6）：单 clock `ticks_total ≤ 20`（schema maximum 落地）；**同时活跃 clocks ≤ 10 由 T-2.7 sampling/validator 出 warning 级检查**（schema 层不加；T-2.7 落地后由实测倒推真实上限，本 ADR v0.2 修订）
  - **tick_effects.effect_op 与 StateEffect.op 映射**（v1.0 新增；critique §9）：`effect_op` 枚举值与现有 `StateEffect.op`（set / inc / dec / add / remove）一致；T-2.7 effect 应用器用统一映射函数
  - 时钟存储位置：`/state/ontology/<world_name>.json` 顶层 `clocks: []` 数组
- 替代方案及否决理由：
  - 不立时钟 schema：阻塞 prompt 模板（T-2.5）context 注入；扩 ADR-006 而不分立 = 单条 ADR 太大
  - 含 time-based 步进：违反 ADR-002 + ADR-004 极简精神；运行时是 JSON 播放器无真时间
  - **同时活跃 ≤ 10 写进 schema**（v1.0 新增）：定义域随阶段演进；T-2.7 实测倒推后由 ADR-017 v0.2 修订，比硬写 schema 灵活
- 后果：
  - prompt 模板必须在 GraphContext 注入当前活跃 clocks 状态（v1.0 字段名 `active_clocks`）
  - validator 必须校验 tick_effects.path 落入合法 state path 命名空间（ADR-016）
  - T-2.7 第二层 2B 抽样验证可推理时钟状态空间（ticks_total × clocks 数 = 抽样维度）

## ADR-018：关系层 narrative_weight
- 状态：已接受（2026-05-03）
- 背景：PZ §3.3——LLM 倾向把所有关系都写进每场对白，污染节奏；作者需控制"哪些关系真的进戏"
- 决策：
  - character entity 加 `relations: []` 字段（**嵌入式**，不引入全局关系表——v1.0 §2.5 / Q3）
  - 每项 `{target_character_ref, relation_type, narrative_weight: enum["core","minor","context_only"]}`
  - 语义：`core` = 必须显性体现；`minor` = 可选体现；`context_only` = 仅作 prompt 一致性 anchor，不出现在玩家可见对白
  - prompt 模板（T-2.5）按 narrative_weight 决定 context 注入：core / minor 进 prompt，context_only 仅作合法性约束
- 替代方案及否决理由：
  - 不加权重字段：LLM 在多角色场景下会写"全员问候"式对白；阶段 2 70% 接受率难达
  - 加 numeric weight（0-100）：作者难校准；离散三档对作者审阅心智更友好
  - `mandatory / optional / background` 字面：与 BG3 任务系统术语易混淆；core/minor/context_only 偏向叙事理论术语
  - **全局关系表**（v1.0 新增）：会破 ADR-006 单一真相之源（同一关系在 from / to 两端冗余）；嵌入到 character envelope 内更自然
- 后果：
  - 角色花名册更新工作量：T-2.2 落地 vellin / corvan / aelwin 关系矩阵
  - prompt 模板必须按 narrative_weight 决定注入逻辑

## ADR-019：角色槽位持久化形态
- 状态：已接受（2026-05-03）
- 背景：U-GPT-5——ROADMAP 阶段 2 重点工作"角色槽位（role slot casting）与动态选角"持久化决策点未拆开
- 决策：
  - 持久化层（`/state/ontology/` + `/content/<scene>/scene.json`）仍 concrete `character_refs`——不破 ADR-006 单一真相之源
  - 抽象槽（如 "the betrayer", "the witness", "the broken oath-keeper"）作为 generator 中间产物
  - 落到节点级 `generation_trace.slot_assignments` 字段（**走 optional + additionalProperties 兼容路径，不 bump dialogue_graph schema_version**——v1.0 修订；STAGE_2_TASKS §2.4） — 结构：`slot_assignments: {<slot_id>: {character_ref, assigned_at, source_prompt_hash}}`
  - 后续场景生成可读取此 trace 维持槽位一致性（跨场景同槽 → 同 character）
  - 阶段 2 不实现"动态换角"逻辑——那是阶段 3 跨场景一致性范畴
- 替代方案及否决理由：
  - 持久化层引入 `slot_tags` 字段双轨：违反 ADR-006 单一真相；schema 复杂度大
  - 完全只靠 generator 中间产物 + 不写 trace：跨场景重生成不可重现
  - **generation_trace bump dialogue_graph schema_version 至 0.3.0**（v1.0 修订）：会破 gold scene + 阶段 0/1 测试；按 SCHEMA_v0.2 先例 optional 字段走兼容路径更稳
- 后果：
  - generation_trace 字段表追加 slot_assignments 子字段（**dialogue_graph + node schema_version 不动**）
  - generate_scene（T-2.6）必须在节点产物里写 slot_assignments
  - validator 不强制 slot_assignments 必填（trace 仍 optional）

## ADR-020：阶段 2 baseline 协议
- 状态：已接受（2026-05-03）
- 背景：U-GPT-4 硬闸门——70% 接受率口径必须先定义再写代码（ROADMAP 启动闸门）
- 决策：
  - **样本数 N**：15 场景（场景级单次成本高于节点级；N=20 太烧；N=10 统计弱）
  - **重试规则**：复用 ADR-013 max_retries=2（共 3 次）；schema 失败 + 图论失败回喂模型
  - **AI 判官权重**：节点级 21 维度 × 节点数 + 场景级新增 6–10 维度（图拓扑健康 / 节奏 / 角色弧线 / 决策意义 / 收束 / 长度合理 / context 一致性 / 关系层一致性 / 时钟一致性 / ID 命名规范）；具体维度由 T-2.9 落地
  - **机械失败口径**：option 长度（≤ 25 汉字）+ path 前缀（落入 ADR-016 五个命名空间）+ bond ID 白名单（**state_path_slug 反查**——v1.0 修订）+ target_node_id 闭合 + unavailable_behavior 枚举合法性 + state path 命名空间合法性 + StateCondition 形态互斥
  - **接受率分母**：通过机械预检 + 进入 review_log 的场景数
  - **接受率分子**：作者标 [A]ccept 的场景数（不是 AI 判官打分）
  - **报告同时给 gross pass rate 和人工接受率**（v1.0 新增；critique §10 weakness 2）：gross pass = 通过机械预检的场景数 / 总尝试场景数；接受率（作者签字）作为最终判定
  - **AI 判官与作者关系**：AI 判官是辅助参考分（21 维 + 场景级新增），作者最终标 [A]/[R]/[S]——与阶段 1 R6 一致
  - **成本估算口径统一**（v1.0 修订；critique 5.2）：每场景估 ~$0.5–$1.0；N=15 总 $7–$15；N=20 总 $10–$20
- 替代方案及否决理由：
  - **N=20 场景**：成本 $10–$20，烧；N=15 平衡（v1.0 成本口径修订）
  - 接受率分子用 AI 判官：阶段 1 R6 已锁"作者最终签字"
  - 不定义机械失败口径：U-GPT-4 漏抓的核心点；模糊定义将下游统计一致性废
- 后果：
  - T-2.4 R8 机械预检器要按本协议落地
  - T-2.9 AI 判官 prompt 按本协议设计权重
  - T-2.12 实证 batch run 按 N=15 跑

## ADR-021：ADR-009 第二层方法论拆 2A 拓扑 + 2B 抽样验证 + 有界符号执行
- 状态：已接受（2026-05-03）
- 背景：U-GPT-1 🔴——当前 schema 缺状态变量定义域 / 初始状态集合 / effect 边界，"证明任意合法状态组合可达结局"目前不可判定；ROADMAP 阶段 2 完成标志措辞需修订
- 决策：
  - **2A 纯拓扑校验**（v1.0 修订；critique 4.7 / Q5）：图遍历层 — **结构拓扑 + condition 引用形态合法性**（仅检查 path 命名空间 / op 枚举 / 字段结构）/ 前置条件路径闭合（option.condition 字段格式合法）/ 不可达节点 / 死锁（非 end 节点入度可达但 option 集合中无任何 condition=null option）/ 分支收敛性。**condition satisfiability 不在 2A 内**——避免把启发式包装成 condition-aware 已完成
  - **2B 抽样验证 + 有界符号执行**：
    - 抽样 N=100 路径起步（从 entry 出发随机选 option，记录 state 演化，检查能否到 end 节点）
    - 有界符号执行：在 ADR-016 命名空间内枚举 effect 链产生的 state 组合（边界由 ADR-017 时钟数 × ticks_total + flag 离散值集决定）
    - **condition satisfiability 全部走 2B**（v1.0 修订）
    - **完成标志措辞修订**（ROADMAP §阶段 2 完成标志，**跨边界 X1，由作者另起 L1 doc 修订会话**）：从"证明任意合法状态组合下至少有 1 个结局可达"改为"**抽样验证 N=100 路径 + 有界符号执行下未发现反例**"
  - **N 值首版**：N=100；**经验阈值，不暗示充分证明**（v1.0 新增；critique §10 weakness 3）；阶段 2 实测后由 ADR-021 v0.2 倒推合理 N
  - **完成标志拆双报**（v1.0 新增；critique 4.7 / Q5）：T-2.7 完成标志分别报告（a）2A 纯拓扑 pass（gold scene 全过 + 0 error）；（b）condition-aware（2B 抽样 + 有界符号执行）pass（gold scene 抽样 N=100 全 reach end + 0 反例）
- 替代方案及否决理由：
  - 严格证明：当前 schema 不支持，强行写完成标志会造成"过线假象"
  - 仅抽样模拟不做有界符号执行：U-GPT-1 推荐双路径——抽样找显式反例，符号执行覆盖低概率组合
  - **2A 内含 condition-aware**（v1.0 修订）：A2 自承"复杂；起步用启发式"；启发式包装成 condition-aware "已完成"会误导阶段 2 验收
  - **给 2A 加有限 state evaluator**（Q5 替代方案 B）：state evaluator 复杂度高、阶段 2 起步范围；拆双报清晰显示边界
- 后果：
  - validator 第二层（T-2.7）按 2A + 2B 拆分实现
  - T-2.7 完成标志拆双报；T-2.13 验收报告引用双报数据
  - ROADMAP 完成标志措辞由作者另起 L1 修订会话同步（不在本任务范围；**跨边界 X1**）

# 立项规则（共通）
- 状态行 = "已接受（2026-05-03）"
- 后果行明示哪些下游 L3 任务依赖本 ADR
- 末尾在 /docs/DECISIONS.md "变更历史" 段追加：
  ```
  - 2026-05-03：作者明确授权新增 ADR-016 / 017 / 018 / 019 / 020 / 021（阶段 2 六条架构决策一次性立），属 CLAUDE.md 规则 10 的明示例外。整合自 STAGE_2_TASKS_v1.0_draft（含 GPT-5.5 critique 校准）。L2 整合规划师会话（claude/musing-fermi-f6bfd3）2026-05-03 L1-L2 校准产物。
  ```

# 不要做的事
- 不要修改 SCHEMA_v0*.md（那是 T-2.2 范围）
- 不要修改任何 /schema/ 文件
- 不要修改任何代码
- 不要碰 ROADMAP.md 阶段 2 完成标志措辞——那是另一个 L1 修订会话（**跨边界 X1**）
- 不要在 ADR 内写"如何实现"的代码细节（ADR 是 what + why + 后果，不是 how）
- 不要超过 6 条 ADR 范围（dramatic_triggers 是 character 字段，并入 ADR-016；不单立）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- /docs/DECISIONS.md 的 diff 摘要（按 ADR 分段）
- 6 条 ADR 各自字数（建议每条 ≤ 100 行）
- commit message：`docs: add ADR-016/017/018/019/020/021 for Stage 2 (T-2.1)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.1_<topic>_review.md`（**v1.0 修订**：跟模板默认路径）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
```

---

### T-2.2 ｜ schema 落地（本体扩展 + 时钟 + Chapter/Act + dramatic_triggers + narrative_weight）｜ [B-author-gate]

```text
你的任务是把 ADR-016/017/018/019 的 schema 决策落地到 /schema/ + /state/ontology/，并新增 SCHEMA_v0.3.md 设计说明文档。
作者已通过 2026-05-03 L2 规划师会话明确授权（CLAUDE.md 规则 2/10 例外）——**新建 schema 文件首版即 const "0.3.0"；既有 schema 文件 const 保持 "0.1.1" 不动**（v1.0 修订；STAGE_2_TASKS §2.4）。

# 任务类型：[B-author-gate]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 动 schema + 改 SCHEMA_v0*.md + 动 /state/ontology/；CLAUDE.md 规则 2 + 10 例外（作者已在 2026-05-03 L1-L2 校准会话明确授权）
- A 阶段：按 ABC 闭环 commit + push + 开 PR；**v0.3 起统一 commit + 开 PR**
- B/C 阶段：作者会更仔细审 PR diff（毕竟动 schema）；过 ABC + L2 验收后 merge

# 模块边界（硬性；v1.0 修订）
允许修改 / 新建：
  - /schema/character.schema.json（**新建**；正式化角色 schema，对应 ADR-016；schema_version const "0.3.0"）
  - /schema/location.schema.json（**新建**；schema_version const "0.3.0"）
  - /schema/clock.schema.json（**新建**；schema_version const "0.3.0"）
  - /schema/chapter.schema.json（**新建**；schema_version const "0.3.0"）
  - /schema/dialogue_graph.schema.json（**仅修改：generation_trace 字段表追加 slot_assignments 子字段，optional + additionalProperties 兼容路径；schema_version const 保持 "0.1.1" 不动**——v1.0 修订）
  - /schema/node.schema.json（同上，generation_trace 子字段联动；const 保持 "0.1.1"）
  - /state/ontology/waystation.json（修改：扩展 character 实体加 character_features + dramatic_triggers + relations[narrative_weight] + state_path_slug；location 实体扩展 + 新增 location_id；新增顶层 chapters[] + clocks[] + system_time）
  - /docs/SCHEMA_v0.3.md（**新建**；设计说明，含复合版本号语义解释）
  - /generator/scripts/regenerate_models.sh（修改：把新 schema 加入生成范围）
  - /generator/models/_generated/（自动重新生成）
  - **/schema/tests/test_stage2_ontology_schema.py（v1.0 新增；critique 4.5）** — schema 关键卡口测试，必须先于下游 generator 测试落
  - **/state/tests/test_stage2_ontology_loader.py（v1.0 新增；critique 4.5）** — loader 兼容测试（按 entity["id"] 索引仍 pass）
  - /generator/tests/（仅测 generated models 消费 + prompt/context 消费；schema 校验本身归 /schema/tests/）
严禁修改：
  - /schema/option.schema.json / state_effect.schema.json / state_condition.schema.json / image_asset.schema.json（**这些 schema_version const 保持 "0.1.1"，不动**——v1.0 修订；详 STAGE_2_TASKS §2.4）
  - /docs/SCHEMA_v0.md / SCHEMA_v0.2.md（历史版本不动）
  - CLAUDE.md / DECISIONS.md（除 T-2.1 外不该出现 ADR 修改）
  - /engine/ / /validator/（validator 扩展是 T-2.7 / T-2.4 范围）
  - /content/test_scene_v0/scene.json（gold standard 不动；schema_version 保持 0.1.1，由 SCHEMA_v0.2 先例）

# 必读
- /CLAUDE.md
- /docs/DECISIONS.md ADR-016/017/018/019（**T-2.1 落地后才能跑本任务**——pre-flight check：grep ADR-016 /docs/DECISIONS.md，没有就停下来）
- /docs/STAGE_2_TASKS.md §2.4（schema_version 复合版本号语义；**v1.0 关键决策依据**）+ §2.5（envelope 契约）+ §2.6（state_path_slug 字段）
- /docs/SCHEMA_v0.md（基线版）
- /docs/SCHEMA_v0.2.md（image_asset + visual_assets 增量参考；本 v0.3 仿其格式 + "非结构性变更不联动 schema_version" 先例）
- /state/ontology/waystation.json（当前桩状态）
- /state/ontology/__init__.py（当前 loader，按 entity["id"] 索引；本任务不动 loader 但需测试兼容）
- /generator/CLAUDE.md（阶段 1.5 例外段落，了解本体写入合法授权机制）
- /schema/tests/test_schemas.py（现有 schema 测试位置参考；本任务在 /schema/tests/ 加新文件）

# 待落地点

## 1. /schema/character.schema.json 新建（v1.0 修订；envelope 契约 + state_path_slug）
- $schema = JSON Schema 2020-12
- schema_version = "0.3.0"
- 校验对象 = entity 全对象（含 envelope 字段，不引入 character_id 冗余名）
- 必填字段：
  - id（pattern `^char_[a-z0-9_]+$`，envelope 字段）
  - type（const "character"，envelope 字段）
  - display_name
  - description
  - **state_path_slug**（v1.0 新增；pattern `^[a-z0-9_]+$`；语义详 STAGE_2_TASKS §2.6）
  - character_features（string array，描述性特征如 "stoic mercenary"）
  - relations（object array，每项 `{target_character_ref, relation_type, narrative_weight: enum[core/minor/context_only]}`）
- 可选字段：
  - dramatic_triggers（object array，每项 `{trait, when, how, priority?: int, cooldown_scenes?: int}`）
  - visual_assets（保留 v0.2 的 ImageAsset 数组形态）
- additionalProperties: false

## 2. /schema/location.schema.json 新建（v1.0 修订；envelope 契约）
- 校验对象 = entity 全对象
- 必填：
  - id（pattern `^(scene_|loc_)[a-z0-9_]+$`）
  - type（const "location"）
  - display_name
  - description
  - location_type: enum[scene, sublocation]
- 可选：parent_location_ref / visual_assets（沿用 ImageAsset 数组）
- additionalProperties: false

## 3. /schema/clock.schema.json 新建
- 必填：id（pattern `^clk_[a-z0-9_]+$`）/ name / scope: enum[world, faction, environmental] / ticks_total: integer minimum 1 maximum 20 / ticks_filled: integer minimum 0
- 必填：advance_rule: {type: enum[every_n_scenes, on_long_rest, on_faction_action, on_player_choice], params: object}
- 可选：tick_effects: array of {at_tick: integer, effect_op: enum[set,inc,dec,add,remove], path: string, value: any}
- additionalProperties: false

## 4. /schema/chapter.schema.json 新建
- 必填：chapter_id（pattern `^chap_[a-z0-9_]+$`）/ display_name / acts: array of {act_id, display_name, included_scenes: array of scene_anchor refs}
- additionalProperties: false

## 5. /schema/dialogue_graph.schema.json + node.schema.json 修改（v1.0 关键修订）
- **schema_version const 保持 "0.1.1" 不动**（不再 bump 至 0.3.0；v1.0 §2.4）
- generation_trace 字段表追加 slot_assignments 子字段：optional dict[str, {character_ref, assigned_at, source_prompt_hash}]；走 additionalProperties + optional 兼容路径
- 不改 dialogue_graph / node 任何已有字段语义；不动 option / state_effect / state_condition 任何字段（schema_version 也不动）
- 注意：/schema/option.schema.json + state_effect.schema.json + state_condition.schema.json 的 schema_version **保持 0.1.1 不动**——按 SCHEMA_v0.2 "非结构性变更不联动 schema_version" 先例

## 6. /state/ontology/waystation.json 修改（v1.0 修订）
- 顶层新增：
  - `system_time`: {scene_count: 0, long_rest_count: 0}（注：在 state path 命名空间表中等价于 `world.scene_count` / `world.long_rest_count` 状态路径）
  - `clocks`: []（首版起步空数组；阶段 2 内由作者按需添加）
  - `chapters`: []（首版起步空数组；可后续 L3 任务填充《铁誓驿站》所属 chapter）
- 现有 entities[type="character"] 三个对象（vellin / corvan / aelwin）扩展：
  - **加 state_path_slug**（v1.0 新增）：vellin → "vellin"；corvan → "corvan"；aelwin → "aelwin"（默认 = id 去 `char_` 前缀，与 gold scene `relationship.vellin.trust` 等路径对齐）
  - 加 character_features 数组（基于已有 description 抽取 3-5 条；不改原 description）
  - **加 dramatic_triggers 数组**（v1.0 修订；critique §10 weakness 4 + STAGE_2_TASKS D10）：起步给 1-2 个 seed 示例（如 vellin 的 trigger：`{trait: "stoic mercenary", when: "被质问过去", how: "沉默几秒后岔开话题", priority: 1}`），让 T-2.5 prompt 测试不空转
  - 加 relations 数组（vellin ↔ corvan、vellin ↔ aelwin、corvan ↔ aelwin 三对；narrative_weight 首版按场景关键度估值——vellin↔corvan = core / vellin↔aelwin = core / corvan↔aelwin = minor，可由作者校准）
- 现有 entities[type="scene"]（scene_waystation_of_iron_oath）改为：
  - id 保持 scene_waystation_of_iron_oath（envelope id 字段）
  - 加 location_type: "scene" / description（必填）
- 保留 entities[].visual_assets 字段（v0.2 已加；不动）

## 7. /docs/SCHEMA_v0.3.md 新建（v1.0 修订；含复合版本号语义）
- 仿 SCHEMA_v0.2.md 格式
- §1 增量摘要：v0.3.0 引入哪些新 schema 文件 + 哪些 optional 字段追加（**不联动既有 schema_version**）
- §2 character schema 字段表 + 完整示例 + state_path_slug 语义
- §3 location schema 字段表
- §4 clock schema 字段表 + advance_rule.type 四子类语义 + **明示"不存在 time_based 子类"**
- §5 chapter schema 字段表
- §6 generation_trace.slot_assignments 增量（**强调走 optional 兼容路径，不 bump dialogue_graph const**）
- §7 兼容性约束：
  - v0.3.0 不破坏 v0.1.x / v0.2.0 任何 existing 字段
  - **复合版本号语义**：阶段 2 的 "v0.3" 是 ontology 模块（character / location / clock / chapter）的 MINOR bump，不是 dialogue_graph schema 模块的 bump；两组 schema 文件版本号独立演进
  - 引用 SCHEMA_v0.2 "非结构性变更不联动 schema_version" 先例
- §8 留给 image_validator / graph_validator 的语义约束（不在 schema 层表达的部分）

## 8. /generator/models/_generated/ 重新生成
- 跑 /generator/scripts/regenerate_models.sh（如新建可运行的版本）
- 生成 character.py / location.py / clock.py / chapter.py
- /generator/models/__init__.py 重导出新类型

## 9. /schema/tests/ 新增（v1.0 新增；critique 4.5）
- /schema/tests/test_stage2_ontology_schema.py：
  - waystation.json 三个 character 对象通过 character.schema.json 校验（含 state_path_slug 字段）
  - scene_waystation_of_iron_oath 通过 location.schema.json
  - 构造 sample clock 通过校验；超界（ticks_total > 20）拒收
  - 构造空 chapter 通过校验
  - **gold scene `/content/test_scene_v0/scene.json` 仍 pass dialogue_graph schema v0.1.1**（关键回归测试；critique 3.2）
  - state path 命名空间表（world / faction / relationship / flag / player）枚举校验
  - generation_trace 含 slot_assignments 在 dialogue_graph schema 下被接受

## 10. /state/tests/ 新增（v1.0 新增；critique 4.5）
- /state/tests/test_stage2_ontology_loader.py：
  - 现有 loader（state/ontology/__init__.py，按 entity["id"] 索引）在新 schema 下仍能加载 waystation.json
  - state_path_slug 字段被 loader 正确识别（如有索引需求）
  - 不破阶段 0/1 既有 loader 测试

## 11. /generator/tests/ 新增（仅测 generated models 消费）
- test_character_model_consumption.py：generated character.py 可被 prompt context 消费
- test_clock_model_consumption.py：generated clock.py 可被 prompt context 消费
- 不在此目录测 schema 校验本身（那归 /schema/tests/）

# 实施顺序提醒（pre-flight）
1. 先 `grep "ADR-016" /docs/DECISIONS.md` ——找不到立刻停下来报告（T-2.1 还没跑）
2. 先 `pytest`——确认基线绿
3. 按 1-11 顺序落地
4. 每步落地后跑一次 pytest（增量验证）
5. **关键回归**：跑完 #5 后立即跑 `pytest /schema/tests/`，确认 gold scene 仍 pass dialogue_graph v0.1.1（critique 3.2 / §2.4 核心约束）

# 已知坑提醒
- Gemini 不接受 additionalProperties: false——这是给 datamodel-code-generator 用的；T-2.5 / T-2.6 在 prompt schema 注入前会 sanitize（已在 GeminiProvider 内 sanitize，参考 baseline_001 教训）
- StateCondition 的两形态互斥（叶 vs 复合）已在 v0.1.1 锁定，不动
- /content/test_scene_v0/scene.json 的 schema_version 保持 0.1.1（gold standard 不动）
- **既有 schema (dialogue_graph/node/option/state_effect/state_condition) 的 schema_version const 保持 "0.1.1" 不动**——v1.0 关键修订；不要误改

# 不要做的事
- 不要碰 dialogue_graph / option / state_effect / state_condition 已有字段语义
- **不要 bump dialogue_graph / node / option / state_effect / state_condition 的 schema_version const**（v1.0 关键修订；§2.4）
- 不要在本任务里写 prompt 模板（T-2.5 范围）
- 不要在本任务里改 validator（T-2.4 / T-2.7 范围）
- 不要预先把作者还没填的 clocks / chapters 字段填上"示例"——空数组起步（**dramatic_triggers 例外**：给 1-2 个 seed，让 T-2.5 不空转）
- 不要给 vellin / corvan / aelwin 写虚构的关系类型 / narrative_weight；按 ADR-018 推荐值起步即可

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- /schema/ 新文件清单 + 修改清单（**明确说明：新建 schema const "0.3.0"；既有 schema const 保持 "0.1.1"**）
- /state/ontology/waystation.json 的 diff 摘要
- /docs/SCHEMA_v0.3.md 的字数 + 字段总数统计
- pytest 输出（**含 /schema/tests/ + /state/tests/ + /generator/tests/ 三组**全过 + 既有测试不破）
- **关键回归证据**：gold scene `/content/test_scene_v0/scene.json` 仍 pass dialogue_graph v0.1.1
- A 阶段产出：PR URL + commit hash + 测试输出（A 阶段直接 commit + push + 开 PR；不再等作者授权）
- commit message：`feat(schema): land Stage 2 ontology + clock + chapter + narrative_weight + dramatic_triggers (T-2.2)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.2_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
```

---

### T-2.3 ｜（已并入 T-2.1）

> 本草稿建议 T-2.3 并入 T-2.1（一次性立 6 条 ADR-016~021）。**13 个编号槽位 = 12 个 paste-ready prompt + T-2.3 placeholder**（v1.0 修订；critique 5.1）。如 cross-LLM critique 反对此合并，可拆出 ADR-021（ADR-009 第二层）独立成 T-2.3。

---

### T-2.4 ｜ R8 机械预检器扩展（dialogue node 级别）｜ [A-execute]

```text
你的任务是落地阶段 1 R8 + ADR-020 baseline 协议机械失败口径——把 image_validator 思路移植到 dialogue node 级别。

# 任务类型：[A-execute]
- 改 validator 代码 + 测试；不动 schema / ADR / SCHEMA_v0*.md / L1 文档
- 完成后 commit + push 即可
- routine 串行 OK

# 模块边界（硬性）
允许修改：
  - /validator/dialogue_validator.py（新建；机械预检模块）
  - /validator/__init__.py（导出新模块）
  - /validator/tests/
严禁修改：/schema/、/state/、/state/ontology/、/engine/、/content/、/generator/、/docs/

# 必读
- /CLAUDE.md
- /validator/CLAUDE.md（如存在）
- /generator/image_validator.py（image 版机械预检器；移植参考）
- /docs/STAGE_1_ACCEPTANCE.md §4 R8
- /docs/DECISIONS.md ADR-020 机械失败口径段
- /docs/STAGE_2_TASKS.md §2.6（state_path_slug 字段语义；**v1.0 关键依据**——BOND_ID_UNKNOWN 检查用 slug 反查）
- /docs/SCHEMA_v0.3.md state path 命名空间表

# 待落地点

## 1. /validator/dialogue_validator.py 新建
模块核心函数：

def validate_node_mechanical(node: dict, *, ontology: dict | None = None) -> ValidationResult:
    """
    机械预检 dialogue node。返回多 issue 列表。
    """

@dataclass
class ValidationIssue:
    severity: Literal["error", "warning"]
    code: str           # 如 "OPT_LEN_OVER" / "PATH_NS_INVALID"
    field_path: str     # 如 "options[2].text"
    message: str

@dataclass
class ValidationResult:
    issues: list[ValidationIssue]
    @property
    def has_error(self) -> bool: return any(i.severity == "error" for i in self.issues)

## 2. 9 类机械检查（从 ADR-020 机械失败口径展开；v1.0 修订 C3）
对每条 dialogue node：
- C1 OPT_LEN_OVER：option.text 长度 > 25 汉字（中文 = char count；英文 = word count；混合 = max）→ error
- C2 PATH_NS_INVALID：state_effect.path / state_condition.path 不落入 5 个命名空间（world / faction.<id> / relationship.<slug> / flag / player）→ error
- C3 BOND_ID_UNKNOWN（**v1.0 修订**）：state_effect.path 含 `relationship.<state_path_slug>`、其中 `<state_path_slug>` 不在本体花名册（**用 ontology 中 character entity 的 `state_path_slug` 字段反查 entity.id**）→ error（需要 ontology 参数才能跑；ontology=None 时跳过此条）
- C4 TARGET_UNREACHABLE：option.target_node_id 不在同图 nodes 字典 → error
- C5 UNAVAIL_BEHAVIOR_INVALID：option.unavailable_behavior 不在 [hide, disable, disable_with_hint] → error
- C6 STATE_CONDITION_FORM_MIX：StateCondition 同时含叶字段（op/path/value）和复合字段（all_of/any_of/not）→ error
- C7 EFFECT_OP_INVALID：state_effect.op 不在 [set, inc, dec, add, remove] → error
- C8 CONDITION_OP_INVALID：state_condition.op 不在 [eq, neq, gt, gte, lt, lte, has, has_not] → error
- C9 NODE_TYPE_OPTIONS_MISMATCH：type=dialogue 但 options 空 / type=end 但 options 非空 → error

## 3. 接口扩展
def validate_graph_mechanical(graph: dict, *, ontology: dict | None = None) -> dict[str, ValidationResult]:
    """对图内每个 node 跑 validate_node_mechanical，返回 node_id → result 字典。"""

## 4. 测试 /validator/tests/test_dialogue_validator.py
- 各 9 类 issue 的正反例
- 单 node / 全图两种用法
- ontology=None 时 C3 跳过不报错
- **C3 关键测试**（v1.0 新增）：构造 ontology 含 vellin (state_path_slug="vellin") + corvan (state_path_slug="corvan")；node 用 `relationship.vellin.trust` → pass；node 用 `relationship.unknown_slug.trust` → C3 error
- 通过《铁誓驿站》gold standard（/content/test_scene_v0/scene.json）：所有节点应通过；如有 issue 报告作者（不修 gold standard，由作者拍板）

# 不要做的事
- 不要在此任务里实现图论第二层（2A/2B 是 T-2.7）
- 不要修改 generator 里的 prompt（T-2.5 范围）
- 不要 sanitize / 修复 node——validator 只报 issue，不改写
- 不要做 LLM 判官（T-2.9）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- diff 摘要 + 9 类 issue 各自的代码位置
- pytest 输出
- 在《铁誓驿站》上跑一次的结果（通过率 + 任何 issue）
- commit message: `feat(validator): mechanical pre-check for dialogue nodes (R8 + ADR-020) (T-2.4)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.4_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.5 ｜ scene 级 prompt 模板 + skeleton-first 生成策略｜ [A-execute]

```text
你的任务是设计 scene 级 prompt 模板 + skeleton-first 生成策略，作为 generate_scene 主函数的实现基础。

# 任务类型：[A-execute]
- 改 prompt 模板 + 写 strategy 模块；不动 schema / ADR / SCHEMA_v0*.md
- 完成后 commit + push 即可
- routine 串行 OK

# 模块边界（硬性；v1.0 修订）
允许修改 / 新建：
  - /generator/prompts/scene/__init__.py（**v1.0 新增**；critique 4.6 — 让 generator.prompts.scene 成为正式 Python 子包）
  - /generator/prompts/scene/system.py
  - /generator/prompts/scene/few_shot.py
  - /generator/scene_strategies.py（新建；skeleton-first 生成）
  - /generator/generate_node.py（**仅扩展 NodeRequirement.allowed_targets 字段**；v1.0 新增 critique 4.9）
  - /generator/tests/
  - **/pyproject.toml**（**v1.0 新增；critique 4.6** — packages 列表追加 `generator.prompts.scene`，否则未来 wheel/开源剥离会漏 scene prompt 子包）
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、/docs/、/generator/llm_provider.py、/generator/budget.py、/generator/context_assembler.py（T-2.0/T-2.6 范围）

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-013 / ADR-016 / ADR-017 / ADR-018 / ADR-019
- /docs/STAGE_2_TASKS.md §2.6（state_path_slug；prompt 输出 slug）+ §2.8（一致性细节 — location_candidates / active_clocks）
- /docs/SCHEMA_v0.3.md
- /generator/prompts/system.py（节点级 system prompt 参考）
- /generator/prompts/few_shot.py（节点级 few-shot 参考）
- /generator/generate_node.py（NodeRequirement 当前定义）
- /content/test_scene_v0/scene.json（gold standard）
- /docs/HANDOFF_STAGE_1_TO_2.md §"阶段 2 规划粗想"中关于 scene 生成策略的 A/B/C 三候选（C = skeleton-first 已被 Wave 2 默认采纳）
- /pyproject.toml 当前 packages / package-data 配置

# 待落地点

## 1. /generator/prompts/scene/__init__.py（v1.0 新增）
- 空 module docstring；让 setuptools 识别为 package
- 不暴露任何符号（让 system.py / few_shot.py 各自被显式 import）

## 2. /generator/prompts/scene/system.py
SCENE_SYSTEM_PROMPT 字符串常量（中文），描述：
- 你是 RPG 场景级对话图生成器（区别于阶段 1 节点级）
- 目标：一次生成一棵完整对话树（5–15 节点，3–5 个 ending），符合 DialogueGraph schema v0.1.1（**注**：dialogue_graph schema_version 不变；新字段走 optional 兼容路径——v1.0 §2.4）
- 输入：scene_anchor / target_beats（节拍序列）/ participating_npcs（含 character_features + dramatic_triggers + relations narrative_weight） / **active_clocks**（v1.0 字段名统一，§2.8）/ system_time / **location_candidates**（v1.0 字段名统一）
- 严格约束：
  - 节点 ID / 选项 ID 命名遵循 ADR-016 正则
  - state path 落入 ADR-016 五个命名空间；**`relationship.<state_path_slug>.*` 必须用 character entity 的 state_path_slug 字段值，不是 character_id**（v1.0 §2.6）
  - 使用 narrative_weight = core/minor 关系；context_only 仅作 anchor 不写出
  - dramatic_triggers 触发条件以 prescriptive 写法编织进对白
  - StateCondition 双形态互斥（参考 R2 修复后的 system prompt）
  - Option.text ≤ 25 汉字（参考 R3 修复后的硬约束）
  - 进入节点的 narrative beat 标签：参考 target_beats 顺序

## 3. /generator/prompts/scene/few_shot.py
def load_iron_oath_scene_few_shot() -> dict:
- 把整个《铁誓驿站》5 节点图作为单一示例对：
  - 输入：模拟 GraphContext + scene_setting (scene_anchor, target_beats, participating_npcs)
  - 输出：完整 DialogueGraph JSON
- 起步只一个 few-shot；过拟合再补

## 4. /generator/scene_strategies.py（v1.0 修订；critique 4.9 — skeleton edges 约束 fill）
@dataclass
class SkeletonNode:
    """骨架节点：节点 ID + 类型 + 节拍标签 + 出场 character"""
    node_id: str
    type: Literal["dialogue", "end"]
    beat: str
    speaker_ref: str | None
    expected_branch_count: int  # entry/中间节点的 option 数量预估

@dataclass
class GraphSkeleton:
    """整图骨架：节点 + 边连接（无具体 narration / option text）"""
    nodes: list[SkeletonNode]
    edges: list[tuple[str, str]]  # (from_node_id, to_node_id) 期望连接
    entry_node_id: str
    end_node_ids: list[str]

    def get_allowed_targets(self, node_id: str) -> list[str]:
        """返回该节点在 skeleton 中应连出的目标 node_id 集合"""
        return [to_id for from_id, to_id in self.edges if from_id == node_id]

def generate_skeleton(
    *, scene_setting: SceneSetting, target_beats: list[str], participating_npcs: list[dict],
    provider: LLMProvider,
) -> SkeletonResult:
    """
    第 1 阶段：用 LLM 生成图骨架（无具体 text）
    返回：GraphSkeleton + raw_text + cost
    """

def fill_skeleton(
    *, skeleton: GraphSkeleton, scene_context: dict, provider: LLMProvider,
) -> FillResult:
    """
    第 2 阶段：按节点顺序生成每个节点的 narration + options
    每个节点调一次 generate_node（复用阶段 1 实现）
    **v1.0 修订（critique 4.9）**：每个节点的 NodeRequirement 注入 allowed_targets =
        skeleton.get_allowed_targets(node_id)；generate_node prompt 必须明示
        "本节点 option.target_node_id 必须在 allowed_targets 列表内"；
        后处理拒收 LLM 生成的 skeleton 外 target_node_id（视为 schema_invalid 触发回喂）
    返回：DialogueGraph 完整 JSON + per-node attempt records + total_cost
    """

def generate_scene_skeleton_first(
    *, scene_setting, target_beats, participating_npcs, provider, max_retries: int = 2,
) -> SceneGenerationResult:
    """对外主函数 = generate_skeleton + fill_skeleton 串联"""

## 5. /generator/generate_node.py 扩展（v1.0 新增；critique 4.9）
- NodeRequirement dataclass 加字段：`allowed_targets: list[str] | None = None`（默认 None 时不约束，向后兼容阶段 1 节点级调用）
- generate_node 函数签名加可选参数：当 allowed_targets 非 None 时，prompt context 注入"本节点 option.target_node_id 限于：{list}"硬约束
- 后处理：响应解析后检查 option.target_node_id 是否在 allowed_targets 内；不在 → 标记为 schema_invalid，触发回喂重试

## 6. SceneGenerationResult dataclass
@dataclass
class SceneGenerationResult:
    success: bool
    graph: dict | None
    skeleton: GraphSkeleton | None
    failure_reason: str | None  # "skeleton_invalid" / "fill_node_invalid" / "fill_target_out_of_skeleton" / "budget_exceeded" / "provider_error"
    skeleton_attempts: list[AttemptRecord]
    fill_attempts: dict[str, list[AttemptRecord]]  # node_id → attempt list
    total_cost_usd: float

## 7. /pyproject.toml 修改（v1.0 新增；critique 4.6）
- packages 列表追加 `generator.prompts.scene`（确保 wheel 含本子包）
- package-data 暂不动（T-2.9 加 markdown 时再扩，避免本任务越界）

## 8. 测试 /generator/tests/test_scene_strategies.py + test_generate_node_allowed_targets.py
- 用 FakeProvider 注入：
  - 第 1 阶段返回合法 skeleton → success
  - 第 1 阶段 3 次失败 → success=False, "skeleton_invalid"
  - 第 2 阶段某个节点 3 次失败 → success=False, "fill_node_invalid"
  - **第 2 阶段 LLM 生成 skeleton 外 target_node_id**（v1.0 新增；critique 4.9）→ 第一次拒收 + 回喂；如三次都越界 → success=False, "fill_target_out_of_skeleton"
  - 各节点输入 prompt 正确含 GraphContext 扩展信息（character_features / dramatic_triggers / active_clocks / system_time / narrative_weight / location_candidates）
- /generator/tests/test_generate_node_allowed_targets.py：测 NodeRequirement.allowed_targets 字段在 None / 非空 两种情况下 generate_node 行为差异

# 不要做的事
- 不要实现 generate_scene 主函数（T-2.6）——本任务仅 strategies 和 prompt
- 不要在此任务里跑真实 Gemini API
- 不要提前实现 graph 视图（T-2.8）
- 不要硬编码模型 ID / 温度参数
- 不要扩 /generator/context_assembler.py（T-2.6 范围；本任务仅扩 NodeRequirement）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 模块结构 + 主函数签名
- prompt 模板节选（中文）
- pyproject.toml diff（packages 加 `generator.prompts.scene`）
- 测试输出（pytest -v；含 allowed_targets 越界拒收测试）
- commit message: `feat(generator): scene-level prompts + skeleton-first strategy with allowed_targets (T-2.5)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.5_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.6 ｜ generate_scene 主函数（依赖 T-2.5 + T-2.4）｜ [A-execute]

```text
你的任务是实现阶段 2 核心目标函数 generate_scene()——这是阶段 2 的主交付物。

# 任务类型：[A-execute]
- 写主函数 + 集成；不动 schema / ADR / SCHEMA_v0*.md
- 完成后 commit + push 即可

# 前置硬依赖（v1.0 修订；critique 3.4）
- T-2.5（scene_strategies）已 commit + merge
- **T-2.4（dialogue_validator）已 commit + merge**（v1.0 修订；本任务整合 validate_graph_mechanical 进主流程）
- T-2.2（schema 落地）已 commit + merge

# 模块边界（硬性）
允许修改 / 新建：
  - /generator/generate_scene.py（新建）
  - /generator/context_assembler.py（扩展：场景级 SceneGraphContext）
  - /generator/tests/
允许只读导入：/validator/、/generator/models/、/generator/llm_provider.py、/generator/budget.py、/generator/scene_strategies.py、/generator/generate_node.py
严禁修改：/schema/、/state/、/state/ontology/、/engine/、/validator/、/content/、/docs/、其他 generator 子模块

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-011/012/013/016/017/018/019
- /docs/STAGE_2_TASKS.md §2.8（一致性细节 — active_clocks / location_candidates / primary_location_ref）
- /docs/SCHEMA_v0.3.md
- /generator/generate_node.py（阶段 1 节点级实现 + T-2.5 加的 allowed_targets 字段；本任务复用）
- /generator/scene_strategies.py（T-2.5 落地）
- /validator/dialogue_validator.py（T-2.4 落地的 validate_graph_mechanical；本任务整合）
- /content/test_scene_v0/scene.json（gold standard）

# 待落地点

## 1. /generator/generate_scene.py 主函数

def generate_scene(
    *,
    scene_setting: SceneSetting,             # scene_anchor / target_beats / Chapter ref
    target_beats: list[str],                 # 节拍序列
    participating_npcs: list[str],           # 角色 ID list
    ontology: dict,                          # 完整本体（character / location / clocks / system_time）
    provider: LLMProvider,
    max_retries: int = 2,
) -> SceneGenerationResult

@dataclass
class SceneSetting:
    scene_anchor: str
    chapter_ref: str | None
    primary_location_ref: str               # v1.0 字段名（不再是 location_ref）
    expected_node_count_min: int   # 默认 5
    expected_node_count_max: int   # 默认 15

# 流程：
1. budget.check_and_charge(预估成本)（按 npc 数 × beats 数 × 单 node 成本估算）
2. 装配 SceneGraphContext（含 character_features / dramatic_triggers / relations[narrative_weight=core,minor] / active_clocks / system_time / Chapter/Act 上下文 / location_candidates）
3. 调 scene_strategies.generate_scene_skeleton_first(...)
4. 整合为完整 DialogueGraph JSON
5. 跑 schema 校验（生成的 graph 通过 dialogue_graph.schema.json v0.1.1）
6. **跑机械预检 validator.validate_graph_mechanical（T-2.4 落地）**——v1.0 关键依赖（critique 3.4）
7. 任一阶段失败 → 失败回喂 + 重试（最多 max_retries 次）
8. 全失败 → 返回 success=False
9. 不抛异常给调用方

## 2. /generator/context_assembler.py 扩展（v1.0 修订；§2.8 一致性）
@dataclass
class SceneGraphContext:
    """场景级 context（与节点级 GraphContext 字段集合并）"""
    scene_anchor: str
    chapter_ref: str | None
    location_candidates: list[dict]         # v1.0 修订（不再是 location_card：dict）
    primary_location_ref: str | None        # v1.0 新增：场景主地点 ID（如需）
    participating_characters: list[dict]   # 含 character_features / dramatic_triggers / relations / state_path_slug
    relations_matrix: list[dict]           # narrative_weight 过滤后的关系（core + minor 才入）
    active_clocks: list[dict]              # v1.0 字段名（不再是 faction_clocks；含 world / faction / environmental 三类）
    system_time: dict                      # {scene_count, long_rest_count}
    target_beats: list[str]

def assemble_scene_context_block(scene_ctx: SceneGraphContext, scene_setting: SceneSetting) -> str

## 3. budget 估算
def estimate_scene_cost(*, npc_count, beat_count, expected_node_count) -> float
- 粗估：1 次 skeleton 调用 + N 次 fill_node 调用（N ≈ expected_node_count）
- 单调用 cost 沿用 GeminiProvider.estimate_cost
- 单次场景上限：建议默认 $1.50（场景级单次硬卡比节点 $0.50 高 3 倍）；通过 budget.PER_CALL_BUDGET_USD 配置

## 4. 测试 /generator/tests/test_generate_scene.py
- FakeProvider 注入；不调真实 API
- scenarios:
  1. 第一次 skeleton + N 次 fill 全合法 → success
  2. skeleton 第一次失败、第二次合法 → success
  3. fill 某节点 3 次全失败 → success=False, "fill_node_invalid", 列哪个 node_id
  4. budget 触发 → success=False, "budget_exceeded"
  5. **validator 机械预检（T-2.4）发现 issue → 回喂 + 重试**（v1.0 关键测试；critique 3.4）
  6. SceneGraphContext 注入正确（**字段全 present**：active_clocks / location_candidates / state_path_slug 等）

# 不要做的事
- 不要在本任务里跑真实 API（那是 T-2.12 实证 batch run）
- 不要扩展 schema
- 不要做 graph 视图（T-2.8）
- 不要做 AI 判官（T-2.9）
- 不要做实验 CLI（T-2.8）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 主函数签名 + 流程图（文字描述）
- SceneGraphContext 完整字段（**v1.0 字段名校对**：active_clocks / location_candidates / primary_location_ref）
- 测试输出（6 scenarios 全过 + 含 validator 机械预检集成测试）
- commit message: `feat(generator): generate_scene() main function with skeleton-first + mechanical validation (T-2.6)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.6_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.7 ｜ validator 扩展 2A 拓扑 + 2B 抽样验证 + 有界符号执行｜ [A-execute]

```text
你的任务是按 ADR-021 落地 ADR-009 第二层校验——拆 2A 纯拓扑（**仅结构 + condition 引用形态合法性**）+ 2B 抽样验证（N=100 路径）+ 有界符号执行；2A / 2B 完成标志**双报**。

# 任务类型：[A-execute]
- 改 validator + 测试；不动 schema / ADR / SCHEMA_v0*.md
- 完成后 commit + push 即可

# 模块边界（硬性；v1.0 修订）
允许修改 / 新建：
  - /validator/graph_validation.py（**新建**；2A 拓扑；**包装现有 graph_check.py**——v1.0 §2.7 / Q7）
  - /validator/sampling.py（新建；2B 抽样 + 有界符号执行）
  - /validator/__init__.py（导出新模块；保留 graph_check 现有导出）
  - /validator/tests/
严禁修改：/schema/、/state/、/state/ontology/、/engine/、/generator/、/content/、/docs/
**严禁删除或重写 /validator/graph_check.py**（保留向后兼容；v1.0 §2.7）

# 必读
- /CLAUDE.md
- /docs/DECISIONS.md ADR-009 / ADR-021 / ADR-016 / ADR-017
- /docs/STAGE_2_TASKS.md §2.7（validator 模块命名 — graph_validation 包装 graph_check）+ §2.8（effect_op vs StateEffect.op 映射）+ ADR-021 决策核心（2A 范围 + 双报完成标志）
- /docs/SCHEMA_v0.3.md state path 命名空间
- /validator/graph_check.py（**现有；本任务包装它而非替代**）
- /validator/dialogue_validator.py（T-2.4 落地的机械预检；本任务在其上叠加）
- /content/test_scene_v0/scene.json（gold standard）

# 待落地点

## 1. /validator/graph_validation.py 新建（v1.0 修订：包装 graph_check + 2A 拓扑；§2.7）

# 包装层
from validator.graph_check import (...)  # 复用现有函数；保留向后兼容

# 2A 拓扑新增
def validate_graph_topology(graph: dict) -> TopologyResult:
    """
    返回拓扑检查结果。
    **v1.0 修订（critique 4.7 / Q5）**：仅检查结构拓扑 + condition 引用形态合法性
    （path 命名空间 / op 枚举 / 字段结构）；**不检查 condition satisfiability**
    （那归 2B sampling）
    """

@dataclass
class TopologyIssue:
    severity: Literal["error", "warning"]
    code: str  # "PATH_NOT_REACHABLE" / "DEAD_END_NODE" / "NEVER_REACHED" / "CONDITION_FORM_INVALID"
    node_id: str | None
    option_id: str | None
    message: str

@dataclass
class TopologyResult:
    issues: list[TopologyIssue]
    @property
    def has_error(self) -> bool: ...
    
    # 子结果（便于实验报告分项）
    unreachable_nodes: list[str]
    deadlock_nodes: list[str]
    convergence_groups: list[list[str]]  # 多路径汇合的节点群
    condition_form_issues: list[tuple[str, str]]  # (node_id, option_id) — 仅形态非法

## 2. 4 类拓扑检查（v1.0 修订；critique 4.7 / Q5 — 2A 范围降级）
- A1 NEVER_REACHED：从 entry_node_id 起 BFS，所有 option（无 condition 或 condition=null）都尝试，不可达 → error
- A2 DEAD_END_NODE：非 end 节点入度可达，但 option 集合中**无任何 condition=null option**（启发式定义；condition 满足性判断归 2B）→ error
- A3 CONDITION_FORM_INVALID（**v1.0 修订**：从 CONDITION_NEVER_SATISFIED 改为 CONDITION_FORM_INVALID）：option.condition 字段形态不合法（path 命名空间错 / op 枚举错 / 叶 vs 复合混用）→ error。**condition satisfiability 不在 2A 内**——见 2B
- A4 CONVERGENCE：识别多路径汇合节点（入度 > 1 且非 entry）→ warning（不算 issue，作为信息）

## 3. 同时活跃 clocks 数检查（v1.0 新增；critique §6 + ADR-017 D9）
- validate_graph_topology 返回 TopologyResult.warnings 含一项：若 ontology.clocks 当前活跃数 > 10（按 ticks_filled > 0 或 advance_rule 命中判定），出 warning "ACTIVE_CLOCKS_OVER_SOFT_LIMIT"
- 不阻塞通过；T-2.7 后续实测倒推真实上限

## 4. /validator/sampling.py（2B 抽样验证 + 有界符号执行）

def validate_graph_sampling(
    graph: dict, *,
    initial_state: dict | None = None,
    sample_count: int = 100,
    max_path_length: int = 50,
) -> SamplingResult:
    """
    从 entry 出发随机选 option 跑 N=100 路径，记录是否到达 end。
    **v1.0 修订（critique §10 weakness 3）**：N=100 是经验阈值起步，不暗示充分证明
    """

@dataclass
class SamplingResult:
    sample_count: int
    reached_end_count: int
    deadlock_count: int          # 中途无可选 option（非 end 节点）
    avg_path_length: float
    end_distribution: dict[str, int]  # end_node_id → 命中次数
    failure_examples: list[FailedSample]  # 不到 end 的样本，给作者排查
    condition_unsatisfiable_examples: list[tuple[str, str]]  # 抽样过程发现的 condition 不可满足 (node_id, option_id)

@dataclass
class FailedSample:
    path: list[str]              # node_id 列表
    state_at_failure: dict
    reason: str

def validate_graph_bounded_symbolic(
    graph: dict, *,
    state_var_domains: dict[str, list],  # 状态变量定义域（由作者声明 / 从本体推导）
    bound: int = 10,                      # 有界符号执行的 state 组合上限
) -> SymbolicResult:
    """
    在 state_var_domains 内枚举 state 组合，对每组组合检查 graph 是否仍有 entry → end 路径。
    """

@dataclass
class SymbolicResult:
    explored_states: int
    states_without_path_to_end: list[dict]  # 反例

## 5. 命名空间感知 + effect_op 映射（v1.0 修订；§2.8 / critique §9）
- state path 命名空间从 ADR-016 解析：world.* / faction.<id>.* / relationship.<state_path_slug>.* / flag.* / player.*
- effect 应用器：`tick_effects.effect_op`（ADR-017）等价于现有 `StateEffect.op`（set / inc / dec / add / remove）；**用统一映射函数处理两者**——不写两套语义代码

## 6. 测试 /validator/tests/test_graph_validation.py + test_sampling.py
- 拓扑 4 类各正反例
- **graph_check 现有测试不破**（v1.0 §2.7 关键回归）
- 抽样：在《铁誓驿站》上 N=100 应 100% reach end（gold standard 全路径都通）
- 有界符号执行：构造一个 state 变量小定义域的人造图（≤ 10 状态组合），验证能枚举所有
- 反例：构造一个有死锁的图，2A 报 DEAD_END_NODE，2B 抽样命中失败样本
- **active clocks 数 > 10 触发 warning**（v1.0 新增）
- effect_op 映射统一性测试（v1.0 新增）

## 7. 完成标志拆双报（v1.0 新增；critique 4.7 / Q5）

T-2.7 完成报告必须分别给出：
- **(a) 2A 纯拓扑 pass**：在《铁誓驿站》gold standard 上 0 error，可有 0~1 个 CONVERGENCE warning + 可能的 ACTIVE_CLOCKS_OVER_SOFT_LIMIT warning
- **(b) condition-aware（2B 抽样 + 有界符号执行）pass**：抽样 N=100 全 reach end + 0 condition_unsatisfiable_examples + 有界符号执行 0 反例

不混淆为 "2A pass" 单一指标——避免把启发式包装成 condition-aware "已完成"。

# 不要做的事
- 不要把 LLM 判官混进 validator（T-2.9 范围）
- 不要做 graph 视图渲染（T-2.8）
- 不要把状态变量定义域硬编码——由调用者传入（state_var_domains）；阶段 2 起步不强制定义域
- 不要尝试做"严格证明"——按 ADR-021 完成标志措辞 = "抽样 + 有界符号执行下未发现反例"
- **不要在 2A 内做 condition satisfiability**（v1.0 修订；critique 4.7 / Q5）——那归 2B sampling
- **不要删除或重写 /validator/graph_check.py**（v1.0 §2.7）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 模块结构 + 主函数签名（含 graph_validation.py 包装 graph_check.py 的导入关系）
- **双报**（v1.0 新增）：(a) 2A 纯拓扑在《铁誓驿站》上的实测；(b) 2B 抽样 + 有界符号执行在《铁誓驿站》上的实测
- 测试输出（含 graph_check 现有测试不破 + 新增测试全过）
- commit message: `feat(validator): graph topology (wraps graph_check) + sampling + bounded symbolic (ADR-021) (T-2.7)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 双报数据（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.7_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.8 ｜ scene experiment + review CLI 扩展（含图视图 + AI judge runner）｜ [A-execute]

```text
你的任务是把阶段 1 的 experiment / review_cli / metrics 工具链扩展到场景级，加入 U-GPT-7 强建议的图视图（mermaid / dot / ASCII 三选一），**并新增 scene_ai_judge runner**（v1.0 修订；critique 4.8 — 否则 T-2.12 / AI_JUDGE_REPORT.md 无人负责生成）。

# 任务类型：[A-execute]
# 前置硬依赖（v1.0 修订；critique 3.4）
- T-2.6 已 commit + merge
- **T-2.4（dialogue_validator）已 commit + merge**（scene_review CLI 展示机械预检 summary）
- **T-2.7（graph_validation + sampling）已 commit + merge**（scene_review CLI 展示拓扑 + 抽样 summary）

# 模块边界（硬性；v1.0 修订）
允许修改 / 新建：
  - /generator/scene_experiment.py（新建）
  - /generator/scene_review_cli.py（新建）
  - /generator/scene_metrics.py（新建）
  - /generator/graph_view.py（新建；mermaid / dot / ASCII 渲染）
  - **/generator/scene_ai_judge.py**（**v1.0 新增**；critique 4.8 — AI 判官 runner）
  - /generator/tests/
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、/docs/、其他 generator 子模块、/pyproject.toml（T-2.5 / T-2.9 范围）

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /generator/experiment.py + review_cli.py + metrics.py（阶段 1 节点级；本任务移植格式）
- /generator/visual_experiment.py + visual_review_cli.py + visual_metrics.py（阶段 1.5 视觉级；移植 review log 结构）
- /docs/DECISIONS.md ADR-009 / ADR-020 / ADR-021
- /docs/STAGE_2_TASKS.md §2.8（CLI 命令统一为 `python -m generator.scene_review_cli`）+ §3 ADR-020 完成标志（gross pass + 接受率双报）+ ADR-021 双报
- /docs/reviews/master_plan/2026-04-30_synthesis.md U-GPT-7 强建议
- /docs/HANDOFF_STAGE_1_TO_2.md "AI 判官 prompt 视觉化"段落
- /validator/dialogue_validator.py（T-2.4 落地）
- /validator/graph_validation.py + sampling.py（T-2.7 落地）

# 待落地点

## 1. /generator/scene_experiment.py
CLI: `python -m generator.scene_experiment --batch-name <name> --count <N>`
- 跑 N=15 次 generate_scene（默认 N=15，与 ADR-020 baseline 协议一致）
- 每次的 SceneSetting / target_beats / participating_npcs 从内置 fixture 集合采样
- fixture 起步以《铁誓驿站》为参考，作者后续 L3 可加场景类型
- 输出：/generator/experiments/<timestamp>_<batch_name>/
  - scene_results.jsonl（每行一个 SceneGenerationResult 序列化）
  - scene_summary.txt（schema_pass_rate / topology_pass_rate / sampling_reach_rate / mean_cost / failure_distribution / **gross_pass_rate**）
  - graph_views/（每个 success scene 一份 mermaid + dot + ASCII 三视图）
- 启动时打印当日剩余预算
- 任何一次 BudgetExceeded → 立即停止落地已完成

## 2. /generator/scene_review_cli.py（v1.0 修订；§2.8）
CLI: **`python -m generator.scene_review_cli --batch-dir <path>`**（v1.0 修订：与 T-2.12 命令统一；不再用 `python -m generator.scene_review`）
- 终端 UI 依次展示 success=True 的 scene
- 每个 scene 显示：
  - SceneSetting 摘要
  - mermaid / ASCII 图视图（默认 ASCII；--web 模式开 mermaid 浏览器）
  - 节点列表 + 关键 narration / option 文本
  - **validator 三类 summary**（v1.0 关键依赖 critique 3.4 / 4.8）：
    - 机械预检（T-2.4）issue 摘要
    - 拓扑（T-2.7 2A）双报：纯拓扑 pass + condition 形态合法性
    - 抽样（T-2.7 2B）reach_end_count / deadlock_count
- 操作：[A]ccept / [R]eject / [S]kip
- Reject 时输入一行原因
- 输出：scene_review_log.jsonl
  - 每行：{iter_id, scene_id, schema_pass, topology_pass, sampling_pass, mechanical_pass, accepted, reason, reviewed_at}
- 可中断 / 可继续
- **加 `--help` smoke test**（v1.0 §2.8）：`python -m generator.scene_review_cli --help` 必须返回 0 + 列 CLI flag

## 3. /generator/scene_metrics.py
def compute_scene_metrics(batch_dir: Path) -> dict
返回：
- total_attempts / schema_pass_rate / topology_pass_rate / sampling_reach_rate / mechanical_pass_rate
- **gross_pass_rate**（v1.0 新增；ADR-020 修订）：通过机械预检的场景数 / 总尝试场景数
- mean_cost_per_attempt / total_cost
- failure_reason_distribution
- (若 review_log 存在) acceptance_rate（按 ADR-020 分母分子）+ reject_reason_top_5

CLI: `python -m generator.scene_metrics --batch-dir <path>`

## 4. /generator/graph_view.py
def render_mermaid(graph: dict) -> str
def render_dot(graph: dict) -> str
def render_ascii(graph: dict, max_width: int = 80) -> str
- 节点用 ID 标注 + type 颜色（end 节点不同色）
- option 用 condition / unavailable_behavior 标注
- mermaid 兼容 GitHub 渲染；dot 兼容 graphviz；ASCII 用 box-drawing characters

## 5. /generator/scene_ai_judge.py（v1.0 新增；critique 4.8）

def run_scene_ai_judge(
    *, batch_dir: Path, provider: LLMProvider, prompt_template_path: Path,
) -> AIJudgeReport:
    """
    对 batch_dir 中所有 success=True 的 scene 跑 AI 判官 prompt（T-2.9 落地的 REVIEW_PROMPT_AI_JUDGE_SCENE.md）
    pass 1 lenient + pass 2 strict 双 pass
    输出 AI_JUDGE_REPORT.md 到 batch_dir
    """

@dataclass
class AIJudgeReport:
    pass1_lenient_scores: dict[str, dict]  # scene_id → 维度 → 分数
    pass2_strict_scores: dict[str, dict]
    weakest_dimensions: list[tuple[str, float]]  # 维度名 → 平均分（最弱前 5）
    advisory_recommendation: dict[str, Literal["accept", "reject", "marginal"]]  # scene_id → 判官推荐（仅 advisory，作者 [A]/[R] 才是接受率分子）

CLI: `python -m generator.scene_ai_judge --batch-dir <path>`
- 用 GeminiProvider（实际调真 API；可用 FakeProvider 在测试中）
- T-2.12 实证 batch run 时由作者手动调本 CLI 生成 AI_JUDGE_REPORT.md（不在 generate_scene 主流程内自动跑，避免成本失控）

## 6. 测试 /generator/tests/test_scene_experiment_smoke.py + test_graph_view.py + test_scene_ai_judge_smoke.py
- FakeProvider 跑 scene experiment，验证 jsonl 格式 + summary
- review_cli 非交互（mock stdin） + `--help` smoke test
- 三种视图渲染《铁誓驿站》gold standard 不抛异常
- **scene_ai_judge 用 FakeProvider 跑一次完整 pass1+pass2 流程**（v1.0 新增；critique 4.8）→ 验证 AI_JUDGE_REPORT.md 格式

# 不要做的事
- 不要做 Web UI（CLI 即可）
- 不要让 experiment 默认烧很多钱（默认 N=15，约 $7–$15；v1.0 成本口径）
- 不要在 scene_ai_judge 里用真 API 跑测试（用 FakeProvider）
- 不要把 AI 判官打分作为接受率分子（按 ADR-020 §6，分子是作者标 [A]ccept；判官仅 advisory）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- CLI 用法说明（含 `python -m generator.scene_review_cli --help` 输出 + scene_ai_judge CLI 输出）
- 一次 dry-run（FakeProvider）输出（experiment + ai_judge）
- 三种视图样例（《铁誓驿站》各一份）
- commit message: `feat(generator): scene experiment + review CLI + graph views + AI judge runner (T-2.8)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.8_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.9 ｜ baseline 协议正式定义 + 场景级 AI 判官 prompt v1 ｜ [B-author-gate]

```text
你的任务是把 ADR-020 的 baseline 协议落地为正式协议文档 + 场景级 AI 判官 prompt v1，**并同步 pyproject.toml package-data**（v1.0 修订；critique 4.6）。

# 任务类型：[B-author-gate]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 协议口径间接影响完成标志判定 + 阶段 2 验收
- A 阶段：按 ABC 闭环 commit + push + 开 PR；**v0.3 起统一 commit + 开 PR**
- B/C 阶段：作者会更仔细审 PR diff（协议口径决定 ROADMAP 完成标志措辞）；过 ABC + L2 验收后 merge

# 模块边界（硬性；v1.0 修订）
允许修改 / 新建：
  - /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md（新建）
  - /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md（新建）
  - **/pyproject.toml**（**v1.0 新增；critique 4.6** — package-data 追加 `"generator.prompts.scene" = ["*.md"]`，否则未来 wheel/开源剥离会漏 scene 子包的 markdown 资源）
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、/docs/、其他 generator 子模块

# 必读
- /CLAUDE.md
- /docs/DECISIONS.md ADR-020
- /docs/STAGE_2_TASKS.md §3 ADR-020 决策核心（v1.0 修订：报告同时给 gross pass + 人工接受率；成本口径统一）
- /generator/prompts/REVIEW_PROMPT_AI_JUDGE.md（阶段 1 节点级 21 维 prompt；本任务移植扩展）
- /generator/prompts/visual/REVIEW_PROMPT_AI_JUDGE_VISUAL.md（阶段 1.5 视觉级 12 维 prompt；移植格式参考）
- /docs/STAGE_1_ACCEPTANCE.md §2.4（21 维度严格模式下最弱三项；理解维度可塑性）
- /pyproject.toml（确认 packages 已含 `generator.prompts.scene`，由 T-2.5 加；本任务在 package-data 区追加）

# 待落地点

## 1. /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md
按 ADR-020 全集落字（前面已锁定，本任务把 ADR 决策落成可执行文档）：

§1 协议范围
§2 样本数：N=15 场景
§3 重试规则：max_retries=2（沿用 ADR-013）
§4 AI 判官权重表（节点级 21 维 + 场景级 6-10 维），具体维度由 §6 落地
§5 机械失败口径（option 长度 / path 前缀 / bond ID 白名单（**state_path_slug 反查**） / target_node_id 闭合 / unavailable_behavior 枚举 / state path 命名空间 / StateCondition 形态互斥）
§6 接受率分子分母明示（分母 = 机械预检通过 + 进入 review_log；分子 = 作者标 [A]ccept；非 AI 判官打分）
§7 阶段 2 完成判定：N=15 场景接受率 ≥ 70%
§8 与阶段 1 R6（AI 判官替代人工）的关系：阶段 1 接受 AI 判官；阶段 2 仍以作者最终签字为准；AI 判官提供辅助 advisory 分
§9 **报告口径**（v1.0 新增；critique §10 weakness 2）：每次 batch 必须同时报告 gross pass rate（通过机械预检的场景数 / 总尝试场景数）+ 人工接受率（作者 [A] / 进入 review_log 数）
§10 **成本估算口径**（v1.0 新增；critique 5.2）：每场景 ~$0.5–$1.0；N=15 总 $7–$15；N=20 总 $10–$20

## 2. /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md
场景级 AI 判官 prompt（中文）：

§A 输入：完整 DialogueGraph JSON + SceneSetting + 本体 character_features / dramatic_triggers / clocks / system_time
§B 评估维度：
- 节点级（21 维 × N 节点；维度沿用阶段 1 REVIEW_PROMPT_AI_JUDGE.md 的 A1-D5）
- 场景级新增 6-10 维：
  - S1 图拓扑健康：是否所有节点可达 / 是否有死锁
  - S2 节奏：beat 序列是否符合 target_beats（无跳跃 / 无重复）
  - S3 角色弧线：每个 NPC 在场景内的状态变化是否有意义（不是"工具人"）
  - S4 决策意义：每条 option 的后果是否真有差异（不是"换皮"）
  - S5 收束：所有 ending 是否对场景核心冲突给出 closure
  - S6 长度合理：节点数在 SceneSetting expected_node_count_min/max 范围内
  - S7 context 一致性：dramatic_triggers 是否被恰当编织进对白（不是"挂在台词外的描述"）
  - S8 关系层一致性：narrative_weight=core 的关系是否显性体现，context_only 是否未出现在玩家可见对白
  - S9 时钟一致性：进入场景时 active_clocks 状态是否被反映在叙事
  - S10 ID 命名规范：node_id / option_id / state path 是否合 schema 正则；relationship.<state_path_slug> 是否落入本体花名册
§C 输出格式：维度打分 (0-2 三档) + 总分 + accept/reject 决策
§D pass 1 lenient + pass 2 strict 双 pass 模式（沿用阶段 1）

## 3. /pyproject.toml 修改（v1.0 新增；critique 4.6）
- 在 package-data（或 [tool.setuptools.package-data] 段）追加：`"generator.prompts.scene" = ["*.md"]`
- 确保 setuptools 把 REVIEW_PROMPT_AI_JUDGE_SCENE.md 打进 wheel
- 不动 packages 列表（T-2.5 已加 `generator.prompts.scene`）

# 不要做的事
- 不要把判官 prompt 实际跑起来（那是 T-2.12 实证 batch run + T-2.8 scene_ai_judge runner 范围）
- 不要把判官打分作为接受率分子（按 ADR-020 §6，分子是作者标 [A]ccept）
- 不要修改阶段 1 的 REVIEW_PROMPT_AI_JUDGE.md（它是节点级，仍有效）
- 不要在本任务里写 scene_ai_judge.py runner（T-2.8 范围）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 两份新文档字数 + 章节
- 各维度首版描述
- pyproject.toml diff（package-data 加 `"generator.prompts.scene" = ["*.md"]`）
- A 阶段产出：PR URL + commit hash + 测试输出（A 阶段直接 commit + push + 开 PR；不再等作者授权）
- commit message：`docs: Stage 2 baseline protocol + scene-level AI judge prompt v1 (T-2.9)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.9_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
```

---

### T-2.10 ｜ sidecar OPEN_SOURCE_CARVE_OUT_INDEX.md v0.1 ｜ [A-execute]

```text
你的任务是按 C5 强建议建立开源剥离边界清单首版 sidecar，记录阶段 2 起手时已知的"私有依赖"。

# 任务类型：[A-execute]
# 模块边界
允许新建：/docs/OPEN_SOURCE_CARVE_OUT_INDEX.md
严禁修改：其他任何文件

# 必读
- /CLAUDE.md
- /docs/ROADMAP.md 阶段 4
- /docs/STAGE_2_TASKS.md §2.1 D6（v1.0 修订：首版加 scene prompt 子包 + scene fixtures 标注）+ §4.2（C5 强建议）
- /docs/reviews/master_plan/2026-04-30_synthesis.md C5

# 待落地点

## /docs/OPEN_SOURCE_CARVE_OUT_INDEX.md
首版结构：

§1 用途
- 跟踪从 forgewright 仓库剥离开源框架时需要拆出 / 替换 / 文档化的内容
- 阶段 2 起维护，阶段 4 执行剥离

§2 三类边界
A. fixture / 角色 / 场景内容（作者本人项目；不能进开源框架默认）
   - /content/test_scene_v0/scene.json（《铁誓驿站》）
   - /state/ontology/waystation.json（vellin / corvan / aelwin）
   - /generator/prompts/few_shot.py 引用的内容
   - /generator/prompts/scene/few_shot.py 引用的内容（**v1.0 新增；D6 修订**）
   - /generator/prompts/scene/system.py 含《铁誓驿站》场景默认 prompt 时（**v1.0 新增；D6 修订** — 标记并由 T-2.5 落地后回填）
   - /generator/fixtures/scene/（如 T-2.12 加 scene fixture，**v1.0 新增**）
   
B. 资产版权（视觉资产）
   - /content/visuals/（mini probe 5 张 vellin 立绘 + 后续 batch 资产）
   - /content/visuals/_reference/（作者私有风格参考；已 .gitignore）
   - /generator/image_cost_log.jsonl + import_log.jsonl（runtime 产物）
   
C. provider 假设（默认 SDK / API key）
   - GeminiProvider 默认 model_id（gemini-3.1-pro-preview）—— 开源默认应给可替换
   - OpenAIImageProvider（gpt-image-1）—— 同上
   - .env / .env.example（API key）—— 已 .gitignore

§3 阶段 2 / 3 维护规则
- 每个新增的 schema fixture / 资产引用 / provider 假设落新一行到 §2 对应类
- L3 任务执行会话发现新边界时追加（[A-execute] 兼容 routine）

§4 v0.1 状态：起步清单（即上述 §2）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 文档章节
- **无单元测试**（v1.0 修订；critique 5.3 — 纯文档任务）；运行 markdown link sanity check 或 N/A：
  - 可选：用任意 markdown link checker（如 `markdown-link-check`）跑一次；无则报告 "not applicable"
- commit message: `docs: open source carve-out index v0.1 (C5) (T-2.10)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.10_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.11 ｜ cost_log 反向校准（R7）+ usage_metadata 接入 + record_id 串联 + 三态 refund ｜ [A-execute]

```text
你的任务是落地阶段 1 R7——cost_log 高估失败请求成本，接入 Gemini 实际 usage_metadata 反向更新，**并改 check_and_charge 返回稳定 record_id + 加三态 refund**（v1.0 修订；critique 4.10 / Q6 选 B）。

# 任务类型：[A-execute]
# 模块边界（v1.0 修订）
允许修改：
  - /generator/budget.py
  - /generator/providers/gemini.py
  - /generator/cost_log.py
  - **/generator/generate_node.py**（**v1.0 新增；critique 3.3 + 4.10** — 仅 reconcile/refund hook 接入；不动业务逻辑）
  - /generator/tests/
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、/docs/、其他 generator 子模块

# 必读
- /CLAUDE.md
- /docs/STAGE_1_ACCEPTANCE.md §4 R7 + §6 真实费用回顾
- /docs/DECISIONS.md ADR-012
- /docs/STAGE_2_TASKS.md §5 R7 行（v1.0 修订：record_id 串联 + 三态 refund；provider 异常分类作 R2.* follow-up）
- /generator/cost_log.py（当前实现，append-only）
- /generator/providers/gemini.py（StructuredResponse.input_tokens / output_tokens 已记录）
- /generator/budget.py（check_and_charge 当前返回 None；本任务改为返回 record_id）
- /memory/gemini_sdk_quirks.md（HttpOptions.timeout 单位 / response_schema 不接 additionalProperties；本任务不直接相关但要知道 SDK 坑）

# 待落地点

## 1. /generator/cost_log.py（v1.0 修订）
新增 update 操作（之前是 append-only）：
def update_record(record_id: str, *, actual_input_tokens: int, actual_output_tokens: int, actual_cost_usd: float) -> None
- 找到匹配 record_id 的记录（应该唯一；若找不到报错）
- 更新 input_tokens / output_tokens / cost_usd 为实际值
- 在记录里加 `reconciled: true` + `reconciled_at` 字段

新增 mark_refunded(record_id: str, *, reason: str) -> None：
- 标记记录 cost_usd=0 + status="refunded" + refund_reason=<reason>
- 用于失败前/连接失败的场景

新增 record 写入时返回稳定 record_id（如 timestamp + counter 哈希；保证全过程唯一）

## 2. /generator/budget.py（v1.0 关键修订；critique 4.10 / Q6 选 B）
- **check_and_charge 改返回稳定 record_id**（之前返回 None；v1.0 必做层）
  - 签名：`def check_and_charge(...) -> str`（返回 record_id）
- 新增 reconcile_after_call(record_id: str, *, actual_input_tokens: int, actual_output_tokens: int, actual_cost_usd: float) 在 generate_node 调用结束后调一次
  - 内部调 cost_log.update_record(record_id, ...)
- 新增 refund_estimated(record_id: str, *, reason: str) -> None
  - 反向 _release 已记的 estimated_cost
  - cost_log.mark_refunded(record_id, reason=reason)
- **失败分类**（v1.0 修订；Q6 选 B — 仅做核心三态 refund + record_id；详细分类作 R2.* follow-up）：
  - 三态 refund：
    - "pre_call_budget_fail"（不到 check_and_charge；无 record，不需 refund）
    - "request_not_sent"（连接失败 / pre-flight 校验失败 → refund 全额 estimated_cost）
    - "request_sent_failure"（请求已送出但响应失败 → 默认按 estimated_cost 计费保留；作 R2.* follow-up 决定是否细分）
  - **不做** GeminiProvider 差异化异常体系（critique 4.10 方案 A）——开 R2.1 follow-up 项交阶段 2 完成后或阶段 3 处理

## 3. /generator/providers/gemini.py
- StructuredResponse 字段已含 input_tokens / output_tokens
- 但需要把 SDK 返回的 usage_metadata 完整透传（含 cached / billable / reasoning 等子字段）
- 加 actual_cost_usd 字段（用 estimate_cost 计算实际）

## 4. /generator/generate_node.py 修改（v1.0 新增；critique 3.3）
- 仅在调用结束的 hook 位置加：
  - 成功：`budget.reconcile_after_call(record_id, actual_input_tokens=..., actual_output_tokens=..., actual_cost_usd=...)`
  - 失败（request_not_sent 类）：`budget.refund_estimated(record_id, reason="request_not_sent")`
  - 失败（request_sent_failure 类）：默认不 refund（按 estimated 计费）；记 log "request_sent_failure refund deferred to R2.1"
- check_and_charge 调用处接收返回的 record_id 并传递给上述 hooks
- 不动 generate_node 的业务逻辑（节点生成 / 重试 / schema 校验等不动）

## 5. 测试
- mock SDK usage_metadata 验证 reconcile 流程
- mock 失败场景验证 refund 三态流程：
  - pre_call_budget_fail → 没 record_id；不动 cost_log
  - request_not_sent → record_id refund 走全额
  - request_sent_failure → record_id 不 refund，记日志
- record_id 唯一性测试（多次 check_and_charge 不重复）

# 不要做的事
- 不要去 Google AI Studio 控制台对账（那是作者侧手工任务）
- 不要修改 ADR-012 预算上限
- 不要预防性给 OpenAIImageProvider 也加（那是阶段 1.5 范围；本任务仅 GeminiProvider）
- **不要做 GeminiProvider 差异化异常体系**（v1.0 修订；Q6 方案 A 不做）——作 R2.1 follow-up 项；本任务范围仅核心 record_id + 三态 refund
- 不要在本任务里改 generate_node 业务逻辑（仅 hook 接入）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- diff 摘要
- 测试输出（含三态 refund 测试）
- 一次 mock 端到端验证（成功 + 三种失败情况）
- **R2.1 follow-up 项标注**（v1.0 新增）：在 commit message 或 PR body 里点明 "provider 差异化异常分类作 R2.1 follow-up"
- commit message: `fix(generator): reconcile cost_log with actual usage_metadata + record_id + tri-state refund (R7) (T-2.11)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.11_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
- push 后报 commit hash
```

---

### T-2.12 ｜ 实证 batch run（N=15 场景）+ 接受率统计 ｜ [A-execute]

```text
你的任务是按 ADR-020 baseline 协议跑实证 N=15 场景 batch，作为阶段 2 验收的实测数据来源。**含 AI 判官 runner 调用**（v1.0 修订；critique 4.8）。

# 任务类型：[A-execute]
# 前置硬依赖
- T-2.4（机械预检器）已 commit + merge
- T-2.7（validator 2A + 2B）已 commit + merge
- T-2.8（scene experiment + review CLI + scene_ai_judge runner）已 commit + merge
- T-2.9（baseline 协议 + AI 判官 prompt）已 commit + merge + 作者授权
- 作者已设置 GEMINI_API_KEY

# 模块边界
允许修改 / 新建：
  - /generator/experiments/<batch_dir>/（运行产物）
  - /generator/fixtures/scene/（如需扩展场景 fixture 集合）
  - /generator/tests/（如需补 batch run 单元测试）
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、/docs/、其他 generator 子模块

# 必读
- /CLAUDE.md
- /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md
- /generator/scene_experiment.py + scene_review_cli.py + scene_metrics.py + **scene_ai_judge.py**（v1.0 新增依赖）
- /docs/STAGE_2_TASKS.md §3 ADR-020（成本口径 + 双报）+ ADR-021（双报）
- /docs/DECISIONS.md ADR-020 / ADR-021

# 待落地点

## 1. fixture 扩展（如需）
- 阶段 1.5 没有 fixture 完整生成；阶段 2 需要 N=15 个 SceneSetting + target_beats + participating_npcs 组合
- 起步：以《铁誓驿站》为模板生成 15 个变体（不同 NPC 组合 / target_beats 重排）
- 或作者预先提供 15 个真实 SceneSetting

## 2. 跑 batch
- 作者设置 GEMINI_API_KEY 后跑：
  `python -m generator.scene_experiment --batch-name baseline_005 --count 15`
- **预期成本**（v1.0 修订；critique 5.2）：每场景 ~$0.5–$1.0；总 $7–$15
- 跑完跑：`python -m generator.scene_review_cli --batch-dir <ts>_baseline_005`（v1.0 命令名修订；§2.8）
- 作者逐 scene [A]/[R]/[S]
- 跑：`python -m generator.scene_metrics --batch-dir <ts>_baseline_005`
- **跑 AI 判官 runner**（v1.0 新增；critique 4.8）：`python -m generator.scene_ai_judge --batch-dir <ts>_baseline_005` → 生成 AI_JUDGE_REPORT.md

## 3. 实测产物
- batch_dir/scene_results.jsonl
- batch_dir/scene_review_log.jsonl
- batch_dir/scene_summary.txt
- batch_dir/graph_views/（mermaid + dot + ASCII）
- **batch_dir/AI_JUDGE_REPORT.md**（v1.0 修订；由 T-2.8 的 scene_ai_judge runner 生成；pass 1 lenient + pass 2 strict 双重）

## 4. 中间产物报告（不在本任务 commit；T-2.13 验收报告引用）
- **gross pass rate + 接受率双报**（v1.0 修订；ADR-020 §9 / critique §10 weakness 2）
- schema_pass_rate / topology_pass_rate / sampling_reach_rate / mechanical_pass_rate
- failure_reason 分布
- mean_cost_per_scene + 总成本（与口径 $7–$15 对照）
- 与 ROADMAP 完成标志（≥ 70%）的对比

# 不要做的事
- 不要伪造数据
- 不要写阶段 2 验收报告（T-2.13 范围）
- 不要修改协议（如发现协议有问题报告作者，由 T-2.9 v0.2 修订）
- 不要把 AI 判官打分作为接受率分子（按 ADR-020 §6）

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- batch_dir 路径
- 关键指标（**gross pass + 接受率双报** / schema_pass / topology_pass / sampling_reach / 总成本）
- AI 判官报告路径 + pass1/pass2 关键维度摘要
- 任何异常（成本超预期 / 多次 BudgetExceeded / 等）
- commit message：`chore(generator): Stage 2 baseline_005 N=15 batch run with AI judge (T-2.12)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 实测数据摘要

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff（含实测数据 + AI 判官报告 + scene_review_log）；report 落 `/docs/reviews/<ISO_DATE>_T-2.12_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；如 B 阶段发现 batch run 数据异常（如 schema_pass < 70%），吃 B 报告决定回 T-2.5/T-2.6/T-2.9 修后重跑 batch；追加 commit 到原 PR
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；过关前 PR 一律不 merge
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
```

---

### T-2.13 ｜ 阶段 2 验收报告 ｜ [B-author-gate]

```text
你的任务是写阶段 2 验收报告，仅在 T-2.12 跑完且作者已完成 scene_review 后启动。

# 任务类型：[B-author-gate]（v0.3 治理修订后概念保留；实操按 ABC 闭环）
- 验收报告 = 修 L1 文档；CLAUDE.md 规则 9 例外
- A 阶段：按 ABC 闭环 commit + push + 开 PR；**v0.3 起统一 commit + 开 PR**
- B/C 阶段：作者会更仔细审 PR diff + 末段签字（验收性质）；过 ABC + L2 验收 + 作者签字后 merge

# 模块边界
允许新建：/docs/STAGE_2_ACCEPTANCE.md
允许修改：/docs/ROADMAP.md（**仅记录段；不动完成标志措辞** — v1.0 修订；详跨边界 X1）/ /docs/HANDOFF_STAGE_2_TO_3.md（新建）
严禁修改：其他任何文件 / 任何代码 / **不动 ROADMAP §阶段 2 完成标志措辞**（跨边界 X1，由作者另起 L1 修订会话）

# 必读
- /docs/STAGE_1_ACCEPTANCE.md / STAGE_1.5_ACCEPTANCE.md（参照格式）
- /docs/ROADMAP.md 阶段 2 完成标志（**v1.0 提醒**：当前文本可能含旧"证明"措辞；引用 ADR-021 实际口径，不引用 ROADMAP 旧文本）
- /docs/STAGE_2_TASKS.md §3 ADR-020 / ADR-021 决策核心（双报口径；成本口径）
- /docs/DECISIONS.md ADR-020 / ADR-021
- /generator/protocols/STAGE_2_BASELINE_PROTOCOL.md
- batch_dir 产物（T-2.12 产出，含 AI_JUDGE_REPORT.md）

# 待落地点

## /docs/STAGE_2_ACCEPTANCE.md 仿 STAGE_1.5_ACCEPTANCE 格式

§1 阶段 2 完成判定核对
- 表格：ROADMAP / ADR-020 / ADR-021 目标 vs 实测
- **完成标志按 ADR-021 实际口径**（v1.0 修订）："抽样验证 N=100 路径 + 有界符号执行下未发现反例"——不引用 ROADMAP 旧"证明"文本（ROADMAP 文本同步修订属跨边界 X1，由作者另起 L1 doc 修订会话；T-2.13 仅记录引用 ADR-021）
- 整体结论（通过 / 部分通过 / 未通过）

§2 baseline_005 实验数据
- N=15 实测
- **gross pass rate + 接受率双报**（v1.0 修订；ADR-020 §9）
- schema_pass_rate / topology_pass_rate / sampling_reach_rate / mechanical_pass_rate
- **2A 纯拓扑 / condition-aware（2B）双报**（v1.0 修订；ADR-021）
- AI 判官 pass 1 lenient + pass 2 strict 评分
- 各维度最弱三项

§3 工作量速览
- T-2.0 ~ T-2.13 commit 表格

§4 遗留问题（R2.*）
- 阶段 1 / 1.5 R 项归宿
- **新发现的阶段 2 R2.* 项**（v1.0 提醒）：T-2.11 已开 R2.1 follow-up（GeminiProvider 差异化异常体系 + 失败分类细化）；其他随实测发现追加

§5 阶段 3 启动前置条件
- C2 ADR-009 第三层（阶段 3 规划师范围）
- C6 内容依赖索引
- U-CL-1 阶段 3 完成标志加质量门槛
- U-CL-5 长对话一致性缓解 ADR / 任务
- U-GPT-7 审阅 UI 第一版含图视图

§6 真实费用回顾
- 与口径 $7–$15 对照（v1.0 ADR-020 §10）

§7 模块边界自检（grep 确认运行时 / schema / engine / validator 不依赖 generator）

§8 跨 LLM 评审实绩

§9 签字（作者填）

## /docs/HANDOFF_STAGE_2_TO_3.md 新建
仿 HANDOFF_STAGE_1_TO_2.md 格式
- 阶段 2 做了什么 + 别重建
- 阶段 3 启动条件
- 阶段 3 启动闸门候选清单（C2 / C6 / U-CL-1 / U-CL-5 / U-GPT-7）
- 阶段 3 规划师必读列表
- 注意：本文件仅是阶段 2 → 阶段 3 交接草稿；阶段 3 L2 规划师启动后由其自定 STAGE_3_TASKS_draft

## /docs/ROADMAP.md 更新记录段（v1.0 修订；仅记录，不动完成标志措辞）
- 新增 2026-XX-XX 一行：阶段 2 验收 [pass / partial pass]，schema 合格率 / 接受率 / 抽样 reach 率指标
- 标 ADR-016~021 立项
- 标阶段 2 实测费用
- **不动 ROADMAP §阶段 2 完成标志措辞**（v1.0 修订；跨边界 X1）——由作者另起 L1 doc 修订会话改"证明" → "抽样 + 有界符号执行下未发现反例"

# 不要做的事
- 不要伪造数据
- 不要替作者签字（签字行留空）
- 不要规划阶段 3（那是阶段 3 规划师）
- 不要修改 ADR-016~021（已签字立项）
- **不要改 ROADMAP §阶段 2 完成标志措辞**（v1.0 修订）——跨边界 X1，由作者另起 L1 doc 修订会话

# A 阶段完成标志（本会话范围；ABC 闭环见 §1.5 + 段末"B/C 阶段"段）
- 两份新文档 + ROADMAP diff（仅记录段）
- 关键指标（双报 + 双报）
- A 阶段产出：PR URL + commit hash（验收报告作者签字行预留空白；签字由作者在 ABC 闭环 + L2 验收后填写——签字与 PR merge 同期）
- commit message：`docs: Stage 2 acceptance report (T-2.13)`
- 末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
- A 阶段额外要求：开 PR（base=`main`，head=本 worktree 分支名）；A 阶段产出 = PR URL + commit hash + 测试输出（push + 开 PR 后即"本会话完成"）

# B / C 阶段（不在本会话范围；治理备忘 v0.3 §10）

- **B 阶段**：作者另起 **Codex 会话（GPT-5.5）**；用 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）作模板 review 本 PR diff；report 落 `/docs/reviews/<ISO_DATE>_T-2.13_<topic>_review.md`（v1.0 修订）
- **C 阶段**：作者另起 Claude Code 会话；吃 B 报告改代码 + **追加 commit 到原 PR**（不开新 PR）
- **L2 验收闭环**：A+B+C 全部完成 + L2 验收过关后作者 merge PR；**过关前 PR 一律不 merge**；打回时回 C 跑二轮（必要时回 B 重 review）
- 你（A 阶段）不需要等 B/C——push + 开 PR 后即"本会话完成"，后续作者推进
```

---

---

## 9. 跨任务一致性核对（v1.0 修订）

跨任务字段 / 命名 / 接口检查（含 GPT-5.5 critique §9 全部锚点）：

| 跨任务项 | v0.1.1 状态 | v1.0 状态 |
|---|---|---|
| **character_features / dramatic_triggers** | T-2.1 / T-2.2 / T-2.5 / T-2.6 名称一致；T-2.2 起步空 dramatic_triggers 缺示例 | 一致；**T-2.2 起步加 1-2 个 seed 示例**（如 vellin trigger，§2.1 D10 / critique §10 weakness 4） |
| **narrative_weight** | core/minor/context_only 跨 T-2.1/T-2.2/T-2.5 一致；relation 是 character 内嵌还是全局未定 | 一致；**relation 内嵌 character envelope，不引入全局关系表**（§2.5 / Q3） |
| **clock 字段** | id/scope/ticks_total/ticks_filled/advance_rule/tick_effects 基本一致；tick_effects.effect_op 与现有 StateEffect.op 命名不同 | 一致；**T-2.7 effect 应用器明示 effect_op 等价 StateEffect.op，用统一映射函数**（§2.8 / critique §9） |
| **state path 命名空间** | 最大不一致：`relationship.<character_id>` vs gold 的 `relationship.vellin` | **统一为 `relationship.<state_path_slug>.*`**；character entity 加 state_path_slug 字段（§2.6 / Q1） |
| **generation_trace.slot_assignments** | T-2.1/T-2.2/T-2.6 大方向一致；schema_version 兼容未定 | 一致；**走 optional + additionalProperties 兼容路径，不 bump dialogue_graph const**（§2.4 / Q2） |
| **SceneGraphContext 字段集** | T-2.5 prompt 写 `faction_clocks`，T-2.6 dataclass 写 `active_clocks`；T-2.0 写 `location_candidates`，T-2.6 写 `location_card` | **统一**：clocks 字段 = `active_clocks`（含 world / faction / environmental 三类）；location 字段 = `location_candidates: list[dict]` + 可选 `primary_location_ref: str | None`（§2.8 / critique 4.1 / §9） |
| **scene review 命令** | T-2.8 文件名 `scene_review_cli.py`；T-2.12 命令 `python -m generator.scene_review` | **统一为 `python -m generator.scene_review_cli`**；T-2.8 加 `--help` smoke test（§2.8 / critique §9） |
| **validator 模块命名** | 现有 `validator/graph_check.py`；T-2.7 新建 `graph_validation.py` 未明示关系 | **`graph_validation.py` 包装现有 `graph_check.py`；后者保留向后兼容**（§2.7 / Q7 / critique §9） |
| **2A / 2B 范围划分**（v1.0 新增） | v0.1.1 ADR-021 草稿 + T-2.7 把 condition-aware 放进 2A，但 A2 自承启发式 | **2A 仅结构拓扑 + condition 引用形态合法性；condition satisfiability 全部走 2B**；T-2.7 完成标志拆双报（§3 ADR-021 / Q5 / critique 4.7） |
| **schema_version 策略**（v1.0 新增） | v0.1.1 把 dialogue_graph + node 升至 0.3.0，与 gold scene 必须保 0.1.1 互否 | **既有 schema (dialogue_graph/node/option/state_effect/state_condition) const 保持 0.1.1；新建 schema (character/location/clock/chapter) const "0.3.0"；新增字段走 optional + additionalProperties 兼容路径**（§2.4 / Q2 / critique 3.2） |
| **character/location envelope vs character_id**（v1.0 新增） | v0.1.1 character.schema 要求 character_id；现 ontology entities[] 用 id envelope | **character schema 校验 entity 全对象，envelope id 字段保留（不引入 character_id）；relations 内嵌 character envelope**（§2.5 / Q3 / critique 4.2） |
| **B 报告路径**（v1.0 新增） | v0.1.1 §1.5 + 各 L3 写 `/docs/reviews/_targets/<task>_review_<topic>.md`；模板 commit `8842c43` 路径 `/docs/reviews/{ISO_DATE}_{TARGET}_review.md` 互否 | **统一跟模板**：`/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`；删 `_targets/` 子目录（§1.5 / Q4 / critique 4.3） |
| **T-2.0 / T-2.11 模块边界**（v1.0 新增） | T-2.0 允许列表无 context_assembler.py，但 R4 要改它；T-2.11 同 generate_node.py | **T-2.0 加 context_assembler.py（仅 location_candidates 字段）；T-2.11 加 generate_node.py（仅 reconcile/refund hook）**（§7 / critique 3.3） |
| **T-2.6 / T-2.8 真实依赖**（v1.0 新增） | T-2.6 依赖只写 T-2.5；T-2.8 依赖只写 T-2.6；但代码层 T-2.6 依赖 T-2.4 / T-2.8 依赖 T-2.4+T-2.7 | **T-2.6 依赖改 T-2.5+T-2.4；T-2.8 依赖改 T-2.6+T-2.4+T-2.7**（§7 / §6 / critique 3.4） |
| **AI judge runner**（v1.0 新增） | T-2.9 prompt 不实际跑 / T-2.8 不做调用 / T-2.12 列 AI_JUDGE_REPORT.md 为产物——无人负责生成 | **T-2.8 新增 scene_ai_judge.py runner；T-2.12 调本 runner 生成 AI_JUDGE_REPORT.md**（§7 / critique 4.8） |
| **fill_skeleton allowed_targets**（v1.0 新增） | v0.1.1 fill_skeleton 仅"每个节点调一次 generate_node"，未约束 target_node_id | **T-2.5 fill_skeleton 注入 allowed_targets / expected_out_edges 给 generate_node prompt + 后处理拒收 skeleton 外 target；NodeRequirement.allowed_targets 字段扩展**（§7 / critique 4.9） |
| **pyproject.toml scene 子包**（v1.0 新增） | T-2.5 新建 generator/prompts/scene/ + T-2.9 新建 markdown，但未授权改 pyproject | **T-2.5 加 packages 列表；T-2.9 加 package-data**（§7 / critique 4.6） |
| **/schema/tests + /state/tests**（v1.0 新增） | T-2.2 新增测试只放 /generator/tests/，schema 错误下游才发现 | **T-2.2 允许 + 要求新增 /schema/tests/test_stage2_ontology_schema.py + /state/tests/test_stage2_ontology_loader.py；/generator/tests/ 仅测 generated models 消费**（§7 / critique 4.5） |
| **cost reconcile record_id + 三态 refund**（v1.0 新增） | check_and_charge 返回 None；失败一律 cost_usd=0（过度乐观） | **check_and_charge 返回稳定 record_id；reconcile_after_call(record_id)；refund_estimated(record_id)；三态 refund**（pre_call_budget_fail / request_not_sent / request_sent_failure）；**provider 差异化异常分类作 R2.1 follow-up**（§7 / Q6 / critique 4.10） |
| **active clocks ≤ 10 检查点**（v1.0 新增） | PZ §3.4 D9 拍板软上限，但无 schema/test/validator 检查点 | **T-2.7 sampling/validator 加 ACTIVE_CLOCKS_OVER_SOFT_LIMIT warning**（schema 不加；T-2.7 实测倒推后 ADR-017 v0.2 修订）（§3 ADR-017 / critique §6） |
| **system_time 双轨 state path**（v1.0 新增） | system_time 字段拍板，但与 state path 命名空间表关系未明 | **ADR-016 state path 表明示 `world.scene_count` / `world.long_rest_count` 落入 `world.*` 命名空间**（§2.2 / §3 ADR-016 / critique §6） |
| **gross pass rate 报告口径**（v1.0 新增） | ADR-020 草稿仅说接受率分子分母；critique 指出 N=15 统计置信区间宽 | **ADR-020 §9 + STAGE_2_BASELINE_PROTOCOL §9 要求每次 batch 同时报告 gross pass rate + 人工接受率**（§3 ADR-020 / critique §10 weakness 2） |
| **N=100 经验阈值标注**（v1.0 新增） | ADR-021 草稿写 N=100 起步，未标"经验阈值" | **ADR-021 决策核心明示"经验阈值，不暗示充分证明"；T-2.13 验收报告引用此口径**（§3 ADR-021 / critique §10 weakness 3） |
| **ROADMAP 完成标志措辞**（v1.0 新增） | ADR-021 后果段说"由作者另起 L1 修订会话同步"，但任务清单无明确触发点 | **跨边界 X1**：T-2.13 验收报告引用 ADR-021 实际口径，**不引用 ROADMAP 旧"证明"文本，也不修 ROADMAP 完成标志**；ROADMAP 文本同步由作者另起 L1 doc 修订会话处理（§13） |
| **成本估算口径**（v1.0 新增） | ADR-020 替代方案"N=20 成本约 $5"；T-2.12 "N=15 预期 $7-$15"——成本口径打架 | **统一**：每场景 ~$0.5–$1.0；N=15 总 $7–$15；N=20 总 $10–$20（§3 ADR-020 §10 / critique 5.2） |
| **§11 版本历史口径**（v1.0 新增） | "全部 12 个 L3 prompt"与 §7 13 条互否（T-2.3 并入 T-2.1） | **统一为"12 个 paste-ready prompt + T-2.3 placeholder = 13 个编号槽位"**（§7 / §11 / critique 5.1） |
| **T-2.10 完成标志测试要求**（v1.0 新增） | 纯文档任务模板要求"测试输出"——模板残留 | **改"无测试；运行 markdown link sanity check 或 not applicable"**（§8 T-2.10 / critique 5.3） |

---

## 10. 已识别的开放风险（cross-LLM critique 时可重点扫；v1.0 修订）

L2 整合后自评：以下 4 条是 v1.0 草稿可能被下一轮 critique 攻击的最弱点。**v0.1.1 §10 弱点 5（"Sibling 涌现项目接口不预留"）已删除**——critique R1 反对作为弱点（已锁拍板 + ADR-004 极简精神，不应在 v1.0 中防御过度），v1.0 同意。

### 10.1 ⚠️ schema_version 后向兼容机制无形式化测试覆盖率指标

v1.0 §2.4 决策"既有 schema 不动 const + 新增字段走 optional 兼容路径"在 T-2.2 测试中要求"gold scene 仍 pass v0.1.1 dialogue_graph schema"。但**没有要求**：
- 跨阶段 0/1/1.5 既有所有测试 fixture 都跑一遍回归
- additionalProperties 兼容性的形式化检查（如新增字段在所有既有 sample 上都 optional）

阶段 2 后期或阶段 3 启动时若发现某个被遗漏的 fixture 因新字段被拒收，将造成回归债。下一轮 critique 可建议 T-2.2 加"全 fixture 回归通跑"硬要求。

### 10.2 ⚠️ state_path_slug 字段在跨场景同名场景下的歧义保护无机制

v1.0 §2.6 决策 character entity 加 `state_path_slug` 字段，默认值 = `id` 去 `char_` 前缀。但**未要求**：
- ontology loader 检查 slug 跨 character 唯一性
- 多 character 同 slug 时报错

阶段 2 起步只 vellin/corvan/aelwin 三 character 不撞，但阶段 3 角色扩展若有同名（如两个不同的 vellin），会让 `relationship.vellin.trust` 路径歧义。下一轮 critique 可建议 T-2.2 在 /state/tests/ 加"slug 跨 entity 唯一性"测试。

### 10.3 ⚠️ scene_ai_judge runner 调真实 API 的成本未在 ADR-020 / T-2.12 显式估算

v1.0 §7 / T-2.8 新增 scene_ai_judge.py runner，T-2.12 调本 runner 生成 AI_JUDGE_REPORT.md。但**未估算**：
- 每次 AI 判官调用的成本（pass 1 + pass 2 双 pass × N=15 场景 × 节点级 21 维 + 场景级 6-10 维）
- 是否进入 budget.PER_CALL_BUDGET_USD 控制
- 失败时 reconcile/refund 是否覆盖 scene_ai_judge 调用（T-2.11 仅覆盖 generate_node hook）

下一轮 critique 可建议 T-2.8 / T-2.11 范围扩展或新开 T-2.14（AI judge runner 的成本治理）。

### 10.4 ⚠️ Wave 3 三任务（T-2.4 / T-2.5 / T-2.7）真实并行度受 routine 与 PR merge 节奏限制

v1.0 §6 wave 图清晰列出 Wave 3 = {T-2.4, T-2.5, T-2.7}。但 ABC 闭环 + PR merge 硬规则（§1.5.3）要求每条 PR 走 A+B+C+L2 验收才 merge——若三任务同时进 A 阶段，B 阶段（作者另起 Codex 会话）需串行处理，B 阶段瓶颈会让真实并行收敛到串行。

下一轮 critique 可建议 §6 增补"实际并行度估算 = (A 阶段并行) + (B 阶段串行)"或在治理备忘 v0.4 引入"B 阶段并行机制"（如多 Codex 会话同时跑不同 PR）。

---

## 11. 版本

本文件版本：**v1.0**（GPT-5.5 critique 整合版）
日期：2026-05-03
产出方：阶段 2 L2 整合规划师会话（worktree claude/musing-fermi-f6bfd3）

### 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-05-03 | 首版草稿；按治理备忘 v0.2 [A-execute] / [B-author-gate] 任务分类制度落地（产出方：claude/ecstatic-lewin-6aee3c） |
| v0.1.1 | 2026-05-03 | L1 下达治理备忘 v0.3 修订：任务分类降级为概念注释（实操不依赖）；所有 L3 一律走统一 ABC 三阶段闭环。修订点：§0 新增 v0.1.1 修订说明；§1.5 新增 ABC 闭环全局说明；§6 routine 兼容性段重写；§8 全部 12 个 paste-ready prompt + T-2.3 placeholder = 13 个编号槽位（**v1.0 修订口径**），末尾"完成报告"段升级为"A 阶段完成标志 + B/C 阶段说明"统一格式；§9 Wave 4 段重写；4 个原 [B-author-gate] L3（T-2.1 / T-2.2 / T-2.9 / T-2.13）顶部任务类型段改写为"概念保留；实操按 ABC 闭环 commit + push + 开 PR" |
| **v1.0** | **2026-05-03** | **GPT-5.5 cross-LLM critique 整合版。基于 v0.1.1 + 2026-05-03 GPT-5.5 critique（19 finding：🔴 5 / 🟡 10 / 🟢 4）+ 2026-05-03 L1 Wave 2 校准（"全选推荐"路径）。完整修订对照表见 §12。核心修订**：（a）§1.5 B 报告路径改 `/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`，删 `_targets/` 子目录约定（critique 4.3 / Q4）；（b）§2 新增 5 个小节（§2.4 schema_version 复合语义 / §2.5 envelope 契约 / §2.6 state_path_slug / §2.7 graph_validation 包装 / §2.8 一致性细节）；（c）§3 ADR-016 state path 表改用 `<state_path_slug>`；ADR-019 generation_trace 改走 optional 兼容路径不 bump dialogue_graph const；ADR-020 加 gross pass + 接受率双报口径 + 成本口径统一；ADR-021 拆双报完成标志；（d）§7 任务概览表修依赖列（T-2.6 = T-2.5+T-2.4 / T-2.8 = T-2.6+T-2.4+T-2.7）+ 模块边界扩充（T-2.0 / T-2.2 / T-2.5 / T-2.8 / T-2.9 / T-2.11）；（e）§8 13 个 prompt 全部按 critique + Wave 2 拍板修订；（f）§10 删原弱点 5（R1 反对作为弱点）+ 加 4 条新弱点；（g）§12 新增完整修订记录；（h）§13 新增跨边界清单（X1/X2/X3）。产出方 worktree：claude/musing-fermi-f6bfd3 |

### 基于

- /CLAUDE.md
- /docs/ROADMAP.md
- /docs/DECISIONS.md ADR-001~015
- /docs/DEBATE_NOTES.md（含 Round 5 段）
- /docs/HANDOFF_STAGE_1_TO_2.md v0.2
- /docs/STAGE_1_ACCEPTANCE.md / STAGE_1.5_ACCEPTANCE.md
- /docs/SCHEMA_v0.md / SCHEMA_v0.2.md
- /docs/reviews/master_plan/2026-04-30_synthesis.md
- /docs/REVIEW_PROMPT_CODE_GPT.md（commit `8842c43`；ABC 闭环 B 阶段模板）
- L1 inline §A 治理备忘 v0.2 + §B PZ 反思 v0.1（2026-05-03 L1→L2 prompt 注入；未落盘）
- L1 inline 治理备忘 v0.3 ABC 闭环升级（2026-05-03 L1→L2 prompt 注入）
- 2026-05-03 L1-L2 校准（"全同意默认"路径）
- **v0.1.1 草稿**：`.claude/worktrees/ecstatic-lewin-6aee3c/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_v0.1.md`（L2 草稿源）
- **GPT-5.5 critique 报告**：`/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_gpt_critique.md`（critique 源；commit 在 main 工作树）
- **2026-05-03 L1 Wave 2 校准**：作者明示 "Q1-Q7 全选推荐 / R1 同意删 §10.5"

---

## 12. 修订记录（v0.1.1 → v1.0；critique finding 完整对照）

### 12.1 ✅ 直接吸收（12 条）

| critique 编号 | finding 摘要 | v1.0 落地位置 | 修订方向 |
|---|---|---|---|
| 3.3 | T-2.0 / T-2.11 模块边界禁止任务自己要改的文件 | §7 任务概览（T-2.0 / T-2.11 模块边界列）+ §8 T-2.0 + §8 T-2.11 | T-2.0 允许列表加 `/generator/context_assembler.py`（仅 GraphContext.location_card → location_candidates 字段）；T-2.11 加 `/generator/generate_node.py`（仅 reconcile/refund hook 接入）；删 T-2.0 v0.1.1 line 289 "如果 dataclass 改动太大就停"模糊兜底 |
| 3.4 | T-2.6 / T-2.8 依赖图漏掉真实代码依赖 | §6 wave 图修订说明 + §7 任务概览（T-2.6 / T-2.8 依赖列） | T-2.6 依赖改 T-2.5+T-2.4；T-2.8 依赖改 T-2.6+T-2.4+T-2.7；wave 图本身正确无需重排 |
| 3.5 | T-2.1 A 阶段 commit/PR 规则内自相矛盾 | §8 T-2.1 任务类型段 + 完成标志段 | 删 v0.1.1 line 471 "等作者明示 commit it"旧流程残留；统一 ABC 顶部措辞（直接 commit + push + 开 PR） |
| 4.1 | T-2.0 / T-2.5 / T-2.6 location_candidates 未贯穿 scene context | §2.8 一致性细节表 + §8 T-2.0 + T-2.5 + T-2.6 | T-2.5 prompt 输入 + T-2.6 SceneGraphContext 字段名统一为 `location_candidates: list[dict]`；如需主地点用 `primary_location_ref: str | None`；同步 T-2.0 R4 措辞 |
| 4.4 | T-2.1 paste-ready prompt 引用的草稿路径在 main 不存在且会过期 | §8 全部 13 个 prompt 必读段 + §11 §13 引用规则 | v1.0 全部 L3 prompt 引用自身决策章节时统一改为 `/docs/STAGE_2_TASKS.md` 对应章节；草稿仅作评审史料；v0.1.1 §9 line 1615"L2 v0.1.1 草稿已落 /docs/..."表述同步修正（v1.0 §0 / §11 已说明 v1.0 落 worktree） |
| 4.5 | T-2.2 schema 关键任务没有授权 /schema/tests/ 与 /state/tests/ | §7 任务概览（T-2.2 模块边界列）+ §8 T-2.2 模块边界 + 待落地点 9/10/11 | T-2.2 允许 + 要求新增 `/schema/tests/test_stage2_ontology_schema.py` + `/state/tests/test_stage2_ontology_loader.py`；`/generator/tests/` 仅测 generated models 消费 |
| 4.6 | T-2.5 / T-2.9 新建 generator.prompts.scene 子包但未授权 pyproject 配置 | §7 任务概览（T-2.5 / T-2.9 模块边界列）+ §8 T-2.5 待落地点 7 + T-2.9 待落地点 3 | T-2.5 允许新增 `generator/prompts/scene/__init__.py` + 改 `pyproject.toml` packages 加 `generator.prompts.scene`；T-2.9 同步 package-data 加 `"generator.prompts.scene" = ["*.md"]` |
| 4.8 | T-2.12 AI_JUDGE_REPORT.md 没有任务负责实际生成 | §7 任务概览（T-2.8 模块边界 + 名称）+ §8 T-2.8 待落地点 5 + T-2.12 §3 | T-2.8 加 `scene_ai_judge.py` runner（fake provider 可测；T-2.12 实证 batch 调它生成 AI_JUDGE_REPORT.md）；不降级为 optional |
| 4.9 | T-2.5 / T-2.6 skeleton edges 没写清如何约束 fill 阶段 target_node_id | §7 任务概览（T-2.5 模块边界）+ §8 T-2.5 待落地点 4-5 + 测试段 | T-2.5 fill_skeleton 把每节点 `allowed_targets`/`expected_out_edges` 注入 generate_node prompt + 后处理拒收 skeleton 外 target；扩展 `NodeRequirement.allowed_targets` 字段；测试覆盖"LLM 越界 → 拒收 + 回喂"（含三次越界 → success=False, "fill_target_out_of_skeleton"） |
| 5.1 | §11 "全部 12 个 L3 prompt" 与 13 任务口径不一致 | §7 任务总数行 + §11 变更历史 | 统一为"12 个 paste-ready prompt + T-2.3 placeholder = 13 个编号槽位" |
| 5.2 | T-2.1 / T-2.12 baseline 成本数字前后不一致 | §3 ADR-020 决策核心 §10 + §8 T-2.12 §2 | 统一口径"每场景 ~$0.5-$1.0；N=15 总 $7-$15；N=20 总 $10-$20"；ADR-020 替代方案段同步 |
| 5.3 | T-2.10 纯文档任务完成标志仍要求"测试输出" | §8 T-2.10 完成标志段 | 改"无测试；运行 markdown link sanity check 或 not applicable" |

### 12.2 ⚠️ 部分同意（6 条；按 Wave 2 全选推荐落地）

| critique 编号 | Wave 2 选项 | v1.0 落地位置 | 修订方向 |
|---|---|---|---|
| 3.1（Q1） | A | §2.1 D11 + §2.6 + §3 ADR-016 决策核心 + §8 T-2.1 ADR-016 + T-2.2 待落地点 1+6 + T-2.4 待落地点 2 + T-2.5 prompt | state path 命名空间继续用短 slug（`relationship.<state_path_slug>.*`）；character entity 显式加 `state_path_slug` 字段（默认 = `id` 去 `char_` 前缀）；ADR-016 表语义改用 slug；T-2.4 BOND_ID_UNKNOWN 用 slug 反查 entity.id |
| 3.2（Q2） | A | §2.4 + §3 ADR-016 决策核心 + §3 ADR-019 决策核心 + §8 T-2.2 模块边界 + 待落地点 5 + 实施顺序 | 既有 schema (dialogue_graph/node/option/state_effect/state_condition) 的 schema_version const 保持 "0.1.1" 不动；新增字段（如 generation_trace.slot_assignments）走 optional + additionalProperties 兼容路径；新建 schema (character/location/clock/chapter) 首版即 const "0.3.0"；SCHEMA_v0.3.md 解释复合版本号语义 |
| 4.2（Q3） | A | §2.5 + §3 ADR-016 + ADR-018 决策核心 + §8 T-2.2 待落地点 1+2 | 保留 entity envelope 字段名 `id`（不引入 character_id 冗余名）；character.schema.json 校验 entity 全对象，`properties.id.pattern: "^char_[a-z0-9_]+$"` + `properties.type.const: "character"`；location 同；relations 内嵌 character envelope，不引入全局关系表 |
| 4.3（Q4） | A | §1.5 §1.5.1 + §8 全部 13 个 prompt 末尾 B 阶段段 | v1.0 §1.5 + 各 L3 末段 B 报告路径 = `/docs/reviews/<ISO_DATE>_T-2.X_<topic>_review.md`（跟 REVIEW_PROMPT_CODE_GPT.md commit `8842c43` 模板）；删除 `_targets/` 子目录约定 |
| 4.7（Q5） | A | §3 ADR-021 决策核心 + §8 T-2.7 待落地点 1-2 + 完成标志拆双报段 | 2A 明确降为"结构拓扑 + condition 引用形态合法性"（path 命名空间 / op 枚举 / 字段结构）；condition satisfiability 全部走 2B 抽样 + 有界符号执行；T-2.7 完成标志拆"纯拓扑 pass / condition-aware（2B）pass"双报 |
| 4.10（Q6） | **B**（不是 A） | §7 任务概览（T-2.11 模块边界）+ §8 T-2.11 待落地点 1-4 + R2.1 follow-up 标注 | 必做层（进 T-2.11）：check_and_charge 改返回稳定 record_id；reconcile_after_call(record_id)；refund_estimated(record_id)；三态 refund（pre_call_budget_fail / request_not_sent / request_sent_failure）；**provider 差异化异常分类作 R2.1 follow-up（不在 T-2.11 范围）** |
| §9 Q7 | A | §2.7 + §8 T-2.7 模块边界（严禁删除 graph_check.py） | `graph_validation.py` 包装现有 `graph_check.py`（import 现有函数 + 加 2A 新逻辑）；`graph_check.py` 保留向后兼容 |

### 12.3 ❌ 反对（1 条）

| critique 编号 | finding | v1.0 处置 | 论据 |
|---|---|---|---|
| §10 弱点 5 反驳（R1） | critique 反对 v0.1.1 §10.5 "Sibling 涌现项目接口不预留" 作为弱点 | **v1.0 §10 删除该条**（v0.1.1 §10.5 不进 v1.0） | 同意 critique 反对——v0.1.1 §10 line 1648 把"接口不预留"列为弱点是 self-confirmation bias 反向（自我抬杠）。v1.0 §10 直接删除该条 + 维持 PZ §6 拍板 + ADR-004 极简精神立场。Wave 2 校准作者已确认 |

### 12.4 顺手补的小修（不另列编号；critique §6 / §7 / §9 / §10 锚点）

| 项 | v1.0 落地位置 | 修订方向 |
|---|---|---|
| `tick_effects.effect_op` vs `StateEffect.op` 命名映射 | §2.8 + §3 ADR-017 决策核心 + §8 T-2.7 待落地点 5 | T-2.7 effect 应用器明示 effect_op 等价 StateEffect.op（set/inc/dec/add/remove）；用统一映射函数 |
| `SceneGraphContext.faction_clocks` vs `active_clocks` | §2.8 + §8 T-2.5 prompt + T-2.6 dataclass | 统一为 `active_clocks`（含 world / faction / environmental 三类） |
| `scene_review_cli.py` vs `python -m generator.scene_review` 命令名 | §2.8 + §8 T-2.8 待落地点 2 + T-2.12 §2 | 统一为 `python -m generator.scene_review_cli`；T-2.8 加 `--help` smoke test |
| system_time 双轨 state path 落入 `world.*` 命名空间 | §2.2 + §3 ADR-016 决策核心 + §8 T-2.2 待落地点 6 | ADR-016 state path 表 `world.*` 命名空间明示含 `world.scene_count` / `world.long_rest_count`（合法 state path） |
| 时钟同时活跃 ≤ 10 检查点 | §3 ADR-017 决策核心 + §8 T-2.7 待落地点 3 | T-2.7 sampling/validator 加 active clocks count 检查（ACTIVE_CLOCKS_OVER_SOFT_LIMIT warning 级；schema 不加，由 T-2.7 实测倒推） |
| advance_rule 不存在 time_based 子类 | §2.2 + §3 ADR-017 决策核心 + §8 T-2.2 待落地点 7 SCHEMA_v0.3.md §4 | SCHEMA_v0.3.md §4 明示"不存在 time_based 子类" |
| §10 弱点 2（N=15）补强 | §2.1 D4 + §3 ADR-020 决策核心 §9 + §8 T-2.9 待落地点 1 §9 | ADR-020 + STAGE_2_BASELINE_PROTOCOL 加"报告同时给 gross pass rate + 人工接受率" |
| §10 弱点 3（N=100 起步无理论）标注 | §3 ADR-021 决策核心 + §8 T-2.7 sampling.py docstring | ADR-021 + T-2.7 sampling 函数明示 N=100 是经验阈值，不暗示充分证明 |
| §10 弱点 4（dramatic_triggers 无 seed） | §2.1 D10 + §8 T-2.2 待落地点 6 | T-2.2 落地 vellin/corvan/aelwin 三 character 时给 1-2 个 seed 示例（如 vellin 的 trigger） |

---

## 13. 跨边界清单（不进 v1.0；待作者另起会话处理）

下列 3 项是 critique / Wave 2 整合过程中识别出的"超出 L2 整合规划师边界"事项，**v1.0 草稿不处理**，由作者另起会话推进。

### X1：ROADMAP §阶段 2 完成标志措辞修订

- **来源**：critique 5.4 + ADR-021 后果段 + v1.0 §3 ADR-021 决策核心
- **修订内容**：ROADMAP §阶段 2 当前完成标志含"证明任意合法状态组合下至少有 1 个结局可达"措辞；ADR-021 已修订为"**抽样验证 N=100 路径 + 有界符号执行下未发现反例**"
- **为什么不在 v1.0 范围**：L2 整合规划师严禁修改 L1 文档（CLAUDE.md / ROADMAP.md / DECISIONS.md / ...，CLAUDE.md 规则段 + 本草稿任务描述）
- **作者另起做的事**：
  1. 另起 L1 doc 修订会话（专门改 ROADMAP）；按 ABC 闭环走 PR
  2. T-2.13 验收报告（v1.0 §8 T-2.13 已修订）**不动 ROADMAP §阶段 2 完成标志措辞**——仅引用 ADR-021 实际口径作为完成判定依据
  3. 时机建议：ADR-021 立项 PR merge 后（即 T-2.1 完成后）即可启动 ROADMAP 修订；或在 T-2.13 验收前同步处理

### X2：ADR-016 ~ ADR-021 立项（6 条 ADR 一次性 commit）

- **来源**：v0.1.1 §3 候选 ADR + v1.0 §3 + T-2.1 paste-ready prompt（v1.0 §8）
- **修订内容**：6 条 ADR 实际 commit 进 `/docs/DECISIONS.md`（含 ADR-016 本体最小契约 / ADR-017 时钟 / ADR-018 narrative_weight / ADR-019 角色槽位 / ADR-020 baseline 协议 / ADR-021 ADR-009 第二层）
- **为什么不在 v1.0 范围**：L2 整合规划师不立 ADR；v1.0 仅识别 + 描述决策核心；实际立项动作由 L3 执行会话跑 T-2.1 paste-ready prompt 落
- **作者另起做的事**：
  1. v1.0 草稿 commit 进 `/docs/STAGE_2_TASKS.md` 后（即 X3 完成后），另起 L3 执行会话跑 T-2.1 paste-ready prompt（v1.0 §8 T-2.1）
  2. T-2.1 走 ABC 闭环：A 阶段 commit + push + 开 PR；B 阶段 Codex review；C 阶段 Claude Code 修；L2 验收过关后 merge
  3. T-2.1 PR merge 后才能启动 T-2.2（schema 落地）— 严格串行关键路径

### X3：v1.0 草稿 commit 进 /docs/STAGE_2_TASKS.md

- **来源**：作者明示授权另起 L3 执行 + v1.0 §0 下一步说明
- **修订内容**：v1.0 草稿（本文件）整合内容 commit 进 `/docs/STAGE_2_TASKS.md`（[B-author-gate] 任务）
- **为什么不在 v1.0 范围**：L2 整合规划师只能产 `/docs/reviews/master_plan/2026-05-XX_STAGE_2_TASKS_v1.0_draft.md`（即本文件）；不能直接进 `/docs/STAGE_2_TASKS.md`——后者是另一个 L3 任务由作者明示授权后落
- **作者另起做的事**：
  1. 审 v1.0 草稿（本文件）+ §12 修订记录 + §13 跨边界清单 + §10 自评 4 弱点
  2. 如有反对方案 / 校准点 → 反馈给 L2（本会话）出 v1.1（在本草稿同目录新文件，保留 v1.0 审计）；如全同意 → 明示授权
  3. 明示授权后另起 L3 执行会话把 v1.0 内容 commit 进 `/docs/STAGE_2_TASKS.md`，走 ABC 闭环
  4. v1.0 commit 进 STAGE_2_TASKS.md 的 PR merge 后，Wave 0 三 L3（T-2.0 / T-2.10 / T-2.11）即可启动 A 阶段

---

> **v1.0 草稿全文完。共 §0-§13 + 13 个 paste-ready prompt + 完整修订记录 + 跨边界清单。**
>
> **下一步（不在本会话范围）**：
> 1. 作者审 v1.0（本文件）；如有反对 / 校准 → 反馈给本 L2 会话出 v1.1
> 2. 全同意 → 作者明示授权后另起 L3 执行会话把 v1.0 commit 进 `/docs/STAGE_2_TASKS.md`（[B-author-gate]，走 ABC 闭环）
> 3. 同期可启动 X1（ROADMAP 修订 L1 doc 会话）；与 X3 并行不冲突
> 4. v1.0 commit 进 STAGE_2_TASKS.md 的 PR merge 后，启动 X2（T-2.1 ADR-016~021 立项）+ Wave 0 三 L3（T-2.0 / T-2.10 / T-2.11）
