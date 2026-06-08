# 决策：结构层采纳"分拍节点图"为默认（2026-06-08）

> 正式记录 = `/docs/DECISIONS.md` **ADR-038**（作者明确授权的规则 10 例外）。
> 本文件是 `/generator` 内的同步设计 note（边界内、便于生成器开发者就近查阅）。

## 决策
1. **node 定义** = 一个玩家面对的对话节拍（NPC 文本 + ≥1 个玩家回应）。**分叉是某些节点的属性，不是节点的定义**；单选项节点（"继续"/短追问）合法且必要，用于铺陈。
2. **结构层产分拍节点图**：**choice 节点**（多选项决策点）+ **单选项 beat 链**（信息密集自动分拍成 2-3 拍，露西说一点→玩家接一句→再说一点）。
3. **路径/路线 = 涌现**（`option.target_node_id` → 节点链），不另立 schema 概念。
4. **schema 不变** —— `node.schema.json` 已支持：`type=dialogue ⇒ options minItems:1`（单选项合法），旁白 = `speaker_ref=null`。原型里"固定 4 节点 / 每节点 ≥3 选项"是 generator 原型 + 实验 DOC 的脚手架，非 schema 约束。

## 证据（generator/experiments/multipass_structure/）
- **N3 分拍样例**：`2026-06-08_n3_paced_sample/sample.md`（7 句一锅端 → 3 个单选项节拍）。
- **露西全场 v1**：`2026-06-08_lucy_paced_scene/scene.md`（开场 + 枢纽 choice 节点 + 软/硬各 3 拍；7 调用 / $0.18 / 3.4 min）。

## v1 边界 + follow-up（如实）
- v1 拓扑**半固定脚手架**（`multipass_paced_lucy.py`：开场 → 枢纽 → 两分支 → end），用已验证 call 类型规避中转站超时。**完全动态拓扑（LLM 自决节点数/结构）= 后续 refinement。**
- 选项第一人称：beat 选项已去冗余"我"（"楼下是谁？"）；choice 节点选项仍带"我" → 全面统一是 **Phase 2 文风/约定层**（与 AP-8 反模式规则联动）。
- 把 beat-pacing 正式固化进 generator 正式管线（替换/并存 `system.py` 单 pass）= follow-up。
- 扩多场景复核接受率 = follow-up。

## 相关代码
- `generator/prompts/node/multipass/beat_pacing.py` —— 节拍编排 prompt（瘦身 AP + role rules + 第一人称隐含选项）。
- `generator/scripts/pace_n3_sample.py` —— N3 分拍样例。
- `generator/scripts/multipass_paced_lucy.py` —— v1 全场分拍引擎。
