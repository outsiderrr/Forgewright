# ADR-039 首版核心闭环（P-A + P-B）L2 任务拆解 v0.1

> **性质**：L2 整合规划师产物（ADR-039 写作提示词包转向 · 首版收窄范围的施工拆解）。
> **状态**：草稿——待作者按 governance §5 起 cross-LLM critique（可复用 [/docs/REVIEW_PROMPT_L2_STAGE_TASKS.md](../../REVIEW_PROMPT_L2_STAGE_TASKS.md)）→ 消化 → 作者明示授权后，T-3P 系列进 L3 执行 + STAGE_3_TASKS.md 增补修订。
> **日期**：2026-06-29 · **产出方**：L2 整合规划师会话（worktree claude/pa-pb-l2-plan）
> **规划基线**：main `ec834cc`（ADR-039 + ADR-040 已落地；`generator/multipass/` 结构层完整）。
> **上游拍板**：ADR-039 五点拍板 + 两叉口裁决（2026-06-21）；ADR-040（2026-06-23）；本拆解两岔口作者拍板（2026-06-29）：回流格式 = **轻量标签 markdown**（单一格式单一解析器）；回流交付 = **存成文件 + CLI 摄入**。

---

## 0. TL;DR

把 ADR-039 首版核心闭环拆成 **4 个 L3 任务（T-3P 系列，与 T-3X 同款并列主线命名）**：

```
T-3P-0  确定性拆拍器 + 结构锁定/回流格式契约定稿   （软地基，先行独立 ABC）
   ↓ merge 后
T-3P-1  P-A 写作提示词包渲染器（0 LLM）   ∥   T-3P-2  P-B 回流解析 + 确定性合并 + 硬报错
   ↓ 两者 merge 后
T-3P-3  回流验收管线接线 + E2E 闭环实测（lucy 正反两例）
```

四个任务**全部不触 `/schema`**（判定依据见 §7）。跨场景连续性只做便宜版（§5.4）。P-C / P-D / P-E 不在本拆解内（ADR-039 决策四）。

---

## 1. 范围与不做

**做**（= ADR-039 决策四 + 后果·新工作·首版）：

- **P-A 提示词渲染器**：结构骨架 → 每场景一份写作提示词包（结构锁定 + 格式契约 + 文风指南 + 连续性摘要），含**确定性拆拍器**（ADR-039 决策三：beats 拆拍从 LLM 涌现改为确定性结构产物，前置于 P-A/P-B）。
- **P-B 回流合并器（新模块）**：解析编剧回流文本 → 按 node_id + 显式选项序号对齐 → 确定性合并 → 硬报错（key 对不上 / 节点缺失 / 选项数不符即退回）→ 复用三层校验器验收（`generation_source="human"`）→ 落地可玩。

**不做**（写进每个 L3 prompt 的硬边界）：

- ❌ P-C（幕级打包 / 手动 loop）/ P-D（费工连续性：NPC 状态增量持久化 + 台词级 callback）/ P-E（文风资产完整重打包）——推到核心闭环验证后（ADR-039 决策四）。
- ❌ 自建正文生成——任何在本仓库用 LLM 写 narration / dialogue / option.text 的代码路径（ADR-039 决策一）。
- ❌ 动 `/schema`（ADR-039 schema 影响判定；见 §7）。
- ❌ 动 `/engine`（运行时 0 LLM；ADR-002/004）。
- ❌ 审阅 UI 改造（回流交付走文件 + CLI，作者 2026-06-29 拍板；UI 看板归 P-C 方向）。

---

## 2. 作者已拍板的设计岔口（2026-06-29，本拆解会话 AskUserQuestion）

| 岔口 | 拍板 | 影响 |
|---|---|---|
| P-B 回流文本格式 | **轻量标签 markdown**（单一格式；不做 JSON 严格模式） | P-A 输出格式段 + P-B 解析器只实现一种语法（§4）；与提案 §6 倾向一致 |
| 编剧回流交付形态 | **存成文件 + CLI 摄入**（`python -m generator.promptpack ingest …`） | P-B 是纯 CLI 工具；退回单落文件可留档重跑；不动 tools/review_ui |

---

## 3. 复用资产事实清单（四路只读探查 2026-06-29 复核，带 文件:行号）

> 以下事实是任务边界与"复用 vs 新写"判断的证据基线；L3 施工会话可直接引用。

### 3.1 结构骨架（P-A 的输入面）

- Pass1 产物 = `design` dict：`contract / topology / skeletons / proses / beats / ends`（`generator/multipass/engine.py:198,224,414-417`）；落盘 `design.json`（engine.py:599-632）。
- **拆拍现状 = LLM 涌现**：拓扑 pass 决定哪段是 beats 链 + 链带哪些 reveals；引擎按 `MAX_REVEALS_PER_BEAT_CALL=4` 确定性分块（engine.py:55-56）；**chunk 内拆几拍 + 每拍揭哪条线索完全由 LLM 决定**（beat_pacing.py:22-34；schema 仅约束 2-3 拍，beat_pacing.py:115-118），且 `design["beats"]` 无"本拍揭哪条线索"记录——这正是 ADR-039 决策三要新写确定性拆拍器的原因。
- 结构/正文槽位边界：结构信息只在 design sidecar（topology/skeletons）；成品图中 LLM 手笔只剩 `narration` / `dialogue[].line` / `options[].text` 三类正文槽（engine/assemble 综合，见 assemble.py:2-5 docstring）。

### 3.2 确定性装配（P-B 的复用半 + 语义相反半）

- `assemble_graph`（assemble.py:70-88）：机械字段全由代码填（option_id / target_node_id / condition=None / effects=[] / unavailable_behavior="hide" / speaker_ref=None + dialogue[]，ADR-040 不变量硬编码于 :135,151,171）。
- **可直接复用**：`_normalize_line`（:18-35，整句包裹引号归一为裸正文）、`_dialogue_entries`（:38-50，行数组→[{speaker_ref,line}]，图级单说话人）、`_mk_option`（:59-67）、`entry_graph_node_id` / target_map（:53-56,96，beats 链入口 = `{pid}_b1`）。
- **语义相反、必须新写**：对齐 = 位置索引 + 12 条静默/告警容错（截断、回退第一出边、缺数据照样产空节点等，assemble.py:103-175 逐条清单见侦察报告）——P-B 要的是 node_id + 序号主键对齐 + 硬报错，**不改 assemble.py，新写对齐层**。

### 3.3 验收通路（P-B 直接可用，0 改动）

- 三层聚合 `validator.validate(graph_dict) -> ValidationReport`（validator/__init__.py:78-96；输入 dict）。
- 机械预检 `validate_graph_mechanical(graph, ontology=…, generation_source="human")`（dialogue_validator.py:330-335）；**human 只豁免 monotonic**（state_path_validator.py:110-111 + dialogue_validator.py:134-150），其余照跑。
- AP 预检 `detect_anti_patterns(node)`（anti_pattern_detector.py:219；覆盖 narration / options[].text / dialogue[].line 的 AP-7/8/10；未被 `__init__` 导出，按 engine.py:475 先例直接 import）。
- ADR-040 闭合校验已在一致性层（consistency_check.py:121-139）。
- **schema 不用动的关键证据**：`generation_trace.source` enum 已含 `"human"`（node.schema.json:96、option.schema.json:50）。
- 现成对偶测试模板：`generator/multipass/tests/test_reassemble_lucy_adr040.py`（真实数据重装配→三层全过）；真实 fixture 在 `generator/experiments/multipass_structure/2026-06-11_convfix/lucy/`（design.json / scene.json / scene.md 在盘）。

### 3.4 文风/格式资产（P-A pack 内容来源；只做 pack 内最小重述，非 P-E）

- `ROLE_RULES_TEXT` 三分类契约（role_rules.py:12-53）——约 87% 是对"文本本身"的要求，天然是编剧格式说明书。
- AP 黑名单分层（anti_pattern_blacklist.py:8-15）：`UNIVERSAL_AP_IDS=(AP-2,3,4,6,9)` 普适层 + `BAIMIAO_PRESET_AP_IDS=(AP-1,5)` 白描预设层；AP-7/8/10 程序化检测不进提示词。
- 白描预设三件套（prompts/style/presets/baimiao.py:16-45）+ 锚点库 A1-A18（prompts/style/anchors_v1.json；全部 project_generated 版权干净；含防搬运守卫文案 style/__init__.py:40-43）。
- 文本量化契约散落点（P-A pack 须收录）：choice narration 250-400 字 / option ≤25 字（pass2_prose.py:47,57）；beat narration 60-120 字 / 接话 ≤20 字自然口语（beat_pacing.py:30,42-49）；end 80-200 字收束（pass2_prose.py:233）；人称约定 D 两套并存（pass2_prose.py:59-60）；承接规则（beat_pacing.py:37-38）。

### 3.5 便宜版连续性（P-A 注入；不建新机制）

- `prior_scene_summaries` 全链路现成且**无 multipass 依赖**：sidecar 读取 `read_summary_sidecar`（scene_summary_writer.py:245-278）、封顶 5 + 幕边界保留 `truncate_prior_scene_summaries`（context_assembler.py:479-549）、渲染块 `render_prior_scene_summaries_block`（:552-581）。
- "一行 NPC 状态摘要"**无现成机器载体**；最近字段 = `scene_spec["character_state"]`（作者手写自由文本，已注入结构 pass，pass1_skeleton.py:173）——便宜版 = 直接透传该字段 + prior summaries 渲染块。机器派生的 NPC 状态数值属 P-D，明确不做。

### 3.6 IO / CLI 惯例（新 CLI 对齐）

- argparse + `main(argv) -> int` + `python -m generator.<module>`；kebab-case 长 flag；CLI > env > default；退出码 2=输入错 / 1=运行失败（batch_scheduler.py:925-1095、version_recorder.py:384-459 等）。
- 落盘：`content/<scene_dir>/scene.json` + sidecar 同目录（`scene.version.json` / `scene.deps.json` / `scene.summary.json`）；写入顺序 "write scene → assign chapter → write deps → record version" 不可协商（generate_scene.py:579-597）。
- `version_recorder.record_version` 的 `generation_method` 白名单 = `{batch_scheduler, manual_edit, regenerate, playtest_fix}`（version_recorder.py:59-67）——T-3P-3 需扩一枚举值（§8 开放项 1）。

---

## 4. 回流格式契约 v1（规范段；T-3P-0 落成代码常量，P-A/P-B 共同实现）

> 作者 2026-06-29 拍板轻量标签 markdown 单一格式。本节是 v1 规范草案；T-3P-0 施工时以 `generator/promptpack/format_spec.py` 落成单一真相源（常量 + 错误分类），文字与代码不一致时以代码 + 其测试为准。

### 4.1 标签语法

```
[node: <node_id>]          ← node_id = 成品图节点 id；beats 拍用锁定微节点 id（{pid}_b{i}，与 assemble 的 entry_graph_node_id 一致）
narration: <旁白正文>       ← 必填；值 = 冒号后至下一个 key 行 / 下一个 [node:] 之间全部文本（允许多行）
dialogue:                  ← 可选；0 行合法
  - <该 NPC 的一句话，裸正文不带引号包裹>
  - <第二句>
options:                   ← 仅 choice 节点；序号必须 1..N 连续完整，N = 锁定选项数
  1: <玩家第一人称台词>
  2: <…>
continue: <接话>            ← 仅 beats 拍（单选项）；end 节点无 options / continue
```

- 节点类别 → 必交 key：**choice** = narration + options（数量精确）[+ dialogue 可选]；**beats 拍** = narration + continue [+ dialogue 可选]；**end** = narration [+ dialogue 0-2 行可选]。
- dialogue 行说话人归属：**v1 = 图级单说话人**（锁定配置 `speaker_ref`，与 assemble.py `_dialogue_entries` 现状一致）；编剧不写说话人名。多 NPC 场景归属见 §8 开放项 3。
- 编剧不得增删节点、不得改 node_id、不得增删选项序号——提示词包"输出格式"段原样声明。
- **图级运行配置随 design 落盘**（评审修正）：graph_id / scene_anchor / speaker_ref / character_refs 现状只在内存 `SceneRunConfig`（engine.py:74-77）从不落盘，而 P-B 产 scene.json 的图级字段全靠它——T-3P-0 的 structure-only 模式把 `design["run_config"]` 一并写进 design.json，P-A/P-B 从同一文件读，不各收配置参数。
- **IO envelope 冻结 + 共享 loader**（critique F-3）：design.json 沿现有 wrapper（顶层 `{design, call_metas, …}`，消费者读 `payload["design"]`）；spec 文件沿现有 `{config, spec}` wrapper（读 `payload["spec"]`，config 段与 design.run_config 同源同形、loader cross-check 一致性）。T-3P-0 落 `promptpack/io.py` 两个 loader（`load_design_artifact` / `load_scene_spec`），P1 两任务只准经 loader 读输入。
- **CLI 约定**：v1 各工具用独立模块入口（`python -m generator.promptpack.render_pack` / `…promptpack.ingest`），不建共享 `__main__.py`（P1 两任务并行不碰同一文件、可独立 revert）；退出码三态 = 0 成功 / 1 回流拒收（格式 E 类或验收 fail）/ 2 用法・输入错误。structure-only 的作者可用入口 = `run_multipass_scene.py --structure-only`（critique F-2）。**终端播放入口 = `python -m engine <scene.json>`**（`engine/__main__.py`；`python -m engine.player` 会静默空跑——critique F-1）。

### 4.2 硬报错分类（收集全清单后一次退回，不 fail-fast）

| 代码 | 含义 |
|---|---|
| E1 missing_node | 锁定骨架有、回流缺的节点 |
| E2 unknown_node | 回流有、锁定骨架没有的节点（结构已锁定，不接受新增） |
| E3 duplicate_node | 同一 node_id 出现两个块 |
| E4 option_count_mismatch | 选项序号缺号 / 多号 / 不连续 / 与锁定数不符 |
| E5 missing_field | 必填 key 缺失（narration / continue） |
| E6 unknown_key | 不认识的字段 key（含 end 节点出现 options 等错位） |
| E7 empty_text | key 在但正文为空 |
| E8 parse_error | 无法归属任何 key 的行 |

边界判定（format_spec 落码时逐 case 定死；样张覆盖）：`options:` 块**整体缺失** = E5（必填块缺失）；块在但序号缺 / 多 / 不连续 = E4；不该出现的块（如 end 带 options）= E6。

任一 E → **不产 scene.json**；退回单 = console 摘要 + `<reply>.reject.md` 落盘（逐条：代码 / 节点 / 期望 vs 实际 / 给编剧的一句话修改指引）。

---

## 5. 任务拆解（T-3P 系列）

> 命名沿 T-3X 先例：与 T-3 主线编号并列的系列标签，不是 T-3.6a 式子任务。四任务**每个都有独立规格需求 → 各走完整 ABC**（governance §10.6 判定：T-3P-0 改生成器输出契约 = 软地基单审；T-3P-1/2/3 各为独立新模块/验收）。B 报告落 `/docs/reviews/<ISO_DATE>_T-3P-X_<topic>_review.md` 并 push main（governance §10 第 7 条）。paste-ready prompt 文件：[/docs/prompts/stage_3/T-3P-0.md](../../prompts/stage_3/T-3P-0.md) ~ [T-3P-3.md](../../prompts/stage_3/T-3P-3.md)。

### 5.1 T-3P-0 确定性拆拍器 + 结构锁定 / 回流格式契约定稿

| 项 | 内容 |
|---|---|
| 性质 | **软地基（改生成器输出契约），先行独立 ABC**（governance §10.7；完整 ABC——默认模式，非 §10.6 三特殊模式） |
| 模块边界 | 允许：`/generator/multipass/`（新建 beat_split.py + engine.py 加 structure-only 模式 + **assemble.py 仅限新增公开别名不改行为**）、`/generator/scripts/run_multipass_scene.py`（**仅限**新增 `--structure-only` flag，critique F-2）、`/generator/promptpack/`（新建包：format_spec.py + io.py + `__init__.py`）、`/generator/version_recorder.py`（**仅限** generation_method 新增 `"writer_ingest"` 值）、两处 tests、fixture/样例目录。严禁：`/schema` `/validator` `/engine` `/state` `/tools`；**不改 render.py** |
| 内容 A | **确定性拆拍器**：输入 topology beats 节点（node_id / reveals[] / next）→ 输出锁定拆拍计划 `beats_plan`：`[{beat_id: "{pid}_b{i}", reveals: […], is_last}]`。不变量：确定性（同输入同输出）、每条 reveal 恰好落一拍、保序、id 与 assemble `entry_graph_node_id` 约定一致。拆拍数值规则（默认每拍 ≤2 条、拍数下限）由施工会话定 + 作者按样例验收 |
| 内容 B | **structure-only 运行模式**：`run_multipass_scene` 增开关——只跑 contract + topology + skeleton 三类 LLM 调用 + 确定性拆拍，**跳过 prose/beats/end 正文调用**（ADR-039 决策五：Pass 2 退役为生成路径，代码不删）；design 增**两个 key**：`beats_plan = {pid: [BeatSlot]}`（dict 按链分组——lucy 有 5 条链，载体形态在此锁死）+ `run_config = {graph_id, scene_anchor, speaker_ref, character_refs, npc_name}`（评审修正：这些字段现状只在内存 `SceneRunConfig` 从不落盘，P-B 产 scene.json 图级字段全靠它）；此模式不产 scene.json（无正文可装配） |
| 内容 C | **回流格式契约 v1 + IO envelope/CLI/退出码约定落成代码**：`format_spec.py` = 标签语法常量 + 节点类别必交 key 表 + E1-E8 逐 case 定死（§4 为草案，代码为准，格式变化需回样张同步）；`io.py` = `load_design_artifact` / `load_scene_spec` 两 loader（wrapper 读取 + legacy 报错 + config↔run_config cross-check，critique F-3）；独立模块入口约定（不建共享 `__main__.py`）+ 退出码三态 + `--structure-only` CLI 暴露（critique F-2） |
| 内容 D | **version_recorder 枚举扩值**（`"writer_ingest"`——"给别人定规矩"归地基一次浇好，T-3P-3 只消费；governance §2 carve-out 校准条款论证：该值被后续所有回流落地依赖）+ **assemble 复用符号公共化**（normalize_line / dialogue_entries / mk_option 加公开别名，T-3P-2 不引跨包私有符号） |
| 内容 E | **共用 fixture**：合成 augmented lucy design.json（legacy design + beats_plan + run_config）落固定路径——T-3P-1/2/3 golden 全部引用这一份（评审修正：否则 P1 两会话各自现场合成、字节级不一致） |
| 完成标准 | 拆拍器单测（确定性 / 覆盖 / 保序 / id）全过；structure-only 模式 smoke（0 正文调用、design 含两 key）；version_recorder 既有值回归测试；augmented fixture + 拆拍样例 + 格式契约样张落盘；全仓测试基线 0 regression |
| **concrete 验收形态** | ① 拆拍样例对照 markdown（lucy `soft_private_line` 8 条线索：旧 LLM 涌现 6 拍 vs 新确定性拆拍、每拍揭哪条），作者按"这样分拍玩起来对不对"批效果，不审代码；② **格式契约样张 + 假想退回单样张**（评审修正：格式契约是 P-B 命门，作者在 P0 就以 concrete 形态审过再冻结，不等 P1 才第一次看见） |
| schema-touch | **不动**。分拍微节点本就合法（ADR-038 决策四）；beats_plan / run_config 只进 design sidecar（generator 侧产物，非 /schema 治理对象） |

### 5.2 T-3P-1 P-A 写作提示词包渲染器

| 项 | 内容 |
|---|---|
| 性质 | 独立 ABC；依赖 T-3P-0 merge；与 T-3P-2 并行 |
| 模块边界 | 允许：`/generator/promptpack/render_pack.py`（新建）+ `/generator/promptpack/tests/`（format_spec / `__init__.py` 归 T-3P-0 只读）。严禁：`/schema` `/validator` `/engine` `/state` `/tools`；不改 multipass 引擎（只读其 design.json 产物）；**0 LLM 调用**（纯确定性渲染，无 budget 需求） |
| 输入 | design.json（须含 T-3P-0 落盘的 beats_plan + **run_config** 两 key——图级配置从 design 读、不另收参数；legacy design 缺 key 报错）+ scene_spec（background / character_state；lucy 实物 `generator/experiments/multipass_structure/specs/lucy.json`）+ 可选 `--summaries <sidecar 路径…>` |
| 输出 | `<graph_id>.pack.md`——整场一个文件，编剧唯一交付物 |
| pack 结构 | ① 任务头（结构锁定声明）② 场景契约（player_goal / npc_goal / npc_fear / 禁则，取自 design.contract）③ 故事至此（prior summaries 渲染块复用 + character_state 一行透传；§3.5）④ 逐节点树序填空单（借鉴 render.py `_walk` 树序）：choice = function/situation/choice_pressure/reveals/hides + 各选项〔intent〕+ 去向；beats 链 = 每拍"本拍揭露"清单 + 承接规则；end = 收束要求 ⑤ 文风段（role_rules 编剧版最小重述 + 普适 AP(2,3,4,6,9) + 白描预设(AP-1,5 + PROSE_STYLE_RULES) + 锚点 few-shot 带防搬运守卫 + §3.4 量化契约）⑥ 输出格式段（由 format_spec 生成，含每节点应交 key 清单） |
| CLI | 独立模块入口 `python -m generator.promptpack.render_pack`（T-3P-0 CLI 约定；不建共享 `__main__.py`，与 T-3P-2 并行零文件交叉、可独立 revert） |
| 完成标准 | golden-file 测试（**T-3P-0 augmented lucy fixture**，不自行合成）；段落齐全性 / 选项序号去向正确性 / beats_plan 对齐测试；确定性测试；全仓 0 regression |
| **concrete 验收形态** | lucy 整场真 pack 渲染落盘，作者通读，按"一个编剧拿到这个能不能直接开写、会不会写崩结构"判效果 |
| schema-touch | 不动 |
| 文风范围红线 | 只做 pack 需要的最小重述；14 维 taxonomy / judge / 完整资产重打包 = P-E，不做 |

### 5.3 T-3P-2 P-B 回流解析 + 确定性合并 + 硬报错

| 项 | 内容 |
|---|---|
| 性质 | 独立 ABC；依赖 T-3P-0 merge；与 T-3P-1 并行 |
| 模块边界 | 允许：`/generator/promptpack/ingest.py`（新建：parser + aligner + merger + CLI）、`/generator/promptpack/tests/`（format_spec / `__init__.py` 归 T-3P-0 只读）。严禁：`/schema` `/validator` `/engine` `/state` `/tools`；**不改 assemble.py**（只 import T-3P-0 公共化的公开别名，不引跨包私有符号；若需行为变化即违规，停下报告）；0 LLM |
| 解析 | format_spec 语法 → `{node_id: {narration, dialogue[], options{序号:text} | continue}}`；strict；**收集全部错误再退回**（E1-E8） |
| 对齐 | 对锁定骨架（design.json 的 topology/skeletons/beats_plan/**run_config**——图级字段从 run_config 读，不另收参数）做全键精确对齐：节点集合相等、choice 选项序号 1..N 精确、beats 每拍 continue 必有 |
| 合并 | 复用 assemble 机械半（mk_option / target_map / normalize_line / dialogue_entries 公开别名）→ scene.json（schema_version "0.1.1"；ADR-040：narration=纯旁白 + dialogue[] + 节点 speaker_ref=null）；node + option 级 `generation_trace.source="human"`；确定性 = 同 reply + 同 design（含 run_config）→ 逐字节相同 |
| 退回单 | console 摘要 + `<reply>.reject.md`（§4.2 形态）；任一 E 不产 scene.json |
| CLI | 独立模块入口 `python -m generator.promptpack.ingest <design.json> <reply.md> [--out <scene.json>]`（T-3P-0 CLI 约定 + 退出码三态） |
| 完成标准 | E1-E8 错误矩阵逐类测试；golden merge 基于 **T-3P-0 augmented fixture**（golden 允许占位文本——只验格式/对齐/机械正确性；旧 lucy 正文按 6 拍写、与新拆拍无机械映射，作者演示物的 beats 部分手工微改写）+ 与 `test_reassemble_lucy_adr040.py` 对偶的"合并产物过三层校验"测试；确定性测试；全仓 0 regression |
| **concrete 验收形态** | 一次真实合并 path 演示（reply.md → scene.json diff 可读）+ 一张真实退回单（构造 3+ 种错的坏回流），作者按"编剧拿到退回单知不知道怎么改"判效果 |
| schema-touch | 不动（generation_trace.source="human" 现行合法，§3.3） |

### 5.4 T-3P-3 回流验收管线接线 + E2E 闭环实测

| 项 | 内容 |
|---|---|
| 性质 | 独立 ABC（实测变体，参 T-3.10 先例：A 阶段含实测 + 报告）；依赖 T-3P-1 + T-3P-2 merge |
| 模块边界 | 允许（generator/CLAUDE.md 默认禁区的本任务显式豁免清单，仿阶段 1.5 例外体例）：`/generator/promptpack/`（acceptance.py + ingest CLI 接线 + tests）、`content/_e2e_writer_loop/`（E2E 落地**隔离目录**）、`/docs/reviews/master_plan/`（仅新增 E2E 报告）、E2E 中间产物目录。严禁：`/schema` `/state` `/tools`；`/validator` 只读调用；`/engine` 只读运行；**不改任何共享模块**（writer_ingest 枚举已由 T-3P-0 浇好，只消费） |
| 验收管线 | ingest 成功后自动跑：`validate(graph)`（三层）+ `validate_graph_mechanical(graph, ontology, generation_source="human")` + 逐节点 `detect_anti_patterns`（AP flag 记录进报告不拦截，沿 multipass 引擎同款处理）→ 验收报告 `<scene>.acceptance.md` + `.json`（pass/fail + 分层 issue 清单）。**如实边界**（评审修正，写进 E2E 报告）：路线 A 下编剧触不到结构字段，语义层验收闸守的是结构完整性/本体一致性（防管线 bug、防绕过 P-B 手改、防配置错），对编剧手笔的把关主要在格式层 E1-E8 + AP 记录——这是锁结构的设计后果，不许夸大成"能拦编剧写坏的文字" |
| 落地 | `--land` = 写 scene.json + `record_version(generation_method="writer_ingest")`；E2E 落地目标 = `content/_e2e_writer_loop/` 隔离目录（fixture 实为 LLM 旧正文的人工改写，挂 human 标只是管线角色标记——审计诚实起见不入正式内容库，报告写明来源；见 §8 确认项 7）；deps sidecar 对 human 回流暂不写（§8 确认项 2） |
| E2E 实测（A 阶段必做） | lucy 场景：①（好回流）按 T-3P-0 augmented fixture 的新 beats_plan 手工改写 lucy 正文 → render 产 pack 留档 → ingest 合并 → 验收全过 → `--land content/_e2e_writer_loop/` → **`python -m engine <scene.json>`** 终端玩通（critique F-1 修正命令；报告粘贴实际命令与关键输出片段防空跑）；②（坏回流，两层分开、如实标注性质）格式层 = 构造 3+ 类 E 错误 → 正确退回单（对编剧错误的真实拦截面）；语义层 = 直接构造非法 graph 喂验收管线（**技术负路径测试**，非编剧回流模拟——编剧触不到这些字段）→ 正确 fail；③ E2E 报告落 `/docs/reviews/master_plan/`（含如实边界说明 + ROADMAP ADR-039 新完成口径逐条判定证据） |
| 测试 | 验收管线单测（三层 fail / 机械 fail human 豁免与否各一 / AP 不拦截 / pass 全绿）；**格式段↔解析器对偶测试**（T-3P-1 pack 输出格式段的示例块必须能被 T-3P-2 parser 解析——P1 并行期无法互测，落本任务机器闭环）；落地 + version sidecar 测试 |
| **concrete 验收形态** | 作者本人终端玩通回流场景 + 读坏回流退回单——这就是 ADR-039 重定义的阶段 3 完成标志实证 |
| schema-touch | 不动 |

---

## 6. Wave 依赖图

```
Wave P0（软地基，先行串行落定；ADR-037 §10.7）:
   T-3P-0  拆拍器 + structure-only + 全部共享契约   [软地基；完整 ABC]
   ↓ PR merge 后
Wave P1（并行）:
   T-3P-1  P-A 渲染器        T-3P-2  P-B 解析+合并
   ↓ 两者 PR merge 后
Wave P2（实测）:
   T-3P-3  验收管线 + E2E 闭环实测
```

- 回滚单位 = 依赖闭包（governance §10.6）：P1 两任务互不依赖可单独 revert；T-3P-3 依赖 P1 全部。
- 与 T-3 主线旧任务无依赖交叉：批量调度 / 审阅 UI / 一致性维护等已 merge 资产不动；T-3.10（完成标志实测）的口径已由 ROADMAP ADR-039 重定义段更新，其对 T-3P 系列的承接在 critique 后的 STAGE_3_TASKS 修订里处理（§9）。

---

## 7. schema-touch 判定汇总（ADR-039 红线）

| 任务 | 判定 | 证据 |
|---|---|---|
| T-3P-0 | 不动 | 分拍微节点 schema 本就支持（ADR-038 决策四）；beats_plan 是 generator 侧 design sidecar 字段，design.json 不在 /schema 治理内 |
| T-3P-1 | 不动 | 纯渲染，产物是 markdown |
| T-3P-2 | 不动 | scene.json 形态不变（0.1.1 兼容路径）；`generation_trace.source` enum 已含 "human"（node.schema.json:96 / option.schema.json:50） |
| T-3P-3 | 不动 | validator 只读调用；version sidecar 无 /schema 定义（generator 侧约定） |

**安全阀**（写进每个 prompt）：施工中若发现必须动 `/schema`（或等价语义变更）→ 立即停批 → 报告作者 → 单独 schema-only ABC（ADR-037 §10.7 硬闸；B 阶段见到 /schema diff 直接 🔴 停批）。

---

## 8. 开放项与作者确认项（如实；三项确认项作者已于 2026-06-29 逐条拍板 ✅）

1. **version_recorder 枚举扩值**（已挪入 T-3P-0 地基，评审修正）：`generation_method` Literal 加 `"writer_ingest"`——改共享模块契约，按 governance §2 carve-out 校准条款（被后续所有回流落地依赖）归地基任务单审浇好；不复用 `"manual_edit"` 是为了审计诚实。
2. **【已拍板 ✅ 2026-06-29】deps sidecar 对 human 回流不写**（首版）：`content_dependency_index` 语义是"LLM context assembly trace"（ADR-023），human 回流没有对应生成上下文；后果 = 一致性维护（T-3.7 propagate）对回流场景**不覆盖**，本体变更时回流场景不会被标记重审——这是主动留的盲区，留待有真实编剧反馈后定（可能属 P-D 邻域）。**作者确认接受此盲区**。
3. **dialogue 说话人归属 v1 = 图级单说话人**：与 assemble 现状一致（assemble.py:43 注释）；多 NPC 同场对白的归属标记（如 `- lucy: <line>` 前缀）是格式契约 v2 内容，v1 不做——当前实测场景均为单 NPC。
4. **`scene_spec["character_state"]` 是手写自由文本**：便宜版连续性直接透传；机器派生 NPC 状态数值 = P-D，本拆解不碰（ADR-039 决策四理由①）。
5. **structure-only 模式的 prompt 残留**：骨架 prompt 中若有引用后续正文 pass 的措辞，T-3P-0 施工时顺手核查（只改措辞不改契约；超出即停）。
6. **好回流 fixture 的来源**：lucy 旧正文是按 LLM 6 拍写的，新确定性拆拍拍数不同——T-3P-3 的"完美编剧"fixture 由施工会话手工改写匹配新 beats_plan（这本身就是编剧角色的最小模拟，成本可控）；T-3P-2 的 golden 测试则允许占位文本（只验机械正确性）。
7. **【已拍板 ✅ 2026-06-29】E2E 场景落隔离目录、不入正式内容库**：E2E 的"编剧正文"实为 LLM 旧正文的人工改写，挂 `source="human"` 只是管线角色标记——为审计诚实，落 `content/_e2e_writer_loop/` 隔离目录并在报告写明来源；首个真正入正式库的回流场景等真实编剧/作者手笔。**作者确认此处理**。
8. **【已拍板 ✅ 2026-06-29】量化文风契约收进 P-A pack 做最小重述**：pivot §13.1 把 pass2_prose/beat_pacing 的文本契约（字数/人称约定 D/承接规则）列为 P-E 收编对象；本拆解判定 pack 缺了这些编剧无法开写（附录 A 作者已批样例本就含字数/禁则/锚点），故 P-A 做**最小重述**收录、14 维 taxonomy/judge/完整资产重打包仍归 P-E 推后。**作者确认此划界**。
9. **【如实局限】语义层验收闸对编剧手笔基本恒 pass**：路线 A 下编剧触不到结构字段（speaker_ref 锁定 / condition・effects 代码填 / monotonic 对 human 豁免），三层 + 机械预检守的是结构完整性与本体一致性（防管线 bug / 防绕过 P-B 手改 / 防配置错误）；对编剧错误的真实拦截面 = 格式层 E1-E8 + AP 记录。这是锁结构的设计后果而非缺陷，但 E2E 报告与对外表述不得夸大验收闸的把关能力（已写进 T-3P-3 任务规格）。

---

## 9. 下一步（governance §5 L2 流程）

1. ~~作者对本拆解跑 cross-LLM critique~~ ✅ **已完成（2026-07-02）**：报告 [2026-07-02_pa_pb_breakdown_gpt_critique.md](2026-07-02_pa_pb_breakdown_gpt_critique.md)（main `52ae755`）——F-1 🔴 播放命令空跑 / F-2 🟡 structure-only 缺 CLI 暴露 / F-3 🟡 IO envelope 未冻结 / F-4 🟢 mode 标签术语；§10.6 五问 = 1/2 过、3/4 有条件过、5 不过；事实抽查无造假；决策忠实度无推翻已定案。
2. ~~L2 消化 critique~~ ✅ **已完成（2026-07-02，v0.3）**：F-1~F-4 全部采纳并核实修入（播放命令改 `python -m engine` / T-3P-0 增 `--structure-only` CLI + io.py 两 loader / mode 标签改治理枚举写法）。→ **下一步 = 作者明示授权**（授权后：删 4 份 prompt 元数据表的"待作者授权"行 + 回填授权来源）。
3. 授权后随 PR 落 STAGE_3_TASKS.md 增补（§6 wave 图加 P0-P2 段 + §7 任务表加 T-3P 四行 + §8 prompt 索引四行 + 系列命名规则注；v1.0.3 修订记录）——**L2 文档修订**，经 critique + 作者授权后落（STAGE_X_TASKS 是 L2 产物，不是 L1 fixation 对象）。
4. L3 开工顺序：T-3P-0 →（T-3P-1 ∥ T-3P-2）→ T-3P-3；每任务起手 `执行 T-3P-X` 或"请按 /docs/prompts/stage_3/T-3P-X.md 的指示执行任务。"

---

## 版本

- v0.3（2026-07-02）：消化正式 cross-LLM critique（[2026-07-02_pa_pb_breakdown_gpt_critique.md](2026-07-02_pa_pb_breakdown_gpt_critique.md)，Codex/GPT-5.5，main `52ae755`）。四 finding 全采纳并逐条对代码核实：F-1 🔴 终端播放命令 `python -m engine.player`→`python -m engine <scene.json>`（player.py 无 argv 入口，原命令静默空跑；T-3P-3 两处 + §4/§5.4 修正，E2E 报告须贴实际命令输出）；F-2 🟡 T-3P-0 增 `run_multipass_scene.py --structure-only` CLI 暴露（沿 --topology-only 先例）+ smoke；F-3 🟡 IO envelope 冻结（design.json wrapper 读 `payload["design"]`；spec `{config,spec}` wrapper + config↔run_config cross-check）+ `promptpack/io.py` 两共享 loader，P1 禁自写解析；F-4 🟢 四份 prompt mode 标签改治理枚举写法（ABC 粒度/special mode/B 保留/授权来源四段式）。待作者明示授权。
- v0.2.1（2026-06-29）：作者拍板 §8 三个确认项（deps sidecar 首版不写 / E2E 隔离目录 / 量化契约最小重述进 P-A）✅；critique paste-ready prompt 落 `_prompts/2026-06-29_pa_pb_breakdown_critique.md`（内置 §10.6 五问）。
- v0.2（2026-06-29）：吸收 L2 会话内部三路对抗性预审（决策忠实度 / 治理合规 / 五文件互洽；每路均实地核对 文件:行号）。主要修正：`run_config` 随 design 落盘（P-B 图级字段来源缺口）、CLI 独立模块入口（P1 并行冲突）、augmented lucy fixture 归 T-3P-0 交付（三下游共用）、beats_plan 载体锁死为 dict、version_recorder 枚举扩值挪入 T-3P-0、assemble 复用符号公共化、格式契约样张进 P0 验收物、退出码三态与 E4/E5/E6 边界定死、T-3P-3 反例口径两层拆分 + 如实边界说明、E2E 落隔离目录、§8 增作者确认项（2/7/8）与如实局限（9）、§9 critique 附 §10.6 五问 + 修正 fixation 措辞、4 份 prompt 加"待授权"标记。**注**：本预审是 L2 自查，不替代 governance §5 的正式 cross-LLM critique。
- v0.1（2026-06-29）：初版。L2 整合规划师会话产出；含作者两岔口拍板（轻量标签格式 / 文件+CLI 摄入）。待 cross-LLM critique。
