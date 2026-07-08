# T-3P-3 ｜ ADR-039 首版核心闭环 E2E 实测报告（P-A + P-B + 验收 + 落地 + 播放）

> **性质**：L3 施工会话 A→C 阶段 E2E 实测产物（参 T-3.10 先例）。
> **日期**：2026-07-09 · **分支**：`claude/t3p3-acceptance-e2e`（基线 main `3be51d1`）。
> **任务**：[/docs/prompts/stage_3/T-3P-3.md](../../prompts/stage_3/T-3P-3.md) · **拆解**：[2026-06-29_pa_pb_task_breakdown.md](2026-06-29_pa_pb_task_breakdown.md) §5.4。
> **C 阶段口径修订**：B 报告（[/docs/reviews/2026-07-09_T-3P-3_acceptance_e2e_review.md](../2026-07-09_T-3P-3_acceptance_e2e_review.md) F-1/F-2）+ 作者 2026-07-09 拍板 **Option 1**：**本体解析 = 硬拦（ADR-006 生产语义）**。本报告已按此重写，不再有"本体解析降级为 note"的口径。

---

## 0. TL;DR（诚实结论）

| 环节 | 结果 |
|---|---|
| ① P-A 渲染写作提示词包（35 节点块） | ✅ rc=0 |
| ② P-B 合并回流 → scene.json（35 节点，**结构有效**） | ✅ rc=0（合并本身成功） |
| ③ 验收闸（三层全硬拦 + 机械 human + AP 记录） | ❌ lucy 正例 **正确 FAIL**（37 条本体解析未通过——lucy 引用未发布本体） |
| ④ `--land` 落地 | ✅ **正确拒绝**（验收 FAIL → 不落地、不留 scene.json、不记版本；报告留盘） |
| ⑤ 播放链路（**直接**喂合并产物给 engine，不经验收闸） | ✅ rc=0，玩通到「—— 结局 ——」 |
| ⑥ 反例·格式层（坏回流 4 类 E 错误） | ✅ 正确退回单，rc=1，未产 scene.json |
| ⑦ 反例·语义层（非法 graph 喂验收管线） | ✅ 正确 FAIL（硬拦 41 条：37 本体 + 1 闭合 + 1 schema + 2 机械） |

**一句话结论**：**结构闭环达标**（P-A → P-B → 合并 → 结构层 + 机械层验收接线完整）+ **本体一致性守门达标**（验收闸对引用未发布本体的 lucy 场景**正确拒收落地**，证明守门在工作 ADR-006）。**"验收全过 → 落地 → 玩" 的全绿 happy-path 留待本体齐全的场景**（当前 fixture 不满足；补齐 lucy 本体触 `/state` 白名单外，列为 R 项 follow-up）。

> 诚实说明：lucy 正例 FAIL 是**比"可疑 PASS"更强的演示**——它证明验收闸真的在守本体一致性，而不是把 37 条本体解析问题静默放过。上一版报告（A 阶段）把这批场景声明为 PASS 依赖了"本体解析降级为 note"的口径，B 报告 F-1 判其违反三层硬拦规格；作者拍板本体解析硬拦后，本版按 FAIL 如实重写。

全仓测试：**1572 → 1589 passed / 6 skipped**（+17，全部本任务新增；0 regression）。

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

### ②③④ P-B 合并 + 验收 + 落地（本任务新接线）— lucy 正例**正确 FAIL 不落地**

```
$ python -m generator.promptpack.ingest \
    generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
    generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/reply_good.md \
    --land content/_e2e_writer_loop/lucy_roadhouse
[合并成功] lucy_roadhouse_multipass：35 节点 → content/_e2e_writer_loop/lucy_roadhouse/scene.json
[验收] lucy_roadhouse_multipass：FAIL → content/_e2e_writer_loop/lucy_roadhouse/scene.acceptance.md
  验收未通过，未落地：一致性层 37 错（说话人闭合 / option_id 唯一 / 本体引用未解析）。……本体解析类是场景引用了当前未加载的本体条目（补齐本体或修正 ref 后重跑；本体一致性 = 真相之源守门 ADR-006）。
[未落地] 验收未通过（硬拦错误 37 条），已删除落地目录的候选 …/scene.json、未记版本；验收报告留在 …/scene.acceptance.md 供排查。
# rc=1（EXIT_REJECTED）
```

隔离目录 `/content/_e2e_writer_loop/lucy_roadhouse/` 落地后**只有验收报告**（`scene.acceptance.md` + `.json`，显示 **FAIL**），**无 scene.json / 无 scene.version.json**——守门正确拒收。这份 FAIL 报告是正确产物。

### ⑤ 播放链路演示（直接喂合并产物，**不经验收闸**）

播放与"验收放行落地"正交。P-B 合并产物**结构有效可玩**，直接喂 engine 能玩通：

```
$ python -m engine <合并产物 scene.json>     # 入口 = engine/__main__.py（critique F-1）
```

（合并产物本身不在正式落地目录——lucy 验收 FAIL 不落地。此处演示用合并产物临时落盘后播放；测试 `test_lucy_merge_product_plays_through_engine` 已固化：喂 `4→1→1→1→1` 路径玩到结局。）

**实际输出**：narration 纯旁白 + dialogue[] 逐句按说话人（`char_lucy：「…」`）+ 3–6 选项，玩到「—— 结局 ——」rc=0。**如实注明**：engine 对未解析 ref（char_lucy / scene_hibo_roadhouse 不在已加载本体）**降级为原 ref 显示**（stderr `[警告] 本体条目未找到`），不 crash、不影响可玩性——这与验收闸把本体解析判 FAIL 是同一事实的两个面：**播放宽容（只是显示降级），落地严格（本体不全不放行）**。

---

## 2. 反例（两层分开，如实标注各自性质）

### 2.1 格式层反例 —— 对**编剧错误**的真实拦截面

坏回流 `reply_bad.md` 从 `reply_good.md` 确定性变异出 4 类 E 错误（`make_negatives.py`）：

```
[拒收] lucy_roadhouse_multipass：4 处需修改，未产出 scene.json
  - [E1 missing_node] pressure_line_b4：回流文本里没有这个节点的块
  - [E4 option_count_mismatch] opening：交了 1: / 2: / 3: / 5:
  - [E6 unknown_key] end_soft_leave：块里带了 options:
  - [E8 parse_error] opening：第 12 行在 options 块内但不是序号行……
退回单已写入 …/reply_bad.reject.md    # rc=1，未产 scene.json
```

退回单逐条给编剧「期望 / 实际 / 修改指引」。**这是路线 A 下验收链条真正拦编剧的那一面**——格式层 E1-E8（在 P-B 解析/对齐阶段，早于验收闸）。

### 2.2 语义层反例 —— **技术负路径测试**（非编剧回流模拟）

⚠️ **性质如实标注**：路线 A 下编剧**触不到**结构字段，编剧无论如何写正文都产不出下面这种坏图。本反例是**直接构造**非法 graph 喂验收管线，验证验收闸对「管线 bug / 被手改的 scene.json / 配置错」这条防线硬拦。

`illegal_scene.json` 在 lucy 合并产物上**再**注入两处非本体解析类违规（`make_negatives.py`）→ `run_acceptance` → **FAIL，硬拦 41 条**：

```
判定：❌ 未通过（FAIL）  节点数 35  硬拦错误 41
- 一致性层 39 错：37 本体解析（char_lucy / scene_hibo_roadhouse 等未发布）
                 + 1 闭合（opening/dialogue[N] speaker_ref 'char_ghost_writer' 未在 character_refs 声明）
- Schema 层：1  → /nodes/opening/options/0/effects/0/op 'not_a_real_op' 非法枚举
- 机械预检：2  → EFFECT_OP_INVALID + PATH_NS_INVALID（op 非法 / path 首段 'flags' 越命名空间）
```

演示了三层（schema/graph/cons）+ 机械层**全部硬拦**——本体解析、闭合违规、机械违规同为 blocking（C 阶段 Option 1）。

---

## 3. 如实边界说明（不许夸大 —— 写死进本报告）

**路线 A 锁结构的设计后果**：编剧只填正文（narration / dialogue 行 / options 文本），**触不到**结构字段（speaker_ref 由 run_config 锁定 / condition·effects 由代码填 / monotonic 对 human 豁免）。所以三层 + 机械预检对"纯正文错误"**基本恒 pass**。

**因此验收闸守的是结构完整性 + 本体一致性**（防管线 bug / 防绕过 P-B 手改 scene.json / 防配置错误 / **防本体引用不全**），**对编剧手笔的把关主要落在**：
- ingest 的**格式层 E1-E8**（§2.1，编剧错误的真实拦截面）；
- 本模块的 **AP 记录**（反模式 flag，给编剧/制作人的 QA 信息，**不拦落地**——唯一的非阻断层）。

**不得**把语义层验收闸描述成"能拦编剧写坏的文字"——§2.2 是技术负路径，非编剧回流模拟。

### pass/fail 判定（C 阶段 Option 1；ADR-006）

- **硬拦（fail）**：`validator.validate(graph)` 三层（schema / graph / **consistency 全部**，含闭合违规 + **本体解析**）+ 机械预检 error。**consistency 层不拆分、不降级**。
- **只记录不拦**：**只有 AP flag**（沿 multipass engine.py 先例）。

**本体解析硬拦的理由**（ADR-006 / CLAUDE.md 规则 5 = 世界本体是真相之源）：回流验收若允许 `scene_anchor` / `character_refs` / `location_ref` 全部 unresolved 仍 PASS，就不能称为"本体一致性守门"。**后果如实**：引用未发布本体的 fixture 场景（lucy）**正确 FAIL、被拒收落地**——这是守门在工作。

### 盲区（主动留、作者 2026-06-29 已拍板接受，拆解 §8.2）

deps sidecar 对 human 回流**不写**——一致性维护（T-3.7 propagate）对回流场景不覆盖，本体变更时回流场景不会被标记重审。留待真实编剧反馈后定（可能属 P-D 邻域）。

---

## 4. fixture 来源（审计诚实 —— 隔离目录、不入正式内容库）

E2E 正例的"编剧正文"（`reply_good.md`）**实为施工会话对旧露西 LLM 实测正文的人工改写**（choice/end 沿用旧正文；beats 链按 T-3P-0 新 beats_plan 每拍 1 条锁定线索手工微改写）。挂 `generation_trace.source="human"` **只是管线角色标记**，不代表真人编剧手笔。

落地目标 = **`/content/_e2e_writer_loop/`（隔离目录）**，**不作为正式内容入库**（作者 2026-06-29 拍板）。且因本体未发布，本场景当前**验收 FAIL 本就不会落地**；首个真正入正式内容库的回流场景，等真实编剧/作者手笔**且本体齐全**。

---

## 5. 对 ROADMAP ADR-039 新完成口径的逐条判定证据（按 B 报告 F-2 纠正，不夸大）

完成标志（ROADMAP.md:210）：「**结构→提示词包→（编剧任意来源回流）→验收落地播放**的核心闭环跑通，且对一份回流场景能给出正确通过/失败判定。」

| 口径分句 | 证据 | 判定 |
|---|---|---|
| **结构** | 锁定骨架 design.json（T-3P-0 structure-only 产物）作为全链输入 | ✅ |
| **→ 提示词包** | §1① P-A 产 35 节点块 pack（rc=0）；格式段↔解析器对偶测试证明 pack 输出格式段可被 P-B parser 解析回来 | ✅ |
| **→（编剧任意来源回流）** | §1② 编剧 BYOM 回流 `reply_good.md`（轻量标签 markdown）经 CLI 文件摄入 | ✅ |
| **→ 验收** | §1③ 验收闸三层全硬拦 + 机械 human + AP 记录接线完整；**对 lucy 正例正确 FAIL**（本体未发布） | ✅（守门达标） |
| **→ 落地** | §1④ `--land` 在验收 FAIL 时**正确拒绝**（不落地、不留 scene.json、不记版本） | ✅（拒收路径达标） |
| **→ 播放** | §1⑤ 直接喂合并产物给 engine 玩通到结局（rc=0）；如实注明播放不经验收闸 | ✅（合并产物可玩） |
| **对一份回流场景能给出正确通过/失败判定** | lucy 正例正确 **FAIL**（本体守门）+ 反例格式层正确退回（§2.1）+ 反例语义层正确 FAIL（§2.2） | ✅ |

**结论（不夸大）**：
- **结构闭环达标** = P-A → P-B → 合并 → 结构层 + 机械层验收接线完整、可跑。
- **本体一致性守门达标** = 验收闸对本体不全场景正确拒收（ADR-006）。
- **"验收全过 → 落地 → 玩" 的全绿 happy-path** 因当前 fixture 引用未发布本体而**未在 lucy 上演示**；单测用本体可解析的最小图（`char_vellin` 等 waystation id）证明"三层全过时 PASS + --land 写入 + version sidecar"这一路径可行（`test_land_pass_resolvable_writes_scene_and_version_sidecar`）。lucy 上的全绿 happy-path 列为 **R 项 follow-up**（§6 R-4）。

---

## 6. 遗留清单（R 项；按"反向回退"惯例列，不在本任务内顺手改上游）

- **R-1（信息，非缺口）**：`version_recorder` 落地时生成 `<scene>.version.json.lock` fcntl 哨兵文件（transient）。已在 `.gitignore` 加 `*.version.json.lock` 放行。可考虑 version_recorder 收尾自删哨兵——归 T-3.8a 邻域，不在本任务改。
- **R-2（如实局限，已知已拍板）**：deps sidecar 对 human 回流不写（§3 盲区）——一致性维护对回流场景不覆盖。作者 2026-06-29 已接受；留待真实编剧反馈（可能 P-D）。
- **R-3（口径已收敛）**：本体解析在验收闸的处理 = **硬拦**（C 阶段 Option 1 / ADR-006，作者 2026-07-09 拍板）。原 A 阶段"降级为 note"口径已废止。
- **R-4（全绿 happy-path follow-up；本任务无法在 lucy 上完成）**：lucy fixture 引用 `char_lucy` / `scene_hibo_roadhouse` 未在 `/state/ontology/` 发布——要在 lucy 场景上演示"验收全过 → 落地 → 玩"全绿 happy-path，需**给 lucy 配套最小本体**（新增 `/state/ontology/*.json` 条目）。**这触 `/state` 白名单外**（本任务硬边界严禁动 `/state`），故列为 follow-up：由作者授权的 schema/state 会话补本体后，另起会话在 lucy 上跑全绿 E2E。当前用本体可解析的最小图（waystation id）在单测里证明该路径代码可行。

---

## 附：本任务改动范围（allowed 白名单内，PR body 声明）

- 新建：`generator/promptpack/acceptance.py`（验收管线；C 阶段本体解析改硬拦）、`generator/promptpack/tests/test_acceptance.py`。
- 改：`generator/promptpack/ingest.py`（CLI 接 `--land` + 验收闸；ingest_reply 合并语义不动）。
- E2E 隔离落地：`content/_e2e_writer_loop/lucy_roadhouse/`（当前只有 FAIL 验收报告——守门正确拒收）。
- E2E 中间产物：`generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/`（+ `.gitignore` 放行行）。
- 报告：本文件。
- **未动**：`/schema` `/state` `/tools`；`/validator` 只读调用；`/engine` 只读运行（player 不改）；`version_recorder` 只消费 `writer_ingest` 枚举（T-3P-0 已浇好，不改）。
