# SCHEMA_v0.2.md — 项目 Schema 设计基线 · v0.2 增量

> 本文件承接 SCHEMA_v0.md（v0.1.x）；记录 v0.2.0 引入的 Schema 增量。
>
> **重要**：v0.2.0 是项目**首次新增 schema 文件**（不是修改 existing schema）。existing `/schema/*.json` + `/content/test_scene_v0/scene.json` 的 schema_version 保持 0.1.1（沿用阶段 1 T-1.0 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例）。仅新增文件 `/schema/image_asset.schema.json` 起步 schema_version=0.2.0。

## 1. 增量摘要

阶段 1.5 在 v0.2.0 引入两处增量，均为**新增**而非修改：

- 新增 `/schema/image_asset.schema.json`：定义 ImageAsset 视觉资产元数据（角色立绘 / 场景背景）。schema_version 起步 `0.2.0`。
- 扩展 `/state/ontology/waystation.json` 中 `entities[]` 内 `type=="character"` 的 3 个对象：在末尾新增 `visual_assets: []` 字段（路径 A：仅扩展数据，不正式化角色 Schema；STAGE_1.5_TASKS.md P0.1）。

**保持不变**（v0.2.0 一律不动）：

- `/schema/dialogue_graph.schema.json` / `node.schema.json` / `option.schema.json` / `state_effect.schema.json` / `state_condition.schema.json`：5 个 existing schema 文件的任何字段或 `schema_version`（保持 `0.1.1`）。
- `/content/test_scene_v0/scene.json`：v0.1.1 数据样例不动（`schema_version` 仍为 `0.1.1`）。
- `/state/ontology/waystation.json` 中 `type=="scene"` 的对象（`scene_waystation_of_iron_oath`）：**暂不加** `visual_assets`。scene_background 资产仅在 `manifest.json` 用 `target_ref` 索引，不嵌入本体（按 synthesis §9.4 推荐方案落地；阶段 2 作者拍板是否反向给 scene/location 也加 `visual_assets[]`）。
- `/state/ontology/waystation.json` 顶层结构（`entities[]` 数组本身的元素增删）。

## 2. ImageAsset Schema 定义

### 2.1 字段总览

| 字段 | 类型 | 必填 | 约束 | 一句话语义 |
|---|---|---|---|---|
| `schema_version` | string (const) | ✗ | `"0.2.0"` | 本对象 schema 版本；可省略，若填则必为 `0.2.0`。 |
| `asset_id` | string | ✓ | `^img_[a-z0-9_]{1,64}$` | 全仓库唯一资产 ID（唯一性留给 image_validator）。 |
| `asset_kind` | enum | ✓ | `character_sheet` / `scene_background` | 资产种类（向后兼容名；与 `asset_role` 当前等价）。 |
| `target_ref` | string | ✓ | minLength 1 | **Round 5 U-GPT-3 硬闸门**：通用挂载锚点 ID（如 `char_vellin` / `scene_waystation_of_iron_oath`）。 |
| `target_type` | enum | ✓ | `character` / `location` / `scene` | **Round 5 U-GPT-3 硬闸门**：锚点类型；决定镜像字段语义有效性。 |
| `asset_role` | enum | ✓ | `character_sheet` / `scene_background` | **Round 5 U-GPT-3 硬闸门**：资产在叙事中扮演的角色；预留扩展（`item_icon` / `ui_portrait`）。 |
| `character_ref` | string \| null | ✗ | — | 向后兼容镜像字段；`target_type=character` 时语义层 required 且必须 == `target_ref`。 |
| `location_ref` | string \| null | ✗ | — | 向后兼容镜像字段；`target_type∈{location,scene}` 时语义层 required 且必须 == `target_ref`。 |
| `source_mode` | enum | ✓ | `manual` / `api` | ADR-014 双模生成策略：手动从 ChatGPT 网页端导入 / OpenAI Image API 自动调用。 |
| `format` | enum | ✓ | `png` / `webp` | 图像文件格式。 |
| `width` | integer | ✓ | 256 ≤ w ≤ 4096 | 宽度像素（缩略图最低边界 / API 上限）。 |
| `height` | integer | ✓ | 256 ≤ h ≤ 4096 | 高度像素（同 `width`）。 |
| `file_size_bytes` | integer | ✗ | minimum 1 | 文件字节数；R8 机械预检字段。 |
| `has_alpha` | boolean | ✗ | — | 透明通道存在；`character_sheet` 应 true / `scene_background` 应 false（语义层校验）。 |
| `file_path` | string | ✓ | `^content/visuals/[A-Za-z0-9_/-]+\.(png\|webp)$` | 相对仓库根、仅允许入库后的 `content/visuals/` 下 PNG/WEBP 路径（pattern 阻断目录穿越 / 绝对路径 / 非 visuals 目录）。 |
| `prompt_hash` | string | ✗ | `^[a-f0-9]{64}$` | 生成时 prompt 文本的 sha256 hex（64 位小写 hex）；用于追溯。 |
| `generation_metadata` | object | ✗ | 自由 dict | prompt 文本 / 风格基准引用 / 时间戳 / API 元数据；schema 不约束内部结构。 |
| `style_reference_id` | string \| null | ✗ | — | 指向 `_reference/` 内的基准图标识。 |
| `reference_ids` | array of string | ✗ | default `[]` | **Round 5 U-GPT-6 软闸门**：本资产引用的 `_reference/` 基准图 ID 数组；trace 风格依赖。 |
| `reference_license_note` | string | ✗ | default `""` | **Round 5 U-GPT-6 软闸门**：每张引用基准图的来源 + 许可（如 `ref_001: own photograph CC0`）。 |
| `open_source_ok` | boolean | ✗ | default `false` | **Round 5 U-GPT-6 软闸门**：能否进开源 release dataset；默认 false 安全侧。 |
| `commercial_ok` | boolean | ✗ | default `false` | **Round 5 U-GPT-6 软闸门**：能否进商业版；默认 false 安全侧。 |
| `created_at` | string | ✓ | format `date-time` | ISO 8601 / RFC 3339；format 严格校验由 image_validator 完成。 |

`additionalProperties: false`（未声明字段被 schema 拒收）。

### 2.2 留给 image_validator 的语义约束（**不在 schema 层表达**）

下列约束**不**在 JSON Schema 中用 `if/then/else` 或 `oneOf` 表达——阶段 1 baseline_001 教训：datamodel-code-generator 与 Gemini schema 子集对复合形态有已知坑（STAGE_1.5_TASKS.md P0.1）。schema 层仅声明字段类型 / 枚举 / 边界；语义校验由 image_validator 拒收不一致样本。

1. `target_type=="character"` ⇒ `character_ref == target_ref` AND `location_ref == null`。
2. `target_type=="location"` ⇒ `location_ref == target_ref` AND `character_ref == null`。
3. `target_type=="scene"` ⇒ `location_ref == target_ref`（向后兼容；当前 `scene_waystation_of_iron_oath` 试点）AND `character_ref == null`。
4. `asset_kind` 与 `asset_role` 当前枚举重合（有意——`asset_kind` 向后兼容名；`asset_role` 预留扩展位）；image_validator 校验两者一致。
5. `has_alpha` 与 `asset_role` 一致性：`character_sheet` 应 `true`，`scene_background` 应 `false`。
6. `target_ref` / `character_ref` / `location_ref` 在本体花名册（`/state/ontology/`）中可解析。
7. `asset_id` 全仓库唯一。

### 2.3 完整示例 JSON

character_sheet 实例（角色立绘）：

```json
{
  "schema_version": "0.2.0",
  "asset_id": "img_vellin_neutral",
  "asset_kind": "character_sheet",
  "target_ref": "char_vellin",
  "target_type": "character",
  "asset_role": "character_sheet",
  "character_ref": "char_vellin",
  "location_ref": null,
  "source_mode": "manual",
  "format": "png",
  "width": 1024,
  "height": 1536,
  "file_size_bytes": 1843200,
  "has_alpha": true,
  "file_path": "content/visuals/vellin/img_vellin_neutral.png",
  "prompt_hash": "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7",
  "generation_metadata": {
    "prompt_text": "Vellin, a stoic mercenary in worn leather armor; neutral expression; ...",
    "model_id": "gpt-image-1",
    "style_reference_id": "ref_bg3_oilpaint_001"
  },
  "style_reference_id": "ref_bg3_oilpaint_001",
  "reference_ids": ["ref_bg3_oilpaint_001"],
  "reference_license_note": "ref_bg3_oilpaint_001: author Pinterest collection (private use only; not for redistribution)",
  "open_source_ok": false,
  "commercial_ok": false,
  "created_at": "2026-05-01T12:00:00Z"
}
```

scene_background 实例（场景背景，target_type=scene 试点）：

```json
{
  "asset_id": "img_waystation_dusk",
  "asset_kind": "scene_background",
  "target_ref": "scene_waystation_of_iron_oath",
  "target_type": "scene",
  "asset_role": "scene_background",
  "character_ref": null,
  "location_ref": "scene_waystation_of_iron_oath",
  "source_mode": "api",
  "format": "webp",
  "width": 2048,
  "height": 1152,
  "has_alpha": false,
  "file_path": "content/visuals/_scenes/img_waystation_dusk.webp",
  "created_at": "2026-05-01T12:00:00Z"
}
```

## 3. 本体角色实体扩展：visual_assets 字段

### 3.1 路径 A 决策（不正式化角色 Schema）

阶段 1.5 P0.1 决策为**路径 A：仅扩展数据，不正式化角色 Schema**（见 STAGE_1.5_TASKS.md "锁定的架构决策"表）。

- **不新建** `/schema/character.schema.json` 或 `/schema/location.schema.json`。
- 仅在 `/state/ontology/waystation.json` 现有的 `entities[]` 中 `type=="character"` 的对象**末尾新增** `visual_assets` 字段。
- 本体角色对象目前只有 `id` / `display_name` / `type` 三个字段；它们仍是**桩形态**，不受 JSON Schema 严格校验（路径 A 的本意）。
- 阶段 2 作者拍板是否正式化角色 / 地点 Schema；届时 `visual_assets` 字段会迁移到正式 schema，本对象的字段语义保持兼容。

### 3.2 visual_assets 字段语义

`visual_assets` 是 `array`，每个元素是**完整 ImageAsset 对象**（按 `/schema/image_asset.schema.json` 校验）。

**决策（见 STAGE_1.5_TASKS.md P0.1 / T-1.5.7 §1811）**：直接嵌入**完整 ImageAsset 对象**，而非通过 `asset_id` 引用。

理由：

1. 简化层次。`manifest.json` 也保存完整 ImageAsset 对象（可按 `asset_id` 建索引；T-1.5.7 草案为 `assets: dict[str, ImageAsset]`），而不是只存 `asset_id` stub；与本体中的嵌入对象保持字段一致。
2. 引用层次太多会让 image_validator 闭合性校验复杂化（要先解析 `asset_id` → `manifest.json` 查表 → 才能拿到完整对象）。
3. 当前本体规模小（3 个角色 × ~10 张立绘 ≈ 30 个嵌入对象），全量存的成本可忽略。
4. 阶段 4 开源剥离时若需要分文件，再做反向迁移即可。

### 3.3 哪些实体加 visual_assets

v0.2.0 仅在 `entities[]` 中 `type=="character"` 的对象添加 `visual_assets`。

- ✅ `char_vellin` / `char_corvan` / `char_aelwin`：3 个角色对象末尾各加 `visual_assets: []`。
- ❌ `scene_waystation_of_iron_oath`：`type=="scene"` 项**暂不加**——按 synthesis §9.4 推荐方案落地：scene_background 资产仅在 `manifest.json` 用 `target_ref` 索引，不嵌入本体。
  - 阶段 2 作者若决定反向给 scene/location 也加 `visual_assets[]` 数组，**ImageAsset schema 不动**——只在角色 / 地点本体侧多加一个嵌入路径。

`visual_assets` 起步空数组 `[]`；T-1.5.7 image_import CLI 入库时由确定性代码追加完整 ImageAsset dict。

### 3.4 示例（修订后形态）

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

## 4. 兼容性约束

- v0.2.0 不破坏 v0.1.x 任何 existing 字段。existing `/schema/*.json` 5 个文件 + `/content/test_scene_v0/scene.json` 的 `schema_version` 保持 `0.1.1`。
- v0.1.x 数据加载时 `visual_assets` 视为空数组（默认）。任何按 v0.1.x 写的工具读 v0.2.0 的本体不会断——多出的 `visual_assets` 字段对 v0.1.x 工具是 unknown 字段（路径 A 下本体无严格 schema，不会被拒收）。
- DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 在 v0.2.0 内**不变**（既不改字段也不联动 `schema_version`）。
- **未来短视频扩展点（钩子说明，1.5 不实现）**：阶段 1.5 仅实现静态 PNG / WEBP；技术成熟后才考虑短视频循环（HANDOFF_STAGE_1_TO_1.5.md "作者对视觉的态度"段）。届时扩展方式：
  - 在 `format` 枚举追加 `mp4` / `webm` 等。
  - 新增 `video_duration_ms` / `video_format_codec` 等字段（schema_version MINOR bump 至 0.3.0）。
  - 现有 `width` / `height` 字段语义保持（视频帧尺寸）。
  - **本版本仅说明，不实现**——避免预先抽象（CLAUDE.md "Don't add features beyond what the task requires"）。

## 版本

本文件版本：v0.2.0
最后更新：2026-05-01
