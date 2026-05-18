# ADR-034 候选 · Schema 格式中立 IR 可行性调研报告

> **来源**：2026-05-15 ADR-034 调研会话（claude/wonderful-proskuriakova-e68be2 worktree）
> **状态**：调研完成（research complete 调研完成）；ADR-034 候选立项决定**留待作者拍板**
> **触发**：2026-05-15 T-3Y L2 综合规划师会话识别风险——Forgewright dialogue_graph schema 凭直觉自设计，未对标业界事实标准，未来集成 / 迁移 / 用户群扩展时存在适配性风险
> **覆盖**：4 工具调研（Ink / Articy:Draft / Twine SugarCube / Dialogic 2.x）+ T-3Y 进展报告 §4/§5/§8 字段集对照 + ADR-034 草案
> **不覆盖**：ADR-035 L3 宿主选型（平行任务）；T-3Y 工程子任务（T-3Y-1 工作）；Schema 实际落地（仅产报告）

**日期**：2026-05-15 · **产出方**：ADR-034 调研会话 · **作者评审状态**：⏸ 待

---

## §1 背景与动机

### 1.1 立项触发

2026-05-15 T-3Y L2 综合规划师会话（详 [2026-05-15_T-3Y_design_progress.md](2026-05-15_T-3Y_design_progress.md)）在讨论"工具生态"时识别一个架构层级的风险：

> Forgewright 的 dialogue_graph JSON schema 当前是**作者凭直觉自己设计**的，没有显式对标业界事实标准。即便 Forgewright 自己探索出 schema 设计，**如果跟业界通用格式不兼容，未来集成 / 迁移 / 用户群扩展时会有适配性问题**。

L2 建议立 **ADR-034 候选**：Forgewright JSON schema 作为格式中立 IR（intermediate representation 中间表示）+ Ink / Articy / Dialogic / Twine superset 兼容。作者要求详细调研后再决定立不立。

### 1.2 项目数据格式哲学回顾

Forgewright 的 schema 设计有三条 ADR 层硬约束：

- **ADR-006 世界本体是真相之源（Single Source of Truth）**：所有 AI 生成内容必须能追溯到本体，违反本体的内容被校验器拒收。LLM 不能直接写本体。
- **ADR-016 阶段 2 本体最小可生成契约**：state path 命名空间限定五个（`world.*` / `faction.<id>.*` / `relationship.<slug>.*` / `flag.*` / `player.*`）；schema 版本号策略允许 schema 模块独立演进（dialogue_graph 模块 `0.1.1` + ontology 模块 `0.3.0` 共存）。
- **ADR-027 世界观不可知性原则（World-Agnostic Principle）**：schema / prompt / 代码不引入硬编码单一世界观假设；具体游戏世界由 ontology 注入。

这三条共同决定：Forgewright 的 schema 不是"游戏 mod 描述格式"，而是"AI 生产内容 + validator 强校验 + 运行时极薄"的三位一体契约。

### 1.3 ADR-034 拟解决问题

是否应正式承诺 Forgewright JSON schema 兼容业界主流格式（Ink / Articy / Twine / Dialogic）？以何种形态承诺（superset / subset / 双向有损映射）？承诺后对 T-3Y 草案 §4+§5 字段集设计的回馈是什么？

本报告通过 4 工具调研给出事实层证据，并产 ADR-034 候选草案（§6）。最终立 / 不立 / 缓议由作者拍板。

### 1.4 调研方法与资料覆盖

4 个并行 general-purpose subagent 调研 4 工具；判断准则："主流能实现相同效果则推主流"（作者签字）。

| 工具 | 调研路径 | 覆盖率自评 |
|---|---|---|
| Ink | Writing with Ink 全文档 + JSON runtime spec + 多教程 | 95% |
| Articy:Draft | articy.com docs + scenarioworld/articy-js TypeScript 类型反推 + 论坛 | **75%**（闭源 GUI 未下载） |
| Twine SugarCube | motoslave docs + Twee 3 spec + Twine Cookbook | 90% |
| Dialogic 2.x | docs.dialogic.pro + GitHub repo + DeepWiki | 90% |

未覆盖项（flag for follow-up）：Articy GUI 真实导出 / Twine 玩家交互 / Ink runtime 源码 / Dialogic .dtl↔DialogicEvent 双向转换损耗。

---

## §2 业界工具语义清单

> 本段 per-tool 视角列出 4 个工具的核心语义机制（每工具 ≥ 10 机制）。横向对比表见 §9 附录 A。

### 2.1 Ink（Inkle Studios DSL）

Ink 是一种**源 DSL + 编译 JSON 运行时**两层架构：作者写 `.ink` 文本（人类友好），`inklecate` 编译为 `.json` bytecode-like 产物（非人类 / 非 LLM 友好的纯运行时格式）。

**1. Knot（结）** — 顶级节段，dotted-path 寻址 `-> knot_name`。例：`=== forest === ...content... -> end`

**2. Stitch（缝）** — knot 内子节段。例：`= clearing`，寻址 `-> forest.clearing`

**3. Once-only choice (`*`)** — 一次性选项，选过即消。例：`* [Talk to Vellin] -> talk`

**4. Sticky choice (`+`)** — 粘性选项，重访仍在。例：`+ [Look around again] -> look`

**5. Variable declaration** — `VAR`（global 持久化）/ `CONST`（不可变）/ `~ temp`（knot-local 临时）三关键字。例：`VAR money = 0` 然后 `~ money = money + 5`

**6. Conditional choice gate** — 选项前 `{cond}` 大括号守卫。例：`* {has_key and not door_open} [Unlock the door] -> open_door`

**7. Inline conditional text** — 文本行内 `{cond: A | B}` 切换；序列形式 `{!/&/~}` 自加规则。例：`"His real name was {met_blofeld.learned_his_name: Franz | a secret}."`

**8. State mutation** — `~ var = expr` 行内修改。例：`~ trust = trust - 1`

**9. Tunnel** — call-with-auto-return（带自动返回的子流调用），`-> sub ->` 处理完跳回调用点。例：`-> dungeon -> .`

**10. Thread** — 把远端 knot 的 choices 拉入当前 weave。例：`<- side_choices`

**11. LIST type** — 枚举旗标集合 + `?` 成员测试 + `+=` set 操作。**业界最接近 progressive disclosure 的原语**。例：`LIST Facts = (fogg_is_odd), first_name_phileas` 然后 `{Facts ? fogg_is_odd: I smiled.}`

**12. Implicit read-count** — 每 knot/stitch 自动维护 integer visit counter。例：`{knot_name >= 1}` 或 `TURNS_SINCE(knot)`

**13. EXTERNAL function** — host-bound 外部函数。例：`EXTERNAL roll_dice(sides)`，runtime 用 `BindExternalFunction` 注入。

**14. Tag (`#`)** — 行级附加标签，扁平字符串，runtime 可读。例：`Alice: "Hello." # speaker: alice`

**15. Compiled JSON runtime format** — `.json` bytecode-like：`{"inkVersion": 21, "root": [["^Hello world", {"#n": "hello"}], "done", null]}`。控制字节 `"ev"` / `"/ev"` / `"out"`，divert 编码 `{"->": "path"}`。**不是人类 / LLM 可写格式**。

**关键缺口**（与 Forgewright 对照）：无 scene-scope 变量、无声明式 pre/post 契约、无 reachability / coverage 静态分析、无结构化作者元数据。

### 2.2 Articy:Draft（articy Software GmbH 商业工具）

Articy 是**专有图形化编辑器 + JSON / XML 导出**模式：作者在 GUI 内拖拽节点，导出 `.json` / `.xml` 给运行时（Unity / Unreal / Godot importer 等）。

**1. FlowFragment** — 分层容器节点；含 input/output pin；可嵌套子流。Hierarchy 树记录父子关系。

**2. Dialogue** — FlowFragment 的对话子类型；专门容纳对白序列。

**3. DialogueFragment** — 单条对白节点；含 `Speaker: Id`（外键到 Entity）+ `MenuText`（玩家选项标签）。

**4. Hub** — 多选项汇聚节点；列出可选下一步。

**5. Jump** — 跨流跳转节点；目标可指任意 Pin。

**6. Condition node** — 输入决策节点；articy:expresso 脚本 evaluating 后路由。

**7. Instruction node** — 输出执行节点；articy:expresso 脚本变更全局状态。

**8. Pin** — 节点的输入 / 输出端口；**Input pin 可挂 condition；Output pin 可挂 instruction**。**业界唯一形式化 pin-level pre/post 系统**——比 Forgewright scene-level 更细一档，但漏洞更多（多 output pin 易漏复制 instruction）。

**9. articy:expresso** — C-like 脚本语言；运算符 `==, !=, <, >, &&, ||, !` + 函数调用。例：`Inventory.key == true && GameState.talkedToGuard != true`

**10. GlobalVariables / VariableSet** — 命名空间组织全局变量；类型 Boolean / Integer / String。例：`Inventory.collectedTokens += 5`

**11. Template（3-tier）** — Property → Feature → Template；Feature 是可挂到任意节点的可复用字段束。**Forgewright project 配置层设计参考点**（ADR-029 类似精神）。

**12. seen / unseen / seenCounter** — 内置 visit 追踪函数。例：`if (seen(DialogueFragmentRef)) { ... }`

**13. fallback(BranchingPointReference)** — 1.2+ 引入；"穷尽其他选项后回退" 显式语义。**业界唯一原生 mandatory-with-fallback 形态**。

**14. Conflict UI** — 编辑器内冲突检测（多人协作场景）；非 schema 层验证。

**15. Export format** — 私有 `.articy`（编辑期，二进制）+ JSON / XML 导出（运行时消费）。Top-level shape: `{Project, Settings, Packages, ObjectDefinitions, GlobalVariables, Hierarchy, ScriptMethods}`

**关键差异**（与 Forgewright 对照）：Articy 编辑期是 GUI 拖拽（非 schema-first），但其 Template 系统 + Pin-level 契约 是 Forgewright 可以借鉴的两个机制。

### 2.3 Twine SugarCube 2.x

Twine 是**故事格式无关的最小核心 + 故事格式插件**架构：Twine 2 编辑器提供 passage + link 基础结构；SugarCube / Harlowe / Chapbook 等故事格式各自定义脚本语言层。SugarCube 2.x 是最强表达力的故事格式。源格式 Twee 3（`.twee` 文本），编译产物 `.html`（自包含可玩）。

**1. Passage** — 原子叙事节点；命名块。Twee 3 头：`:: PassageName [tags] {metadata}`。例：`:: Forest Clearing [forest scene1]\nThe trees thin out.`

**2. Passage tag** — 自由标签；SugarCube 暴露为 CSS class + `tags()` / `visitedTags()` 查询。例：`:: Tavern Door [tavern act1]`

**3. Wiki-link** — `[[Text|Target]]` 创建从当前 passage 到 Target 的链接。例：`[[Enter the cave|Cave]]`

**4. Setter link** — 在 link 内嵌赋值。例：`[[Lie|Next][$rep -= 2]]`

**5. `<<link>>` macro** — 程序化 link 替代 wiki-link；可带 actions。例：`<<link "Enter the cave" "Cave">><</link>>`

**6. Story variable (`$var`)** — 进入 history（saved）的玩家状态。例：`<<set $hp to 10>>`

**7. Temporary variable (`_var`)** — passage-scoped；不持久化。例：`<<set _i to 0>>`

**8. Setup global (`setup.X`)** — 静态全局，never cloned, never saved。例：`setup.MAX_HP = 100`（在 init passage 内）

**9. `<<if>>` macro（容器宏）** — `<<if cond>>…<<elseif>>…<<else>>…<</if>>`；可嵌任意位置实现行内条件文本。例：`Hello <<if $met>>again<<else>>there<</if>>, traveler.`

**10. `<<set>>` macro** — 状态变更。例：`<<set $rep += 1>>`

**11. `<<include>>` macro** — 把另一 passage 渲染后内联入当前。例：`<<include "MandatoryReminder">>`

**12. `<<widget>>` macro** — 参数化复用宏；定义在 widget-tagged passage 内。例：`<<widget "greet">><<print "Hi, "+$args[0]>><</widget>>` 然后 `<<greet "Mira">>`

**13. `visited()` / `hasVisited()`** — 访问计数 / 布尔查询。例：`<<if hasVisited("Steal")>>`

**14. StoryData passage（保留）** — 全项目元数据 JSON。例：`:: StoryData\n{"ifid":"D674C58C-...","format":"SugarCube","format-version":"2.36.0","start":"Intro"}`。**`ifid`（UUID v4）是 IFID 规范的必填字段**——业界唯一对外公认的故事级唯一标识。

**15. PassageHeader / PassageFooter / PassageReady / PassageDone（保留）** — 全局钩子 passages，自动 prepend/append 到每个 passage 渲染。**业界唯一原生 story-wide hook**——用于"force info appearance on every path"约定。

**16. Canonical format** — `.twee` 文本源（passage 块）+ `.html` 编译产物（单文件自包含）。Twee 3 spec 由 IFTC（Interactive Fiction Technology Foundation）维护。

**关键差异**（与 Forgewright 对照）：Twine 的"最小核心"哲学完全不约束 schema——几乎所有高阶机制（speaker / scene / coverage / knowledge）都是用户空间约定，无 validator 强制。Forgewright 与 Twine 在哲学上是相反方向。但 Twine 的 `ifid` + StoryData JSON 结构是值得对齐的故事级元数据规范。

### 2.4 Dialogic 2.x（Godot 4 视觉小说插件）

Dialogic 是**Godot 引擎插件**：编辑期作者用 Dialogic 编辑器写 `.dtl` 文本 timeline 文件；运行时由 Dialogic autoload 解析为 `DialogicEvent` 资源数组并播放。**Timeline format 是 .dtl 文本，不是 JSON**——这是与 Forgewright 哲学的根本差异。

**1. Timeline** — 事件 array 的命名容器；`.dtl` 文本格式（**非 JSON**）+ 运行时 `DialogicTimeline` 资源。无 `from_json()` API。

**2. DialogicEvent（基类）** — 事件资源 base class；每事件类型 extend it 自定义 `get_shortcode()` / `_execute()` 等。

**3. Text Event** — 单条对白；前缀 `CharacterName (variant): ...` 自动绑 Character resource。例：`Emilio (happy): Hello!`

**4. Choice Event** — `- option text` 行；后续 indented 行是该 branch body。例：`- Maybe | [if {Stats.Charisma} > 10] [else="disable"]`

**5. set event（Variable Event）** — 变量赋值；操作符 `=, +=, -=, *=, /=`。例：`set {MyVariable} += 10`

**6. if / elif / else event** — 条件分支；Godot-style 表达式 + `{Var}` 替换。例：`if {Player.Wisdom} > 3:`

**7. Jump event** — 跨 timeline 跳转；语法 `jump TimelineName/LabelIdentifier`。例：`jump Town/Market`

**8. Label event** — 跳转目标。例：`label Market`

**9. Character resource (.dch)** — 单独资源文件；含 portraits + 名字 + 颜色等。例：`join Emilio (excited) center [animation="Bounce In"]`

**10. join / leave / update event** — 角色舞台运营（VN 风格）

**11. Background event** — `[background path="..."]`。例：`[background path="res://assets/backgrounds/dialogic_factory.png"]`

**12. Music / Sound event** — 音频资源调用

**13. Dialogic.VAR autoload** — 全局变量总线；folder 仅命名空间组织（非 scope）。例：`Dialogic.VAR.Group.other_variable`。**外部 Godot autoload 属性也可直接写**（`set Autoload.property = "..."`）。

**14. History subsystem** — "has this event been visited?" 查询；可持久化到全局 info save。**Forgewright player_known_info 参考点**——但仅提供 visit 事实，不提供 knowledge 语义。

**15. Glossary subsystem** — 设定百科条目存储；**不带 unlock state**（需自维护变量）。

**16. Extension API** — `DialogicIndexer` + `DialogicEvent` extend + `DialogicSubsystem` extend；hooks: `_execute()` / `clear_game_state()` / `load_game_state()` / `pause()` / `resume()`。

**17. Signal-based host integration** — `timeline_started` / `timeline_ended` / `signal_event` / `text_signal` 给 host 通知。**关键架构限制**：Forgewright JSON 不能直接 ingest；需 transpile to `.dtl`（这对 ADR-035 L3 宿主选型有决定性影响）。

**关键差异**（与 Forgewright 对照）：Dialogic 的 timeline 是**线性事件流 + 跳转**，没有 graph 拓扑视图；与 Forgewright 的 dialogue_graph DAG 模型不同。集成路线必然走 transpile 而非 share schema。

---

## §3 3 个 Distinct 立场的候选方案

> 本段给出 3 个**设计哲学根本不同**的候选方案。3 版之间不是 superficial 措辞差异——是关于"Forgewright schema 与业界工具生态的关系"的 3 种根本立场。详细评分见 §4，agent 推荐见 §5。
>
> 横向跨工具机制对比（旧 §3 表格）已 fold 进 §2 per-tool 视角；如需 horizontal view 见 §9 附录 A（保留 reference table）。

### 3.1 v_full_ir（激进 · Schema 作为格式中立 IR）

**设计哲学**

工具民主路线——Forgewright JSON schema 作为业界格式中立 IR；任何业界工具（Ink / Articy / Twine / Dialogic）的现有内容都应能无损（或最小损失）转换为 Forgewright JSON，反之亦然。社区采纳路径：用户先在熟悉工具内创作，再导入 Forgewright 享受 AI 生成 + 校验 + 溯源能力；或在 Forgewright 内创作，导出到任意工具播放。Forgewright 不是某种新格式，而是业界格式之间的桥梁与超集。

**具体方案**

1. Schema 扩展覆盖 4 工具核心机制 superset：
   - `node.narration` 升级为支持行内条件文本微语言（对齐 Ink `{cond: A|B}` + SugarCube `<<if>>` 容器宏）
   - `option.choice_visibility` enum (`once` / `sticky` / `disabled`)（对齐 Ink `*`/`+` + Articy seen/unseen + fallback()）
   - `graph` 加 `sub_graph_calls` 字段（call-with-return 语义），对齐 Ink tunnel
   - state path 加第 6 命名空间 `knowledge.*`（对齐 Ink LIST + Articy Glossary）
   - `chapter` 加 `ifid` (UUID v4) 字段（对齐 Twine StoryData IFID 规范）
   - `node` 加 `pin_inputs[] / pin_outputs[]` 字段（对齐 Articy pin-level pre/post 契约）
2. 双向适配器 4 个：
   - `forgewright ↔ ink`（`.ink` 源 ↔ `.json`，含 LIST / tunnel / weave 双向 mapping）
   - `forgewright ↔ articy`（Articy JSON 导出 ↔ Forgewright JSON）
   - `forgewright ↔ twine`（`.twee` ↔ `.json`）
   - `forgewright ↔ dialogic`（`.dtl` ↔ `.json`）
3. T-3Y capability surplus（progressive disclosure / coverage strategy / scene metaparams / player_known_info）保留为 optional 字段，但导出时降级（map to nearest equivalent + warn）

**工程量 estimation**

- Schema 扩展（含 6 大新字段族 + 行内条件文本微语言 parser）：~3 工程周
- 4 双向适配器，每个 ~2-3 工程周 = **8-12 工程周**
- Validator 扩展（双向 / 行内条件文本解析 / 降级 mapping 校验）：~2 工程周
- Test 套件（每工具 5-10 sample input × 2 directions = 40-80 cases）：~2 工程周
- 文档（每工具适配文档 + 降级损失列表）：~2 工程周
- **总计：17-21 工程周（4-5 个月单人时间）**
- **当前阶段 0-3 立即工程量：~3 周（Schema 扩展）；其余在阶段 4 开源剥离时**

**优**

- 社区采纳路径最完整：作者可在任意工具内创作，Forgewright 提供"superset 之家"
- 与业界生态最紧密：Ink / Twine 用户可继续在原工具写作 + 导入 Forgewright 享受 AI 生成 + 校验
- 长期工具影响力最大：成为业界 IR 后，Forgewright 的设计决策会影响后续工具
- 中文社区入口宽：双语 Twine / Dialogic 教程已存在，Forgewright 借力即可

**劣**

- Schema 体积爆炸：违反 ADR-004 极简精神（schema 字段数预计从当前 ~60 增至 ~120）
- T-3Y capability surplus 在导出路径上**必然降级**：progressive disclosure → flatten；coverage strategy → 丢弃；scene metaparams → 转 global var；player_known_info → 拆 list + summary 双轨——Forgewright 设计价值 in transit 流失
- 工程债压在前期：4-5 个月单人时间换"未来兼容性"，当前阶段 0-3 用不上
- 维护成本永续：业界工具每升级（Ink 1.x → 2.x、Articy 每年 X 版本号 + 等）都需要 4 个适配器同步升级

**风险**

- **R1（高）违反核心哲学**：ADR-004 极简 + ADR-006 SOT + ADR-027 World-Agnostic 全部受冲击；为了兼容工具引入的特性可能反咬 schema 设计，例如为了对齐 Articy template 系统可能引入运行时 LLM 调用的诱惑
- **R2（高）工程量永远做不完**：4 个双向适配器 × 业界工具升级频率 = 永远 maintenance 队列；阶段 4 之前 Forgewright 主线开发可能被这个吸光
- **R3（中）社区采纳预期失败**：业界用户惯性强，即使提供完美双向适配，多数用户仍留在原工具；Forgewright 投入与回报严重不匹配
- **R4（中）滑坡到"少功能版业界 IR"**：为了真正兼容，Forgewright schema 可能逐步去除独特设计；最后变成"另一个少功能的 IR"，失去 capability surplus 这一核心差异
- **R5（中）跨工具语义不一致带来 bug**：例如 Ink 的 sticky 选项语义与 Articy 的 seen 计数语义不完全等价；双向 mapping 会产生 silent semantic drift（静默语义漂移）

---

### 3.2 v_thin_export（保守 · Schema 不做 IR，仅单向导出 shims）

**设计哲学**

核心价值优先路线——Schema 服务于 AI 生成 + 校验 + 溯源（Forgewright 的真实差异化能力），工具生态是副产物。Forgewright JSON schema 是 AI 生成 schema，**不假装是 IR**；与业界工具的桥梁只在阶段 4 开源剥离时建，且只做单向（forgewright → tool），不承诺 RT 无损往返。Ink / Articy 因架构异构（DSL 源 + 编译产物 vs JSON-native + 私有编辑期格式 vs JSON-native），不做双向适配器；Twine / Dialogic 作为可选导出目标。

**具体方案**

1. Schema 保持当前 v0.3 + T-3Y 草案路线，**不为 IR 兼容性扩展任何字段**
2. 阶段 4 开源剥离时加 2 个单向适配器：
   - `forgewright-to-twine.py`（输出 `.twee` 文本）
   - `forgewright-to-dialogic.py`（输出 `.dtl` 文本）
   - 适配器明示 lossy：progressive disclosure → flatten；coverage strategy → 丢弃；scene metaparams → 转 global var；player_known_info → 拆 list + summary；scene pre/post → inline `<<if>>` guards
3. ADR-034 文档明示 schema 定位：**"AI-generation-aware schema with optional single-direction export shims; NOT a format-neutral IR"**
4. ADR-034.X follow-up 不在本路线范围；若发现局部对齐价值（如 chapter.ifid），通过独立 ADR 在未来排期

**工程量 estimation**

- Schema 修订（仅 ADR-034 文档措辞）：**~0 工程周（只改文档）**
- 2 单向适配器，每个 ~2 工程周 = **4 工程周（推迟到阶段 4）**
- Test 套件（每适配器 5 sample input = 10 cases）：~1 工程周
- 文档（每适配器 lossy 损失列表）：~0.5 工程周
- **总计：~5-6 工程周（约 1.5 个月，全部摊到阶段 4）**
- **当前阶段 0-3 立即工程量：0 周**

**优**

- 保 T-3Y capability surplus 完整：无导出压力，无降级损耗
- 维护成本最低：2 个单向适配器 + 无 follow-up
- 当前阶段 0-3 工程量为零：**不阻塞 T-3Y / T-3.X 主线**
- 哲学一致：与 ADR-004 极简 + ADR-006 SOT + ADR-027 World-Agnostic 全对齐
- 决策可逆性高：若阶段 4 发现需要更多对齐，可临时升级到 v_incremental 或 v_full_ir

**劣**

- 社区采纳门槛高：用户必须接受 JSON 写作（无 Twine / Ink 那种作者友好 DSL）
- 工具生态价值有限：Ink / Articy 用户无法迁移；Twine / Dialogic 用户只能消费导出，不能反向贡献
- 长期影响力受限：Forgewright 成为孤岛而非 hub
- 阶段 4 开源剥离时可能后悔：若发现某些用户需求只能用 IR 路线解决，要回头补做 v_full_ir 的工作（但工程债推迟到那时再说）

**风险**

- **R1（低）开源采纳率低**：但作者本人创作 + AI 辅助流水线不受影响；开源是副产物
- **R2（中）后期被迫加 IR 路线**：若开源阶段发现 Ink / Articy 用户群是关键扩张路径，可能要回头做 v_full_ir 的工作（但有足够数据支撑后再决定）
- **R3（低）社区批评"封闭"**：定位措辞清晰可化解（"我们做 AI 生成 schema，不做 IR；想要 IR 请用别的工具"）
- **R4（低）失去与工具生态的反馈循环**：但 Forgewright 内部 AI 生成 + validator 已能闭环，不依赖外部反馈
- **R5（中）跨平台分发能力受限**：用户做完游戏后，分发渠道只有"自带的运行时"或"Web 自研"，无法借力 Twine 编译的 HTML 单文件分发便利性
- **R6（低）评估手段受限**：单向导出意味着 Forgewright 内的设计选择无法通过"试导出到 Twine 看效果"来快速 evaluate；必须在 Forgewright 自身 validator + 测试场景里 ground truth；测试基础设施工程量被推回 Forgewright 主线

---

### 3.3 v_incremental（折衷 · Schema 主体 AI 生成路线，但局部对齐主流原语）

**设计哲学**

借鉴主义路线——不立 IR，但承认借鉴价值。Forgewright schema 主体保持"AI 生成 schema"路线（同 v_thin_export），但在 schema 层显式承认**对齐机会**——业界主流原语（Ink LIST、Twine StoryData ifid、Articy Template、Articy seen/unseen 等）能在不违反 Forgewright 哲学（ADR-004 / 006 / 027）的前提下被借鉴时，逐 ADR 修订对齐。每一次修订 = 与一种业界原语对齐一次；不立"IR 完备性"承诺；保留"何时停止对齐"的灵活性。

**具体方案**

1. Schema 主体保持 v0.3 + T-3Y 草案路线（同 v_thin_export）
2. 立 4 个 follow-up ADR 候选，每个对齐一项业界主流原语：
   - **ADR-034.1**：`knowledge.*` state path 第 6 命名空间（对齐 Ink LIST + Articy Glossary）—— **优先级最高**，T-3Y player_known_info 工程依赖
   - **ADR-034.2**：`Option.choice_visibility` enum (once / sticky / disabled)（对齐 Ink `*`/`+` + Articy seen/unseen + fallback()）—— **中优先级**，对齐 gold scene 已用的 condition + flag 模式
   - **ADR-034.3**：`node.narration` inline conditional text 微语言（对齐 Ink `{cond: A|B}` + SugarCube `<<if>>`）—— **低优先级**，阶段 3-4 观察 LLM 生成期是否因 narration 是 plain string 而节点膨胀
   - **ADR-034.4**：`chapter.ifid` UUID v4 字段（对齐 Twine StoryData）—— **低优先级**，开源剥离阶段加
3. 单向导出适配器 2 个（同 v_thin_export）作为阶段 4 副产物
4. ADR-034 主文档措辞：**"AI-generation-aware schema that selectively aligns with industry primitives where they fit; not a format-neutral IR"**
5. **明示停止条件**（v_incremental 独有 D5）：当某次对齐识别为"为对齐而对齐"（即业界原语与 Forgewright 哲学冲突或 capability surplus 必然受损）时立即停止，不再继续对齐方向

**工程量 estimation**

- Schema 修订（4 个 follow-up ADR 各自落地）每个 ~2-3 工程周 = **8-12 工程周**
- 但分散到 4 个独立 ADR，每个独立排期；当前阶段 3-4 实际工程量 ~2-4 周/ADR × 1-2 个/季 = **可控**
- 2 单向适配器（同 v_thin_export）= **4 工程周（阶段 4）**
- ADR-034 主文档（措辞修订 + follow-up 列表）：~0.5 工程周
- **总计：12-17 工程周；分散到 6-12 个月，按节奏排**
- **当前阶段 0-3 立即工程量：~3 工程周（仅 ADR-034.1 knowledge namespace 入 T-3Y-1 工程依赖）**

**优**

- 保 T-3Y capability surplus 完整（同 v_thin_export）
- 局部对齐主流原语，符合作者签字"主流能实现相同效果则推主流"原则
- 工程节奏可控：每 follow-up ADR 独立排期 + 评审 + 落地，不强制一次性大动
- ifid 等元数据兼容业界 = 阶段 4 开源剥离时社区采纳路径更平滑
- 哲学张力可控：每次对齐都有明示 ADR 评审，不会无意识违反 ADR-004 / 006 / 027

**劣**

- 战略上 partial unclear："对齐多少算够？" 即使 D5 立了"停止条件"，实际操作仍依赖判断
- ADR 修订频次高：4 个 follow-up + 未来发现的新对齐机会，ADR 列表膨胀
- 测试套件膨胀：每 follow-up 字段都需要 validator 扩展 + test case
- 4 个 follow-up 之间可能产生依赖（如 ADR-034.1 knowledge 命名空间依赖 ADR-034.2 choice_visibility 的语义定义），排期复杂度增加

**风险**

- **R1（中）滑坡到 v_full_ir**：对齐机会不止 4 个；每识别一个新原语就立 follow-up，可能逐步累积成事实上的 IR——本路线已立 D5 "明示停止条件"作为防御
- **R2（中）ADR 维护负担**：4 个 follow-up 落地后可能还有 5、6、7 个候选；ADR 列表膨胀，每次修订都要回顾架构哲学一致性
- **R3（低）局部对齐冲突**：例如 `Option.choice_visibility` once/sticky 与 v0.3 的 `unavailable_behavior` (hide/disable/disable_with_hint) 字段语义可能重叠或冲突，需要重新设计
- **R4（中）社区误读**：用户看到局部对齐可能误解为"半 IR"，对兼容性产生过高预期；解决：每 follow-up ADR 显式说明"对齐 X 原语；不承诺与原工具的 RT 兼容"
- **R5（低）"停止条件"判定的主观性**：D5 立的"为对齐而对齐则停止"是 fuzzy 标准；可能在某具体 follow-up 上出现争议；解决：每候选 follow-up 必须明示哲学冲突检查

---

## §4 7 维度评分对比表

> 3 个候选方案（v_full_ir / v_thin_export / v_incremental，详 §3）按 7 个评估维度各打 0-10 分；**分数越高 = 该维度上越优**。每行附一句决策性理由。详细 gap 证据 + 反对意见见 §5。

| 维度 | v_full_ir | v_thin_export | v_incremental | 评分理由 |
|---|---|---|---|---|
| **工程量**（分数高 = 工程量小） | 3 | 9 | 6 | v_full_ir 总 17-21 工程周（4-5 月）；v_thin_export 5-6 周（推迟到阶段 4）；v_incremental 12-17 周分散到 6-12 月 |
| **兼容性**（与业界工具） | 9 | 3 | 6 | v_full_ir 4 个双向适配器全覆盖；v_thin_export 仅 2 个单向 shim 到 Twine/Dialogic；v_incremental 局部对齐 + 单向 shim |
| **future-proof**（抗业界工具演化） | 4 | 8 | 7 | v_full_ir 永续 maintenance（每工具升级都要同步适配器）；v_thin_export 暴露面最小；v_incremental defer-to-ADR 控制 |
| **学习曲线**（新用户上手） | 6 | 4 | 5 | v_full_ir 可从熟悉的 DSL 切入（Ink/Twine）；v_thin/incremental 必须接受 JSON-native + Forgewright 独有机制 |
| **集成风险**（分数高 = 风险小） | 4 | 8 | 6 | v_full_ir 跨工具 silent semantic drift（静默语义漂移）高；v_thin_export 暴露面最小；v_incremental 局部对齐冲突 |
| **跨平台分发**（用户发布渠道） | 9 | 5 | 6 | v_full_ir 可借力 4 工具分发渠道（Ink → Inky web、Twine → HTML 单文件等）；v_thin_export 仅 Twine `.html` + Godot `.dtl` + 自研 Web；v_incremental 类 thin |
| **中文社区**（中文用户采纳门槛） | 7 | 4 | 5 | v_full_ir 借力 Twine + Dialogic 中文教程生态；v_thin/incremental 用户必须接受 JSON 写作，门槛高 |

### 4.1 加权倾向

7 维度评分不是单一加权能给答案的——**不同优先级会拉出完全不同的结论**：

- **保守工程纪律加权**（工程量 + future-proof + 集成风险，三维加权）：v_thin_export 25 分 ≫ v_incremental 19 分 ≫ v_full_ir 11 分；**v_thin_export 完胜**
- **生态扩张加权**（兼容性 + 跨平台分发 + 中文社区，三维加权）：v_full_ir 25 分 ≫ v_incremental 17 分 ≫ v_thin_export 12 分；**v_full_ir 完胜**
- **学习曲线单独维度**：v_full_ir 6 > v_incremental 5 > v_thin_export 4；**v_full_ir 略胜**

### 4.2 哲学锚定决定加权

7 维度评分**回避不了哲学层级的根本选择**——

- v_full_ir 假定 schema 应服务工具生态（生态扩张加权）
- v_thin_export 假定 schema 应服务核心价值 AI 生成 + 校验（保守工程加权）
- v_incremental 是两端折衷但有"滑坡到 v_full_ir"风险（§3.3 R1 已识别）

最终选哪个不是评分加权决定的，而是**项目阶段 + 长期定位**决定的——详 §7 拍板指引。

### 4.3 评分置信度说明

- **高置信度**（基于客观证据）：工程量（subagent 调研 + 现有适配器代码量参考）、兼容性（4 工具 §2 per-tool 机制清单证据）、集成风险（具体冲突点已识别如 choice_visibility vs unavailable_behavior）
- **中置信度**（基于设计推断）：future-proof（业界工具升级频率历史推断）、跨平台分发（4 工具的分发渠道公开信息）
- **低置信度**（基于市场判断）：中文社区（无量化数据，仅基于 Twine/Dialogic/Ink/Articy 中文教程可见度估计）、学习曲线（无用户研究，仅基于直觉）

低置信度维度建议在 §5 反对意见中给出 dissent。

---

## §5 调研 Agent 推荐 + 反对意见

> 本段 4 个子段：5.1 = 调研 agent（即本会话）的明示推荐 + 主要论据；5.2 = gap 证据清单（来自调研事实）；5.3 = 反对意见（dissent）含 2 个反向 case + 1 个跨候选共同质疑；5.4 = 事实 / 推断 / 判断分离（透明度）。

### 5.1 Agent 推荐：v_incremental

**调研 Agent 明示推荐 v_incremental**（详 §3.3）。主要论据 5 条：

1. **§4 评分双向不输**：v_incremental 是唯一两个加权方向（保守工程 19 / 生态扩张 17）都不输的方案；v_thin_export 在生态扩张维度仅 12（彻底落败），v_full_ir 在保守工程维度仅 11（彻底落败）。**v_incremental 是真正的 Pareto 平衡点**。
2. **Forgewright 哲学一致**：保 T-3Y capability surplus 完整（同 v_thin_export），不违反 ADR-004 / 006 / 027（同 v_thin_export），但显式承认借鉴主流原语——不同于 v_thin_export 的"封闭"态度。
3. **作者签字原则**："如果主流做法能实现相同效果，那就尽量按主流做法来"——v_incremental 直接实施这一原则；v_thin_export 实质上违反此原则（明知 Ink LIST、Twine ifid 等有借鉴价值仍不学）。
4. **工程节奏可控**：4 个 follow-up ADR 各自独立排期；T-3Y-1 工程会话只需要 ADR-034.1（knowledge namespace），其他 follow-up 阶段 3-4 慢节奏。当前阶段立即工程量仅 ~3 周。
5. **D5 滑坡防御**：v_incremental 独有的"明示停止条件"是 v_full_ir 不具备的防御机制；可应对"为对齐而对齐"诱惑。

### 5.2 Gap 证据清单（10 项，来自调研事实）

> 本表是 ADR-034 立项的核心证据。每条 gap 标记 **涉及层** + **严重度** + **处置建议** + **ADR-034 归属**。

| Gap# | 现象 | 涉及层 | 严重度 | 处置建议 | ADR-034 归属 |
|---|---|---|---|---|---|
| 1 | 行内条件文本缺失（v0.3 narration 是 plain string；Ink + SugarCube 有原生） | v0.3 only | 中 | 阶段 4 前后立 ADR-034.3 加 inline 微语言 | follow-up |
| 2 | once-only / sticky 选项标记缺失（v0.3 + T-3Y 都用 condition + flag 模式） | 两层 | 中 | 立 ADR-034.2 加 `choice_visibility` enum | follow-up |
| 3 | Sub-graph call-with-return tunnel 缺失 | v0.3 only | 低 | 保持现状（与 DAG 哲学冲突） | 不入 |
| 4 | chapter 级元数据缺失（Twine 有 StoryData + ifid 必填） | 两层 | 低 | 阶段 4 立 ADR-034.4 加 `chapter.ifid` | follow-up |
| 5 | T-3Y `scene_metaparams.culprit_id` 违 ADR-027 世界观不可知 | T-3Y only | 中 | 改 `dict[str, JSON]` + 项目配置层 | **留作者拍板**（设计争议点 #1） |
| 6 | T-3Y `scene_reveals.trigger_node_ids` 多路径顺序未明 | T-3Y only | 中 | 用 ordered flag set 模式（参考 Ink LIST） | **留作者拍板**（设计争议点 #2） |
| 7 | T-3Y `scene_seeds.coverage_strategy` validator 强保证不可行 | T-3Y only | 中 | v0.1 用弱保证（参考 Articy fallback()） | **留作者拍板**（设计争议点 #3） |
| 8 | v0.3 无 information disclosure 原语（无 LIST / Glossary 类） | v0.3 only | 中 | **直接进 ADR-034**，立 ADR-034.1 加 `knowledge.*` 命名空间 | **核心** |
| 9 | `state_effect.remove` op 与 T-3Y "不模拟玩家遗忘" 冲突 | T-3Y vs v0.3 schema | 中 | 立 "player-monotonic state path 原则"——LLM 生成内容禁 remove `flag.player_*` / `knowledge.*` / `relationship.*` | **留作者拍板**（设计争议点 #4） |
| 10 | T-3Y `player_known_info.all_known_info_summary` 是自然语言字段不适合 schema | T-3Y only | 中 | 拆 schema-typed list（进 schema）+ 生成层 summary（不进 schema，由 T-3.5 写 prompt context）| **留作者拍板**（设计争议点 #5） |

**10 个 gap 的分布证据强烈支持 v_incremental**——1 个直接进 ADR-034（Gap 8）+ 3 个 follow-up（Gap 1/2/4）+ 5 个 T-3Y 设计争议点（Gap 5/6/7/9/10）+ 1 个保持现状（Gap 3）。这就是 v_incremental "局部对齐 + 4 个 follow-up + 留 T-3Y 争议给作者拍板"的具体落地形态。

**附注**：T-3Y 进展报告 §8 的 4 个待答设计问题在 4 工具中的业界处理（即 progressive disclosure / coverage_strategy / scene_metaparams / scene_static_inputs）的详细对照，已 fold 进 §2 per-tool 清单的"关键差异"段（每工具子段末尾的对比说明）。**关键发现**：4 工具中 0 个有 native 支持——T-3Y 在领跑业界，不在追赶。

### 5.3 反对意见（Dissent）

**Dissent A · 推 v_thin_export（更保守）**

论据：

- §3.3 R1 滑坡风险虽立 D5，但"为对齐而对齐"判定的主观性（R5）让 D5 在实战中可能失效；4 个 follow-up 落地后必然有更多新对齐机会出现，最终滑坡到 v_full_ir
- 阶段 3-4 工程量本就紧（T-3Y / T-3.X 主线 + 阶段 4 开源剥离），多 4 个 follow-up ADR 是 12-17 周额外工程量，可能耽误主线
- T-3Y capability surplus 是 Forgewright 真正差异化优势；追求 ifid + once/sticky 等"小对齐"看似无害，实际上**分散注意力**，让作者审 ADR 时心智成本上升
- 阶段 4 开源剥离时若发现需要更多对齐，可临时升级到 v_incremental；**当前不需提前承诺**

**Dissent B · 推 v_full_ir（更激进）**

论据：

- §2 4 工具 per-tool 清单显示业界已 stabilize 多年（Articy Template / Twine StoryData / Ink LIST 都 5+ 年）；v_full_ir 不是"追赶移动靶"
- v_incremental 的 D5 停止条件等于自我设限——若某对齐机会真有 capability 价值（如完整对接 Ink LIST 的 multi-stage reveal 语义），D5 可能错过
- **中文社区门槛是 strategic concern**：评分 §4 中 v_full_ir 7 vs v_thin/incremental 4-5 的差距，借力 Twine + Dialogic 中文教程生态的价值在长期被严重低估
- 工程量虽大（4-5 月），但全部摊到阶段 4 开源剥离阶段，**不阻塞当前阶段 0-3 主线**

**Dissent C · 跨候选共同质疑（低置信度维度未做用户研究）**

§4.3 已声明的低置信度维度（中文社区、学习曲线）可能严重影响结论——所有 3 个候选都建立在直觉评分上。建议 ADR-034 立项前进行 1-2 周用户研究（如调研 Twine 中文用户对 JSON 写作的接受度），把这两维度从直觉升级为数据。**这是对 3 个候选的共同质疑**。

### 5.4 事实 vs 推断 vs 判断分离（透明度）

| 类别 | 内容 | 可被反驳的方式 |
|---|---|---|
| **事实**（来自 subagent 调研，可验证） | 4 工具 per-tool 机制清单（§2 全部）；4 工具对 T-3Y 4 设计问题的处理；Forgewright v0.3 schema 实际字段 | 重新调研验证 |
| **推断**（基于事实 + 设计原则） | 工程量 estimation（参考开源 importer 代码量）；future-proof 评分（业界升级历史）；3 candidates 的 distinct 设计哲学 | 提供更准确的工程量参考 / 历史数据 |
| **判断**（agent 主观，可被反对） | 推荐 v_incremental；§4 评分（尤其低置信度维度）；Dissent A/B 的相对说服力 | 给出不同判断标准 / 加权 |

---

## §6 ADR-034 草案（status=proposed）

> **本段直接作为 ADR-034 的 fixation 输入** — 待作者拍板后合入 `/docs/DECISIONS.md`。

**标题**：ADR-034 · 选 v_incremental 路线 — Schema 主体 AI 生成 + 局部对齐主流原语 + 阶段 4 单向导出 shims

### 6.1 状态

**proposed**（2026-05-15 调研报告产）；5 个 T-3Y 设计争议点已由作者拍板（2026-05-18，全部接受 Agent A 倾向，详 §7.4）；待 L2 综合规划师评审 + 合入 `/docs/DECISIONS.md`。

### 6.2 背景

2026-05-15 T-3Y L2 综合规划师会话识别风险——Forgewright dialogue_graph schema 凭直觉自设计，未对标业界事实标准，未来集成 / 迁移 / 用户群扩展可能撞兼容性壁。L2 建议立 ADR-034 候选评估 Forgewright JSON schema 与业界 4 工具（Ink / Articy / Twine / Dialogic）的关系。本 ADR 是 ADR-034 调研后的拍板。

调研覆盖 Ink、Articy:Draft、Twine SugarCube、Dialogic 2.x 四工具核心数据模型 + T-3Y 进展报告 §4/§5/§8 的字段集对照 + 4 个待答设计问题的业界答案。详细机制对比见研究报告 §3，gap 分析见 §4，可行性论证见 §5。

**调研核心发现**：

1. 4 工具中**没有一个采用 Forgewright "JSON-native（源 = 运行时）"模式**——3 个用 DSL 源 + 编译产物，1 个用私有编辑期格式 + JSON 导出。架构层级根本异构。
2. T-3Y 进展报告提出的 4 个待答设计问题（scene_metaparams / progressive disclosure / coverage_strategy / scene pre-post），4 工具**0 个原生支持**——T-3Y 是在领跑业界，不是追赶。
3. Forgewright v0.3 落后业界的真实点集中在 3 处：行内条件文本 / 一次性选项标记 / 信息揭露原语（详研究报告 §4 gaps 1/2/8）。

### 6.3 决策

**选 v_incremental（详 §3.3）**：Schema 主体 AI 生成路线 + 局部对齐主流原语 + 阶段 4 单向导出 shims，**不立格式中立 IR**。10 个具体子决策（D1-D10）：

#### D1. Schema 定位措辞

Forgewright dialogue_graph + chapter + scene schema 在 `/docs/SCHEMA_v0.3.md`（或后续修订版）的开篇定位为：

> **AI-generation-aware schema with schema-first validation and single-direction export adapters to Twine / Dialogic / Ink. Not a format-neutral intermediate representation.**
> 中文：为 AI 生成内容流水线优化的 schema，schema-first + validator 驱动；提供单向导出适配器到 Twine / Dialogic / Ink 等业界宿主；**不是格式中立 IR**。

#### D2. 接受 T-3Y 进展报告 §4 + §5 草案的核心结构

scene_metaparams / scene_reveals / scene_seeds / scene_static_inputs/outputs / player_known_info / foreground_goal / background_seeds 等字段是 Forgewright 对业界的**真正 capability surplus**，应作为 Forgewright 差异化优势 documented（写入 SCHEMA_v0.4 / ROADMAP）。

#### D3. 加 `knowledge.*` 作为第 6 个 state path 命名空间

直接对标 Ink LIST + Articy Glossary 主流做法（详研究报告 §4 Gap 8）。具体语义 + pattern + 与 player_known_info 的耦合关系，由 ADR-016 v0.4 修订承接。本 ADR 仅做立项授权。

#### D4. scene_metaparams 字段形态

`dict[str, JSON]` 自由形态 + 项目配置层定义字段名 enum（类似 ADR-029 技能体系项目配置层模式）；schema 不预设具体字段名。**保 ADR-027 世界观不可知性原则**（详研究报告 §4 Gap 5 / §7.B Conflict 1）。

#### D5. scene_reveals 多路径语义

用 **ordered flag set 模式**（详研究报告 §4 Gap 6 / §7.B Conflict 2）。每个 trigger_node 触发时 `+= stage_n`，completion_node 检查 `stage_n_set ⊇ required_stages`。不做隐式 list 顺序解析。参考 Ink LIST 主流做法。

#### D6. scene_seeds.coverage_strategy validator 实现

v0.1 接受**弱保证**（每场景退出时检查 flag 是否被 set；无 path enumeration）；强保证推迟到未来 ADR 修订（详研究报告 §4 Gap 7）。参考 Articy fallback() 主流做法的工程节奏。

#### D7. 立 follow-up ADR 候选清单

ADR-034 立项**不**一次性解决所有 schema gap。下列 follow-up ADR 候选独立排期：

| Follow-up ADR 候选 | 内容 | 优先级 |
|---|---|---|
| ADR-034.1 | `knowledge.*` 命名空间落地（ADR-016 v0.4 修订）| **高**（T-3Y 工程依赖）|
| ADR-034.2 | Option.choice_visibility 字段（once / sticky enum）| 中（gap 2 对齐 Ink + Articy）|
| ADR-034.3 | node.narration inline conditional text 微语言 | 低（阶段 4 前后）|
| ADR-034.4 | chapter.ifid 字段（UUID v4，对齐 Twine StoryData）| 低（开源剥离阶段）|

#### D8. 阶段 4 开源剥离时加单向导出适配器

`forgewright-to-twine.py`（输出 .twee）+ `forgewright-to-dialogic.py`（输出 .dtl）作为开源剥离阶段的标配工具。承认 lossy（Forgewright capability surplus 在导出时被裁），但保留 inverse direction 验证（导出后能否在 Twine / Dialogic 中播放 = 验证集）。

**Ink / Articy 不在 v0.1 适配器范围**——架构异构性大，工程量高，价值低（用户用 Forgewright 就不会切回 Ink）。

#### D9. ADR-034 本身不修改任何现有 schema 或代码

ADR-034 仅做立项决定 + 措辞修订（SCHEMA_v0.3.md / SCHEMA_v0.4 草案的定位段）。具体 schema 字段变更由 follow-up ADR 各自承接。

#### D10 · 明示停止条件（v_incremental 独有）

当某次对齐候选识别为"为对齐而对齐"——即业界原语与 Forgewright 哲学冲突或 capability surplus 必然受损——时立即停止，**不再继续对齐方向**。每候选 follow-up ADR 必须明示哲学冲突检查（ADR-004 / 006 / 027 合规审查 + capability surplus 影响评估）。这是 v_incremental 对"滑坡到 v_full_ir"的核心防御。

#### D11 · Player-monotonic 原则（Gap 9 落地，2026-05-18 作者拍板）

Schema 层强制：LLM 生成的 state effects 在以下 **monotonic 命名空间**下，只允许 `set` / `inc` / `add`，**禁止** `dec` / `remove`：

- `flag.player_*` —— 玩家见证 / 行为 flag（玩家不会忘记做过的事）
- `knowledge.*`（ADR-034.1 新增）—— 玩家知识（玩家不会忘记知道的事实）

**不在 monotonic 清单内**（即允许双向变化）：

- `player.traits` / `player.bonds` —— 性格特征 / 羁绊可被剧情移除（如背叛 → 羁绊消失；喝酒 → 观察能力下降）
- `relationship.<slug>.*`（含 trust / fear / affinity 等）—— 关系状态值自然波动
- `faction.<id>.*` —— 阵营声誉双向
- `world.*` —— 世界状态双向
- `player.gold` / `player.health` 等数值 stat —— 自然双向

**作者手填内容**（`generation_trace.source == "human"`）不受此规则约束（生产期修订可破例）。

Validator 实现示意：

```python
MONOTONIC_NAMESPACES = [r"^flag\.player_.+", r"^knowledge\..+"]
# 规则：generation_trace.source == "llm" 的 effect，path 匹配 MONOTONIC_NAMESPACES 时：
#   - op 必须 ∈ {set, inc, add}
#   - 违反则 validator 拒收
```

**理由**：T-3Y §5.2 拍板"不模拟玩家遗忘——默认玩家记住一切"。但 v0.3 schema 的 `state_effect.op` enum 含 `dec` / `remove`，LLM 可能不当生成"玩家忘了 X"。本 D11 在 schema 层补防御。**清单只 2 条**（不含 traits / bonds），因为作者拍板（2026-05-18）：traits / bonds 属于身份层标签但**可被剧情移除**（背叛 → 羁绊消失；喝酒 → 观察能力下降），不算 monotonic。

### 6.4 替代方案

| 替代 | 简称 | 内容 | 详 |
|---|---|---|---|
| A1 | v_full_ir | 立"格式中立 IR"，4 个双向适配器 | §3.1 |
| A2 | v_thin_export | 不立 IR，只 2 个单向 shim，不立 follow-up | §3.2 |
| A3 | 缓议 | 推迟到 T-3Y-1 后或阶段 4 立项前 | §7 Path 4 |
| A4 | 完全闭门造车 | 不立任何对外适配 | （未在 §3 单列）|

### 6.5 否决理由

| 替代 | 否决理由 |
|---|---|
| **A1 v_full_ir** | Schema 体积爆炸违反 ADR-004 极简；T-3Y capability surplus 在导出路径必然降级（progressive disclosure → flatten；coverage strategy → 丢弃）；工程量 17-21 周阻塞主线；4 适配器永续 maintenance（详 §3.1 R1+R2）|
| **A2 v_thin_export** | 违反作者签字"主流能实现相同效果则推主流"原则——明知 Ink LIST、Twine ifid 等有借鉴价值仍不学；社区采纳门槛过高（中文社区评分 4）；阶段 4 后悔升级成本 12-17 周（详 §3.2 R1+R5 + §5.3 Dissent A 反驳）|
| **A3 缓议** | T-3Y 4 个待答设计问题（progressive disclosure / coverage / metaparams / scene pre-post）阻塞 T-3Y-1 工程会话启动；缓议会延迟主线（详 §5.1 推荐论据 4）|
| **A4 完全闭门** | 失去阶段 4 工具生态价值；用户群扩张被永久封顶；开源剥离阶段意义大幅缩水 |

### 6.6 后果

1. Forgewright schema 在 `/docs/SCHEMA_v0.3.md`（或后续修订）开篇正式定位为"AI-generation-aware schema"（D1）
2. ADR-016 v0.4 修订承接 D3（`knowledge.*` 命名空间）
3. T-3Y-1 工程会话启动时按 D4 / D5 / D6 实现 scene_metaparams / scene_reveals / scene_seeds 字段
4. 4 个 follow-up ADR 候选（D7）独立排期，不阻塞 ADR-034 本身合入
5. 阶段 4 开源剥离阶段加 2 个单向导出适配器（D8）
6. ADR-034 本身不修改任何现有 schema 或代码（D9）；只做立项 + 措辞
7. **5 个 T-3Y 设计争议点**（§5.2 Gap 5/6/7/9/10）**已由作者拍板**（2026-05-18，全部接受 Agent A 倾向，详 §7.4）—— Gap 9 落地为 D11 player-monotonic 原则（monotonic 清单 = `flag.player_*` + `knowledge.*` 两条；traits/bonds 归双向）；Gap 5/6/7/10 进入 T-3Y-1 工程会话实现

### 6.7 关联讨论

- ADR-004（极简）：D1 + 否决 A1 论证基础
- ADR-006（SOT）：本 ADR 不触动 SOT 哲学
- ADR-007（核心是 Runtime 不是 Parser）：D1 措辞与之一致——schema 服务运行时与生成器，不服务 parser
- ADR-016（state path 命名空间）：v0.4 修订承接 D3
- ADR-027（世界观不可知）：D4 的核心约束
- ADR-028（引擎与宿主分离）：D8 适配器的归属层（host adapter，非 engine）
- ADR-029（技能体系项目配置层）：D4 的模式参考

**关联文档**：

- 调研报告：[2026-05-15_ADR-034_schema_ir_research.md](2026-05-15_ADR-034_schema_ir_research.md)（本档）
- T-3Y 进展报告：[2026-05-15_T-3Y_design_progress.md](2026-05-15_T-3Y_design_progress.md)
- ROADMAP：阶段 4 开源剥离段加 D8 适配器条目

**签字**：

- 调研者：Claude (ADR-034 调研会话，2026-05-15)
- 作者：⏸ 待
- L2 综合规划师评审：⏸ 待
- 起草日期：2026-05-15

---

## §7 拍板指引

> 本段提供 **4 条按"最看重维度"分支的拍板路径**。每条都是具体可执行的决策树；作者签字时按自己当前最看重的维度选择即可。Agent 推荐方案见 §5.1（v_incremental）；本段是给"不同优先级"的作者一个 fallback 选择树。

### 7.1 4 条拍板路径

**Path 1 · 如果你最看重 当前阶段工程纪律 + T-3Y 主线不被拖累 → 选 v_thin_export**（详 §3.2）

- 适用场景：当前阶段 3-4 工程负担已重 + 阶段 4 之前不打算做开源剥离 + 对 Forgewright 在闭门状态下能自验证价值有信心
- 风险接受：中文社区采纳门槛高（评分 4）；阶段 4 后悔升级到 v_incremental 成本 12-17 周
- 后续动作：ADR-034 文档定位"AI generation schema + 单向 shim only"；不立 follow-up；阶段 4 加 2 个 shim

**Path 2 · 如果你最看重 主流原语借鉴 + Forgewright 差异化优势保留 + 工程节奏可控 → 选 v_incremental**（详 §3.3 + §6 推荐）

- 适用场景：同意作者签字"主流能实现相同效果则推主流"原则 + 想保 T-3Y capability surplus 完整 + 接受 4 个 follow-up ADR 独立排期
- 风险接受：D5 滑坡防御的有效性；ADR 列表膨胀
- 后续动作：ADR-034 文档定位"selective alignment"；立项 ADR-034.1（knowledge.*）入 T-3Y-1 工程依赖；ADR-034.2-034.4 阶段 3-4 慢节奏排期；阶段 4 加 2 个 shim
- **本 Path = 调研 Agent 推荐方案**

**Path 3 · 如果你最看重 工具生态扩张 + 长期影响力 + 中文社区入口 → 选 v_full_ir**（详 §3.1）

- 适用场景：Forgewright 的长期目标是成为业界 IR + 接管"AI 生成内容跨工具"赛道 + 接受 4-5 月工程投入
- 风险接受：ADR-004 极简 / T-3Y capability surplus 可能受损；4 适配器永续 maintenance；跨工具 silent semantic drift
- 后续动作：ADR-034 文档定位"格式中立 IR"；阶段 0-3 立即启动 schema 扩展（~3 工程周）；阶段 4 启动 4 个双向适配器

**Path 4 · 如果你最看重 决策可逆性 + 当前阶段不被打断 + 留未来选项空间 → 选 缓议（不立 ADR-034）**

- 适用场景：信息不足以判断 v_thin/incremental/full 三选 + 想先解决 T-3Y 4 个设计问题再回头看 schema IR
- 风险接受：T-3Y 4 个待答设计问题（progressive disclosure / coverage / metaparams / scene pre-post）将带着不确定性进入 T-3Y-1 工程，可能 retrofit 成本高
- 后续动作：本调研报告作为参考留档；ADR-034 推迟到 T-3Y-1 后或阶段 4 立项前；不阻塞当前主线

### 7.2 致 ADR-035 调研协同提示

> 本段提供 ADR-034 调研中识别的关键 trade-off 信息，作为 ADR-035 拍板的输入。

**关键发现 1 · Dialogic 2.x 的 timeline format 是 .dtl 文本（非 JSON）**

调研事实：Dialogic 2.x 的 `DialogicTimeline` 资源**没有** `from_json()` / `as_json()` API；canonical format 是 `.dtl` 文本。**对 ADR-035 的影响**：若选 Dialogic 作为 L3 宿主，**必须写 `forgewright-to-dtl` 转换器**——不能直接 ingest Forgewright JSON。

**关键发现 2 · Dialogic 的 host 集成模式 = 共享变量 + 信号**

Forgewright 5 命名空间 state path（+ 未来 `knowledge.*`）**不直接映射**到 Dialogic 命名空间扁平 var；适配层需要做 namespace flattening，且失去 5 命名空间的语义保护（validator 在 Dialogic 内无法运行）。

**关键发现 3 · T-3Y 草案的 capability surplus 在 Dialogic 宿主里完全无法消费**

Dialogic 2.x 完全缺 scene-level pre/post + progressive disclosure + coverage strategy + scene metaparams + player_known_info 双层结构。若选 Dialogic 作为宿主，**T-3Y 全部 capability surplus 都需在 forgewright-side 实现**，导出时退化为扁平 if/elif/else event。

**强烈建议 ADR-035 评估**：自研 Godot scene 系统 / Web 自研 / Ren'Py 自研路线——不要选 Dialogic / Ink / Twine 作为唯一宿主。

### 7.3 决策时机

ADR-034 的合适拍板时机：**T-3Y-1 工程会话启动前**（因 ADR-034.1 knowledge.* 命名空间是其工程依赖）。若选 Path 4（缓议），需要在 T-3Y-1 启动前重新评估。

### 7.4 5 个 T-3Y 设计争议点 · 作者拍板结果（2026-05-18）

> 5 个争议点已由作者（outsiderrr）于 2026-05-18 拍板，**全部接受 Agent A 倾向**。详细讨论见 §5.2 gap 表 + §5.3 dissent。Gap 9 落地为 §6.3 D11 player-monotonic 原则。

| 争议点 | Agent A 倾向 | 作者拍板（2026-05-18）|
|---|---|---|
| Gap 5 · scene_metaparams 字段形态 | `dict[str, JSON]` + 项目配置层定义字段名 enum | ✓ **接受 A**（参考 ADR-029 项目配置层模式；保 ADR-027 世界观不可知）|
| Gap 6 · scene_reveals 顺序语义 | ordered flag set 模式（参考 Ink LIST）| ✓ **接受 A**（依赖 ADR-034.1 `knowledge.*` 命名空间先落地）|
| Gap 7 · coverage_strategy validator 强度 | v0.1 弱保证；v0.2 升级到强保证留口子 | ✓ **接受 A**（mandatory_with_fallback 用 flag set 检查，不做 path enumeration）|
| Gap 9 · player-monotonic 原则 | 在 ADR-034 立此原则 | ✓ **接受 A**；monotonic 命名空间清单 = `flag.player_*` + `knowledge.*` 两条；**traits / bonds 归双向**（可被剧情移除：背叛 → 羁绊消失；喝酒 → 观察能力下降）；落地为 §6.3 D11 |
| Gap 10 · player_known_info summary 字段归属 | 拆分 — schema 层只保 `list[knowledge_id]`；summary 由生成层管理 | ✓ **接受 A**（T-3.5 批量调度器加 prompt-time-context 字段记录 summary，不进 node schema）|

**下游影响**：

1. ADR-034 §6.3 加 **D11**（player-monotonic 原则）落地 Gap 9
2. T-3Y-1 工程会话按 D4 / D5 / D6 / D11 + 上述拍板实现 schema 字段
3. ADR-034.1（`knowledge.*` 命名空间）是 T-3Y-1 工程**硬依赖**——必须先落地

---

## §9 附录：调研覆盖率自评 + 资料源

### 9.1 调研覆盖率自评

| 维度 | 覆盖率 | 备注 |
|---|---|---|
| Ink 数据模型 | 95% | 30+ 页 web tutorial + GitHub spec + JSON runtime format 全读 |
| Articy 数据模型 | 75% | 闭源；二手资料反推；未亲验 GUI 导出 |
| Twine SugarCube 数据模型 | 90% | 文档完整；未亲玩交互 |
| Dialogic 数据模型 | 90% | 文档 + GitHub 仓库；未亲验 .dtl 双向转换 |
| Forgewright v0.3 schema | 100% | 全部 12 个 schema 文件 + SCHEMA_v0.3.md + ADR-006/016/027 read |
| T-3Y 进展报告 | 100% | 全文 355 行 read |
| 4 个 T-3Y 设计问题业界对照 | 95% | 4 工具均给出明确答案；唯一 partial 覆盖项是 Articy 的 fallback() 1.2+ 的精确触发时机 |
| §7.B 设计争议点 | 100%（自评）| 5 个 conflict 识别完毕；可能有遗漏由作者补充 |

### 9.2 资料源（按 §3 表行号引用）

**Ink**：
- [Writing with ink — full reference](https://github.com/inkle/ink/blob/master/Documentation/WritingWithInk.md)
- [Ink JSON runtime format spec](https://github.com/inkle/ink/blob/master/Documentation/ink_JSON_runtime_format.md)
- [inkle/ink-library Snippets](https://github.com/inkle/ink-library)

**Articy**：
- [scenarioworld/articy-js TypeScript schemas](https://github.com/scenarioworld/articy-js)（**最高价值** —— 反推 schema 主依据）
- [articy.com Help Center](https://www.articy.com/help/adx/)
- [articy:draft X Basics Scripting](https://www.articy.com/en/adx_basics_scripting/)

**Twine SugarCube**：
- [SugarCube 2.x docs](https://www.motoslave.net/sugarcube/2/docs/)
- [Twee 3 Specification (IFTF)](https://github.com/iftechfoundation/twine-specs/blob/master/twee-3-specification.md)
- [Twine Cookbook](https://twinery.org/cookbook/)

**Dialogic**：
- [Dialogic 2 Documentation](https://docs.dialogic.pro/)
- [GitHub: dialogic-godot/dialogic](https://github.com/dialogic-godot/dialogic)
- [DeepWiki Dialogic mirror](https://deepwiki.com/dialogic-godot/documentation/)

**Forgewright internal**：
- [SCHEMA_v0.3.md](../../SCHEMA_v0.3.md) + [SCHEMA_v0.md](../../SCHEMA_v0.md) + [SCHEMA_v0.2.md](../../SCHEMA_v0.2.md)
- [DECISIONS.md ADR-006 / 016 / 027 / 029](../../DECISIONS.md)
- [/schema/*.schema.json](../../../schema/)
- [/content/test_scene_v0/scene.json](../../../content/test_scene_v0/scene.json)
- [T-3Y 进展报告](2026-05-15_T-3Y_design_progress.md)

---

## §10 版本

- **v0.1**（2026-05-15）：ADR-034 调研会话产出。等待作者签字 + L2 综合规划师评审。
- **v0.2**（2026-05-18）：5 个 T-3Y 设计争议点（§5.2 Gap 5/6/7/9/10）作者拍板完成（全部接受 Agent A 倾向）；§6.3 加 D11 player-monotonic 原则（monotonic 清单 = `flag.player_*` + `knowledge.*` 两条）；§7.4 拍板表更新；§6.1 状态 / §6.6 后果 / §10 版本同步修订。
- **v0.3+**（未来）：L2 综合规划师评审吸收后修订；合入决策正式落 `/docs/DECISIONS.md` ADR-034 段。

---

**文档边界声明**：本档为研究报告 + ADR-034 候选草案。**不修改任何代码 / schema / 既有 ADR**（严守 CLAUDE.md Rule 2 + Rule 10）。最终立 / 不立由作者签字 + L2 综合规划师评审决定。

