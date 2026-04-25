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
- **阶段 1 严禁修改 `/state/ontology/`**（沿用桩）。视觉资产生成属阶段 1.5，本模块此阶段不出现任何相关代码。
- **不得跨模块改动**：禁止编辑 `/schema/`、`/state/`、`/engine/`、`/validator/`、`/content/`、`/docs/`。需要 Schema 变更时，停下来报告作者（CLAUDE.md 规则 2 / 7）。

## 提交前自检

- `pytest` 通过
- `grep -R "from generator" engine/ state/ schema/ validator/` 无任何匹配（确认运行时未沾染本模块）
- 新增/修改的业务代码无直接 `import google.genai`（必须经 provider 间接使用）
- 未触碰 `/state/ontology/`

## TODO（阶段 1 任务清单的执行单参见 /docs/）

- T-1.3：JSON Schema → Pydantic 自动生成脚手架
- T-1.4：`LLMProvider` Protocol 与 `GeminiProvider` 实现
- T-1.5：`budget.py` + 成本日志
- T-1.6：单节点 prompt 模板与 `generate_node` 入口
