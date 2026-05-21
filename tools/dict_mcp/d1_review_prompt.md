# D1 字面直达 Review Prompt

> talkstyle-skill v0.1 第 1 维度 (D1 字面直达 / locution ≈ illocution) 的 review 端 prompt。

## 用途

对单条对白（NPC dialogue / 玩家选项）执行 D1 字面直达判定：检查"字面意义"和"意图意义"是否收敛。

依赖工具：`lookup_dictionary(word)` —— 查询 CC-CEDICT + 项目 D1 补丁白名单。

## 适用场景

- 生成后 review pipeline
- 人工编辑器辅助 lint
- 测试集回归

## Prompt 模板

```
你是 v0.1 D1 字面直达的判定者。对下面这句对白，按 3 步执行：

[输入]
对白：「<对白文本>」
说话人意图（可选，由作者标注）：<intended_meaning 或省略>

[Step 1：修辞扫描]
扫描句中是否含以下任一现象：
- 活比喻 / 明喻 / 暗喻（"他心硬" / "她笑像玻璃" / "墙比夜厚"）
- 活借代（"今晚穿黑的会从后门进来"）
- 拟人（"夜在低语"）
- 用典 / 典故（"这真是个滑铁卢"）
- 脱离实际比例的夸张（"等了一万年"）
- 委婉语（"他不在了" 替代 "死了"）
- 反语 / 反问断言（"你真聪明" 意思是蠢）
- 暗示性陈述（说 A 让对方明显推 B，且 B 才是主信息）

若扫描结果为"无"：输出 `[D1: pass]` 结束。
若扫描结果为"有"，记下 figurative 短语，进 Step 2。

[Step 2：字典 + 白名单查询]
对每个识别出的 figurative 短语 X，调用：
    lookup_dictionary(word=X)

返回值字段：
- found_in_cedict: bool
- found_in_whitelist: bool
- definitions: list[str]
- tags: { has_figurative, has_literal_only, is_neologism, is_slang, has_idiom_marker }
- whitelist_note: str | None

判定规则：
a) found_in_whitelist = True → pass（项目补丁兜底）
b) found_in_cedict = True 且 definitions 含有义项与说话人意图义匹配
   （包括标注为 (fig.) / (slang) / (neologism) / (idiom) 的义项）→ pass
c) found = False → fail
d) found = True 但 definitions 不含意图义匹配 → fail

[Step 3：输出]
所有 figurative 短语都 pass → 整句 `[D1: pass]`
任一 figurative 短语 fail → `[D1: fail —— 不合规短语: "<X>"，理由: "<原因>"]`

[硬约束]
- 不确定 → 按 fail（v0.1 严格立场）
- 不要凭训练记忆判断词典收录情况，必须调用 lookup_dictionary
```

## 输出格式约定

成功：

```json
{ "d1": "pass", "scanned_phrases": [...] }
```

失败：

```json
{
  "d1": "fail",
  "violating_phrase": "心硬",
  "reason": "活比喻；CC-CEDICT 收录 'hard-hearted; unfeeling' 但说话人意图义 'X' 不匹配此义项",
  "lookup_result": { ... }
}
```

## 跟其他维度的关系

- D1 只看"字面 vs 意图"。**不**判断"装饰是否过度"（D2）、"是否晦涩"（D3）、"是否冗长"（D5）等
- 一句话可能 D1 pass 但 D2 fail（如"他点头同意了"——无 figure，但若有 "他颔首微笑表示赞同" 则被 D2 当装饰扣分）
- 多维度 review 取合集——任一维度 fail 则整句 fail

## 边界 case 处理参考

| 句子 | D1 判定 | 调用 lookup 关键值 |
|------|---------|---------------|
| "他心硬。" | pass | CC-CEDICT "hard-hearted; unfeeling; callous" 直接匹配 |
| "他没接你的烟。" | pass | 无 figure，Step 1 直接 pass |
| "他把心锁进铁盒里。" | fail | "锁进铁盒里" not found, 不在白名单 |
| "她笑像玻璃。" | fail | "像玻璃" not found, 不在白名单 |
| "等了一万年。" | fail | "一万年" 字面计数不匹配实际，dictionary 不会收 |
| "凛然不可侵犯。" | pass | 在白名单（CC-CEDICT 漏收）|
| "这事是他的滑铁卢。" | pass | CC-CEDICT 标 "(fig.) a defeat" |
| "你父亲已经不在了。" | fail | "不在了" 是委婉语，字面 ≠ 意图（死） |
