# Forgewright 愿景 + 路线图（2026-05-18 整合）

> **来源**：2026-05-18 T-3Y L2 综合规划师会话（claude/adoring-wilbur-42c816 worktree）+ 作者拍板
> **状态**：v0.1 草稿；可作为后续 L1 fixation 升级到 `/docs/VISION.md` 或 ROADMAP 增量段的输入
> **触发**：ADR-034 + ADR-035 + ADR-016 v0.4 全部落地后（main HEAD `72d81a7`；2026-05-18），作者要求整体愿景 + 路线图整合

---

## 1. 项目核心价值（4 层独特性；从"真实空白"角度）

| 价值层 | Forgewright 独特性 | 市面对比 |
|---|---|---|
| **数据格式** | 业界事实标准 superset（超集）；Ink / Articy / Dialogic 互操作；knowledge.* 命名空间（ADR-016 v0.4） | Articy 闭源 / Ink 是 DSL 不友好 AI / Twine 太简陋 |
| **内容生产** | **AI 辅助批量生成 + 多层校验 + 审阅 UI** | **市面唯一**——其他工具要么纯人手要么纯运行时 LLM |
| **运行时** | 极简 JSON 播放器 + 通用宿主（Godot 4.x + 自定义 Control nodes；ADR-035） | Inworld / Convai 等都是运行时调 LLM（贵 + 慢 + 失控）|
| **方法论** | 调查叙事品类的**可重复生产工程方法论** | Disco Elysium 工作流是商业机密；CoC 模组面向人类 keeper；这是真实空白 |

**真正不可替代的 = 第 2 行 + 第 4 行**。数据格式（1）和运行时（3）都是手段；目的 = **让 AI 帮你以可控质量 + 可重复方式批量产剧情内容**。

---

## 2. 工程任务核心：文本生成的 3 层

```
┌─────────────────────────────────────────────┐
│ 质感层（quality layer）                    │
│ → 文字风格工作台 + baimiao-skill 系列      │
│ → 解决：写出来的字本身好不好               │
├─────────────────────────────────────────────┤
│ 机制层（mechanism layer）                  │
│ → T-3Y 节点级文本生成 + Forward Planner    │
│ → 解决：单节点 input/output 契约 + 路径    │
│   状态下的信息分配                          │
├─────────────────────────────────────────────┤
│ 格式层（format layer）                     │
│ → schema + validator + knowledge.*         │
│ → 解决：数据结构 + 业界互操作               │
└─────────────────────────────────────────────┘
                    ↓
         ┌─────────────────────┐
         │ L3 宿主（Godot 4.x）│
         │ 玩家最终运行环境     │
         └─────────────────────┘
```

3 层都属于"文本生成"广义范畴，但需要**完全不同的工程能力**。Forgewright 的真正差异化在**机制层 + 方法论沉淀**。

---

## 3. 路线图

### 3.1 已闭环 ✅

| 模块 | 关键产出 | 落地时间 |
|---|---|---|
| 阶段 0 基座 | schema / engine / state / validator MVP | 2026-04-25 ~ |
| 阶段 1-1.5 单节点 | 单节点 AI 生成 + 视觉资产管线 | 2026-04 ~ 05 |
| 阶段 2 场景 | 5 场景实测 + dimensions rubric + critique 闭环 | 2026-05-07 |
| 阶段 3 工程层 | T-3.0~T-3.9 工程任务全部 merged（14 槽位）| 2026-05-09 |
| ADR-031 GM 抉择空间结构化 | 混合方案 D（A 基础 + B NPC 状态机）+ T-3X-1 拆分 | 2026-05-13 |
| T-3Y 设计层 | 6 阶段工作流 + Forward Planner 3 子模块 + 23 决策点 + 4 个争议点 | 2026-05-15 |
| **ADR-034** schema IR | v_incremental 路线 + ADR-016 v0.4（knowledge.* 命名空间）+ 11 子决策 D1-D11 | 2026-05-18 |
| **ADR-035** L3 宿主 | v_godot_custom（Godot 4.x + 自定义 Control nodes）+ /engine/ a+b 合并保留 | 2026-05-18 |
| **5 个 T-3Y 设计争议点** | scene_metaparams / scene_reveals ordered flag set / coverage_strategy v0.1 / player-monotonic D11 / player_known_info schema list | 2026-05-18 |

### 3.2 当前阻塞已解除 🔓

**T-3Y-1 工程会话**（节点级文本生成 mini prototype）—— 依赖 ADR-016 v0.4 + knowledge.* 命名空间，已 unblock。

### 3.3 下一步关键任务（按优先级 + 依赖排序）

| 优先级 | 任务 | 为什么 | 预计 ETA | 适合 AI 整夜工作？ |
|---|---|---|---|---|
| 🔴 **P0** | **T-3Y-1 mini prototype 起跑** | 文本生成机制层的实证；早跑早知道 LLM 质量真假 + 评估 rubric 可不可用；DEBATE §10 项目级赌注的第一份实证 | 1-2 周 | ✓ 高度适合（/goal + auto mode）|
| 🟡 **P1** | **T-3.10 Wave 7 实测期** | 每周 ≥ 10 场景；积累审稿数据；反推 anti-pattern v0.2+；沉淀方法论 | 4-8 周持续 | ✓✓ 最适合（cron 化）|
| 🟢 **P2** | **文字风格工作台迭代** | A/B 判例补全 + 真实 dialogue node 回归测试 + Layer 3 克苏鲁 overlay | 持续 | ⚠ 部分适合 |
| ⏸ **deferred** | L3 宿主集成（Godot + 适配层）| 阶段 4 起手；不阻塞当前 | 阶段 4 | ✓ 适合（阶段 4 时） |
| ⏸ deferred | T-3Y v0.2 内部 ST（ST-3/4/5/7/9）| 等 T-3Y-1 实测数据后再判断要不要做 | 阶段 4 | 部分适合 |
| ⏸ deferred | ADR-034 follow-up（.2/.3/.4） | choice_visibility 字段 / inline conditional / chapter.ifid；中低优先级 | 阶段 3-4 | 部分适合 |

---

## 4. 战略提示（3 条核心 insight）

### 🎯 Insight #1：差异化在方法论沉淀，不在工具本身

Forgewright 工具就算开源了，竞争对手可以 fork。但**调查叙事品类的"哪些场景该埋什么 seed / 哪些节点该 reveal 什么 / Forward Planner 怎么算 player_known_info"** 是工程经验，要靠**阶段 3 T-3.10 实测期 + 阶段 4 落地实战**沉淀。这是**护城河**。

→ **行动**：T-3.10 实测期不只是"跑通工程"，要**有意识地沉淀方法论档案**（如 `/docs/METHODOLOGY/` 系列，待立），未来开源时它就是 Forgewright 的核心 IP（知识产权）。

### 🎯 Insight #2：T-3Y-1 是"AI 质量天花板"的真实测试

T-3Y 设计层已经完了。但**设计再漂亮，AI 真的能不能在严格契约下产出 [A] 率 ≥ 60% 的文本？这是项目级赌注（DEBATE §10）**。

→ **行动**：T-3Y-1 mini prototype **不能拖太久**——1-2 周必须有第一份实测数据。如果实测 [A] 率远低于 60%，整个项目定位需重新审视（4 档回退路径 ADR-031）。

### 🎯 Insight #3："最低成本"初衷已经兑现 90%

ADR-035 闭环让 L3（视觉小说运行时）外包给 Godot；ADR-034 闭环让 L1（数据格式）兼容业界；剩下 L2（内容生产）就是核心创新，不需要妥协。

→ **行动**：守住 L2 创新边界；不要因为"先进工作流"被绕进 commodity（如再造审阅 UI 框架 / 再造 schema validator 框架）。

---

## 5. "AI 整夜工作"的主战场对照

| 任务类型 | 适配度 | 用法 |
|---|---|---|
| L2 综合规划（如本会话） | ❌ 不适合 | 你的每个签字决定大方向 |
| L3 工程任务 A 阶段 | ✓ 高度适合 | /goal + auto mode；治理 v0.4.1 已 codify |
| Codex B 阶段 review | ✓ 已自动化 | PR #38 v0.4.1 落地 |
| Claude C 阶段修复 | ✓ 已自动化 | 现有 ABC 闭环 |
| **T-3Y-1 mini prototype** | ✓✓ 高度适合 | **/goal 拆解 + auto mode** |
| **T-3.10 实测期 batch** | ✓✓✓ 最适合 | cron 化；夜里跑，白天审 |
| 作者审稿 [A]/[R]/[S] | ❌ 不可替代 | ADR-020 核心：作者本人最终编辑者 |
| 文字风格 skill 迭代 | ⚠ 部分适合 | A/B 判例 AI 草案；作者审 |

---

## 6. 一句话总结

> **Forgewright = 把"作家的剧本意图"和"玩家的路径状态"压成 LLM 可消费的严格契约 → LLM 在生产期批量产高质量分支叙事文本 → 多层校验 + 人工审稿入库 → 通过 Godot 等通用引擎以确定性 JSON 数据驱动玩家体验。**
>
> **核心价值不是 LLM 多聪明（市面都聪明），而是把"剧本写作的工程方法论"沉淀成可重复的流水线。**

---

## 7. 升级到 L1 文档的建议路径

本档目前在 `/docs/reviews/master_plan/` 下（L2 综合规划师产物）。如要升格到 L1，候选路径：

| 候选 | 操作 | 优 | 劣 |
|---|---|---|---|
| **A** 新增 `/docs/VISION.md` | L1 fixation 会话立项；将 §1 + §2 + §6 落到 VISION.md | 一份专门的愿景档；未来开源剥离时可作 README 入口 | 多一份 L1 文档 |
| **B** 扩 ROADMAP.md §阶段 4 前置段 | L1 fixation 会话；把 §3.3 路线图 + §4 战略提示 写入 ROADMAP | 不增 L1 文档数；放在已有 ROADMAP 内 | ROADMAP 膨胀 |
| **C** 保留 master_plan + 不升格 | 仅作 L2 reference | 最低成本 | 未来开源时缺正式愿景档 |

**推荐 A**：项目走到阶段 3 末期 + ADR-034/035 闭环，已经有足够 maturity（成熟度）立正式 VISION.md。但**不阻塞** T-3Y-1 推进——可在阶段 4 起手前完成 L1 升级。

---

## 8. 版本

- **v0.1**（2026-05-18）：T-3Y L2 会话整合产出。基于 ADR-034 + ADR-035 + ADR-016 v0.4 闭环后的项目状态。
