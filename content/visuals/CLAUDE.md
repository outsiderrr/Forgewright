# /content/visuals/ 模块说明

- 本目录存放阶段 1.5 视觉资产入库后的产物；不存运行时代码。
- 资产在子目录按 character_id 或 location_id 分组：`vellin/<asset_id>.png`、`scene_waystation_of_iron_oath/<asset_id>.png` 等。
- 所有资产必须先经 `image_validator` 机械预检（T-1.5.4）+ 作者审阅，才能正式入库。
- `manifest.json` 是该目录的索引；由 `image_import` CLI（T-1.5.7）维护，禁止手工编辑。
- `_reference/` 子目录存视觉风格基准图（**不入 git**——版权风险；目录本身用 `.gitkeep` 入 git）。
- `_pending/` 子目录存 manual 模式 prompt 包 + 待入库 PNG（**不入 git**——临时产物）。
