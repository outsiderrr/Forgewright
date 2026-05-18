# Forgewright Godot First Game Host

生产可用的 Godot 4.6 L3 宿主原型，落实 ADR-035 `v_godot_custom` 路线：直接消费 Forgewright JSON dialogue graph，不引入 Dialogic，不包含任何运行时 LLM 调用。

## 目录

```text
host/godot_first_game/
├── project.godot
├── main.gd
├── export_presets.cfg
├── scenes/
│   ├── dialogue_main.tscn
│   └── option_button.tscn
├── scripts/
│   ├── scene_router.gd
│   ├── state_evaluator.gd
│   ├── ontology_resolver.gd
│   ├── skill_check.gd
│   ├── dialogue_control.gd
│   └── option_button.gd
├── data/
│   ├── test_scene_v0/scene.json
│   ├── ontology/waystation.json
│   └── state_runtime_policy.json
├── schema/
│   └── copied JSON Schemas used by the host at runtime
├── themes/default_theme.tres
└── tests/test_runner.gd
```

`data/test_scene_v0/scene.json` mirrors `/content/test_scene_v0/scene.json` for export packaging. In editor/dev runs, `scene_router.gd` also resolves `content/test_scene_v0/scene.json` from the repository root.

## Run

Open `host/godot_first_game/project.godot` in Godot 4.6.2 or newer, then press F5.

CLI:

```bash
godot --path host/godot_first_game
```

Load an explicit scene file:

```bash
godot --path host/godot_first_game -- --scene=/Users/outsider/Desktop/Forgewright/content/test_scene_v0/scene.json
```

## Tests

```bash
godot --headless --path host/godot_first_game --script res://tests/test_runner.gd
```

The test runner covers:

- `state_condition`: `eq` / `neq` / `gt` / `gte` / `lt` / `lte` / `has` / `has_not` / `any_of` / `all_of` / `not`
- `state_effect`: `set` / `inc` / `dec` / `add` / `remove`
- ADR-016 v0.4 monotonic policy for `flag.player_*` and `knowledge.*`
- ontology display-name resolution
- deterministic skill-check rolls
- a smoke path through the packaged gold scene

## Export

The macOS preset writes:

```text
host/godot_first_game/export/ForgewrightFirstGame.app
```

Command:

```bash
godot --headless --path host/godot_first_game --export-release macOS export/ForgewrightFirstGame.app
```

Godot export templates must be installed locally. In the Godot editor this is available from `Editor > Manage Export Templates`.

## Runtime Notes

- `state_evaluator.gd` reads op enums from `schema/state_condition.schema.json` and `schema/state_effect.schema.json`.
- State path namespace validation reads the ADR-016-compatible pattern from `schema/content_dependency_index.schema.json`.
- Monotonic runtime behavior is host-local policy in `data/state_runtime_policy.json`, not world-specific code.
- `ontology_resolver.gd` resolves `speaker_ref` / `location_ref` through `data/ontology/waystation.json`.
- `skill_check.gd` implements the minimal ADR-029 check shape: `skill_id`, `dc`, `roll`, optional modifier from state/config.

Known schema gaps:

- Current `option.schema.json` does not yet define a top-level `active_check` field and forbids additional properties. The host can execute checks when supplied via a future legal `active_check` field or temporary `plugin_metadata.active_check`, but the gold schema cannot currently encode that field without a schema change.
- Current `dialogue_graph.schema.json` includes `scene_metaparams`, `scene_reveals`, `scene_seeds`, and `player_known_info`, but not the T-3Y draft fields `scene_branches`, `scene_actual_inputs`, `scene_actual_outputs`, or `included_node_ids`. `scene_router.gd` supports `scene_branches` when present, but schema-valid gold scenes cannot yet carry it.
