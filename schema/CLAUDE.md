# schema 模块补充规则

## 本模块职责（一句话）

以 JSON Schema 定义 Forgewright 所有核心数据结构，是其他模块的单一事实源。

## 硬性约束（继承自 /CLAUDE.md）

- 源头必须是 JSON Schema；Pydantic / TypeScript 类型等只能作为生成产物（见 /CLAUDE.md 规则 6、ADR-003）。
- 改动本模块属于高风险操作：需暂停其他并行会话后串行处理（见 /CLAUDE.md 作者工作流）。

## TODO

阶段 1 启动时补充：Schema 变更流程、版本化策略、对校验器与生成器的兼容性保证方式。
