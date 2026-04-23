# CLAUDE.md

> This file is read automatically by every Claude Code session in this repository.
> It defines what this project is, what is in scope, and what you must not do.

## 项目是什么

本项目代号 **Forgewright**。它是一条**AI 辅助的分支叙事内容生产流水线**，目标分两步：

1. **短期**：作为作者本人开发一款类博德之门 3 风格中小型 RPG 的专属工具链。
2. **长期**：剥离出通用部分开源，成为独立 RPG 开发者可复用的"叙事内容生成 + 校验 + 导出"框架。

**项目的核心价值不在游戏运行时，而在内容生产期的工具链。** 游戏本身的运行时极简（一个 JSON 对话图播放器，无 LLM 参与）。LLM 只在开发期介入——用来批量生成符合 Schema 的对话内容，并由人工主编审阅。

## 玩家交互模式（非常重要）

本项目的游戏**不是**自由文本对话式 AI 游戏。玩家交互模式是：

- 玩家看到场景描述和 **3–6 个预生成的选项**，点击选项即可。
- 所有对白、分支、NPC 反应都是**开发期预先生成 + 人工审阅**过的静态内容。
- **运行时不调用 LLM**。运行时只是一个读取 JSON 对话图的确定性播放器。
- 这意味着：**不存在玩家欺诈（player exploitation）问题**。不需要运行时反幻觉、反欺诈、流式输出对齐等复杂机制。这些在更早的架构讨论里出现过，但对本项目**不适用**，任何在此方向的工程努力都是浪费。

## 架构共识（来自四轮对抗性评审的结论）

以下是已确认的架构原则。任何修改这些原则的提议必须经过作者（人类）明确同意：

1. **数据格式必须 JSON-native**。不用 Articy:Draft、不用 Ink 脚本、不用 Fountain。所有 Schema 用 JSON Schema 定义。
2. **LLM 不能直接写状态**。所有状态变更只能由确定性代码应用，LLM 只能输出候选 JSON，经过校验后才能落到世界本体。
3. **编剧理论作为可替换插件**，不是核心层。Save the Cat、Egri、Story Circle 等都是插件，框架本身对理论选型保持中立。
4. **运行时和生产期分离**。运行时 = JSON 播放器，极薄、确定性、无 LLM。生产期 = AI 生成 + 校验 + 审阅流水线，是项目主要工作量。
5. **世界本体是真相之源**（Single Source of Truth）。所有 AI 生成内容必须能追溯到本体，违反本体的内容被校验器拒收。

## 仓库结构

```
/schema/          Schema 定义（JSON Schema）。所有其他模块依赖这里。改动必须谨慎。
/engine/          运行时播放器。Python 或 TS。极薄，无 LLM 依赖。
/state/           世界本体 + 状态总线 + 读写 API。
/generator/       AI 生成管线（prompt 模板、调度、层级化生成）。
/validator/       内容校验器（Schema 校验、图论校验、一致性校验）。
/tools/           作家工坊辅助工具（审阅界面、批量调度器等）。
/content/         生成出来的具体游戏内容（世界设定、对话树、角色卡）。
/game/            作者本人游戏实例（用到 /engine + /content）。
/docs/            项目文档。包含 ROADMAP.md、DECISIONS.md、DEBATE_NOTES.md。
```

每个子目录可能有自己的 CLAUDE.md 覆盖或补充本文件。

## 当前阶段

**阶段 0：基座搭建**。目标是在无 LLM 参与的前提下，把 Schema、播放器、状态总线、一个手写测试场景跑起来。

阶段 0 完成的判定标准：作者可以在终端里玩通一个手写的五节点场景，且 `/validator` 能对这个场景做出正确的通过/失败判断。

未进入阶段 1（单节点 AI 生成）之前，**任何关于 LLM 调用、prompt 设计、生成策略的代码都不应该被写入本仓库**。

## 给任何 Claude Code 会话的硬性规则

1. **永远先读本文件和你工作模块目录下的 CLAUDE.md**（如果存在）再开始。
2. **绝对不要跨越模块边界修改代码**。你在 `/generator` 工作时严禁修改 `/schema`、`/engine`、`/state`。如果你认为某个 Schema 必须修改才能完成任务，停下来，报告给作者，等待指示。
3. **绝对不要引入运行时 LLM 调用**。运行时 = `/engine`，LLM 调用只能出现在 `/generator` 和 `/tools` 里，且只在开发期执行。
4. **绝对不要使用以下依赖**：Articy:Draft、Ink（作为数据源）、Fountain、Yarn Spinner 新版（YSPL 许可证）。如果你觉得其中某个"更合适"，错了，不要用。
5. **禁止把编剧理论硬编码进 `/engine` 或 `/schema` 的核心逻辑**。编剧理论以插件目录 `/generator/plugins/<theory_name>/` 的形式存在，核心层对它们保持中立。
6. **JSON Schema 是唯一的 schema 定义方式**。不要用 Pydantic-only、protobuf、TypeScript interface 等替代（可以作为 JSON Schema 的生成产物，但源头必须是 JSON Schema）。
7. **遇到不确定的事先问，不要猜**。对架构层面的问题，宁可停下来问作者，不要自行决定。
8. **不要越俎代庖做规划**。规划由作者和专门的"规划师"会话负责。你是执行者。如果你收到的任务不清晰，向发起任务的人要求澄清，不要自己扩展范围。
9. **严禁修改本文件（CLAUDE.md）** 除非作者明确要求。
10. **严禁修改 `/docs/DECISIONS.md`**（架构决策记录）除非作者明确要求。你可以读它，不能改它。

## 给作者（人类）的工作流提示

- **新开一个 Claude Code 会话前**，决定它在哪个子目录工作，给它一个明确的完成标准。
- **并行会话的接口是文件和 Git 分支**。每个并行任务在自己的分支上工作，由你来合并。
- **Schema 变更是高风险操作**。如果一次并行会话中有任务需要改 Schema，停下所有其他会话，串行处理 Schema 变更，再恢复并行。
- **定期回读 `/docs/DEBATE_NOTES.md`**。它记录了为什么我们选了当前架构而不是其他架构。当你（或任何 Claude）想"改进"架构时，先去那里看看是不是已经被否决过。

## 文档参考

- `/docs/ROADMAP.md`：五阶段路线图（基座 → 单节点 → 场景 → 流水线 → 成品 + 开源剥离）。
- `/docs/DECISIONS.md`：架构决策记录（ADR 格式，每条决策独立带编号和日期）。
- `/docs/DEBATE_NOTES.md`：四轮对抗性评审的关键结论，作为反悔前必读。
- `/docs/SCHEMA_v0.md`：Schema 设计说明（配合 `/schema` 下的 JSON Schema 文件阅读）。

## 版本

本文件版本：v0.1（阶段 0 启动版）
最后更新：[作者填写日期]

---

**If you are a Claude Code session reading this file: acknowledge that you have read it and summarize the three rules most relevant to your current task before you start working.**