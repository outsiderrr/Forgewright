# SCHEMA_v0.md — 阶段 0 对话图 Schema 设计

> 本文件是**设计说明**，不是 JSON Schema 源文件。JSON Schema 源文件由后续任务写入 `/schema/` 目录（ADR-003、CLAUDE.md 规则 6）。
>
> 本文件只描述抽象结构、字段含义、来源溯源、阶段归属。具体场景示例（如某个酒馆、某个 NPC）由下一个任务完成——本文件只给字段占位符级别的机械示例。

---

## 0. 文档定位与边界

### 0.1 覆盖的对象

本文件只设计与**对话图**相关的五类对象：

1. `DialogueGraph`——一张对话图（阶段 0 对应一个"场景"）
2. `Node`——对话图中的节点
3. `Option`——节点上玩家可选的选项（图的出边）
4. `StateEffect`——选项触发时对状态总线的变更意图
5. `StateCondition`——可见性/可用性/到达性的布尔条件

### 0.2 不覆盖的对象（本文件外）

以下 Schema 在本文件范围外，将另开任务：

- **世界本体 Schema**（`/state/ontology/`，ADR-006）——角色花名册、地点、物品、派系关系表、时间线的结构
- **状态总线 Schema**（`/state/` 的读写层）——阵营时钟、变量、玩家持久数据的快照结构
- **生成流水线 Schema**（`/generator/`，阶段 1+）——候选 JSON、intent tag、prompt 模板产出
- **评测 Schema**（ADR-009 的三层评测产物）——阶段 2+
- **插件元数据 Schema**（ADR-005 的编剧理论插件产物）——阶段 2+

本文件**会引用**前两者的实体 ID（例如选项的状态效果指向状态总线的键路径，节点的说话者指向本体花名册的角色 ID），但**不定义**它们的内部结构。引用以字符串 ID 形式留接口，具体解析规则由引用 Schema 的任务负责。

### 0.3 来源溯源约定

本文件的每个维度必须注明来源：

- `[ADR-###]`——直接来自某条架构决策
- `[DEBATE §N.N]`——来自 DEBATE_NOTES 的某主题
- `[ROADMAP 阶段 0]`——来自路线图的当前阶段要求
- `[CLAUDE.md]`——来自项目说明书的硬性规则

**未注明来源的维度不应出现在 v0 设计中。** 这是防止"假想场景驱动设计"的硬性纪律。

---

## 1. schema_version 策略

### 1.1 版本字段位置

`schema_version` 字段**仅出现在 `DialogueGraph` 根对象**。一个图是一个版本单元；内部的 Node / Option / StateEffect / StateCondition **不单独携带** `schema_version`。

理由：

- ADR-003 要求 JSON-native，版本位置应可被任意工具一眼识别
- ADR-004 要求运行时极薄，嵌套版本检查会膨胀播放器代码
- 一张图是一个原子校验 / 入库单位，嵌套版本会带来"图版本 A、内部节点版本 B"的不一致风险

### 1.2 版本语义

采用**显式三段式 semver**字符串（例：`"0.1.0"`）。

- **MAJOR**：不兼容变更（字段含义改变、必需字段删除、枚举值含义改变）。需要迁移工具
- **MINOR**：向后兼容的字段添加（新增 optional 字段、预留命名空间落位）
- **PATCH**：措辞性修订（描述文本、注释），结构不变

阶段 0 使用 `"0.1.0"`，对应本文件。

### 1.3 播放器与校验器对未知版本的行为

- **播放器（`/engine`）**：遇到 MAJOR 不同的版本**拒绝加载**，返回明确错误。不尝试降级、不尝试兼容猜测（呼应 ADR-004 极薄原则与 DEBATE §5 的"任何向运行时添加智能的提议都应被否决"）
- **校验器（`/validator`）**：遇到不认识的 MINOR 字段允许通过（向前兼容）；遇到不认识的 MAJOR 拒收

### 1.4 阶段 0 不解决的版本议题

- 跨版本迁移工具：阶段 3+ 再考虑（涉及批量生成的内容资产保值，不是当前阶段范围）
- 内容文件 vs schema 定义的双版本号：当前合一，后续若分裂再讨论

---

## 2. 维度枚举（来源溯源）

**方法论说明**：以下每类对象先列"必须能表达什么"，每项写明来源。字段设计在第 3 节给出；本节只回答"为什么这个维度存在"。

### 2.1 DialogueGraph 的维度

| 维度 | 为什么需要 | 来源 |
|---|---|---|
| 图的唯一标识 | ADR-010 MVP 50–100 个场景需要各自定位 | ADR-010 |
| schema 版本 | 见第 1 节 | ADR-003 + 本文件 §1 |
| 入口节点 | 运行时播放器必须知道从何开始播放 | DEBATE §5（极简播放器） |
| 节点集合 | 一张对话图的主体 | ADR-001 |
| 图所属的场景锚点（本体引用） | 所有 AI 生成内容必须可追溯到本体实体 | ADR-006 |
| 图涉及的角色锚点清单（本体引用） | 校验器可做"图内说话者是否均在本体花名册中"的一致性检查 | ADR-006 + DEBATE §6.5 关系图谱 |
| 生成来源 / 审阅状态标记（预留） | 开发期 AI 生成后需记录是谁生成、是否经主编审阅 | ADR-008 + ADR-010（人工审阅） |
| 插件元数据命名空间（预留） | 编剧理论插件可挂载节拍标签、张力曲线等 | ADR-005 + DEBATE §6.4 Drama Manager |
| 阵营时钟关联声明（预留） | 图可能推进某个时钟或受时钟状态影响 | DEBATE §6.1 Faction Clocks |

### 2.2 Node 的维度

| 维度 | 为什么需要 | 来源 |
|---|---|---|
| 节点唯一标识 | 图内跳转、校验器报错定位 | ADR-001 + ADR-003 |
| 节点类型 | 播放器需要区分"有选项可选" vs "终止节点" vs 可能的"旁白节点"语义 | DEBATE §5（极简播放器需要区分何时阻塞等待玩家输入） |
| 叙述文本 / 场景描述 | 玩家看到的场景描述 | ADR-001 |
| 说话者 / POV（本体引用） | 追溯到本体角色花名册 | ADR-006 |
| 位置锚点（本体引用） | 场景发生在本体的哪个地点 | ADR-006 |
| 节点上的选项集合 | ADR-001 每场景 3–6 个选项 | ADR-001 |
| 节点可达性前置条件 | 开发期校验选项声明的前置条件是否在玩家可达路径上被满足 | DEBATE §1 残余价值（Story2Game 风格编译期校验） |
| 进入时触发的状态效果（预留） | 有些状态变更不由玩家选择驱动，而是"只要到达该节点就应记一笔"——但也可以全部下放到选项上，留给 §6 歧义 | ADR-008 |
| 节拍 / 张力标签（预留） | 编剧理论插件的挂载点 | ADR-005 + DEBATE §2 "生成时先用结构化约束定框架" |
| 生成追溯（预留） | LLM 生成的节点应记录来源，便于返工 | ADR-008（LLM 只能提议） |

### 2.3 Option 的维度

| 维度 | 为什么需要 | 来源 |
|---|---|---|
| 选项唯一标识 | 图内引用、评测日志追踪 | ADR-003 |
| 玩家可见文本 | ADR-001 预生成选项文本 | ADR-001 |
| 目标节点引用 | 图的出边 | ADR-001 |
| 前置条件（StateCondition） | 决定选项是否可见 / 是否可用 | DEBATE §1 残余价值 + ADR-008 |
| 状态效果（StateEffect 列表） | 选中此项对状态总线的变更意图 | ADR-008 |
| 不满足条件时的呈现语义 | 隐藏？灰显？灰显+提示？这是 UI 语义但必须在数据层表达，否则播放器无法决定；留给 §6 歧义 | ADR-001（玩家看到选项）+ §6 歧义 |
| 风格 / 语气标签（阶段 1+ 再加） | 选项质量评测之一（风格一致性） | DEBATE §9.3 |
| 技能轴 / 能力检定（阶段 1+ 再加） | 选项质量评测之一（能力真实性） | DEBATE §9.3 |
| 生成追溯（预留） | 同 Node | ADR-008 |

### 2.4 StateEffect 的维度

| 维度 | 为什么需要 | 来源 |
|---|---|---|
| 操作类型 | ADR-008 要求白名单化的 function-calling | ADR-008 |
| 目标路径（状态总线地址） | 操作作用在哪个键 | ADR-008 |
| 变更值 / 参数 | 具体变更量 | ADR-008 |
| 本体锚点（当操作涉及本体实体时） | 不能对本体外的实体做效果 | ADR-006 + ADR-008 |
| 阵营时钟子类型（预留） | 推进某个时钟 N 格是特定操作 | DEBATE §6.1 |

### 2.5 StateCondition 的维度

| 维度 | 为什么需要 | 来源 |
|---|---|---|
| 比较操作符 | eq / gt / lt / has / has_not 等 | ADR-008 校验语义 |
| 目标路径（状态总线地址） | 检查哪个键 | ADR-008 |
| 比较值 | 与什么对比 | ADR-008 |
| 组合结构（AND / OR / NOT） | 复合条件的必要性；v0 最小形式由 §6 歧义决定 | DEBATE §1 残余价值（复合前置条件） |

---

## 3. 字段设计

**字段标注规则**：

- 🟢 **阶段 0 必需**：不实现则手写 5 节点场景无法跑通 / 无法被校验
- 🟡 **阶段 0 预留**：v0 schema 接受（optional），手写场景可不填；字段名与位置此刻冻结，以备阶段 1+ 无缝填充
- 🔵 **阶段 1+ 再加**：v0 不写进 schema；需要时做 MINOR 或 MAJOR bump

---

### 3.1 DialogueGraph

| 字段 | 阶段 | 类型（抽象） | 说明 |
|---|---|---|---|
| `schema_version` | 🟢 | 字符串（semver） | 第 1 节定义 |
| `graph_id` | 🟢 | 字符串 | 全仓库唯一 |
| `entry_node_id` | 🟢 | 字符串 | 必须存在于 `nodes` 中 |
| `nodes` | 🟢 | 对象映射（id → Node） | 至少 1 个节点；阶段 0 手写场景 5 个 |
| `scene_anchor` | 🟢 | 字符串（本体引用） | 指向本体场景/地点 ID |
| `character_refs` | 🟢 | 字符串数组（本体引用） | 声明本图涉及的角色，便于一致性校验 |
| `authoring` | 🟡 | 对象 | 生成来源 / 审阅状态 / 主编签名；阶段 0 手写场景可空 |
| `plugin_metadata` | 🟡 | 对象映射（plugin_name → 任意对象） | 编剧理论插件的挂载点；核心层不解释内容 |
| `faction_clocks_touched` | 🟡 | 字符串数组 | 图可能推进/受影响的阵营时钟 ID；阶段 0 可空 |
| `title` | 🔵 | 字符串 | 作者审阅界面的显示名；阶段 3+ 再加 |
| `evaluation_metadata` | 🔵 | 对象 | 评测锚点（期望关键路径等）；ADR-009 第二/三层，阶段 2+ |

---

### 3.2 Node

| 字段 | 阶段 | 类型（抽象） | 说明 |
|---|---|---|---|
| `node_id` | 🟢 | 字符串 | 图内唯一 |
| `type` | 🟢 | 枚举字符串 | 具体枚举值留 §6 歧义待裁定 |
| `narration` | 🟢 | 字符串 | 玩家看到的场景/对白文本 |
| `speaker_ref` | 🟢 | 字符串（本体引用）或 null | null 表示旁白 |
| `location_ref` | 🟢 | 字符串（本体引用） | 继承自图层 `scene_anchor` 或细化 |
| `options` | 🟢 | Option 数组 | 类型为"终止节点"时应为空；语义留 §6 歧义 |
| `reachability_condition` | 🟡 | StateCondition 或 null | 节点可达性前置条件；阶段 0 手写场景可 null |
| `on_enter_effects` | 🟡 | StateEffect 数组 | 进入节点即应用；是否启用留 §6 歧义 |
| `plugin_metadata` | 🟡 | 对象映射 | 同图层 |
| `generation_trace` | 🟡 | 对象 | LLM 生成来源、prompt hash、审阅者 |
| `author_notes` | 🔵 | 字符串 | 审阅界面用；阶段 3+ |

---

### 3.3 Option

| 字段 | 阶段 | 类型（抽象） | 说明 |
|---|---|---|---|
| `option_id` | 🟢 | 字符串 | 节点内唯一即可；建议全图唯一 |
| `text` | 🟢 | 字符串 | 玩家可见文本 |
| `target_node_id` | 🟢 | 字符串 | 必须存在于同一图的 `nodes` 中 |
| `condition` | 🟢 | StateCondition 或 null | 前置条件；null 表示无条件可选 |
| `effects` | 🟢 | StateEffect 数组 | 选中时触发；可空 |
| `unavailable_behavior` | 🟢 | 枚举字符串 | 不满足 `condition` 时呈现语义；枚举值留 §6 歧义 |
| `generation_trace` | 🟡 | 对象 | 同 Node |
| `plugin_metadata` | 🟡 | 对象映射 | 同图层 |
| `style_tags` | 🔵 | 字符串数组 | 语气/风格标签；阶段 1+ 评测需要 |
| `skill_check` | 🔵 | 对象 | 能力检定；阶段 1+ 才考虑是否引入 |

---

### 3.4 StateEffect

| 字段 | 阶段 | 类型（抽象） | 说明 |
|---|---|---|---|
| `op` | 🟢 | 枚举字符串 | 白名单操作类型；具体枚举值留 §6 歧义 |
| `path` | 🟢 | 字符串 | 状态总线键路径（点分或段数组，留 §6 歧义） |
| `value` | 🟢 | 任意基本类型 | 具体意义由 `op` 决定 |
| `ontology_ref` | 🟡 | 字符串 或 null | 当 `op` 涉及本体实体时填写 |
| `faction_clock_op` | 🟡 | 对象 或 null | 阵营时钟专用子结构；阶段 0 不触发 |
| `atomic_group_id` | 🔵 | 字符串 | 多效果原子性分组；阶段 2+ 再加 |

---

### 3.5 StateCondition

| 字段 | 阶段 | 类型（抽象） | 说明 |
|---|---|---|---|
| `op` | 🟢 | 枚举字符串 | `eq`/`neq`/`gt`/`gte`/`lt`/`lte`/`has`/`has_not` 为候选起点；最终枚举留 §6 歧义 |
| `path` | 🟢 | 字符串 | 同 StateEffect |
| `value` | 🟢 | 任意基本类型 | 与 `path` 指向值比较 |
| `all_of` / `any_of` / `not` | 🟡 | 条件数组 / 条件 | 复合条件结构；阶段 0 是否启用留 §6 歧义 |
| `ontology_ref` | 🟡 | 字符串 或 null | 同 StateEffect |

**注**：`op/path/value` 与 `all_of/any_of/not` 在同一对象内如何互斥表达（"叶条件 vs 复合条件"），属于结构性歧义，见 §6。

---

## 4. 最小机械示例（字段占位符级别）

> 仅用占位符展示字段结构。**无具体情节**。下一个任务将生成含具体场景的示例。

```json
{
  "schema_version": "0.1.0",
  "graph_id": "<graph_id>",
  "entry_node_id": "<node_id_A>",
  "scene_anchor": "<ontology_scene_ref>",
  "character_refs": ["<ontology_character_ref>", "..."],
  "nodes": {
    "<node_id_A>": {
      "node_id": "<node_id_A>",
      "type": "<node_type_enum>",
      "narration": "<narration_text>",
      "speaker_ref": "<ontology_character_ref | null>",
      "location_ref": "<ontology_location_ref>",
      "options": [
        {
          "option_id": "<option_id>",
          "text": "<option_visible_text>",
          "target_node_id": "<node_id_B>",
          "condition": {
            "op": "<condition_op>",
            "path": "<state_bus_path>",
            "value": "<comparison_value>"
          },
          "effects": [
            {
              "op": "<effect_op>",
              "path": "<state_bus_path>",
              "value": "<effect_value>"
            }
          ],
          "unavailable_behavior": "<unavailable_behavior_enum>"
        }
      ]
    },
    "<node_id_B>": { "... ": "..." }
  }
}
```

---

## 5. 显式排除（考虑过但不放进 v0）

以下维度在 ADR / DEBATE_NOTES 中出现过或自然会被提出，但**明确不写入 v0**。

1. **运行时 LLM 调用钩子**（如实时 NPC 反应字段、流式生成锚点）——ADR-002 + DEBATE §1。运行时无 LLM，这类字段永远不该存在，不是"阶段 1+ 再加"而是**永久排除**。

2. **玩家欺诈防御字段**（对白可信度分数、防注入标记）——DEBATE §1。本项目采用选项式交互，无玩家自由输入，**问题不存在**。

3. **NPC 记忆流字段 / 长对话锚点**——DEBATE §9.2。这是 LLM 技术局限问题，属于生成流水线的 prompt 工程范畴，不应出现在对话图数据结构中。

4. **Egri Premise 全局不变量字段**——DEBATE §7 + ADR-005。Premise 是可选插件，核心 schema 对价值观保持中立，不预留 `premise_alignment_score` 之类的字段。若插件需要，用 `plugin_metadata["egri"]` 自行存放。

5. **本地化 / i18n 字段**（多语言 `text` 变体）——阶段 4 开源剥离才考虑。v0 的 `text` 是单语言字符串。

6. **玩家 UI 呈现细节**（字体、颜色、头像、动画 id）——超出阶段 0 基座范围，属于游戏实例层（`/game`）而非对话图数据层。

7. **技能检定 / 掷骰子结构**——DEBATE §9.3 只要求"能力真实性可评测"，不要求 v0 有掷骰机制。ADR-010 MVP 不追求深度机制。作为 `Option.skill_check` 的阶段 1+ 字段存在，但 v0 不写入 schema。

8. **存档 / 读档字段**——存档格式是状态总线的序列化问题，不是对话图的问题。

9. **DSL 语法糖字段**（Ink 风格 knots、Yarn 风格 commands）——ADR-003 + DEBATE §3。v0 不借鉴任何 DSL 概念进入字段设计。

---

## 6. 设计歧义 & 待作者裁定

**以下是我作为执行会话不应自行决定的架构级歧义**。每条给出选项、各选项的影响，**不给推荐默认**。等待作者指示。

### D1. `Node.type` 的枚举值

- **A**：最小枚举 `{"dialogue", "end"}`（dialogue = 有选项可继续，end = 终止）
- **B**：含旁白 `{"narration", "dialogue", "end"}`（narration = 无说话者纯场景描述，dialogue = 有说话者）
- **C**：更细分 `{"narration", "dialogue", "branch_hub", "end"}`（branch_hub = 只做分支聚合，无新文本）

不同选择影响播放器渲染逻辑和校验器对"节点必有 options vs 终止节点 options 必为空"的规则。

### D2. `Option.unavailable_behavior` 的枚举值

- **A**：`{"hide", "disable"}`（隐藏 vs 灰显）
- **B**：`{"hide", "disable", "disable_with_hint"}`（后者额外给玩家提示"为什么不可选"）
- **C**：不放入 schema，完全由 UI 层自定——但这违反 ADR-004"极简运行时"需要确定性数据

### D3. 节点级 `on_enter_effects` 是否启用

- **A**：启用——进入节点即应用效果（便于表达"一旦见过此 NPC 就标记"）
- **B**：不启用——所有状态变更只能由选项触发，节点是纯显示单元

选择 B 更极简，但会强迫某些自然状态变更必须依附在前一个节点的某个选项上，可能不符合作者心智。

### D4. `StateCondition` 的复合结构在 v0 是否启用

- **A**：v0 只支持叶条件（单个 `op/path/value`）；复合条件延后
- **B**：v0 支持 `all_of` / `any_of`；不支持 `not`
- **C**：v0 支持三者 `all_of` / `any_of` / `not`（完整布尔代数）

手写 5 节点场景多数只需 A。但 A 到 B/C 的升级是 MAJOR bump 风险大。

### D5. `path`（状态总线键路径）的表示法

- **A**：点分字符串 `"faction.iron_guild.reputation"`
- **B**：段数组 `["faction", "iron_guild", "reputation"]`

A 对作者手写友好；B 对含点号的键名健壮。状态总线 Schema 未定，此处与其强耦合。建议此条**推迟到状态总线 Schema 任务时再决**，v0 先用占位符 `"<state_bus_path>"` 表述，定义时对齐。

### D6. `StateEffect.op` 和 `StateCondition.op` 的具体枚举值

- 本文件只列候选起点（`set/inc/dec/add/remove` for effects；`eq/neq/gt/gte/lt/lte/has/has_not` for conditions）
- 实际枚举需要与状态总线 Schema 一同确定（ADR-008 白名单化）
- 建议此条同样**推迟到状态总线 Schema 任务**

### D7. `graph_id` / `node_id` / `option_id` 的命名空间规则

- 是否要求全仓库唯一？还是只要求图内唯一？ID 是否可含点/斜杠/UUID？
- 影响校验器跨图引用、生成追溯、评测日志定位

### D8. 生成追溯（`generation_trace`）字段的内部结构

- 虽然标注为 🟡 预留，但"预留"需要有最小结构骨架才能真正保留兼容性
- 可以完全留空（`object`）；也可以先写死几个键（`source: "human"|"llm"`，`prompt_hash: string|null`，`reviewed_by: string|null`）
- 阶段 0 不触发 LLM 生成，但**结构冻结得越早，后续兼容性越好**

---

## 7. 完成报告

### 7.1 产出文件路径

`/docs/SCHEMA_v0.md`（本文件）

### 7.2 字段总数统计

按三类阶段归属分别统计：

| 对象 | 🟢 阶段 0 必需 | 🟡 阶段 0 预留 | 🔵 阶段 1+ 再加 | 小计 |
|---|---|---|---|---|
| DialogueGraph | 6 | 3 | 2 | 11 |
| Node | 6 | 4 | 1 | 11 |
| Option | 6 | 2 | 2 | 10 |
| StateEffect | 3 | 2 | 1 | 6 |
| StateCondition | 3 | 2 | 0 | 5 |
| **合计** | **24** | **13** | **6** | **43** |

### 7.3 每类对象阶段 0 必需字段数

- **DialogueGraph**：6 个（`schema_version`、`graph_id`、`entry_node_id`、`nodes`、`scene_anchor`、`character_refs`）
- **Node**：6 个（`node_id`、`type`、`narration`、`speaker_ref`、`location_ref`、`options`）
- **Option**：6 个（`option_id`、`text`、`target_node_id`、`condition`、`effects`、`unavailable_behavior`）
- **StateEffect**：3 个（`op`、`path`、`value`）
- **StateCondition**：3 个（`op`、`path`、`value`）

### 7.4 遇到的设计歧义

共 **8 条**（D1–D8），**未自行决定**，已在第 6 节列出等待作者裁定。

其中 **D5、D6** 建议推迟到后续"状态总线 Schema"任务一并确定（此时两者强耦合）；**D1、D2、D3、D4、D7、D8** 属于对话图自身设计，需在转入 JSON Schema 编码任务（即 `/schema/` 目录落地）前闭环。

### 7.5 暂停报告

**按 CLAUDE.md 规则 7、规则 8，现在停下等待指示**：

- 第 6 节 8 条歧义中，D1–D4、D7、D8 这 6 条需要作者裁定才能进入 JSON Schema 编码阶段
- D5、D6 可以暂搁，但需要作者确认"推迟到状态总线任务"的处理方式

在作者就上述歧义给出指示前，**不启动** `/schema/` 目录下任何 JSON Schema 文件的编写、**不**自行扩展本文档的字段决定。

---

## 版本

本文件版本：v0.1（阶段 0 对话图 Schema 设计初稿）
最后更新：2026-04-23
