# generator

开发期 LLM 生成管线。读取 `/schema/` 与 `/state/ontology/`，调用 LLM 产出候选 JSON，
经 `/validator/` 校验后由人工主编审阅。运行时（`/engine`）严禁依赖本模块（ADR-002 / ADR-004）。

阶段 1 范围：单节点对话生成 + LLMProvider 接口（默认 Gemini，见 ADR-011 / 012 / 013）。
