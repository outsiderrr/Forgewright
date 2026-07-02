# PR #80 P-A/P-B L2 breakdown cross-LLM critique

日期：2026-07-02  
对象：`claude/pa-pb-l2-plan`（PR #80，基于 `main` `ec834cc`）  
范围：`2026-06-29_pa_pb_task_breakdown.md` + `T-3P-0.md` / `T-3P-1.md` / `T-3P-2.md` / `T-3P-3.md`

## Findings

### F-1 🔴 T-3P-3 的终端播放命令会空跑，E2E 可能假阳性

证据：
- `/docs/prompts/stage_3/T-3P-3.md:64`、`:84` 要求用 `python -m engine.player ...` 玩通回流场景。
- 实际 CLI 入口是 `/engine/__main__.py:1`、`:9-14`：`python -m engine <path-to-scene.json>`。
- `/engine/player.py:141-188` 只有 `play()`，没有 module-level argv 入口；`python -m engine.player <path>` 只会加载模块后退出，不会播放。

建议修法：把 T-3P-3 和主拆解里的终端验收命令统一改成 `python -m engine <scene.json>`，并要求 E2E 报告粘贴实际命令与关键输出片段。

### F-2 🟡 structure-only 产 design 只有 API 规格，没有作者/下游可用的 CLI 入口

证据：
- 主拆解只要求 `run_multipass_scene` 增开关（`/docs/reviews/master_plan/2026-06-29_pa_pb_task_breakdown.md:152`）。
- T-3P-0 allowed 白名单不含现有 CLI 文件 `/generator/scripts/run_multipass_scene.py`（`/docs/prompts/stage_3/T-3P-0.md:31`）。
- 现有可运行入口实际在 `/generator/scripts/run_multipass_scene.py:99-132` 解析参数并调用 `run_multipass_scene` / `write_artifacts`。
- T-3P-1 又把 structure-only design 当必需输入（`/docs/prompts/stage_3/T-3P-1.md:42`）。

建议修法：T-3P-0 白名单和完成标准补上 `generator/scripts/run_multipass_scene.py` 的 `--structure-only`（或等价新 CLI）与 smoke 命令；明确该模式只落 `design.json`/`metrics.json`、不落 `scene.json`。

### F-3 🟡 P0/P1/P2 的输入 envelope 没冻结，平行 L3 容易实现出两套 loader

证据：
- 现有 `design.json` 是 wrapper：真实 lucy fixture 顶层第一个 key 是 `"design"`（`/generator/experiments/multipass_structure/2026-06-11_convfix/lucy/design.json:2`），`write_artifacts` 也把 `result.design` 写进外层 `"design"`（`/generator/multipass/engine.py:610-620`）。
- 但 T-3P-0 写 `design["beats_plan"]` / `design["run_config"]`（`/docs/prompts/stage_3/T-3P-0.md:52-54`），T-3P-1/T-3P-2 又说 `design.json` 含 `beats_plan` / `run_config`（`/docs/prompts/stage_3/T-3P-1.md:42`；`/docs/prompts/stage_3/T-3P-2.md:45`），未明说是在顶层还是 `payload["design"]`。
- 现有 lucy spec 同样是 wrapper：`config` + `spec` 两段（`/generator/experiments/multipass_structure/specs/lucy.json:1-12`）；T-3P-1 的输入描述却说 `scene_spec（background / character_state）`（`/docs/prompts/stage_3/T-3P-1.md:42`）并暴露 `--spec <spec.json>`（`:50`）。

建议修法：T-3P-0 冻结共享 IO 契约/loader：`design.json` 沿用现有 wrapper，消费者读取 `payload["design"]`；`--spec` 接受现有 `{config, spec}` 文件并读取 `payload["spec"]`，必要时 cross-check `spec.config` 与 `design.run_config`。

### F-4 🟢 mode 标签术语不符合 governance §10.6 的枚举写法

证据：
- governance 要求每批/PR 的模式标签写 `mode = batch-ABC / skip-BC / L1-fixation` + B 是否保留 + 授权来源（`/docs/governance.md:273-276`），三模式定义在 `/docs/governance.md:280-284`。
- 四份 prompt 的 `mode 标签` 都写“完整 ABC（默认；非 §10.6 三特殊模式）”（如 `/docs/prompts/stage_3/T-3P-0.md:13`、`T-3P-1.md:13`、`T-3P-2.md:13`、`T-3P-3.md:13`），不是治理文本里的 mode 值。

建议修法：把该行改成 `ABC 粒度 = single-L3 ABC；special mode = N/A；B 保留 = 是；授权来源 = 作者 PR #80 授权后回填`，或在主拆解明确定义“默认完整 ABC”不是 §10.6 mode 标签。

## §10.6 五问

1. 切得对吗：有条件过。P0 软地基 → P1 渲染/回流并行 → P2 E2E 集成的依赖图合理；但 F-2/F-3 说明 P0 还漏了 CLI 和 IO envelope 这两个“给别人定规矩”的地基。
2. ≤8 吗：过。共 4 个任务，且拆解明确“四任务每个都有独立规格需求 → 各走完整 ABC”（`/docs/reviews/master_plan/2026-06-29_pa_pb_task_breakdown.md:143`），不是攒批超限。
3. 软地基拉出去了吗：部分过。T-3P-0 已收编 `beats_plan`、`run_config`、`format_spec`、公开别名、`writer_ingest`、共用 fixture；漏项是 F-2 的 structure-only CLI 和 F-3 的 loader/envelope 契约。
4. 集成评审安排了吗：有条件过。T-3P-3 安排了格式段↔解析器对偶测试和正反 E2E（`/docs/prompts/stage_3/T-3P-3.md:62-74`），但 F-1 会让最终播放验收空跑，F-3 应补进机器测试。
5. 模式标签对吗：不过。当前写法能表达“完整 ABC”，但不符合 governance §10.6 的 mode 枚举；按 F-4 小修即可。

## 决策忠实度

未发现拆解推翻已定案事项：ADR-039 转向、首版只 P-A/P-B、轻量标签 markdown + 文件/CLI、§8 三确认项、不动 `/schema` 都被保留。  
不确定：T-3P-0 施工会话是否会自行发现并修改 `generator/scripts/run_multipass_scene.py`；按当前 prompt 白名单，它没有授权这样做，所以按 F-2 报。

## 事实抽查

未发现主拆解 §3 的文件:行号与行为断言造假：
- beats 现状：`MAX_REVEALS_PER_BEAT_CALL=4` 与 beats LLM 调用符合 `/generator/multipass/engine.py:55-56`、`:359-397`；beat schema 2-3 拍符合 `/generator/prompts/node/multipass/beat_pacing.py:115-118`。
- assemble 事实：机械字段由代码填、`speaker_ref=None`、helper 私有且 `__all__` 只导出 `assemble_graph` / `entry_graph_node_id`，符合 `/generator/multipass/assemble.py:70-188`。
- validator/human/AP：`validate(graph_dict)` 三层入口、`generation_source="human"` 只豁免 monotonic、AP 扫 narration/options/dialogue，符合 `/validator/__init__.py:78-96`、`/validator/dialogue_validator.py:130-150`、`:330-343`、`/validator/anti_pattern_detector.py:219-237`。
- schema enum：`generation_trace.source` 已含 `"human"`，符合 `/schema/node.schema.json:90-100` 与 `/schema/option.schema.json:44-55`。
- version/deps：`GenerationMethod` 当前无 `writer_ingest`，写入顺序为 write scene → assign chapter → write deps → record version，符合 `/generator/version_recorder.py:59-67` 与 `/generator/generate_scene.py:579-592`。
