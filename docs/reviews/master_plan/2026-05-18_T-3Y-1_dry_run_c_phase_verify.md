# T-3Y-1 mini prototype 实测报告（dry-run report）

> **日期**：2026-05-18
> **状态**：✅ 成功
> **任务**：T-3Y-1 节点级文本生成 mini prototype 端到端 dry-run
> **节点**：`node_3_info_offer`（A1 dry-run §3.7.3 露西对话节点）
> **场景**：`scene_inn_meet_lucy`（克苏鲁版极乐迪斯科 spiritual successor / 酒馆见露西）

---

## 1. 生成结果（generated narration + options）

### Narration（旁白；199 字）

厨房后门半掩，雨水在门槛外积成一条暗线。露西把托盘扣在水槽边，袖口沾着啤酒沫，目光越过你的肩头，停在角落那两件深色西装上。她从围裙内袋摸出一张黑边名片，先用杯底压住，只露出一个烫银的“V”。「莱特白天讲古文字，夜里换一件旧外套，从后巷上车。他不让人叫教授，只让人叫赖特先生。」她把声音压低，指节贴着杯沿。「有一次他醉了，提到乡下那间小屋，说壁炉后面比银行安静。第二天，给他递名片的人就来这里找我。」

### Options（选项；4 个）

- **opt_continue_press**: 我还要知道他夜里的事。
- **opt_warn_about_vick**: 我能让你避开那两人。
- **opt_press_for_cache**: [察言观色]我想听小屋的事。 *(检定条件 condition: `{"op": "gte", "path": "relationship.lucy.trust", "value": 2}`)*
- **opt_betray_lucy_to_eyes**: 我去和角落那两人谈。

---

## 2. 评估元数据（evaluation metadata）

### 2.1 Rubric scorer 评分（0-10 分）

| 维度（dimension） | 分数（score） | 计算痕迹（trace） |
|---|---|---|
| **信息密度（information_density）** | **8.71** | `{"narration_char_count": 171, "option_count": 4, "quote_count": 3, "formula": "(chars/50)*0.5 + options*1.0 + quotes*1.0", "raw_base_before_clamp": 8.71}` |
| **白描合规度（baimiao_compliance）** | **10.00** | `{"narration_char_count": 171, "evaluation_word_count": 0, "figurative_word_count": 0, "violation_density_per_100_chars": 0.0, "formula": "10 - (eval+figurative)/(chars/100) * 2"}` |

### 2.2 Anti-pattern detector flags（程序化检测）

无 anti-pattern 触发（程序化检测 AP-7/8/10 全 clean）

**未程序化（LLM-as-judge 待办）**：AP-1 对仗式 / AP-2 修辞失底 / AP-3 物理方向 /
AP-4 假靶子否定 / AP-5 总结代细节 / AP-6 锚定未说明标准 / AP-9 读不懂的省略 ——
本报告本节点这 7 条未自动检测；留待作者人工 [A]/[R]/[S] 段判定。

---

## 3. 实测 metrics（实测 token + 耗时 + 成本）

| 指标（metric） | 值 |
|---|---|
| **模型（model）** | `gpt-5.5` |
| **input_tokens** | 3966 |
| **output_tokens** | 1190 |
| **实际成本（actual_cost_usd）** | $0.0222 |
| **LLM 调用耗时（elapsed_sec_llm）** | 25.43 s |
| **总耗时（elapsed_sec_total）** | 25.44 s |
| **finish_reason** | `stop` |
| **开始时间（started_at）** | 2026-05-18 20:34:42 |

---

## 4. Forward Planner 输入（编剧意图 + 玩家状态）

### 4.1 模块 A intent（剧本意图层）

- **foreground_goal**: `r1_wright_double_life.stage_2`
- **background_seeds**: `["S2_vick_dangerous", "S4_country_cottage_cache"]`

### 4.2 模块 B state_summary（状态摘要层）

**relevant_known_info（结构化短列表）**：

  - `knowledge.wright_dead` (阶段 stage 1)
  - `knowledge.lucy_known_to_player`
  - `knowledge.gangster_watching_lucy`

**all_known_info_summary（全局背景；不入 schema）**：

> 玩家是私家侦探，受雇调查教授莱特之死。已走访莱特办公室，发现破镜 + 烧过文件 + 散落的赌债借条。露西是莱特的情人 + 希博公路酒馆侍应；玩家刚被引荐到酒馆。酒馆角落桌有两个穿西装的男人在监视露西方向——大西洋城打手风格。倒计时：通路征兆显现等级 1（远处的幻听 / 转角的影子）。

### 4.3 模块 C reconcile

- **verdict**: `pass`

---

## 5. NPC 状态机快照（npc_state）

```json
{
  "name": "Lucy",
  "current_persona": "wary_but_warming",
  "relationship_with_player": {
    "trust": 1,
    "fear": 2,
    "affinity": 1
  },
  "current_emotion": "受惊但努力镇定",
  "knows_about_culprit": "vick",
  "secret_layer_1": "wright 赌债 / 大西洋城打手",
  "secret_layer_2_locked": "vick 名片 + 弗林德斯监视细节（需 trust ≥ 2 解锁）"
}
```

---

## 6. 待人工审稿 [A]/[R]/[S] 段（accept / revise / scrap）

> 作者按以下三档标注，作为 T-3Y-1 实证完成的最后一步：
>
> - **[A] Accept**：narration 或 option 文本可直接采用
> - **[R] Revise**：需要小修订
> - **[S] Scrap**：需要重生成

| 段落 | 内容片段 | 你的标注 |
|---|---|---|
| Narration | （见上文 §1） | [_] |
| opt_continue_press | `我还要知道他夜里的事。` | [_] |
| opt_warn_about_vick | `我能让你避开那两人。` | [_] |
| opt_press_for_cache | `[察言观色]我想听小屋的事。` | [_] |
| opt_betray_lucy_to_eyes | `我去和角落那两人谈。` | [_] |

整体接受率（gross_pass_rate）= [A] / ([A] + [R] + [S]) = _____

---

## 7. 工程层附录

### 7.1 调用链 trace

```json
{
  "started_at": "2026-05-18 20:34:42",
  "model_id": "gpt-5.5",
  "steps": [
    {
      "step": "env_loaded",
      "base_url": "https://poloai.top/v1",
      "model_id": "gpt-5.5"
    },
    {
      "step": "scene_loaded",
      "graph_id": "scene_inn_meet_lucy",
      "node_id": "node_3_info_offer",
      "scene_seeds": 2,
      "scene_reveals": 1
    },
    {
      "step": "forward_planner",
      "foreground_goal": "r1_wright_double_life.stage_2",
      "background_seeds": [
        "S2_vick_dangerous",
        "S4_country_cottage_cache"
      ],
      "relevant_known_count": 3,
      "reconcile_verdict": "pass"
    },
    {
      "step": "prompt_rendered",
      "system_chars": 3984,
      "user_chars": 3723
    },
    {
      "step": "budget_charged",
      "record_id": "1c9910a9e45a474d8a2924179f187220",
      "estimated_cost_usd": 0.021852,
      "est_input_tokens": 1926,
      "est_output_tokens": 1500
    },
    {
      "step": "llm_call_complete",
      "input_tokens": 3966,
      "output_tokens": 1190,
      "actual_cost_usd": 0.022212,
      "elapsed_sec_llm": 25.433834075927734,
      "finish_reason": "stop"
    },
    {
      "step": "evaluation_complete",
      "anti_pattern_flags": 0,
      "rubric_information_density": 8.71,
      "rubric_baimiao_compliance": 10.0
    }
  ]
}
```

### 7.2 prompt 全文（system + user）

<details>
<summary>system prompt（点开展开）</summary>

```text
你是 Forgewright RPG 项目的**节点级**对话生成器。

## 输入
- 1 个**节点骨架**（含 node_id / speaker_ref / location_ref / on_enter_effects / options 骨架）
- Forward Planner 输出（player_known_info / foreground_goal / background_seeds / NPC 当前 state）

## 输出
- 必须是 valid JSON 单对象，**形态 = 完成后的 Node**（含 narration + 每个 option 的 text 字段）。
- **JSON-only 硬约束**：输出第一个字符必须是 `{`，最后一个字符必须是 `}`；不得包含任何 markdown 围栏（```）/ 自然语言开场白 / 注释 / 控制 token（`<think>` 等）。
- **不要修改输入骨架的结构**：node_id / type / speaker_ref / location_ref / option_id / target_node_id / condition / effects / unavailable_behavior 全部保留原值；你只填 `narration` 和 `options[].text` 两类字段。


## 3 分类角色守则（A1 反馈 v0.1 §3）

每个节点的文本严格分为 3 类，每类有不同的工程契约。**违反任一条 = 不合规**。

### 1. 旁白（Narration）— 第三人称叙述者视角

**可以写的**：
- 物理环境描写（光线 / 声音 / 气味 / 场景布置 / 时间）
- 客观物理动作（NPC 的肢体动作 / 道具操作 / 移动）
- 玩家可直接观察到的细节

**禁止写**：
- ✗ NPC 的内心活动（应通过 NPC 自己的话或动作暗示）
- ✗ NPC 的台词信息（必须由 NPC 自己说出来；典型违规：「她说莱特在人前是教授，人后是另一种人……」——必须改成露西直接说）
- ✗ 玩家的内心活动 / 价值判断（应通过选项让玩家自己做）
- ✗ 总结性评价（"她很狡猾"——用具体行为代替）

### 2. NPC

#### 2a. 旁白带 NPC 名字 / 代词的主谓宾
- 主语：NPC 名字 / 代词
- 写 NPC 的动作 / 表情 / 视线 / 物理姿态
- 例：「露西把空杯子往水槽里一放」/「她的指尖按着那张名片」

#### 2b. NPC 直接说的话（引号内）
- 形态：中文 `"..."` 或 `「」` 包裹的引述
- 写 NPC 此刻说的话本身（必须是 NPC 角色会说的语言 / 措辞 / 节奏）
- 例：「教授的朋友可真多。」露西低声说。
- **工程契约**：NPC 直接说的话必须包含场景的关键信息（不能让旁白替代）

### 3. 玩家

#### 3a. 旁白以玩家为主语
- 主语：「你」/ 玩家代词
- 写玩家的物理感受 / 不可控的反应（疲倦 / 寒意 / 心跳 / 视野模糊）
- 例：「你感到酒精在血液里慢慢散开」
- **限制**：不要替玩家做价值判断或决定（"你决定要……" 是错的）

#### 3b. 玩家说的话或做的动作（option.text）
- 形态：node.options[].text
- 写玩家此刻要说的话 / 要做的动作本身（**第一人称语言**）
- 正例：「我不是来审你。我想知道他到底怎么死的。」
- 正例：「[观察入微] 先把酒馆里不喝酒的人记下来。」（检定标记 + 第一人称动作）
- **反例（禁止）**：「先追问赌债和维克名片，把浅层线索坐实。」（第三人称意图描述）
- **检定标记**：可保留 `[skill_name]` 前缀作为"激活该选项所需技能"提示，但**主体必须第一人称**


## Anti-pattern 黑名单（A1 反馈 v0.1 §2；10 条；违反 = 不合规）

### AP-1: AI 对仗式 / 重复对应感过强
- 单段内避免成对对仗式结构；前半已暗示的，后半不要重复明示
- 反例：「前厅摆着……像一张给警察和好人看的脸；真正的热闹从后门那条窄楼梯往下漏」（前半已暗示"另一面"，后半冗余）

### AP-2: 修辞失底（喻体与本体无共同点）
- 用比喻 / 类比前必须明示喻体和本体的共同点；说不清就直接白描，不用修辞
- 反例：「托盘在她指尖稳得像变戏法」（"变戏法" 与"托盘稳" 无共同点）
- 反例：「你别摆那副法官脸」（"法官脸" 究竟指什么——正义？审视？怀疑？——无线索）

### AP-3: 修辞方向 / 物理逻辑错误
- 用动词 / 修辞前检查物理方向 / 逻辑是否与场景一致
- 反例：「真正的热闹从后门那条窄楼梯往下漏」（"漏" 是从上往下，但热闹是从地下传上来的，方向相反）

### AP-4: 假靶子否定
- 否定句必须否定读者真实预期的靶子；不要竖一个读者本来没预期的靶子去否定
- 反例：「名字落下去时，露西脸上的笑没有碎」（没人预期笑会"碎"）
- 改法：直接写"露西脸上的笑只是停了一拍"

### AP-5: 总结代细节
- 先给具体行为 / 物理细节，避免直接给评价；如果必须给评价，前后要有具体细节铺垫
- 反例：「眼神却老练得不像二十五六岁的人」（"老练"是评价，无可观察细节）
- 正例：「她扫了你一眼，先看鞋，再看手，再看你有没有像常客那样急着找酒」（具体行为）

### AP-6: 锚定未说明的标准
- 不要引入读者不知道的"一般标准"作为对比基准
- 反例：「她的金发颜色新得过分」（"金发的一般标准"读者不知道）
- 改法：写具体细节（如"她的金发还有刚染过的化学气味"）

### AP-7: 旁白抢 NPC 的台词【程序化检测】
- 信息属于 NPC 的，必须用 NPC 直接说的话呈现；旁白只描写物理现象 + 客观环境 + 玩家可观察的细节
- 反例：narration 含「她说莱特在人前是教授，人后是另一种人……」/「他带她去过大西洋城……」（这些信息本应让 NPC 自己说）
- 程序化检测：narration 含「她说 / 他说 / 她告诉你 / 他告诉你 / 她解释 / 他解释」等转述模式 → flag

### AP-8: 选项第三人称化【程序化检测】
- option.text 必须是玩家本人的第一人称语言；`[skill_name]` 检定标记可保留在前
- 反例：「先追问赌债和维克名片，把浅层线索坐实」（第三人称意图描述）
- 反例：「追问那个大学生：给我名字或住址」（"追问那个大学生"是第三人称）
- 程序化检测：option.text 是否以「追问 / 共情 / 警告 / 离开 / 先 / 把 / 与 / 向 / 对」等动词或动作概括开头（去掉 `[skill]` 前缀后判断）→ flag

### AP-9: 读不懂的省略
- 留白前必须确保读者有线索能 fill in；如果线索还没出现，直接交代
- 反例：「有些人欠钱会怕打手，莱特怕的不是打手」（莱特怕的是什么？读者不知道）

### AP-10: 指代不清 / 用单字代称自己【程序化检测】
- 第一人称对话避免用"女孩 / 男孩 / 小孩"等单字代称自己；写"我"或具体名字
- 反例：「女孩也得活下去，你别摆那副法官脸」（露西用"女孩"指代自己）
- 程序化检测：NPC 引号内文本含「女孩 / 男孩 / 小孩 / 老娘」等单字代称 → flag


## 输出字段语义（违反 = 不合规）

### narration（旁白）
- 字数：**150 ~ 400 汉字**之间
- 严格遵守"3 分类角色守则"中的旁白契约——只写物理环境 / NPC 物理动作 / 玩家可观察细节
- **不要在 narration 中替 NPC 转述信息**（违反 AP-7）；NPC 要传达的内容必须放在 NPC 引号内对白里

### options[].text（玩家选项文本）
- 每条 ≤ **25 汉字**
- 严格遵守"3 分类角色守则"中的玩家契约——**第一人称语言**，不是第三人称意图描述（违反 AP-8）
- `[skill_name]` 检定前缀可保留；主体必须第一人称

### 必须承载 foreground_goal
- 本节点 narration + options 的核心信息密度**必须围绕 foreground_goal**（Forward Planner 给出的本节点承载的 reveal + stage）
- foreground_goal 是「编剧期望玩家在本节点知道什么 / 体验什么」的最终判定

### 必须埋下 background_seeds
- Forward Planner 给出的 background_seeds（list of seed_id）必须在本节点的 narration 或 NPC 对白中以**含蓄但有信息量**的方式埋下
- 不要喧宾夺主——seed 是埋的，不是直说的

### 必须基于 player_known_info
- player_known_info 是玩家**已知**的信息列表——你写 NPC 对白时**不要让 NPC 重复玩家已知**
- 写 NPC 对白时假设玩家已知 player_known_info 中列出的全部 knowledge

```

</details>

<details>
<summary>user message（点开展开）</summary>

```text
## 玩家已知信息（player_known_info）

**结构化清单（relevant_known_info）**：
- `knowledge.wright_dead`（阶段 1）
- `knowledge.lucy_known_to_player`
- `knowledge.gangster_watching_lucy`

**全局背景摘要（all_known_info_summary）**：
玩家是私家侦探，受雇调查教授莱特之死。已走访莱特办公室，发现破镜 + 烧过文件 + 散落的赌债借条。露西是莱特的情人 + 希博公路酒馆侍应；玩家刚被引荐到酒馆。酒馆角落桌有两个穿西装的男人在监视露西方向——大西洋城打手风格。倒计时：通路征兆显现等级 1（远处的幻听 / 转角的影子）。

**写作约束**：写 NPC 对白时假设玩家已经知道以上信息；不要让 NPC 重复说一遍。

---

## 本节点的 foreground_goal（前景目标）

**`r1_wright_double_life.stage_2`**

**写作约束**：本节点 narration + NPC 对白 + options 的核心信息密度**必须围绕**此 foreground_goal。

---

## 本节点要埋的 background_seeds（背景种子）

- `S2_vick_dangerous`
- `S4_country_cottage_cache`

**写作约束**：seed 必须以**含蓄但有信息量**的方式埋在 narration 或 NPC 对白中——不要喧宾夺主、不要直接 lecture（说教）；让玩家自己注意到。

---

## NPC 当前 state（来自状态机查询）

**主讲 NPC**: `char_lucy`

**state 快照**：
```json
{
  "name": "Lucy",
  "current_persona": "wary_but_warming",
  "relationship_with_player": {
    "trust": 1,
    "fear": 2,
    "affinity": 1
  },
  "current_emotion": "受惊但努力镇定",
  "knows_about_culprit": "vick",
  "secret_layer_1": "wright 赌债 / 大西洋城打手",
  "secret_layer_2_locked": "vick 名片 + 弗林德斯监视细节（需 trust ≥ 2 解锁）"
}
```

---

## 节点骨架（不要修改 narration / options[].text 之外的字段）

```json
{
  "node_id": "node_3_info_offer",
  "type": "dialogue",
  "narration": "",
  "speaker_ref": "char_lucy",
  "location_ref": "scene_inn",
  "on_enter_effects": [
    {
      "op": "set",
      "path": "flag.lucy_opened_up",
      "value": true
    }
  ],
  "options": [
    {
      "option_id": "opt_continue_press",
      "text": "",
      "target_node_id": "node_5_end_ally",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.lucy_knows_wright_lower_life",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_warn_about_vick",
      "text": "",
      "target_node_id": "node_5_end_ally",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.lucy_alerted",
          "value": true
        },
        {
          "op": "inc",
          "path": "relationship.lucy.trust",
          "value": 1
        }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_press_for_cache",
      "text": "",
      "target_node_id": "node_5_end_ally",
      "condition": {
        "op": "gte",
        "path": "relationship.lucy.trust",
        "value": 2
      },
      "effects": [
        {
          "op": "set",
          "path": "flag.cache_known",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        }
      ],
      "unavailable_behavior": "disable_with_hint"
    },
    {
      "option_id": "opt_betray_lucy_to_eyes",
      "text": "",
      "target_node_id": "node_6_end_cold",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.lucy_betrayed_to_gangs",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": false
        },
        {
          "op": "dec",
          "path": "relationship.lucy.trust",
          "value": 999
        }
      ],
      "unavailable_behavior": "hide"
    }
  ],
  "background_seeds": [
    "S2_vick_dangerous",
    "S4_country_cottage_cache"
  ],
  "foreground_goal": "r1_wright_double_life.stage_2"
}
```

---

## 任务

请按 system prompt 的输出 JSON 形态返回完成后的 Node 对象。
```

</details>

### 7.3 raw LLM 输出

```json
{
  "node_id": "node_3_info_offer",
  "type": "dialogue",
  "narration": "厨房后门半掩，雨水在门槛外积成一条暗线。露西把托盘扣在水槽边，袖口沾着啤酒沫，目光越过你的肩头，停在角落那两件深色西装上。她从围裙内袋摸出一张黑边名片，先用杯底压住，只露出一个烫银的“V”。「莱特白天讲古文字，夜里换一件旧外套，从后巷上车。他不让人叫教授，只让人叫赖特先生。」她把声音压低，指节贴着杯沿。「有一次他醉了，提到乡下那间小屋，说壁炉后面比银行安静。第二天，给他递名片的人就来这里找我。」",
  "speaker_ref": "char_lucy",
  "location_ref": "scene_inn",
  "on_enter_effects": [
    {
      "op": "set",
      "path": "flag.lucy_opened_up",
      "value": true
    }
  ],
  "options": [
    {
      "option_id": "opt_continue_press",
      "text": "我还要知道他夜里的事。",
      "target_node_id": "node_5_end_ally",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.lucy_knows_wright_lower_life",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_warn_about_vick",
      "text": "我能让你避开那两人。",
      "target_node_id": "node_5_end_ally",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.lucy_alerted",
          "value": true
        },
        {
          "op": "inc",
          "path": "relationship.lucy.trust",
          "value": 1
        }
      ],
      "unavailable_behavior": "hide"
    },
    {
      "option_id": "opt_press_for_cache",
      "text": "[察言观色]我想听小屋的事。",
      "target_node_id": "node_5_end_ally",
      "condition": {
        "op": "gte",
        "path": "relationship.lucy.trust",
        "value": 2
      },
      "effects": [
        {
          "op": "set",
          "path": "flag.cache_known",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": true
        }
      ],
      "unavailable_behavior": "disable_with_hint"
    },
    {
      "option_id": "opt_betray_lucy_to_eyes",
      "text": "我去和角落那两人谈。",
      "target_node_id": "node_6_end_cold",
      "condition": null,
      "effects": [
        {
          "op": "set",
          "path": "flag.lucy_betrayed_to_gangs",
          "value": true
        },
        {
          "op": "set",
          "path": "flag.player_got_vick_card",
          "value": false
        },
        {
          "op": "dec",
          "path": "relationship.lucy.trust",
          "value": 999
        }
      ],
      "unavailable_behavior": "hide"
    }
  ],
  "background_seeds": [
    "S2_vick_dangerous",
    "S4_country_cottage_cache"
  ],
  "foreground_goal": "r1_wright_double_life.stage_2"
}
```

---

## 8. 落档信息

- **产出方**：T-3Y-1 工程会话（claude/eloquent-mclean-8f0bd9 worktree）
- **依赖**：ADR-016 v0.4（knowledge.* 命名空间）+ ADR-034 D4-D11（场景级字段）+ ADR-029（技能体系）+ ADR-002/004（运行时无 LLM；生产期分离）
- **commit 范围**：goal 1（schema + Forward Planner stubs + state_path_validator）+ goal 2（prompt 模板 + node_text_gen + anti_pattern_detector + rubric scorer）+ goal 3（本 dry-run）
