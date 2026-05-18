# T-3Y 节点级文本生成抽象 · 设计进展报告

> **来源**：2026-05-14 ~ 2026-05-15 T-3Y L2 综合规划师会话（claude/adoring-wilbur-42c816 worktree）
> **状态**：进展中（in progress）；本档为讨论快照（snapshot），便于下游会话（ADR-034 schema IR 调研 / ADR-035 L3 宿主调研 / 未来 T-3Y-1 工程会话）作为输入引用
> **覆盖**：T-3Y 模块定位 + 边界 + 6 阶段工作流 + 23 决策点 + 场景级字段草案 + 节点级字段草案 + Forward Planner 3 子模块 + 已拍板项 + 4 个待 ADR-034 后回头拍板的设计问题 + 跨 ADR 协同
> **不覆盖**：T-3Y 模块内的 ST-1 ~ ST-9 详细子任务讨论（多为文字风格相关，已外包到作者另起的"文字风格工作台"）

**日期**：2026-05-15 · **产出方**：T-3Y L2 综合规划师会话 + 作者 outsiderrr

---

## 1. T-3Y 模块定位 + 边界

### 1.1 模块定位（作者签字 2026-05-15）

**T-3Y = 单节点好文本生成的自包含模块**。核心目标 = 实现"输入 → 规则 → AI 创作 → 人工审 → 好的输出文本"完整流程，作为一个 self-contained（自包含）模块存在。

### 1.2 模块边界（哪些 fold 进 / 哪些保留独立）

**T-3Y 模块内（fold 进来）**：

| 来源 | 现状 | T-3Y 内归属 |
|---|---|---|
| ADR-030（AestheticPreference schema 字段集预留） | 已 accepted；字段集留空 | T-3Y 的"规则"段（输入契约的一部分） |
| T-3X-1a 工程任务（AestheticPreference schema + prompt hook） | 已立未启动 | 编号待定（合并 / 重命名 / 废弃）；内容 fold 进 T-3Y 工程子任务 |
| AESTHETIC_PREFERENCES.md v0.1 | 已落档 | T-3Y 模块输入档（不动文件本身） |
| A1 反馈 v0.1（10 条 anti-pattern + 3 分类角色守则）| 已落档 PR #?（2026-05-14） | T-3Y 模块输入档（不动文件本身） |
| **拟立 ADR-032**（节点级文本生成抽象总契约） | 待作者授权立项 | T-3Y 模块本体 ADR |

**T-3Y 模块外（保留独立；仅作 T-3Y 接口依赖）**：

| 对象 | 为什么不能 fold |
|---|---|
| T-3X-1b NPC 状态机（ADR-031 落地）| 结构层 / 引擎层（运行时查表，不调 LLM）；与"节点级文本生成"正交。T-3Y 调用它（拿当前 state 作输入），但不拥有它 |
| ADR-031 GM 抉择空间结构化方案 | 更高层架构决策（F1~F7 抉择形式如何结构化）；T-3Y 只是 F2/F7 落到节点级时的文本生成执行环节 |
| ADR-029 技能体系项目配置层 | 引擎核心机制 + 项目配置层；T-3Y 调用它（option text `[skill_name]` 标记的 enum 校验依赖 skills.json） |
| T-3.5 批量调度器 / T-3.6a/b 审阅 UI / T-3.0 ~ T-3.12 其他 | 调用方或基础设施；T-3Y 是被调用模块 |

### 1.3 T-3Y 模块的接口契约

- **输入接口**：聚合 `场景 context（SceneGraphContext）+ NPC 当前 state（NPC 状态机查询）+ 玩家 state（state path 引用）+ 技能 enum + AestheticPreference 字段集 + dramatic_triggers + few-shot 例子库`
- **输出接口**：1 个完成的 dialogue_graph node（narration 旁白 + options 选项 + state_effects 状态变更）+ 评估元数据（rubric 各维度分 + 触发的 anti-pattern flag）
- **调用方**：T-3.5 批量调度器（每节点调一次）+ 审阅 UI（间接：UI 渲染 rubric 元数据 + 提供 [A]/[R]/[S] 标）

---

## 2. 6 阶段工作流（作者签字 2026-05-15）

把"从原始故事素材 → 节点级文本生成完毕"全流程拆 6 阶段：

| 阶段 | 输入 | 输出 | 谁主导 |
|---|---|---|---|
| **阶段 0：素材消化** | 原始故事素材（CoC 模组 / 原创大纲） | 字段集（NPC 卡 / 钩子 / 事实清单 / 时间线 / 场景列表 / GM 即兴空间清单 等 11 类）| AI 主导（90%）+ 作者校对（10%） |
| **阶段 1：幕级规划** | 阶段 0 字段集 | 每幕的 act_purpose（幕意图）/ included_scenes（包含场景）/ act_reveals（幕级揭露）/ act_seeds（幕级种子）| 作者主导（70%）+ AI 草拟（30%） |
| **阶段 2：场景级规划** | 阶段 1 幕表 + 选定场景 | 11 字段（scene_purpose / scene_act_id / scene_metaparams / scene_static_inputs / scene_static_outputs / scene_reveals / scene_seeds / scene_branches + 运行时三字段）| 作者 50% / AI 50% |
| **阶段 3：节拍清单** | 阶段 2 场景级字段 | N 个 beats（节拍 / 戏剧动作单元） | AI 70% / 作者 30% |
| **阶段 4：节拍 → 节点骨架** | 阶段 3 节拍清单 + state effects 设计 | dialogue_graph 骨架（节点 / 选项 / state effects / 拓扑） | AI 80% / 作者 20% |
| **阶段 5：节点文本生成** | 阶段 4 节点骨架 + 全局 context | narration + option text | AI 90%（baimiao-rpg-node skill 完成）+ 作者 [A]/[R]/[S] 审 10% |

### 2.1 关键洞察：阶段 1 是 A1 dry-run 的关键缺口

A1 dry-run（[2026-05-13_A1_dry_run_crimson_letters.md](2026-05-13_A1_dry_run_crimson_letters.md)）跳过了阶段 1（幕级规划），从阶段 0（§1 字段集）直接进入阶段 2/3（§2 场景选择 + 节拍）。本会话补齐这个缺口（详 §3）。

### 2.2 严守信息分层（不偷看后续）

每阶段决策只允许基于**前阶段输出 + 阶段 0 字段集**，不能引用后阶段的具体形态。这是 workflow 通用性的健壮性保证 —— 任何故事 / 任何制作人都能按此流程跑，不需要 retrofit（事后回填）。

---

## 3. 23 个决策点 + 决策结果 + 谁做（Crimson Letters case 走完）

### 阶段 0：素材消化（A1 dry-run 已完成；引用）

| # | 决策点 | 决策结果（具体内容）| 谁做 |
|---|---|---|---|
| 0.1 | 哪些字段从素材直接抽？ | 12 张 NPC 卡 / 1 介入钩子 / 30+ 角色扮演钩子 / 25 条核心事实 / 守秘人笔记 / 时间线 / 4 候选真凶 / 倒计时 5 级 / 5 个 ending / 9 个场景 / 7 形式 GM 即兴空间 | AI |
| 0.2 | 哪些字段 AI 自补？ | 9 个：`display_name` / `if_culprit` / `pair_with` / `background_only` / `acquisition_method` enum / `gm_only_flag` / `event.phase` / `gm_notes.category` / `roleplay_hook.trigger_condition` | AI（待作者确认） |
| 0.3 | 哪些必须作者校对 / 拍板？ | 6 个：真凶选哪个（4 候选）/ 5 级显现具体节奏 / DC 数值 / 红鲱鱼临场时机 / 通路征兆何时何地显现 / 场景访问顺序 | 作者 |

### 阶段 1：幕级规划（本会话新做）

| # | 决策点 | 决策结果 | 谁做 |
|---|---|---|---|
| 1.1 | 分几幕？ | **3 幕** | 作者（依据 §1.5 时间线 + §1.8 5 ending 触发 cluster）|
| 1.2 | 每幕 act_purpose？ | act_1: 开场调查 / act_2: 调查 + 嫌疑人聚集 / act_3: 解决 + 真相揭露 | 作者 + AI 草拟 |
| 1.3 | 每幕含哪些场景？ | act_1: scene_farren_office / scene_wright_office / scene_corpse_morgue;<br>act_2: scene_inn / scene_vick_shop / scene_sanatorium / scene_wright_cottage / scene_hobhouse_manor;<br>act_3: scene_police_station + ending 触发节点 | AI 推荐 + 作者拍板 |
| 1.4 | 每幕 act_reveals？ | act_1: 莱特死因不寻常 / 办公室破镜 + 烧过文件 / 尸体可能附身;<br>act_2: 莱特双面身份 / 维克危险 / 弗林德斯监视 / 大西洋城打手 / culprit_id 真凶确认;<br>act_3: 真凶最终确认 / ending 揭露 | 作者主导 + AI 草拟 |
| 1.5 | 每幕 act_seeds？ | act_1: 露西线索（约会日记）/ 维克可疑提案;<br>act_2: 通路征兆升级 / ending preconditions 累积;<br>act_3: 收尾幕不再埋种子 | 作者主导 + AI 草拟 |

### 阶段 2：场景级规划（本会话新做；以 scene_inn_meet_lucy 为 case）

| # | 决策点 | 决策结果 | 谁做 |
|---|---|---|---|
| 2.1 | scene_purpose？ | 走访露西获取莱特另一面 + 维克线索 + 大西洋城打手线索 | 作者 + AI 草拟 |
| 2.2 | scene_act_id？ | act_2_investigation | AI 自动（阶段 1 幕表） |
| 2.3 | scene_metaparams？ | culprit_id: culprit_vick | 作者（§1.6 选 vick）|
| 2.4 | scene_static_inputs？ | flag.lucy_known_to_player=true / flag.wright_dead=true / flag.gangster_watching_lucy=true / relationship.lucy.trust=0 / player.investigator_credentials=true | AI 推导 + 作者审 |
| 2.5 | scene_static_outputs？ | world_state.lucy_status ∈ {5 种}; 至少之一 inventory.vick_business_card=true 或 flag.gangs_alerted_to_player=true | AI 推导 + 作者审 |
| 2.6 | scene_reveals？ | R1 莱特另一面 / R2 维克危险 / R3 弗林德斯监视 / R4 大西洋城打手 | 作者（§1.3 事实集 → 露西关联事实） |
| 2.7 | scene_seeds？ | S1 大西洋城打手前置 / S2 维克"招惹不得" / S3 弗林德斯监视细节 / S4 乡间小屋藏匿点 | 作者主导（阶段 1 拆解）+ AI 推荐 |
| 2.8 | scene_branches？ | 5 个 exit → 后续场景 routing | AI 拓扑推导 + 作者审 |

### 阶段 3：节拍清单（A1 §2.2 已完成；引用）

| # | 决策点 | 决策结果 | 谁做 |
|---|---|---|---|
| 3.1 | 几个节拍？ | 6 节拍 | AI 拆 + 作者审 |
| 3.2 | 每节拍主题？ | beat_1_arrival / beat_2_lucy_notice / beat_3_wright_name_drops / beat_4_info_layer_unfold / beat_5_eye_tension / beat_6_exit_branch | AI 拆 |
| 3.3 | 节拍间因果链？ | 时间顺序 + CoC 调查节拍体系 | AI |

### 阶段 4：节拍 → 节点骨架（A1 §3.6 / §3.7 已完成 v2.1；引用）

| # | 决策点 | 决策结果 | 谁做 |
|---|---|---|---|
| 4.1 | 节拍 → 节点映射比？ | 6 节拍 → 10 节点（5 dialogue + 5 end）= 1.67:1 | AI |
| 4.2 | 节点拓扑（DAG）？ | node_1 → node_2 → node_3 (hub) → node_4/5/6-10 + 2 个回路 | AI |
| 4.3 | 每节点的 options + condition + effects？ | 19 options / 9 diverges / 8 类 effects | AI |

### 阶段 5：节点文本生成（A1 §4.1.1-4.1.10 已完成；引用）

| # | 决策点 | 决策结果 | 谁做 |
|---|---|---|---|
| 5.1 | 每节点 narration + option text 怎么写？ | 由 baimiao-rpg-node skill 完成；A1 实测 10 节点文本 | AI（skill）+ 作者 [A]/[R]/[S] |

### 跨阶段总结

- **23 决策点中作者必须拍板的 = 7 个**（分幕 / act_purpose / act_reveals / act_seeds / scene_purpose / scene_reveals / scene_seeds + scene_metaparams 中的 culprit_id）
- **AI 主导 16 个**（其他全部）
- **作者工作量集中在阶段 1+2 剧本意图层**

---

## 4. 场景级字段 schema 草案（11 字段；待 ADR-034 调研后形式化）

### 4.1 字段集

```yaml
scene_id: string                  # 场景标识符
scene_purpose: string             # 场景意图（一句话）
scene_act_id: string              # 归属哪一幕

scene_metaparams:                 # 场景元参数（影响整个场景生成期的元变量）
  culprit_id: string              # 真凶（ADR-031 F1 落地）
  difficulty_level: enum          # 难度（ADR-031 F6）
  apparition_level: int           # 当前显现等级（ADR-031 F3）
  # ... 其他项目可扩展

scene_static_inputs:              # 入场前置条件（编剧拍板的硬 precondition）
  - state_path: condition
  
scene_static_outputs:             # 出场后置条件（编剧拍板的硬 postcondition）
  - state_path: condition

scene_reveals:                    # 场景揭露清单（progressive disclosure 渐进揭露结构 - 草案见 §8 问题 2）
  - reveal_id: string
    trigger_node_ids: list[str]
    completion_node_id: string

scene_seeds:                      # 场景种子清单（coverage_strategy 覆盖策略 - 草案见 §8 问题 3）
  - seed_id: string
    planted_in_node_ids: list[str]
    condition: optional
    coverage_strategy: enum       # mandatory_all_paths / mandatory_with_fallback / conditional_reward

scene_branches:                   # 出口分支（指向后续场景）
  - exit_node_id: string
    target_scene_id: string
    condition: optional

# 运行时三字段
scene_actual_inputs: dict         # 进入时算（基于上一场景结束 state）
scene_actual_outputs: dict        # 离开时记录
included_node_ids: list[str]      # 本场景的节点 list
```

### 4.2 scene_inn_meet_lucy 完整实例

详 §3 阶段 2 决策结果 2.1 ~ 2.8。

---

## 5. 节点级字段 schema 草案（待 ADR-034 调研后形式化）

### 5.1 字段集（baimiao-rpg-node skill 输入契约）

```yaml
node_id: string

foreground_goal: string           # 本节点要传达的最关键信息（承载哪个 reveal）

background_seeds:                 # 本节点要埋的 seeds（从 scene_seeds 拆解）
  - seed_id: string

player_known_info:                # 双层结构（解决信息池治理"全量 vs 子集"矛盾）
  relevant_known_info:            # retrieval 短列表（给 skill 直接用）
    - knowledge_item: string
  all_known_info_summary: string  # 全局背景一段话（兜底）

skill_check_input:                # 涉及的检定 + DC（ADR-029 调用）
  - skill_id: string
    dc: int                       # 难度等级；项目配置层定义具体数值
```

### 5.2 关键设计决策

- **player_known_info 双层结构**：解决"全量 vs 子集"矛盾（详 §7 已拍板项 1.1）
- **player_known_info 内容范围**：含 NPC 因玩家互动改变的 state（2.2 拍板）+ 检定结果（2.3 拍板）；不模拟玩家遗忘（2.4 拍板）

---

## 6. Forward Planner（前向规划器）3 子模块设计

### 6.1 模块 A：剧本意图层（编剧 / 宏观）

- **输入**：dialogue_graph 整体结构 + chapter outline + 角色弧光设计
- **输出**：每节点的 **intended_foreground_goal**（编剧期望的节点目的）+ **intended_background_seeds**（编剧期望埋下的种子）
- **由谁产出**：作者人工编写（首版）+ AI 辅助（后续）
- **颗粒度**：场景级 → 节点级
- **时机**：内容生产期，生成节点之前

### 6.2 模块 B：状态摘要层（玩家路径 / 微观）

- **输入**：dialogue_graph 当前路径 + state 状态 + NPC 状态机 state
- **输出**：**actual_player_known_info**（玩家在本节点实际已知的信息）
- **算法**：从 state path / character.knowledge / 完成的检定 等结构化数据**抽取** + summarize
- **颗粒度**：节点级
- **时机**：生成本节点之前，每个节点 / 路径单独算

### 6.3 模块 C：Precondition + Reconcile 协调层

- **输入**：模块 A 输出 + 模块 B 输出 + skill Precondition（前置条件）
- **输出**：
  - 通过 → 调 skill 生成节点
  - 不通过 → 4 个分支：
    - 拆节点（前置注入新节点补足锚点）
    - 改 foreground_goal（弱化编剧意图）
    - 改 background_seeds 历史（往回追溯 seed 分配）
    - 标 unreachable → 报警给作者
- **颗粒度**：节点级

### 6.4 Re-planning 复杂度边界（已拍板）

- 幕级：**永不 replan**（编剧意图固定；详 §7 拍板项 5）
- 场景级 reveals/seeds/purpose：**永不 replan**（编剧意图固定）
- 场景级 actual_inputs/outputs：**进入场景时算一次**
- 节点级：**进入节点时算**

**复杂度 = 每场景 1 次 + 每节点 1 次**（线性可控）。

---

## 7. 已拍板项清单（本会话期间作者签字）

| # | 内容 | 签字日期 |
|---|---|---|
| **1** | T-3Y = 单节点好文本生成的自包含模块；ADR-030 + T-3X-1a + 相关文档全部 fold 进 T-3Y；T-3X-1b / ADR-031 / ADR-029 保留独立 | 2026-05-15 |
| **1.1** | 信息池治理 = **双层结构**（relevant_known_info + all_known_info_summary）；起步用 retrieval 子集，T-3Y-1 实测后调 | 2026-05-15 |
| **2.2** | NPC state 算 player_known_info **边界**：因玩家互动改变的算（如露西信任度上升玩家可感知）；NPC 静态描述不算（如头发颜色） | 2026-05-15 |
| **2.3** | 检定结果（被动注入文本 + 主动检定通过的揭示文本）**算** player_known_info | 2026-05-15 |
| **2.4** | **不模拟玩家遗忘** —— 默认玩家记住一切；运行时无 LLM；遗忘机制会引入巨大复杂度 | 2026-05-15 |
| **3** | **3 层架构 + 动静分配**：幕级全静 / 场景级半静半动 / 节点级全动 | 2026-05-15 |
| **5** | **所有可能场景在编剧期枚举为 DAG**；玩家选择 = navigation（在 DAG 上选路径），不是 generation（不动态生成新场景） | 2026-05-15 |
| **6 阶段工作流** | 见 §2 | 2026-05-15 |
| **3 幕分法** | act_1_opening / act_2_investigation / act_3_resolution | 2026-05-15 |

---

## 8. 4 个待 ADR-034 / 后续讨论拍板的设计问题

### 8.1 问题 1：scene_metaparams 字段必须新增

**现象**：A1 §2.1 的 `culprit_id: culprit_vick` 是场景生成期元参数（ADR-031 F1 落地），影响整个场景的 NPC 反应 + 信息基线。原 9+2 字段草案没列。

**推荐**：新增 `scene_metaparams`（独立于 scene_reveals）。候选项：culprit_id / difficulty_level / apparition_level（当前显现等级）等。

**状态**：⏸ 待 ADR-034 调研业界格式如何处理"场景级元参数"后回头拍板。

### 8.2 问题 2：scene_reveals 应是 progressive disclosure 渐进揭露结构

**现象**：R1 "莱特另一面" 不是一次性 reveal —— 在 node_2 暗示 + node_3 揭露 + node_5 加深的渐进过程。

**推荐**：scene_reveals 字段结构改为 `{reveal_id, trigger_node_ids: list, completion_node_id, depth_per_node}`。不是 flat list of strings（扁平字符串列表）。

**状态**：⏸ 待 ADR-034 调研业界（Ink / Articy）如何表达 progressive disclosure 后回头拍板。

### 8.3 问题 3：scene_seeds 应有 coverage_strategy 覆盖策略字段

**现象**：S3 / S4 都是只在条件路径埋 —— 意味着 scene_seeds 不是简单 list，需要 `{seed_id, planted_in_node_ids, condition, coverage_strategy}` 结构。

**3 种 coverage_strategy（覆盖策略）**：
- `mandatory_all_paths`（强制全路径覆盖）：所有路径都必须埋（S2 这种）
- `mandatory_with_fallback`（强制但带回退）：默认埋；如某路径错过 → 后续场景做 precondition 注入（S1 这种）
- `conditional_reward`（条件性奖励）：仅条件路径埋；后续场景接受不完备覆盖（S3/S4 这种）

**状态**：⏸ 待 ADR-034 调研业界如何处理"信息覆盖策略"后回头拍板。

### 8.4 问题 4：scene_static_inputs 范围决策

**现象**：node_1 opt_observant_setup 有 `condition: player.traits has observant`。这个 trait 是否要进 scene_static_inputs？

**两种处理**：
- (a) **严格 schema**：scene_static_inputs 只列入场强制 precondition；options 的 condition 是节点内的，不进场景级
- (b) **完备 trace**：scene_static_inputs 列出本场景所有 reachability 涉及的 state path，方便 validator 校验 dep_index

**推荐**：(a) —— A1 §2.1 已选；options condition 由 Forward Planner 节点级处理。

**状态**：⏸ 待 ADR-034 调研业界处理后回头拍板（弱依赖）。

---

## 9. 跨 ADR 协同

| ADR | 协同点 | 是否冲突 | 行动 |
|---|---|---|---|
| **ADR-029** 技能体系项目配置层 | T-3Y 调用项目 skills.json（option text `[skill_name]` 标记的 enum 校验依赖）| ✓ 不冲突 | T-3Y ADR-032 草案需声明依赖 |
| **ADR-030** AestheticPreference schema 字段集预留 | **fold 进 T-3Y 模块**——schema 字段集就是 T-3Y 的"规则"段（输入契约的一部分）| ⚠ 需要 ADR-030 v0.2 修订或 retire | 待 ADR-032 立项时一并处理 |
| **ADR-031** GM 抉择空间结构化方案 | T-3Y 是 F2/F7 落到节点级时的执行环节；scene_metaparams（culprit_id / apparition_level / difficulty_level）就是 ADR-031 F1/F3/F6 的落地 | ✓ 不冲突 | T-3Y 不重做 ADR-031 |
| **ADR-018** 关系层 narrative_weight | character.relations 多维（trust / cooperability / fear / affinity）是 player_known_info 模块 B 状态摘要的输入 | ✓ 不冲突 | T-3Y 输入契约引用 |
| **ADR-019** dramatic_triggers | 一次性事件按优先级排序；T-3Y 可能需要查 dramatic_triggers 决定本节点是否触发 event | ✓ 不冲突 | T-3Y 输入契约引用 |
| **ADR-022** playtest bots | playtest 时 5 persona × 20 paths 必须能跑通 Forward Planner（每条 path 独立算 模块 B） | ✓ 不冲突 | T-3Y 设计需 cover playtest 场景 |
| **ADR-023** content_dependency_index | T-3Y 引用的 state paths / character_ids 都要写入 dep_index trace | ✓ 不冲突 | T-3Y 工程实现需 hook |
| **ADR-024** 长对话一致性 SceneGraphContext | T-3Y 模块 B 状态摘要的输入直接复用 prior_scene_summaries 字段 | ✓ 不冲突 | T-3Y 输入契约引用 |
| **ADR-027** World-Agnostic Principle | T-3Y 不绑定具体世界观（克苏鲁等）；scene_metaparams.culprit_id 是项目层填的 | ✓ 严守 | T-3Y ADR-032 草案需声明 |
| **ADR-028** 引擎与宿主分离 | T-3Y 在生产期；不进运行时 | ✓ 严守 | T-3Y ADR-032 草案需声明 |
| **ADR-002 / ADR-004** 运行时无 LLM + 生产期分离 | T-3Y 完全在生产期跑；运行时只是查 T-3Y 生成完的 JSON | ✓ 严守 | T-3Y ADR-032 草案需声明 |

---

## 10. 下游会话引用本档的方式

### 10.1 ADR-034 schema IR 调研会话

**必读全档**。重点：
- §4 场景级字段 schema 草案 + §5 节点级字段 schema 草案 = ADR-034 调研要对标的"Forgewright 设计中"schema
- §8 4 个设计问题 = ADR-034 调研要给出"业界如何处理"的对照答案
- 跨工具对比表的"Forgewright 当前 schema 是否表达"列拆为两列：
  - "Forgewright v0.3（当前落地）"
  - "Forgewright T-3Y 设计（草案；本文档）"

### 10.2 ADR-035 L3 宿主调研会话

**必读 §4 + §5**。重点：
- Godot 适配层估时基于 §4 + §5 的字段（含 scene_metaparams / progressive disclosure / coverage_strategy 等 T-3Y 新增字段）
- 集成方案 §4 要 cover 这些字段在 Dialogic 适配层怎么映射

### 10.3 未来 T-3Y-1 工程会话

**必读全档**。本档是 T-3Y-1 paste-ready prompt 的核心输入。

---

## 11. 版本

- **v0.1**（2026-05-15）：T-3Y L2 会话进展快照，便于 ADR-034 / ADR-035 调研会话作为输入引用。
- **v0.2+**（未来）：T-3Y 会话继续推进 ST-3 / ST-4 / ST-5 / ST-7 / ST-9 子任务后增量更新。
