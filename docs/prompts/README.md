# /docs/prompts/ — 项目 AI 生成提示词归档

> **本目录定位（v0.2 起 broaden）**：存放本项目里**所有 AI 生成 / 供 AI 复用的提示词**，集中归档便于复盘、跨阶段对比、单文件修订。
>
> 当前两类：
> - `stage_N/` —— **L3 任务 paste-ready prompt**（本目录原始用途；受治理 §11 工作流约束；命名 `T-N.X.md`）。
> - 根目录其他 `.md` —— **L1 / 治理类起手 prompt 与 meta-prompt**（轻量归档，不绑 §11 工作流）。
>
> v0.4 「L3 prompt 文件化」的 governance 修订记录见 [/docs/governance.md](../governance.md) §11。

## 目录结构

```
/docs/prompts/
├── README.md                          # 本文件
├── L1_KICKOFF_ABC_PROPOSAL.md         # L1/治理类起手 prompt（提案，未应用）
├── stage_3/                           # 阶段 3 L3 paste-ready prompts (14 个文件)
│   ├── T-3.0.md                 # 起手清理 PATCH
│   ├── T-3.1.md                 # ADR-022~026 立项
│   ├── T-3.2.md                 # content_dependency_index sidecar schema
│   ├── T-3.3.md                 # 长对话一致性 C 起步
│   ├── T-3.4.md                 # playtest bots 框架
│   ├── T-3.5.md                 # 批量生成调度器
│   ├── T-3.6a.md                # 审阅 UI MVP
│   ├── T-3.6b.md                # 审阅 UI integrations
│   ├── T-3.7.md                 # 一致性维护
│   ├── T-3.8a.md                # version_recorder 独立模块
│   ├── T-3.9.md                 # Chapter/Act helper 库
│   ├── T-3.10.md                # 完成标志实测
│   ├── T-3.11.md                # 开源剥离边界 v0.2
│   └── T-3.12.md                # 阶段 3 验收报告
└── stage_4/                     # （阶段 4 起手时由 L2 整合规划师落地）
```

> ⬇️ 下列各节（L3 会话起步模板 / 命名规范 / 与 STAGE_N_TASKS / 历史不回填 / 修订流程 / 跳 BC 破例 / 工作流图）**只适用于 `stage_N/` 下的 L3 任务 prompt**；根目录的 L1/治理类 prompt 不受这些约束（见文末「其他 AI 生成 prompt」）。

## L3 会话起步模板（v0.4 工作流）

作者新会话首条消息标准格式：

**最简版**：
```
执行 T-3.0
```

**明示版**（推荐；避免歧义）：
```
请按 /docs/prompts/stage_3/T-3.0.md 的指示执行任务。
```

会话识别后第一步 Read 对应 prompt 文件 → 按内容开发 + 测试 + commit + push + 开 PR → A 阶段完成。

## 命名规范

- 阶段 N 任务编号：T-N.X（N = 阶段编号；X = 任务编号）
- 拆分子任务：T-N.Xa / T-N.Xb（如 T-3.6a / T-3.6b 拆审阅 UI MVP / integrations）
- 文件名：T-N.X.md（直接用任务编号）
- 路径：`/docs/prompts/stage_N/T-N.X.md`

## 与 STAGE_N_TASKS.md 的关系

- `STAGE_N_TASKS.md` = 阶段 N 任务清单 source-of-truth（含 wave 图 / 决策表 / ADR / 整合记录等架构层文档）
- `/docs/prompts/stage_N/` = 阶段 N 各 L3 任务的 paste-ready prompt 文件（实操层）
- `STAGE_N_TASKS.md` §8 改为表格引用 prompt 文件路径（不再内嵌 ` ```text` 代码块）

## 历史阶段不回填

阶段 0 / 1 / 1.5 / 2 已完成；旧 paste-ready prompts 仍存在 `STAGE_X_TASKS.md` §8 ` ```text` 代码块内。

不回填——历史阶段已 audit 完成，回填工作量大而收益小。阶段 3 起新规范即可。

## 修订流程

修订单个 prompt：直接 Edit `/docs/prompts/stage_N/T-N.X.md` + 走 ABC 闭环（同 v0.3 governance §10）。

prompt 文件 commit message 模板：

- `docs(prompt): T-N.X v1.1 — <修订要点>`（小修订）
- `docs(prompt): T-N.X v2.0 — <重写说明>`（大改）

prompt 文件版本号策略：

- v1.0 = STAGE_N_TASKS.md v1.0 整合时落盘的初版
- v1.X = 阶段 N 内的实测后微调（保留与 v1.0 兼容性；任务范围不变）
- v2.0 = 阶段 N 末期或阶段 N+1 重写（任务范围或工作流大改）

## 与跳 BC 破例 5 类的关系（参 v0.3 governance §10 + STAGE_3_TASKS.md §1.5.4）

- prompt 文件本身的 ergonomic 微调（措辞 / 引用路径 / 示例补充）属"审阅 UI 工坊化 ergonomic 改进"延伸 → 跳 BC 破例第 4 类
- prompt 文件的实质性修订（任务范围 / 模块边界变化）默认走完整 ABC

## 工作流图

```
作者起新 L3 会话（worktree + 新会话）
     │
     │ 首条消息：执行 T-3.X 或 请按 /docs/prompts/stage_N/T-N.X.md 执行
     ▼
会话 Read /docs/prompts/stage_N/T-N.X.md
     │
     ▼
按 prompt 内容开发 + 测试 + commit + push + 开 PR
     │
     ▼
A 阶段产出 = PR URL + commit hash + 测试输出
     │
     ▼
作者起 Codex 会话 review (B 阶段) → /docs/reviews/<date>_T-N.X_review.md
     │
     ▼
作者回 A 原会话/原分支 (C 阶段) → 追加 commit 到原 PR
     │
     ▼
L2 验收过关 → merge PR → 进下一个 L3
```

## 其他 AI 生成 prompt（非 L3）

根目录直接存放 L3 之外的「AI 生成、供 AI 复用」prompt（L1 治理起手、meta-prompt 等）。**不绑** §11 的 T-N.X 命名 / STAGE_N_TASKS / ABC 闭环；命名用描述性全大写（仿 [/docs/REVIEW_PROMPT_CODE_GPT.md](../REVIEW_PROMPT_CODE_GPT.md) 风格）。

当前内容：

- [`L1_KICKOFF_ABC_PROPOSAL.md`](L1_KICKOFF_ABC_PROPOSAL.md) —— 「ABC 阶段层级化 + 设计先于施工」提案的 L1 会话起手 prompt（提案，未拍板/未应用；配套提案全文在作者个人 vault）。

## 版本

- **v0.2（2026-06-08）**：作者授权 broaden 目录定位——从「仅 L3 paste-ready prompt」扩为「项目所有 AI 生成提示词归档」。新增根目录 L1/治理类 prompt（首个：`L1_KICKOFF_ABC_PROPOSAL.md`）。⚠️ **待同步**：governance.md §11 仍按「L3 prompt 文件化」框定本目录，对应措辞同步留待作者授权的 L1 会话处理（§11 属 L1 文档，不在本次 README 改动范围）。
- v0.1（2026-05-08）：首次落盘 — Wave 6 prompt 文件化工作流升级。
