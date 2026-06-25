# SCHEMA_v0.3.md — 项目 Schema 设计基线 · v0.3 增量

> 本文件承接 SCHEMA_v0.md（v0.1.x）+ SCHEMA_v0.2.md（v0.2.0）；记录 v0.3.0 引入的 stage-2 ontology 增量。
>
> **重要（复合版本号语义）**：v0.3.0 是 **ontology 模块**（character / location / clock / chapter）的 MINOR bump，**不是** dialogue_graph schema 模块的 bump。两组 schema 文件版本号**独立演进**：
>
> - 新建 schema 文件首版 const `"0.3.0"`：`/schema/character.schema.json` + `location.schema.json` + `clock.schema.json` + `chapter.schema.json`。
> - 既有 schema 文件 const **保持 `"0.1.1"` 不动**（沿用 SCHEMA_v0.2 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例）：`dialogue_graph.schema.json` + `node.schema.json` + `option.schema.json` + `state_effect.schema.json` + `state_condition.schema.json`。
> - `image_asset.schema.json` 的 const 保持 `"0.2.0"` 不动。
> - 新增字段（如 `node.generation_trace.slot_assignments`，详 §6；以及 ADR-040 的 `node.dialogue`，详 §10）走 **optional + `additionalProperties: false`** 兼容路径，不破 gold scene `/content/test_scene_v0/scene.json`（其 `schema_version` 仍为 `0.1.1`）。
>
> 复合版本号的唯一动机：避免 stage-2 字段扩张破 stage-0/1 验收的 gold standard。详 STAGE_2_TASKS §2.4 / Q2 + ADR-016 schema 版本号策略。

## 1. 增量摘要

阶段 2 起手期（T-2.2）一次性引入：

- **新建** 4 个 schema 文件：`character` / `location` / `clock` / `chapter`（首版 const `0.3.0`）。
- **修改** 1 个 schema 文件：`/schema/node.schema.json` 在 `generation_trace` 字段表追加 optional 子字段 `slot_assignments`（ADR-019；走 optional + `additionalProperties: false` 兼容路径，**不 bump `dialogue_graph` / `node` 的 const**）。
- **扩展** `/state/ontology/waystation.json`：
  - 顶层新增 `system_time` 字段（`scene_count` / `long_rest_count` 双轨；ADR-016）。
  - 顶层新增 `clocks: []` 数组（首版起步空；阶段 2 由作者按需添加；ADR-017）。
  - 顶层新增 `chapters: []` 数组（首版起步空；U-CL-4 强建议前移避免阶段 3 回填；ADR-016）。
  - `entities[type=="character"]` 三个对象（vellin / corvan / aelwin）扩展 `description` / `state_path_slug` / `character_features` / `dramatic_triggers` / `relations`。
  - `entities[type=="scene"]` 一个对象（`scene_waystation_of_iron_oath`）envelope **迁移**：`type` 由 `"scene"` 改为 `"location"`，并新增 `location_type: "scene"` + `description`（v1.0 §2.5 envelope 契约 + §3）。

**保持不变**（v0.3.0 一律不动）：

- `/schema/dialogue_graph.schema.json` / `option.schema.json` / `state_effect.schema.json` / `state_condition.schema.json` / `image_asset.schema.json` 的所有字段语义与 `schema_version` const。
- `/content/test_scene_v0/scene.json`：v0.1.1 数据样例 schema_version 仍为 `0.1.1`。
- `/state/ontology/waystation.json` 中 character entity 已有的 `id` / `display_name` / `visual_assets` 字段。

## 2. Character Schema 定义（`/schema/character.schema.json`）

### 2.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✗ | `"0.3.0"` | 本对象 schema 版本；可省略，若填则必为 `0.3.0`（同 ImageAsset 先例）。 |
| `id` | string | ✓ | `^char_[a-z0-9_]{1,64}$` | envelope 字段（v1.0 §2.5 / Q3）；不引入 `character_id` 冗余名；唯一性由 ontology loader 兜底。 |
| `type` | string (const) | ✓ | `"character"` | envelope 字段；与 location entity `"location"` 互斥；ontology loader 据此分流。 |
| `display_name` | string | ✓ | minLength 1 | 玩家可见名称。 |
| `description` | string | ✓ | minLength 1 | 角色背景描述；prompt context 注入用。 |
| `state_path_slug` | string | ✓ | `^[a-z0-9_]+$` | v1.0 §2.6：state path 命名空间 `relationship.<state_path_slug>.*` 的 slug；默认 = `id` 去 `char_` 前缀。 |
| `character_features` | array of string | ✓ | items minLength 1 | 描述性特征数组（如 `"stoic mercenary"`）；可空。prompt context 注入用。 |
| `dramatic_triggers` | array of object | ✗ | 每项 `{trait, when, how}` 必填 + `priority` / `cooldown_scenes` 可选 | ADR-019 / PZ §4：戏剧义务字段；T-2.5 prompt 模板按 priority 选择触发。 |
| `relations` | array of object | ✓ | 每项 `{target_character_ref, relation_type, narrative_weight}` | ADR-018：嵌入式关系数组（不引入全局表）；narrative_weight 三档语义。 |
| `visual_assets` | array of object | ✗ | items 仅约束 type=object | 阶段 1.5 SCHEMA_v0.2 引入；items 用 generic object（详 §2.3 设计权衡）。可空。 |

`additionalProperties: false`（未声明字段被 schema 拒收）。

### 2.2 留给 image_validator / character_validator / 机械预检器的语义约束（**不在 schema 层表达**）

下列约束**不**在 JSON Schema 中用 `if/then/else` / `oneOf` 表达——SCHEMA_v0.2 P0.1 教训：datamodel-code-generator 与 Gemini schema 子集对复合形态有已知坑。

1. `state_path_slug` 在世界本体内唯一（同一 world 内同 slug 必指同一 character）。
2. `relations[].target_character_ref` 在本体花名册中可解析。
3. `visual_assets` 内每张 ImageAsset 的镜像字段一致性（详 image_asset.schema.json description 第 1-7 项 image_validator 约束）。
4. `dramatic_triggers[].priority` 在 character 内非负去重（让 T-2.5 选择确定）。

### 2.3 visual_assets 字段设计权衡（v0.3 决策）

字段语义沿用 SCHEMA_v0.2 §3 的"嵌入完整 ImageAsset 对象（不通过 asset_id 引用）"策略；但 schema 层**不**用 `$ref: image_asset.schema.json` 约束 items，而是用 generic `{"type": "object"}`。

理由：

1. **避免多文件 cluster 复杂性**：character.schema.json / location.schema.json 若 $ref image_asset.schema.json，则 datamodel-code-generator 会按 cluster 模式生成多文件输出（`character.py` + `image_asset.py`），与现有 dialogue_graph cluster 形态打架，需要在 `regenerate_models.sh` 与 `_postprocess_models.py` 增加大量分支判断。
2. **schema 层不重复表达可由专门 validator 校验的语义**（SCHEMA_v0.2.md §2.2 / §3.2 已确立的哲学）：ImageAsset 完整 shape 校验由 `image_validator` 兜底；character.schema.json 只需保证 visual_assets 是数组且元素是 object。
3. **代价**：character.schema.json 不会拒收一个空 `{}` 作为 visual_assets 元素——但这种数据进入 character entity 也会被 image_validator 在 stage-2 工作流中拒收。

### 2.4 完整示例 JSON

```json
{
  "id": "char_vellin",
  "type": "character",
  "display_name": "Vellin",
  "description": "铁誓驿站现任老板娘。曾在边境军旅短暂服役，如今以中立驿站身份藏匿密信、收容逃兵；外表冷淡且话少。",
  "state_path_slug": "vellin",
  "character_features": [
    "stoic mercenary",
    "驿站老板娘",
    "前边境兵；身上多旧伤"
  ],
  "dramatic_triggers": [
    {
      "trait": "stoic mercenary",
      "when": "被质问过去",
      "how": "沉默几秒后岔开话题",
      "priority": 1
    }
  ],
  "relations": [
    {
      "target_character_ref": "char_corvan",
      "relation_type": "former_brother_in_arms_now_adversary",
      "narrative_weight": "core"
    }
  ],
  "visual_assets": []
}
```

## 3. Location Schema 定义（`/schema/location.schema.json`）

### 3.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✗ | `"0.3.0"` | 同 character；可省略。 |
| `id` | string | ✓ | `^(scene_\|loc_)[a-z0-9_]{1,64}$` | envelope 字段；兼容 `scene_*`（场景级）+ `loc_*`（子位置）双前缀。 |
| `type` | string (const) | ✓ | `"location"` | envelope 字段；与 character entity `"character"` 互斥。 |
| `display_name` | string | ✓ | minLength 1 | 玩家可见名称。 |
| `description` | string | ✓ | minLength 1 | 地点背景描述；prompt context 注入用。 |
| `location_type` | string (enum) | ✓ | `["scene", "sublocation"]` | scene = 场景级（与 dialogue_graph.scene_anchor 一一对应）；sublocation = 子位置。 |
| `parent_location_ref` | string \| null | ✗ | 同 `id` pattern 或 null | sublocation 通常非 null 指向 scene；scene 通常 null。 |
| `visual_assets` | array of object | ✗ | items 仅约束 type=object | 阶段 2 反向给 location 也加（SCHEMA_v0.2 §3.3 预留扩展）；同 character 设计权衡（§2.3）。 |

`additionalProperties: false`。

### 3.2 envelope 迁移说明（v1.0 §2.5 / Q3）

stage-0/1 期间 `/state/ontology/waystation.json` 内 scene_waystation_of_iron_oath 桩态 `type=="scene"`，仅含 `id` / `display_name` / `type` 三个字段。stage-2 起手期（T-2.2）envelope 契约正式化，迁移为：

- `type` 由 `"scene"` 改为 `"location"`（与 location.schema.json `type.const` 一致）。
- 新增 `location_type: "scene"`（保留"这是一个场景级 location"语义，避免信息丢失）。
- 新增 `description` 必填字段（stage-2 prompt context 注入需要）。

迁移影响面：

- `state/tests/test_ontology.py:33` 的 `assert entity["type"] == "scene"` 同步更新为 `assert entity["type"] == "location"` + `assert entity["location_type"] == "scene"`。
- `generator/image_import.py` / `generator/visual_context.py` 等运行时代码引用 `target_type=="scene"` 的是 **ImageAsset 的 `target_type` 字段**（不是 ontology entity 的 `type` 字段）；这些代码路径与本迁移**无关**，不受影响。
- gold scene `/content/test_scene_v0/scene.json` 引用 `scene_anchor: "scene_waystation_of_iron_oath"`，是按 entity id 解析（不按 type），不受影响；validator 闭合性校验同样按 id（详 `validator/consistency_check.py:55-62`）。

### 3.3 留给 graph_validator 的语义约束

1. `parent_location_ref` 闭合性（非 null 时必须可解析回另一 location entity）。
2. `location_type=="sublocation"` ⇒ `parent_location_ref` 通常非 null（warning 级，schema 层不强约）。
3. `dialogue_graph.scene_anchor` 必须解析到 `location_type=="scene"` 的 entity（graph_validator 校验）。

## 4. Clock Schema 定义（`/schema/clock.schema.json`）

### 4.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✗ | `"0.3.0"` | 可省略。 |
| `id` | string | ✓ | `^clk_[a-z0-9_]{1,64}$` | clock 全本体唯一 id。 |
| `name` | string | ✓ | minLength 1 | 人类可读名称。 |
| `scope` | string (enum) | ✓ | `["world", "faction", "environmental"]` | ADR-017 三档分类。 |
| `ticks_total` | integer | ✓ | 1 ≤ x ≤ 20 | PbtA 总格数；schema maximum 20（PZ §3.4 + ADR-017）。 |
| `ticks_filled` | integer | ✓ | minimum 0 | PbtA 当前已填格数；**非 `ticks_current`**（避免与 game-loop counter 混淆）。 |
| `advance_rule` | object | ✓ | `{type, params}` 必填 | 推进规则；`type` 仅四档 event_based 子类。 |
| `tick_effects` | array of object | ✗ | 每项 `{at_tick, effect_op, path, value}` | tick 触发的状态效果；可空（仅作进度展示无 side effect）。 |

`additionalProperties: false`。

### 4.2 advance_rule.type 四子类语义（ADR-017）

| 子类值 | 语义 | 典型 params |
|---|---|---|
| `every_n_scenes` | 每 N 场场景推进一格 | `{n: 2}` |
| `on_long_rest` | 玩家长休时推进一格 | `{}`（参数留空；阶段 2 起步） |
| `on_faction_action` | 阵营做出特定动作时推进一格 | `{faction_id: "iron_oath", action_kind: "patrol"}` |
| `on_player_choice` | 玩家选了带特定 effect 的 option 时推进一格 | `{flag: "iron_oath_full_pursuit"}` |

### 4.3 明示：不存在 `time_based` 子类（ADR-017）

运行时 `/engine` 是 JSON 播放器，**没有真时间**；不允许 `advance_rule.type == "time_based"`。schema enum 不包含此值，validator 拒收任何变体。这是 ADR-002 极简运行时的硬约束。

### 4.4 留给 validator 的语义约束

1. `ticks_filled <= ticks_total`（schema 层无法跨字段表达）。
2. `tick_effects[].path` 落入 ADR-016 五个 state path 命名空间合法性。
3. `tick_effects[].at_tick <= ticks_total`。
4. `id` 全本体唯一性。

### 4.5 完整示例 JSON

```json
{
  "schema_version": "0.3.0",
  "id": "clk_iron_oath_pursuit",
  "name": "铁誓追捕度",
  "scope": "faction",
  "ticks_total": 6,
  "ticks_filled": 0,
  "advance_rule": {"type": "every_n_scenes", "params": {"n": 2}},
  "tick_effects": [
    {
      "at_tick": 6,
      "effect_op": "set",
      "path": "flag.iron_oath_full_pursuit",
      "value": true
    }
  ]
}
```

## 5. Chapter Schema 定义（`/schema/chapter.schema.json`）

### 5.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✗ | `"0.3.0"` | 可省略。 |
| `chapter_id` | string | ✓ | `^chap_[a-z0-9_]{1,64}$` | chapter 全本体唯一 id。 |
| `display_name` | string | ✓ | minLength 1 | 人类可读名称。 |
| `acts` | array of Act | ✓ | 元素见下 | 可空数组（chapter 起步空 acts，作者后续 L3 任务填充）。 |

Act 字段：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `act_id` | string | ✓ | `^act_[a-z0-9_]{1,64}$` |
| `display_name` | string | ✓ | minLength 1 |
| `included_scenes` | array of string | ✓ | 每项 minLength 1；scene_anchor 闭合性留给 graph_validator |

`additionalProperties: false` （chapter 与 act 两层都强约）。

### 5.2 留给 validator 的语义约束

1. `chapter_id` 全本体唯一。
2. `acts[].act_id` 在单 chapter 内唯一。
3. `acts[].included_scenes[]` 内每个 scene_anchor 在本体可解析回 `location_type=="scene"` 的 location entity。

## 6. node.generation_trace.slot_assignments 增量（ADR-019 / §2.4）

### 6.1 增量字段（仅修改 `/schema/node.schema.json`）

`node.generation_trace` 字段表追加 optional 子字段 `slot_assignments`：

| 子字段 | 类型 | 必填 | 一句话语义 |
|---|---|---|---|
| `slot_assignments` | object | ✗ | dict[<slot_id>, {character_ref, assigned_at, source_prompt_hash}]；持久化抽象槽 → concrete character 映射 |

`slot_assignments` 内每个 entry 三键全必填：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `character_ref` | string | ✓ | `^char_[a-z0-9_]{1,64}$` |
| `assigned_at` | string | ✓ | minLength 1 |
| `source_prompt_hash` | string \| null | ✓ | 可 null（作者手填场景无 hash） |

### 6.2 强调：optional + `additionalProperties: false` 兼容路径

- `slot_assignments` 字段不在 `generation_trace.required` 列表内 → 现有 v0.1.x 节点（无 slot_assignments）继续 pass node schema；
- `generation_trace.additionalProperties: false` 仍生效 → 其他未声明字段仍被拒；
- `slot_assignments` 整体可省，省略时 generation_trace 仍合法；
- **关键决策（v1.0 §2.4）**：dialogue_graph + node 的 `schema_version` const **保持 `0.1.1` 不动**，不 bump 至 0.3.0——bump 会破 gold scene + 阶段 0/1 测试。

### 6.3 dialogue_graph.schema.json 不变

ADR-019 明示 slot_assignments **节点级**字段；dialogue_graph 根对象**不**新增 generation_trace（避免双重 trace 路径）。本任务（T-2.2）**不**修改 `/schema/dialogue_graph.schema.json` 任何字段。

## 7. 兼容性约束

- v0.3.0 不破坏 v0.1.x / v0.2.0 任何 existing 字段语义。
- **复合版本号语义（核心约束）**：v0.3 是 ontology 模块的 MINOR bump；dialogue_graph 模块 const 保持 0.1.1；image_asset 模块 const 保持 0.2.0；三组独立演进。
- v0.1.x 数据加载：现有 dialogue_graph / node / option / state_effect / state_condition 五个 schema 的 const 与字段全部不动；现有 gold scene `/content/test_scene_v0/scene.json` 仍 pass dialogue_graph schema v0.1.1（schema/tests/test_stage2_ontology_schema.py:test_gold_scene_still_passes_dialogue_graph_v0_1_1 强制回归）。
- v0.2.0 数据加载：image_asset.schema.json 不动；waystation.json character entity 内 visual_assets 嵌入完整 ImageAsset 对象的形态保持；character.schema.json 在自己的 visual_assets 字段层不约束 ImageAsset shape（详 §2.3 设计权衡），strict 校验仍由 image_validator 做。
- envelope 迁移（详 §3.2）：scene_waystation_of_iron_oath 的 `type` 字段语义升级（"scene" → "location" + location_type "scene"）；运行时 ImageAsset.target_type=="scene" 路径不受影响（详 §3.2 影响面分析）。
- 引用 SCHEMA_v0.2 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例：optional 字段（slot_assignments）走兼容路径，不联动 const。
- **content_dependency_index sidecar（详 §9）**：T-3.2 阶段 3 起手新建独立 schema 文件，首版 const `0.3.0`，与 ontology 模块同 epoch；不动既有 dialogue_graph / node / option 等 schema；不内嵌入 dialogue_graph 字段（避免双重 trace 路径）。

## 8. 留给 image_validator / graph_validator / 机械预检器的语义约束（**不在 schema 层表达**）

汇总（详见各 schema 章节内的子段）：

1. **本体闭合性**：`relations[].target_character_ref` / `parent_location_ref` / `tick_effects[].path` 在五个 state path 命名空间内 / `acts[].included_scenes[]` 解析到 `location_type=="scene"` 的 entity（graph_validator）。
2. **state path 命名空间合法性**：所有 `path` 首段必须落入 `world` / `faction` / `relationship` / `flag` / `player` 之一（ADR-016；schema/tests/test_stage2_ontology_schema.py:test_gold_scene_paths_all_within_state_namespace_whitelist 端到端回归）。
3. **state_path_slug 全本体唯一**（character_validator 兜底；state/tests/test_stage2_ontology_loader.py:test_loader_state_path_slug_is_unique_within_world 早期回归）。
4. **time_based 不存在**（ADR-017；clock.schema.json enum 已硬约；schema/tests/test_stage2_ontology_schema.py:test_clock_schema_advance_rule_no_time_based 回归）。
5. **dramatic_triggers.priority 单 character 内排序确定性**（让 T-2.5 prompt 选择 deterministic）。
6. **slot_assignments.<slot_id>.character_ref 解析回本体**（graph_validator）。
7. **clock.ticks_filled <= ticks_total**（schema 跨字段表达困难，validator 兜底）。
8. **ImageAsset shape**（image_validator；character/location.schema.json 在 visual_assets 字段层不重复表达，详 §2.3）。

## 9. ContentDependencyIndex sidecar Schema 定义（`/schema/content_dependency_index.schema.json`）

> 阶段 3 T-3.2 落地（ADR-023 + ADR-024）。**形态**：per-scene sidecar 文件 `<scene>.deps.json`，与 scene.json 同目录、平行落盘（与阶段 1.5 visual manifest 同哲学）。**写入语义**：context assembly over-approx trace（不是 scene 反查；详 §9.2 + ADR-023 / F5 修订）。**字段约束加严**：F15 修订要点（详 §9.3）。**T-3.2 不写入数据**——本任务仅交付 schema + 文档；sidecar 实际写入流水线由 T-3.5 批量调度器落地。

### 9.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✓ | `"0.3.0"` | 本对象 schema 版本；与 ontology 模块同 epoch（首版 0.3.0）。**不同于 character / location / clock / chapter，本字段是 required**——sidecar 由 batch_scheduler 自动写入，不存在迁移期省略场景。 |
| `scene_id` | string | ✓ | `^[a-z0-9_]+$` | 本 sidecar 所属场景 id；与同目录 scene.json `graph_id` 严格同源（ADR-023 决策核心；GPT-5.5 review 3.2 修订）。pattern 与 dialogue_graph.graph_id `^[a-z0-9_-]+$` 仅去掉连字符——避免 sidecar 文件名与目录解析歧义。一致性由 dep_propagate / batch_scheduler 兜底。 |
| `generated_at` | string | ✓ | format date-time | sidecar 生成 ISO 8601 时间戳；format 校验为 annotation-only（默认 jsonschema validator 不强校），写入器与 dep_propagate 工具按字面格式约定。 |
| `ontology_ids_read` | array of string | ✓ | uniqueItems | context assembly 阶段所有被引用的本体实体 id（char_* / scene_* / loc_* / clk_* / chap_*）；**来自 prompt 注入轨迹，非 scene 产物反推**（F5 修订）。可空数组。 |
| `state_paths_read` | array of string | ✓ | items pattern + uniqueItems | context assembly 阶段读取的 state path 全集；**ADR-016 五命名空间 pattern 强约 + 至少一个段（裸 namespace 拒收）**（F15 修订 + GPT-5.5 review 3.1 修订）。 |
| `state_paths_written` | array of string | ✓ | items pattern + uniqueItems | scene effect 写入的 state path 全集（scene.json `on_enter_effects` + `option.effects` 内 path 字段并集；写入侧从产物可精确反推）；同 read 侧 F15 严约（**裸 namespace 拒收；relationship.* 至少 slug + field 两段**）。 |
| `prompt_template_hash` | string | ✓ | `^sha256:[a-f0-9]{64}$` | 本 scene 生成时 prompt 模板的 SHA256；dep_propagate 反向 propagate 时按 hash 比对（hash 漂移 → mark scene stale）。 |
| `visual_asset_ids_referenced` | array of string | ✗ | uniqueItems | 阶段 1.5 ImageAsset.asset_id 全集；F15 missing-only。 |
| `clock_ids_referenced` | array of string | ✗ | uniqueItems | active clocks 注入 prompt 时的 clk_* 全集（ADR-017）；F15 missing-only。 |
| `chapter_id` | string | ✗ | `^chap_[a-z0-9_]+$` | 本 scene 所属 chapter id；T-3.9 chapter_assembler 写入。F15 missing-only（缺失 = scene 尚未指派；不允许 null）。 |
| `act_id` | string | ✗ | `^act_[a-z0-9_]{1,64}$` | 本 scene 所属 act id；与 chapter.schema.json `act_id` 严格同源（GPT-5.5 review 4.1 修订）；F15 missing-only。 |
| `scene_history_referenced` | array of string | ✗ | items pattern + uniqueItems | **ADR-024 长对话一致性 A/B hook**：注入 prompt 的 prior_scene_summaries 对应 scene id；items pattern 与 scene_id 同源。F15 missing-only。 |
| `prompt_token_estimate` | integer | ✗ | minimum 0 | **ADR-024 token metrics**：注入 LLM prompt 的总 token 估算；用于阶段 3 实测 token 累积曲线。F15 missing-only。 |
| `summaries_injected_count` | integer | ✗ | 0 ≤ x ≤ 5 | **ADR-024 token metrics**：实际注入 prior_scene_summaries 条数；schema 上限 5（与 ADR-024 prompt 上限一致）。F15 missing-only。 |
| `summary_source_hashes` | array of string | ✗ | items pattern `^sha256:[a-f0-9]{64}$` + uniqueItems | **ADR-024 token metrics**：每条注入 summary 的 SHA256（溯源用）。长度应与 summaries_injected_count 一致；schema 跨字段表达困难，写入器兜底。F15 missing-only。 |
| `truncation_reason` | string (enum) | ✗ | `["none", "summaries_over_5", "token_budget", "manual_override"]` | **ADR-024 token metrics**：summaries 被裁剪原因；none = 未触发裁剪。F15 missing-only。 |

`additionalProperties: false`（顶层未声明字段被 schema 拒收 —— F15 严约的核心防御）。

### 9.2 写入语义：context assembly over-approx trace（ADR-023 / F5 修订核心）

**关键决策（与 v0.1 草稿对照）**：sidecar **不是 scene 反查**——`<scene>.deps.json` 不能从 scene.json 内容反推。理由：

1. **scene 内容已 lossy**：prompt 注入的 ontology / state / clock 引用不全部能从生成产物倒推。例如 prompt 给 LLM 注入了 `char_aelwin` 的 character_features 但 LLM 在最终 scene 里没让 aelwin 出场——scene 反查会丢失这条依赖；后续 aelwin entity 改动时 dep_propagate 不会 mark 此 scene stale，导致漂移。
2. **Conservative over-approx 是正确策略**：sidecar 写入时**宁可误报 stale 也不漏依赖**——dep_propagate 多 review 一个本可不动的 scene，远好过漏掉应该 review 的 scene。
3. **写入时机**：T-3.5 批量调度器在 `_build_scene_context` 阶段累加 `GenerationDependencyTrace`（含 character_ids / location_ids / clock_ids / relation_ids / state_paths_read / prompt_template_hash / visual_asset_ids），生成 scene 完毕后落盘 sidecar。

**写入顺序约定（ADR-026 联动；F6 修订）**：write scene → assign chapter（T-3.9 helper 调用）→ write deps（T-3.5 含 dep_index trace）→ record version（T-3.8a 调用）。

**反向用途**：T-3.7 一致性维护工具（`/tools/dep_propagate.py`，T-3.7 落地）按 sidecar 反向 propagate——当本体某 character / location / clock 被改动，扫所有 sidecar 找出 `ontology_ids_read` 包含该 id 的 scene → mark stale，作者 review UI 上看到 stale 列表。

### 9.3 字段约束加严（F15 修订；GPT-5.5 review 3.1/3.2/4.1 C 阶段细化）

v0.1 草稿到 v1.0 的关键收紧（含 PR #40 B 阶段反馈整合）：

1. **state_paths_read / state_paths_written items pattern 强约 + 至少一个段（GPT-5.5 review 3.1 修订）**：必须落入 ADR-016 五命名空间（`world.*` / `faction.<id>.*` / `relationship.<slug>.<field>` / `flag.*` / `player.*`）且**至少一个段**——裸 namespace（如 `"world"` / `"flag"` / `"player"` / `"relationship.vellin"`）拒收；`relationship.*` 至少需 slug + field 两段（与 gold scene `relationship.vellin.trust` 形态对齐）。理由：dep_propagate 反向 propagate 时若把裸 `world` 命名空间整体 stale-mark，会与具体 `world.scene_count` 路径混淆，让 propagate 语义紊乱。pattern 与 ontology 模块（character.state_path_slug 反查 + clock.tick_effects[].path 五命名空间合法性）回归同源。
2. **数组字段 uniqueItems**：ontology_ids_read / state_paths_read / state_paths_written / visual_asset_ids_referenced / clock_ids_referenced / scene_history_referenced / summary_source_hashes 全部 uniqueItems—— 重复入会让 dep_propagate 误算依赖密度。
3. **scene_id pattern 与 dialogue_graph.graph_id 同源（GPT-5.5 review 3.2 修订）**：本字段 pattern `^[a-z0-9_]+$` 与 ADR-023 决策核心明示对齐——比 graph_id `^[a-z0-9_-]+$` 仅去掉连字符（避免 sidecar 文件名与目录解析歧义；os.path 部分实现对 hyphenated 文件名分词不一致），数字起首合法（与 graph_id 同源）。`scene_history_referenced` items 同源 pattern。
4. **act_id pattern 与 chapter.schema.json 严格同源（GPT-5.5 review 4.1 修订）**：本字段 pattern `^act_[a-z0-9_]{1,64}$` 与 chapter.schema.json `acts[].act_id` 字段完全一致——避免 sidecar 引用侧记录 chapter 不可解析的 id（T-3.9 chapter_assembler / T-3.7 dep_propagate 跨文件闭合一致性硬约）。
5. **optional 字段 missing-only**：`chapter_id` / `act_id` / `visual_asset_ids_referenced` / `clock_ids_referenced` / `scene_history_referenced` / `prompt_token_estimate` / `summaries_injected_count` / `summary_source_hashes` / `truncation_reason` 全部走 missing-only 兼容路径——key 缺失代表"本 scene 未引用 / 未触发该 hook"，**不允许 null**（schema 层未声明 null 类型即拒收）。

### 9.4 与 ontology / dialogue_graph schema 的关系

- **不内嵌入 dialogue_graph schema**：sidecar 是**独立 schema 文件**，与 `<scene>.json` 平行落盘；不作为 dialogue_graph schema 的 nested 字段。理由：dialogue_graph schema const 保持 `0.1.1` 不动（v0.3.0 复合版本号策略；详 §1）；sidecar 是阶段 3 新增，独立演进首版 `0.3.0`，与 ontology 模块同 epoch。
- **跨 schema 一致性约束（不在 schema 层表达；写入器兜底）**：
  1. `scene_id` 与同目录 scene.json `graph_id` 一致（**pattern 仅去掉连字符**：sidecar `scene_id` 与 graph_id 同字符类，仅多约束 `_` 与 `-` 互斥；作者若用连字符命名 graph_id，T-3.5 批量调度器写入前需 normalize 或预检报错；GPT-5.5 review 3.2 修订对齐 ADR-023 决策核心）。
  2. `act_id` 与 chapter.schema.json `acts[].act_id` 严格 pattern 同源（GPT-5.5 review 4.1）；sidecar 引用侧不能记录 chapter 不可解析的 id。
  3. `chapter_id` 与 chapter.schema.json `chapter_id` 严格 pattern 同源（本字段不卡 maxLength 而 chapter.schema.json 卡 64；引用侧宽松、定义侧由 chapter.schema.json 兜底）。
  4. `ontology_ids_read[]` 内每个 id 在 `/state/ontology/<world>.json` 可解析（dep_propagate 兜底）。
  5. `state_paths_written` 应与 scene.json `on_enter_effects[].path` ∪ `option.effects[].path` 一致（写入器兜底）。
  6. `summary_source_hashes` 长度等于 `summaries_injected_count`（写入器兜底；schema 跨字段表达困难）。

### 9.5 ADR-024 token metrics hook 字段（v1.0 新增）

阶段 3 实测期会跑一周 ≥ 10 场景；token 累积曲线 + 接受率回归是判断长对话一致性是否撞墙的关键依据（ADR-024 v0.2 修订倒推依据）。本 schema 落地四个 token metrics 字段：

- `prompt_token_estimate` — 全 prompt token 估算（含 SceneGraphContext + prior_scene_summaries + skeleton/fill 模板渲染段）。
- `summaries_injected_count` — 实际注入 prior_scene_summaries 条数（0–5）。
- `summary_source_hashes` — 每条 summary 的 SHA256，溯源用。
- `truncation_reason` — `none` / `summaries_over_5`（超 5 上限被裁）/ `token_budget`（token 预算被裁）/ `manual_override`（作者手动覆盖）。

**与 ADR-024 长对话一致性 A/B hook 联动**：阶段 3 末期如撞墙（token 曲线发散 / 接受率回归），可基于 `scene_history_referenced` + `summary_source_hashes` 升级为 RAG (B) 或 memory stream (A)，**不需重做 schema**。

### 9.6 留给 dep_propagate / batch_scheduler 的语义约束（**不在 schema 层表达**）

下列约束 schema 层无法表达（跨字段或跨文件），由 T-3.5 batch_scheduler 写入兜底 + T-3.7 dep_propagate 反向 propagate 时校验：

1. `scene_id` 与同目录 scene.json `graph_id` 一致（**pattern 字符类同源仅去连字符**：作者命名 graph_id 含连字符时需 normalize 或预检报错；T-3.5 写入前预检）。
2. `ontology_ids_read[]` 内每个 id 在 `/state/ontology/<world>.json` 可解析。
3. `act_id` / `chapter_id` 在 chapter.schema.json 内可解析（pattern 已 schema 层同源严约，但跨文件闭合性仍需 dep_propagate 兜底）。
4. `state_paths_read` / `state_paths_written` 跨字段一致性（写入路径自然也属于读取路径——常见但非必然，validator 不强约）。
5. `summary_source_hashes` 长度与 `summaries_injected_count` 一致。
6. Conservative over-approx 哲学（详 §9.2）：写入时**宁可误报 stale 也不漏依赖**。

### 9.7 完整示例 JSON（含 ADR-024 token metrics）

```json
{
  "schema_version": "0.3.0",
  "scene_id": "ironoath_chapter2_pursuit",
  "generated_at": "2026-05-08T12:00:00Z",
  "ontology_ids_read": [
    "char_vellin",
    "char_corvan",
    "scene_waystation_of_iron_oath",
    "loc_vellin_office",
    "clk_iron_oath_pursuit",
    "chap_iron_oath_betrayal"
  ],
  "state_paths_read": [
    "world.scene_count",
    "faction.iron_oath.reputation",
    "relationship.vellin.trust",
    "flag.player_knows_letter",
    "player.gold"
  ],
  "state_paths_written": [
    "relationship.vellin.trust",
    "flag.iron_oath_full_pursuit"
  ],
  "prompt_template_hash": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "visual_asset_ids_referenced": ["img_vellin_neutral"],
  "clock_ids_referenced": ["clk_iron_oath_pursuit"],
  "chapter_id": "chap_iron_oath_betrayal",
  "act_id": "act_arrival",
  "scene_history_referenced": [
    "glades_ironoath_waystation",
    "ironoath_chapter2_intro"
  ],
  "prompt_token_estimate": 4200,
  "summaries_injected_count": 2,
  "summary_source_hashes": [
    "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "sha256:2222222222222222222222222222222222222222222222222222222222222222"
  ],
  "truncation_reason": "none"
}
```

### 9.8 关联 ADR

- **ADR-023**：本 schema 形态 + 字段集 + 写入语义（context assembly over-approx trace）+ F15 字段约束加严。
- **ADR-024**：长对话一致性 C 起步；token metrics hook 字段（prompt_token_estimate / summaries_injected_count / summary_source_hashes / truncation_reason）+ A/B hook（scene_history_referenced）。
- **ADR-016**：五命名空间表（state_paths_read / state_paths_written items pattern 同源）+ schema 版本号策略（首版 0.3.0）。
- **ADR-026**：批量调度器写入顺序（write scene → assign chapter → write deps → record version）。

## 10. node.dialogue 结构化对白字段增量（ADR-040 / 2026-06-23）

> 本节为后续增量（2026-06-23，晚于 v0.3.0 本体增量），记录在此以保持「当前 schema 设计基线」单一可查。

**动机**：`node.narration` 历史把旁白（场景/动作白描）与 NPC 对白揉成一个字符串，L3 宿主（Godot，ADR-035）无法把「这句谁说的」结构化挂到说话人名字/头像位。ADR-040 把对白拆出为结构化字段。

**变更**：`/schema/node.schema.json` 新增 optional 字段 `dialogue`：

```jsonc
"dialogue": {                       // optional；可省
  "type": "array",
  "items": {
    "type": "object",
    "required": ["speaker_ref", "line"],
    "additionalProperties": false,
    "properties": {
      "speaker_ref": { "type": "string", "minLength": 1 },  // 非 null；∈ character_refs（留 /validator）
      "line":        { "type": "string", "minLength": 1 }   // 裸正文，不含「」包裹体例
    }
  }
}
```

**语义重定义**：`narration` 现 = **旁白**（无说话人）；带说话人的台词进 `dialogue[]`。

**不变量（ADR-040 决策三）**：节点携带非空 `dialogue[]` ⇒ `narration` 为纯旁白 ⇒ `node.speaker_ref` 必为 `null`；非空 `node.speaker_ref` 仅 legacy（pre-040）narration-only 节点保留。

**版本号**：**不 bump**。`dialogue_graph` / `node` 的 `schema_version` const 仍 `"0.1.1"`，走 optional + `additionalProperties: false` 兼容路径（同 §6 slot_assignments）。两条守卫测试（`test_gold_scene_still_passes_dialogue_graph_v0_1_1` + `test_dialogue_graph_schema_version_const_unchanged`）保持绿；老 narration-only 场景（gold scene）不带 `dialogue` 字段仍合法。

**留给 /validator**（不在 schema 层表达）：(1) `dialogue[].speaker_ref ⊆ character_refs` 闭合性 → `consistency_check`（与 `node.speaker_ref` 同址同逻辑）；(2) `dialogue[].line` 文本反模式预检 → `anti_pattern_detector`（AP-10 自称等）。

## 版本

本文件版本：v0.3.0（+ 2026-06-23 §10 ADR-040 node.dialogue 增量）
最后更新：2026-06-23（§10 ADR-040 结构化对白字段增量；走兼容路径不 bump const）。此前：2026-05-08（T-3.2 §9 ContentDependencyIndex sidecar 增量；含 PR #40 GPT-5.5 review C 阶段修订 — state path 拒裸 namespace + scene_id 与 graph_id 严格同源 + act_id 与 chapter.schema.json 严格同源 + $schema/$id 与既有 schema 同源）
