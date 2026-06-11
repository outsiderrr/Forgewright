# 设计：收敛路由 × 静态文本盲点修复（含 junction 承接统一治理）

> 状态：**作者批准 + 已施工 + 真跑验证通过**（2026-06-11；ADR-037 软地基闭环）
> 批准记录：作者修订 B 层（选项数 1-5 灵活，不与分叉绑定）后点头"开工，含真跑验证"。
> 施工：commit `a9a2589`（1364 pytest pass）；验证：`2026-06-11_convfix/VERIFICATION_REPORT.md`
> （vick×2 + lucy×1，三种穿帮全消失，硬校验 3/3，lucy 无劣化，~$0.47/场）。
> 任务书：`docs/handoffs/2026-06-10_structure_convergent_routes_handoff.md`
> 依据：`2026-06-10_review/REVIEW_REPORT.md` §2 根因①⑥ + §2.2 junction 承接遗留

## 0. 目标（一句话）

让"玩家刚说的话"永远不被 NPC 无视或张冠李戴——修掉三种玩家可见的穿帮：

| 穿帮 | 实证 | 玩家体验 |
|---|---|---|
| 答非所问 | vick/c1：选项"有人介绍我谈隐秘收购"→ NPC 回"莱特教授当然来过"（玩家没提莱特） | NPC 像没听清就背台词 |
| choice pressure（选择压力）稀释 | vick/c1 开场 5 选项只有 3 种后果；lucy/c1 corner_assess 5→2 | 选什么都一样，选择是假的 |
| junction（节点交界）失忆 | whitcroft/c1：玩家"说报告。"→ 下一节点 NPC 当没听见，自顾自重新开场 | 对话在节点边界断片 |

## 1. 根因（一句话）

多 pass 管线里，**下游节点生成时不知道玩家是怎么走进来的**：
链首拍 / 子 choice 正文 / end 收束都只拿到"功能 + 契约 + 已揭露线索"，
拿不到入口选项文本或玩家末句——所以只能盲写，盲写就会预设。

## 2. 方案：三层治理（对 handoff §3 五个候选方向的取舍）

### A. 拓扑层 —— 出边数 = 真实分歧数（方向①，裁剪采纳）

1. `TOPOLOGY_SYSTEM` 规则改写：
   - 删除现行"多个选项殊途同归时 routes 可以只有 1 条"的**鼓励收敛**措辞；
   - 改为："**出边数 = 真实分歧数**。玩家会有 N 类语义不同的反应（问不同的事 / 亮不同的牌），
     就给 N 条出边（≤4）；只有多个选项确实是**同一姿态的不同说法**时才共享一条出边，
     且 `stance` 必须写出这条边上所有选项的**共同语义**（后续 pass 靠它写收敛安全的开头）。"
2. 平行分支线索查重（确定性，0 LLM；**同时治方向④的根**）：
   `validate_topology()` 新增检查——同一线索**原文字符串**出现在两个非祖先关系节点的
   `reveals` 里 = 硬错误，进现有重试循环（错误信息要求"为各分支写明不同的完整度/残缺形态"）。
   这把"残缺分层"从口头要求变成机器强制：vick/c2 声明了残缺化却没兑现，就是因为没人拦。
3. **不做**"每条出边声明预期选项数"（handoff 方向①后半）：B 层放宽后骨架不再被迫凑选项，
   收敛只在设计者有意为之时出现，C 层兜底——再加逐边配额属于微管理，增加拓扑 pass 出错面。

### B. 骨架层 —— 选项数 1-5 灵活，不与出边数绑定（方向②，作者修订版 2026-06-11）

> 作者意见（2026-06-11）：选项做成 1-5 之间灵活；**不要把分叉定死**——
> 出边 2 条时依然可以 3 个选项；单选项节点也是合法形态。

1. `build_dynamic_node_schema()` 的 options 范围改为 **1-5 灵活**：
   - `minItems = max(1, len(routes))`（唯一硬下限 = 每条出边至少要有 1 个选项把玩家送过去）；
   - `maxItems = 5`；选项数**不与出边数绑定**——出边 2 条时照样可以 3/4/5 个选项
     （多选项共享一条出边 = 有意收敛，由 C 层收敛安全写法承接）。
   - schema（`node.schema.json`）零改动——本就允许 minItems:1。
2. `PASS1_SKELETON_SYSTEM_DYNAMIC` + user prompt 同步改写："选项数由**真实的玩家反应数**决定，
   1-5 之间灵活：是真选择就给足姿态变体制造选择压力，只是推进则少给；
   **不要为凑数发明会路由错位的选项**。""3-5 个 option"的硬文案改为动态生成。

### C. 入口上下文注入（entry context injection）—— 方向③+⑤统一设计（核心）

引擎为**每个非入口节点**计算"玩家是怎么走进来的"，注入其全部生成调用：

| 入边形态 | 注入内容 | 注入语义 |
|---|---|---|
| 单入口（1 个选项路由进来 / beats 链尾 continue） | 玩家原句「…」 | "NPC 开头第一句必须先承接这句话（回应它，或明确拒答），再推进" —— 与已落地的链内跨 chunk 传话同一措辞 |
| 收敛多入口（≥2 个选项路由进来） | 入口语句清单：每条「选项文本」+（intent/stance） | "开头必须对**所有**入口都成立：不得预设玩家提过其中某个特定信息；可回应它们的共同点（stance 共同语义），或先以中性反应（动作/试探/反问）接住，再引出信息" |

注入点（全部是已有调用，**0 次新增调用**）：
1. **beats 链首 chunk**：经 `situation` 追加（沿用引擎现有 situation 拼接机制；chunk>1 已有跨 chunk 传话，不动）；
2. **子 choice 骨架调用**：入口上下文参与 situation / choice_pressure 设计；
3. **子 choice 正文调用**（`build_pass2_user_prompt` 新参数）：约束 NPC 开场白；
4. **end 收束调用**（`build_end_prose_user_prompt` 新参数）：链尾玩家末句 → 收束旁白承接。

措辞单一来源：prompts 侧新增一个共享 helper（如 `entry_context_block()`），
四个 builder 复用，避免四处各写一版漂移。

数据来源（引擎已有，纯 plumbing/数据接线）：BFS 父先于子 → 生成下游时父节点的
skeleton（route_to）+ prose（最终选项文本）/ beats（链尾 continue 文本）都已存在；
按索引对齐取"路由到本节点的选项最终文本"，缺文本时回退 intent。

### D. 跨分支去重的剩余部分（方向④，轻做）

根已在 A-2 治（拓扑层强制差异化残缺形态）。补两件轻的：
1. `beat_pacing` user prompt 一行规则：保底类线索按**本链 reveals 给定的完整度形态**写，
   不得写出其他分支级别的完整版。
2. metrics（指标）新增可观测项：
   - `route_convergence`：每个 choice 节点"出边 → 选项数"映射（收敛稀释从此可量化跨 run 追踪）；
   - 跨平行分支对白行最大相似度（difflib，纯本地）——近原文复制的客观信号。

   **不做**"措辞清单全文注入 sibling 链"（prompt 膨胀大、根因已在上游治、收益边际）。

## 3. 否决项（防反悔记录）

- **不做 per-entry 链首复制**（每个入口选项单独生成一版链首拍）：节点数与成本成倍涨，
  破坏 pure tree（纯树）经济性；真正语义分歧应该在拓扑层变成独立出边（A），
  残余收敛用收敛安全写法（C）足够。
- **不做 schema / validator / engine / state 任何改动**：全部修复落在 `/generator` 内
  （prompt 文本 + 引擎 plumbing + 确定性校验 + metrics）。
- **不动链内跨 chunk 传话与 beat_pacing 承接规则**（§2.2 已修验证过）——C 只是把同一机制
  延伸到节点交界。

## 4. 成本与风险

- **生成成本不变**：0 次新增调用；仅 prompt 增加约 100-300 tokens/节点（场均 ~$0.4 不变）。
- **拓扑重试率可能略升**（A-2 新硬错误）：每次重试 ~$0.02，重试 ≤2 次上限与回退机制照旧；
  回退脚手架本身不受 A-2 约束（如实记 fallback）。
- **风险：收敛安全开头写得平淡**（"对所有入口都成立"可能趋向中性套话）——
  缓释：A/B 层先把多数收敛消灭在源头，残余收敛少；验收时人工读开场两跳专门盯这点。

## 5. 验收（按 handoff §5）

1. 单元测试全绿（新增：拓扑查重、minItems 动态化、entry context 计算与注入、prompt builder 文案）；
   边界自检 `grep -R "from generator" engine/ state/ schema/ validator/` 0 匹配。
2. 真跑 vick spec × 2 候选（~$0.9）：
   - 开场两跳人工读：链首拍无答非所问（对照 c1 的 business_entry_b1 / sharp_name_test_b1）；
   - 收敛选项有差异化处理（route_convergence 指标 + 人工抽读）;
   - 平行分支无近原文复制（相似度指标 + 人工抽读）；
   - junction 抽查：链尾玩家末句被下游节点承接（对照 whitcroft 的 opening_b3 → approach_choice）。
3. 回归 lucy spec × 1（~$0.4）：确认无劣化（基准 = 作者已接受的 lucy/c1 质量线）。
4. 总预算 ~$1.3。

## 6. 施工清单（批准后）

| 文件 | 改动 |
|---|---|
| `generator/prompts/node/multipass/topology.py` | A-1 规则改写 |
| `generator/multipass/topology.py` | A-2 平行分支线索原文查重（硬错误） |
| `generator/prompts/node/multipass/pass1_skeleton.py` | B：minItems 动态化 + 文案；C：骨架注入块 |
| `generator/prompts/node/multipass/pass2_prose.py` | C：choice 正文 / end 收束 entry context 参数 |
| `generator/prompts/node/multipass/beat_pacing.py` | D-1 一行规则（链首注入走引擎 situation，不改签名） |
| `generator/prompts/node/multipass/`（共享） | C：`entry_context_block()` helper（措辞单一来源） |
| `generator/multipass/engine.py` | C：entry context 计算 + 四处注入；D-2 metrics 两项 |
| 各对应 `tests/` | 新增/更新用例 |

施工顺序：纯本地（prompt + 引擎 + 单测，0 API 消耗）→ vick×2 + lucy×1 真跑（~$1.3）→ 结果报告。
