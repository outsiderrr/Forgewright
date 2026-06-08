# Phase 1 · design-first 多 pass 引擎（结构层）原型 + 测量 — 交付

> 任务书：`docs/handoffs/2026-06-08_phase1_structure_engine_handoff.md`
> 日期：2026-06-08　模型：`gpt-5.5`（new-api 中转，与 baseline 同模型）
> 对照 baseline：`docs/experiments/design_first_node/2026-06-02_lucy_candidate_api_gpt55.md`
> 多 pass 产出：`generator/experiments/multipass_structure/2026-06-08_lucy_multipass/`

## 一句话结论

> **多 pass 值得正式落进 generator。** 同模型、同场景、单候选下，它把结构类四个 2 分维度
> 全抬到 3（结构子集 **+0.75**，§9 总均值 **2.40 → 2.85，+0.45**），客观指标（narration 字数翻倍、
> N1↔N2 选项重叠归零、N1 不再过早泄露）全部正向。**唯一附带条件**：中转站把"一次设计 4 节点"
> 逼成 9 次调用（见下"相对真相"），正式落地要先解决大结构单次生成超时。

## 1. ① baseline + 多 pass 后分 + delta（§9 rubric，0–3）

| 维度 | baseline | 多 pass | Δ | 依据 |
|---|---|---|---|---|
| 场景契约 | 3 | 3 | = | 都强（多 pass 的 npc_goal/fear 更厚，但 baseline 已满）。 |
| **互动结构** | 2 | **3** | **+1** | N1↔N2 选项 intent 重叠 **0**（客观），4 功能清晰分化，N1 的 `hides` 显式拦截深层线索。 |
| **choice pressure** | 2 | **3** | **+1** | 每选项 intent/payoff/cost/relationship_delta 完整；选项是策略姿态而非清单标签。 |
| 选项文本 | 3 | 3 | = | 都第一人称、可说出口。 |
| **露西心理** | 2 | **3** | **+1** | trust/fear/cooperability/affinity 四维变化 + 逐条理由。 |
| 线索分层 | 3 | 3 | = | 都强；多 pass N4 显式枚举残缺/隐藏，略更清楚。 |
| **narration 功能** | 2 | **3** | **+1** | 均值 **274 字**（baseline ~150 贴下限），每句仍承担功能、无注水。 |
| 异常线索 | 3 | 3 | = | "外面二十步宽、里面多四步" 由露西说、可复核；N4 正确隐藏。 |
| 信息归属 | 2 | 2.5 | +0.5 | 关键信息基本在露西对白引号内；N3 narration 有 1 处 "她说话时…" 被 validator AP-7 抓到。 |
| 文风（白描） | 2 | 2.5 | +0.5 | 白描更厚更稳、少判断；个别轻微推断。 |
| **平均** | **2.40** | **2.85** | **+0.45** | |

**结构类子集**（互动结构 / choice pressure / 线索分层 / narration）：**2.25 → 3.00（+0.75）**。
§11 decision gate（均值≥2、choice≥2、narration≥2、线索分层≥2）：多 pass 全部**轻松通过**。

### 结构类客观指标（脚本自动算，非主观）

| 指标 | baseline | 多 pass |
|---|---|---|
| narration 均值字数 | ~150（贴 150 下限） | **274**（N1 293 / N2 247 / N3 271 / N4 287） |
| N1↔N2 选项 intent 重叠 | 近乎全部（同一套 5 选项） | **0** |
| N1 是否过早泄露小屋/铁盒 | 是 | 否（`hides` 显式拦截） |
| validator AP-7/8/10 flag | （baseline 为 markdown，未程序化测） | **1**（N3，validator 兜住） |

## 2. ② 多 pass 拆分设计（实际落地形态）

design-first 从"一个大 prompt"拆成 **plan-compose-write**（参考 StoryWriter）：

- **Pass 1a — 场景契约**（1 次）：只产 Scene Contract。
- **Pass 1b — 逐节点骨架**（4 次）：每次只设计 1 个节点的 Interaction Skeleton；
  喂入"前序节点的功能 + 已揭露线索 + 已用选项角度" → **强制功能分化 + 线索分层**。
  4 个节点功能由 `NODE_FUNCTIONS` 预定（handoff §3② 已规定，省掉模型现想 4 功能的重推理）。
  **只带结构规则，0 条文风/AP**。
- **Pass 2 — 逐节点正文**（4 次）：把骨架当固定输入，写 narration + 露西对白 + 玩家第一人称选项；
  带**历史压缩**（祖先节点已揭露线索 + 已用选项角度，N3/N4 互不串味），**带瘦身后文风规则**。

> 注：原设计是 **1 次骨架 + 4 次正文 = 5 次**（方案 B）。中转站把"一次出 4 节点"逼成超时
> （见 §4），故 Pass 1 进一步拆成 contract + 逐节点 = **9 次**。逐节点骨架反而让功能分化更强，
> 是"被逼出来的正向副作用"。

代码：`generator/prompts/node/multipass/{pass1_skeleton,pass2_prose}.py` +
`generator/scripts/multipass_lucy_dry_run.py`（隔离原型，**未动** system.py/anti_pattern_blacklist.py/role_rules.py）。

## 3. ③ prompt 瘦身 diff

| | baseline / 现有 system.py 合成 prompt | 多 pass 后 |
|---|---|---|
| AP-7/8/10 | 在 prompt（system.py 点名 AP-7/8 + anti_pattern_blacklist 全 10 条），又被 validator 程序化抓 | **生成 prompt 里全部移除**（validator 兜底；本次实测兜住 1 处 AP-7） |
| AP-8 重复 | 3 处（anti_pattern_blacklist + system.py + role_rules 3b） | **0 处** |
| Pass 1 骨架 | — | **0 条 AP**（结构层不需要文风黑名单） |
| Pass 2 正文 | — | **AP-1~6 + AP-9（7 条）** + role_rules 三契约 |

瘦身用"过滤 canonical 黑名单"实现（`slimmed_anti_patterns()`，单一真相源、不复制粘贴）。

## 4. 相对真相 / caveat（务必连同结论一起看）

1. **n=1**：单候选。§10 建议 2-3 候选；本次按"1 sample 通过再扩全集"先取信号。结论是"值得，且应扩样/扩场景复核"，不是"已证毕"。
2. **delta 把"多 pass 结构"和"我重写的 prompt"绑在一起**——二者是同一个干预（多 pass 就是这套重写），可归因于"多 pass 方法整体"，但不能拆出"纯拆分 vs 纯改 prompt"各占多少。
3. **中转站逼出的 9 次拆分**：new-api + gpt-5.5 对"一次设计 4 节点的大结构"**持续 502**（实测大请求 751s 重试后放弃；tiny/中等请求 3–35s 正常）。根因 = 复杂大输出耗时 > 上游网关超时。正式落地要么换不超时的 provider，要么把逐节点拆分固化为正式架构。
4. **成本/时延**：本场景 **$0.2643 / 4.6 分钟 / 9 次调用**（中转站每次附带 ~6000-9000 token 固定输入开销）。baseline 是单次调用。规模化时这是真实代价。
5. 之前 3 次 502 失败**全额退款（$0）**；本任务今日实际花费 ≈ **$0.36**（正式跑 $0.26 + 诊断探测 ~$0.10）。

## 5. 建议的正式落改（信号正向后，单独立项给作者）

- 把"逐节点骨架 + 逐节点正文 + 历史压缩"固化进 generator 正式管线（替换/并存于现有 system.py 单 pass）。
- 把 system.py / anti_pattern_blacklist / role_rules 的 AP-7/8/10 正式移除 + 更新其测试（本原型未动它们）。
- provider 层加"大结构生成超时"的应对（换 provider 或强制逐节点）。
- 扩到 2-3 候选 + 多场景复核接受率，再定稿。
