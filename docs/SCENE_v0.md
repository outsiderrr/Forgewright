# SCENE_v0.md — 阶段 0 示例场景：《铁誓驿站》

**文档版本**：v0.1 · **最后更新**：2026-04-23
**依赖**：`docs/SCHEMA_v0.md` **v0.1.1**（`schema_version` = `0.1.1`）。若 SCHEMA_v0.md 后续升级到 0.2.x，本文件须同步审阅。

> 本文件是**场景设计规约**，不是可执行 JSON。
>
> 目标：为后续任务 T-0.8（手写 JSON 内容）和 T-0.9（validator 校验逻辑）提供一个参考场景。内容严格依据 SCHEMA_v0.md v0.1.1 的字段定义；不使用任何 SCHEMA_v0.md 未定义的字段；不对 SCHEMA_v0.md 做任何修改。
>
> **表示法备注**：`StateEffect.path` 与 `StateCondition.path` 的具体表示法（点分字符串 vs 段数组）由 D5 推迟至 `/state` 状态总线 Schema 任务。本文件在伪 JSON 中以**点分字符串**作为可读示意（如 `"relationship.vellin.trust"`），不构成对 D5 的预先裁决——T-0.8 落地 JSON 时将以当时的最终表示法为准。`op` 值亦同（D6 推迟；本文件使用 SCHEMA_v0.md §3.4/§3.5 给出的候选起点）。

---

## 1. 场景概览

### 1.1 情节梗概

玩家是一名游走边境的赏金猎人，黄昏时抵达**铁誓驿站**（Waystation of the Iron Oath）。驿站长 **Vellin** 是玩家的旧识——五年前他们曾一起在南境陶窑山口服役。玩家发现 Vellin 正在藏一封带血的信：写信人是三年前一起共事的少年兵 **Aelwin**，他杀死了虐待部下的百夫长后从铁誓卫队逃亡，现正躲在东边的牧人废屋里等消息。

当晚，铁誓卫队的巡逻官 **Corvan**（玩家的另一位旧识）抵达驿站搜查逃兵线索。玩家必须在三重旧情之间做出选择：庇护 Vellin 与 Aelwin，或向 Corvan 报告。

### 1.2 角色锚点（本体引用占位）

| 角色 ID | 描述 | 本场景中的动机 |
|---|---|---|
| `char_vellin` | 驿站长，玩家旧识，曾同袍 | 救 Aelwin，哪怕赌上自己的职位与性命 |
| `char_corvan` | 铁誓卫队巡逻官，玩家旧识 | 履行卫队职责，但对旧友留余地 |
| `char_aelwin` | 逃兵，场景中不出场 | 求生；不后悔杀百夫长 |

### 1.3 地点锚点

`scene_anchor` = `scene_waystation_of_iron_oath`（驿站主厅）。所有节点 `location_ref` 均继承此锚点（本场景不做地点细化）。

### 1.4 图元数据

| 字段 | 值 |
|---|---|
| `schema_version` | `"0.1.1"` |
| `graph_id` | `"glades_ironoath_waystation"`（合规于 D7：仅小写 / 数字 / `_` / `-`）|
| `entry_node_id` | `"arrival_waystation"` |
| `scene_anchor` | `"scene_waystation_of_iron_oath"` |
| `character_refs` | `["char_vellin", "char_corvan", "char_aelwin"]` |

---

## 2. 图拓扑

```
                  arrival_waystation  [N1 · dialogue · entry]
                   /       |        \
                  / (a)    | (b)     \ (c · gated)
                 /         ↓          \
                / vellin_confession    \
               /   [N2 · dialogue]      \
              |      |         \         \
              |      | (a)      \ (b)     ↓
              |      ↓           ↓         patrol_arrives
              |      |           |         [N3 · dialogue]
              |      |           |          /     |     \
              |      |           |    (a)  / (b)  | (c · gated)
              |      |           |        /       |       \
              ↓      ↓           ↓       ↓        ↓        ↓
              ─── end_silent_ally ───    ─── end_iron_blade ───
                  [N4 · end]                  [N5 · end]
```

- **分支**：N1 有 3 个选项（满足 a）；N2 有 2 个；N3 有 3 个。
- **汇合**：N4 由 `{N2, N3}` 两路汇入；N5 亦由 `{N2, N3}` 两路汇入（满足 b、e）。
- **结局**：N4、N5 两种不同结局（满足 f）。
- **节点级容错（BG3 式）**：结局 N4「沉默的同盟」既可由 N1→N2 正面对峙后承诺保守秘密达成，也可由 N1→N3 在 Corvan 面前撒谎或诉诸旧情达成——作者无需穷举所有组合即可保留多路径可行性。

---

## 3. 节点详述

### 3.1 N1 · `arrival_waystation`（入口 · dialogue）

**说话者**：`char_vellin`（玩家进门后 Vellin 的开场白）

**叙述文本**（≈210 字）：

> 黄昏时分你策马抵达铁誓驿站。山风把塔楼顶的旗帜吹得猎猎作响——那面绣着断剑与铁环的旗已经褪成铜绿色。
>
> 推开吱呀作响的橡木门，你看到 Vellin 站在柜台后。她比你记忆里瘦了一圈，左眉骨上多了一道新伤。她抬头，瞳孔先是一缩，又迅速挤出一个笑容。
>
> "……是你啊。没想到铁誓路还有人走。"她一边说，一边把柜台上的几张纸不动声色地推到油灯后面。那叠纸边缘有一道半干的暗红色，像被按过带血的指腹。
>
> 她倒了一杯酒推过来。"来得不巧。巡逻官今晚会到。你想住下，还是喝完就走？"

**选项**：

| option_id | 可见文本 | 目标 | 守卫 | unavailable_behavior |
|---|---|---|---|---|
| `opt_confront_letter` | "[按住那叠纸] 你手上沾的不是酒。" | N2 | 无 | `hide` |
| `opt_sit_and_wait` | "给我续一杯。巡逻官来之前我就是个过路客。" | N3 | 无 | `hide` |
| `opt_read_the_room` | "[观察入微] 那叠纸的折痕是军驿函件的折法。我明白。留我一晚，别让我碰到你的灯。" | N3 | 需玩家具备 `trait.observant` **且**尚未触发过同类暗语（用复合条件 `all_of` + `not` 演示）| `disable_with_hint` |

**字段级伪 JSON 示意**：

```json
{
  "node_id": "arrival_waystation",
  "type": "dialogue",
  "narration": "<见上文 N1 叙述>",
  "speaker_ref": "char_vellin",
  "location_ref": "scene_waystation_of_iron_oath",
  "on_enter_effects": [],
  "options": [
    {
      "option_id": "opt_confront_letter",
      "text": "[按住那叠纸] 你手上沾的不是酒。",
      "target_node_id": "vellin_confession",
      "condition": null,
      "effects": [],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_sit_and_wait",
      "text": "给我续一杯。巡逻官来之前我就是个过路客。",
      "target_node_id": "patrol_arrives",
      "condition": null,
      "effects": [],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_read_the_room",
      "text": "[观察入微] 那叠纸的折痕是军驿函件的折法。我明白。留我一晚，别让我碰到你的灯。",
      "target_node_id": "patrol_arrives",
      "condition": {
        "all_of": [
          { "op": "has", "path": "player.traits", "value": "observant" },
          { "not": { "op": "eq", "path": "flag.read_the_room_used", "value": true } }
        ]
      },
      "effects": [
        { "op": "set", "path": "flag.read_the_room_used", "value": true },
        { "op": "inc", "path": "relationship.vellin.trust", "value": 1 }
      ],
      "unavailable_behavior": "disable_with_hint"
    }
  ]
}
```

> 演示点：分支（3 选项）· StateCondition 复合形态（`all_of` 套 `not`）· StateEffect（`set` + `inc`）· `unavailable_behavior` 的 `hide` 与 `disable_with_hint` 两种取值。

---

### 3.2 N2 · `vellin_confession`（dialogue）

**说话者**：`char_vellin`（坦白）

**on_enter_effects**：进入节点即标记玩家见过血信（演示 D3 启用的 `on_enter_effects`）。

**叙述文本**（≈260 字）：

> 你直视她的眼睛，把手按在那叠纸上。她没有躲，像是早料到这一刻。沉默了半盏茶的工夫，她把油灯挑亮了些，示意你看那封信。
>
> 笔迹潦草，墨水蹭在血上晕开：Aelwin——你记得这个名字，三年前和你一起守过陶窑山口的少年兵——在信里写道自己已经逃出铁誓卫队的补给线，正躲在东边的牧人废屋里等回信。他写道："我杀的是百夫长 Hael，他把我们当柴火用。我不后悔。只求你让我消失。"
>
> Vellin 把信合上，声音压得极低："如果铁誓拿到这张纸，Aelwin 会被挂在驿站门口风干三天。我想让他消失——真的消失，去北境，改个名字。
>
> 但我需要你装作从没来过。明早巡逻官要搜驿站，他听不得我半句谎话。你是过路人，你有借口。"

**选项**：

| option_id | 可见文本 | 目标 | 守卫 | unavailable_behavior |
|---|---|---|---|---|
| `opt_promise_silence` | "Hael 活该。我什么都没看见。" | N4 | 无 | `hide` |
| `opt_report_to_oath` | "我欠铁誓一份军饷。明早我会把事情告诉 Corvan。" | N5 | 无 | `hide` |

**字段级伪 JSON 示意**：

```json
{
  "node_id": "vellin_confession",
  "type": "dialogue",
  "narration": "<见上文 N2 叙述>",
  "speaker_ref": "char_vellin",
  "location_ref": "scene_waystation_of_iron_oath",
  "on_enter_effects": [
    { "op": "set", "path": "flag.player_saw_blood_letter", "value": true }
  ],
  "options": [
    {
      "option_id": "opt_promise_silence",
      "text": "Hael 活该。我什么都没看见。",
      "target_node_id": "end_silent_ally",
      "condition": null,
      "effects": [
        { "op": "inc", "path": "relationship.vellin.trust", "value": 2 },
        { "op": "set", "path": "flag.oath_broken_conspiracy", "value": true }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_report_to_oath",
      "text": "我欠铁誓一份军饷。明早我会把事情告诉 Corvan。",
      "target_node_id": "end_iron_blade",
      "condition": null,
      "effects": [
        { "op": "inc", "path": "faction.iron_oath.reputation", "value": 1 },
        { "op": "set", "path": "flag.aelwin_betrayed", "value": true }
      ],
      "unavailable_behavior": "hide"
    }
  ]
}
```

> 演示点：`on_enter_effects`（D3 决议启用）· Option 无守卫的 `condition: null` 形态 · StateEffect 多项数组。

---

### 3.3 N3 · `patrol_arrives`（dialogue）

**说话者**：`char_corvan`（巡逻官推门入内）

**叙述文本**（≈290 字）：

> 你含糊地岔开话题，接过酒去靠墙的长凳坐下。Vellin 开始收拾柜台，动作比平时慢了半拍。
>
> 三炷香后，门被马靴重重踢开。巡逻官 Corvan 走进来，两名持矛卫兵跟在身后。他摘下头盔，露出你再熟悉不过的那张脸——五年前你们一起在兰岭追过私盐队，也是在这间驿站烤过火。
>
> "Vellin。"他的声音没有寒暄，"我们查到有个逃兵的口信从这里过。你知道规矩。"
>
> 他的目光越过 Vellin，落在你身上，停留了两秒。"……你也在。"
>
> 你看到 Vellin 的手指无声地扣住了柜台边缘，指节发白。Corvan 的右手已经按在腰间剑柄上——那是他习惯性动作，不一定意味着杀意，但也不意味着他不会动手。
>
> 他转回头，对 Vellin 说："我给你一次机会。信在哪里？"

**选项**：

| option_id | 可见文本 | 目标 | 守卫 | unavailable_behavior |
|---|---|---|---|---|
| `opt_lie_for_vellin` | "Corvan，我进门到现在没见过什么信。我用兰岭那年我们烧过的旗发誓。" | N4 | 无 | `hide` |
| `opt_reveal_to_corvan` | "柜台油灯后面。那是逃兵 Aelwin 的字。" | N5 | 无 | `hide` |
| `opt_invoke_old_bond` | "[诉诸旧情] 兰岭那年你差点死在我刀下。今晚这一单，让我和 Vellin 自己了结。" | N4 | Corvan 信任值 ≥ 2 **或** 曾与 Corvan 共享过往（用 `any_of` 演示）| `disable` |

**字段级伪 JSON 示意**：

```json
{
  "node_id": "patrol_arrives",
  "type": "dialogue",
  "narration": "<见上文 N3 叙述>",
  "speaker_ref": "char_corvan",
  "location_ref": "scene_waystation_of_iron_oath",
  "on_enter_effects": [],
  "options": [
    {
      "option_id": "opt_lie_for_vellin",
      "text": "Corvan，我进门到现在没见过什么信。我用兰岭那年我们烧过的旗发誓。",
      "target_node_id": "end_silent_ally",
      "condition": null,
      "effects": [
        { "op": "inc", "path": "relationship.vellin.trust", "value": 1 },
        { "op": "dec", "path": "relationship.corvan.trust", "value": 1 }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_reveal_to_corvan",
      "text": "柜台油灯后面。那是逃兵 Aelwin 的字。",
      "target_node_id": "end_iron_blade",
      "condition": null,
      "effects": [
        { "op": "inc", "path": "faction.iron_oath.reputation", "value": 2 },
        { "op": "set", "path": "flag.aelwin_betrayed", "value": true }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_invoke_old_bond",
      "text": "[诉诸旧情] 兰岭那年你差点死在我刀下。今晚这一单，让我和 Vellin 自己了结。",
      "target_node_id": "end_silent_ally",
      "condition": {
        "any_of": [
          { "op": "gte", "path": "relationship.corvan.trust", "value": 2 },
          { "op": "has", "path": "player.bonds", "value": "lanridge_shared_past" }
        ]
      },
      "effects": [
        { "op": "inc", "path": "relationship.vellin.trust", "value": 1 },
        { "op": "set", "path": "flag.corvan_looked_away", "value": true }
      ],
      "unavailable_behavior": "disable"
    }
  ]
}
```

> 演示点：汇合（→ N4、→ N5 各两入边之一）· StateCondition 叶形态 + 复合 `any_of` 形态 · `unavailable_behavior` 的 `disable` 第三种取值。

---

### 3.4 N4 · `end_silent_ally`（end · 结局一）

**说话者**：`null`（旁白；D1 决议：旁白由 `speaker_ref = null` 表示，不作为独立节点类型）

**叙述文本**（≈155 字）：

> 三天后，东边的牧人废屋空了，灶里还留着一把没烧尽的信灰。铁誓卫队没有在补给线上抓到任何人。
>
> Vellin 把那杯没动过的酒替你留了一整年——这是后来你在北境收到的第一封她的信里写的。信末尾只有一句："欠你的，慢慢还。"
>
> 断剑与铁环的旗帜仍然挂在驿站顶上，只是你知道，它庇护的早已不是它声称的那些东西。

**字段级伪 JSON 示意**：

```json
{
  "node_id": "end_silent_ally",
  "type": "end",
  "narration": "<见上文 N4 叙述>",
  "speaker_ref": null,
  "location_ref": "scene_waystation_of_iron_oath",
  "options": []
}
```

> 演示点：`type = "end"` + `options = []`（D1 校验规则）· `speaker_ref = null` 旁白表达 · 该结局可由 `{N2→opt_promise_silence, N3→opt_lie_for_vellin, N3→opt_invoke_old_bond}` 三条入边中任一到达（BG3 式节点级容错）。

---

### 3.5 N5 · `end_iron_blade`（end · 结局二）

**说话者**：`null`（旁白）

**叙述文本**（≈160 字）：

> 铁誓卫队没有让你失望。Aelwin 被从牧人废屋里拖出来时还穿着你们当年在陶窑山口一起领的那件粗麻内衬。三日后他的尸体挂在驿站门口的铁架上，腐臭味要一整个春天才散得干净。
>
> Vellin 被押送回主城受审。临走前她没有看你一眼。
>
> Corvan 把一枚铜环塞进你手心："铁誓记你这一份。下次缺差事，来找我。"
>
> 你收起铜环，上马，没有回头。

**字段级伪 JSON 示意**：

```json
{
  "node_id": "end_iron_blade",
  "type": "end",
  "narration": "<见上文 N5 叙述>",
  "speaker_ref": null,
  "location_ref": "scene_waystation_of_iron_oath",
  "options": []
}
```

> 演示点：第二种结局；由 `{N2→opt_report_to_oath, N3→opt_reveal_to_corvan}` 两条入边汇合到达。

---

## 4. 演示点对照

| 要求 | 演示位置 | 说明 |
|---|---|---|
| (a) 分支：≥1 节点有 ≥2 选项 | N1（3 选项）、N2（2 选项）、N3（3 选项） | 全图 3 个 dialogue 节点都分支 |
| (b) 汇合：≥2 节点出边指向同一目标 | N4 由 N2、N3 汇入；N5 由 N2、N3 汇入 | 每个结局均有 ≥2 入边 |
| (c) 至少一次 StateEffect | N1.opt_read_the_room.effects、N2.on_enter_effects、N2/N3 几乎所有选项 effects | 含 `set`/`inc`/`dec` 候选 op |
| (d) 至少一次 StateCondition 作为选项守卫 | N1.opt_read_the_room.condition、N3.opt_invoke_old_bond.condition | 叶形态 + 复合形态都有 |
| (e) ≥1 结局节点可从 ≥2 条路径到达 | N4 三条入边（N2.opt_promise_silence、N3.opt_lie_for_vellin、N3.opt_invoke_old_bond）；N5 两条入边 | N4、N5 均满足 |
| (f) ≥2 种不同结局 | N4「沉默的同盟」、N5「铁誓之刃」 | 两结局叙事后果截然相反 |

---

## 5. Schema 覆盖度自检表

对 SCHEMA_v0.md v0.1.1 §3 标记为 🟢 的全部 **27 个阶段 0 必需字段**逐一清点本场景是否演示。字段归类依据 SCHEMA_v0.md §7.2。

### 5.1 DialogueGraph（6 个 🟢）

| 字段 | 状态 | 演示位置 |
|---|---|---|
| `schema_version` | ✅ 已演示 | §1.4 值为 `"0.1.1"` |
| `graph_id` | ✅ 已演示 | §1.4 值为 `"glades_ironoath_waystation"` |
| `entry_node_id` | ✅ 已演示 | §1.4 值为 `"arrival_waystation"` |
| `nodes` | ✅ 已演示 | §3.1–§3.5 五节点 |
| `scene_anchor` | ✅ 已演示 | §1.3 `"scene_waystation_of_iron_oath"` |
| `character_refs` | ✅ 已演示 | §1.2 三角色数组 |

### 5.2 Node（6 个 🟢）

| 字段 | 状态 | 演示位置 |
|---|---|---|
| `node_id` | ✅ 已演示 | 五节点各一 ID |
| `type` | ✅ 已演示 | N1/N2/N3 用 `"dialogue"`；N4/N5 用 `"end"`（两枚举值齐全）|
| `narration` | ✅ 已演示 | §3.1–§3.5 每节点有叙述文本 |
| `speaker_ref` | ✅ 已演示 | 非 null（N1=Vellin、N2=Vellin、N3=Corvan）与 null（N4、N5 旁白）两形态齐全 |
| `location_ref` | ✅ 已演示 | 五节点均引用 `scene_waystation_of_iron_oath` |
| `options` | ✅ 已演示 | 含 dialogue 节点非空数组（D1 规则）与 end 节点空数组（D1 规则）两种合法形态 |

### 5.3 Option（6 个 🟢）

| 字段 | 状态 | 演示位置 |
|---|---|---|
| `option_id` | ✅ 已演示 | 八个选项均独立 ID |
| `text` | ✅ 已演示 | 八个选项均有玩家可见文本 |
| `target_node_id` | ✅ 已演示 | 八条出边合法指向 |
| `condition` | ✅ 已演示 | 含 `null`（大多数）与非 null（N1.opt_read_the_room、N3.opt_invoke_old_bond）两形态 |
| `effects` | ✅ 已演示 | 含空数组（N1.opt_confront_letter、N1.opt_sit_and_wait）与非空数组（N2/N3 多处）两形态 |
| `unavailable_behavior` | ✅ 已演示 | 三枚举值 `hide`、`disable`、`disable_with_hint` 均有实例（分别在 N1.opt_confront_letter / N3.opt_invoke_old_bond / N1.opt_read_the_room）|

### 5.4 StateEffect（3 个 🟢）

| 字段 | 状态 | 演示位置 |
|---|---|---|
| `op` | ✅ 已演示 | 使用候选集中的 `set`、`inc`、`dec`（D6 推迟，最终白名单由 `/state` 任务确定）|
| `path` | ✅ 已演示 | 点分字符串示意，例如 `"relationship.vellin.trust"`（D5 推迟，表示法由 `/state` 任务确定）|
| `value` | ✅ 已演示 | 含布尔（`true`）、整数（`1`/`2`）两种基本类型 |

### 5.5 StateCondition（6 个 🟢）

| 字段 | 状态 | 演示位置 |
|---|---|---|
| `op` | ✅ 已演示 | 叶形态：`has`（N1.opt_read_the_room）、`gte`（N3.opt_invoke_old_bond）、`eq`（N1 内嵌 `not` 子条件）|
| `path` | ✅ 已演示 | 叶形态多处 |
| `value` | ✅ 已演示 | 含字符串（`"observant"`）、布尔（`true`）、整数（`2`）|
| `all_of` | ✅ 已演示 | N1.opt_read_the_room.condition 外层 |
| `any_of` | ✅ 已演示 | N3.opt_invoke_old_bond.condition 外层 |
| `not` | ✅ 已演示 | N1.opt_read_the_room.condition 内层（嵌于 `all_of` 的第二项）|

### 5.6 合计

| 对象 | 🟢 字段总数 | 本场景覆盖数 | 未覆盖 |
|---|---|---|---|
| DialogueGraph | 6 | 6 | 0 |
| Node | 6 | 6 | 0 |
| Option | 6 | 6 | 0 |
| StateEffect | 3 | 3 | 0 |
| StateCondition | 6 | 6 | 0 |
| **合计** | **27** | **27** | **0** |

**结论**：本场景完整演示了 SCHEMA_v0.md v0.1.1 的全部 27 个 🟢 阶段 0 必需字段（含所有枚举值、所有可 null 字段的两种形态、StateCondition 的叶 / 复合两形态及三种复合键）。无需追加演示节点，也无需接受任何覆盖空缺。

**未清点项说明**：🟡 字段（如 `on_enter_effects`、`generation_trace`、`authoring` 等）不在本检查范围内。本场景顺带演示了 `on_enter_effects`（N2），但未演示 `generation_trace`、`authoring`、`plugin_metadata`、`faction_clocks_touched`、`reachability_condition`、`ontology_ref`、`faction_clock_op`——这些是 🟡 预留字段，不是 🟢 阶段 0 必需；T-0.8 落地 JSON 时可按需选演。

---

## 6. 错误变体（供 validator 实现参考）

以下三章各给出一个**故意坏掉**的场景变体。每个变体基于第 3 节的基准场景，只描述**差异点**，不重写完整图。T-0.9 的 validator 应能对每种变体给出明确拒收原因。

### 6.1 错误变体 E1 · 悬空引用（Dangling Reference）

**例一：`target_node_id` 指向不存在节点**

基准场景的 N3.opt_reveal_to_corvan.target_node_id 从 `"end_iron_blade"` 改为 `"end_iron_gallows"`。`nodes` 映射中不存在该 ID，其他字段保持合法。

```json
{
  "option_id": "opt_reveal_to_corvan",
  "text": "柜台油灯后面。那是逃兵 Aelwin 的字。",
  "target_node_id": "end_iron_gallows",
  "condition": null,
  "effects": [ /* 同基准 */ ],
  "unavailable_behavior": "hide"
}
```

**预期 validator 拒收**：`Option.target_node_id` 必须存在于同图 `nodes` 映射中（SCHEMA_v0.md §3.3 `target_node_id` 说明）。

**例二：`speaker_ref` 指向本体外的 ID**

基准场景的 N3.speaker_ref 从 `"char_corvan"` 改为 `"char_corvax_the_unknown"`，且该 ID 未在 `character_refs` 中声明、也未在本体花名册中注册。

**预期 validator 拒收**：违反 ADR-006 + DEBATE §6.5 的一致性校验——图内所有 `speaker_ref`（非 null）必须同时出现在 `character_refs` 且在本体花名册中可解析。具体的本体校验器实现依赖 `/state/ontology/` 任务，但**图内声明闭合性**（图内 `speaker_ref` ⊆ `character_refs`）在 T-0.9 validator 首版即可执行。

---

### 6.2 错误变体 E2 · 不可达节点（Unreachable Node）

在基准场景中插入第六个节点 `orphan_warning_from_vellin`，该节点：

- 合法定义（`node_id`、`type = "dialogue"`、`narration`、`speaker_ref = "char_vellin"`、`location_ref`、非空 `options` 数组）
- **但没有任何其他节点的出边指向它**
- `entry_node_id` 仍为 `arrival_waystation`，不是该孤岛节点

```json
{
  "node_id": "orphan_warning_from_vellin",
  "type": "dialogue",
  "narration": "Vellin 想在你离开前告诉你最后一件事——但没有任何路径把你引到这里。",
  "speaker_ref": "char_vellin",
  "location_ref": "scene_waystation_of_iron_oath",
  "options": [
    {
      "option_id": "opt_dummy",
      "text": "（此选项永远不会被玩家看到）",
      "target_node_id": "end_silent_ally",
      "condition": null,
      "effects": [],
      "unavailable_behavior": "hide"
    }
  ]
}
```

**预期 validator 拒收**（拓扑层校验，对应 ADR-009 第二层 + SCHEMA_v0.md §2.1 "节点集合"语义）：从 `entry_node_id` 出发的可达节点集合必须覆盖 `nodes` 映射中的所有节点。孤岛节点是阶段 0 校验器必须能检出的最基本拓扑缺陷。

---

### 6.3 错误变体 E3 · Schema 违反（Schema Violation）

三个子变体各独立出现：

**E3a · 必需字段缺失**：基准场景的 N2 对象**删除** `narration` 字段。其他字段合法。

**预期 validator 拒收**：`Node.narration` 是 🟢 必需字段（SCHEMA_v0.md §3.2）。JSON Schema 层即应在 `required` 中列出该字段，违反者在最外层 Schema 校验即失败，无需进入拓扑层。

**E3b · 类型错误**：基准场景的 N1.options 字段从数组写成对象：

```json
{
  "node_id": "arrival_waystation",
  "options": {
    "opt_confront_letter": { /* ... */ },
    "opt_sit_and_wait": { /* ... */ }
  }
}
```

**预期 validator 拒收**：`Node.options` 类型为 `Option[]`（SCHEMA_v0.md §3.2）；对象形态违反类型约束。同样在 JSON Schema 层即应失败。

**E3c · ID 不符合 D7 正则**：基准场景的 `graph_id` 从 `"glades_ironoath_waystation"` 改为 `"Glades.WayStation#01"`：

- 含大写字母（违反 `^[a-z0-9_-]+$` 中的"仅小写"）
- 含 `.`（D7 明文禁用）
- 含 `#`（不在允许集内）

```json
{
  "schema_version": "0.1.1",
  "graph_id": "Glades.WayStation#01",
  "entry_node_id": "arrival_waystation",
  /* 其他字段同基准 */
}
```

**预期 validator 拒收**：D7 决议固定的正则 / 长度 / 禁用字符规则。正则应由 JSON Schema 的 `pattern` 关键字强制。

**附加样例**（option_id 违规）：将 N3.opt_invoke_old_bond.option_id 改为 `"opt/invoke old bond"`（含斜杠 + 空格）——违反 `^[a-zA-Z0-9_-]+$` 正则，亦应被拒。

---

## 7. 后续任务的衔接提示

### 7.1 T-0.8（手写 JSON 内容）

- 以本文件第 3 节为蓝本生成 `/content/` 下的五节点场景 JSON。
- 落地时 `path` 表示法需与 T-0.5（状态总线 Schema）的最终选择对齐；若 T-0.5 采纳**段数组**形式（D5 选项 B），本文件示意中的 `"relationship.vellin.trust"` 须改写为 `["relationship", "vellin", "trust"]`。
- `op` 具体枚举值需与 T-0.5 的白名单对齐；若本文件使用的候选起点（`set`/`inc`/`dec`/`has`/`gte`/`eq`）在白名单中被重命名或删除，手写 JSON 须跟随调整。
- 本体锚点 ID（`scene_waystation_of_iron_oath`、`char_vellin` 等）在本体 Schema 任务完成前是占位符；T-0.8 落地时须在本体花名册中补登三名角色与一个地点，否则 `character_refs` 与 `speaker_ref` 的闭合性校验会失败。

### 7.2 T-0.9（validator 实现）

validator 首版至少需能对本文件第 6 章三种错误变体给出拒收：

1. **Schema 层**（JSON Schema 关键字）：E3a 必需字段缺失、E3b 类型错误、E3c 正则违反。
2. **图论层**（拓扑校验）：E1 例一（悬空 `target_node_id`）、E2（不可达节点）。
3. **一致性层**（跨图 / 跨本体引用）：E1 例二（`speaker_ref` 超出 `character_refs` 闭合集）。第三类在本体 Schema 落地前可先实现**图内闭合**子集。

三层对应 ADR-009 第一 / 第二层评测的子集；第三层（LLM-as-judge + 模拟）不在 T-0.9 范围内。

---

## 8. 版本

本文件版本：v0.1（T-0.3 初稿）
依赖 SCHEMA_v0.md 版本：v0.1.1（`schema_version` = `0.1.1`）
最后更新：2026-04-23

### 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | T-0.3 初稿：《铁誓驿站》5 节点场景 + 27 个 🟢 字段全覆盖 + 3 种错误变体 |
