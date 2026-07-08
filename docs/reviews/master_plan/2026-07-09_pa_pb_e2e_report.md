# T-3P-3 ｜ ADR-039 首版核心闭环 E2E 实测报告（P-A + P-B + 验收 + 落地 + 播放）

> **性质**：L3 施工会话 A 阶段 E2E 实测产物（参 T-3.10 先例：A 阶段含实测 + 报告）。
> **日期**：2026-07-09 · **分支**：`claude/t3p3-acceptance-e2e`（基线 main `3be51d1`）。
> **任务**：[/docs/prompts/stage_3/T-3P-3.md](../../prompts/stage_3/T-3P-3.md) · **拆解**：[2026-06-29_pa_pb_task_breakdown.md](2026-06-29_pa_pb_task_breakdown.md) §5.4。

本报告是 ADR-039 重定义的**阶段 3 完成标志口径**的 concrete 证据：
「**结构 → 提示词包 → （编剧任意来源回流）→ 验收落地播放** 的核心闭环跑通，且对一份
回流场景能给出正确通过 / 失败判定」（ROADMAP.md:210）。

---

## 0. TL;DR

| 环节 | 结果 |
|---|---|
| ① P-A 渲染写作提示词包（35 节点块） | ✅ rc=0 |
| ② P-B 合并回流 → scene.json（35 节点） | ✅ rc=0 |
| ③ 验收闸（三层 + 机械 human + AP 记录） | ✅ **PASS**（硬拦 0；37 条本体解析待挂、0 AP flag） |
| ④ `--land` 落地 content/_e2e_writer_loop/ + 版本 sidecar | ✅ v1 / `generation_method=writer_ingest` |
| ⑤ `python -m engine <scene.json>` 终端玩通到结局 | ✅ rc=0，reach「—— 结局 ——」 |
| ⑥ 反例·格式层（坏回流 4 类 E 错误） | ✅ 正确退回单，rc=1，未产 scene.json |
| ⑦ 反例·语义层（非法 graph 喂验收管线） | ✅ 正确 FAIL（硬拦 4 条） |

全仓测试：**1572 → 1586 passed / 6 skipped**（+14，全部本任务新增；0 regression）。

---

## 1. 全链命令 + 产物路径

所有命令从仓库根执行，0 LLM。复现脚本见
[`generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/README.md`](../../../generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/README.md)。

### ① P-A 渲染（T-3P-1，复用不改）

```
$ python -m generator.promptpack.render_pack \
    --design generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
    --spec   generator/experiments/multipass_structure/specs/lucy.json \
    --out    generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/lucy_roadhouse_multipass.pack.md
已渲染写作提示词包：…/lucy_roadhouse_multipass.pack.md（35 个节点块）   # rc=0
```

产物：`generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/lucy_roadhouse_multipass.pack.md`（留档）。

### ②③④ P-B 合并 + 验收 + 落地（本任务新接线）

回流正例 = 复用 T-3P-2 演示物 `reply_good.md`（35 节点全交齐；正文来源见 §4）。

```
$ python -m generator.promptpack.ingest \
    generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
    generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/reply_good.md \
    --land content/_e2e_writer_loop/lucy_roadhouse
[合并成功] lucy_roadhouse_multipass：35 节点 → content/_e2e_writer_loop/lucy_roadhouse/scene.json
[验收] lucy_roadhouse_multipass：PASS → content/_e2e_writer_loop/lucy_roadhouse/scene.acceptance.md
  验收通过：结构完整、闭合无违规、机械预检干净。（另有 37 条本体解析待挂……不拦落地）
[落地] lucy_roadhouse_multipass v1 → content/_e2e_writer_loop/lucy_roadhouse/scene.json（版本 sidecar …/scene.version.json）
# rc=0
```

落地产物（`/content/_e2e_writer_loop/lucy_roadhouse/`，隔离目录）：
- `scene.json`（35 节点 dialogue_graph，可玩）
- `scene.acceptance.md` + `.acceptance.json`（验收报告，成对 sidecar）
- `scene.version.json`（`generation_method=writer_ingest` / `version=1`；git 审计串锚在本分支）

### ⑤ 终端玩通（入口 = `engine/__main__.py`；critique F-1 钉死）

```
$ python -m engine content/_e2e_writer_loop/lucy_roadhouse/scene.json
```

**实际首屏 stdout 片段**（喂入选择序列 `4→1→1→1→1` 走 pressure 链到结局）：

```
------------------------------------------------------------
【（旁白） · scene_hibo_roadhouse】

希博公路酒馆的前厅被煤油灯照得发黄，吧台上有没擦干的水痕……露西把杯布搭回肩上，视线在你的嘴唇和窗边之间短短移了一次。

char_lucy：「声音放低。这里有人听闲话，也有人专听不该听的词。」
char_lucy：「别在吧台上说小屋、钥匙、教授、铁盒。你要是来买酒，就像个买酒的人。」
char_lucy：「靠窗那个没点酒，报纸翻了三次，一口水都没要。他看的不是你。」

  1. 我不说那些词，慢慢来。
  2. 我付钱，拿话就走。
  3. 我先看窗边和楼梯。
  4. 莱特的事，不说会更麻烦。

> 选择（1-4）:
```

**结局片段**（stdout 末尾，rc=0）：

```
char_lucy：「知道就走，别在这儿把话说满。」
char_lucy：「以后也别用这种问法找我。」

—— 结局 ——
```

引擎按 ADR-040 渲染：`narration` 纯旁白 + `dialogue[]` 逐句按说话人（`char_lucy：「…」`）+
3–6 选项点选。stderr 有 17 行 `[警告] 本体条目未找到: char_lucy / scene_hibo_roadhouse
（使用原 ref 显示）`——这与验收报告的 37 条本体解析待挂同源（露西引用未发布本体，见 §3），
引擎降级为原 ref 显示、不影响可玩性。

**给作者的一条命令玩通**：

```
python -m engine content/_e2e_writer_loop/lucy_roadhouse/scene.json
```

（入口是 `python -m engine <scene.json>`；`python -m engine.player` 会静默空跑，别用错。）

---

## 2. 反例（两层分开，如实标注各自性质）

### 2.1 格式层反例 —— 对**编剧错误**的真实拦截面

坏回流 `reply_bad.md` 从 `reply_good.md` 确定性变异出 4 类 E 错误
（`make_negatives.py`）：

```
$ python -m generator.promptpack.ingest <fixture design.json> \
    generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/reply_bad.md
[拒收] lucy_roadhouse_multipass：4 处需修改，未产出 scene.json
  - [E1 missing_node] pressure_line_b4：回流文本里没有这个节点的块
  - [E4 option_count_mismatch] opening：交了 1: / 2: / 3: / 5:
  - [E6 unknown_key] end_soft_leave：块里带了 options:
  - [E8 parse_error] opening：第 12 行在 options 块内但不是序号行……
退回单已写入 …/reply_bad.reject.md    # rc=1，未产 scene.json
```

退回单 `reply_bad.reject.md` 逐条给编剧「期望 / 实际 / 修改指引」（编剧不是工程师，
照着改即可）。**这是路线 A 下验收链条真正拦编剧的那一面**——格式层 E1-E8。

### 2.2 语义层反例 —— **技术负路径测试**（非编剧回流模拟）

⚠️ **性质如实标注**：路线 A 下编剧**触不到**结构字段（speaker_ref 由 run_config 锁定、
effects/condition 由代码填），编剧无论如何写正文都产不出下面这种坏图。本反例是**直接
构造**非法 graph 喂验收管线，验证验收闸能拦住「管线 bug / 被手改的 scene.json / 配置错」
这条防线——不是"编剧写坏了文字被拦"。

`illegal_scene.json` 从已落地的合法 scene.json 确定性注入两处结构违规
（`make_negatives.py`）→ `run_acceptance` → 验收报告 **FAIL**：

```
判定：❌ 未通过（FAIL）  节点数 35  硬拦错误 4
- Schema 层：1  → /nodes/opening/options/0/effects/0/op 'not_a_real_op' 非法枚举
- 一致性闭合：1 → opening/dialogue[3] speaker_ref 'char_ghost_writer' 未在 character_refs 声明
- 机械预检：2  → EFFECT_OP_INVALID + PATH_NS_INVALID（op 非法 / path 首段 'flags' 越命名空间）
```

验收闸正确拒收（硬拦 4 条），guidance 明确指向"问题出在管线或被手改过的 scene.json，
别退回给编剧改正文"。

---

## 3. 如实边界说明（不许夸大 —— 写死进本报告）

**路线 A 锁结构的设计后果**：编剧只填正文（narration / dialogue 行 / options 文本），
**触不到**结构字段。所以三层校验 + 机械预检对"纯正文错误"**基本恒 pass**——
- `speaker_ref` 由 `run_config.speaker_ref` 锁定，编剧不写说话人；
- `condition` / `effects` 由确定性合并代码填，编剧碰不到；
- `monotonic` 对 `generation_source="human"` 豁免（ADR-034 D11）。

**因此验收闸守的是结构完整性 + 本体一致性**（防管线 bug / 防绕过 P-B 手改 scene.json /
防配置错误），**对编剧手笔的把关主要落在**：
- ingest 的**格式层 E1-E8**（§2.1，编剧错误的真实拦截面）；
- 本模块的 **AP 记录**（反模式 flag，给编剧/制作人的 QA 信息，**不拦落地**）。

**不得**把语义层验收闸描述成"能拦编剧写坏的文字"——§2.2 是技术负路径，非编剧回流模拟。

### 本体解析待挂（pass/fail 判定的诚实处理）

一致性层对 `scene_anchor` / `character_refs` / `location_ref` / effect·condition 的
`ontology_ref` 做本体解析（`state.ontology.get_entity`，ADR-006 单一事实源）。露西 fixture
引用的 `char_lucy` / `scene_hibo_roadhouse` **不在已发布的驿站本体**（`/state/ontology/`
只装了 `waystation.json`）——故正例验收产出 **37 条"does not resolve in ontology"**。

验收管线把一致性层拆两半：
- **闭合违规**（speaker_ref / dialogue[].speaker_ref 未在 character_refs 声明、option_id
  重复）→ **硬拦 fail**（真结构错，编剧触不到、只可能来自管线/手改）；
- **本体解析**（`... does not resolve in ontology`）→ 单列为**「本体解析待挂」记录，
  不计入 blocking、不拦落地**。

理由（诚实交代，非缺陷掩盖）：本体解析结果取决于**当前加载了哪份本体**，是环境/fixture
依赖量。隔离目录 E2E 场景**刻意**引用未发布本体（露西不在正式内容库）。真正的本体守门
发生在正式内容入库、对着已发布本体重跑时。此口径与既有 author-reviewed 先例一致：
- `generator/multipass/tests/test_reassemble_lucy_adr040.py:118` 断言露西重装配图的**全部**
  cons issue 都是 "does not resolve in ontology"；
- T-3P-2 演示物 README（PR #89 已 merge）明确记露西 37 条 cons 为本体解析假阳性。

**盲区（主动留、作者 2026-06-29 已拍板接受，拆解 §8.2）**：deps sidecar 对 human 回流
**不写**——一致性维护（T-3.7 propagate）对回流场景不覆盖，本体变更时回流场景不会被标记
重审。留待真实编剧反馈后定（可能属 P-D 邻域）。

---

## 4. fixture 来源（审计诚实 —— 隔离目录、不入正式内容库）

E2E 正例的"编剧正文"（`reply_good.md`）**实为施工会话对旧露西 LLM 实测正文的人工改写**
（choice/end 沿用旧正文；beats 链按 T-3P-0 新 beats_plan 每拍 1 条锁定线索手工微改写）。
挂 `generation_trace.source="human"` **只是管线角色标记**，不代表真人编剧手笔。

为审计诚实，落地目标 = **`/content/_e2e_writer_loop/`（隔离目录）**，**不作为正式内容
入库**（作者 2026-06-29 拍板，拆解 §8.7）。首个真正入正式内容库的回流场景，等真实
编剧/作者手笔。

---

## 5. 对 ROADMAP ADR-039 新完成口径的逐条判定证据

完成标志（ROADMAP.md:210）：「**结构→提示词包→（编剧任意来源回流）→验收落地播放**的核心
闭环跑通，且对一份回流场景能给出正确通过/失败判定。」

| 口径分句 | 证据 | 判定 |
|---|---|---|
| **结构** | 锁定骨架 design.json（T-3P-0 structure-only 产物；beats_plan + run_config 落盘）作为全链输入 | ✅ |
| **→ 提示词包** | §1① P-A `render_pack` 产 35 节点块写作提示词包（rc=0）；格式段↔解析器对偶测试证明 pack 输出格式段可被 P-B parser 解析回来 | ✅ |
| **→（编剧任意来源回流）** | §1② 编剧 BYOM 回流 `reply_good.md`（轻量标签 markdown）经 CLI 文件摄入 | ✅ |
| **→ 验收** | §1③ 验收闸三层 + 机械 human + AP 记录 → PASS（硬拦 0）；报告成对落盘 | ✅ |
| **→ 落地** | §1④ `--land` 写 content/_e2e_writer_loop/scene.json + `record_version(writer_ingest)` | ✅ |
| **→ 播放** | §1⑤ `python -m engine <scene.json>` 玩通到「—— 结局 ——」，rc=0，实际命令+输出已粘贴 | ✅ |
| **对一份回流场景能给出正确通过/失败判定** | 正例 PASS（§1③）+ 反例格式层正确退回（§2.1）+ 反例语义层正确 FAIL（§2.2） | ✅ |

**结论**：ADR-039 首版核心闭环（P-A + P-B + 验收 + 落地 + 播放）在 lucy 场景上端到端跑通，
且对正/反例给出正确判定。阶段 3 完成标志新口径 **达标**（正文质量不再是本仓库验收对象，
如实边界见 §3）。

---

## 6. 遗留清单（R 项；按"反向回退"惯例列，不在本任务内顺手改上游）

施工中对 T-3P-0/1/2 已合并产物的观察，无一阻断本任务；均记为 R 项供作者/规划师定夺：

- **R-1（信息，非缺口）**：`version_recorder` 落地时生成 `<scene>.version.json.lock` fcntl
  哨兵文件（transient）。本任务已在 `.gitignore` 加 `*.version.json.lock` 放行，避免哨兵
  被误 commit。若未来落地路径统一，可考虑 version_recorder 收尾自删哨兵——**归 T-3.8a
  邻域，不在本任务改**。
- **R-2（如实局限，已知已拍板）**：deps sidecar 对 human 回流不写（§3 盲区）——一致性
  维护对回流场景不覆盖。作者 2026-06-29 已接受；留待真实编剧反馈（可能 P-D）。
- **R-3（口径澄清，非 bug）**：验收管线对本体解析 issue 的 pass/fail 处理（§3）依赖
  "当前加载本体"这一环境量。当前隔离目录 E2E 刻意用未发布本体，故降级为 note。**正式
  内容入库流程**（首个真实回流场景落正式库时）需要一条"对着完整已发布本体跑本体守门"的
  硬门——归 P-C/D 或正式入库任务，不在本任务范围。

---

## 附：本任务改动范围（allowed 白名单内，PR body 声明）

- 新建：`generator/promptpack/acceptance.py`（验收管线）、`generator/promptpack/tests/test_acceptance.py`。
- 改：`generator/promptpack/ingest.py`（CLI 接 `--land` + 验收闸；ingest_reply 合并语义不动）。
- E2E 隔离落地：`content/_e2e_writer_loop/lucy_roadhouse/`。
- E2E 中间产物：`generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/`（+ `.gitignore` 放行行）。
- 报告：本文件。
- **未动**：`/schema` `/state` `/tools`；`/validator` 只读调用；`/engine` 只读运行（player 不改）；
  `version_recorder` 只消费 `writer_ingest` 枚举（T-3P-0 已浇好，不改）。
