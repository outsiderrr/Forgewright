# D1 字面直达（locution ≈ illocution）v0.1.1

> talkstyle-skill v0.1 第 1 维度。codex review 第 1 轮后修订版。

## D1.1 精确定义

**D1 字面直达**：对白的常规字面命题（locutionary content）+ 显性言语行为力（illocutionary force），应直接呈现说话人要听者接收的内容；不要求听者做非词典化转义或语用反推。

通俗：词 / 短语按通常句法组合后的常规字面义 ≈ 说话人想让听者接收的意图义。

**学术锚点**：Austin / Searle 言语行为理论之 locutionary act + illocutionary force。注：v0.1 把这两者收敛到 ≈ 关系；v0.2 处理两者的偏差（subtext / implicature / motivation）。

## D1.2 v0.1 禁止类别（9 类要求"非词典化解读"的修辞）

| # | 类别 | 中文术语 | 反例 |
|---|---|---|---|
| 1 | Live metaphor | 活比喻 / 暗喻 | "他**把心锁进铁盒里**" |
| 2 | Simile | 明喻（X 像 Y） | "她的笑**像玻璃**" |
| 3 | Live metonymy | 活借代 | "今晚**穿黑的**会从后门进来" |
| 4 | Personification | 拟人 | "**夜在低语**" / "门不愿意开" |
| 5 | Allusion | 用典 / 典故 | "这真是个**滑铁卢**" |
| 6 | Hyperbole | 夸张（脱离实际比例） | "**等你等了一万年**" |
| 7 | Euphemism | 委婉语 | "他**不在**了"（=死了） |
| 8 | Irony / 反问断言 | 反语 / 反问 | "你**真聪明**"（=蠢） |
| 9 | Implicature (narrowed) | 显性 A 代 B 暗示 | 说话人明显以 A 代 B，且 B 才是行动性 / 评价性主信息 |

**类别 9 限定**（codex review fix）：必须是"说话人明显以 A 代 B"——单纯"听者可能要推理"的描述性陈述不算。例如"你今天没带伞"如果意图就是描述事实，pass；若说话人明显在用此句指责"你没准备好"，fail。

## D1.3 v0.1 允许：词典化 / 死比喻

字典里把"意图义"作为独立义项收录的 figurative，pass D1。

**判别原则**（codex review 后保留充分条件立场）：

> 该 figurative 表达的"意图义"是否被 CC-CEDICT（含项目补丁白名单）收录？  
> 是 → 死比喻 → pass D1  
> 否 → 活比喻 → fail D1

**工程实现**：调用 [zh-dict-mcp](https://github.com/outsiderrr/zh-dict-mcp) 的 `lookup_dictionary` 工具。返回的 JSON 含 `found_in_cedict` / `found_in_whitelist` / `definitions` / `tags` 等字段，用来判定。

**示例死比喻（pass D1）**：

| 表达 | CC-CEDICT 收录义项 |
|---|---|
| 看见 | to see; to catch sight of |
| 把握 | to grasp; (also fig.); to seize |
| 等等 | wait a minute; et cetera |
| 算了 | let it be; forget about it |
| 白宫 | White House |
| 滑铁卢 | Waterloo; (fig.) a defeat |
| 内卷 | (neologism, attested by 2017) ... |

## D1.4 判定规则（3 步流程，Q3 仅为兜底）

按顺序问 3 个问题。Q3 仅在 Q1 yes 且 Q2 无法明确判断时使用（codex review fix —— 原版有 unreachable bug）。

```
Q1【修辞扫描】
   句中有无活比喻 / 明喻 / 借代 / 拟人 / 用典 / 夸张 / 委婉
   / 反语 / 显性 A 代 B 暗示？
   - 否 → pass D1
   - 是 → 进 Q2

Q2【字典查询】
   调 lookup_dictionary(word="<figurative 表达>")。
   - definitions 中含义项 ≈ 说话人意图义？
     - 是 → pass D1
   - definitions 含 (fig.) / (slang) / (neologism) / (idiom)
     标注且义项匹配意图义？
     - 是 → pass D1
   - found_in_whitelist = True → pass D1（项目补丁兜底）
   - found_in_cedict = False 且 found_in_whitelist = False → fail D1
   - found = True 但义项不匹配意图义 → 进 Q3

Q3（兜底）【替换测试】
   把 figurative 表达替换成它的字面解释，意图是否保持？
   - 保持 → 装饰性 figurative → fail D1
   - 不保持 → fail D1（按 "不确定也 fail" 立场，
     不留 flag 给人审）
```

## D1.5 正反例（5 对）

### 例 1（活比喻 vs 具体动作）

| 反例（fail D1）| 正例（pass D1）|
|---|---|
| "他**把心锁进铁盒里**。" | "他**没有改主意**。" 或 "他**拒绝帮你**。" |

**说明**（codex Angle 4.1 修订）：原反例"他心硬"在 CC-CEDICT 收录"hard-hearted; unfeeling; callous"独立义项，按 D1.3 应该 pass。换成更明显活比喻——"锁进铁盒里"在 CC-CEDICT 必查不到。

### 例 2（明喻 vs 直接描状，需明确原意）

| 反例 | 原意（作者标注） | 正例 |
|---|---|---|
| "她笑得**像一面玻璃**。" | 笑得僵 | "她笑了一下，**表情很僵**。" |
| "她笑得**像一面玻璃**。" | 笑声很轻 | "她笑了一下，**声音很轻**。" |
| "她笑得**像一面玻璃**。" | 笑得冷 / 假 / 易碎 等多义 | 拆多句：**"她笑了一下，但很冷。眼神没跟。"** |

**说明**（codex Angle 4.2 修订）：明喻常压缩多个评价（冷+脆+假+透明）；v0.1 已知局限：必须先明确"作者要传达哪几个评价"，然后拆分多句直说。**接受句长变长是 v0.1 的代价**。

### 例 3（委婉语 vs 直说）

| 反例 | 正例 |
|---|---|
| "你父亲已经**不在**了。" | "你父亲**死了**。" |

**说明**：v0.1 阶段强制直说。v0.2 上动机分层后，"避免说'死'"可以作为子动机重新引入。

### 例 4（项目实际反例）

| 反例 | 正例 |
|---|---|
| "墙薄，**人耳朵更薄**。" | "墙这边听不清，**后厨门关不严**。" |

**说明**："耳朵薄"是创造性活比喻；正例换两个可观察的物理事实，意图（说话要小心）完整传达。

### 例 5（死比喻—允许，列出防过判）

| 看似 figurative 但 pass D1 | CC-CEDICT 义项 |
|---|---|
| "我**看见**他站在门口。" | to see; to catch sight of |
| "**算了**，不说了。" | let it be; forget about it |
| "你**懂**我的意思吧？" | to understand |

## D1.6 可植入 prompt 片段（生成端 / review 端分工）

### 生成端规则（拼进 system prompt / character instructions）—— 高层简洁

```
[D1 · 字面直达]
写对白时，让字面意义 ≈ 想传达的意思。

禁止 4 大类：
- 非字面映射（比喻 / 明喻 / 借代 / 拟人 / 用典）
- 避讳或反向表达（委婉 / 反语 / 反问断言）
- 脱离实际比例的夸张
- 显性 A 代 B 暗示（说话人明显用 A 指代 B，且 B 才是主信息）

允许：CC-CEDICT 收录的死比喻 / 习惯用法 / 词典化感叹
```

### Review 端规则（拼进 review / validator prompt）—— 详细 checklist

```
[D1 · 字面直达 review]
对每句对白按顺序执行：

1. 修辞扫描：有无活比喻 / 明喻 / 借代 / 拟人 / 用典
   / 夸张 / 委婉 / 反语 / 反问断言 / 显性 A 代 B 暗示？
   - 否 → pass D1，结束
   - 是 → 进 2

2. 字典查询：调 lookup_dictionary(word="<figurative 表达>")
   - definitions 中有义项与说话人意图义匹配
     （含 fig./slang/neologism/idiom 标注义项）→ pass D1
   - found_in_whitelist = True → pass D1
   - 都不匹配 → 进 3

3. 替换测试（兜底）：把 figurative 替换成字面解释，意图保持？
   - 保持 → 装饰性，fail D1
   - 不保持 → fail D1（不确定也 fail）

输出：[D1: pass] 或 [D1: fail (引用具体短语 + 理由)]
```

## D1.7 跟其他维度的关系

- **D2 拒绝装饰**：D1 管"字面 ≠ 意图"语义层；D2 管"字面 = 意图但形式工整"形式层。交叉 case（一虚一实结构如"不买酒也不买平安"）归 **D2**，D1 保持纯语义判定
- **D3 避免晦涩 / D4 避免歧义**：D1 命中跟 D3/D4 几乎不重叠（D3 看字面读懂难度，D4 看字面多解读，D1 看字面≠意图）
- **D5 简明**：去掉装饰 figurative 通常会让句子变长——D1 命中常顺带触发 D5 关注
- **D6 有序**：D1 跟 D6 几乎不重叠
- **v0.2**：D1 显式不处理 implicature 跨句 / subtext / 动机；那些是 v0.2 内容
- **v0.3+**：D1 不处理角色身份相关的词袋（颔首 / 凛然 / 释怀 等 register 问题）；那些是 v0.3
