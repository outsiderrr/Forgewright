# SCHEMA_v0.3.md — 项目 Schema 设计基线 · v0.3 增量

> 本文件承接 SCHEMA_v0.md（v0.1.x）+ SCHEMA_v0.2.md（v0.2.0）；记录 v0.3.0 引入的 stage-2 ontology 增量。
>
> **重要（复合版本号语义）**：v0.3.0 是 **ontology 模块**（character / location / clock / chapter）的 MINOR bump，**不是** dialogue_graph schema 模块的 bump。两组 schema 文件版本号**独立演进**：
>
> - 新建 schema 文件首版 const `"0.3.0"`：`/schema/character.schema.json` + `location.schema.json` + `clock.schema.json` + `chapter.schema.json`。
> - 既有 schema 文件 const **保持 `"0.1.1"` 不动**（沿用 SCHEMA_v0.2 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例）：`dialogue_graph.schema.json` + `node.schema.json` + `option.schema.json` + `state_effect.schema.json` + `state_condition.schema.json`。
> - `image_asset.schema.json` 的 const 保持 `"0.2.0"` 不动。
> - 新增字段（如 `node.generation_trace.slot_assignments`，详 §6）走 **optional + `additionalProperties: false`** 兼容路径，不破 gold scene `/content/test_scene_v0/scene.json`（其 `schema_version` 仍为 `0.1.1`）。
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

## 版本

本文件版本：v0.3.0
最后更新：2026-05-03
