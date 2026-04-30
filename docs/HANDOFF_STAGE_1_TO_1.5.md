# HANDOFF_STAGE_1_TO_1.5.md

> 阶段 1 规划师会话 → 阶段 1.5 规划师会话的交接档。
> 让下一个规划师不继承阶段 1 上下文也能快速上手。

**日期**：2026-04-30 · **版本**：v0.1 · **产出方**：阶段 1 规划师会话

---

## 项目是什么（三句话）

Forgewright 是一条 AI 辅助的分支叙事 RPG 内容生产流水线。短期用于作者本人一款类 BG3 的中小型 RPG；长期剥离出通用框架开源。核心价值不在游戏运行时，在内容生产期的工具链。

阶段 1 已落地"单节点 AI 文本生成"；阶段 1.5 是**视觉资产生成**——为同一套节点配 VN 风立绘 + 场景背景。

## 玩家交互模式铁律（别重开讨论）

预生成选项式——玩家点 3–6 个预生成选项。**运行时无 LLM 调用**。**视觉资产同样静态预生成**——不存在运行时图像合成。1.5 阶段任何"实时换脸/动态生成"提议都不适用。

## 阶段 1 做了什么（别重建）

14 次 commit，约 2200 行业务代码 + 7 份新文档。主线：

- `/generator/` 模块从无到有：模块骨架、Pydantic 自动生成、LLMProvider Protocol + GeminiProvider、budget.py 成本守卫、generate_node 主函数（B+ 上下文 + 重试循环）、experiment + review_cli + metrics 工具链
- 配套 ADR：011（Provider 可插拔）/ 012（成本治理）/ 013（Structured Output）
- AI-as-judge 替代人工审阅：21 维度 / 5 类评分体系
- 验收：`/docs/STAGE_1_ACCEPTANCE.md`（有条件通过：schema 85% / 接受率 100%）

## 阶段 1 收尾时的架构遗留（清理工 / 阶段 2 主线 / 阶段 1.5 应略过）

来自 `/docs/STAGE_1_ACCEPTANCE.md` §4 的 R1–R8。**1.5 规划师只需关心其中跟视觉/Schema 相关的几条**：

| 编号 | 内容 | 1.5 规划师该不该处理 |
|---|---|---|
| R1 | Schema 合格率 85% | 否（属阶段 2 prompt 调优；与视觉无关） |
| R2 | 复合 condition few-shot 缺失 | 否（同上） |
| R3 | 选项过长 | 否（同上） |
| R4 | location_ref 错配（fixture 缺 location_candidates） | **可选**（如果 1.5 也用 fixture 形态调用图像 API，可借鉴此教训） |
| R5 | 本体污染（D1） | **重要**：1.5 一定会引入"角色 visual_assets" Schema 扩展；本体污染问题会迁移到视觉层（同一个 character_ref 不同立绘出现脸不一致是同源问题） |
| R6 | AI 判官替代人工 | **借鉴**：1.5 可以同样用 AI 判官评图，但视觉判官能力差异大，需要重新校准 |
| R7 | cost_log 高估 | **重要**：图像 API 单价比文本 LLM 高 1–2 个数量级，预算治理要重新设计；不能让 baseline_001 那种 0% 成功率的批次烧掉 $30 |
| R8 | 机械预检器 | **重要**：图像生成的可数值化属性（分辨率/格式/EXIF）也应预检 |

## 阶段 1.5 启动条件（摘自 ROADMAP「阶段 1.5」段，由 T-1.1 commit 1d2030f 落地）

**目标函数**：
- `generate_character_sheet(character_ref) -> list[ImageAsset]`：N 张表情/姿势立绘
- `generate_scene_background(location_ref) -> list[ImageAsset]`：1–3 张背景

**完成标志**：
- 资产入库 `/content/visuals/` + `manifest.json`
- 本体角色实体新增 `visual_assets` 字段（**首次动 Schema！** 已授权动 Schema，路径 C；详见下方 §警示）
- 至少为《铁誓驿站》3 个角色 + 1 个场景 完成资产生成 + 入库
- 接受率（用 AI 判官或作者本人）≥ 50%

**预算治理（建议规划师重新拍板）**：
- 文本 LLM 单调用约 $0.02；图像生成单调用 **$0.05–$0.40**（视提供商）
- 阶段 1.5 总盘子建议 $50–$80（高于阶段 1 的 $30）
- 单次硬卡建议 $1.00（高于阶段 1 的 $0.50，因为图像生成单价高）

## ⚠️ Schema 扩展警示（CLAUDE.md 规则 2 + 9 的特殊情况）

**阶段 1.5 是项目至今第一次动 Schema**。CLAUDE.md 规则 2 严禁跨边界改 Schema，规则 9 严禁不经授权改架构文件。但作者已在 ROADMAP「阶段 1.5」段（commit 1d2030f）**显式授权 Schema 扩展**，路径 C 含义如下：

- 允许在本体角色 Schema（`/state/ontology/` 桩或未来正式 Schema）新增 `visual_assets: array of ImageAssetRef` 字段
- 允许在 `/schema/` 新增 `image_asset.schema.json`
- 严禁修改 DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 任何已有字段
- Schema 升级走 MINOR bump（schema_version 0.1.x → 0.2.0）

**1.5 规划师产出 TASKS 文档时，必须有一条专门的 Schema 任务**，串行优先（schema 定稿前不开其他并行执行会话），同阶段 0 串行关键路径策略。

## 阶段 1.5 规划粗想（给下一个规划师做参考，不照抄）

下一个规划师应按阶段 0/1 规划师的开场流程：**先读全部元文档 → 给作者理解确认 → 等作者校准 → 再规划**。下面是阶段 1 规划师对阶段 1.5 任务拆分的**粗预判**，**未与作者校准过**：

### 关键架构决策（需作者拍板）

1. **图像提供商选择**：候选 Imagen 4 / GPT-Image-1 / Flux 1.1 Pro / Midjourney（API 化的 v7）/ 本地 SDXL
   - 跟 LLM 不同，图像 API **没有 LLMProvider 那么标准化的接口**；每家的提示语法、控制选项、并发模式差异大
   - 作者已表态"我看看有没有可以参考的（开源框架）"——规划师应预留时间帮作者比较 ComfyUI、A1111、Replicate 等生态
2. **风格定义**：类 BG3 的"半写实 + 油画感 + 戏剧光影"——但执行会话需要锚定的"风格基准图"才能稳定生成；建议作者提供 2–3 张参考图（自购或 Pinterest 收藏）
3. **角色一致性**：同一角色不同表情/姿势保持脸/服装一致——是 1.5 最硬的骨头
   - 候选方案：A. ControlNet + reference image；B. IPAdapter；C. LoRA fine-tune；D. 接受图片间细微差异
   - 不同提供商对 A/B/C 的支持度差异大，跟 #1 强耦合
4. **NPC 分级**：ROADMAP 提的轻档（4–6 张）+ 重档（10–15 张）双档——具体分给哪些 NPC 由作者决定
5. **Schema 扩展形态**：`ImageAsset` schema 字段（width / height / format / asset_id / generation_metadata 等）；`visual_assets` 在角色实体里如何引用

### 任务拆分粗预判（阶段 1 是 8 任务，阶段 1.5 估计 6–10 任务）

- T-1.5.0：HANDOFF 阅读 + 校准（规划师）
- T-1.5.1：新 ADR（图像提供商选择 + 一致性策略 + 视觉风格基准）
- T-1.5.2：Schema 扩展（image_asset.schema.json + 角色 ontology 加 visual_assets）— **串行关键路径**
- T-1.5.3：图像 provider 接口 + 默认实现（Imagen / GPT-Image-1）
- T-1.5.4：generate_character_sheet 主函数（含一致性策略）
- T-1.5.5：generate_scene_background 主函数
- T-1.5.6：资产入库 + manifest.json + /content/visuals/ 目录组织
- T-1.5.7：experiment + review CLI（图像版；review CLI 要能在终端展示缩略图或开浏览器）
- T-1.5.8：阶段 1.5 验收报告

## 与作者协作的风格备忘（继承自阶段 0/1）

- **作者不会编程**。所有代码产出通过执行会话完成；规划师的输出是任务拆解 + 提示词，不写代码
- 作者偏好快速决策：要推荐值让他拍板；不喜欢"每项都分析一遍"——给利弊 + 推荐，由他"全同意"或逐条改
- 作者打字偶尔有错字（GitHub 账号 `outsiderrr`）——以环境探测值为准
- 作者已建立 **AI-as-judge 习惯**（阶段 1 引入）；1.5 规划师可继续这一思路，但视觉判官需另写 prompt（21 维度文本 prompt 不直接适用）
- 作者明确不愿追求"最后 10% 完美主义"；schema 85% 留给阶段 2，1.5 阶段建议同样宽容
- 作者对**视觉**的态度：先做静态 PNG；技术成熟后再考虑短视频循环（schema 钩子预留即可，1.5 阶段不实现）

## 必读顺序（新规划师首轮阅读）

1. `/CLAUDE.md`
2. `/docs/ROADMAP.md`（特别是阶段 1.5 段 + 阶段 1 完成标志做对比）
3. `/docs/DECISIONS.md`（**全部 13 条**——尤其 ADR-002 / 011 / 012 / 013）
4. `/docs/DEBATE_NOTES.md`（至少 §1、§5）
5. `/docs/STAGE_1_ACCEPTANCE.md`（确认 §4 R1–R8 哪些与 1.5 相关）
6. `/docs/STAGE_1_TASKS.md`（执行会话提示词的产出格式参考）
7. `/content/test_scene_v0/scene.json`（本体桩；1.5 要为里面的角色生成立绘）
8. 本文件（HANDOFF_STAGE_1_TO_1.5.md）

## 工作模式（阶段 0/1 已跑通，不要改）

- **规划师会话**：产出任务拆分 + 提示词；不写代码；回答架构歧义时给利弊 + 推荐不替作者决定
- **执行会话**：只做单一任务；硬性限定在自己的模块目录；完成后 commit + push（末尾附 Co-Authored-By）
- **并行多会话**：模块互不重叠可并行；push 时 rebase 兜底
- **Schema 级变更**：1.5 阶段**唯一**例外，作者已在 ROADMAP 显式授权扩展（仅限 visual_assets 相关 schema）；规则 9/10 仍保护 CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / SCHEMA_v0.md（1.5 改 Schema 时需要新建 SCHEMA_v0.5.md 或 SCHEMA_v0.2.md，不要直接污染 v0.md）

## 阶段 1 残留的工作流改进建议（下个规划师可采纳）

- **AI 判官 prompt 模板化**：阶段 1 的 21 维度 prompt 是文本评审用，1.5 需要重写视觉版；建议规划师产出 `REVIEW_PROMPT_AI_JUDGE_VISUAL.md`
- **机械预检器**（R8）：图像有可数值化属性（分辨率、文件大小、是否含可识别角色），先机械检测再让 LLM 判官评语义；这条若 1.5 阶段先实现，对阶段 2 也直接受益
- **cost_log 反向校准**（R7）：阶段 1.5 启动前去 Google AI Studio 控制台对账一次，确认 cost_log 高估幅度；图像 API 也要做同样校准
