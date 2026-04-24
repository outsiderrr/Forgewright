# HANDOFF_STAGE_0_TO_1.md

> 阶段 0 规划师会话 → 阶段 1 规划师会话的交接档。
> 让下一个规划师不继承阶段 0 上下文也能快速上手。

**日期**：2026-04-24 · **版本**：v0.1 · **产出方**：阶段 0 规划师会话

---

## 项目是什么（三句话）

Forgewright 是一条 AI 辅助的分支叙事 RPG 内容生产流水线。短期用于作者本人一款类 BG3 的中小型 RPG；长期剥离出通用框架开源。核心价值不在游戏运行时，在内容生产期的工具链。

## 玩家交互模式铁律（别重开讨论）

预生成选项式——玩家点 3–6 个预生成选项。**运行时无 LLM 调用**。不存在玩家欺诈问题。任何"反欺诈"/"实时生成"/"流式对齐"提议本项目都不适用，见 DEBATE_NOTES §1 已彻底排除。

## 阶段 0 做了什么（别重建）

9 次 commit，约 2000 行业务代码：

- `/schema/`：Schema v0.1.1 的 5 个 JSON Schema 文件（Draft 2020-12）+ 21 条测试
- `/engine/`：终端播放器（210 行 / ADR-004 上限 500 行；7 条测试）
- `/state/`：WorldState + effects + conditions + 本体桩；点分字符串 path；5+8 种 op 白名单；63 条测试
- `/validator/`：三层校验器（schema + graph + consistency）+ CLI；14 条测试
- `/content/test_scene_v0/`：《铁誓驿站》5 节点示例 + 3 个错误变体
- 验收：`/docs/STAGE_0_ACCEPTANCE.md`

## 阶段 0 收尾时的架构遗留（清理工，非阶段 1 主线）

1. **D5/D6 回填 SCHEMA_v0.md**：§3.4/§3.5 文字仍说"推迟至状态总线任务"，但 T-0.7 实际已用点分字符串 + 候选 enum。建议阶段 1 起手时做一个小 PATCH，改成"已固定"措辞。
2. **本体 Schema**：`/state/ontology/` 目前是桩（只含 SCENE 需要的 4 个实体）。真正的世界本体 Schema（ADR-006）应在阶段 2 前做；阶段 1 单节点生成沿用桩即可。
3. **CI 未配置**：阶段 0 未要求，阶段 3 审阅工作台之前应补。
4. **STAGE_0_ACCEPTANCE.md 自引用 hash**：表格里的 `ad1e7f5` 是 amend 前的 hash（因为 commit 无法包含自身最终 hash），非阻塞问题，可在阶段 1 PATCH commit 顺手修成"见 git log 最新记录"措辞。

## 阶段 1 启动条件（摘自 ROADMAP §阶段 1）

**目标函数**：`generate_node(context, requirements) -> DialogueNode`
- 通过 Schema 校验的单节点 JSON
- 格式合格率 ≥ 95%、人工接受率 ≥ 50%

**首次引入 LLM**：`/generator/` 目录在此诞生。CLAUDE.md 规则 3 在生产期放开，在运行时（`/engine`）**永久**保持关闭。

## 阶段 1 规划粗想（给下一个规划师做参考，不照抄）

下一个规划师应按阶段 0 规划师的开场流程做：**先读全部元文档 → 给作者理解确认 → 等作者校准 → 再规划**。下面是阶段 0 规划师对阶段 1 任务拆分的**粗预判**：

- Python dataclass 绑定层（/generator 操作 DialogueNode 需要类型化结构）
- LLM 提供商 + API 密钥 + 成本跟踪方案（一条新 ADR）
- Prompt 模板（few-shot 参考 SCENE_v0.md）
- Structured Output / Constrained Decoding 配置
- 生成 → 校验 → 重试循环
- 首轮真实 API 成本 + 合格率测量

实际任务清单由新规划师与作者对齐后产出，以上仅作抛砖引玉。

## 与作者协作的风格备忘

- **作者不会编程**。所有代码产出通过执行会话完成；规划师的输出是任务拆解 + 提示词，不写代码
- 作者偏好快速决策：要推荐值让他拍板；不喜欢"每项都分析一遍"——给利弊 + 推荐，由他"全同意"或逐条改
- 作者打字偶尔有错字（GitHub 账号 `outsiderrr` 曾被拼成 `outsidrrr`）——以环境探测值为准
- 作者对 **BG3 式剧情容错**（多路径汇合 / 角色槽位 / 结局可达性保证）有兴趣；阶段 2 ROADMAP 备忘已预留"新增 ADR：角色槽位"

## 必读顺序（新规划师首轮阅读）

1. `/CLAUDE.md`
2. `/docs/ROADMAP.md`（特别是阶段 1 段）
3. `/docs/DECISIONS.md`（至少 ADR-002、003、008）
4. `/docs/DEBATE_NOTES.md`（至少 §1、§5）
5. `/docs/SCHEMA_v0.md`（阶段 1 生成对象的形态）
6. `/docs/STAGE_0_ACCEPTANCE.md`（确认阶段 0 已验收）
7. 本文件（HANDOFF_STAGE_0_TO_1.md）

## 工作模式（阶段 0 已跑通，不要改）

- **规划师会话**：产出任务拆分 + 提示词；不写代码；回答架构歧义时给利弊 + 推荐不替作者决定
- **执行会话**：只做单一任务；硬性限定在自己的模块目录；完成后 commit + push（末尾附 Co-Authored-By）
- **并行多会话**：模块互不重叠可并行；push 时 rebase 兜底
- **Schema 级变更**：规则 9/10 保护 CLAUDE.md 和 DECISIONS.md，需作者明确授权
