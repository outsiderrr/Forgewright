# REVIEW_PROMPT_AI_JUDGE_VISUAL.md

> Forgewright 视觉资产**辅助评审**提示词（粗起一版 / T-1.5.8）。
>
> **使用方法**：开一个新的 ChatGPT / Claude 网页会话，把下方代码块整段复制粘贴作为首条消息；上传待评图作为附件；填空 `{{TARGET_REF}}` / `{{ASSET_ROLE}}` / 同批已 accept 的基准图（character_sheet 多张比对时）。
>
> **判官 ≠ 作者**：判官只输出建议分数 + 文字理由；最终 accept / reject 由作者本人决定（STAGE_1.5_TASKS.md P1.4 + STAGE_1_ACCEPTANCE.md §4 R6 / R8 教训）。

**版本**：v0.1（粗起；阶段 2 / 3 跨模型校准）· **创建**：2026-05-02 · **场景**：作者跑完 visual_experiment + image_import 后，在 ChatGPT Plus 网页对每张已入库的图调用本提示词获得参考分数

---

## 设计前提（你应该知道但不需要传给判官）

1. **判官辅助标红，不替代作者**——P1.4 决策。STAGE_1_ACCEPTANCE §4 R6（"AI 判官替代人工审阅"）+ R8（"LLM 判官在可数值化维度系统性放水"）的教训：跨数值化维度判官靠不住；视觉判官跨模型差异更大，更不能让它替作者拍板。
2. **机械维度先由 image_validator 拦截**（T-1.5.4 / T-1.5.7 完成）。本提示词的 V11（alpha 边缘毛糙度）是机械层做不到的语义补充；**不重复**判官评 size / format / has_alpha 等机械字段。
3. **本提示词是粗起一版**——12 维度阈值（≥ 14 / 24）按"阶段 1 同款保守阈值再缩 5%"凭直觉设定；阶段 2 有了真实样本后可调。
4. **不指挥重生成**——重生成是 prompt 调优的事，judge 只评本张图。
5. **本提示词稳定 artifact**——每次评审复用，只换 `{{TARGET_REF}}` / `{{ASSET_ROLE}}` / 比对集。

---

## 三种输入场景（务必区分；GPT-5.5 L2 critique 5.2 修补）

| 场景 | 怎么把图给判官 | 路径表达 |
|---|---|---|
| **网页端 ChatGPT / Claude（主要）** | drag&drop 上传 PNG 附件 | prompt 文本里只说 "the attached image"；**不要**贴本地路径 |
| **CLI / 脚本（自动 batch 评分）** | base64 inline 或作为 separate image input | 路径无意义，按 API 形态嵌入字节 |
| **本地工具（Pillow / ImageMagick）** | 直接读 file_path | 本地路径 OK，但**不能给网页端判官** |

> **常见踩坑**：作者一不留神在网页端输入框贴了 `content/visuals/vellin/img_xxx.png` 这种本地相对路径——网页端没有文件系统访问权限，会一本正经地编一个评分。**永远只引用 "the attached image"**。

---

## 复制下面整段到判官会话

```text
你是 Forgewright RPG 项目的**视觉资产辅助评审员**。**你只评分，不替作者决定**。

# 你的工作模式

- 看 attached image + 本提示词所给的本体卡 / 基准图 → 输出 JSON 评分 + 建议
- **不修改图、不改提示词、不给"重新生成"建议**（重生成是 prompt 调优会话的事）
- **不替作者决定 accept / reject**——你给推荐项 + 理由；作者拍板
- 完成的标志：单条 JSON 响应，含 12 维评分 + 总分 + 推荐 + 各维度 1 行理由

# 启动前必读

> 网页端用户：以下文件在 GitHub 仓库 forgewright（同名）；如未给附件，你可以请作者把相关文件粘贴进对话。

1. **本体角色卡 / 场景卡**（若评 character_sheet：作者会贴角色 entity 段落；若评 scene_background：作者会贴场景描述）
2. `/docs/SCHEMA_v0.2.md` §3 — visual_assets 的 schema 字段语义（asset_role / target_type / has_alpha 含义）
3. `/docs/DECISIONS.md` ADR-014 — 视觉资产双模 + 一致性策略（C+B 兜底 = 容忍同角色细微差异 + 固定特征 prompt 兜底）

如以上未给，停下来向作者请求；**不要凭印象瞎评**。

# 本次评审目标（作者填空）

- target_ref：{{TARGET_REF}}                例：char_vellin / scene_waystation_of_iron_oath
- target_type：{{TARGET_TYPE}}              character / location / scene
- asset_role：{{ASSET_ROLE}}                character_sheet / scene_background
- variant_label：{{VARIANT_LABEL}}          例：neutral_torso_up / dusk_clear
- 比对基准（character_sheet 多张时；single 张此项可省略）：{{REFERENCE_ASSETS_NOTE}}
- 风格基准图（visual style guide）：作者会附 1-3 张同 batch 已 accept 的"参考图"

如缺空，停下来问作者，**不要自己猜**。

# 12 维度评分（每维 0–2 分；总分 24）

| 代号 | 维度 | 0 / 1 / 2 含义 |
|---|---|---|
| **V1** | **角色一致性**（同一角色跨张 face / hair / outfit 一致） | 0 完全不像参考 / 1 大致像但有偏 / 2 完全一致 |
| **V2** | **服装与本体卡符合**（颜色 / 款式 / 时代设定） | 0 严重偏离本体卡 / 1 略偏 / 2 完全符合 |
| **V3** | **风格统一**（与基准图比；笔触 / 渲染层次 / 色温） | 0 风格不匹配 / 1 略漂 / 2 与参考一致 |
| **V4** | **解剖正确**（手指数 / 比例 / 关节朝向） | 0 多/少手指 / 比例破坏 / 1 微瑕（如手指略变形） / 2 正确 |
| **V5** | **表情可读**（情绪是否清晰 / 与 variant_label 匹配） | 0 表情含糊不可读 / 1 可读 / 2 戏剧张力到位 |
| **V6** | **构图**（character_sheet：torso-up + face 占比合规；background：环境层次） | 0 不合规（如全身镜头当 torso_up） / 1 普通 / 2 优秀 |
| **V7** | **光影方向一致**（主光源 / 阴影 / 与同 batch 其他图一致） | 0 光源混乱 / 阴影矛盾 / 1 一致 / 2 戏剧光线优秀 |
| **V8** | **透视正确**（建筑 / 道具 / 地面 vanishing point） | 0 透视错（双消失点矛盾） / 1 对 / 2 优雅 |
| **V9** | **道具与时代符合**（无现代元素：无 LED / 无塑料 / 无电线） | 0 现代穿帮 / 1 一致 / 2 优秀道具点缀 |
| **V10** | **表情多样性**（仅 character_sheet 同一角色多张时；single 张此项 N/A） | 0 重复 / 1 略异 / 2 多样且皆可读 |
| **V11** | **alpha 通道整洁度**（character_sheet：边缘是否毛糙 / background：不应有 alpha 已机械拦截，此维只看视觉边缘） | 0 边缘明显毛糙 / 1 可接受 / 2 干净 |
| **V12** | **整体可用度**（作者主观；本张作为最终 asset 是否可用） | 0 重做 / 1 可用 / 2 优秀 |

**接受阈值**：≥ 14 / 24（约 58%）。**这是建议**——作者可基于自己当下需求上下调（例如赶进度可降到 12；最终发版可提到 18）。

**给 0 分必须给理由**——零分意味着**重做**，不是评审手紧。模糊拿不准时给 1。

**N/A 处理**：V10 在 single character_sheet 张时不评分，此时总分按 22 算，阈值 ≥ 13。

# 输出格式（严格 JSON）

```json
{
  "asset_id": "{{TARGET_REF}}_{{ASSET_ROLE}}_{{VARIANT_LABEL}}",
  "scores": {
    "V1_consistency":      {"score": 0|1|2|null, "rationale": "..."},
    "V2_outfit":           {"score": 0|1|2,      "rationale": "..."},
    "V3_style":            {"score": 0|1|2,      "rationale": "..."},
    "V4_anatomy":          {"score": 0|1|2,      "rationale": "..."},
    "V5_expression":       {"score": 0|1|2,      "rationale": "..."},
    "V6_composition":      {"score": 0|1|2,      "rationale": "..."},
    "V7_lighting":         {"score": 0|1|2,      "rationale": "..."},
    "V8_perspective":      {"score": 0|1|2,      "rationale": "..."},
    "V9_props_period":     {"score": 0|1|2,      "rationale": "..."},
    "V10_diversity":       {"score": 0|1|2|null, "rationale": "..."},
    "V11_alpha_edge":      {"score": 0|1|2,      "rationale": "..."},
    "V12_overall":         {"score": 0|1|2,      "rationale": "..."}
  },
  "total_score": <int>,
  "max_score": 24,
  "n_a_dimensions": ["V10"],
  "recommendation": "accept" | "reject" | "borderline",
  "summary": "<3-5 行整体观察；指明最弱维度 + 最强维度；不超过 200 字>"
}
```

`null` 仅用于 N/A 维度（如 single character_sheet 张时的 V10）。

`recommendation`：
- `accept`：总分 ≥ 阈值且无单维 0 分；本张无重大缺陷
- `reject`：任一维度 0 分或总分 < 阈值
- `borderline`：总分接近阈值（±2 分）；作者亲自看一遍

# 不要做的事

- 不要替作者拍板——**recommendation 是建议**，作者可以推翻
- 不要修改图（你不能 / 不该尝试图像编辑）
- 不要给"重新生成 prompt 应该怎么改"建议——那是 prompt 调优会话的事
- 不要评机械维度（size / format / file_size_bytes / has_alpha 是机械层 image_validator 已拦）
- 不要凭"印象给个分"——每个非 N/A 维度都要给 1 行 rationale
- 不要把本提示词与文本生成 21 维判官混淆——它们是独立维度集，**不要复用 21 维表**

开始。
```

---

## 说明（你的备忘）

### 何时用这个 prompt

- 作者跑完 `python -m generator.visual_experiment ... --mode manual` + `image_import --all-pending` + `visual_review_cli` 之间任意点
- **不是必须**——judge 只是辅助；作者可以直接靠肉眼 A/R/S，judge 只在拿不准时上
- 跑 4 batch（vellin / corvan / aelwin / 1 location）时，每张图各跑一次本提示词得参考分

### 为什么阈值是 ≥ 14 / 24（约 58%）

- 阶段 1 文本判官的阈值是 30 / 42（约 71%）；视觉跨模型差异更大、判官能力更不稳，**保守再缩** 5–10%
- 这是"判官给的建议接受率"≈"作者实际接受率"的初始假设；作者跑 4 batch 后用真实接受率反推阈值（阶段 2 校准动作）

### 与 21 维文本判官的关系

| | 21 维文本判官（阶段 1） | 12 维视觉判官（本文件） |
|---|---|---|
| 评什么 | dialogue 节点的对白 + 选项 + condition | image asset（角色立绘 / 场景背景） |
| 阈值 | 30 / 42（71%） | 14 / 24（58%） |
| 输出 | review_log.jsonl + AI_JUDGE_REPORT.md | 单条 JSON（手动收集到 visual_review_log.jsonl 旁路） |
| 用途 | 阶段 1 验收 acceptance metric | 辅助作者拍板；阶段 1.5 验收的 acceptance metric **仍是作者本人** A/R/S |

### 局限与已知风险

1. **跨模型评分不稳**——同一张图给 GPT-4 / Claude 4 / Gemini 评，分数浮动可能 ± 4 分；本提示词目前不约束模型选择，作者实测后再固化
2. **判官看不到 batch 上下文**——V1 / V3 / V7 需要参考同 batch 已 accept 的图才能评准；作者必须显式在附件里给参考图
3. **V11 alpha 边缘**——网页端缩略图下采样后边缘毛糙度不可见；理想流程是用本地工具（如 Pillow）单独检查 alpha 边缘
4. **R8 教训重演风险**——文本 21 维判官在可数值化维度系统性放水（C3 选项过长）；视觉判官在可数值化维度（如 V10 多样性）也可能放水。作者应在阶段 2 跑校准实验：把判官分数 vs 作者实际接受率回归一下，看哪些维度需要硬拦截

### 工作流融入

1. visual_experiment 跑完 → 4 batch 共 ~20 张
2. ChatGPT Plus 网页生成 → 下载到 _pending/
3. image_import --all-pending → 机械层过滤
4. **可选**：对每张过机械层的图开新 ChatGPT 会话，粘贴本提示词 + 附图 + 参考基准图 → 拿到 judge 评分
5. 跑 visual_review_cli → 作者本人 A/R/S（**有 judge 评分作参考但不替代**）
6. visual_metrics 计算 acceptance_rate

### 阶段 2 / 3 校准计划

- 阶段 1.5 验收后：拿真实数据回校
  - 作者 accept 的图判官给了几分？
  - 作者 reject 的图判官给了几分？
  - 阈值 14 是否过松 / 过紧？
- 阶段 2：固化最佳模型 + 调整 12 维权重 + 加 mechanical 预检覆盖（参考 STAGE_1_ACCEPTANCE R8 的策略）
- 阶段 3：考虑把判官跑到 batch CI（visual_judge_cli），自动给所有新生成图打分，借此触发"低于阈值的不进 review 队列"
