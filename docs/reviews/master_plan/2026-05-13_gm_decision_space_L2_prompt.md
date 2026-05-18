# GM 抉择空间结构化方案 — L2 综合规划师会话提示词

> Forgewright 项目 T-3X-0 阅读伴侣会话发掘出的核心问题（"如何把 CoC 模组里 GM 留白结构化为确定性 JSON 对话图所需数据"）的 L2 综合规划师入口。
>
> **使用方法**：开一个新 Claude 会话（worktree 或 conductor 任意），把下方 ` ```text` 代码块全文复制粘贴作为首条消息。L2 会话产出 → 给作者签字 → 进 L1 fixation 执行会话立 ADR-031 + 启动 T-3X-1 L3 工程会话。

**日期**：2026-05-13 · **版本**：v0.1 · **触发来源**：T-3X-0 阅读伴侣会话（claude/clever-lehmann-0709c4 worktree；Crimson Letters 听读样本反向归纳）

---

## 设计前提（不传给 L2 会话，作者了解即可）

1. **不是 critique 任务**——`REVIEW_PROMPT_L2_STAGE_TASKS.md` 是对 v0.1 草稿做 adversarial critique；本提示词是让 L2 综合规划师**从零起草 ADR 草案 + L3 prompt**。两份提示词角色不同。
2. **本提示词承接**：T-3X-0 阅读伴侣会话产出（对照表 + 偏好档 v0.1）→ L2 综合规划师起草 ADR-031 草案（暂定编号；落地时按 DECISIONS.md 空闲编号顺延）+ T-3X-1 paste-ready prompt → 作者签字 → L1 fixation 落地 → L3 工程执行。
3. **是否走 cross-LLM critique 由 L2 自判**——如 L2 产出方案多分支 / 决策影响范围广 / 字段定义争议大，建议走 Codex GPT-5.5 critique（用 `REVIEW_PROMPT_L2_STAGE_TASKS.md` 模板）；如方案聚焦无分歧，可直接进 L1 fixation。
4. **不修 ADR-030**——ADR-030 已接受（字段集预留），本任务可能增立 ADR-031（GM 抉择空间结构化）；ADR-030 字段集仍按原计划在 T-3X-1 L3 落地。

---

## 复制下面整段代码块到新 Claude L2 会话

```text
你是 Forgewright 项目的 L2 综合规划师会话。本会话目标 = **基于 T-3X-0 阅读伴侣会话产出，起草"GM 抉择空间结构化方案"ADR 草案 + T-3X-1 L3 工程会话 paste-ready prompt**。

# 你是什么会话（硬性边界）

- L2 综合规划师 = 起草 ADR 草案 + 出 L3 prompt
- **不写代码**
- **不修 L1 文档**（CLAUDE.md / DECISIONS.md / ROADMAP.md / DEBATE_NOTES.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md / STAGE_*_TASKS.md / AESTHETIC_PREFERENCES.md）
- **不修 ADR-030**——ADR-030 字段集预留仍按原计划由 T-3X-1 L3 实证归纳，不在本会话职权内
- **不替作者拍板架构决策**——给候选方案对比 + 推荐 + 利弊 + 风险，由作者签字
- **唯一允许写入的位置**：`/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md`（落档你的 ADR 草案 + T-3X-1 prompt 草稿）

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。第一款游戏 = "克苏鲁版极乐迪斯科 spiritual successor" —— 纯文本驱动、对话 + 调查 + 检定、**无战斗**、**无思维内阁**、**无内心独白**。运行时极薄 JSON 对话图播放器（**无 LLM**）；玩家交互 = 3-6 个预生成选项。当前 main HEAD `1c1c04b`，阶段 3 工程层 12 任务已 merge（2026-05-08~09），Wave 7 起 T-3.10 实测期（1 周 ≥ 10 场景），ADR 已立至 ADR-030。

# T-3X-0 触发洞察（本任务的起点）

T-3X-0 是作者本人**非工程**审美锚点任务——让作者读 3 部经典剧本（Crimson Letters + Dead Light + 极乐迪斯科 Final Cut），反向归纳审美偏好，产出 AESTHETIC_PREFERENCES.md v0.1 给 T-3X-1 工程会话立 ADR-030 schema 字段集。

**作者本次会话只听完了第 1 部 Crimson Letters 的中文听读版**（约 73 KB / 24 节），然后**主动收尾 T-3X-0**。理由：识别出**真正阻塞 T-3X-1 的不是审美 4 维**，而是**"GM 抉择空间结构化"**这个引擎抽象层的核心问题。

## 核心问题（要解决的）

**CoC 模组是骨架式作品**——Crimson Letters 这类模组写给守秘人（GM）跑团时即兴用，**留白大量"GM 抉择空间"**。但 Forgewright 引擎要求**确定性 JSON 对话图**——所有"GM 抉择"都必须**预先压成数据**或**由确定性代码即时生成**。**两者之间存在结构鸿沟**。

无论是 **(场景一) 改编已有模组**，还是 **(场景二) 原创**，核心都是同一个工作流：

**"叙事意图（人脑 / 模组）→ 确定性 JSON 对话图（引擎可执行）"的转换**

差别只在输入端（已有材料库 vs 作者一句话）；**输出端共用同一份 schema**。所以这个抽象层一旦立起来，两种场景都能复用。这是本任务的杠杆所在。

## GM 抉择空间的 7 种具体形式（Crimson Letters 反向归纳）

| 形式 | Crimson Letters 中的体现 | 候选结构化方案（脑暴，未拍板） |
|---|---|---|
| **真凶选择**（5 候选 NPC） | 模组列考特 / 罗奇 / 弗林德斯 / 维克 / 自定，由 GM 选 | 元参数（culprit_id），开场定 / 动态定 / 随机 |
| **NPC 反应**（多套行为按玩家行为切换） | 每个 NPC 有"角色扮演钩子" + "守秘人笔记" + "若被选为真凶"段 | NPC 状态机 + 反应矩阵（state × event → next_state + response） |
| **威胁显现节奏**（5 征兆何时触发） | "通路征兆" 5 种由 GM 决定何时触发 | 倒计时机制（行动数 / 事件 / 时间触发） |
| **多解决路径**（藏 / 销毁 / 神话技能） | 模组列 3 种结局，玩家选 + GM 评判 | 多结局分支（world_state → ending） |
| **场景扩展**（GM 加剧情线 / 派系） | 模组明文鼓励 GM 加自己的剧情 | 场景模板 + 插件式追加 |
| **难度调整**（玩家莽撞则加难度） | 模组写"对瓷器店里横冲直撞的莽夫不该手软" | 难度参数（影响检定 DC / NPC 警觉度） |
| **即兴**（红鲱鱼地点临场变黑帮入场点） | 试玩示例：霍布豪斯宅邸临场变成黑帮入场点 | **不可完全结构化** ⚠️ |

## 核心赌注（本任务的隐含前提）

Forgewright 工具一期的核心赌注 = **"AI 海量预生成 + 人工审阅 = 给玩家伪即兴体验"**。

如果这个赌注不成立（AI 无法预生成足够丰富的内容覆盖 GM 即兴空间），整个工具一期定位需要重新审视。**你的 ADR 草案必须显式承认这个赌注，并列出"如赌注不成立的回退方案"作为风险段**。

# 你的核心任务

## 任务 1：起草 GM 抉择空间结构化方案 ADR 草案

**目标产出**：`/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md`

内容必须包含：

1. **背景**：T-3X-0 触发上下文 + 与 ADR-030 关系 + 核心问题陈述
2. **决策范围**：明确 ADR 覆盖什么、不覆盖什么（特别是与 ADR-030 边界 + 与 ADR-029 技能体系边界 + 与 ADR-028 引擎与宿主分离边界）
3. **候选方案对比**（**至少 3 个**）：每个候选含
   - 核心抽象（数据模型 / 状态机 / 触发器机制）
   - 7 种 GM 抉择空间形式的覆盖度（哪些形式该方案覆盖、哪些不覆盖）
   - 工程复杂度（schema 字段数 / engine 改动 / generator 改动 / validator 改动）
   - 与现有 ADR 一致性（特别 ADR-002 / ADR-004 / ADR-006 / ADR-028 / ADR-029 / ADR-030）
   - 风险
4. **推荐方案**：按"决策完整性 + 工程可行性 + 与作者已知偏好对齐"三维选推荐
5. **赌注承认 + 回退路径**：核心赌注（AI 海量预生成 → 伪即兴）+ 如赌注不成立的回退方案（如：手工编写、玩家自定义、AI 在线生成模式等——讨论但不立即采纳）
6. **替代方案及否决理由**：每个未选方案的否决理由
7. **后果**：决策对其他模块的影响（schema / engine / generator / validator / content / tools）
8. **未解项**：明确列出本 ADR 暂不解决、留给后续 ADR 或工程会话的问题
9. **关联讨论**：与 ADR-005 / ADR-027 / ADR-028 / ADR-029 / ADR-030 的关系陈述

如确认要新立 ADR，预定编号 = **ADR-031**（DECISIONS.md 当前最大 ADR-030，按顺序）。但如果你判断本任务不需要立新 ADR（如可整合进 ADR-030 v0.2 修订），请在草案前言明示并给出理由。

## 任务 2：起草 T-3X-1 L3 工程会话 paste-ready prompt

**目标产出**：同一文件 §最后一段 paste-ready prompt 段（参考 STAGE_3_TASKS.md §8 任务 prompt 体例）

T-3X-1 在 STAGE_3_TASKS.md v1.0.1 + ADR-030 中原本定位 = **基于 T-3X-0 产出的 AESTHETIC_PREFERENCES.md v0.1 落地 ADR-030 schema 字段集 + prompt hook**。本次 T-3X-0 收尾产出**还多出**一个核心方向：**基于本 ADR 草案（ADR-031）落地 GM 抉择空间结构化机制**。

你需要判断 T-3X-1 是否：

- **方案 A**：合并为单一 L3 任务（同时落 ADR-030 字段 + ADR-031 机制）
- **方案 B**：拆分为两个 L3 任务（T-3X-1a = ADR-030 字段；T-3X-1b = ADR-031 机制）
- **方案 C**：T-3X-1 仍按原 ADR-030 范围（只立审美字段）；ADR-031 落地推到 T-3X-2 新增 L3 任务

给出推荐 + 理由 + 风险评估。然后按推荐方案，给出 paste-ready prompt 完整文本（含模块边界 / 必读 / 待落地点 / 不要做的事 / 测试 / commit message 等 STAGE_3 §8 标准段落）。

# 必读（按顺序，全部读完再起草）

## 主审对象（T-3X-0 收尾产出）

1. `/docs/reviews/aesthetic/T-3X-0_crimson_letters_reading.md` — **本任务起点。Crimson Letters 阅读对照表，特别 §5 元结构判断 + §6 总结**
2. `/docs/AESTHETIC_PREFERENCES.md` v0.1 — **作者审美偏好基线**

## 上游约束（理解决策来源）

3. `/CLAUDE.md` — 项目硬 10 条规则
4. `/docs/ROADMAP.md` §阶段 3 + §阶段 4
5. `/docs/DECISIONS.md` — 全部 ADR；特别 **ADR-002 / ADR-004 / ADR-005 / ADR-006 / ADR-027 / ADR-028 / ADR-029 / ADR-030**
6. `/docs/DEBATE_NOTES.md` — 全文重点 §1 §2 §6 §8 §9 + Round 5 段
7. `/docs/SCHEMA_v0.md` + `/docs/SCHEMA_v0.2.md` + `/docs/SCHEMA_v0.3.md` — schema 语义边界
8. `/docs/SCENE_v0.md` — 场景级数据模型

## 历史决策对照

9. `/docs/HANDOFF_STAGE_2_TO_3.md` — 阶段 3 接口
10. `/docs/STAGE_3_TASKS.md` — 阶段 3 任务清单（重点 §1.5 ABC 流程 + §8 任务 prompt 体例）
11. `/docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md` v0.2 — 审美层决策（ADR-030 触发链）
12. `/content/test_scene_v0/scene.json` — gold standard 场景（参考输出端 schema 形态）

## 样本（理解作者听感反应来源）

13. `/Users/outsider/Desktop/剧本/猩红信笺_听读版_全文.txt` — 作者听读样本全文（约 73 KB / 24 节，纯中文，桌面文件不在仓库）—— **不要求精读全文**，但可按需采样阅读以理解作者对 CoC 模组结构的具体反应

# 已知约束（不可违反）

## 来自 CLAUDE.md

- 数据格式必须 JSON-native（JSON Schema 是唯一 schema 定义方式）
- LLM 不能直接写状态（所有状态变更只能由确定性代码应用）
- 运行时和生产期分离（运行时 = JSON 播放器，无 LLM）
- 世界本体是真相之源（Single Source of Truth）
- 编剧理论作为可替换插件，不是核心层

## 来自 ROADMAP / 战略校准 v0.1

- 第一款游戏定位 = "克苏鲁版极乐迪斯科 spiritual successor"
- **不做**：传统战斗系统 / 思维内阁 / 内心独白
- **主做**：对话 + 调查 + 物品 + NPC + 技能体系 + 检定
- MVP 场景数量 = 10-100 弹性区间（ADR-010 v0.2）

## 来自 ADR-027 / ADR-028 / ADR-029

- World-Agnostic Principle：不绑定具体世界观
- 引擎与宿主分离：本 ADR 决策应作用于**生成期**，不在引擎运行时强制注入
- 技能体系作为项目配置层：本 ADR 不绑定具体技能体系

## 来自 ADR-030

- ADR-030 字段集留空预留待 T-3X-1 实证归纳——本 ADR **不**预定 ADR-030 字段集
- 本 ADR 与 ADR-030 协同但范围不重叠：ADR-030 = "作者审美维度词汇库"；本 ADR = "GM 抉择空间结构化"

## 来自 AESTHETIC_PREFERENCES.md v0.1

- 作者**已表态**：CoC 骨架结构 OK（可借鉴）
- 作者**已表态**：审美 4 维具体度量 TBD（可推到 demo 文本或工程会话补充）
- 作者**已表态**：核心赌注（AI 海量预生成 → 伪即兴）需在本 ADR 显式承认

# 评审维度（你的 ADR 草案需覆盖）

## 1. 决策完整性

- 覆盖 T-3X-0 对照表 §5 列出的 7 种 GM 抉择空间形式中**至少 6 种**（即兴可承认不可结构化）
- 覆盖两种工作场景（改编模组 + 原创）的共同点

## 2. 与现有 ADR 一致性

- 是否违反 CLAUDE.md 10 条规则？
- 是否与 ADR-002 / ADR-004 / ADR-006 / ADR-028 冲突？
- 是否与 ADR-030 范围重叠？

## 3. 工程复杂度

- schema 字段集大小（具体可量化估算）
- engine 模块改动（运行时是否需要新机制？如状态机、条件触发器、好感度计数等）
- generator 模块改动（AI prompt 模板新增字段）
- validator 模块改动（新增校验规则）

## 4. AI 可生成性

- AI 是否能在合理 token 预算 + cost 内生成符合本机制的内容？
- 单场景的 LLM 调用次数估算
- baseline_NNN 数据可参考（如 baseline_010 / baseline_011 等阶段 2/3 实测数据）

## 5. 作者偏好对齐

- 与 AESTHETIC_PREFERENCES.md v0.1 §2 + §5 表态对齐
- 与 ROADMAP §阶段 3 + 战略校准 v0.1 §Q1.4 北极星指标（更快更好完成 A）对齐
- 不引入"过预防性设计"或"过激进设计"

## 6. 失败模式

- 如核心赌注（AI 海量预生成 → 伪即兴）不成立，回退路径是什么？
- 如某种 GM 抉择空间形式（如即兴）确实无法结构化，玩家体验如何弥补？

# 产出物落档

你的所有产出统一落到：

```
/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md
```

文件结构建议：

```markdown
# GM 抉择空间结构化方案 — ADR-031 草案 + T-3X-1 L3 prompt

**日期**：YYYY-MM-DD · **版本**：v0.1 · **产出方**：L2 综合规划师会话

## 0. 前言

[是否需要新立 ADR-031 / 整合进 ADR-030 v0.2 的判断 + 理由]

## 1. ADR-031（暂定）草案

### 1.1 背景
### 1.2 决策范围
### 1.3 候选方案对比（≥ 3 个）
### 1.4 推荐方案
### 1.5 赌注承认 + 回退路径
### 1.6 替代方案及否决理由
### 1.7 后果（对其他模块的影响）
### 1.8 未解项
### 1.9 关联讨论

## 2. T-3X-1 拆分判断

[方案 A 合并 / B 拆分 / C 推到 T-3X-2 的对比 + 推荐 + 理由]

## 3. T-3X-1 L3 paste-ready prompt

[按 STAGE_3 §8 体例完整 prompt 文本]

## 4. 与 cross-LLM critique 的关系

[是否建议走 critique 流程 + 理由]

## 5. 移交给作者签字的明示事项

[列出本草案需要作者明示授权的事项，参考 DECISIONS.md §变更历史"作者明确授权"段落措辞]

## 6. 版本

v0.1 / YYYY-MM-DD / L2 综合规划师会话产出
```

# 跑批要求

- 必读全部读完再起草——不要边读边写
- 产出体量预期：1500–3500 行 markdown
- 不写代码、不修任何已有 L1 文档、不修 ADR-030
- 落档后给作者 git commit + push 命令模板让作者复制运行（不自己 commit）
- 报告 chat 末尾仅输出：落档路径 + 草案总长 + 候选方案数 + 推荐方案 + 建议是否走 cross-LLM critique + git 命令模板

# 不要做的事

- ❌ 不要直接修 ADR-030（字段集预留不动）
- ❌ 不要替作者拍板（候选方案对比 + 推荐 + 利弊 + 风险，最终签字由作者）
- ❌ 不要把 ADR 草案直接写到 DECISIONS.md（草案落到 master_plan 目录；定稿走 L1 fixation 执行会话）
- ❌ 不要给 T-3X-1 prompt 加跨模块工作（如 prompt 里写"同时改 engine 状态机 + schema 字段 + validator 规则"——保持模块边界）
- ❌ 不要做 SCOPE EXPANSION（本任务范围聚焦 GM 抉择空间结构化，不顺手扩展到玩家关系模型 / 多人合作 / 多分支存档等阶段 4+ 议题）
- ❌ 不要假装作者审美 4 维已确定（v0.1 偏好档大量 TBD，本 ADR 应在不依赖具体 4 维度量的前提下立起来）

# 完成标志

- `/docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md` 落档
- 含 ≥ 3 个候选方案完整对比
- 含推荐方案 + 赌注承认 + 回退路径
- 含 T-3X-1 拆分判断（A/B/C）+ paste-ready prompt
- 含与 cross-LLM critique 关系判断
- chat 输出：路径 + 总长 + 候选方案数 + 推荐 + critique 建议 + git 命令模板

开始起草。
```

---

## 后续工作流（作者侧；不传给 L2 会话）

```
T-3X-0 阅读伴侣会话（本会话）产 AESTHETIC_PREFERENCES.md v0.1 + 对照表
    ↓
[作者起 Claude L2 综合规划师会话 + 用本提示词]   ← 本文件
    ↓
L2 会话落档 /docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md
    ↓
[作者判断是否走 cross-LLM critique]
    ↓ (如走)
[作者起 Codex 会话 + 用 REVIEW_PROMPT_L2_STAGE_TASKS.md 模板（占位符填本草案）]
    ↓
Codex critique 落档 → [作者起新 Claude L2 整合会话] → 产 v1.0
    ↓ (如直接跳)
作者签字
    ↓
L1 fixation 执行会话 → 立 ADR-031 + 更新 STAGE_3_TASKS.md 增 T-3X-1 paste-ready prompt
    ↓
L3 工程会话（T-3X-1 / T-3X-1a + T-3X-1b / T-3X-2 视拆分判断）→ 立 schema 字段 + 改 AI prompt 模板 + 改 engine（如需）
```

---

## 与现有治理的关系

本提示词对应工作流的 **L2 起草步骤**（不同于 `REVIEW_PROMPT_L2_STAGE_TASKS.md` 的 L2 critique 步骤）。整体 L1 → L2 → L3 治理见 `/docs/governance.md` v0.3。

---

## 版本

本文件版本：v0.1
最后更新：2026-05-13
首次创建用途：T-3X-0 收尾 → ADR-031 起草 → T-3X-1 启动衔接
