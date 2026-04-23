# 本体桩（阶段 0 stub）

**正式本体 Schema 将在后续任务定义；当前仅作为阶段 0 最小实现。**

本目录下的 `*.json` 文件是 T-0.7 时为跑通 SCENE_v0.md《铁誓驿站》场景手写的本体桩，
仅包含最小字段，不声明完整的世界设定 Schema。

## 条目字段

每个实体仅含三字段：

| 字段 | 说明 |
|---|---|
| `id` | 全仓库唯一 ID，遵守 SCENE_v0.md D7 正则（`^[a-z0-9_-]+$`）。前缀约定：`char_*` 角色，`scene_*` 场景，`loc_*` 地点（若以独立于场景的地点出现）。 |
| `display_name` | 显示名。 |
| `type` | `"character"` \| `"location"` \| `"scene"`。 |

更丰富的字段（性格、派系归属、地理坐标、关系图谱）由正式本体 Schema 任务定义。

## 当前覆盖的实体

来源：`/docs/SCENE_v0.md` v0.1 §1.2 与 §1.3。

| id | 类型 | 说明 |
|---|---|---|
| `char_vellin` | character | 驿站长，玩家旧识 |
| `char_corvan` | character | 铁誓卫队巡逻官，玩家旧识 |
| `char_aelwin` | character | 逃兵，场景中不出场 |
| `scene_waystation_of_iron_oath` | scene | 铁誓驿站；在 SCENE_v0.md 中同时作为所有节点的 `location_ref`（§1.3 说明该场景不做地点细化） |

**显式不含**：`char_corvax_the_unknown`。这是 SCENE_v0.md §6.1 E1 例二的**故意坏掉**的错误变体，用于 validator 的一致性拒收样本；本体桩必须把它留在外面才能让 validator 在 T-0.9 中正常拒收。

## 加载规则

`state.ontology.get_entity(entity_id)` 在模块首次加载时扫描本目录所有 `*.json`，按 `id`
建索引；重复 `id` 抛 `ValueError`。阶段 0 不检查 JSON Schema——等正式本体 Schema
任务上线时再补。
