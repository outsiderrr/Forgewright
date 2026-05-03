# 开源剥离边界清单（OPEN_SOURCE_CARVE_OUT_INDEX）v0.1

> Sidecar，跟踪从 `forgewright`（私有 + 全过程仓库）剥离 `forgewright-framework`（开源工具核心）时需要拆出 / 替换 / 文档化的内容。
> 阶段 2 起手时建立首版（C5 强建议；STAGE_2_TASKS §2.1 D6），阶段 4 执行剥离。

## §1 用途

- 跟踪从 forgewright 仓库剥离开源框架时需要**拆出 / 替换 / 文档化**的内容。
- 阶段 2 起维护，阶段 4 执行剥离。
- 不替代 ROADMAP §4（剥离动作本身），仅作为"已知私有依赖"的连续清单 hook，避免阶段 4 才发现遗漏。

## §2 三类边界

### A. fixture / 角色 / 场景内容（作者本人项目；不能进开源框架默认）

- `/content/test_scene_v0/scene.json`（《铁誓驿站》gold scene）
- `/state/ontology/waystation.json`（vellin / corvan / aelwin 角色实体 + 关系）
- `/generator/prompts/few_shot.py` 引用的内容（节点级 few-shot 含《铁誓驿站》台词 / 角色名）
- `/generator/prompts/scene/few_shot.py` 引用的内容（**v1.0 新增；D6 修订** — 场景级 few-shot 同上）
- `/generator/prompts/scene/system.py` 含《铁誓驿站》场景默认 prompt 时（**v1.0 新增；D6 修订** — 标记并由 T-2.5 落地后回填）
- `/generator/fixtures/scene/`（如 T-2.12 加 scene fixture，**v1.0 新增**）

### B. 资产版权（视觉资产）

- `/content/visuals/`（mini probe 5 张 vellin 立绘 + 后续 batch 资产；版权属作者，不进开源默认）
- `/content/visuals/_reference/`（作者私有风格参考；已 `.gitignore`）
- `/generator/image_cost_log.jsonl` + `import_log.jsonl`（runtime 产物，非框架内容；剥离时不带）

### C. provider 假设（默认 SDK / API key）

- `GeminiProvider` 默认 `model_id`（`gemini-3.1-pro-preview`）—— 开源默认应给可替换 provider 接口或抽象基类，不锁定 Google
- `OpenAIImageProvider`（`gpt-image-1`）—— 同上
- `.env` / `.env.example`（API key）—— 已 `.gitignore`；开源仓只留示例 stub，不带具体 key 或 endpoint

## §3 阶段 2 / 3 维护规则

- 每个新增的 schema fixture / 资产引用 / provider 假设落新一行到 §2 对应类。
- L3 任务执行会话发现新边界时追加（`[A-execute]` 兼容 routine）。
- 追加格式：`- <路径>（<一句话来由 / 任务编号 / 修订标记>）`。
- 不在此处做剥离动作本身（阶段 4 才执行）；本清单仅记录"已知"。

## §4 v0.1 状态：起步清单

即上述 §2。本版本由 T-2.10 起步，吸收 STAGE_2_TASKS v1.0 D6（critique 4.6）对 scene prompt 子包 + scene fixtures 的修订标注。

---

**版本**：v0.1
**起步任务**：T-2.10（C5 强建议落地）
**最后更新**：2026-05-03
