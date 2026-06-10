# Handoff 草稿 · 收敛路由 × 静态文本盲点修复（复核根因①⑥）

> 给一个**全新会话**的自包含任务书草稿。由作者移交/改写后使用（本文件在 /generator 边界内起草；
> 正式 handoff 位置按惯例为 /docs/handoffs/，由作者或规划师会话落位）。
> 性质：触及拓扑/骨架 prompt 与引擎编排 = 软地基 → 按 ADR-037 **设计先行**。

## 0. 开始前
读 `CLAUDE.md` + `generator/CLAUDE.md`，acknowledge 三条最相关规则再动手。

## 1. 背景
结构层正式引擎（`generator/multipass/`，多 pass + 分拍 + 动态拓扑）已于 2026-06-10 落地并通过
多场景复核（6/6 硬校验；接受率见 `2026-06-10_review/REVIEW_REPORT.md`）。复核定位出一个
未修的系统性根因（报告 §2 第 1、6 项）：

**拓扑出边数 < 骨架选项数（3-5）时，语义不同的选项收敛到同一条后续链；链首拍不知道玩家
实际选了哪句话。**后果分级：
- 轻：choice pressure 稀释（多个选项得到完全相同的后续文本）——lucy/c1 corner_assess 5→2。
- 重：**答非所问**——vick/c1 开场选项 4（"有人介绍我谈隐秘收购"）/ 选项 5（"听说对家出价"）
  都没提莱特，但收敛到的链首拍回应"莱特教授当然认识"（实证见
  `2026-06-10_review/vick/candidate_1/scene.md` business_entry_b1 / sharp_name_test_b1）。
- 伴生：分支功能重合 → 跨分支信息近原文复制（vick/c2 open_business vs rival_bid）。

## 2. 先读
- `generator/experiments/multipass_structure/2026-06-10_review/REVIEW_REPORT.md`（§2 根因清单）
- `generator/experiments/multipass_structure/2026-06-10_review/prescreen/vick_c1.md` + `vick_c2.md`
- `generator/multipass/{engine,topology}.py` + `generator/prompts/node/multipass/{topology,pass1_skeleton,beat_pacing}.py`
- `generator/experiments/multipass_structure/DESIGN_2026-06-10_formal_landing.md`

## 3. 候选修复方向（设计时取舍，非全做）
1. **拓扑层**：topology prompt 要求"出边数 = 真实分歧数"；choice 节点声明每条出边的预期选项数；
   校验器（`generator/multipass/topology.py`）可加软警告。
2. **骨架层**：routes=2 时放宽 `build_dynamic_node_schema` 最少选项至 2（schema 不改，
   node.schema.json 本就允许 minItems:1）。
3. **链首拍收敛安全**：beats / 子 choice 的首拍 prompt 注入"可能的入口姿态/选项文本清单"，
   要求开头对所有入口成立（不预设玩家说过什么）。
4. **跨分支去重**：分拍 prompt 已有历史压缩；对"平行分支"（非祖先关系）补充
   "其他分支已用措辞"清单，要求改变完整度与措辞。

## 4. 硬约束（沿用 2026-06-08 handoff）
只在 `/generator`；schema/validator/engine/state 不动；LLM 走 `LLMProvider` + budget；
中转站 `prompt_only` + 小调用（est_output_tokens ≤ 2000 护栏已在 `generator/multipass/calls.py`）。

## 5. 验收建议
- 单元测试全绿 + 边界 grep 0 匹配。
- 真跑验证：vick spec（`specs/vick.json`）× 2 候选——链首拍无答非所问（人工读开场两跳）、
  收敛选项有差异化处理、平行分支无近原文复制；成本预估 ~$0.9。
- 顺带回归：lucy spec × 1 确认无劣化。

## 6. 范围红线
只动结构层。文风/审美（Phase 2）与 validator 检测器调参（AP-7 引号内 span 排除等，
报告 §2 第 7 项）不在本任务，后者需作者单独授权。
