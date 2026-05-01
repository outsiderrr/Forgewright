# generator 模块补充规则

## 本模块职责（一句话）

开发期的 LLM 调用层：把 `/schema/` 与 `/state/ontology/` 喂给 LLM，产出候选 JSON，交给 `/validator/` 校验。

## 硬性约束（继承自 /CLAUDE.md，并补充阶段 1 三条 ADR）

- **运行时（`/engine`）严禁 import 本模块下任何符号**（ADR-002 / ADR-004）。本模块只在开发期执行。
- **LLM 调用必须走 `LLMProvider` 接口**（ADR-011）。业务代码不得直接 `import google.genai`；只允许 `/generator/providers/` 下的具体 provider 实现持有该 import。
- **任何 API 调用前必须经 `budget.check_and_charge()` 拦一次**（ADR-012）。无例外，包括重试、调试脚本。超额抛 `BudgetExceeded`。
- **结构化输出走 provider 原生能力**（ADR-013）：Gemini 用 `response_schema`；最多 3 次（含初次）尝试，失败标记 `generation_failed` 并写日志，**不抛异常**。
- **`/generator/models/_generated/` 由 `datamodel-code-generator` 从 `/schema/*.json` 自动生成**，不得手动编辑。源头唯一是 JSON Schema（CLAUDE.md 规则 6）。
- **提示词模板放 `/generator/prompts/`**，按节点类型分文件；不要把模板硬编码到调度逻辑里。
- **阶段 1 历史**：阶段 1（generate_node 单节点生成）期间，本模块严禁修改 `/state/ontology/`（沿用桩），且不出现任何视觉资产相关代码。该约束已于阶段 1 验收（2026-04-30）后解除。
- **阶段 1.5 授权**：根据 ADR-014（视觉资产双模生成）+ ADR-015（1.5/2 sequencing），本模块在阶段 1.5 期间允许：
  - 新增视觉资产相关代码（`image_provider.py` / `image_budget.py` / `image_cost_log.py` / `generate_visual.py` / `image_import.py` / `manifest.py` / `visual_experiment.py` / `visual_review_cli.py` / `visual_metrics.py` 等）
  - 新增 `/generator/prompts/visual/` 子包
  - 新增 `/generator/providers/manual_import.py` 和 `/generator/providers/openai_image.py`
  - 通过 `image_import` CLI 修改 `/state/ontology/waystation.json` 的 `entities[]` 中 `type=character` 项的 `visual_assets` 数组（仅 `visual_assets` 字段；不动其它任何字段）
- **阶段 1.5 边界仍在**：
  - 不得直接 `import google.genai` 或 `import openai` 到业务代码（必须经 `ImageProvider` 接口；ADR-011 + ADR-014）
  - 任何 image API 调用前必须经 `image_budget.check_and_charge()`（ADR-012 + ADR-014）
  - 运行时（`/engine`）严禁依赖本模块（ADR-002 + ADR-004 不变）
  - 不得修改 `/state/ontology/waystation.json` 的 `entities[]` 内非 `visual_assets` 字段（保护本体真相之源 ADR-006）
- **跨模块改动约束**：默认禁止编辑 `/schema/`、`/state/`、`/engine/`、`/validator/`、`/content/`、`/docs/`。需要 Schema 变更时，停下来报告作者（规则 2 / 7）。**阶段 1.5 例外**（已授权）：`image_import` CLI 经过 `image_validator` 校验后可写 `/state/ontology/waystation.json` 的 `entities[].visual_assets` 字段；T-1.5.7 的模块边界对此显式列出。

## 提交前自检

- `pytest` 通过
- `grep -R "from generator" engine/ state/ schema/ validator/` 无任何匹配（确认运行时未沾染本模块）
- 新增/修改的业务代码无直接 `import google.genai`（必须经 provider 间接使用）
- 未触碰 `/state/ontology/`，但阶段 1.5 已授权的 `image_import` CLI 例外除外：仅可经 `image_validator` 校验后写 `/state/ontology/waystation.json` 的 `entities[].visual_assets`，不得改任何非 `visual_assets` 字段
- 1.5 阶段：确认未直接 `import google.genai` / `import openai`；确认所有 image API 调用经过 `image_budget`

## TODO（阶段 1 任务清单的执行单参见 /docs/）

- T-1.3：JSON Schema → Pydantic 自动生成脚手架
- T-1.4：`LLMProvider` Protocol 与 `GeminiProvider` 实现
- T-1.5：`budget.py` + 成本日志
- T-1.6：单节点 prompt 模板与 `generate_node` 入口
