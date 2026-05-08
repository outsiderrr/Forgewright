# Stage 2 Task Plan Critique — GPT-5.5

**评审者**：GPT-5.5 via Codex
**评审日期**：2026-05-03
**评审对象**：`/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_v0.1.md` v0.1.1（治理 v0.3 ABC 闭环修订版）
**项目状态**：阶段 1.5 部分通过（commit `9be7a3e`），ADR-015 sequencing 解锁；阶段 2 草稿 v0.1.1 待 cross-LLM critique 后整合产 v1.0

---

## 1. 一句话总判

草稿的大方向是可执行的：13 个 L3 基本覆盖了阶段 2 的主路径、5+2 闸门和 PZ 拍板项；但 v1.0 不能直接产出，必须先修几处“执行会话会照着 prompt 走进死胡同”的硬伤，尤其是 schema_version 兼容、state path 命名、真实 wave 依赖和 ABC 段冲突。

## 2. 严重度分布

| 严重度 | 数量 |
|---|---|
| 🔴 | 5 |
| 🟡 | 10 |
| 🟢 | 4 |
| **合计** | 19 |

## 3. 必修（🔴）

### 3.1 [CONSIST/TEST] T-2.2 / T-2.4 / T-2.7 — `relationship.<character_id>` 会让 gold standard 过不了

**问题**：草稿把合法 state path 写成 `relationship.<character_id>.*`，且 character schema 要求 `character_id` 形如 `char_vellin`；但《铁誓驿站》gold scene 现有路径是 `relationship.vellin.trust` / `relationship.corvan.trust`。T-2.4 又要求在 gold standard 上全过，并按本体花名册校验 relationship id；按当前计划实现会直接把 gold standard 判 fail。
**指向**：草稿 `ADR-016` state path 表 `:352`、`character_id` pattern `:530`、T-2.4 C3 `:690`、gold standard 必过 `:706`、T-2.7 gold N=100 `:1090`；现有样本见 `/content/test_scene_v0/scene.json:44`、`:99`、`:120`，本体 id 见 `/state/ontology/waystation.json:4`、`:136`。
**建议路径**：v1.0 必须明确二选一：A. state path 命名空间继续用短 slug（`relationship.vellin.*`），并在本体中显式提供 `state_path_slug` / alias；B. 迁移 gold scene 到 `relationship.char_vellin.*` 并把“gold 不动”禁令相应改掉。不要让 T-2.4 执行会话现场猜。

### 3.2 [SCHEMA/TEST] T-2.2 — `schema_version` bump 与“gold scene 保持 0.1.1”互相打架

**问题**：T-2.2 要把 `dialogue_graph.schema.json` / `node.schema.json` 的 schema_version 升到 0.3.0，同时又明令 `/content/test_scene_v0/scene.json` 保持 0.1.1 且 gold standard 后续必须通过。当前根 schema 用 `const: "0.1.1"`；若直接改为 `0.3.0`，现有 gold 和所有阶段 0/1 测试会被 schema 层拒收。草稿同时说“不破 v0.1.x / v0.2.0”，但没有给兼容机制。
**指向**：草稿 T-2.2 允许修改与禁改 `:503-515`，版本升级 `:550-554`，兼容性说明 `:578`，gold 不动提醒 `:603`；SCHEMA_v0 规定版本只在 DialogueGraph 根对象 `/docs/SCHEMA_v0.md:54`；当前 const 见 `/schema/dialogue_graph.schema.json:10-12`。
**建议路径**：v1.0 先补版本策略：例如 root `schema_version` 接受 `0.1.1` 与 `0.3.0` 两档、或新增版本化 schema registry、或保持现有 graph const 不动而只新增 optional 字段。无论选哪条，都要写进 T-2.2 测试要求：old gold scene 仍 pass，新 v0.3 sample 也 pass。

### 3.3 [SCOPE] T-2.0 / T-2.11 — 模块边界禁止了任务自己要求改的文件

**问题**：T-2.0 允许列表只有 `/generator/prompts/`、tests、fixtures，却要求修改 `/generator/context_assembler.py`；T-2.11 允许列表没有 `/generator/generate_node.py`，却要求修改它接入 reconcile/refund。执行会话若遵守模块边界会停，若硬改会违反 prompt。
**指向**：T-2.0 允许/严禁 `:250-256`，R4 待改 `:287-289`；T-2.11 允许/严禁 `:1374-1380`，generate_node 待改 `:1408-1410`。
**建议路径**：把这些文件显式加入允许列表，并限定只改对应接口；或者把相关改动拆到依赖任务。不要保留“如果 dataclass 改动太大就停”的模糊兜底，因为这是任务核心，不是可选探索。

### 3.4 [DEP] T-2.6 / T-2.8 — 依赖图漏掉真实代码依赖，wave 会抢跑

**问题**：§7 表里 T-2.6 只依赖 T-2.5，但它的流程要调用 T-2.4 的 `validate_graph_mechanical`；T-2.8 只依赖 T-2.6，但它的 summary/review UI 要展示机械预检、拓扑和抽样结果，实际依赖 T-2.4 + T-2.7。按当前 wave 执行，T-2.6/T-2.8 很容易在需要的 validator API 尚未 merge 时启动。
**指向**：wave 图 `:181-190`，概览依赖 `:221-223`，T-2.6 调机械预检 `:922`，T-2.8 输出 topology/sampling 指标 `:1158`、review 展示 validator summary `:1170`。
**建议路径**：把 T-2.6 依赖改为 T-2.5 + T-2.4；把 T-2.8 依赖改为 T-2.6 + T-2.4 + T-2.7，或明确 validator 结果在 T-2.8 中是 optional adapter 并有降级测试。建议前者，减少阶段 2 验收前的“先 stub 后补”债。

### 3.5 [ABC] T-2.1 — A 阶段 commit/PR 规则内自相矛盾

**问题**：T-2.1 顶部说 v0.3 起 A 阶段直接 commit + push + 开 PR，不再等作者授权；但 A 阶段完成标志又写“等作者明示 `commit it` 或调整后再 commit”。这是 ADR 关键路径任务，执行会话看到两条相反规则会停下来问，ABC 闭环也会失去统一性。
**指向**：T-2.1 ABC 说明 `:326-330`，完成标志 `:466-474`，特别是 `:471`。
**建议路径**：删除“等作者明示 commit it”这条旧流程残留。若 ADR 任务仍要额外作者签字，应写成“PR 开出后由 B/C/L2/作者在 merge 前审”，不要阻塞 A 阶段 commit。

## 4. 应修（🟡）

### 4.1 [CONSIST/GATE] T-2.0 / T-2.5 / T-2.6 — `location_candidates` 没有贯穿到 scene 级上下文

**问题**：R4 的核心修法是把单 `location_card` 升为 `location_candidates`，防模型乱猜地点；但 T-2.6 的 `SceneGraphContext` 又回到 `location_card: dict`，T-2.5 scene prompt 输入也没有明确 location_candidates。R4 在节点级修了，scene 级主路径可能重新犯同一个错。
**指向**：T-2.0 R4 `:287-288`；T-2.5 scene prompt 输入 `:763-777`；T-2.6 SceneGraphContext `:927-939`。
**建议路径**：统一字段名为 `location_candidates: list[dict]`，scene context/prompt/few-shot/generate_scene 全部沿用；如仍需要当前地点，另设 `primary_location_ref`。

### 4.2 [CONSIST/SCHEMA] T-2.2 — character/location schema 与当前聚合本体形态未对齐

**问题**：现有本体实体是聚合 `entities[]`，每项有 `id` / `type` / `display_name`；T-2.2 新 schema 却要求 `character_id` / `location_id` 且 `additionalProperties: false`。草稿没有说明是保留 `id` 作为 envelope 字段、还是迁移为 `character_id`、还是两个都存。若按字面实现，`state.ontology` 现有按 `entity["id"]` 建索引的 loader 和测试都会受影响。
**指向**：T-2.2 character schema `:527-533`，location schema `:535-538`，ontology 修改 `:556-568`；当前 loader 见 `/state/ontology/__init__.py:16-35`。
**建议路径**：在 T-2.2 增加“本体 envelope 契约”：`id` / `type` 是否保留、`character_id` 是否等于 `id`、正式 schema 校验的是 entity 全对象还是 payload 子对象。并要求更新/新增 `state/tests` 覆盖 loader 兼容。

### 4.3 [ABC] 全局 / 13 个 L3 — B 阶段 report 路径与 `REVIEW_PROMPT_CODE_GPT.md` 模板冲突

**问题**：§1.5 和各 L3 段要求 B 报告落 `/docs/reviews/_targets/<task>_review_<topic>.md`，但被指定使用的 `/docs/REVIEW_PROMPT_CODE_GPT.md`（commit `8842c43`）模板规定 report 路径是 `/docs/reviews/{{ISO_DATE}}_{{REVIEW_TARGET_SHORT}}_review.md`。如果作者原样粘模板，报告会落到另一个目录；如果作者手改模板，又不再是 paste-ready。
**指向**：ABC 全局 `:80-82`，L3 段示例 `:311`；模板路径见 `git show 8842c43:docs/REVIEW_PROMPT_CODE_GPT.md` 行 `92-95`。
**建议路径**：二选一：A. plan 跟随模板，B 报告仍落 `/docs/reviews/`；B. 每个 L3 A 阶段产出一份已覆盖路径的 Codex review prompt。不要同时说“用 stable 模板”又要求模板外路径。

### 4.4 [DOC] T-2.1 — paste-ready prompt 引用的草稿路径在 main 不存在且会过期

**问题**：T-2.1 必读要求 `/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_v0.1.md` §3，但当前 main 工作树没有这个文件；我只能在 `.claude/worktrees/ecstatic-lewin-6aee3c/...` 找到。v1.0 合入后 L3 执行应读 `/docs/STAGE_2_TASKS.md`，继续引用 draft 会让执行会话找不到源或读过期内容。
**指向**：T-2.1 必读 `:339`；§9 又声称草稿已落 `/docs/...` `:1615`。
**建议路径**：v1.0 中所有 L3 prompt 引用自身时统一改成 `/docs/STAGE_2_TASKS.md` 对应章节；保留 draft 作为评审史料即可，不要作为执行源。

### 4.5 [TEST/SCOPE] T-2.2 — schema 关键任务没有授权 `/schema/tests/` 与 `/state/tests/`

**问题**：T-2.2 是 schema 串行卡口，却把新增测试放到 `/generator/tests/`，没有允许新增 `/schema/tests/` 或 `/state/tests/`。这会重演阶段 1.5 L2 critique 抓过的问题：schema 错误被下游 codegen 或 generator 测试才发现，定位太晚。
**指向**：T-2.2 允许列表 `:497-509`，测试要求 `:586-592`；现有 schema 测试位置见 `/schema/tests/test_schemas.py:1-27`。
**建议路径**：允许并要求 `/schema/tests/test_stage2_ontology_schema.py`、`/state/tests/test_stage2_ontology_loader.py`；generator tests 只测 generated models 和 prompt/context 消费。

### 4.6 [SCOPE] T-2.5 / T-2.9 — 新建 `generator.prompts.scene` 子包但未授权打包配置

**问题**：T-2.5 新建 `/generator/prompts/scene/system.py` / `few_shot.py`，T-2.9 新建 scene judge markdown；当前 `pyproject.toml` 静态列包，只到 `generator.prompts.visual`，package-data 也只覆盖 visual。源码路径运行可能没事，安装包或未来开源剥离会漏掉 scene prompt 子包/markdown。
**指向**：T-2.5 文件边界 `:743-749`，T-2.9 文件边界 `:1234-1238`；当前配置 `/pyproject.toml:25-41`。
**建议路径**：T-2.5 允许新增 `generator/prompts/scene/__init__.py` 并改 `pyproject.toml` packages；T-2.9 或 T-2.5 同步 package-data，或改用 setuptools auto-discovery。

### 4.7 [EDGE/TEST] T-2.7 — 2A “前置闭合/死锁”目标与实现草图的启发式不匹配

**问题**：ADR-021/T-2.7 把 2A 说成前置闭合、死锁、不可达、收敛；但 A2 又承认“要先求状态空间，复杂；起步用启发式”。这不是不能做，而是完成标志仍写 gold 2A 全过，容易把 condition-aware 校验包装成纯拓扑已完成。
**指向**：ADR-021 2A 定义 `:437`，T-2.7 A2/A3 `:1037-1041`，完成标志 `:1094-1098`。
**建议路径**：把 2A 明确降为“结构拓扑 + 条件引用形态检查”，把 condition satisfiability 放到 2B；或给 2A 增加明确的有限 state evaluator。完成标志要分别报告“纯拓扑 pass”和“condition-aware pass”。

### 4.8 [EDGE/TEST] T-2.12 — `AI_JUDGE_REPORT.md` 没有任何任务负责实际生成

**问题**：T-2.9 只写场景级 AI 判官 prompt，明确不实际跑；T-2.8 scene experiment/review CLI 也明确不做 AI 判官调用；T-2.12 却把 `AI_JUDGE_REPORT.md` 列为产物。执行到 batch run 时会发现缺少 runner/命令。
**指向**：T-2.8 不做 AI 判官 `:1201-1203`，T-2.9 不跑判官 `:1281-1283`，T-2.12 产物 `:1481-1487`。
**建议路径**：在 T-2.8 加 `scene_ai_judge.py` runner，或在 T-2.12 明确由本任务新增轻量 runner/手工调用流程。若 AI 判官只是 advisory，可把 report 从硬产物降级为 optional。

### 4.9 [CONSIST] T-2.5 / T-2.6 — skeleton-first 没写清“骨架边”如何约束填充节点

**问题**：`GraphSkeleton.edges` 是 skeleton-first 的核心，但 `fill_skeleton` 只说“每个节点调一次 generate_node”。现有 generate_node 的 `NodeRequirement` 没有 allowed target list；如果 fill 阶段不把 skeleton 的子节点 ID 注入 prompt 或后处理约束，LLM 可以生成任意 `target_node_id`，导致 skeleton 只是摆设，靠机械预检重试兜底会很烧。
**指向**：T-2.5 skeleton/fill 定义 `:784-818`，T-2.6 主流程整合/重试 `:916-924`。
**建议路径**：在 T-2.5 明确 `fill_skeleton` 对每个节点传入 `allowed_targets` / `expected_out_edges`，并测试“LLM 生成 skeleton 外 target 时被拒收并回喂”。必要时扩展 NodeRequirement，而不是只靠自然语言。

### 4.10 [EDGE] T-2.11 — cost 反向校准把失败一律视为 0 成本，且缺 record id 串联

**问题**：T-2.11 要用 timestamp 更新记录，又让 `reconcile_after_call(estimated_record_id, ...)` 接收 record id；但现有 `check_and_charge()` 不返回 id，草稿也没要求改返回值。更重要的是，provider error / schema invalid 后一律 `cost_usd=0 + failed_no_charge` 过度乐观：请求可能已到 provider 并产生 usage，只是本地解析/校验失败。
**指向**：T-2.11 update API `:1391-1397`，budget/reconcile `:1398-1402`，generate_node 接入 `:1408-1410`；现有 `check_and_charge()` 返回 `None` 见 `/generator/budget.py:42-78`。
**建议路径**：让 `check_and_charge` 返回稳定 `record_id`；失败分三类：pre-call budget fail 无记录、request未发出/连接失败可 refund、provider 返回 usage 但 schema invalid 应按 actual usage 计费。测试覆盖三类。

## 5. 可选（🟢）

### 5.1 [DOC] §11 — “全部 12 个 L3 prompt”与 13 任务口径不一致

**问题**：版本历史写“全部 12 个 L3 paste-ready prompt”，但 §7 说 13 条（T-2.3 并入 T-2.1）。这不影响执行，但会让作者数任务时困惑。
**指向**：任务总数 `:230`，版本历史 `:1664`。
**建议路径**：统一为“12 个 paste-ready prompt + T-2.3 placeholder，13 个编号槽位”。

### 5.2 [DOC] T-2.1 / T-2.12 — baseline 成本数字前后不一致

**问题**：ADR-020 否决 N=20 的理由写“成本约 $5”，但 T-2.12 又说 N=15 预期 $7-$15。N=15 选择可以成立，但成本论据前后打架。
**指向**：ADR-020 替代方案 `:425`，T-2.12 成本 `:1476`。
**建议路径**：统一估算口径，最好用“每场景估 $X-Y，所以 N=15 总 $7-$15；N=20 总 $10-$20”。

### 5.3 [DOC] T-2.10 — 纯文档任务完成标志仍要求“测试输出”

**问题**：T-2.10 只新建 sidecar 文档，但段末模板要求“PR URL + commit hash + 测试输出”。这只是模板残留。
**指向**：T-2.10 完成标志 `:1351-1356`。
**建议路径**：改成“无测试；运行 markdown/link sanity check（如有）或说明 not applicable”。

### 5.4 [DOC] T-2.9 / T-2.13 — ROADMAP 完成标志措辞修订没有明确触发点

**问题**：ADR-021 写 ROADMAP “证明”措辞需由另一个 L1 修订会话同步；但任务清单没有安排何时触发。T-2.13 只更新 ROADMAP 记录段，不改完成标志。若一直不处理，阶段 2 验收会拿旧 ROADMAP 文本和新 ADR-021 口径并存。
**指向**：ADR-021 后果 `:447-448`，T-2.13 ROADMAP 更新 `:1584-1587`。
**建议路径**：v1.0 加一个“跨边界提醒”：T-2.1 merge 后作者另开 L1 doc 修订，或在 T-2.13 明确只可记录，不可改完成标志；验收报告需引用 ADR-021 作为实际口径。

## 6. 5+2 阶段 2 启动闸门落地核对（专项）

逐条评估 7 项闸门是否充分内化到对应任务：

| 闸门 | 类型 | 归属任务 | 草稿落地 | 评估 |
|---|---|---|---|---|
| C1 本体最小契约 | 硬 | T-2.1 ADR-016 + T-2.2 schema | character / location / relation / state path / clocks / Chapter/Act 都进了 ADR + schema | **部分字面化**：范围充分，但 state path 与 gold、不破旧 schema、ontology envelope 三处会卡执行，见 🔴3.1/3.2 与 🟡4.2。 |
| C3 R 项 cleanup | 硬 | T-2.0（R2/R3/R4）+ T-2.4（R8）+ T-2.11（R7） | R2/R3/R4/R8/R7 都有任务 | **部分充分**：R4 的 `location_candidates` 未贯穿 scene context，且 T-2.0/T-2.11 边界冲突，见 🔴3.3、🟡4.1。 |
| U-GPT-1 ADR-009 第二层拆 2A/2B | 硬 | T-2.1 ADR-021 + T-2.7 validator | ADR 口径、N=100、bounded symbolic 都写入 | **部分充分**：不再写严格证明是对的，但 2A condition-aware 目标与启发式实现不匹配，ROADMAP 文本修订也没有触发点。 |
| U-GPT-4 baseline 协议 | 硬 | T-2.1 ADR-020 + T-2.9 协议文档 | N=15、重试、分子分母、机械失败、AI 判官维度都写入 | **基本充分**：协议文档足够启动；缺 AI judge runner 与成本口径小矛盾，见 🟡4.8 / 🟢5.2。 |
| U-GPT-5 角色槽位持久化 | 硬 | T-2.1 ADR-019 + T-2.2 schema generation_trace.slot_assignments | concrete `character_refs` + `generation_trace.slot_assignments` | **基本充分**：决策内化到位；需随 🔴3.2 解决 generation_trace 增量的版本兼容。 |
| U-CL-4 Chapter/Act schema | 强建议 | T-2.1 ADR-016 + T-2.2 chapter.schema.json | chapter schema + ontology `chapters: []` | **充分到起步级**：前移完成；空数组起步可接受，但后续 fixture/scene_anchor 如何挂 chapter 可在 T-2.6/T-2.13 记录。 |
| C5 开源剥离边界 | 强建议 | T-2.10 sidecar | `OPEN_SOURCE_CARVE_OUT_INDEX.md` 起步 | **基本充分**：覆盖 fixture / 资产 / provider；可顺手补新增 scene prompt 子包和未来 schema fixtures。 |

## 7. PZ 反思 §3/§4 拍板项落地核对（专项）

| 拍板项 | 归属任务 | 草稿落地 | 评估 |
|---|---|---|---|
| 系统时间双轨（world.scene_count + world.long_rest_count） | T-2.1 ADR-016 + T-2.2 ontology | ADR-016 与 T-2.2 `system_time` | **充分**，但 state path 表需兼容 `world.scene_count` 作为状态路径。 |
| 时钟三类（world / faction / environmental） | T-2.1 ADR-017 + T-2.2 clock.schema.json | `scope` enum + `clocks: []` | **充分**。 |
| advance_rule 默认仅 event_based | T-2.1 ADR-017 + T-2.2 enum | `every_n_scenes` / `on_long_rest` / `on_faction_action` / `on_player_choice` | **基本充分**：枚举是 event-based 子类；建议 SCHEMA_v0.3 明说“不存在 `time_based`”。 |
| narrative_weight 三档（core/minor/context_only） | T-2.1 ADR-018 + T-2.2 character.schema.json + T-2.5 prompt 模板 | enum + prompt 过滤规则 | **充分**，但关系对象的 `from/to` vs 嵌入 character relations 形态需在 T-2.2 明确。 |
| 时钟边界软上限（ticks_total ≤ 20 / 同时活跃 ≤ 10） | T-2.1 ADR-017 + T-2.2 schema maximum + T-2.7 实测倒推 | `ticks_total maximum 20` + ADR v0.2 倒推 | **部分充分**：单 clock 上限落地；“同时活跃 ≤10”没有 schema/test/validator 检查点。 |
| dramatic_triggers 字段集 | T-2.1 ADR-016 + T-2.2 character.schema.json | `{trait, when, how, priority?, cooldown_scenes?}` | **部分充分**：字段落地；首版空数组会让 T-2.5 无实证样本，至少需 SCHEMA_v0.3 或 test fixture 给 1-2 个示例。 |

## 8. ABC 闭环落地核对（专项）

| 检查项 | 评估 |
|---|---|
| §1.5 全局 ABC 闭环描述完整性 | **基本充分**：三阶段、L2 验收、merge 硬规则、routine 边界都清楚。 |
| 13 个 L3 prompt 末尾 ABC 段一致性 | **部分充分**：大多数一致；T-2.1 残留“等作者 commit it”必须删；T-2.3 无 prompt 属 placeholder 需说明“12 个 prompt”。 |
| A 阶段 PR 流程（base=main, head=worktree 分支）可执行性 | **基本充分**：每段都要求 PR；但顶部旧句“commit + push 即可”容易弱化 PR，v1.0 可统一措辞。 |
| B 阶段引用 REVIEW_PROMPT_CODE_GPT.md（commit `8842c43`）+ report 落 `/docs/reviews/_targets/T-X.X_review_<topic>.md` 是否能落地 | **有漏点**：模板自身输出路径不是 `_targets`，见 🟡4.3。 |
| C 阶段“追加 commit 到原 PR（不开新 PR）”的可执行性 | **充分**：规则明确。 |
| L2 验收闭环 + PR merge 硬规则的明示度 | **充分**：§1.5 和每段末尾都明示。 |
| routine 仅串联 A 阶段、不跨 B/C 验收的描述清晰度 | **充分**：§1.5.4、§6、§9 重复强调，足够防 routine 抢跑 merge。 |

## 9. 任务间一致性核对（专项）

跨任务字段 / 命名 / 接口检查：

- `character_features` / `dramatic_triggers`：T-2.1 / T-2.2 / T-2.5 / T-2.6 名称一致；问题是 T-2.2 起步空 `dramatic_triggers` 缺示例，T-2.5 很难验证 prompt 是否真的使用。
- `narrative_weight`：`core/minor/context_only` 跨 T-2.1 / T-2.2 / T-2.5 一致；需明确 relation 是 character 内嵌还是全局关系表。
- clock 字段：`id / scope / ticks_total / ticks_filled / advance_rule / tick_effects` 基本一致；`tick_effects.effect_op` 与现有 StateEffect 字段 `op` 命名不同，T-2.7 effect 应用器需明示映射。
- state path 命名空间：最大不一致在 `relationship.<character_id>` vs gold 的 `relationship.vellin`；这是 🔴3.1。
- `generation_trace.slot_assignments`：T-2.1 / T-2.2 / T-2.6 大方向一致；但 schema_version 兼容需先解决。
- `SceneGraphContext` 字段集：T-2.5 prompt 写 `faction_clocks`，T-2.6 dataclass 写 `active_clocks`；T-2.0 写 `location_candidates`，T-2.6 写 `location_card`。这两处建议统一。
- scene review 命令：T-2.8 文件名是 `scene_review_cli.py`，但 T-2.12 命令写 `python -m generator.scene_review`。建议统一并加 `--help` smoke test。
- validator 模块命名：现有仓库已有 `validator/graph_check.py`；T-2.7 新建 `graph_validation.py`，需说明是替代、包装还是并存，避免两套 graph validator 口径分裂。

## 10. L2 §10 自评 5 弱点核对

逐条标 ✓ 同意 / ⚠️ 部分同意 / ❌ 反对：

| L2 自评弱点 | 你的判断 | 论据 |
|---|---|---|
| 1. ADR-016 大头 6 条合并立项 | ⚠️ 部分同意 | 6 条同 PR可接受，但 T-2.1 prompt 的 ABC 冲突和 ROADMAP 修订跨边界要先修；不是“必须拆 ADR”的问题。 |
| 2. N=15 场景样本数偏低 | ✓ 同意 | N=15 可作为首轮成本折中，但统计置信区间宽；报告至少要同时给 gross pass rate 与人工接受率。 |
| 3. 2B 抽样 N=100 路径起步无理论依据 | ✓ 同意 | 可以起步，但 T-2.7/T-2.13 要把它写成经验阈值，不要暗示充分证明。 |
| 4. dramatic_triggers 三键 + 两 optional 字段尚未实证 | ✓ 同意 | 字段合理；缺少一两个 seed 示例会让 T-2.5 prompt 测试空转。 |
| 5. Sibling 涌现项目接口不预留 | ❌ 反对作为弱点 | 这是已锁拍板 + ADR-004 极简精神；不预留是正确约束，不应在 v1.0 中为此防御过度。 |

补充弱点（如有）：`schema_version` 后向兼容、relationship state path ID 口径、AI judge runner 缺位、T-2.8/T-2.6 真实依赖漏写，比 §10 原 5 条更可能导致阶段 2 实施卡壳。

## 11. Top 3 你最担心的事

按“如果不处理，阶段 2 最可能在哪里翻车”排序：

1. schema_version bump 把 0.1.1 gold scene 和既有测试打爆，导致 T-2.2 之后所有 validator/prompt 任务在假绿或全红之间摇摆。
2. state path 命名空间从 `relationship.vellin` 悄悄变成 `relationship.char_vellin`，机械预检与 gold standard 互相否定。
3. wave 依赖漏掉 T-2.4/T-2.7，routine 或作者按表推进时让 T-2.6/T-2.8 抢跑，产生 stub、返工和 PR 阻塞。

## 12. 给阶段 2 L2 规划师的修订建议清单（**paste-ready**）

> 作者：把下面 ` ```text` 代码块**整段**复制到新一轮阶段 2 L2 规划师 Claude 会话首条消息。该会话会逐条响应 + 整合产 v1.0。

```text
GPT-5.5 已完成 STAGE_2_TASKS_draft_v0.1.md v0.1.1 评审，报告路径：/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_gpt_critique.md

请你（新一轮阶段 2 L2 规划师）逐条响应 + 整合产 v1.0 草稿。

# 待响应 finding 清单

🔴 CRITICAL（必修，全部）：
3.1 [CONSIST/TEST] T-2.2/T-2.4/T-2.7 — `relationship.<character_id>` 与 gold scene 的 `relationship.vellin`/`relationship.corvan` 不一致，会让 gold standard 过不了；锚点草稿 :352、:530、:690、:706、:1090。
3.2 [SCHEMA/TEST] T-2.2 — `schema_version` bump 至 0.3.0 与 “content/test_scene_v0 保持 0.1.1 且必过”冲突；锚点 :503-515、:550-554、:578、:603。
3.3 [SCOPE] T-2.0/T-2.11 — 模块边界禁止了任务要求修改的 `context_assembler.py` 与 `generate_node.py`；锚点 :250-256、:287-289、:1374-1380、:1408-1410。
3.4 [DEP] T-2.6/T-2.8 — 依赖图漏掉 T-2.4/T-2.7，T-2.6/T-2.8 会抢跑 validator API；锚点 :181-190、:221-223、:922、:1158、:1170。
3.5 [ABC] T-2.1 — A 阶段 “直接 commit+PR” 与 “等作者 commit it” 自相矛盾；锚点 :326-330、:466-474。

🟡 IMPORTANT（建议全修；如某条修起来风险高/不确定，单独提出由作者决定）：
4.1 [CONSIST/GATE] T-2.0/2.5/2.6 — `location_candidates` 未贯穿 scene prompt/context；锚点 :287-288、:763-777、:927-939。
4.2 [CONSIST/SCHEMA] T-2.2 — character/location schema 与当前 `entities[]` 聚合本体的 `id/type` envelope 未对齐；锚点 :527-538、:556-568。
4.3 [ABC] 全局 — B report 路径 `_targets` 与 `REVIEW_PROMPT_CODE_GPT.md` commit 8842c43 模板路径冲突；锚点 :80-82、:311。
4.4 [DOC] T-2.1 — prompt 引用 `/docs/reviews/master_plan/2026-05-03_STAGE_2_TASKS_draft_v0.1.md`，main 不存在且 v1.0 后会过期；锚点 :339、:1615。
4.5 [TEST/SCOPE] T-2.2 — schema 关键任务未授权 `/schema/tests/` 与 `/state/tests/`；锚点 :497-509、:586-592。
4.6 [SCOPE] T-2.5/T-2.9 — 新建 `generator.prompts.scene` 子包但未授权更新 `pyproject.toml` package/package-data；锚点 :743-749、:1234-1238。
4.7 [EDGE/TEST] T-2.7 — 2A condition-aware 目标与启发式实现不匹配；锚点 :437、:1037-1041、:1094-1098。
4.8 [EDGE/TEST] T-2.12 — `AI_JUDGE_REPORT.md` 没有 runner 负责生成；锚点 :1201-1203、:1281-1283、:1481-1487。
4.9 [CONSIST] T-2.5/T-2.6 — skeleton edges 没写清如何约束 fill 阶段 target_node_id；锚点 :784-818、:916-924。
4.10 [EDGE] T-2.11 — cost reconcile 缺 record_id 串联，且失败一律 0 成本过度乐观；锚点 :1391-1402、:1408-1410。

🟢 NICE（默认跳过；如有 1–2 条极简单的可顺手修）：
5.1 §11 — “全部 12 个 L3 prompt”与 13 个编号槽位口径不一致；锚点 :230、:1664。
5.2 T-2.1/T-2.12 — N=15 / N=20 成本估算前后不一致；锚点 :425、:1476。
5.3 T-2.10 — 纯文档任务完成标志仍要求“测试输出”；锚点 :1351-1356。
5.4 T-2.9/T-2.13 — ROADMAP “证明”措辞修订没有明确触发点；锚点 :447-448、:1584-1587。

# 响应纪律

- 对每条 finding 标 ✅ 同意 / ⚠️ 部分同意 / ❌ 反对（引 ADR / synthesis / R 项 / 实测数据论证）
- ✅ 同意的：直接修订草稿 v0.1.1 → 产 v1.0；落到 `/docs/reviews/master_plan/2026-05-XX_STAGE_2_TASKS_v1.0_draft.md`（仍不进 /docs/STAGE_2_TASKS.md，那是 [B-author-gate] 由作者另起会话落）
- ❌ 反对的：明确论据，不修订
- ⚠️ 部分同意的：写出修订方案，不修订文件，让作者拍板
- 跨边界（修需动 ROADMAP / DECISIONS / SCHEMA_v0.x.md / 任何代码）→ 不要修；改成“建议作者另开会话处理”

# 不要做的事

- 不要 disable 测试 / 跳过验证
- 不要修改 ADR-001~015 / synthesis / Round 5 闸门内容 / PZ 反思拍板项
- 不要重写整段草稿
- 不要替作者拍板 §9 开放决策
- 不要因“原 L2 写的当然对”而手松；本轮就是抓 self-confirmation bias

# 完成报告

- v1.0 草稿路径
- 已修 finding + 论据
- ⚠️ 部分同意 / ❌ 反对的清单 + 论据
- 跨边界项清单（待作者另开会话处理）
- 是否仍建议直接产 v1.0 commit 进 /docs/STAGE_2_TASKS.md（综合 GPT 评审后）
```

## 13. 评审范围外的观察（可忽略）

当前评审对象文件不在 main 工作树的 `/docs/reviews/master_plan/`，而在 `.claude/worktrees/ecstatic-lewin-6aee3c/docs/reviews/master_plan/`。这不影响本次 critique，但 v1.0 整合前要确认作者/规划师会话拿到的是同一份 v0.1.1。
