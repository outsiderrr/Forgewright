# Master Plan Critique — Round 5 — GPT-5.5

**评审者**：GPT-5.5 via Codex
**评审日期**：2026-04-30
**项目当前状态**：阶段 1 有条件通过；阶段 1.5 已规划待执行
**评审范围**：阶段 1.5 / 2 / 3 / 4 + 跨阶段架构

---

## 1. 一句话总判

Forward 路线图方向是健康的，但阶段 2/3 的评测与本体层还没有硬到足以承接“场景级生成”和“完整流水线”。阶段 1.5 可以启动，但建议先补一个很小的启动闸门：统一 1.5/2 sequencing 口径、冻结最小角色/地点视觉事实卡、明确背景资产如何挂回本体。

## 2. 严重度分布

| 严重度 | 数量 |
|---|---:|
| 🔴 | 3 |
| 🟡 | 10 |
| 🟢 | 3 |
| **合计** | 16 |

## 3. 必修（🔴）

### 3.1 [SEQ / DEBT] — 阶段 2 在正式本体未落地时启动，会把 R4/R5 放大成场景级污染
**问题**：阶段 2 要生成完整对话树，还要做角色槽位和结局可达性；但当前世界本体仍是三字段 stub，`SCHEMA_v0.md` 明确把世界本体 Schema 排除在 v0 外。阶段 1 已经暴露 `location_ref` 错配和本体污染；进入场景级生成后，这不会自然消失，只会从“单节点错一个字段”扩散成“整棵图引用了假地点/假关系/假过去”。  
**指向**：`ROADMAP.md:147-161`；`SCHEMA_v0.md:25-35`；`state/ontology/README.md:1-18`；`STAGE_1_ACCEPTANCE.md:122-123`；`HANDOFF_STAGE_1_TO_2.md:81-85`。  
**建议路径**：阶段 2 启动前加一个“本体最小可生成契约”闸门：角色卡、地点候选、关系/派系事实、允许状态路径、禁止本体外事实。不是推翻阶段 1 schema，而是在阶段 2 的 `generate_scene()` 前置输入里固定可引用事实边界。

### 3.2 [EVAL] — “任意合法状态组合下至少 1 个结局可达”目前不可判定
**问题**：ROADMAP 要求图论校验做到前置条件路径闭合、死锁检测、分支收敛，并进一步“证明任意合法状态组合下至少有 1 个结局可达”。但当前 Schema 只有 `StateCondition` 的布尔形态和点分 `path`，没有状态变量的定义域、初始状态集合、效果代数边界、合法状态组合生成规则。没有这些，校验器只能做拓扑遍历，无法证明条件路径可满足性。  
**指向**：`ROADMAP.md:152-161`；`DECISIONS.md:161-179`；`SCHEMA_v0.md:241-258`；`SCHEMA_v0.md:77-80`。  
**建议路径**：把 ADR-009 第二层拆成两个可验收子层：2A 纯拓扑（悬空、不可达、终止、SCC），2B 有界状态符号执行（状态域、初始状态、effect 应用、condition satisfiability）。若 2B 只做抽样模拟，也要在完成标志里明说，别写“证明”。

### 3.3 [EVAL / GAP] — ADR-009 第三层 playtest bots 没有落在阶段 3 完成标志里
**问题**：ADR-009 已接受三层评测，第三层是 playtest bots + LLM-as-judge 找最差路径；但阶段 3 完成标志只要求批量调度、审阅界面、一致性维护、版本控制和“一周 10 个场景”。这会让项目在没有模拟玩家覆盖的情况下进入阶段 4 的 50–100 场景填充，最容易漏掉“某类玩家路径体验很差但单场景审阅看不出来”的问题。  
**指向**：`DECISIONS.md:167-179`；`DEBATE_NOTES.md:213-232`；`ROADMAP.md:176-183`；`ROADMAP.md:196-208`。  
**建议路径**：阶段 3 完成标志补一条最小第三层：至少 N 个 bot persona、每场景 M 条模拟路径、输出 worst-10% 场景清单，并把人工审阅只抽查 worst bucket。否则“完整内容生产流水线”名不副实。

## 4. 应修（🟡）

### 4.1 [SEQ] — 阶段 1.5 与阶段 2 的先后口径在文档间冲突
**问题**：当前 ROADMAP 和 STAGE_1.5_TASKS 都把 1.5 作为已规划待执行；但 `HANDOFF_STAGE_1_TO_2.md` 仍写“阶段 1.5 已推迟”，理由还是等待图像 API，而 ADR-014 已经用 manual 模式消除了 API key 阻塞。这个冲突会误导后续执行会话：有人会按“先 2 后 1.5”，有人会按“先 1.5”。  
**指向**：`ROADMAP.md:91-135`；`DECISIONS.md:271-278`；`HANDOFF_STAGE_1_TO_2.md:29-37`；`STAGE_1.5_TASKS.md:48-73`。  
**建议路径**：作者拍板一个 sequencing 口径：推荐“1.5 manual 主线可先启动；2 的本体/角色槽位 schema 变更串行协调”。不要同时保留“1.5 等 API”和“manual 不阻塞验收”两套叙述。

### 4.2 [GAP] — 背景图生成没有一等引用位置，容易变成 manifest 里的孤儿资产
**问题**：ROADMAP 要求 `generate_scene_background(location_ref)`，但 Schema 扩展只明确“角色实体新增 `visual_assets` 字段”。如果背景图只进 `/content/visuals/manifest.json`，而不挂到 scene/location/entity 或至少 manifest target 索引，后续播放器/审阅器无法稳定知道某个场景该显示哪张背景。  
**指向**：`ROADMAP.md:103-106`；`ROADMAP.md:118`；`SCHEMA_v0.2.md:7-17`；`STAGE_1.5_TASKS.md:40-44`；`STAGE_1.5_TASKS.md:1860-1864`。  
**建议路径**：在 `ImageAsset` 或 manifest 中强制记录 `target_ref` + `target_type`（character / scene / location）和 `asset_role`（portrait / expression / background）。是否给 location/scene 也加 `visual_assets` 字段可由作者拍板，但不要只靠文件夹位置表达关系。

### 4.3 [RISK] — ADR-014 的 dev/prod prompt 同源是假设，不应推迟到大批量后才验证
**问题**：ADR-014 默认 ChatGPT Plus 网页与 OpenAI Image API 共用一套 prompt，但网页端和 API 端可能有不同隐式上下文、参考图处理、默认尺寸/质量、审美倾向。ROADMAP 允许 API 路径作为 stretch goal 不阻塞验收，这没错；但如果完全不做 parity smoke test，就可能在阶段 3/4 才发现 manual 资产和 API 资产不可混用。  
**指向**：`DECISIONS.md:271-278`；`DECISIONS.md:288-292`；`ROADMAP.md:108-109`；`STAGE_1.5_TASKS.md:45`；`STAGE_1.5_TASKS.md:1655`。  
**建议路径**：不要求 API 阻塞 1.5，但建议把“3 条 prompt 的 dev/prod 对比”列为 1.5 验收的已验证/未验证项。若 API key 没有，就显式遗留 R1.5-*，不要让“同源”默认变成事实。

### 4.4 [EVAL / SCOPE] — 阶段 2 的 70% 人工可接受率缺少样本定义
**问题**：`generate_scene()` 的完成标志写“单次生成人工可接受率 ≥70%”，但没有定义样本数、失败是否计入、是否允许重试、人工 vs AI 判官权重、机械预检失败是否直接算 reject。阶段 1 至少有 20 次 baseline、失败原因分布和 strict judge；阶段 2 若不先定义实验协议，70% 会变成不可复现口号。  
**指向**：`ROADMAP.md:145-150`；`STAGE_1_ACCEPTANCE.md:14-19`；`STAGE_1_ACCEPTANCE.md:23-47`；`STAGE_1_ACCEPTANCE.md:124-126`。  
**建议路径**：阶段 2 规划时写清楚 baseline 协议：例如 10 个场景 seed、每个最多 1 次重试、schema/graph/mechanical 任一失败即 reject、AI 判官只预筛，最终至少抽样人工确认。

### 4.5 [DEBT] — R1–R8 传播目前主要写在 HANDOFF，不在 ROADMAP 完成标志里
**问题**：HANDOFF 对 R2/R3/R4/R8 的处理很明确，但 ROADMAP 阶段 2 的“重点工作”只写角色槽位 ADR 和结局可达性，没把阶段 1 遗留项作为启动闸门。执行会话若只读 ROADMAP，会误以为 R 项只是背景噪音。  
**指向**：`ROADMAP.md:158-162`；`STAGE_1_ACCEPTANCE.md:115-128`；`HANDOFF_STAGE_1_TO_2.md:39-55`。  
**建议路径**：阶段 2 的第一批任务显式加“Stage 1 cleanup gate”：R2/R3/R4/R8 必须先合入；R5/R7 作为作者拍板项。不要让它们只存在于验收报告尾巴里。

### 4.6 [OPEN] — 阶段 4 才“开始考虑开源剥离”太晚
**问题**：ROADMAP 阶段 3 禁止开始考虑开源剥离，阶段 4 才同时做 MVP 内容填充和开源框架 v0.1。真正的剥离风险不是 README/LICENSE，而是作者游戏实例数据、provider 密钥、prompt、资产版权、插件接口、测试 fixture 是否早已混在核心代码里。到 50–100 场景后再分，会变成考古。  
**指向**：`ROADMAP.md:189-192`；`ROADMAP.md:196-208`；`DECISIONS.md:126-139`；`DECISIONS.md:202-217`；`DECISIONS.md:286-292`。  
**建议路径**：不建议阶段 3 做正式剥离；建议从阶段 2/3 起维护“框架/游戏实例边界清单”：哪些目录未来开源、哪些仅作者游戏、哪些测试 fixture 可开源、哪些资产/参考图不可开源。阶段 4 再执行剥离，但边界钩子要早留。

### 4.7 [TIME] — 4.5–7 个月对“工程”可能成立，对“内容+视觉+开源验证”偏乐观
**问题**：阶段 0/1 的代码推进很快，但阶段 1 是有条件通过，且靠 AI 判官替代人工；阶段 4 又要求 50–100 场景、完整主线、开源仓库、非作者测试用户。ADR-010 已写仅审阅 50–100 场景就要 1–3 个月，这还没算视觉返工、审阅 UI、playtest bots、开源文档和外部用户支持。  
**指向**：`ROADMAP.md:13-22`；`ROADMAP.md:196-208`；`DECISIONS.md:183-198`；`STAGE_0_ACCEPTANCE.md:31-44`；`STAGE_1_ACCEPTANCE.md:75-128`。  
**建议路径**：把总时长拆成两条估算：工程 MVP 约 4.5–7 个月；内容+开源 v0.1 带人工审阅和外部用户验证，建议另给 6–10 个月风险区间或明确“50 场景版本优先，100 场景是 stretch”。

### 4.8 [DECIDE] — 角色槽位最终落到“抽象槽”还是“具体角色”必须在阶段 2 代码前拍板
**问题**：ROADMAP 只写新增 ADR：role slot casting 与动态选角；HANDOFF 提了 `slot_tags` vs 独立 `role_slot.schema.json`。但 `generate_scene()` 输出的是 `DialogueGraph`，它目前要求 concrete `character_refs`。如果生成器内部用抽象槽、输出前再 cast，validator 和审阅 UI 要看的对象完全不同。  
**指向**：`ROADMAP.md:147-160`；`SCHEMA_v0.md:170-171`；`HANDOFF_STAGE_1_TO_2.md:96-110`。  
**建议路径**：阶段 2 先写 ADR 决定：抽象槽是否允许进入持久化 JSON？推荐持久化层仍落 concrete `character_refs`，抽象槽作为 generator 中间产物和 `generation_trace`/metadata 记录。

### 4.9 [GAP] — 阶段 3 的“一致性维护”缺少内容依赖索引
**问题**：阶段 3 要做到“本体变更时标记需重审的已生成内容”，但当前图层只有 `character_refs`、`scene_anchor`、`location_ref` 和有限的 `generation_trace`。如果某个角色年龄、派系关系、过去事件、视觉特征变化，系统如何知道哪些节点/选项/图像需要重审？没有依赖索引，阶段 3 只能全量重审。  
**指向**：`ROADMAP.md:176-181`；`DECISIONS.md:108-123`；`SCHEMA_v0.md:170-176`；`SCHEMA_v0.md:193-207`。  
**建议路径**：阶段 2 末或阶段 3 起手加 `content_dependency_index`：记录每个生成产物读过哪些 ontology ids / state paths / prompt template hash / visual asset ids。它可以是生产期 sidecar，不必污染运行时 schema。

### 4.10 [GAP / OPEN] — 视觉参考图与生成资产的版权/来源元数据没有进入完成标志
**问题**：1.5 要作者放 2–3 张风格参考图，且明确不入 git；但 manifest 完整性 100% 当前更像技术完整性，没有要求记录参考来源、授权状态、是否可开源、是否可商用、prompt hash。阶段 4 若商业化或开源，这会变成资产合规黑箱。  
**指向**：`ROADMAP.md:105-118`；`ROADMAP.md:132-134`；`DECISIONS.md:276-278`；`STAGE_1.5_TASKS.md:70-73`；`STAGE_1.5_TASKS.md:1633-1655`。  
**建议路径**：manifest 至少加 provenance 字段：`source_mode`、`prompt_hash`、`reference_ids`、`reference_license_note`、`open_source_ok`、`commercial_ok`。参考图本体仍不入 git，但来源记录不能靠作者记忆。

## 5. 可选（🟢）

### 5.1 [SCOPE] — 阶段 1.5 API stretch goal 应在验收报告里单列“未验证”，不要隐含通过
**问题**：ROADMAP 允许 manual 路径阻塞验收、API 路径作为 stretch goal，这个取舍合理。但如果验收报告只写“1.5 通过”，后续读者可能以为双模都可用。  
**指向**：`ROADMAP.md:108-109`；`STAGE_1.5_TASKS.md:1816-1818`；`STAGE_1.5_TASKS.md:1851-1854`。  
**建议路径**：验收报告明确分三态：manual passed / API implemented / API parity validated。API 未做不判 fail，但必须留下状态。

### 5.2 [GAP] — 阶段 3 审阅工具最好从一开始支持图视图，而不是只做左右文本批准
**问题**：阶段 3 的审阅界面描述是“左内容右批准/打回”，这对单节点够用，对场景图不够。作者需要看路径、条件、汇合、最差 bot 路径和视觉资产缩略图，否则审阅会退化成逐段读小说。  
**指向**：`ROADMAP.md:176-183`；`DECISIONS.md:167-179`；`HANDOFF_STAGE_1_TO_2.md:160-164`。  
**建议路径**：阶段 3 UI 不必豪华，但第一版应有 graph/mermaid/dot 视图、路径列表、validator issues 面板、visual asset thumbnail，避免后期重做审阅心智模型。

### 5.3 [TIME / GAP] — 当前“每任务执行→Codex 评审→Claude 修复”的人工编排成本会随阶段 2/3 膨胀
**问题**：1.5 任务计划要求每个任务都产 Codex prompt、独立评审、再复制修复提示到 Claude。这个 review/author 分离很好，但作者不会编程，阶段 2/3 任务数更多时，复制、追踪、合并状态本身会吃掉很多带宽。  
**指向**：`STAGE_1.5_TASKS.md:5-14`；`STAGE_1.5_TASKS.md:75-79`；`ROADMAP.md:176-183`。  
**建议路径**：阶段 3 的“版本控制集成/审阅工具”可以顺手覆盖任务状态面板：任务、commit、review 报告、修复状态、遗留 R 项。不急，但别让作者靠聊天记录管理 40 个小任务。

## 6. DEBATE_NOTES 已结案核对

列出我想说但已被 DEBATE_NOTES 否决的事项（不算 finding）：

- 想建议运行时用 LLM 做兜底对话/动态修补图，但 DEBATE 主题 1 与 ADR-002 已明确否决。
- 想建议用 Ink / Articy 作为作者友好图编辑或导出源，但 DEBATE 主题 3 与 ADR-003 已否决作为核心数据源。
- 想建议把某套编剧理论或 Premise 做核心质量约束，但 DEBATE 主题 4/7 与 ADR-005 已否决；只能做插件。
- 想建议扩大到 BG3 级大图以验证上限，但 ADR-010 已锁 50–100 场景 MVP，DEBATE 主题 9 也承认大规模图生成是未解问题。
- 想建议玩家自由文本或混合输入提高互动感，但 ADR-001 已锁选项式交互。

## 7. 阶段 1 R1–R8 传播评估

| R | 描述 | 阶段 2/3 复现风险 | 当前覆盖 | 缺口 |
|---|---|---|---|---|
| R1 | Schema 合格率 85% | 高。场景级输出比单节点更长，复合结构更多，失败率可能上升。 | `HANDOFF_STAGE_1_TO_2.md:45` 覆盖；ROADMAP 未显式写 cleanup gate。 | 阶段 2 baseline 协议 + 起手修 R2/R3/R4/R8；不要直接上 `generate_scene()`。 |
| R2 | 复合 condition few-shot 缺失 | 很高。阶段 2 的图论校验正围绕 condition 展开。 | `HANDOFF_STAGE_1_TO_2.md:46` 覆盖；`ROADMAP.md:152-153` 只写校验目标。 | few-shot 示例、复合深度约束、condition satisfiability 测试。 |
| R3 | 选项过长 | 高。场景级生成会追求戏剧文本，选项更容易膨胀。 | `HANDOFF_STAGE_1_TO_2.md:47` 覆盖；ROADMAP 未写。 | 机械预检硬阈值 + prompt 硬约束 + review UI 标红。 |
| R4 | location_ref 错配 | 很高。多地点/多场景后 fixture 单地点假设会失效。 | `HANDOFF_STAGE_1_TO_2.md:48` 覆盖；1.5 可借鉴。 | `location_candidates`、scene/location ontology、背景资产 target_ref 同步设计。 |
| R5 | 本体污染 | 极高。阶段 2 若无正式本体，会污染整棵图；1.5 会变成视觉脸/服装污染。 | `STAGE_1_ACCEPTANCE.md:123` 说阶段 2 本体 Schema 后会更准；`HANDOFF_STAGE_1_TO_2.md:49` 强相关。 | 阶段 2 本体最小 schema 闸门；1.5 角色固定特征卡。 |
| R6 | AI 判官替代人工 | 高。阶段 2/3 若继续靠 AI 判官，会高估质量。 | 1.5 已写“作者本人 + AI 辅助”；阶段 3 写作者跑一周 10 场景。 | 阶段 2/3 需要 human calibration sample；playtest bots 也要和人工决策比对。 |
| R7 | cost_log 高估 | 中高。scene 生成 token 更大，图像 API 单价更敏感。 | `HANDOFF_STAGE_1_TO_2.md:51` 覆盖；ADR-012 有预算框架。 | 使用 provider usage metadata 反向校准；按 scene/image 分预算，不只按 call。 |
| R8 | 机械预检器 | 很高。没有机械层，LLM 判官会继续漏掉长度、白名单、引用等可数值问题。 | 1.5 有 `image_validator`；`HANDOFF_STAGE_1_TO_2.md:52` 覆盖。 | 阶段 2 文本机械预检器应进入启动 gate：option length、path prefix、bond id、ontology id、target id。 |

## 8. 待作者拍板的开放决策（DECIDE 类汇总）

1. 阶段 1.5 与阶段 2 的实际 sequence：先 1.5 manual、先 2、还是 1.5/2 并行但 schema 串行？
2. 阶段 2 是否必须先落地正式本体最小 Schema？若是，范围到角色/地点/关系/状态路径哪一级？
3. 角色槽位是否允许进入持久化 JSON，还是只作为 generator 中间产物？
4. 背景资产挂载到哪里：location/scene 也有 `visual_assets`，还是 manifest 用 `target_ref` 解决？
5. “任意合法状态组合可达结局”是要严格证明、有限域符号执行，还是抽样模拟？
6. 阶段 3 是否把 playtest bots 作为完成标志，而不是推到阶段 4？
7. API 路径未验证时，阶段 1.5 验收是否允许“manual passed, API unverified”的有条件通过？
8. 开源剥离边界清单从阶段 2 开始维护，还是坚持阶段 4 才开始？

## 9. Top 3 你最担心的事

按“如果不处理，project 最可能在哪里翻车”排序：

1. 阶段 2 没有正式本体/状态域就做场景级生成，导致图校验看起来通过，内容却在事实层污染。
2. ADR-009 第三层缺位，阶段 4 才发现 50–100 场景里有大量糟糕路径和死角体验。
3. 开源剥离边界太晚才维护，最后框架核心、作者游戏内容、视觉版权、provider 假设混在一起。

## 10. 评审范围外的观察（可忽略）

- 现有 `docs/reviews/2026-04-30_T-1.5.1_review.md` 已经抓到 ROADMAP 中 path A/path C 术语不一致、ADR-014 manual 背景契约漏写等局部问题；本报告只在跨阶段层面使用这些信号，不重复计数。
- 本次只做规划评审，未运行测试，也没有修改 ROADMAP / DECISIONS / DEBATE_NOTES / schema / 代码。
