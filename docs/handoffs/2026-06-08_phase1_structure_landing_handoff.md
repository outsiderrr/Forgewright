# Handoff · 结构层"正式落地"——多 pass + 分拍引擎并入 generator 正式管线

> 给一个**全新会话**的自包含任务书。无本次讨论记忆,所需上下文全在下面。
> 性质:**软地基改动**(触及 generator 生产管线 + `system.py` 契约 + 测试)→ 按 ADR-037 **设计先行**:先出方案给作者过目,再施工。

## 0. 开始前(CLAUDE.md 规则 1)
你在 Forgewright 仓库工作。**先读** `CLAUDE.md` + `generator/CLAUDE.md`,按规则 1 acknowledge 并总结对本任务最相关的 3 条规则,再动手。

## 1. 背景(self-contained)
Forgewright = AI 辅助分支叙事内容生产流水线(开发期生成 CRPG 对话图;运行时无 LLM)。
2026-06-08 一条 Phase 1(结构层)原型会话已**验证并经作者采纳**两件事(见 `docs/DECISIONS.md` **ADR-038**):
- **多 pass 生成**(plan-compose-write:骨架 → 逐节点正文 + 历史压缩 + 瘦身文风)比单一大 prompt 改善结构(§9 均值 2.40→2.85,结构子集 +0.75)。
- **分拍节点图**:node = 一个对话节拍(NPC 文本 + ≥1 个玩家回应);**choice 节点**(多选项决策点)+ **单选项 beat 链**(信息密集自动分拍);schema 不变(`node.schema.json` 已支持单选项)。

但这些目前只是**隔离原型**(`generator/prompts/node/multipass/` + `generator/scripts/*`),**没并入 generator 正式管线**。本任务 = 把它正式落地。

## 2. 先读这些(都在仓库)
- `generator/experiments/multipass_structure/FINDINGS.md` —— Phase 1 原型结论 + delta + caveat。
- `generator/experiments/multipass_structure/DECISION_paced_nodes.md` + `docs/DECISIONS.md` ADR-038 —— 决策原文。
- `generator/prompts/node/multipass/{__init__,pass1_skeleton,pass2_prose,beat_pacing}.py` —— 原型 prompt 模块。
- `generator/scripts/{multipass_lucy_dry_run,multipass_paced_lucy,pace_n3_sample}.py` —— 原型 runner(看实际接法)。
- `generator/prompts/node/system.py` —— **现有单 pass 节点生成器**(本任务要替换/并存的对象)。
- `schema/node.schema.json` —— node 模型(`type=dialogue ⇒ options minItems:1`;旁白 = `speaker_ref=null`)。**不要改 schema**(ADR-038 已确认无需改)。
- `validator/anti_pattern_detector.py` —— AP-7/8/10 程序化检测(瘦身的兜底)。

## 3. 任务(设计先行 → 作者过方案 → 再施工)
**先出设计**(pass 接口 / 如何并入正式管线 / 如何处置 system.py 契约与测试),作者点头再写代码。要解决这 5 项:
1. 把多 pass + 分拍引擎**并入 generator 正式管线**(替换 or 并存 `system.py` 单 pass)。
2. 正式从 `system.py`(+ `anti_pattern_blacklist` + `role_rules` 3b)移除 AP-7/8/10,**更新它们的测试**(`test_prompts_node.py` 现在 assert 10 条全在)。
3. provider 层**大结构生成超时**应对:中转站(new-api + gpt-5.5)对复杂大单次生成**持续 502**;原型靠"逐节点 / 逐拍拆分 + `prompt_only`"规避。把这个固化为正式架构,或在 provider/调度层处理。
4. **完全动态拓扑**:让结构层按场景自决节点数/类型/分支(原型 v1 是半固定脚手架:开场→枢纽→两分支→end)。⚠️ **超时高风险点**(一次规划整张图),要小心拆调用。可作为本任务一部分,也可拆出去——由你的设计 + 作者定。
5. **多场景 × 多候选复核**:现在只 n=1(露西)。扩到 2-3 候选 + 多场景,测接受率,再定稿。

## 4. 硬约束
- **只在 `/generator`**(含 generator 下的测试);schema 不改(ADR-038);不碰 `/engine` `/state`。validator 默认不改——若第 2 项瘦身要动 validator,停下报告作者。
- LLM 调用走 `LLMProvider` + `budget.check_and_charge()`(ADR-011/012),不直接 import SDK;调试脚本也过 budget。
- **中转站现实**:`.env` 配 `LLM_API_KEY` / `LLM_BASE_URL`(`http://api.key77qiqi.com/v1`)/ `LLM_MODEL`(`gpt-5.5`);`json_mode` 用 **`prompt_only`**(`json_object`/`json_schema` 在大请求上会 502);大单次生成会超时,必须拆小。
- **软地基纪律(ADR-037)**:本任务改 `system.py` 生成契约 + 测试 = 软地基,**设计先行、作者过方案再施工**;别在没设计的情况下直接改定型代码。

## 5. 交付物
1. 设计说明(管线并入方式 / system.py 契约处置 / 超时架构 / 动态拓扑取舍)+ 作者批准。
2. 落地代码(多 pass + 分拍成为正式生成路径)+ 测试全绿 + 边界自检(`grep -R "from generator" engine/ state/ schema/ validator/` 无匹配)。
3. 多场景复核结果(接受率)。
4. 一句话:结构层是否可判定"生产就绪"。

## 6. 范围红线
本任务**只动结构层**。文风/质感(选项"我"统一、审美锚点、反 AI 腔预设)= **Phase 2**,别在这做。
