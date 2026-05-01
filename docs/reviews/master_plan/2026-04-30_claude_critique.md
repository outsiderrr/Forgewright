# Master Plan Critique — Round 5 — Claude

**评审者**：Claude (cold-start session)
**评审日期**：2026-04-30
**项目当前状态**：阶段 1 有条件通过；阶段 1.5 已规划待执行（STAGE_1.5_TASKS.md v0.1）
**评审范围**：阶段 1.5 / 2 / 3 / 4 + 跨阶段架构

---

## 1. 一句话总判

**前向路线图整体方向正确，但存在三类系统性缺口**：(a) 阶段 2/3/4 的完成标志比阶段 0/1 显著松散且不可测，(b) ADR-009 评测分层第三层（playtest bots）+ 本体 Schema 正式化均无明确落地阶段，(c) 时间估算对阶段 3（审阅 UI + 一致性维护）和阶段 4（开源剥离）严重偏乐观——前两个阶段的"快进"假象不可外推。**阶段 1.5 可以启动，但启动前应补两个硬指标**（角色一致性 + manifest 完整性的可测义）。

## 2. 严重度分布

| 严重度 | 数量 |
|---|---|
| 🔴 | 4 |
| 🟡 | 7 |
| 🟢 | 3 |
| **合计** | **14** |

---

## 3. 必修（🔴）

### 3.1 [SCOPE] — 阶段 3 完成标志包含"作者跑一周完成 10 场景"，但缺质量门槛

**问题**：[ROADMAP.md:177-184](../../ROADMAP.md#L177-L184) 阶段 3 完成标志写"作者实际跑一周，完成至少 10 个场景的生成+审阅+入库"。这是**过程指标**，不是产品指标。如果 10 个场景里 8 个生成出来需要重写一半内容（接受率 20%），按字面也算"完成"。但 50–100 场景的 MVP 真正需要的是"流水线在 X% 接受率下吞吐 Y 场景/周"——只有这个指标能反推阶段 4 的 MVP 完成时间。

**指向**：[ROADMAP.md:177-184](../../ROADMAP.md#L177-L184) 阶段 3 § 完成标志

**建议路径**：把完成标志改为"在 ≥ X% 单次接受率（X 建议 60，比阶段 2 的 70 略松，因为多场景上下文复杂）下，作者每周稳定吞吐 Y 场景（建议 8–12）"，并要求阶段 3 验收报告记录返工次数分布。具体阈值由作者拍板。

---

### 3.2 [EVAL] — ADR-009 评测分层第三层（playtest bots）在路线图中无落地阶段

**问题**：ADR-009 [DECISIONS.md:161-180](../../DECISIONS.md#L161-L180) 明确评测分三层；DEBATE_NOTES §8 [DEBATE_NOTES.md:213-234](../../DEBATE_NOTES.md#L213-L234) 强调第二/三层是"开源框架的市场机会"。但路线图：
- 阶段 2 重点工作 [ROADMAP.md:158-162](../../ROADMAP.md#L158-L162) 只提"validator 扩展：结局可达性"——这是第二层（图论）的一部分
- 阶段 3 重点工作 [ROADMAP.md:186-188](../../ROADMAP.md#L186-L188) 只提"Chapter/Act 层级结构设计"——**没有 playtest bots**
- 阶段 4 没有提

**为什么 CRITICAL**：50–100 场景 MVP 完全靠作者人审 + LLM 判官（已被阶段 1 R6 标记为"替代人工，需阶段 4 真用户校准"）+ LLM 判官又在可数值化维度系统性放水（R8）——**三层评测里第三层是真正能降低作者审阅带宽的杠杆**。没它，作者每天 2–5 场景的瓶颈无法突破，MVP 完成时间会被审阅带宽锁死，与 ADR-010 的"工作负载可控"假设冲突。

**指向**：[ROADMAP.md:170-194](../../ROADMAP.md#L170-L194)（阶段 3 全段）+ [DECISIONS.md:161-180](../../DECISIONS.md#L161-L180)（ADR-009）

**建议路径**：把"playtest bot 框架（ADR-009 第三层）"写进阶段 3 重点工作，作为与"批量生成调度器"并列的子系统。或者新增 ADR 明确 playtest bots 推迟到阶段 4 的代价（可能等于：MVP 内容产出延迟 1–2 个月）。

---

### 3.3 [GAP/SEQ] — 本体 Schema 正式化无路线图位置；从阶段 0 桩态拖到阶段 3+

**问题**：
- 阶段 0 验收 [STAGE_0_ACCEPTANCE.md](../../STAGE_0_ACCEPTANCE.md)：本体仍是桩
- 阶段 1 R5 [STAGE_1_ACCEPTANCE.md:124](../../STAGE_1_ACCEPTANCE.md#L124)：本体污染部分由"fixture 模糊+本体 Schema 阶段 0 仍是桩"导致
- 阶段 1.5 [STAGE_1.5_TASKS.md:40](../../STAGE_1.5_TASKS.md#L40) 显式选"Path A：仅扩展数据，不正式化角色 Schema"
- 阶段 2 ROADMAP [ROADMAP.md:139-167](../../ROADMAP.md#L139-L167) 没有提本体 Schema 正式化
- 阶段 3 重点工作只提 Chapter/Act 容器，仍未提本体本身

**为什么 CRITICAL**：阶段 2 `generate_scene()` 要生成多节点对话，**多节点上下文里的角色/地点引用一致性是 R4/R5 的指数化版本**——单节点 4/4 错配的 aelwin location_ref 在多节点对话树里会产生跨节点污染（一个节点说 vellin 在驿站，另一节点说她在陶窑山口）。本体桩 + Path A 数据扩展持续累积技术债，到阶段 3 一致性维护时再做 schema 正式化 = 之前所有生成内容的 generation_trace 反向索引全部需要重建。

**指向**：[ROADMAP.md 阶段 2 全段](../../ROADMAP.md#L139)（缺失：本体 Schema 正式化任务）+ [HANDOFF_STAGE_1_TO_1.5.md:38-39](../../HANDOFF_STAGE_1_TO_1.5.md#L38-L39)（R4/R5）

**建议路径**：在阶段 2 起手期增加任务"本体 Schema 正式化（character / location / faction 三类基础实体）"，**串行卡口**——同阶段 0/1.5 的 Schema 串行先例。或者由作者明确"本体桩持续到阶段 3，承担 R4/R5 在阶段 2 加倍的成本"。两个方向都是合法选择，但路线图不能继续不提。

---

### 3.4 [TIME] — 阶段 3 + 阶段 4 时间估算严重偏乐观（潜在 +30–50%）

**问题**：路线图 [ROADMAP.md:13-22](../../ROADMAP.md#L13-L22) 估阶段 3 = 4–6 周，阶段 4 = 6–8 周+。基于阶段 0/1 实际推进节奏（阶段 0：估 1–2 周/实际 ~4 天；阶段 1：估 2–3 周/实际 ~6 天）形成的"快进印象"不可外推到阶段 3/4：

- **阶段 3 主要工作量是审阅 UI**（Web 或桌面）。"左内容右批准/打回"听上去简单，但要支持：图缩略图预览、prompt 重新触发、版本对比、本体变更标记、generation_trace 反向索引可视化。Claude Code 写复杂前端的迭代成本远高于写后端 + JSON Schema。**作者不会编程**意味着所有 UI bug 需要作者描述 + Claude 调试。仅 UI 一项 3–4 周不够。
- **一致性维护"本体变更时标记需重审"**是一行字描述了一个未设计的子系统（见 §3.3）。
- **阶段 4 同时做"MVP 内容填充 50–100 场景"+"开源剥离"**：内容填充按 ADR-010 自己估算就是 1–3 个月（每天 2–5 场景）；开源剥离要做隔离 game-specific / 写文档 / 找测试用户 / 测试用户跑通的反馈周期，至少 4–6 周。**两件事并行不会减一半**——作者带宽是单 thread。

**指向**：[ROADMAP.md:13-22](../../ROADMAP.md#L13-L22) 总估算表 + [ROADMAP.md:200-215](../../ROADMAP.md#L200-L215) 阶段 4

**建议路径**：把阶段 3 改成 6–10 周，阶段 4 改成 10–14 周+；总估算从 4.5–7 月调整为 6–9 月。或者把"阶段 4 = MVP 完成 + 开源剥离"拆成阶段 4a（MVP）和阶段 4b（开源剥离），明确 4b 可以是阶段 4a 验收后的独立子项目。

---

## 4. 应修（🟡）

### 4.1 [SCOPE] — 阶段 1.5 完成标志多处不可测

**问题**：[ROADMAP.md:102-110](../../ROADMAP.md#L102-L110) 阶段 1.5 § 完成标志：
- "manifest.json 完整性 100%"——什么是"完整性"？所有字段非空？还是 schema 校验通过？没定义。
- "至少为《铁誓驿站》3 个角色 + 1 个场景完成资产生成 + 入库"——"完成"是什么？vellin 重档 10–15 张全部入库？或入库 ≥ 10 张？
- "接受率 ≥ 50%（**作者本人** + 机械预检 + AI 判官辅助；不替代）"——计算口径：分母是生成数还是机械预检通过数？分子是作者打勾就算？还是机械预检 + AI 判官 + 作者三者都通过才算？

**指向**：[ROADMAP.md:102-110](../../ROADMAP.md#L102-L110) + [STAGE_1.5_TASKS.md:1810-1817](../../STAGE_1.5_TASKS.md#L1810-L1817)（验收报告模板的"实测"列）

**建议路径**：在阶段 1.5 启动前，把这 3 个完成标志拆成可测义。例如：
- "manifest.json 完整性 = 入库资产的 manifest 字段全部通过 image_asset.schema.json 校验，且 source_mode / asset_id / character_ref 等关键字段无 null"
- "vellin 入库 ≥ 10 张，corvan ≥ 4 张，aelwin ≥ 4 张，1 location ≥ 1 张"
- "接受率 = (作者本人通过 ∩ 机械预检通过) / 生成总数"——AI 判官只做辅助标红不参与口径

---

### 4.2 [RISK] — 角色一致性 C+B 兜底无硬指标

**问题**：ADR-014 [DECISIONS.md:275](../../DECISIONS.md#L275) 决定"C + B 兜底——容忍同一角色不同立绘细微差异（C）；prompt 显式描述固定特征做兜底（B）"。但**没有定义**"细微差异"的可测含义，也没有"如果一致性失败到什么程度算 1.5 验收 fail"。vellin 重档 10–15 张，**任意两张作者一眼看出"是不同人"**——这种概率有多大没人测过。如果验收时发现一致性是失败的，**已经入库的 manifest + cost log 投入**已经沉没。

**指向**：[DECISIONS.md:275](../../DECISIONS.md#L275)（ADR-014）+ [STAGE_1.5_TASKS.md:38](../../STAGE_1.5_TASKS.md#L38)（P1.2 决策行）

**建议路径**：T-1.5.6（generate_character_sheet）落地前先跑一次 mini probe（vellin 5 张），让作者亲自看："5 张里有多少张你能一眼说出'这是同一角色'"。如果 < 4/5 就在 T-1.5.6 启动前回炉 prompt 而不是直接做 vellin 重档 10–15 张。这是 ADR-014 假设的实证检验，1.5 验收前必做。

---

### 4.3 [RISK/SEQ] — dev/prod prompt 同源性假设未实证；API 路径作为 stretch goal 推后会传播到阶段 2

**问题**：ADR-014 关键假设是 ChatGPT Plus 网页 + OpenAI Image API "dev/prod 共用一套 prompt"。但：
- ChatGPT 网页对 GPT-Image 的封装层可能含 system prompt 修饰 / 安全过滤层 / 上下文记忆
- OpenAI Image API 是"裸"调用
- 同一份 prompt 在两边出图差异多大没有测过

**[ROADMAP.md:108-109](../../ROADMAP.md#L108-L109) 把 API 路径定为 stretch goal**——意味着 1.5 验收时 API 路径**可能根本没跑过**。dev/prod 同源性未实证就被冻结。阶段 2 启动期一旦真的开始批量自动化生成，发现 manual 调到完美的 prompt 在 API 出图风格漂移，就要回炉 1.5 阶段的 prompt 模板——这是阶段 2 起手 1–2 周延迟。

阶段 1 已经教训过：baseline_001 烧了 $0.47 才发现 Gemini schema 不接受 additionalProperties（[STAGE_1_ACCEPTANCE.md:103](../../STAGE_1_ACCEPTANCE.md#L103)）。OpenAI Image API 也可能有未知坑。

**指向**：[DECISIONS.md:263-292](../../DECISIONS.md#L263-L292)（ADR-014）+ [ROADMAP.md:108-109](../../ROADMAP.md#L108-L109)

**建议路径**：1.5 阶段在 vellin 重档跑完前**至少跑一次 API 路径单张对比**（vellin 同 prompt manual 出 1 张 + API 出 1 张，作者看是否同源）。把这做成 1.5 完成标志的 hard requirement 而不是 stretch goal——成本 ≈ $0.17（一张图）。如果作者明确不愿先配 API key，那把"dev/prod 同源性未验证"显式列入阶段 1.5 R 项，传播到阶段 2 启动前置条件。

---

### 4.4 [DEBT] — R2/R3/R4/R8 在阶段 2 多节点场景下放大；路线图当前覆盖不足

**问题**：阶段 1 R 项里这四条**单节点已暴露**，多节点场景里会**指数化放大**：

- **R2** StateCondition 复合形态 [STAGE_1_ACCEPTANCE.md:120](../../STAGE_1_ACCEPTANCE.md#L120)：单节点常见，多节点对话树（5–15 节点 × 多 condition 边）几乎每节点都会用复合 condition；prompt 不补 few-shot 等于 R2 在阶段 2 是 4–10× 频次
- **R3** 选项过长 [STAGE_1_ACCEPTANCE.md:121](../../STAGE_1_ACCEPTANCE.md#L121)：单节点 5/13 节点 ≥ 27 字；多节点 generate_scene 会按节点独立采样，长度违规率不变 = 整树命中率 = 1 − (1−p)^N（N=节点数）
- **R4** location_ref 错配 [STAGE_1_ACCEPTANCE.md:122](../../STAGE_1_ACCEPTANCE.md#L122)：fixture 升级到 location_candidates 数组在阶段 1.5 / 2 才做（HANDOFF 把它标"可选"+"重要"）
- **R8** 机械预检器 [STAGE_1_ACCEPTANCE.md:126](../../STAGE_1_ACCEPTANCE.md#L126)：阶段 1.5 引入图像版机械预检（image_validator）但**文本版机械预检（option 长度 / path 前缀 / bond ID 白名单）路线图没有阶段位**

**[ROADMAP.md:139-167](../../ROADMAP.md#L139-L167) 阶段 2 重点工作只列了 2 项**——角色槽位（新 ADR）+ validator 扩展（结局可达性）。R2/R3/R4 的 prompt 调优 + R8 的文本版机械预检都没有显式提。

**指向**：[ROADMAP.md:158-162](../../ROADMAP.md#L158-L162) 阶段 2 重点工作 + [STAGE_1_ACCEPTANCE.md §4](../../STAGE_1_ACCEPTANCE.md)

**建议路径**：阶段 2 路线图增加显式重点工作行："阶段 1 R2/R3/R4/R8 prompt 调优 + 文本版机械预检（generator 侧 image_validator 的对偶物）"。或者由阶段 2 规划师产出的 STAGE_2_TASKS.md 显式吸收这一点（但这是隐含的，作者需要在 HANDOFF_STAGE_1.5_TO_2.md 里强制要求）。

---

### 4.5 [SEQ] — Chapter/Act schema 设计推到阶段 3 = 阶段 1/2 内容需要回填层级

**问题**：[ROADMAP.md:186-188](../../ROADMAP.md#L186-L188) 阶段 3 重点工作含"Chapter/Act 层级结构设计——支持分层叙事的容器结构，位于世界本体层而非对话图层"。但 SCHEMA_v0.md / SCHEMA_v0.2.md 都没有 Chapter/Act 字段。

**为什么 IMPORTANT**：阶段 1（已落地）+ 阶段 2（即将开始）生成的所有 DialogueGraph（每个对应一个场景）都没有 Chapter/Act 容器。阶段 3 才设计 = 阶段 2 已生成的 N 个场景需要在阶段 3 重新归类到 Chapter——这是回填迁移。如果阶段 2 生成 30+ 场景，回填成本不小。Schema 增量（v0.3.0）+ generation_trace 是否需要更新都要重新决定。

**指向**：[ROADMAP.md:186-188](../../ROADMAP.md#L186-L188)

**建议路径**：把"Chapter/Act schema 设计"前移到阶段 2 起手期（与§3.3 的本体 Schema 正式化打包做）。阶段 2 的 generate_scene() 已经需要"场景属于哪个 Chapter"作为生成上下文（戏剧节拍依赖整体位置），不在阶段 2 设计本身就有缺口。

---

### 4.6 [GAP] — DEBATE §9.2 长对话一致性问题在路线图中无任何缓解措施

**问题**：[DEBATE_NOTES.md:247-251](../../DEBATE_NOTES.md#L247-L251) 列"长对话一致性"为三个未解问题之一。"记忆流机制（Generative Agents 风格）缓解"被提了一句，但**路线图阶段 2/3/4 没有任何对应任务**。阶段 2 generate_scene() 多节点上下文一定会撞上：第 1 个节点 vellin 说 X，第 8 个节点 vellin 行为与 X 不一致，模型自己遗忘了。

**指向**：[ROADMAP.md 阶段 2 全段](../../ROADMAP.md#L139)（缺失）+ [DEBATE_NOTES.md:247-251](../../DEBATE_NOTES.md#L247-L251)

**建议路径**：阶段 2 增加显式 R 项或 ADR："generate_scene() 上下文管理策略——是否在节点间显式传递已生成节点摘要？这是 prompt 工程方向的探索性任务，可以是 ADR 候选"。即使最终结论是"接受 5–10% 不一致率，靠人工审阅修"，也应该路线图明示，而不是不提。

---

### 4.7 [OPEN] — 开源剥离 hook 在阶段 4 才开始 = content / generator 与作者私有内容耦合到最后

**问题**：[ROADMAP.md:196-215](../../ROADMAP.md#L196-L215) 阶段 4 才开始开源剥离。但阶段 0/1/1.5/2/3 全程：
- /content/ 含 char_vellin / scene_waystation_of_iron_oath 等作者私有命名
- generator 的 fixture / prompt 模板 / experiment harness 被设计成围绕《铁誓驿站》场景
- 阶段 1.5 引入的 visual_assets 路径 /content/visuals/_reference/ 是作者私有版权风险图

阶段 4 时一次性剥离 = 大量改动。每个被作者直接 hard-code 的"vellin"都要替换为示例占位符；fixture 要拆 generic + author-specific。这是隐藏的迁移成本。

**指向**：[ROADMAP.md 阶段 4 全段](../../ROADMAP.md#L196-L215) + [STAGE_1.5_TASKS.md:1879-1886](../../STAGE_1.5_TASKS.md#L1879-L1886)（模块边界自检脚本未含 author-coupling 检查）

**建议路径**：阶段 1.5 / 2 起手时增加"开源就绪度"轻量约束——例如要求所有 fixture 用 placeholder.json + author_overrides.json 双层，禁止业务代码 import 含具体角色名的常量。这是低成本的 hook，避免阶段 4 集中返工。

---

## 5. 可选（🟢）

### 5.1 [DECIDE] — 商业化 vs 开源许可证决策应早点拍板（即便答案是"先 MIT"）

**问题**：[ROADMAP.md:210-213](../../ROADMAP.md#L210-L213) 把"游戏是否商业化（影响开源框架许可证策略）"列为阶段 4 关键决策"到时候再做"。但许可证选择影响阶段 0–3 的依赖选型——任何 GPL / AGPL 依赖会传染最终框架。阶段 1.5 引入 OpenAI SDK + image API 的使用条款也跟商业用途相关。

**建议路径**：现在就拍板默认 MIT（作者保留切换权）；阶段 1.5 / 2 选依赖时简单 grep 一下许可证是否兼容。

### 5.2 [STYLE] — STAGE_1.5_TASKS.md 1900+ 行接近不可读

**问题**：单文件 1937 行，每个 T-1.5.X 都内嵌完整的执行 prompt + Codex review prompt 模板（套娃的 ` ```text` 围栏 + 模板 placeholder）。规划师未来若要更新模板，10 处 placeholder 需要同步修改。

**建议路径**：阶段 2 规划师参考时考虑把"Codex review prompt 模板"抽到独立文件 _prompts/_template.md，每个任务只引用，不重复。1.5 阶段已经成型不必动。

### 5.3 [GAP] — 阶段 1.5 没有"作者 ChatGPT Plus 订阅到期 / 涨价"的 fallback

**问题**：ADR-014 把 ChatGPT Plus 当 sunk cost。但 1.5 持续 2–3 周中订阅可能到期 / OpenAI 改额度（从 GPT-Image Plus 额度移走）。manual 模式断供时 1.5 进度受阻。

**建议路径**：路线图更新记录加一行："如果 ChatGPT Plus 网页 GPT-Image 额度不够，退化到 API 模式（API 路径其实已经在 ADR-014 里有 OpenAIImageProvider）"。这是已经存在的 fallback，只是没在路线图明示。

---

## 6. DEBATE_NOTES 已结案核对

我读完了 DEBATE_NOTES 主题 1–8 + §9 三个未解问题。**没有发现需要翻案的事项**。以下是想说但已被 DEBATE_NOTES 否决/已沉淀，不算 finding：

- 想说"是否应该考虑混合交互（选项式 + 偶尔自由文本）"——DEBATE 主题 1 + ADR-001 已锁死
- 想说"运行时是否在某些边缘场景调用轻量 LLM 做对白润色"——DEBATE §1 + ADR-002 已锁死
- 想说"Articy/Ink 是否作为 import 入口"——DEBATE 主题 3 已沉淀（Ink/Fountain 仅可作为可选 adapter）
- 想说"是否应该硬编码一个'默认编剧理论'到核心层"——DEBATE 主题 4 + ADR-005 已锁死
- 想说"开源框架是否应该提供 Premise 校验器"——DEBATE 主题 7 已沉淀（Premise = 可选插件，不是核心）

---

## 7. 阶段 1 R1–R8 传播评估

| R | 描述 | 阶段 2/3 复现风险 | 当前覆盖 | 缺口 |
|---|---|---|---|---|
| R1 | Schema 合格率 85%（净模型层 ≈ 95%） | **中**：阶段 2 多节点采样下网络瞬时错误期望放大 N× | HANDOFF 标"阶段 2 prompt 调优"；但 ROADMAP 阶段 2 重点工作没显式提 | 阶段 2 起手期补 prompt 调优任务 |
| R2 | StateCondition 复合 condition few-shot 缺失 | **高**：多节点对话树几乎每节点用复合 condition | HANDOFF 标"阶段 2 prompt 调优" | 同上；详见 §4.4 |
| R3 | 选项过长（C3 维度） | **高**：N 节点 → 命中率 = 1 − (1−p)^N | HANDOFF 提"建议改硬约束" | 文本版机械预检器（R8 对偶物）路线图无阶段位，详见 §4.4 |
| R4 | location_ref 错配（aelwin fixture 4/4） | **高**：generate_scene 涉及多 location，fixture 不升级会跨节点污染 | HANDOFF 标"阶段 1.5 / 2 改 fixture 引入 location_candidates 数组" | 1.5 是否真做不确定（HANDOFF 标"可选"），传到阶段 2 必做 |
| R5 | 本体污染（D1 维度，跨节点交叉） | **极高**：多节点对话树是污染温床；本体 Schema 仍桩 | HANDOFF 标"重要"；但 ROADMAP 阶段 2/3 没有本体 Schema 正式化任务 | §3.3 本体 Schema 正式化 |
| R6 | AI 判官替代人工 | **中**：阶段 2 70% 接受率仍由 AI 判官评？ | HANDOFF 标"阶段 4 真用户校准" | 阶段 2 是否仍用 AI 判官 + 文本判官能否 transfer 到 70% 阈值未明 |
| R7 | cost_log 高估失败请求成本 | **低**：阶段 2 同样的工程坑 | HANDOFF 标"阶段 2 接入 usage_metadata 反向更新" | 路线图阶段 2 重点工作未提；图像 API 同样需要 |
| R8 | 机械预检器（图像版在 1.5 引入） | **高**：文本版（option 长度 / path 前缀 / bond ID 白名单）路线图未规划 | 1.5 image_validator 落地；文本版 R8 在阶段 2 仍未规划 | 详见 §4.4 |

**汇总**：8 项里 5 项是 R3/R4/R5/R8 + R2 在阶段 2 多节点放大场景下指数化的；当前路线图阶段 2 重点工作只有 2 行，**显著覆盖不足**——见 §4.4。

---

## 8. 待作者拍板的开放决策（DECIDE 类汇总）

1. **阶段 1.5 角色一致性硬指标**：是否在 T-1.5.6 启动前要求作者跑一次 vellin 5 张 mini probe（"5 张里 ≥ 4 张作者一眼看出是同一人"）作为 1.5 启动 gate？（§4.2）
2. **阶段 1.5 dev/prod 同源性硬验证**：是否要求 1.5 验收前至少跑 1 张 API 路径对比（成本 ≈ $0.17），把"dev/prod 同源"从 stretch goal 升为 hard requirement？（§4.3）
3. **本体 Schema 正式化时机**：阶段 2 起手期（推荐）/ 阶段 3 / 持续桩态？（§3.3）
4. **ADR-009 评测第三层 playtest bots 落地阶段**：阶段 3 / 阶段 4 / 推到开源剥离后？（§3.2）
5. **Chapter/Act schema 设计前移**：与本体 Schema 正式化打包做（推荐）/ 保持阶段 3？（§4.5）
6. **总时间估算调整**：阶段 3 改 6–10 周 / 阶段 4 改 10–14 周+ / 阶段 4 拆 4a + 4b？（§3.4）
7. **开源剥离早期 hook**：阶段 1.5 / 2 起手就引入 fixture 双层（generic + author-specific）/ 阶段 4 集中处理？（§4.7）
8. **商业化许可证决策**：现在拍板 MIT 默认 / 留到阶段 4？（§5.1）

---

## 9. Top 3 你最担心的事

1. **阶段 3 审阅 UI + 一致性维护被严重低估，是路线图最大的时间黑洞**。Claude 不擅长写复杂前端，作者不会编程，迭代成本高。"左内容右批准/打回"扩展为支持图缩略图 + prompt 重新触发 + 本体变更标记 + generation_trace 反向索引 = 3–4 周变 6–10 周。如果 UI 难用，作者审阅 50–100 场景的体验会非常痛苦，**很可能在阶段 3 中段失去动力**——这是项目存活级风险，比任何技术债都严重。

2. **R5 本体污染 + 本体 Schema 仍为桩，会在阶段 2 多节点对话指数化放大**。单节点 4/4 错配 location_ref 在多节点对话树会变成跨节点污染（一个节点 vellin 在驿站，下一节点说她在陶窑山口）。阶段 2 ROADMAP 没有显式说要先正式化本体 Schema 就启动 generate_scene()，等于"在污染温床上批量生产"。

3. **dev/prod prompt 同源性假设未实证 + API 路径作为 stretch goal**。ADR-014 把"manual + API 共享 prompt"作为公理，但 ChatGPT Plus 网页对 GPT-Image 的封装层 vs OpenAI 裸 API 差异未测过。若到阶段 2 才发现 prompt 不可 transfer，1.5 阶段所有 manual 调优工作的杠杆消失，需要 1–2 周重做 prompt——这是阶段 2 起手延迟，又会进一步压缩本就吃紧的阶段 3/4 时间窗口。

---

## 10. 评审范围外的观察（可忽略）

- 阶段 0/1 推进节奏比纸面估计快 2–3 倍（阶段 0 估 1–2 周/实际 4 天；阶段 1 估 2–3 周/实际 6 天），这容易让作者形成"路线图整体偏保守"的错误印象——但阶段 0/1 主要是文档 + 单一函数后端代码，最适合 LLM 协作；阶段 3 的复杂前端 + 一致性维护、阶段 4 的开源用户测试反馈周期，都是 LLM 协作收益锐减的工作类型。**不要按阶段 0/1 的节奏倒推阶段 3/4 时间预算**——这条不算 finding，但作为 §3.4 的辅助证据值得记录。

- STAGE_1.5_TASKS.md 的 "Codex 评审 prompt 自动产出" 工作流（task 评审 → 生成 review prompt → 作者贴到 Codex → 报告 §9 是 paste-ready 的修复 prompt）是个相当精巧的设计，跨 LLM 评审 + review/author 分离做得不错——这条不算 finding，是观察。
