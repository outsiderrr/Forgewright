# 回流格式契约 v1 样张（T-3P-0）

> **给作者的验收说明**：这是编剧（BYOM）拿到的提示词包里「输出格式」段的**假想样例** +
> 一张**假想退回单**。请按两个问题批：① 编剧看得懂吗（不看我们的代码能照着写吗）？
> ② 退回单拿到手知道怎么改吗？格式定义的单一真相源在
> `generator/promptpack/format_spec.py`（本样张与代码不一致时以代码为准，改格式需回此样张同步）。
>
> 节点 id / 选项数 / 拍内线索都由我们锁定（结构不让编剧动）；编剧只填三类正文：
> 旁白（narration）、NPC 对白（dialogue）、玩家台词（options / continue）。
> 样例正文是为审格式手写的假想占位，不是本仓库生成的正文（ADR-039：正文由编剧写）；
> 节点名与选项数取自共用 fixture（`lucy/design.json`，opening = 4 选项），对照不困惑。

---

## 一、编剧回复的格式（假想样例，三类节点各一）

编剧对**每个锁定节点**交一个块。块与块顺序随意，node_id 必须与提示词包给定的逐字一致；
不得增删节点、不得改 node_id、不得增删选项序号。

### 1. choice 节点（多选项决策点）：必交 `narration` + `options`（序号 1..N 连续完整，N = 锁定选项数）；`dialogue` 可选

fixture 里 `opening` 锁定 4 个选项（安抚 / 给钱 / 观察 / 逼问），故序号 1..4：

```
[node: opening]
narration: 酒馆里只剩三张桌子有人。露西在吧台后擦一只杯子，
擦得比需要的久。靠窗的角落坐着一个男人，桌上没有酒，只有一份摊开的报纸。
dialogue:
  - 要喝什么就坐吧，外头冷。
options:
  1: 我想找个人，打听点事。别担心，就我们两个听得见。
  2: 一句话的事，说完我就走。[放下几枚硬币]
  3: [先不开口，坐下观察角落那个男人]
  4: 我直说了：莱特教授的事。你最好现在就讲。
```

- `narration:` 的值从冒号后开始，**允许多行**，直到下一个 key 行或下一个 `[node: ...]` 为止（多行值只有 narration 有）。
- `dialogue:` 块每行以 `- ` 开头，**裸正文不带引号包裹**（「」/""都不要）；说话人不用写——本场对白统一是锁定配置里的那位 NPC（露西）。0 行时整个 `dialogue:` 块可省。
- `options:` 序号行形如 `1: 台词`，一行一条写完；序号必须从 1 连续编到 N，不多不少。

### 2. beats 拍（单选项锁定微节点，id 形如 `{链}_b{i}`）：必交 `narration` + `continue`；`dialogue` 可选

每拍锁定要揭的**那 1 条**线索（提示词包会随块给出，如 `soft_private_line_b1` 锁定：
`莱特在希博公路北侧有一间旧测绘小屋。`）——正文必须把它揭出来，且不得提前揭后面拍的线索。

```
[node: soft_private_line_b1]
narration: 露西把杯子放下，往角落瞟了一眼，声音压得很低。
dialogue:
  - 好，你别抬高声音，我就说方位。
  - 北边。希博公路北侧，他有间旧测绘小屋。
continue: 怎么过去？
```

- `continue:` = 玩家把对话推进到下一拍的一句短话或动作（≤20 字），只此一条，不编号，一行写完。

### 3. end 节点（收束）：必交 `narration`；`dialogue` 可选（0-2 行）；**无 `options` / `continue`**

```
[node: end_soft_leave]
narration: 你把杯子推回吧台，起身离开。门口的风比来时硬，
你揣着几句不能在亮处念出来的话，往北边看了一眼。
```

---

## 二、假想退回单样张（`<reply>.reject.md`）

任何一条硬报错 → 整份回流**不落地**（不产 scene.json），收集全部问题一次退回：

```
# 回流退回单：lucy_roadhouse_multipass（3 处需修改）

逐条修完后整份重交；node_id / 选项序号以随包的「锁定节点清单」为准。

1. [E1 missing_node] 节点 `soft_private_line_b3`
   期望：锁定清单里的每个节点都要交一个 [node: ...] 块
   实际：回流文本里没有这个节点的块
   修改指引：补交 [node: soft_private_line_b3] 块（本拍锁定线索：
   「路标是第七码碑和一根断了半截的电线杆。」）。

2. [E4 option_count_mismatch] 节点 `opening` 的 options
   期望：序号 1..4 连续完整（锁定选项数 = 4）
   实际：交了 1: / 2: / 3: / 5:（缺 4，多 5）
   修改指引：把第四个选项的序号改回 4，选项总数保持 4 条，不得增删。

3. [E6 unknown_key] 节点 `end_soft_leave` 出现 `options:` 块
   期望：end 节点只交 narration（dialogue 可选），无 options / continue
   实际：块里带了 2 条 options
   修改指引：删掉该节点的 options: 块；结局分支不在这里选，结构已锁定。
```

---

## 三、错误代码全表（E1-E8；定义随包给编剧）

| 代码 | 名称 | 含义 |
|---|---|---|
| E1 | missing_node | 锁定骨架有、回流缺的节点 |
| E2 | unknown_node | 回流有、锁定骨架没有的节点（不接受新增） |
| E3 | duplicate_node | 同一 node_id 出现两个块 |
| E4 | option_count_mismatch | 选项序号缺号 / 多号 / 不连续 / 与锁定数不符 |
| E5 | missing_field | 必填 key 缺失（narration / continue / options 块整体缺失） |
| E6 | unknown_key | 不认识或不该出现的 key（含错位块、重复出现的已知 key） |
| E7 | empty_text | key 行或序号行在但正文为空 |
| E8 | parse_error | 无法归属任何 key 的游离行 |

边界判定口径（逐 case 定死在 `format_spec.py`）：

- `options:` 块**整体缺失** = E5；块在、有序号行但缺 / 多 / 不连续 = E4；不该出现的块（end 带 options 等）= E6。
- 同一节点块内**已知 key 第二次出现**（两个 `narration:`、两个 `options:` 块）= E6，从第二次出现处记；首个块正常归属。
- **空正文全归 E7**：序号行有序号无正文（`3: ` 后为空）= E7；dialogue 块内空 `- ` 条目 = E7；`options:` key 在但块内 **0 条序号行** = E7（空块唯一归属 E7，不落 E4——E4 只管序号行存在但对不上）。`dialogue:` 块 0 行是合法可选，不算错。
- **多行值只有 narration**：`continue:` 的值、options 序号行、dialogue `- ` 行都是单行值，其后的续行无法归属 = E8。
