# Handoff · Phase 2 文风/质感层——样例锚点 + 维度 taxonomy + 同维校验 + 规则分层

> 给一个**全新会话**的自包含任务书。无本前讨论记忆，所需上下文全在下面。
> 性质：**软地基改动**（触及 generator 生成 prompt 层 + 新立锚点/judge 机制）→ 按 ADR-037
> **设计先行**：先出方案给作者过目（基于目标和结果沟通，渲染 concrete 形态），作者点头再施工。
> 起草：2026-06-12，由 Phase 1 结构层落地会话按约定生成（作者授权落位 /docs/handoffs/）。

## 0. 开始前（CLAUDE.md 规则 1）

你在 Forgewright 仓库工作。**先读** `CLAUDE.md` + `generator/CLAUDE.md`，按规则 1 acknowledge
并总结对本任务最相关的 3 条规则，再动手。

## 1. 背景（self-contained）

Forgewright = AI 辅助分支叙事内容生产流水线（开发期生成 CRPG 对话图；运行时无 LLM）。

**结构层（Phase 1）已收官**：多 pass + 分拍 + 动态拓扑引擎 = `generator/multipass/`
（PR #75 + PR #76 merged，main `8eb04d8` 起可用）。作者终审"有条件生产就绪"，
收敛路由 / junction 承接已修，维克类场景解除暂缓。**当前文本质量的瓶颈在文风/质感层**——
作者 2026-06-10 审阅时表态"质量提升后置到 Phase 2"。

**Phase 2 方向已于 2026-06-08 讨论收敛**（advisory 记录 =
`docs/reviews/master_plan/2026-06-08_creation_aesthetic_layer_discussion.md`；
⚠️ 该文件可能仍是作者主仓未提交文件——若读不到，本节摘录即权威输入）：

1. **核心机制 = 样例锚点（example-conditioning，范例条件化）**：用户提交/批准一份
   "符合自己审美的文风样例"，当 few-shot 锚点驱动批量生成——**样例 = 控制**，比规则/分数强。
2. **维度（dimensions）的岗位**：探索 + 校验（不是控制）——前端给用户调，后端给
   judge/validator 校验产出，**同一套维度 taxonomy 前后通用**。
3. **反 AI 腔规则迟早分两层**：普适"结构"规则（任何风格都不该犯，如 AP-8 选项第三人称化）
   vs 可换"审美预设"（如白描/反隐喻 = 一个预设，应可换）。新初心（让人快速做 RPG 的软件）
   要求**文风成为参数**。
4. **范围边界（最重要，别混）**：核心只认"一份用户批准的样例"；
   **文风提示词编译器 = 辅助工具，非核心，本任务不做**（方向 4 另立）。

**对应工作清单（讨论记录 §3 方向 3 四阶段，即本任务范围）**：
- 3.1 定义固定文风维度 taxonomy（~10–20 维；从 dialogue-flow 5 维 + 10 条 AP +
  白描/talkstyle 轴提炼）
- 3.2 核心管线接受"用户批准样例"当锚点（few-shot；按 role_rules 3 分类——
  旁白 / NPC 对白 / 玩家选项——各配锚点）
- 3.3 judge 用**同一套维度**给批量产出打分（前控制 = 后校验；AP-1~6 + AP-9 的
  LLM-as-judge 执行层也落在这里）
- 3.4 反 AI 腔规则分层（普适结构 vs 可换审美预设；白描降为"一个预设"）

**等作者拍的两个决策**（讨论记录 §5 #3/#4，本任务设计阶段要给出提案供拍板）：
- 决策 A：文风维度 taxonomy 具体清单（作者审美参与定）
- 决策 B：10 条 AP 哪些归"普适结构"、哪些归"审美预设"（与 A 一起定）

## 2. 先读这些（按优先级）

1. `docs/reviews/master_plan/2026-06-08_creation_aesthetic_layer_discussion.md` ——
   上位讨论 + 工作清单（若 untracked 读不到，以 §1 摘录为准，并提醒作者提交该文件）。
2. `generator/experiments/multipass_structure/PHASE2_INPUT_aesthetic_observations.md` ——
   结构层复核攒下的文风观察：**作者三条审美口径**（玩家台词别电报体 / 确认类用代称不复述 /
   不为个案立新 AI 腔标准）+ AP 检测器误报型 + 修辞边界案例 + 量化基线。
3. **作者已接受的文本样本**（锚点候选的最优先来源）：
   - `generator/experiments/multipass_structure/2026-06-10_whitcroft_v2/scene.md`（作者"基本过关"基准）
   - `generator/experiments/multipass_structure/2026-06-10_lucy_roadhouse_multipass/scene.md`（作者接受）
   - `generator/experiments/multipass_structure/2026-06-11_convfix/` 下 vick/lucy 重跑（作者终审状态问作者）
4. `docs/AESTHETIC_PREFERENCES.md`（v0.1）——作者审美偏好档；注意 §0 明示
   温度/节奏/弧光/价值轴四维**有意 TBD**——taxonomy 提案正是补这块的机会。
5. 现行文风规则机器：`generator/prompts/node/anti_pattern_blacklist.py`（提示词版 7 条；
   AP-7/8/10 已归 validator 程序化检测）+ `role_rules.py`（3 分类契约）+
   `generator/prompts/node/multipass/{pass2_prose,beat_pacing}.py`（文风段落所在地）。
6. `generator/experiments/multipass_structure/2026-06-10_review/REVIEW_REPORT.md` ——
   质量基线 + 已修/未修问题账本。
7. `docs/reviews/master_plan/2026-05-09_aesthetic_layer_decision_v0.1.md` + DECISIONS.md
   ADR-030（审美锚点）/ ADR-018（按需注入）/ ADR-008（生成/校验分离）——历史决策约束。

## 3. 任务（设计先行 → 作者过方案 → 再施工）

**先出设计**（taxonomy 提案 / 规则分层提案 / 锚点库格式与注入方式 / judge 形态 / 评估方案），
作者点头再写代码。要解决这 5 项：

1. **文风维度 taxonomy 提案**（决策 A）：~10–20 维草案；**每一维配正/反例句**
   （从作者已接受样本和被拒样本里摘真句），渲染成作者可逐维勾选/修改的 concrete 形态——
   作者按"最终效果"判断，不读抽象定义。
2. **AP 规则分层提案**（决策 B）：10 条 AP 逐条标"普适结构 / 审美预设"+ 理由；
   白描相关规则归入"预设"后，预设的开关/替换机制怎么落（prompt 装配层参数化）。
3. **样例锚点机制**：从作者已接受文本提取锚点候选（旁白 / NPC 对白 / 玩家选项三类各若干条），
   **渲染给作者挑选批准** → 锚点库 v1（格式 + 存放位置自行设计，建议 `generator/prompts/style/`
   下 JSON/MD，git 跟踪）→ 注入 multipass 生成路径（pass2 / beat_pacing / end 收束），
   遵守 ADR-018 按需注入、控制 token 增量（给出每调用增量数字）。
4. **同维 judge（LLM-as-judge）**：用拍板后的 taxonomy + AP-1~6/9 给产出打分；
   落 `/generator`（judge 调 LLM，不进 /validator——validator 保持确定性，边界铁律）；
   产出形态对齐现有 metrics/复核报告习惯（可机读 + 可人读）。
   注意作者口径：**不为个案扩规则集**——judge 是执行已有标准，不是立新标准。
5. **A/B 评估收口**：固定结构层版本，lucy + whitcroft + vick 三 spec 各跑
   带锚点 vs 不带锚点对照（≥6 次运行），judge 同维打分 + 作者审剧本 markdown →
   文风层是否达到"作者少改即可用"的一句话判定。
   顺带收口结构层移交的残留：保底专名相似对（0.80–0.82）是否需文风层进一步压低，交作者裁量。

## 4. 硬约束

- **只在 `/generator`**（含其测试）施工；新 handoff/报告文档须作者明示授权才动 `/docs`。
  **schema 不改；/validator 不改**（judge 在 generator 侧；若设计推导出 validator 必须动，
  停下报告作者）。结构层逻辑（拓扑/路由/承接/组装）**不动**——只动文风规则段与锚点注入。
- LLM 调用走 `LLMProvider` + `budget.check_and_charge()`（ADR-011/012）；judge 调用同样过 budget。
- **中转站现实**：`.env` 配 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`；`json_mode=prompt_only`；
  全部小调用（`generator/multipass/calls.py` 的 est_output_tokens ≤ 2000 护栏沿用）。
  锚点注入会加大 prompt——注意输入 token 成本，给出实测数字。
- **版权红线**：锚点库（会进仓库、将来可能随框架开源）只收**项目自产已接受文本或作者自写文本**；
  外部版权文本（如极乐迪斯科段落）只可作私有对照实验，不得进锚点库。
- **软地基纪律（ADR-037）**：设计先行；锚点库内容与 taxonomy 必须经作者批准才算"用户批准样例"
  ——这是核心机制的定义本身，不是流程客套。
- 预算量级：评估 A/B ~6–8 次运行 + judge 调用，预估 $4–6；超出先报作者。

## 5. 交付物

1. 设计说明（taxonomy / 规则分层 / 锚点机制 / judge / 评估方案）+ 作者拍板记录（决策 A/B）。
2. 锚点库 v1（作者批准的样例，git 跟踪）+ 锚点注入落地代码 + 预设分层落地 + 测试全绿 +
   边界自检（`grep -R "from generator" engine/ state/ schema/ validator/` 无匹配）。
3. judge 打分器 + A/B 评估报告（带/不带锚点对照 + 作者审阅接受情况）。
4. 一句话：文风层是否可判定"达到作者少改即可用"。

## 6. 范围红线

- **文风提示词编译器（方向 4）不做**——非核心辅助工具，另立任务。
- **结构层不动**：拓扑/路由/承接/组装/分拍机制保持 main `8eb04d8` 行为；
  发现结构层 bug 记录移交，不顺手修。
- **DOME 一致性图谱（方向 5.1）不做**——validator 安全网另立。
- 运行时无 LLM（CLAUDE.md 架构共识 4）不变；锚点机制全部是开发期行为。
