# tools/talkstyle/ —— talkstyle-skill v0.1 spec 暂存区

talkstyle-skill v0.1 各维度 spec 草稿暂存区。每个维度独立成文件，方便迭代。后续将整合成 SKILL.md，剥离到公开仓库 [outsiderrr/talkstyle-skill](https://github.com/outsiderrr/talkstyle-skill)（待建）。

## 当前文件

| 文件 | 维度 | 状态 |
|---|---|---|
| `d1_spec.md` | D1 字面直达（locution ≈ illocution）| v0.1.1, codex review 过 |
| `d2_spec.md` | D2 拒绝装饰（formal patterning rejection）| v0.1.1, codex review 过 |
| `d3_spec.md` | D3 避免晦涩（Grice manner-1, avoid obscurity） | v0.1.1, codex review 过 |
| `d4_spec.md` | D4 避免歧义（Grice manner-2, avoid ambiguity）| v0.1.1, codex review 过（含三态：pass / fail / flag）|
| `d5_spec.md` | D5 简明（Grice manner-3, be brief）| v0.1.1, codex review 过（含替换测试 + 粒子边界）|
| `d6_spec.md` | D6 有序（Grice manner-4, be orderly）| v0.1.1, codex review 过（含条件倒置 + 白名单局部豁免）|

## 总体设计

talkstyle-skill v0.1 = locution ≈ illocution 收敛 + 6 维度并列检查（任一命中即 fail）。

- **D1**：语义层（字面 ≠ 意图）— Austin locutionary ≈ illocutionary
- **D2**：形式层（字面 = 意图但句式重排）— Leech & Short formal patterning
- **D3**：可读性（字面本身太难）— Grice avoid obscurity
- **D4**：单义性（字面本身多解）— Grice avoid ambiguity
- **D5**：长度（信息量 vs 句长比）— Grice be brief
- **D6**：顺序（信息颗粒按合理顺序）— Grice be orderly

## 不在 v0.1 范围

- subtext / motivation / implicature 跨句 → v0.2
- character sociolect / register matching → v0.3
- character-bound vocabulary（颔首 / 凛然 / 释怀 等高 register 词）→ v0.3
- tone / relational dynamics（aggressive / 婉转 / 防御）→ v0.4+

## 工程后端

D1 调用 [zh-dict-mcp](https://github.com/outsiderrr/zh-dict-mcp) PyPI 包做字典查询。补丁白名单见 `../dict_mcp/supplement_whitelist.yaml`。

D2-D6 不需字典查询，纯 LLM 模式识别。
