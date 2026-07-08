# T-3P 共用 fixture（T-3P-0 产出；T-3P-1/2/3 golden 测试统一引用这一份）

## lucy/design.json ——是"超集"，下游别依赖正文段

合成方式 = **legacy 全量运行产物**（`2026-06-11_convfix/lucy/design.json`，真实结构层实测）
+ `beats_plan`（确定性拆拍器对其 topology 的输出）+ `run_config`（抄 `specs/lucy.json` config 段）。

⚠️ 因此它带有**真实 structure-only 运行不会有的内容**：`proses` / `beats` / `ends` 非空、
`validation` 有值、call_metas 含正文调用。真实 `--structure-only` 产物这些段是**空 dict / {}**
（生产形态由 `generator/multipass/tests/test_engine.py::test_structure_only_design_carries_beats_plan_and_run_config` 钉死）。
**T-3P-1/2 的实现与 golden 不得依赖这些段存在非空内容**——只准消费
`contract` / `topology` / `skeletons` / `beats_plan` / `run_config`（经
`generator.promptpack.io.load_design_artifact` 读取）。

可再生性由 `generator/multipass/tests/test_t3p_fixture.py` 钉死（beats_plan 与拆拍器对
fixture 自身 topology 的输出逐字节一致；run_config 与 specs/lucy.json config 段一致）。

## 其他文件

- `beat_split_comparison.md`：拆拍样例对照（旧 LLM 涌现 vs 新确定性拆拍）——作者验收物①。
- `format_contract_sample.md`：回流格式契约样张 + 假想退回单——作者验收物②。
