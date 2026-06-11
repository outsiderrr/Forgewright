# 设计：多 pass + 分拍引擎并入 generator 正式管线（Phase 1 结构层落地）

> 状态：**待作者批准**（ADR-037 设计先行；批准前不动任何定型代码）
> 任务书：`docs/handoffs/2026-06-08_phase1_structure_landing_handoff.md`
> 依据：ADR-038（分拍节点图）+ `FINDINGS.md`（多 pass +0.45 / 结构子集 +0.75）+ `DECISION_paced_nodes.md`

## 0. 目标（一句话）

把已验证的多 pass + 分拍原型变成 generator 的**正式结构层生成路径**：
场景 spec（JSON）进 → **通过 validator 的分拍对话图** + **作者可审的剧本 markdown** + 客观指标出。

## 1. 总体形态

新增 `generator/multipass/` 引擎包，prompt 沿用 `generator/prompts/node/multipass/`（脱离"原型"状态，docstring 更新）。

```
generator/multipass/
  calls.py      # 小调用 helper（budget 拦截 → provider → 对账/退款；从脚本 _one_call 正式化）
  topology.py   # 拓扑规划 pass（动态拓扑；含确定性结构校验 + 回退）
  engine.py     # run_multipass_scene()：编排全部 pass
  assemble.py   # 确定性组装（0 LLM）：拼成合法 dialogue_graph JSON
  render.py     # 剧本式 markdown 渲染（作者审阅形态）
  tests/
```

管线（每场景一次运行，**全部是已验证的小调用类型**）：

```
scene_spec
  → ① 场景契约 pass（1 次小调用）
  → ② 拓扑规划 pass（1 次小调用；LLM 自决节点数/类型/接线；见 §6）
  → ③ 逐 choice 节点骨架 pass（每节点 1 次；带历史压缩）
  → ④ 逐 choice 节点正文 pass（每节点 1 次）
  → ⑤ 逐 beat 链分拍 pass（每链 1 次；reveals > 4 自动分块）
  → ⑥ 确定性组装（0 LLM）：node_id / option_id / target_node_id 接线、
       机械字段默认值（condition=null、effects=[] 等）全由代码填——LLM 不写状态（架构共识 2）
  → ⑦ validator：schema + mechanical + AP-7/8/10 程序化检测（flag 记录进结果，不再进 prompt）
  → 产物：scene.json（合法图）+ design.json（契约/拓扑/骨架 sidecar）
        + scene.md（剧本式渲染）+ metrics.json（客观指标 + 成本）
```

一次 8–12 节点的场景 ≈ 10–12 次调用 / $0.30–0.45 / ~5 分钟。

## 2. handoff 五项任务的处置总表

| # | 任务 | 处置 |
|---|---|---|
| 1 | 并入正式管线 | §1 新引擎包；system.py 并存（§3） |
| 2 | AP-7/8/10 prompt 移除 + 测试 | §4 |
| 3 | 大结构生成超时应对 | §5 调用粒度架构化 |
| 4 | 完全动态拓扑 | §6 推荐入本任务（小调用拓扑规划 pass）——作者拍板 |
| 5 | 多场景 × 多候选复核 | §7 |

## 3. system.py 单 pass 契约处置：**并存**（推荐）

- `system.py` / `node_text_gen`（T-3Y-1）的职责 = "给定**已有**骨架 + Forward Planner 输出，填单节点正文"——与多 pass 引擎（从场景 spec **设计 + 写**全场）是**不同工位**；T-3Y-1 六阶段工作流仍依赖它。
- 处置：保留，prompt 同步瘦身（§4），docstring 标注"结构层默认生成路径 = generator/multipass"。
- 否决"替换/删除"：会连根拔起 forward_planner 工作流（项目级赌注第一个正向数据点），且"修补/重写单个节点正文"的场景将来仍需要这个工位。

## 4. AP-7/8/10 从生成 prompt 全移除（单一真相源原则不变）

- `anti_pattern_blacklist.py`：canonical prompt 文本改为 **7 条**（AP-1~6 + AP-9），**编号不变不重排**；模块 docstring 指明 AP-7/8/10 的唯一归宿 = `validator/anti_pattern_detector.py`。
- `system.py`：拼接 7 条版；删掉 OUTPUT_FORMAT_SPEC 里"（违反 AP-7）/（违反 AP-8）"点名（保留角色契约的结构性表述——"NPC 的话由 NPC 自己说"是结构规则，不是文风黑名单）。
- `role_rules.py` 3b：删去与 AP-8 重复的反例行；保留"第一人称"正向契约。
- `pass2_prose.py` / `beat_pacing.py`：直接用 7 条版；`slimmed_anti_patterns()` 过滤器退役（canonical 已是 7 条，无需再过滤）。
- 测试更新：`test_prompts_node.py` 改 assert 7 条在 + **AP-7/8/10 不在**；新增回归测试"AP-7/8/10 文本不出现在任何生成 prompt"。multipass 测试同步。
- **validator 零改动**（detect_ap7/8/10 及其测试已存在）。

## 5. 超时应对 = 调用粒度架构化（不是 provider 补丁）

- 原则固化：引擎只发 **5 种已验证小调用**（契约 / 拓扑 / 单节点骨架 / 单节点正文 / 单 beat 链），架构上不存在"一次设计整图"的大调用。
- `calls.py` 加护栏：`est_output_tokens` 超上限（暂定 2000）直接报错"拆小"，不让注定 502 的请求出门耗 751 秒。
- 失败语义沿用原型：budget 先充后对账，ProviderError 全额退款再抛。
- json_mode 默认 `prompt_only`（读 `.env` LLM_JSON_MODE），与中转站现实一致。

## 6. 动态拓扑：推荐入本任务（作者拍板）

- 形态：② = **1 次小调用**，输出只有结构骨架 JSON——每个节点的 id / 类型（choice｜beat 链｜end）/ 一句话功能 / 接线 / 每链线索预算，**不含任何正文**。输出尺寸与契约 pass 同级（数百 token），不触发大请求超时。
- 确定性校验（0 LLM）：单入口、全可达、≥1 个 end、beat 链线性、choice 节点 3–5 选项、节点总数上限 12（对齐 v2.2 复杂度）。不合法重试 ≤2 次，仍失败**回退半固定脚手架**（v1 形状），结果里如实记 fallback。
- 不做的代价：多场景复核就是把"露西形状"的脚手架往所有场景上套，接受率测不出真东西。
- 风险缓释：这是唯一未实测过中转站的 call 类型 → 全量复核前先单独 smoke 1 次（~$0.03）。

## 7. 多场景 × 多候选复核

- 场景：露西（对照）+ **2 个新场景**（从 Crimson Letters A1 dry-run NPC 卡起草 spec；**spec 先给作者过目，再花钱生成**）。
- 候选：每场景 2 个（同 spec 重跑）= 共 6 次运行；预估总成本 **~$2–3**。
- 测量：① validator 硬通过率（schema + mechanical）② AP-7/8/10 flag 数 ③ 结构客观指标（narration 字数 / intent 重叠 / 每拍 reveal 数）④ 作者审 6 份剧本 markdown → 接受率。
- 定稿判据（建议）：硬通过 6/6 **且** 作者接受 ≥ 4/6（≈70%，对齐阶段 2 gross_pass_rate 先例）→ 结构层判"生产就绪"；否则如实列 gap。

## 8. 边界自检承诺

只动 `/generator`（含其测试）；`/schema` `/engine` `/state` `/validator` 零改动；
`grep -R "from generator" engine/ state/ schema/ validator/` 无匹配；pytest 全绿。

## 9. 施工顺序（批准后）

1. prompts 瘦身 + 测试更新 + `calls.py`（纯本地，0 API 消耗）
2. topology / engine / assemble / render + 单元测试（mock provider，0 API 消耗）
3. 露西 smoke 真跑 1 次（~$0.40）→ 剧本 markdown 给作者过目
4. 2 个新场景 spec → 作者过目 → 6 次复核 → 接受率报告 + 生产就绪一句话判定
