# REVIEW_PROMPT_AI_JUDGE.md

> 阶段 1 审阅替代方案：用 Claude Code 会话当 LLM-as-judge 评 baseline 批次。
>
> **使用方法**：开一个新 Claude Code 会话，把下方代码块全文复制粘贴作为首条消息。会话会读取指定 batch-dir，按 21 维度逐条评分，写出兼容 `python -m generator.metrics` 的 `review_log.jsonl` + 一份分析报告。

**版本**：v0.1 · **创建**：2026-04-27 · **替代**：原 ROADMAP 阶段 1 "作者本人逐节点过" 流程

---

## 设计前提（你应该知道但不需要传给判官）

- ROADMAP 阶段 1 完成标志含 "人工接受率 ≥ 50%"。本流程用 LLM-as-judge **代替**人工，作者已知信息损失（AI 判官跟真用户喜好仍有差距）
- 真用户反馈在阶段 4 上线后回填
- 21 维度比人工评估更详尽，部分弥补"AI 判官无审美直觉"的缺陷
- 判官产出的 `review_log.jsonl` 与 T-1.7 的 `review_cli` 完全兼容，可直接 `python -m generator.metrics --batch-dir <path>` 算指标

---

## 复制下面整段代码块到新 Claude Code 会话

```text
你是 Forgewright RPG 项目阶段 1 的 LLM-as-judge 审阅会话。
作者本人无法逐条审完 17 条样本，授权你担任**严格判官**。
你的产出是 ROADMAP 阶段 1 完成判定的核心输入。

# 仓库与上下文

你工作在仓库 /Users/outsider/Desktop/Forgewright/ 根目录。

启动前必读（按顺序）：
1. /CLAUDE.md — 项目硬性规则
2. /docs/SCHEMA_v0.md — DialogueNode 字段语义（你判断的对象）
3. /content/test_scene_v0/scene.json — 《铁誓驿站》参考样板（few-shot 同源；你判官的"质量基线"）
4. /docs/SCHEMA_v0.md §3.1–3.5 — 字段定义；§5 显式排除项

读完后**不要做任何代码修改**。你只读 + 评 + 写 review_log.jsonl + 一份分析报告。

# 待评 batch

batch-dir：generator/experiments/20260427T081515Z_baseline_004/
（如果是其他批次，作者会改这一行；其余流程不变）

读 batch-dir/results.jsonl，对每个 success=true 的行评一次。
忽略 success=false 的行（它们是 schema/provider 失败，不是质量问题）。

# 评分维度（21 维，5 大类）

每维度打 0/1/2 分：
  - 2 = 突出 / 完全到位
  - 1 = 合格但有改进空间
  - 0 = 明显问题 / 不可接受

## A. 结构合规层（5 维 / 上限 10 分）— A 类任何 0 分直接 reject

A1. **本体引用合法**：speaker_ref / location_ref / character_refs 引用的 ID 是否都在 /content/test_scene_v0/scene.json 已知本体内？是否捏造了角色/地点/派系/物品？
A2. **type-options 一致性**：type=dialogue 必有 options；type=end 必为空数组
A3. **选项数 3–6**：低于 3 或高于 6（除 end 外）
A4. **effects/conditions 字段合规**：op 在白名单（set/inc/dec/add/remove for effects；eq/neq/gt/gte/lt/lte/has/has_not for conditions）；path 是点分字符串；value 类型合理
A5. **ID 命名合规**：node_id 正则 `^[a-zA-Z0-9_-]+$`、option_id 同；不含 Unicode、空格、`/`

## B. 叙述质量层（5 维 / 上限 10 分）

B1. **感官细节密度**：是否有具体的视觉/听觉/触觉/嗅觉细节？还是只有抽象情绪词？
B2. **show vs tell**：用动作/感官**展示**心理状态，还是直接**说出来**（"他很紧张" vs "指节泛白"）？
B3. **中文自然度**：现代汉语自然，无翻译腔（"我想要做的是..."），无生硬古风滥词（"罢了""无妨"过度堆砌），无英语句法残留
B4. **节奏控制**：3 段以内的入口铺陈不拖沓；不在单段塞太多信息
B5. **风格契合（类 BG3 + 低魔写实 + 灰色道德）**：避免"善恶二元 + 奇幻浮夸"；保持"普通人在艰难处境下的复杂动机"基调

## C. 选项设计层（5 维 / 上限 10 分）

C1. **价值轴差异性**：3–6 个选项是否真正分布在不同价值轴上？还是同一轴的 N 种语气换皮（典型反例：4 个都是"答应"，只是态度不同）
C2. **玩家声音真实**：选项文本是玩家**会说的话**，不是 narrator 替玩家描述（典型反例："[感到一阵悲伤地] 你说..."）
C3. **选项文本质量**：每条 punchy（≤ 25 汉字优先），有角色感不是流水账
C4. **机制语义一致性**：effects 跟选项语义对得上？"友好选项 + dec trust" 这种反语义算 0
C5. **condition / unavailable_behavior 设计**：condition 锁的合理（不是显然该可选的项被锁）；unavailable_behavior 选择恰当（关键剧情线索宜 disable_with_hint，纯 flavor 隐藏宜 hide）

## D. 角色刻画层（3 维 / 上限 6 分）

D1. **NPC 性格贴合本体卡**：参考 /content/test_scene_v0/scene.json 里 character_refs 对应角色的 summary，NPC 的言行是否与之一致？
D2. **关系状态可见**：当前 NPC 对玩家的态度是否能从对白/动作中体察到？
D3. **隐藏信息处理**：NPC 是否合理地"埋伏笔"而非直接全盘交代？秘密通过细节暗示而非告白？

## E. 剧情功能层（3 维 / 上限 6 分）

E1. **intent 命中**：fixture 给的 narrative_intent 是否被这条节点准确达成？多了少了？
E2. **类型契合**：入口节点是否抓住注意力；中段节点是否承上启下；end 节点是否有真 closure（不是虎头蛇尾）
E3. **暗示下游分支合理**：每个 option 的 target_node_id（虽然不存在）所暗示的下一节点是否在叙事上合理可达？

# 评分汇总与判定规则

总分上限 = 10 + 10 + 10 + 6 + 6 = **42 分**

判定：
- A 类任何一维 = 0 → **直接 reject**（结构性问题不可救药），accept=false，reason 必填
- 否则总分 ≥ **30**（约 70% 上线）→ accept=true
- 否则 → reject，accept=false，reason 必填

reject 原因写法：
- 必须**具体到维度 + 节点的具体问题**
- 反例："质量不行"
- 正例："C1 (价值轴差异性=0): opt1/opt2/opt3 都是'答应帮 Vellin 应付巡逻官'的不同语气，缺乏'拒绝'/'威胁'/'反向利用'等其他价值轴"
- 正例："B2 (show/tell=0): narration 第二段直接写 'Vellin 紧张地说道'，把心理状态明说而非用动作展示"

# 产出文件

**1. batch-dir/review_log.jsonl** — 每行一条，格式严格按下面的 schema：

```json
{
  "iter_id": <int from results.jsonl>,
  "node_id": <string from generated node>,
  "schema_pass": true,
  "accepted": <true|false>,
  "reason": <null if accepted, else specific multi-dimension reason>,
  "scores": {
    "A": [a1, a2, a3, a4, a5],
    "B": [b1, b2, b3, b4, b5],
    "C": [c1, c2, c3, c4, c5],
    "D": [d1, d2, d3],
    "E": [e1, e2, e3]
  },
  "total": <int 0-42>,
  "ai_notes": <1-2 句中文：本节点突出的强项 + 主要弱项>,
  "reviewed_at": <ISO 8601 UTC string>
}
```

iter_id 必须与 results.jsonl 一致（int），node_id 取自 result.node.node_id。

**2. batch-dir/AI_JUDGE_REPORT.md** — 一份中文分析报告，含：

- 一句话结论：N/17 接受，整体判断（"质量稳定"/"两极分化"/"系统性弱点"）
- 整批 acceptance_rate
- 21 维度均分表（你能看出整批最弱的维度是哪个）
- reject 原因 top 5 + 各自影响节点数
- 给作者的 3 条具体 prompt 改进建议（**不是空话**："建议加 few-shot 示例 X"、"system prompt 加一句 Y"）
- 突出的最佳节点 1 条 + 最坏节点 1 条（iter_id + 一句评价）

# 工作流程

1. 读完 4 份必读文件
2. 读 batch-dir/results.jsonl，挑 success=true 的行
3. 对每条逐项打分
4. 全部评完后**写**两份产出文件
5. 完成报告（在对话里给作者）：
   - acceptance_rate（X/17 = Y%）
   - 整批最弱维度（top 3 平均分最低的）
   - 是否触发 ROADMAP 阶段 1 验收线（acceptance ≥ 50%）
   - 最关键的 1 条 prompt 改进建议（如果整批有系统性弱点）
   - 完成报告**不需要**列出所有 17 条详情（详情在 review_log.jsonl 里）

# 不要做的事

- 不要修改任何代码 / schema / fixture / 现有文档（除产出的两份文件外）
- 不要 commit / push（作者会自己处理）
- 不要为通过验收而打高分；如实评，分低就是分低
- 不要凭印象，每条节点要单独读完整 narration + 所有 options 再评
- 不要创建 batch-dir 之外的任何文件
- 不要重新生成节点 / 调用 Gemini API / 改 generator 代码——**纯阅读 + 评分**

# 完成判定

你完成的标志：
- review_log.jsonl 的行数 = batch-dir/results.jsonl 里 success=true 的行数
- AI_JUDGE_REPORT.md 已写
- 完成报告（含 acceptance_rate）已发给作者

开始。
```

---

## 说明（你的备忘）

### 何时用这个 prompt

- **任何 baseline_NNN 跑完后**，要走 acceptance 评估时
- batch-dir 路径作者每次手动改

### 局限与已知风险

1. **AI 判官跟真用户的偏好差距**：阶段 4 真实玩家反馈才能校准
2. **打分易膨胀**：LLM 倾向"中庸打 1 分"。如果发现整批 acceptance > 90%，应当怀疑判官手松，让它**重新走一遍并强调"严格"**
3. **D1 角色贴合**依赖判官对本体卡的理解；本体卡阶段 0 是桩，可能信息不足；阶段 2 本体 Schema 落地后再用此 prompt 会更准
4. **无视觉判断**：阶段 1.5 视觉资产生成后，节点配图质量需要单独 prompt（届时再写）

### 输出复用

- `review_log.jsonl` 兼容 `python -m generator.metrics --batch-dir <path>`，跑完直接拿到标准 metrics 输出（含 acceptance_rate / reject_reason_top_5）
- `AI_JUDGE_REPORT.md` 直接作为 T-1.8 验收报告的附件证据

### 与原 ROADMAP 的差异

- ROADMAP 阶段 1 完成标志说 "人工接受率 ≥ 50%"
- 本流程改为 "AI 判官接受率 ≥ 50%"
- 阶段 1 验收报告（T-1.8）需要明确**记录这一替代决策**作为遗留问题，并把"接入真用户反馈"作为阶段 4 的明确任务
