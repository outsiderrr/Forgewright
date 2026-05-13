# GM 抉择空间结构化方案 — ADR-031 草案 + T-3X-1 L3 prompt

> 本文件 = L2 综合规划师产出（**起草档；待作者签字**）。承接 T-3X-0 阅读伴侣会话（[`/docs/reviews/aesthetic/T-3X-0_crimson_letters_reading.md`](aesthetic/T-3X-0_crimson_letters_reading.md) §5 + [`/docs/AESTHETIC_PREFERENCES.md`](../../AESTHETIC_PREFERENCES.md) §5）识别的"GM 抉择空间结构化 = 引擎抽象层核心问题"议题。
>
> 由作者签字 → L1 fixation 执行会话立 ADR-031 + 更新 STAGE_3_TASKS.md → L3 工程会话（T-3X-1 拆分形态由 §2 拍板）启动。

**日期**：2026-05-13 · **版本**：v0.1 · **产出方**：T-3X L2 综合规划师会话（claude/jovial-elion-c8d60c worktree）
**主输入**：T-3X-0 收尾 3 文件（对照表 §5 + 偏好档 v0.1 §5 + L2 提示词）+ 必读 13 项
**触发上下文**：T-3X-0 阅读伴侣会话 2026-05-13 Crimson Letters 单样本反向归纳 → 识别 7 种 GM 抉择空间形式 → L2 提示词承接

---

## 0. 前言（是否需要新立 ADR-031）

### 0.1 判断

**结论：是，需要新立 ADR-031**（不应整合进 ADR-030 v0.2 修订）。

### 0.2 理由

- **范围不重叠**：
  - **ADR-030**（AestheticPreference schema；2026-05-12 已 merge）= "作者审美维度词汇库"——温度 / 节奏 / 弧光 / 价值轴等**质感层**字段集
  - **本 ADR-031**（GM 抉择空间结构化）= "引擎抽象层机制"——CoC 骨架结构 → 确定性 JSON 对话图的转换契约；schema + engine + generator + validator 多模块影响
- **决策颗粒度独立**：ADR-030 的字段集可纯由作者偏好驱动；ADR-031 涉及引擎运行时执行模型、generator 生成期决策结构、validator 校验语义——架构层级更深，需独立可追溯决策
- **赌注层级不同**：ADR-031 含一个**项目级隐含赌注**（"AI 海量预生成 + 人工审阅 = 给玩家伪即兴体验"——T-3X-0 偏好档 §5.4 明示）；如赌注不成立，工具一期定位需重新审视。这种**项目级赌注**应有独立 ADR 承载，不应埋在 ADR-030 v0.2 子段
- **预定编号**：DECISIONS.md 当前最大 ADR-030（2026-05-12 已 merge）；新 ADR 顺延 **ADR-031**

### 0.3 范围声明（本 ADR 覆盖 / 不覆盖）

| 覆盖 | 不覆盖 |
|---|---|
| GM 抉择空间 7 种形式的结构化契约 | ADR-030 字段集（审美词汇库；由 T-3X-1a 实证归纳）|
| 现有 schema（dialogue_graph / character / clock / chapter）的语义边界扩展 | ADR-029 项目配置层（技能体系；独立机制）|
| 生产期 generator 流水线对 GM 抉择空间的实现策略 | ADR-028 引擎与宿主分离（本 ADR 严守此原则；详 §1.2.B）|
| validator 新增校验规则（机械层 / 拓扑层） | 阶段 4 进阶机制（GOAP NPC / 多人合作 / 多分支存档）|
| 项目级赌注承认 + 回退路径 | 长对话一致性（ADR-024 已覆盖；本 ADR 不重复）|

---

## 1. ADR-031（暂定）草案

### 1.1 背景

#### 1.1.1 触发链

```
战略校准 v0.1 (2026-05-09)
    ↓ 北极星 = A 完成度
审美层决策 v0.2 (2026-05-09)
    ↓ §6 修订清单 + §7 T-3X-0 指引模板
PR-A/B/C/D 全部 merge (2026-05-12)
    ↓ ADR-030 (字段集预留) + STAGE_3_TASKS.md v1.0.1
T-3X-0 阅读伴侣会话 (2026-05-13)
    ↓ Crimson Letters 单样本反向归纳
识别"GM 抉择空间结构化 = 引擎抽象层核心问题"
    ↓ AESTHETIC_PREFERENCES.md v0.1 §5 + 对照表 §5
本 L2 综合规划师会话 → ADR-031 起草（本草案）
```

#### 1.1.2 核心问题陈述

**CoC 模组（Crimson Letters 这类）是骨架式作品**——为守秘人（GM）跑团时**即兴**用，**留白大量"GM 抉择空间"**：

- NPC 描写 / 事实线索 / 角色扮演钩子 / 守秘人笔记 / 时间线 / 多嫌疑人结构 = **骨架**（可结构化）
- 真凶选择 / NPC 反应路由 / 威胁节奏 / 解决路径 / 场景扩展 / 难度调整 / 即兴 = **留白**（由 GM 跑团时即兴决定）

而 Forgewright 引擎要求 **确定性 JSON 对话图**（ADR-002 + ADR-004 极简运行时；DEBATE §5）——所有"GM 抉择"必须**预先压成数据**或**由确定性代码即时生成**。

**两者之间存在结构鸿沟**。本 ADR 要解决的就是"如何把 GM 留白结构化为引擎可执行数据"。

#### 1.1.3 两种工作场景共同点（关键洞察）

无论是 **(场景一) 改编已有 CoC 模组** 还是 **(场景二) 原创**，核心都是同一个工作流：

```
叙事意图（人脑 / 模组）→ 确定性 JSON 对话图（引擎可执行）
```

差别只在输入端：

| 场景 | 输入 | 工作流 |
|---|---|---|
| 改编模组 | 已有材料库（NPC + 钩子 + 留白）| 结构提取 + 填补留白 |
| 原创 | 作者一句话 / 主题 | 结构生成 + 填充细节 |

**输出端共用同一份 schema**——所以抽象层一旦立起来，两种场景都能复用。**这是本 ADR 的杠杆所在**。

#### 1.1.4 7 种 GM 抉择空间形式（Crimson Letters 反向归纳）

T-3X-0 对照表 §5 + L2 提示词识别的 7 种形式：

| # | 形式 | Crimson Letters 体现 | 候选结构化机制（脑暴起点） |
|---|---|---|---|
| F1 | **真凶选择**（5 候选 NPC） | 模组列考特 / 罗奇 / 弗林德斯 / 维克 / 自定 | 元参数（`culprit_id`）+ state path `world.culprit` |
| F2 | **NPC 反应**（多套行为按玩家行为切换）| 每 NPC 含"角色扮演钩子" + "守秘人笔记" + "若被选为真凶"段 | NPC 状态机 + 反应矩阵（state × event → next_state + response）|
| F3 | **威胁显现节奏**（5 征兆何时触发）| "通路征兆" 5 种由 GM 决定何时触发 | ADR-017 clock + tick_effects |
| F4 | **多解决路径**（藏 / 销毁 / 神话技能）| 模组列 3 种结局 | 现 dialogue_graph end nodes + world_state → ending 分支 |
| F5 | **场景扩展**（GM 加剧情线 / 派系）| 模组明文鼓励 GM 加自己的剧情 | 场景模板 + 插件式追加（多 dialogue_graph 拼接）|
| F6 | **难度调整**（玩家莽撞则加难度）| 模组写"对瓷器店里横冲直撞的莽夫不该手软" | 难度参数（影响 active_check DC / NPC 警觉度 state path）|
| F7 | **即兴**（红鲱鱼临场变黑帮入场点）| 试玩示例：霍布豪斯宅邸临场变成黑帮入场点 | ⚠️ **不可完全结构化**（详 §1.5 赌注承认）|

### 1.2 决策范围

#### 1.2.A 与 ADR-030 的边界

- **ADR-030（已立）** = 字段集预留（AestheticPreference schema 容器；待 T-3X-1a 实证归纳具体字段）；侧重**质感词汇库**
- **本 ADR-031** = GM 抉择空间结构化机制；侧重**叙事结构契约**
- **不重叠**：偏好档（ADR-030）告诉 AI "这场戏应该写得多暗黑、节奏多紧"；GM 抉择空间机制（ADR-031）告诉引擎 "这场戏的 NPC 反应路由 / 倒计时 / 多结局应该怎么数据化执行"

#### 1.2.B 与 ADR-028 引擎与宿主分离的边界

- ADR-028 = 引擎核心不实现具体输入输出形态；输入 = 离散标识符；输出 = 结构化叙事块
- 本 ADR-031 设计的 GM 抉择空间数据**全部作用于生成期**（generator + validator 在 prompt 注入 + 校验阶段使用）+ **少量作用于运行时**（engine 在 ADR-017 clock tick + ADR-008 state effect 中已有同款机制；本 ADR 不引入新的运行时执行复杂度）
- **严守 ADR-028**：本 ADR 不引入任何宿主层（鼠标 / 键盘 / VR / 语音）相关字段

#### 1.2.C 与 ADR-029 技能体系作为项目配置层的边界

- ADR-029 = 引擎核心不预设技能列表 / 数量 / 骰子规则；只规范 `active_check`（选项级主动检定）+ `passive_injection`（节点级被动注入）基础机制
- 本 ADR-031 的 F6 难度调整 = `active_check.dc` 字段调整 + NPC 警觉度 state path（属于 character 的可配置 attribute）；**完全在 ADR-029 配置层影响范围内**，不引入新技能机制
- **严守 ADR-029**：F1-F7 的所有候选机制都不绑定具体技能体系；具体 attribute / DC 公式由项目配置层定义

#### 1.2.D 与 ADR-027 World-Agnostic Principle 的边界

- ADR-027 = schema / prompt / 代码不引入硬编码单一世界观假设
- 本 ADR-031 含 CoC 体裁特征（如 SAN / 倒计时显现 / 多嫌疑人调查）——这些是**叙事结构层**特征（与世界观不绑定；其他体裁如赛博朋克侦探、维多利亚悬疑都能复用）
- **严守 ADR-027**：本 ADR schema 字段命名中性（不用 `coc_culprit_pool` 而用 `culprit_pool`；不用 `cthulhu_threat_ticks` 而用 `escalation_clock`）

#### 1.2.E 与 ADR-002 / ADR-004 / ADR-006 极简运行时的边界

- ADR-002 = 运行时不调用 LLM
- ADR-004 = 运行时与生产期严格分离
- ADR-006 = 世界本体是真相之源；LLM 不能直接写状态
- 本 ADR-031 的 F2 NPC 状态机 = **生产期 AI 生成 + 人工审阅的静态数据**；运行时只需**查表**（state × event → next_state + response），与现有 ADR-008 condition 评估同款，不调用 LLM
- **严守极简运行时**：F1-F7 的所有候选机制运行时执行模型都是"查表 + 应用 state effect + tick clock"，不引入新执行复杂度；预计运行时代码增量 ≤ 100 行（DEBATE §5"500 行"上限充裕）

### 1.3 候选方案对比

#### 1.3.A 候选方案 A：纯枚举 + 元参数化（最薄）

**核心抽象**：完全复用现有 schema（dialogue_graph + character + clock + chapter）；GM 抉择空间通过 state path 元参数 + 现有机制覆盖。

| 7 种形式 | A 覆盖方式 | 是否原生支持 |
|---|---|---|
| F1 真凶选择 | state path `world.culprit_id`（开场 chapter 入口节点设置）+ option.condition 路由 | ✓ 现 schema 支持 |
| F2 NPC 反应 | character.dramatic_triggers（ADR-019）+ 节点级 narration 按 condition 路由 | △ 部分（无显式状态机）|
| F3 威胁节奏 | ADR-017 clock + tick_effects | ✓ 现 schema 支持 |
| F4 多解决路径 | 现 dialogue_graph end nodes + state_paths_written 分支 | ✓ 现 schema 支持 |
| F5 场景扩展 | 多个独立 dialogue_graph 拼接（chapter.acts.included_scenes 排列）| ✓ 现 schema 支持 |
| F6 难度调整 | state path `world.difficulty` + active_check.dc 公式（项目配置层）| ✓ 现 schema 支持 |
| F7 即兴 | ⚠️ 不结构化；预生成 multi-variant 在选项层提供"多入口"（每场景 6-10 个 option 中 3-5 个为非线性入口）| ⚠️ 仅缓解 |

**工程复杂度**：
- schema 字段数：**0 新增字段**（完全复用）
- engine 改动：**0 行**（不引入新执行模型）
- generator 改动：~50-100 行（prompt 模板新增"GM 抉择空间引导段"+ generation_trace 记录 culprit_id 等元参数）
- validator 改动：~30-50 行（拓扑层校验多结局可达性已在 ADR-021 §2B 覆盖；F1 真凶选择路由的"culprit 一致性"校验新增）

**与现有 ADR 一致性**：
- ✓ 完全兼容 ADR-002/004/006/027/028/029/030
- ✓ 不破 schema_version（dialogue_graph 仍 0.1.1）

**风险**：
- F2 NPC 反应表达力弱——CoC 模组那种"NPC 多层伪装"（绅士古玩商 → 食尸鬼）在节点级 narration 路由层表达可能笨重；作者审阅时难以追溯"为什么这个 NPC 在这个分支说这句话"
- F7 即兴的"伪即兴体验"完全依赖**预生成内容海量** + **AI 创意触达边界**——核心赌注完全押在 A 方案的成败上

**优点**：
- 工程成本最低；阶段 3 即可落地
- 零新概念引入；作者学习成本零
- 与现有 baseline_011 工程层 100% gross_pass_rate 不冲突

#### 1.3.B 候选方案 B：NPC 状态机 + 反应矩阵（中等）

**核心抽象**：在 A 基础上**显式新增** `npc_state_machine` schema——每个 NPC 含 state graph（state × event → next_state + response template）。

| 7 种形式 | B 覆盖方式 | 是否原生支持 |
|---|---|---|
| F1 真凶选择 | 同 A（元参数）| ✓ |
| F2 NPC 反应 | **NPC 状态机**：每 NPC 定义 states + transitions + 每 state 的 response_template（含 narration 变体 + 可选 effects）| ✓ 强表达 |
| F3 威胁节奏 | 同 A（clock）| ✓ |
| F4 多解决路径 | 同 A（end nodes）| ✓ |
| F5 场景扩展 | 同 A | ✓ |
| F6 难度调整 | 同 A + **NPC 状态机的"警觉度" state**（如 `vellin.alertness ∈ {calm, suspicious, hostile}`）| ✓ 增表达 |
| F7 即兴 | 同 A | ⚠️ 仅缓解 |

**新增 schema 字段（草拟，不预定）**：

```json
// /schema/npc_state_machine.schema.json (首版 const "0.4.0")
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["character_ref", "states", "initial_state"],
  "properties": {
    "schema_version": { "const": "0.4.0" },
    "character_ref": { "type": "string", "pattern": "^char_[a-z0-9_]{1,64}$" },
    "initial_state": { "type": "string" },
    "states": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["narration_variants", "transitions"],
        "properties": {
          "narration_variants": { "type": "array", "items": { "type": "string" } },
          "transitions": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["event", "target_state"],
              "properties": {
                "event": { "type": "string" },
                "condition": { "$ref": "state_condition.schema.json" },
                "target_state": { "type": "string" },
                "effects": { "type": "array", "items": { "$ref": "state_effect.schema.json" } }
              }
            }
          }
        }
      }
    }
  },
  "additionalProperties": false
}
```

**工程复杂度**：
- schema 字段数：**1 新文件 ~80 行 JSON Schema**（npc_state_machine.schema.json）
- engine 改动：~50-80 行（运行时状态机执行器；查表 + 应用 effect + 切换 state；不调 LLM）
- generator 改动：~150-250 行（prompt 模板按 NPC 状态机生成各 state 的 narration_variants + transitions）
- validator 改动：~100-150 行（状态机闭合性 / 不可达 state / 死锁 / 与 dialogue_graph 引用一致性）

**与现有 ADR 一致性**：
- ✓ 兼容 ADR-002/004（运行时状态机查表，不调 LLM；ADR-008 state effect 同款执行）
- ✓ 兼容 ADR-027（状态机定义中性；不绑定世界观）
- ✓ 兼容 ADR-029（npc.alertness 等 state 由项目配置层定义；引擎不预设状态枚举）
- ⚠️ 与 ADR-019 character.dramatic_triggers 部分重叠——需要明确：dramatic_triggers = 触发器（一次性事件按优先级排序）；NPC 状态机 = 持续状态（多 event 路由 + 持久 state）。两者协同（详 §1.7 后果）

**风险**：
- **作者审阅负担 +30-50%**：每个 NPC 多写一份状态机定义；如 baseline_011 N=15 场景每场景 5 个 NPC，则需审阅 75 份 NPC 状态机
- **状态空间爆炸**：N 个 NPC × M 个 state × K 个 event ≈ 中等规模就 100-500 个 transition cell；如何 prompt AI 不写垃圾 transition 是新难题
- **与 dramatic_triggers 协同语义需明示**——否则会出现"AI 既在 dramatic_triggers 又在状态机里定义同一行为"的冗余

**优点**：
- F2 NPC 反应表达力强；作者审阅时可看 NPC 行为全貌（不是散落在 N 个 dialogue node 里）
- 状态机与 dialogue_graph 解耦——多场景复用同一 NPC 状态机（如 Vellin 跨 3 个章节都是同一状态机；审阅一次终身受益）
- 为未来 GOAP NPC 行为层（DEBATE §6.2 提到）留扩展空间

#### 1.3.C 候选方案 C：场景模板 + 元参数化（化模组结构为参数）

**核心抽象**：把整个 CoC 模组结构（NPC 卡片 + 钩子 + 守秘人笔记 + 倒计时 + 多嫌疑人 + 多结局）作为**模板**（schema 定义）；模组改编 = 填模板；原创 = 选模板再填。

| 7 种形式 | C 覆盖方式 | 是否原生支持 |
|---|---|---|
| F1 真凶选择 | 模板字段 `culprit_pool: [character_ref]` + `culprit_selection_strategy: "preset" \| "dynamic" \| "random"` | ✓ |
| F2 NPC 反应 | 模板字段 `npc_briefs[]`（每 NPC 含 `roleplay_hook` / `keeper_notes` / `if_culprit_branch`）+ 节点级 narration 按 condition 路由 | ✓ 中等表达 |
| F3 威胁节奏 | 模板字段 `escalation_clock: clock_id` + `escalation_signs[]`（按 tick 触发的 narration 变体）| ✓ |
| F4 多解决路径 | 模板字段 `endings[]`（每 ending 含 `world_state_condition` + `narration_template`）| ✓ |
| F5 场景扩展 | 模板字段 `expansion_hooks[]`（允许作者追加 dialogue_graph 实例）| ✓ |
| F6 难度调整 | 模板字段 `difficulty_baseline: int` + 每 active_check 引用 baseline + offset | ✓ |
| F7 即兴 | 模板字段 `improvisation_pool[]`（预生成 N 个"红鲱鱼变种"备用入口）| ⚠️ 增缓解 |

**新增 schema 字段（草拟，不预定）**：

```json
// /schema/investigation_scenario_template.schema.json (首版 const "0.4.0")
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["template_id", "scenario_kind", "culprit_pool", "npc_briefs", "escalation_clock", "endings"],
  "properties": {
    "schema_version": { "const": "0.4.0" },
    "template_id": { "type": "string", "pattern": "^tmpl_[a-z0-9_]{1,64}$" },
    "scenario_kind": { "enum": ["investigation_multi_suspect", "investigation_single_track", "linear_drama"] },
    "culprit_pool": {
      "type": "array",
      "items": { "type": "string", "pattern": "^char_[a-z0-9_]{1,64}$" },
      "minItems": 1
    },
    "culprit_selection_strategy": { "enum": ["preset", "dynamic", "random"] },
    "npc_briefs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["character_ref", "roleplay_hook"],
        "properties": {
          "character_ref": { "type": "string" },
          "roleplay_hook": { "type": "string" },
          "keeper_notes": { "type": "string" },
          "if_culprit_branch": { "type": "string" }
        }
      }
    },
    "escalation_clock": { "type": "string", "pattern": "^clk_[a-z0-9_]{1,64}$" },
    "escalation_signs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["at_tick", "narration_template"],
        "properties": {
          "at_tick": { "type": "integer", "minimum": 1 },
          "narration_template": { "type": "string" }
        }
      }
    },
    "endings": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "object",
        "required": ["ending_id", "world_state_condition", "narration_template"],
        "properties": {
          "ending_id": { "type": "string" },
          "world_state_condition": { "$ref": "state_condition.schema.json" },
          "narration_template": { "type": "string" }
        }
      }
    },
    "expansion_hooks": { "type": "array", "items": { "type": "string" } },
    "difficulty_baseline": { "type": "integer", "minimum": 1, "maximum": 100 },
    "improvisation_pool": { "type": "array", "items": { "type": "string" } }
  },
  "additionalProperties": false
}
```

**工程复杂度**：
- schema 字段数：**1 新文件 ~120 行 JSON Schema**
- engine 改动：**0 行**（模板是生成期数据；运行时只播放 dialogue_graph）
- generator 改动：~200-300 行（模板 → dialogue_graph 的转换器；prompt 模板按模板字段生成场景）
- validator 改动：~100-150 行（模板字段闭合性 + 模板 → dialogue_graph 完整性校验）

**与现有 ADR 一致性**：
- ✓ 兼容 ADR-002/004（模板是生成期数据；运行时不感知模板）
- ⚠️ 与 ADR-027 World-Agnostic 张力——`scenario_kind` 枚举的 `investigation_multi_suspect` 看起来贴 CoC 体裁；建议加 `linear_drama` 等枚举确保通用性（草拟里已加）
- ✓ 兼容 ADR-029（模板字段中性；不绑定技能体系）

**风险**：
- **模板的"完整度陷阱"**：模板字段越多越精确，模组改编越方便；但原创就会被模板约束（作者要先选模板再创意；与"作者一句话"理想流程冲突）
- **模板 → dialogue_graph 转换器是新增工程模块**——可能很复杂；与现有 generator 流水线（skeleton-first）的耦合策略需 ADR 后续细化
- **scenario_kind 枚举可能爆炸**——CoC 调查 / 极乐迪斯科对话密集 / 战斗 / 解谜 / 社交博弈每个都要一类模板？维护负担会随体裁多样化线性增加

**优点**：
- 对 CoC 模组改编场景**最贴合**（直接把 Crimson Letters 这类模组转成模板实例）
- 模板 = 显式记录"叙事结构契约"——比 A/B 方案的隐式契约（散落在 dialogue_graph 节点里）更可审阅
- 为未来"作者拍照贴 PDF → AI 提取模板字段 → 转 dialogue_graph"工作流留接口

#### 1.3.D 候选方案 D：混合 A+B（**T-3X 推荐**）

**核心抽象**：

- **基础层 = A**（完全复用现有 schema；F1/F3/F4/F5/F6 用元参数 + 现有机制）
- **增强层 = B**（仅 F2 NPC 反应引入 NPC 状态机；其他不变）
- **F7 即兴 = 显式承认不可结构化 + multi-variant 预生成作弊**（A/B 同款）

| 7 种形式 | D 覆盖方式 | 来源 |
|---|---|---|
| F1 真凶选择 | state path `world.culprit_id` + option 路由 | A |
| F2 NPC 反应 | **NPC 状态机**（新增 schema）+ character.dramatic_triggers（保留 ADR-019）| B |
| F3 威胁节奏 | ADR-017 clock + tick_effects | A（现有）|
| F4 多解决路径 | dialogue_graph end nodes + state_paths_written | A（现有）|
| F5 场景扩展 | 多 dialogue_graph 拼接 + chapter.acts.included_scenes | A（现有）|
| F6 难度调整 | state path `world.difficulty` + active_check.dc + NPC 状态机的"警觉度" state | A+B |
| F7 即兴 | 不结构化；预生成 multi-variant（每场景 6-10 options 中 3-5 个非线性入口）| A/B 同款 |

**工程复杂度**：
- schema 字段数：**1 新文件 ~80 行**（npc_state_machine.schema.json）+ **0 个 dialogue_graph 字段修改**
- engine 改动：~50-80 行（NPC 状态机查表执行器）
- generator 改动：~150-200 行（NPC 状态机 prompt 模板 + skeleton 生成增强）
- validator 改动：~100-130 行（状态机闭合性 + 与 dialogue_graph 引用一致性）

**与现有 ADR 一致性**：
- ✓ 全部兼容（A 的完全兼容性 + B 的 ADR-019 dramatic_triggers 协同清晰：dramatic_triggers = 一次性触发器；NPC 状态机 = 持续状态）
- ✓ ADR-029 配置层影响范围内（npc.alertness 等 state 由项目配置层定义）

**与作者已知偏好对齐**：
- ✓ 与 AESTHETIC_PREFERENCES.md v0.1 §2.3 主做"NPC 互动"对齐——NPC 状态机正是 NPC 互动的核心抽象
- ✓ 与 v0.1 §5 "CoC 骨架可借鉴" + "GM 抉择空间 7 种形式" 对齐
- ✓ 与战略校准 v0.1 北极星（更快更好完成 A）对齐——A 复用现有 schema 让 F1/F3/F4/F5 立即可用；B 仅在 F2 投入新抽象（最高 leverage 点）

**风险**：
- 仍承担 B 的"作者审阅负担 +30-50%"——但仅限 NPC 状态机部分（不像纯 B 全 7 形式都用状态机）
- F7 即兴仍依赖核心赌注（同 A）

**优点**：
- **最佳工程/表达力平衡**：F1/F3/F4/F5/F6 用现有机制（零工程成本）；F2 用最少新抽象解决最难形式
- **可分批落地**：T-3X-1b 可拆 2 个 PR（PR1 = A 基础层 prompt 模板调整；PR2 = B NPC 状态机 schema + engine 执行器）
- **失败模式可控**：如 NPC 状态机最终证明过度工程化，可在阶段 4 撤回到纯 A 方案，不破 dialogue_graph 等核心 schema

### 1.4 推荐方案

**推荐：方案 D（混合 A+B）**

#### 1.4.1 评分维度（按 L2 提示词 §评审 6 维）

| 维度 | A | B | C | D |
|---|---|---|---|---|
| **决策完整性**（覆盖 7 形式中至少 6 种）| 6 ✓ | 7 ✓ | 7 ✓ | 7 ✓ |
| **与现有 ADR 一致性**（CLAUDE.md / ADR-002/004/006/027/028/029/030）| ✓ 完全 | ✓ 完全 | ⚠️ ADR-027 张力 | ✓ 完全 |
| **工程复杂度**（schema + engine + generator + validator）| ~80-150 行 | ~330-480 行 | ~300-430 行 | ~300-410 行 |
| **AI 可生成性**（合理 token / cost）| ✓ 高 | ⚠️ 中（状态机生成复杂）| ⚠️ 中（模板转换复杂）| ⚠️ 中（仅 F2 复杂）|
| **作者偏好对齐**（v0.1 + 战略校准 + ROADMAP）| ⚠️ F2 表达力弱 | ✓ 强表达 | ✓ CoC 体裁贴合 | ✓ 平衡 |
| **失败模式可控性**（赌注不成立时的回退路径）| ⚠️ 全押 A | ⚠️ B 撤回成本中 | ❌ C 撤回成本高（模板转换器已建）| ✓ 可分批撤回到纯 A |

#### 1.4.2 推荐 D 的核心理由

1. **最佳工程/表达力平衡** — A 的简单 + B 在 F2 的强表达；其他 5 形式零工程成本
2. **可分批落地** — T-3X-1b 可拆 2 个 PR；先 A 基础层（PR1）再 B 状态机（PR2）；每 PR 独立可验收
3. **失败模式可控** — 如 NPC 状态机最终过度工程化，可阶段 4 撤回纯 A，不破 dialogue_graph 核心 schema
4. **与作者偏好深度对齐** — v0.1 §2.3 主做 NPC 互动 + §5 GM 抉择空间核心问题 = NPC 状态机正是这两者的交集
5. **CoC 改编 + 原创双场景都适用** — A 部分覆盖原创流水线；B 部分覆盖模组改编时 NPC 反应矩阵的复杂表达

#### 1.4.3 推荐 D 的次要保留

- **C 模板方案的优点未完全吸收** — 模板的"显式叙事结构契约"可读性高，但代价是 scenario_kind 枚举爆炸 + 模板转换器复杂度。**折中**：D 的 generator prompt 模板可借鉴 C 的模板字段命名（如 `culprit_pool` / `escalation_signs` / `endings` 等措辞），但不立 schema 层模板对象。这样既得到 C 的可读性益处，又不付 C 的工程代价。
- **T-3X-1b 落地时如发现 F2 不足以撑住 NPC 反应表达力，可后续阶段 4 立 ADR-032 引入完整 C 模板方案** — 不在本 ADR 范围。

### 1.5 赌注承认 + 回退路径

#### 1.5.1 核心赌注（项目级；首次明文承认）

> **Forgewright 工具一期的核心赌注 = "AI 海量预生成 + 人工审阅 = 给玩家伪即兴体验"。**
>
> 如果这个赌注不成立（AI 无法预生成足够丰富的内容覆盖 GM 即兴空间），整个工具一期定位需要重新审视。

赌注的具体含义：

- GM 即兴 = 人类直觉随机抓取一切上下文产出新分支（如 Crimson Letters 试玩示例：霍布豪斯宅邸**临场变成**黑帮入场点；这是模组没写、玩家创造、GM 即兴接住）
- Forgewright 的应对：**预生成 multi-variant**（每场景 6-10 option 中 3-5 个为非线性入口；每个入口都有完整 dialogue_graph 子树）
- 赌注的具体押注点：玩家**主观体验上**感觉"哇这个游戏怎么什么都能做"——但实际上玩家选项有限，只是丰富度足够掩盖"非真即兴"

#### 1.5.2 如赌注不成立的回退路径（4 档）

| 失败模式 | 回退路径 | 工程代价 | 影响 |
|---|---|---|---|
| **轻度**：AI 预生成 multi-variant 数量不足 | 加强作者人工编写关键路径变种（每场景手写 1-2 个 multi-variant 兜底）| 低（不改架构）| ROADMAP 阶段 4 内容估算 +20-40% 作者时间 |
| **中度**：AI 预生成质量参差（部分 variant 玩家明显感觉假）| 引入"AI 生成 + 作者 ABC 重审"质量门槛（每场景 60-80% 自动接受率作 baseline；不达标重生成）| 中（generator 加 reject-regenerate 循环）| 阶段 3 实测 throughput 降 30-50%；MVP 场景数从 100 退到 30-50 |
| **重度**：玩家明显感觉"选项有限"破坏伪即兴体验 | **scope 砍**——主线场景数大幅缩减（10 场景精品代替 100 场景宽广）；剩余靠"重玩价值"+ "高分支密度"补偿 | 高（重新定义 MVP scope）| ROADMAP 阶段 4 重写；估时 +6-12 月 |
| **致命**：预生成 + 选项式范式根本无法覆盖叙事 RPG 的多样性需求 | **架构重审** — 考虑回到 DEBATE §1 排除的"运行时 LLM"方向（但需重新评估 ADR-002 + 玩家欺诈防御等）；或彻底改 scope 到非叙事 RPG（如纯解谜 / 卡牌 / 战棋）| 极高（项目重定位）| 工具一期不成立；项目层面战略转向 |

#### 1.5.3 实测验证赌注的时机

- **阶段 3 T-3.10 实测期**（1 周 ≥ 10 场景）= 赌注的**第一次实证机会**
- **T-3.10 [A]ccept rate ≥ 60% + Wilson 95% CI**（STAGE_3_TASKS v1.0.1 §1）= 轻度失败模式的早期信号
- **阶段 4 MVP 内容期**（50-100 场景）= 中度/重度失败模式的实证窗口
- **阶段 4 itch.io 免费发布 + 3-5 朋友玩通**（战略校准 v0.1 完成定义档 c/d）= 致命失败模式的最终验证

#### 1.5.4 建议进 DEBATE_NOTES.md（明示）

本赌注是 T-3X-0 阅读伴侣会话**发掘出的项目最深层赌注**。AESTHETIC_PREFERENCES.md v0.1 §5.4 已建议进 DEBATE_NOTES。本 ADR 重申建议：

- 作者明示授权后由 L1 续接执行会话立 DEBATE §10（或同类编号）"核心赌注：AI 海量预生成 = 伪即兴" 段
- DEBATE_NOTES 应记录：赌注内容 / 触发会话（T-3X-0）/ 验证时机 / 回退路径 4 档
- 这不在本 ADR 范围；需作者另起 L1 修订会话

### 1.6 替代方案及否决理由

#### 1.6.1 否决纯 A 的理由

- F2 NPC 反应表达力弱 — CoC 模组"NPC 多层伪装"在节点级 narration 路由层笨重；作者审阅难以追溯
- 全押 F7 核心赌注上 — 失败模式可控性差（一旦赌注不成立无中间方案）

#### 1.6.2 否决纯 B 的理由

- 7 形式都用状态机过度工程化 — F3/F4/F5 现有机制（clock / end nodes / chapter.acts）已足够
- 作者审阅负担 +50% 而非 +30%；状态空间爆炸风险大

#### 1.6.3 否决纯 C 的理由

- 模板"完整度陷阱" — 原创流水线被模板约束（与"作者一句话"理想流程冲突）
- scenario_kind 枚举爆炸风险 — 维护负担线性增加
- 模板 → dialogue_graph 转换器是新增大模块 — 工程代价高且与现有 generator 耦合策略不清晰
- 与 ADR-027 World-Agnostic 张力（虽可通过中性命名缓解，但 schema 层叙事结构"模板化"本身就增了 vendor lock-in 风险）

#### 1.6.4 否决"完全不立 ADR"的理由

- T-3X-0 阅读伴侣会话已明示 "GM 抉择空间结构化是 T-3X-1 真正阻塞点"——不立 ADR 等于把工程债推到 T-3X-1 工程会话现场拍板（违反 CLAUDE.md 规则 8 "不要越俎代庖做规划"）
- ADR-030 字段集预留（无机制）+ 无 ADR-031（无契约）= T-3X-1 工程会话无锚点；高风险

#### 1.6.5 否决"整合进 ADR-030 v0.2 修订"的理由（详 §0.2）

- 范围不重叠；ADR-030 是字段集；本 ADR 是机制契约
- 决策颗粒度独立；架构层级不同
- 项目级赌注应有独立 ADR 承载

### 1.7 后果（对其他模块的影响）

#### 1.7.1 schema 模块影响

- **新增 1 个 schema 文件**：`/schema/npc_state_machine.schema.json`（首版 const `0.4.0`；与 ADR-030 schema 同 epoch；草拟见 §1.3.B）
- **不改任何既有 schema**（dialogue_graph / node / option / state_effect / state_condition / character / location / clock / chapter / image_asset / content_dependency_index 全部不动）
- **dialogue_graph 不嵌入 npc_state_machine**（独立 schema；通过 character_ref 关联）—— 沿用阶段 3 ADR-023 dep_index sidecar 的"独立文件 + 引用关联"哲学

#### 1.7.2 engine 模块影响

- **新增 ~50-80 行**：运行时 NPC 状态机查表执行器（state × event → next_state + response 路由）
- **不调 LLM**（与现 ADR-008 state effect 同款执行模型）
- DEBATE §5 极简运行时"500 行"上限保留（当前约 200-300 行；NPC 状态机后约 250-380 行；充裕）

#### 1.7.3 generator 模块影响

- **新增 ~150-200 行**：
  - prompt 模板新增"NPC 状态机生成段"（按 character.dramatic_triggers + character_features 生成 states + transitions）
  - skeleton-first 策略（ADR-026 + T-3.5 阶段 3）增强：先生成 dialogue_graph skeleton，再为涉及的每个 NPC 生成 / 复用其状态机
  - generation_trace 新增 npc_state_machine_refs 字段（追溯生成期使用了哪些 NPC 状态机）

#### 1.7.4 validator 模块影响

- **新增 ~100-130 行**：
  - schema 层校验：npc_state_machine schema 闭合性（unique state_id / target_state 闭合 / transition.event 命名规范）
  - 拓扑层校验：状态机不可达 state 检测 / 死锁检测（无出 transition 的非终止 state 拒收）
  - 一致性层校验：状态机引用的 character_ref 在本体可解析 / dialogue_graph 节点引用的 NPC 状态机存在 / 跨多 dialogue_graph 同一 NPC 状态机一致性

#### 1.7.5 content_dependency_index sidecar 影响（ADR-023）

- **可能新增 1 个 optional 字段**：`npc_state_machine_ids_referenced: array of string`（content_dependency_index.schema.json 同步 minor bump）—— 用于 T-3.7 dep_propagate 反向 propagate（NPC 状态机改动时 mark 引用 scene stale）
- 本字段是 missing-only optional；不破现有 sidecar
- **由 T-3X-1b 工程会话拍板是否落地**——非阻塞 ADR-031

#### 1.7.6 ADR-019 character.dramatic_triggers 协同语义（明示）

- ADR-019 dramatic_triggers = **触发器**（一次性事件按优先级排序；常态写作期 prompt 提示）
- 本 ADR-031 NPC 状态机 = **持续状态**（多 event 路由 + 持久 state；运行时执行）
- **协同关系**：
  - dramatic_triggers 触发后**可写入 NPC 状态机的 event 队列**（如"被质问过去" trigger 触发后写入 vellin.event 为 "queried_about_past" → NPC 状态机据此 transition 到 "defensive" state）
  - dramatic_triggers 不替代状态机（前者是事件发生器；后者是状态持久化器）
- 这种协同是**生产期 prompt 模板的约定**，不在 schema 层强约——与 ADR-008 + ADR-006 "LLM 不能直接写状态"哲学同源

#### 1.7.7 与 STAGE_3_TASKS.md v1.0.1 的影响

- **T-3X-1 拆分判断**（详 §2）：T-3X 推荐 B（拆 T-3X-1a + T-3X-1b）→ STAGE_3_TASKS §7 / §6 wave 图同步更新
- **R3.X follow-up 候选**：如 T-3X-1b 实测发现 NPC 状态机生成质量不达标，进 R3.4+ 链路
- **T-3.10 实测期影响**：T-3.10 启动前置追加 "T-3X-1a + T-3X-1b 全部 merge"（取代原 "T-3X-1 merge"）

#### 1.7.8 与 ROADMAP §阶段 3 + §阶段 4 的影响

- **阶段 3 时长**：T-3X-1b 引入新 schema + engine + generator + validator 改动；估时 +1-2 周（ROADMAP §阶段 3 表"5-9 周"可能要补充为 "6-11 周"；由 L1 fixation 拍板）
- **阶段 4 内容期**：核心赌注实证窗口；如赌注重度失败，scope 砍到 30-50 场景（详 §1.5.2 回退路径中度模式）

#### 1.7.9 与 DEBATE_NOTES.md 的影响

- 建议进 DEBATE §10（或同类编号）"核心赌注：AI 海量预生成 = 伪即兴"段（详 §1.5.4）
- DEBATE §2 plot-centric 骨架 + character-centric 肌肉哲学得到具体抽象支持（NPC 状态机 = character-centric 肌肉的工程实现）

### 1.8 未解项（本 ADR 不解决，留给后续）

#### 1.8.1 留给 T-3X-1b L3 工程会话

- **npc_state_machine schema 字段集**（具体字段命名 / minLength / pattern / additionalProperties 行为）：由 T-3X-1b 实证落地；本 ADR 仅给草拟（§1.3.B 的 npc_state_machine.schema.json 草稿）
- **NPC 状态机生成 prompt 模板**：按本 ADR §1.7.3 generator 影响段实测起草
- **NPC 状态机 vs dramatic_triggers 协同的具体 prompt 措辞**：T-3X-1b prompt 模板里明示二者职责区分（详 §1.7.6 协同语义）

#### 1.8.2 留给阶段 3 后续 R3.X follow-up

- **NPC 状态机生成质量阈值**：T-3.10 实测期定阈值（如"NPC 状态机 ≥ 80% 节点 transition 通过作者审阅"）；不达标进 R3.X 修复链路
- **NPC 状态机审阅 UI**（T-3.6a/b 已落地的 review_ui 是否需扩展）：T-3.10 实测期评估；如审阅效率不足由 R3.X follow-up 扩

#### 1.8.3 留给阶段 4

- **F7 即兴的进一步缓解策略**（如基于玩家选择历史的动态变种生成）—— 当前赌注靠预生成 multi-variant 覆盖；如不足由阶段 4 实测后立 ADR-032
- **完整 C 模板方案**（如 D 在 F2 不足以撑住 NPC 反应表达力时）—— 阶段 4 立 ADR-033 引入
- **GOAP NPC 行为层**（DEBATE §6.2 提到）—— 与 NPC 状态机有重叠；阶段 4 评估是否合并

#### 1.8.4 留给作者另起 L1 修订会话

- **DEBATE_NOTES.md §10 核心赌注段**（详 §1.5.4）—— 不在本 ADR 范围；作者明示授权后另起 L1 修订会话立
- **ROADMAP §阶段 3 时长更新**（5-9 周 → 6-11 周；详 §1.7.8）—— 由 PR-D 后续 L1 fixation 同步
- **STAGE_3_TASKS.md v1.0.2 修订**（T-3X-1 拆分形态落地；详 §2）—— 由本 ADR 签字后 L1 fixation 执行会话同步

### 1.9 关联讨论

#### 1.9.1 与已立 ADR 的关系陈述

| ADR | 关系 |
|---|---|
| **ADR-001** 玩家交互预生成选项式 | ✓ 强化（本 ADR 的 F7 即兴正是预生成 multi-variant 的实证）|
| **ADR-002** 运行时不调用 LLM | ✓ 严守（NPC 状态机运行时查表，不调 LLM）|
| **ADR-003** 数据格式 JSON-native | ✓ 严守（新增 schema 用 JSON Schema 定义）|
| **ADR-004** 运行时与生产期分离 | ✓ 严守（NPC 状态机数据生产期生成；运行时执行）|
| **ADR-005** 编剧理论作为可替换插件 | ✓ 兼容（本 ADR 是叙事**结构**契约，不是叙事**理论**；与 Save the Cat 等理论插件正交）|
| **ADR-006** 世界本体是真相之源 | ✓ 严守（NPC 状态机 state 持久化到 state path；与 ADR-008 同款写入路径）|
| **ADR-008** LLM 不能直接修改状态 | ✓ 严守（NPC 状态机 transition 通过 state effect 改 state path；不直接写）|
| **ADR-009** 评测分三层 | ✓ 增强（NPC 状态机为第三层 playtest bots 提供新评测维度——bot 经历不同 state path 触发的 NPC 反应矩阵）|
| **ADR-010** v0.2 MVP 场景数量弹性 10-100 | ✓ 兼容（如赌注重度失败可砍到 30-50；轻度失败可保持 50-100）|
| **ADR-016** 五命名空间 state path | ✓ 严守（NPC 状态机 state 落入 character / relationship 命名空间）|
| **ADR-017** 时钟系统 | ✓ 复用（F3 威胁节奏直接用现有 clock + tick_effects）|
| **ADR-018** 关系层 narrative_weight | ✓ 协同（character.relations 与 NPC 状态机正交；前者跨场景，后者场景内）|
| **ADR-019** 角色槽位持久化 + dramatic_triggers | ✓ 协同（详 §1.7.6 协同语义）|
| **ADR-020** v0.2 baseline 协议阶段 2/3/4 三阶段 | ✓ 兼容（NPC 状态机 [A]ccept rate gate 复用 ADR-020 阶段 3 期间口径）|
| **ADR-021** 第二层方法论 2A 拓扑 + 2B 抽样 | ✓ 增强（NPC 状态机闭合性 / 不可达 state / 死锁 = 拓扑层新增校验维度）|
| **ADR-022** playtest bots 完成标志 | ✓ 协同（5 persona × 20 paths 实测可包含 NPC 状态机 transition 覆盖率）|
| **ADR-023** content_dependency_index sidecar | ✓ 可能扩展（详 §1.7.5 sidecar 影响）|
| **ADR-024** 长对话一致性 C 起步 + A/B hook | ✓ 不冲突（NPC 状态机 state 持久化天然有助于跨场景一致性；但不替代长对话上下文管理）|
| **ADR-025** 审阅 UI 架构 | ✓ 可能扩展（T-3.6a/b 已落地；NPC 状态机视图由后续 R3.X 评估是否新增）|
| **ADR-026** 批量调度器并发模型 | ✓ 兼容（NPC 状态机生成与 dialogue_graph 生成同款 generate_scene hook）|
| **ADR-027** World-Agnostic Principle | ✓ 严守（npc_state_machine schema 字段命名中性；不绑定世界观）|
| **ADR-028** 引擎与宿主分离 | ✓ 严守（本 ADR 不引入宿主层字段；NPC 状态机 → 输出结构化叙事块）|
| **ADR-029** 技能体系作为项目配置层 | ✓ 严守（F6 难度调整复用 active_check + passive_injection；不预设技能）|
| **ADR-030** AestheticPreference schema 字段集预留 | ✓ 正交（ADR-030 = 质感词汇库；本 ADR = 结构契约）|

#### 1.9.2 与 DEBATE_NOTES 的关系

- DEBATE §1 玩家交互预生成选项式 — 本 ADR 是该原则在 GM 抉择空间维度的工程落地
- DEBATE §2 plot-centric + character-centric 共存 — NPC 状态机正是 character-centric 肌肉的工程实现
- DEBATE §5 极简运行时 — 本 ADR 严守 500 行上限（NPC 状态机查表 ~50-80 行）
- DEBATE §6.1 PbtA 阵营时钟 — F3 威胁节奏直接用 clock
- DEBATE §6.4 Drama Manager — F1 真凶选择 + F6 难度调整等元参数可作 Drama Manager 的输入
- DEBATE §6.5 关系图谱 — NPC 状态机的 state 持久化到 character.relations 命名空间
- DEBATE §9.1 "谁来写那张图" — 本 ADR 的 F1-F7 抽象层是回答"AI 生成时按什么结构生成"的核心；解决"AI 生成几千节点无法保证没有逻辑死锁"的部分

#### 1.9.3 与战略校准 v0.1 北极星指标的关系

- **北极星 = A 完成度**（作者本人 RPG 作品完成）
- 本 ADR 的工具改进合法性自检：
  - **问句**：本 ADR 落地会让 A 完成时间缩短吗？
  - **答案**：会（F1-F5 用现有机制让 A 立即可写；F2 NPC 状态机虽增审阅负担，但避免了未来"散落 NPC 反应难以维护"的债务爆炸）
- **失败模式警示**（战略校准 v0.1 末段）：本 ADR 不是"工具滑回继续做工具"——是为 A 完成铺路的必要抽象

---

## 2. T-3X-1 拆分判断

### 2.1 三个方案对比

#### 2.1.A 方案 A：合并为单一 L3 任务（T-3X-1）

- T-3X-1 同时落 ADR-030 字段集（审美词汇库）+ ADR-031 机制（GM 抉择空间结构化）
- **优点**：单 PR 闭环
- **缺点**：
  - 工作量爆炸（schema 字段集归纳 + schema 新文件 + engine 状态机执行器 + generator 大改 + validator 大改）
  - 风险耦合（一个失败拖另一个）
  - B 阶段 Codex review 焦点稀释

#### 2.1.B 方案 B：拆分为两个 L3 任务（T-3X-1a + T-3X-1b）

- **T-3X-1a**：ADR-030 字段集实证归纳 + AestheticPreference schema 落地 + prompt hook（审美词汇库）
- **T-3X-1b**：ADR-031 NPC 状态机 schema + engine 执行器 + generator 增强 + validator 扩展（GM 抉择空间机制）
- **优点**：
  - 边界清晰（前者纯字段集；后者纯机制）
  - 可并行（无强依赖；T-3X-1a 改 generator 的 prompt 注入段，T-3X-1b 改 generator 的 skeleton 生成段，仅 generator 文件 merge 风险，可协调）
  - 风险解耦（任一失败不拖另一）
  - 与现有 PR-A/B/C/D 拆 ABC 流程同款体例
- **缺点**：
  - 需协调 generator 文件 merge（中等复杂度）
  - L2 验收两次（作者审阅带宽 +1 次）

#### 2.1.C 方案 C：T-3X-1 仍按原 ADR-030 范围；ADR-031 落地推到 T-3X-2

- T-3X-1 = 纯 ADR-030 字段集（原 v0.2 决策档计划）
- T-3X-2 = 新任务编号；ADR-031 NPC 状态机
- **优点**：
  - T-3X-1 完全按原计划执行（不偏离决策档 v0.2 §6.4）
  - ADR-031 工作量延后到 T-3.10 实测期之后（如 T-3.10 发现赌注问题再立 ADR-031 更准）
- **缺点**：
  - **T-3.10 实测期会缺 NPC 状态机机制**——审美层 [A]ccept rate 评估时 NPC 反应表达力弱（F2）会影响测准；可能误判赌注（实际是 F2 表达力问题被误归结为 AI 生成质量问题）
  - ADR-031 推迟意味着 dialogue_graph 内"散落 NPC 反应"作为基线 — T-3.10 实测期 50 场景累积后再补 NPC 状态机会有大量重构债务
  - 与决策档 v0.2 §6.2 推荐"T-3X-1 编号紧密绑定 ADR-030 落地"的字面措辞冲突（虽然可以由作者明示授权扩展）

### 2.2 T-3X 推荐：方案 B（拆 T-3X-1a + T-3X-1b）

**理由**：

1. **边界清晰 + 风险解耦** — 两 ADR 的字段类型完全不同（前者数据字典；后者执行抽象），物理分开更稳
2. **可并行** — T-3X-1a 实证归纳期间（基于偏好档 v0.1），T-3X-1b 可同步起草 NPC 状态机 schema + engine 执行器；两 PR 各自开 ABC 闭环
3. **T-3.10 实测期前置完整** — T-3X-1a + T-3X-1b 都 merge 后 T-3.10 起步；审美层 [A]ccept rate 评估时 NPC 反应表达力已有 F2 抽象支撑
4. **与现有 ABC 流程体例同款** — 与 PR-A/B/C/D 拆法 + 跳 BC 破例 5 类清单（STAGE_3_TASKS §1.5.4）一致
5. **作者审阅带宽 +1 次可控** — T-3X-1a 修订量预期小（只新增 schema 字段 + prompt 注入段）；T-3X-1b 修订量大（schema + engine + generator + validator）；两 PR 时间分散对作者更友好

**推荐执行顺序**：

```
T-3X-1a（ADR-030 字段集） → 完成 → 启动 T-3X-1b
                                    ↓
                            （可与 T-3X-1a B/C 阶段并行准备）
                                    ↓
T-3X-1b（ADR-031 机制） → 完成 → T-3.10 启动
```

T-3X-1a 是 T-3X-1b 的软依赖（T-3X-1b prompt 模板可引用 ADR-030 schema 字段命名以避免重复定义）；但 T-3X-1b 不强阻塞于 T-3X-1a 完成（可并行起步）。

**STAGE_3_TASKS.md v1.0.2 修订点**（由 L1 fixation 执行会话同步；不在本 ADR 范围）：

- §7 任务清单 T-3X-1 行拆为 T-3X-1a + T-3X-1b 两行
- §6 wave 图 Wave 6.5 拆为 Wave 6.5a（T-3X-1a）+ Wave 6.5b（T-3X-1b）
- §1 完成标志表"审美层 review 激活前置"行更新依赖（T-3X-1 → T-3X-1a + T-3X-1b）
- §10 修订记录追加 v1.0.2 条目

---

## 3. T-3X-1 L3 paste-ready prompt（按推荐 B 方案输出）

### 3.1 T-3X-1a paste-ready prompt

```text
你是 Forgewright 项目 L3 工程会话——T-3X-1a（ADR-030 AestheticPreference schema 字段集实证归纳 + prompt hook）。

# 你的任务（一句话）

基于 T-3X-0 产出的 /docs/AESTHETIC_PREFERENCES.md v0.1，**实证归纳**审美偏好维度字段集 → 落 /schema/aesthetic_preference.schema.json 首版 const "0.4.0" → 在 generator prompt 模板中加 aesthetic_preference_context 注入段。**不**预定字段；字段集来自偏好档 v0.1 + 你与作者的迭代调整。

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。第一款游戏 = "克苏鲁版极乐迪斯科 spiritual successor"。当前 main HEAD 含 ADR-001~031（ADR-030 字段集留空预留；ADR-031 GM 抉择空间结构化由 T-3X-1b 落地）。T-3X-0 阅读伴侣会话 2026-05-13 产出偏好档 v0.1（单样本基线 + 大量 TBD）。

# 前置依赖

- **ADR-030 已立**（PR #51 merged 2026-05-12；字段集留空预留）
- **ADR-031 已立**（PR-? merged YYYY-MM-DD；GM 抉择空间结构化；本 PR 与之协同但不依赖其完成）
- **T-3X-0 已收尾**（PR #55 merged 2026-05-12；偏好档 v0.1）
- **本 PR 与 T-3X-1b 软依赖**（T-3X-1b 可并行；详 ADR-031 §2.2）

# 必读（按顺序）

1. /CLAUDE.md — 项目硬规则 10 条
2. /docs/AESTHETIC_PREFERENCES.md v0.1 — **本任务字段集源**（特别 §2 硬约束 + §3 四维偏好基线 + §5 元结构判断 + §6 TBD 清单）
3. /docs/reviews/aesthetic/T-3X-0_crimson_letters_reading.md — 反向归纳起点
4. /docs/DECISIONS.md ADR-030 + ADR-031（本任务参考）
5. /docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md（L2 综合规划师产出；本 prompt 即来自 §3.1）
6. /docs/SCHEMA_v0.3.md §1-§5 — schema 体例参考
7. /docs/STAGE_3_TASKS.md v1.0.1 §1.5 ABC 流程 + §8 任务 prompt 体例
8. /docs/reviews/master_plan/2026-05-01_review_routine_governance.md v0.4.1 §10 ABC 流程
9. /generator/scene_strategies.py + /generator/prompts/scene/ — prompt 模板现状

# 模块边界（硬性）

允许修改：
- /schema/aesthetic_preference.schema.json（**新建**；首版 const "0.4.0"）
- /schema/tests/test_aesthetic_preference_schema.py（**新建**；schema 闭合性测试）
- /generator/scene_strategies.py（aesthetic_preference_context 注入段）
- /generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md 或同款（aesthetic_preference_context 在判官 prompt 中的角色）
- /generator/tests/（注入段 unit test）
- /docs/AESTHETIC_PREFERENCES.md（**仅追加** v0.2 字段集归纳段；不重写 v0.1）

**严禁修改**：
- CLAUDE.md / DEBATE_NOTES.md
- DECISIONS.md（ADR-030 已立；本 PR 不修订 ADR）
- ROADMAP.md / STAGE_3_TASKS.md / HANDOFF_STAGE_2_TO_3.md（L1 文档）
- 其他 /schema/*.json 既有文件（dialogue_graph / character / location / clock / chapter / content_dependency_index 等）
- /engine/* / /state/* / /validator/* （非生产期模块）
- /docs/prompts/stage_3/T-3.X.md 其他文件（除本 T-3X-1a.md 外）

# 待落地点

## 落地点 1：实证归纳字段集 → 追加 AESTHETIC_PREFERENCES.md v0.2 段

读 v0.1 §3 四维偏好 + §5 元结构判断 + §6 TBD 清单；基于已知信息提出字段集 v0.2 草案（**与作者迭代**——你提议；作者 +/- 字段；不要替作者拍板）：

候选起点字段（**T-3X-0 归纳产出可推翻；不预定**）：
- `temperature`（暗黑 / 明朗 / 灰色 / 戏谑 各 0-10）
- `pacing`（节拍体系枚举 + 密度 0-10）
- `character_arc`（弧光类型 + 强度）
- `value_judgment`（价值立场 + 道德灰度）
- `reference_works`（引用经典作品 + 吸收要点）
- `enabled`（boolean；项目是否启用该偏好档）
- `schema_version`（const "0.4.0"）

迭代落地到 AESTHETIC_PREFERENCES.md 新增 §10 "v0.2 字段集归纳"段（不重写 v0.1）。

## 落地点 2：落 /schema/aesthetic_preference.schema.json

按 §10 字段集落 JSON Schema（首版 const "0.4.0"；与 ADR-030 schema 文件路径一致）；遵守 schema 体例：

- `$schema`: "http://json-schema.org/draft-07/schema#"
- `$id`: 与其他 schema 同源
- `type`: "object"
- `required`: 必填字段列表
- `properties`: 各字段类型 + 约束（pattern / enum / minimum / maximum 等）
- `additionalProperties: false`（与现有 schema 体例一致）

## 落地点 3：generator prompt 模板注入 aesthetic_preference_context

修改 /generator/scene_strategies.py + /generator/prompts/scene/ 的相关 prompt 模板：

- skeleton-first 策略（ADR-026 + T-3.5 阶段 3）的 skeleton 生成 prompt 加 aesthetic_preference_context 段（注入偏好档关键字段）
- fill 生成 prompt 同样注入
- 节点级 prompt（如 NPC 对白生成）按需注入

具体注入字段子集由你拍板（可全注入或按场景类型筛选）。

## 落地点 4：schema 测试

落 /schema/tests/test_aesthetic_preference_schema.py：

- 测 schema 字段集闭合性
- 测必填字段缺失拒收
- 测枚举值 out-of-range 拒收
- 测 additionalProperties: false 强约

## 落地点 5：generator unit test

落 /generator/tests/ 新增 / 增量 unit test 验证 aesthetic_preference_context 注入正确（mock provider + assert prompt 含字段）

# ABC 闭环要求

**默认走完整 ABC**（[B-author-gate]；与 PR-A/C 同款）：

- **A 阶段（本会话）**：write + commit + push + 开 PR；commit 后等作者明示 B 阶段
- **B 阶段**：作者另起 Codex 会话；review prompt 复用 /docs/REVIEW_PROMPT_CODE_GPT.md v0.2；review 报告 push 到 main 独立 commit
- **C 阶段**：吃 B review 报告 → 追加 commit 到原 PR

# A 阶段执行步骤

1. 验证 ADR-030 + ADR-031 + T-3X-0 收尾 PR 都已 merge
2. 读必读清单（9 项）
3. 落地点 1：与作者迭代字段集 → 追加 AESTHETIC_PREFERENCES.md v0.2 段
4. 落地点 2：落 schema 文件
5. 落地点 3：generator prompt 模板修订
6. 落地点 4 + 5：schema 测试 + generator unit test
7. 跑 pytest / 跑 /review skill
8. commit + push + 开 PR（title + body 参 PR-A/B/C/D 模式）
   - title: `feat(generator): T-3X-1a — AestheticPreference schema 字段集实证归纳 + prompt hook (ADR-030 落地)`

# 完成判定

- AESTHETIC_PREFERENCES.md §10 v0.2 字段集归纳段已追加
- /schema/aesthetic_preference.schema.json 首版落地
- /schema/tests/ 新增测试通过
- /generator/scene_strategies.py + prompts/scene/ 注入段落地
- /generator/tests/ 新增测试通过
- PR open + commit + push 完成
- PR body 含 ABC 流程段
```

### 3.2 T-3X-1b paste-ready prompt

```text
你是 Forgewright 项目 L3 工程会话——T-3X-1b（ADR-031 GM 抉择空间结构化 NPC 状态机 schema + engine 执行器 + generator 增强 + validator 扩展）。

# 你的任务（一句话）

基于 ADR-031 §1.3.D 推荐方案（混合 A+B），落地 NPC 状态机抽象：新建 /schema/npc_state_machine.schema.json + /engine/npc_state_machine.py 查表执行器 + /generator/ NPC 状态机生成 prompt 模板 + /validator/ 状态机校验。**严格遵守 ADR-002 极简运行时**（运行时不调 LLM）+ **严守 ADR-019 协同语义**（dramatic_triggers 触发器 vs 状态机持续状态分工）。

# 项目背景（一句话）

Forgewright = AI 辅助分支叙事 RPG 内容生产流水线。第一款游戏 = "克苏鲁版极乐迪斯科 spiritual successor"。当前 main HEAD 含 ADR-001~031。T-3X-0 阅读伴侣会话 2026-05-13 识别"GM 抉择空间结构化是引擎抽象层核心问题"；本 ADR-031 推荐方案 D（混合 A+B），F1/F3/F4/F5 用现有机制（零工程成本），F2 用 NPC 状态机新抽象，F6 用现有 active_check + 状态机警觉度 state，F7 即兴显式不结构化（核心赌注）。

# 前置依赖

- **ADR-030 已立**（PR #51 merged 2026-05-12）
- **ADR-031 已立**（PR-? merged YYYY-MM-DD；GM 抉择空间结构化）
- **T-3X-0 已收尾**（PR #55 merged 2026-05-12；偏好档 v0.1）
- **本 PR 与 T-3X-1a 软依赖**（可并行；ADR-031 §2.2 推荐 T-3X-1a 先；本 PR 可借鉴 T-3X-1a 的字段命名）

# 必读（按顺序）

1. /CLAUDE.md — 项目硬规则 10 条
2. /docs/DECISIONS.md ADR-031（**本任务核心**）+ ADR-002 / ADR-004 / ADR-006 / ADR-008 / ADR-017 / ADR-018 / ADR-019 / ADR-021 / ADR-027 / ADR-028 / ADR-029 / ADR-030
3. /docs/DEBATE_NOTES.md §1 / §2 / §5 / §6.1 / §6.2 / §6.5 / §9.1
4. /docs/SCHEMA_v0.3.md §2-§5 + §8（schema 体例 + 五命名空间 + 留给 validator 的语义约束）
5. /docs/AESTHETIC_PREFERENCES.md v0.1 §5 元结构判断 + 对照表 §5 7 种形式
6. /docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md（L2 综合规划师产出；本 prompt 即来自 §3.2；特别 §1.3.D 推荐方案 + §1.7 后果 + §1.8.1 留给本任务的未解项）
7. /docs/SCENE_v0.md + /content/test_scene_v0/scene.json — 现有 dialogue_graph 实例参考
8. /generator/generate_scene.py + /generator/scene_strategies.py + /generator/prompts/scene/ — 现有 generator 流水线
9. /validator/*.py — 现有 validator 模块
10. /engine/*.py — 极简运行时（注意 ADR-004 + DEBATE §5 极简原则）
11. /docs/STAGE_3_TASKS.md v1.0.1 §1.5 ABC 流程 + §8 任务 prompt 体例
12. /docs/reviews/master_plan/2026-05-01_review_routine_governance.md v0.4.1 §10 ABC 流程

# 模块边界（硬性）

允许修改：
- /schema/npc_state_machine.schema.json（**新建**；首版 const "0.4.0"；体例参考 §SCHEMA_v0.3 character.schema.json）
- /schema/tests/test_npc_state_machine_schema.py（**新建**）
- /engine/npc_state_machine.py（**新建**；运行时查表执行器；预估 50-80 行；DEBATE §5 极简原则）
- /engine/tests/test_npc_state_machine.py（**新建**）
- /generator/scene_strategies.py（NPC 状态机生成段；与 T-3X-1a 的 aesthetic_preference_context 注入段共存；merge 协调）
- /generator/prompts/scene/（NPC 状态机生成 prompt 模板）
- /generator/generation_trace.py 或同款（**追加** npc_state_machine_refs 字段；不破现有 generation_trace 字段）
- /generator/tests/（新增 unit test）
- /validator/npc_state_machine_validator.py（**新建**；闭合性 + 不可达 state + 死锁检测）
- /validator/tests/（新增校验测试）
- /content/test_scene_v0/scene.json + 同目录新增示例 NPC 状态机 JSON（gold standard 实例参考；与现有 scene.json 联动；可选）

**严禁修改**：
- CLAUDE.md / DEBATE_NOTES.md / DECISIONS.md
- ROADMAP.md / STAGE_3_TASKS.md / HANDOFF_STAGE_2_TO_3.md（L1 文档）
- 其他 /schema/*.json 既有文件（dialogue_graph / character / location / clock / chapter / content_dependency_index / image_asset / aesthetic_preference 全部不动）
- /engine/dialogue_graph_player.py 或同款核心播放器（除非接入 NPC 状态机查表是必要的最小改动；如有 ≤ 20 行；明示是 hook 而非主逻辑）
- /state/* （状态总线核心不动；NPC 状态机 state 通过现有 state_effect 写入 character / relationship 命名空间）
- /docs/prompts/stage_3/T-3.X.md 其他文件（除本 T-3X-1b.md 外）
- 任何代码 / 测试 / fixture 在本 PR 范围外

# 待落地点

## 落地点 1：落 /schema/npc_state_machine.schema.json

按 ADR-031 §1.3.B 草拟落 JSON Schema：

- `character_ref` (string; pattern `^char_[a-z0-9_]{1,64}$`)
- `initial_state` (string)
- `states` (object; additionalProperties = state 定义对象)
  - 每 state: `narration_variants` (array) + `transitions` (array)
  - 每 transition: `event` + `condition`（$ref state_condition）+ `target_state` + `effects`（$ref state_effect）
- `additionalProperties: false`
- const "0.4.0"

## 落地点 2：落 /engine/npc_state_machine.py 查表执行器

预估 50-80 行（DEBATE §5 极简）：

- 输入：当前 NPC state + event + state bus snapshot
- 处理：查 transitions[] → 评估 condition（复用现有 state_condition 评估器）→ 选 target_state → 应用 effects（复用现有 state_effect 应用器）
- 输出：next_state + 触发的 narration_variant（按 condition 选）
- **不调 LLM**（ADR-002 严守）

## 落地点 3：落 /validator/npc_state_machine_validator.py

约 100-130 行：

- schema 闭合性（unique state_id / target_state 可解析 / event 命名规范）
- 拓扑层：不可达 state 检测（BFS from initial_state）+ 死锁检测（非终止 state 无出 transition 拒收）
- 一致性层：character_ref 在本体可解析 / dialogue_graph 节点引用的 NPC 状态机存在

## 落地点 4：generator NPC 状态机生成 prompt 模板

修改 /generator/scene_strategies.py + /generator/prompts/scene/：

- skeleton-first 策略增强：先生成 dialogue_graph skeleton，识别出场 NPC，然后为每个 NPC 生成 / 复用其状态机
- prompt 模板按 character.dramatic_triggers + character_features 生成 states + transitions
- 明示协同语义（参 ADR-031 §1.7.6）：
  - dramatic_triggers = **触发器**（一次性事件按优先级排序；触发后写入 NPC.event）
  - NPC 状态机 = **持续状态**（多 event 路由 + 持久 state；运行时执行）
- generation_trace 追加 npc_state_machine_refs 字段

## 落地点 5：content_dependency_index sidecar 可选扩展

视需要在 /schema/content_dependency_index.schema.json 追加 optional 字段 `npc_state_machine_ids_referenced`（missing-only）。

**判断**：如本 PR scope 已大，可推到 R3.X follow-up；不阻塞本 PR。

## 落地点 6：示例 NPC 状态机（可选 gold standard）

在 /content/test_scene_v0/ 或同款目录新增示例 NPC 状态机 JSON（如 vellin.state_machine.json），含 calm / suspicious / hostile 三 state + transitions。

**判断**：如本 PR scope 已大，gold standard 可推到下一个内容期；不阻塞本 PR。

## 落地点 7：测试

- /schema/tests/test_npc_state_machine_schema.py：schema 闭合性 / 必填缺失 / additionalProperties 强约 / 跨字段一致性
- /engine/tests/test_npc_state_machine.py：查表执行器单元测试 + 与现有 state_effect / state_condition 集成测试
- /validator/tests/test_npc_state_machine_validator.py：闭合性 / 不可达 / 死锁 / 一致性
- /generator/tests/：prompt 模板注入 / generation_trace 字段追加

# ABC 闭环要求

**默认走完整 ABC**（[B-author-gate]；与 PR-A/C 同款；本 PR 修订量大，强烈不建议跳 BC）：

- **A 阶段（本会话）**：write + commit + push + 开 PR；commit 后等作者明示 B 阶段
- **B 阶段**：作者另起 Codex 会话；review prompt 复用 /docs/REVIEW_PROMPT_CODE_GPT.md v0.2；review 重点 = schema 字段命名 + engine 极简性 + generator 协同语义清晰度 + validator 完整性
- **C 阶段**：吃 B review 报告 → 追加 commit 到原 PR

# A 阶段执行步骤

1. 验证 ADR-030 + ADR-031 + T-3X-0 收尾 PR 都已 merge；T-3X-1a 可未完成（本 PR 软依赖）
2. 读必读清单（12 项）
3. 落地点 1：落 /schema/npc_state_machine.schema.json
4. 落地点 2：落 /engine/npc_state_machine.py
5. 落地点 3：落 /validator/npc_state_machine_validator.py
6. 落地点 4：generator prompt 模板 + generation_trace
7. 落地点 5 + 6（可选；视 scope）
8. 落地点 7：所有测试落地
9. 跑 pytest / 跑 /review skill
10. commit + push + 开 PR（title + body 参 PR-A/B/C/D 模式）
    - title: `feat(engine + generator + validator + schema): T-3X-1b — NPC state machine 抽象 (ADR-031 落地)`

# 完成判定

- /schema/npc_state_machine.schema.json 首版落地 + 测试通过
- /engine/npc_state_machine.py 落地 + 测试通过（≤ 80 行；极简严守）
- /validator/npc_state_machine_validator.py 落地 + 测试通过
- /generator/ NPC 状态机生成 prompt 模板落地 + unit test 通过
- generation_trace 追加 npc_state_machine_refs 字段
- PR open + commit + push 完成
- PR body 含 ABC 流程段 + 严守 ADR-002/004 极简运行时声明 + 与 ADR-019 协同语义说明
```

---

## 4. 与 cross-LLM critique 的关系

### 4.1 是否建议走 critique

**建议：走 Codex GPT-5.5 critique**

### 4.2 理由

1. **方案多分支**：本草案含 4 候选方案（A / B / C / D）+ 推荐 D；候选间评分维度多（决策完整性 / ADR 一致性 / 工程复杂度 / AI 可生成性 / 作者偏好对齐 / 失败模式可控性）—— GPT-5.5 视角可能识别 L2 单方未抓到的取舍点（参 Round 5 跨 LLM 评审 ~50% 事项增益数据）
2. **决策影响范围广**：本 ADR 影响 schema + engine + generator + validator + ADR-019 协同 + ADR-023 sidecar + STAGE_3_TASKS + ROADMAP 时长 + DEBATE_NOTES 赌注段 — 范围越广越值得跨视角 critique
3. **字段定义争议大**：NPC 状态机 schema 字段集（草拟见 §1.3.B）是新抽象；GPT-5.5 可能从工程实现角度给字段命名 / additionalProperties / pattern 强度 / state event 命名规范等具体建议
4. **核心赌注承认是项目层议题**：赌注 + 4 档回退路径（详 §1.5.2）需要"不一样的视角"——L2 单方可能对失败模式过于乐观或过于悲观；GPT-5.5 critique 可校准

### 4.3 critique prompt 使用建议

- 复用 [/docs/REVIEW_PROMPT_L2_STAGE_TASKS.md](../../REVIEW_PROMPT_L2_STAGE_TASKS.md) 模板
- `{{REVIEW_TARGET}}` 填本草案路径 + §1-§3 全文
- critique 重点维度建议：
  - 候选方案完整性（4 个候选是否覆盖了主要架构空间？还有第 5 候选吗？）
  - 推荐 D 的评分维度是否合理？是否漏抓某些维度？
  - NPC 状态机 schema 字段集合理性（与 ADR-019 dramatic_triggers 协同的清晰度？state event 命名规范？）
  - 核心赌注承认是否充分？4 档回退路径是否真实可执行？
  - T-3X-1 拆分判断（B 推荐合理？还是 A 合并更稳？）
  - 与 ADR-002/004 极简运行时严守的严格度（engine 50-80 行是否真能实现？）

### 4.4 如不走 critique 的备选

如作者拍板**跳过 critique**（如时间紧 / 风险已知 / 信赖 L2 起草），可直接进 L1 fixation 执行会话立 ADR-031；但建议在 ADR 草案前言段加注"本 ADR 起草未走 cross-LLM critique；后续如 T-3.10 实测反馈不达预期，需另立 ADR v0.2 修订"。

---

## 5. 移交给作者签字的明示事项

按 DECISIONS.md §变更历史"作者明确授权"段落措辞习惯，本草案需作者明示授权以下事项：

### 5.1 立 ADR-031（GM 抉择空间结构化方案）

- 编号 = ADR-031（DECISIONS.md 当前最大 ADR-030 顺延）
- 决策核心 = §1.3.D 推荐方案（混合 A+B）
- 字段集草拟 = §1.3.B npc_state_machine.schema.json 草稿（实际字段集由 T-3X-1b 落地拍板）
- 赌注承认 + 4 档回退路径 = §1.5

### 5.2 T-3X-1 拆分判断 = §2.1.B 方案 B（推荐拆 T-3X-1a + T-3X-1b）

- T-3X-1a = ADR-030 字段集实证归纳
- T-3X-1b = ADR-031 NPC 状态机机制
- STAGE_3_TASKS.md v1.0.2 修订点 = §2.2 末段

### 5.3 cross-LLM critique 选择

- T-3X 推荐 = **走**（详 §4.1）
- 备选 = 跳过（详 §4.4）
- 由作者拍板

### 5.4 DEBATE_NOTES.md §10 核心赌注段是否同期立

- T-3X 建议 = **同期**（DEBATE_NOTES 是项目级架构记录；核心赌注是首次正式承认）
- 备选 = 推到 ADR-031 merge 后另起 L1 修订会话立
- 由作者拍板

### 5.5 ROADMAP §阶段 3 时长更新

- T-3X 建议 = 5-9 周 → **6-11 周**（含 T-3X-1b 引入新 schema + engine + generator + validator 改动；估时 +1-2 周）
- 备选 = 保持 5-9 周（如 T-3X-1b 仅修最小集；不强约时长）
- 由作者拍板

### 5.6 git commit + push 命令模板（作者复制运行；L2 不自动 commit）

```bash
# 在 worktree claude/jovial-elion-c8d60c 内
git add docs/reviews/master_plan/2026-05-13_gm_decision_space_ADR_draft.md
git commit -m "$(cat <<'EOF'
docs(reviews): L2 综合规划师产出 — GM 抉择空间结构化方案 ADR-031 草案 + T-3X-1 拆分判断 + T-3X-1a/T-3X-1b paste-ready prompts

承接 T-3X-0 阅读伴侣会话产出（PR #55 merged）+ L2 提示词（PR #55 内）+ T-3X L2 校准备忘 v0.2.3（PR #56 merged）。L2 综合规划师会话起草 ADR-031（GM 抉择空间结构化方案）草案：

- §0 前言（立 ADR 必要性判断）
- §1 ADR-031 草案（4 候选方案对比 + 推荐 D 混合 A+B + 赌注承认 + 4 档回退路径 + 与现有 ADR-001~030 关系陈述）
- §2 T-3X-1 拆分判断（推荐 B：拆 T-3X-1a + T-3X-1b）
- §3 T-3X-1a + T-3X-1b paste-ready prompts（按 STAGE_3_TASKS §8 体例 + ABC 闭环 + 模块边界 + 完成判定）
- §4 cross-LLM critique 建议（走 Codex GPT-5.5 critique）
- §5 移交给作者签字 6 项

待作者签字 → L1 fixation 执行会话落地 ADR-031 + STAGE_3_TASKS.md v1.0.2 + （可选）DEBATE_NOTES §10 核心赌注段 + （可选）ROADMAP §阶段 3 时长更新。

追溯：
- T-3X-0 收尾 PR #55
- T-3X 校准备忘 v0.2.3 PR #56
- L2 提示词 /docs/reviews/master_plan/2026-05-13_gm_decision_space_L2_prompt.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git push -u origin claude/jovial-elion-c8d60c
```

签字流程：

1. 作者拍板 §5.1-5.5 五项
2. 如签字通过 → L1 fixation 执行会话立 ADR-031（参 PR-A 模式）
3. 同期 / 后续 → 启动 T-3X-1a + T-3X-1b L3 工程会话（按拆分判断）
4. T-3X-1a + T-3X-1b 全部 merge → T-3.10 启动

---

## 6. 版本

本文件版本：v0.1
最后更新：2026-05-13
产出方：T-3X L2 综合规划师会话（claude/jovial-elion-c8d60c worktree）
基于：T-3X-0 收尾产出 3 文件 + L2 提示词 + 必读 13 项

### 修订记录

- **v0.1（2026-05-13）**：L2 综合规划师起草初版。4 候选方案对比 + 推荐 D 混合 A+B + 赌注承认 + 4 档回退路径 + T-3X-1 拆分判断 + T-3X-1a/T-3X-1b paste-ready prompts + cross-LLM critique 建议 + 移交给作者签字 6 项。
- **v0.1-postclarification（2026-05-13）**：L1 措辞清算执行会话（claude/bold-dubinsky-4b584a worktree）补丁——基于 PR #58 L1 fixation merged 后 blueprint-auditor 审计发现的 3 处 AI 修辞清算：「一句话」「伪即兴体验」「multi-variant / 海量预生成」。作者选项 A 拍板：删除赌注修辞，只留可测目标。措辞清算落地 L1 文档：
    - `/docs/DECISIONS.md` ADR-031 §背景"一句话"段重写 + §核心赌注段重写为"项目级可测目标" + §F7 覆盖矩阵行措辞替换为 STAGE_3_TASKS §1.7 量化矩阵引用 + 关联讨论 ADR-001 行措辞替换
    - `/docs/DEBATE_NOTES.md` §10 整段重写：标题 "核心赌注" → "项目级可测目标 + 风险回退路径"；6 子段全部清洗"伪即兴" / "multi-variant" / "海量预生成"措辞；4 档回退路径表格内容保留（替换 variant 等措辞为 diverge 选项 / 路线）
    - `/docs/STAGE_3_TASKS.md` 新增 §1.7「量化矩阵」段：7 量化轴拍板值 + 3 新术语定义（选项 diverge 度 / 路线分支密度 / 候选稿数）+ 总节点数估算 + 替代措辞声明
    - `/docs/AESTHETIC_PREFERENCES.md` §5.4 「核心赌注」改写为「项目级可测目标」+ §1 Crimson Letters 描述行 + §5.3 输入端表述行清洗
  - **本草案 body 段未动**（仅追加本修订记录条目）——ADR-031 草案 body 内 "伪即兴 / multi-variant" 等措辞作为 L2 起草史保留（历史留档；L1 已立 ADR-031 为准）。后续 L2/L3 引用 ADR-031 时以已 merged L1 文档为准。

