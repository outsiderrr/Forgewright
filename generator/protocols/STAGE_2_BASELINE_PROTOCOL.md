# STAGE_2_BASELINE_PROTOCOL.md

> 阶段 2 baseline 实证协议 v1。落地 ADR-020（《阶段 2 baseline 协议》），把决策固化为可执行流程文档。
>
> 本文件是 T-2.12（实证 batch run）+ T-2.13（验收报告）+ T-2.4（机械预检器）+ T-2.8（scene_ai_judge runner）+ T-2.9（本任务）的协议口径基准；任何对接受率分子/分母、机械失败口径、报告口径、AI 判官权重、成本估算的引用都以本文件为准。

**版本**：v1（ADR-020 落地版）· **创建**：2026-05-04 · **承接**：[ADR-020](../../docs/DECISIONS.md) · **配套**：[REVIEW_PROMPT_AI_JUDGE_SCENE.md](../prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md)

---

## §1 协议范围

本协议规范 **阶段 2 `generate_scene()` baseline batch run** 的全套口径，包括：

- 样本数与重试规则（§2 / §3）
- AI 判官权重表（§4）—— 具体维度由配套 prompt 文件 §B 落地
- 机械失败口径（§5）—— 由 T-2.4 `dialogue_validator` 实现
- 接受率分子分母（§6）—— 与阶段 1 R6 的差异在 §8 说明
- 阶段 2 完成判定（§7）
- 报告口径（§9）—— 每次 batch 必须双报
- 成本估算口径（§10）

**适用任务**：T-2.12 实证 batch run、T-2.13 验收报告、T-2.4 R8 机械预检器、T-2.8 `scene_ai_judge` runner、T-2.9 AI 判官 prompt。

**不在本协议范围**：阶段 1 节点级 baseline（参见 `/docs/STAGE_1_ACCEPTANCE.md`）；阶段 1.5 视觉级 baseline（参见 `/docs/STAGE_1.5_ACCEPTANCE.md`）；ROADMAP 阶段 3+ 多场景级联 baseline。

---

## §2 样本数：N=15 场景

**N=15 场景**（每场景调一次 `generate_scene()`，节点数由 SceneSetting `expected_node_count_min/max` 决定）。

**取舍依据**（ADR-020 替代方案及否决理由）：

- N=10 场景：统计显著性弱（70% 接受率 ±15% 置信区间过宽）；阶段 2 验收判定不稳
- N=20 场景：成本 $10–$20，超阶段 2 启动单 batch 预算；如 N=15 实测接受率介于 60%–80% 边界带，T-2.13 可申请补 5 个场景上 N=20
- 单场景成本远高于阶段 1 单节点（场景 = 多节点 + 完整图拓扑 + context 注入），故压缩到 N=15 平衡

**实施层**：T-2.12 `scene_experiment.py` 默认 `--count 15`；CLI 可覆盖。

---

## §3 重试规则：max_retries=2（沿用 ADR-013）

**单场景重试预算**：`max_retries=2`（共 3 次尝试）；沿用 ADR-013 阶段 1 节点级策略。

**触发回喂的失败类型**：
- Schema 失败（`response_schema` 未通过、字段缺失、类型不符）
- 图论失败（T-2.7 第二层 2A 拓扑校验失败：不可达节点 / 死锁 / 前置条件路径未闭合 / 分支收敛性问题）
- 机械预检失败（§5 七项任一不通过）

**回喂内容**：validator/预检器输出的具体错误（path + violation type），不重写 prompt（保持可重现）。

**3 次都失败**：标记 `generation_failed`，写入 `results.jsonl`，**不抛异常**；该场景计入 §6 §9 的 "总尝试场景数"，不计入 "进入 review_log"。

**注**：`generate_scene()` 内层节点级重试由 ADR-013 单独治理；本协议的 max_retries=2 指**场景级**外层重试。

---

## §4 AI 判官权重表

阶段 2 AI 判官分两层：

**节点级**（21 维度 × 节点数 N_node）：
- 沿用阶段 1 `/docs/REVIEW_PROMPT_AI_JUDGE.md` A1–E3 全集
- 每节点上限 42 分；每节点判定按阶段 1 同款规则（A 类任一 0 分直接 reject；总分 ≥ 30 → accept）
- 节点级聚合到场景级：节点接受率 = accept 节点数 / 总节点数

**场景级新增**（6–10 维度，本版定 10 维 S1–S10；详见配套 prompt §B）：
- S1 图拓扑健康 / S2 节奏 / S3 角色弧线 / S4 决策意义 / S5 收束 / S6 长度合理 / S7 context 一致性 / S8 关系层一致性 / S9 时钟一致性 / S10 ID 命名规范
- 每维 0/1/2 分，上限 20 分
- 场景级判定阈值：≥ 14 / 20（约 70%）；任一维度 0 分降级为 reject

**总判定（advisory）**：场景级 reject ∪ 节点级接受率 < 70% → 判官标 reject；否则 accept。

**关键约束**：判官输出**仅作辅助参考分**，不进入接受率分子（§6 / §8）。

---

## §5 机械失败口径

七类机械检查；任一不通过即场景未进入 review_log（不计入接受率分母 §6）。由 T-2.4 `/validator/dialogue_validator.py` 实现。

| 编号 | 检查项 | 规则 | 来源 |
|---|---|---|---|
| **M1** | option 长度 | option.text ≤ 25 汉字（按 unicode 计数；中英文混排按 0.5 字符折算英文）| 阶段 1 R3 → ADR-020 |
| **M2** | path 前缀 | 所有 effect.path / condition.path 必须落入 ADR-016 定义的五个命名空间之一：`world.*` / `faction.<faction_id>.*` / `relationship.<state_path_slug>.*` / `flag.*` / `player.*` | ADR-016 |
| **M3** | bond ID 白名单（**state_path_slug 反查**）| 出现在 `relationship.<X>.*` 中的 `<X>` 必须能反查到本体某 character entity 的 `state_path_slug` 字段值（不是 entity.id；保 gold scene `relationship.vellin.trust` 不动）| ADR-016 §state_path_slug + ADR-020 |
| **M4** | target_node_id 闭合 | 所有 option.target_node_id 必须指向本图内已存在的 node_id；entry 节点入度 = 0；end 节点 type=end | T-2.7 / ADR-021 §2A 部分前移 |
| **M5** | unavailable_behavior 枚举 | option.unavailable_behavior 字段值必须 ∈ schema 枚举（如 `disable_with_hint` / `hide`）；不允许自由文本 | ADR-020 |
| **M6** | state path 命名空间合法性 | 与 M2 同源；**M2 检查前缀是否合规，M6 检查 path 整体不出现非五命名空间字段**（如禁止裸 `npc.foo.bar`）| ADR-016 |
| **M7** | StateCondition 形态互斥 | 同一 condition 节点不得既含 leaf 字段（`op` / `path` / `value`）又含复合字段（`all_of` / `any_of`）；阶段 1 R2 复合 condition 模型常误为 string-array 教训 | 阶段 1 R2 → ADR-020 |

**机械检查执行顺序**：M4 → M2/M6 → M3 → M1 → M5 → M7（轻量结构 → 命名空间 → 引用闭合 → 文本约束 → 枚举/形态）。

**输出**：`gross_pass: bool` + 失败时附 `failure_codes: ["M3", "M5"]` 列表。

---

## §6 接受率分子 / 分母

**分母 = 通过机械预检（§5 全过）+ 进入 review_log 的场景数**

- 机械预检失败的场景**不进入分母**（计入 §9 gross pass rate 的失败侧）
- `generation_failed`（§3）的场景**不进入分母**
- 进入 review_log 后作者无论标 [A]/[R]/[S] 都记入分母（含 [S]kip — skip 算 reject 侧分子不加）

**分子 = 作者最终标 [A]ccept 的场景数**

- 不是 AI 判官打分（判官打分作 advisory，详 §4 / §8）
- [S]kip 算未达 accept 标准，等同于 reject 侧

**接受率 = 分子 / 分母**（场景级；非节点级）。

**与阶段 1 接受率定义的差异**：阶段 1 同样以"作者标 [A]"为分子（R6 教训锁定）；阶段 1 因带宽授权改为"AI 判官替代人工"。阶段 2 不再使用替代——见 §8。

---

## §7 阶段 2 完成判定

**N=15 场景接受率 ≥ 70%**（即 ≥ 11 / 15）→ 阶段 2 baseline 完成判定通过。

判定输入清单（T-2.13 验收报告）：
1. §6 接受率：分子 / 分母 / 比率
2. §9 gross pass rate：通过机械预检的场景数 / 总尝试场景数
3. §4 判官 advisory 数据：节点级 21 维聚合表 + 场景级 10 维均分表（不影响 §7 判定，仅作分析）
4. §5 机械失败 top reason 表（按 M1–M7 编号统计）
5. §3 `generation_failed` 场景列表 + 失败原因分类

**接受率介于 60%–70% 边界带**：T-2.13 可申请补 5 个场景上 N=20 再判定（不强制；作者权衡）。

**接受率 < 60%**：本 baseline 失败；回 prompt 调优（T-2.5 改）+ 本体调优（T-2.2 增补）+ 重跑。

---

## §8 与阶段 1 R6 的关系

**阶段 1 R6**：因审阅带宽，作者授权 AI 判官（21 维 prompt）替代"人工审阅"作为接受率分子；该决策记入 STAGE_1_ACCEPTANCE §4 R6，标记"阶段 4 上线后接入真用户反馈校准"。

**阶段 2 不复用 R6 替代**：

- 阶段 2 baseline N=15 场景作者亲手标 [A]/[R]/[S]——审阅带宽可承担（每场景 ~5–10 min × 15 场景 ≈ 1–2.5 小时）
- AI 判官（本协议配套 `REVIEW_PROMPT_AI_JUDGE_SCENE.md`）提供**辅助 advisory 分**：作者审阅时先看判官评分作锚，再亲眼过原文最终拍板
- §6 分子明确定义 = "作者标 [A]"；判官分**不进分子**

**为什么不沿用 R6**：
- 阶段 1 是节点级 17 条，每条平均 200 字；阶段 2 是场景级 15 条，每条平均 5–15 节点 × 200 字 = 1000–3000 字——单场景审阅成本上升 5–15 倍，但总条数下降到 15 条，**总审阅时间反而可承担**
- 阶段 2 引入本体（ADR-016）/ 时钟（ADR-017）/ 关系层（ADR-018）等**作者本人作主编**才能拍板的语义维度；AI 判官在这些维度上无足够 grounding（参考 STAGE_1_ACCEPTANCE §4 R8：判官在可数值化维度系统性放水 ⇒ 在主编语义维度更可疑）
- 阶段 4 真用户反馈仍是终极校准；阶段 2 选作者亲审是**对 R6 替代的最严回归**

---

## §9 报告口径（v1.0 新增；critique §10 weakness 2）

每次 batch 报告（T-2.12 输出 + T-2.13 验收报告）必须**同时给两条比率**：

- **gross pass rate**（机械预检通过率）= 通过 §5 全套机械预检的场景数 / **总尝试场景数**（含 `generation_failed`）
- **人工接受率**（作者签字接受率）= 作者标 [A] 的场景数 / **进入 review_log 的场景数**（即 §6 分母）

**两者关系示意**：

```
总尝试 N=15
├── generation_failed (3 次都重试失败)         → 不进 gross pass 分子；不进 review_log
├── 机械预检失败 (gross_pass=false)            → 不进 gross pass 分子；不进 review_log
└── 机械预检通过 + 进 review_log               → 进 gross pass 分子；进接受率分母
    ├── 作者 [A]ccept                          → 进接受率分子
    ├── 作者 [R]eject                          → 不进接受率分子
    └── 作者 [S]kip                            → 不进接受率分子
```

**为什么必须双报**：
- 单报接受率会掩盖 prompt / schema / generator 失败的"假高分"（如机械预检过的 5 场景全 accept = 100%，但总尝试 15 场景 ⇒ 真实质量 33%）
- gross pass rate 可定位失败侧重点（schema 失败 vs 机械失败 vs 生成失败）
- 阶段 2 §7 判定线（70%）依据 **接受率**（更严苛侧）；gross pass 仅作诊断

**输出位置**：T-2.12 `scene_metrics.py` 输出 `metrics.json` 含两条字段；T-2.13 验收报告含两条数字 + 关系图。

---

## §10 成本估算口径（v1.0 新增；critique 5.2）

**每场景成本估算**：~$0.5–$1.0

- 单节点 ~$0.03–$0.05（阶段 1 baseline_004 实测）
- 单场景 5–15 节点 ⇒ ~$0.15–$0.75（不含重试）
- 加 max_retries=2 重试预算（部分场景）+ context 注入开销 ⇒ 上修到 $0.5–$1.0 区间

**N=15 总盘子**：$7–$15
**N=20 总盘子（如补样）**：$10–$20

**预算治理**：
- T-2.12 `scene_experiment.py` 启动前必须 `image_budget` 等价的文本 budget pre-check（ADR-012）
- 每场景调用前 `budget.check_and_charge()` 拦一次；超额抛 `BudgetExceeded`
- 单 batch 软上限建议设为协议估算值的 1.5×（即 N=15 给 $22.5 预算缓冲）

**注**：上述估算基于 Gemini 3.1 Pro Preview 单价；如阶段 2 中途换模型（ADR-011 LLMProvider 接口允许），需重估并 v0.2 修订本节。

---

## §11 协议变更历史

- **v1**（2026-05-04）：T-2.9 创建。承接 ADR-020 全集 + critique 5.2 / §10 weakness 2 修订（成本口径统一 + 双报口径）。

## §12 引用关系

| 引用方向 | 文档 | 引用内容 |
|---|---|---|
| 本文件 → | [ADR-020](../../docs/DECISIONS.md) | 决策来源 |
| 本文件 → | [ADR-016](../../docs/DECISIONS.md) | state path 命名空间 + state_path_slug |
| 本文件 → | [ADR-013](../../docs/DECISIONS.md) | max_retries=2 |
| 本文件 → | [ADR-021](../../docs/DECISIONS.md) | 2A 部分前移到 M4 闭合 |
| 本文件 → | [REVIEW_PROMPT_AI_JUDGE_SCENE.md](../prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md) | §4 维度落地 |
| → 本文件 | T-2.4 (dialogue_validator) | §5 机械失败口径 |
| → 本文件 | T-2.8 (scene_ai_judge) | §4 判官权重 |
| → 本文件 | T-2.12 (scene_experiment) | §2 N=15 + §3 重试 + §9 双报 + §10 预算 |
| → 本文件 | T-2.13 (验收报告) | §6 分子分母 + §7 完成判定 + §9 双报 |
