# STAGE_1.5_ACCEPTANCE.md — 阶段 1.5 验收报告（部分通过）

**文档版本**：v0.1
**阶段**：1.5（视觉资产生成 — manual + API 双模）
**签字日期**：2026-05-02
**签字人**：outsiderrr

---

## 1. 阶段 1.5 完成判定核对

依据 [`/docs/ROADMAP.md`](ROADMAP.md) 「阶段 1.5 § 完成标志」+ [`/docs/STAGE_1.5_TASKS.md`](STAGE_1.5_TASKS.md) 「锁定的架构决策」+ Round 5 综合闸门（**U-CL-2** / **U-CL-3** / **C4** / **C8** / **U-GPT-3** / **U-GPT-6**）：

| 指标 | ROADMAP / TASKS 目标 | 实测 | 判定 |
|---|---|---|---|
| 入库总数（vellin 10 + corvan 5 + aelwin 4 + 1 location = 20） | ≥ 20 | **5 / 20**（vellin 5 张 mini probe；corvan / aelwin / scene = 0；剩余 14 张 + 1 background **作者主动跳过**全 batch run） | ⚠️ **未达数量目标**（见 §4 R1.5-1 说明） |
| **接受率**（**Round 5 U-CL-2**：分子 = 作者标 [A]ccept；分母 = 入库（机械预检通过 + 进入 review_log） | ≥ 50% | **未测**（无 visual_review_log——作者未跑 visual_review_cli；mini probe 5 张系作者**亲眼**确认 5/5 同一人，但未走 review_log 路径） | ⏸ **未测**（见 §4 R1.5-2） |
| 机械预检通过率（image_validator 输出 0 error） | ≥ 80% | **100%**（5/5；mini probe 全过——含 RGB→RGBA Pillow 模式转换后） | ✅ **MET** |
| **manifest.json 完整性**（**Round 5 U-CL-2**：每条入库资产含 image_asset.schema.json 全部 required 字段） | 100% | **100%**（5/5 含 asset_id / asset_kind / asset_role / target_ref / target_type / source_mode / format / width / height / file_path / created_at + provenance 字段全） | ✅ **MET** |
| manual 路径全跑通（dev = ChatGPT Plus 网页 + import CLI） | 是 | **是**（mini probe 端到端：visual_experiment → ChatGPT 手工 → image_import → manifest + ontology 写入；产物可在 main 看到） | ✅ **MET** |
| **C8 三态 API 验收口径**（Round 5 硬闸门） | manual passed = 必须；API implemented + API parity validated = stretch | 见 §1.1 | ⚠️ **部分** |
| **U-CL-3 mini probe gate**（vellin 5 张 ≥ 4/5 同一人） | ≥ 4/5 | **5/5 PASS**（作者亲检；T-1.5.6 期内通过） | ✅ **MET** |
| **U-GPT-3 manifest target 三字段**（target_ref / target_type / asset_role） | required 入 schema 且贯穿数据流 | **三字段贯穿**（schema → ImageProvider Protocol → meta.json → image_import → manifest）；5 张 mini probe 全部正确写入 | ✅ **MET** |
| **U-GPT-6 provenance 字段**（reference_ids / open_source_ok / commercial_ok 等）| schema 预留 | **schema 预留 + manifest 默认值落地**（mini probe 5 张含字段但默认空 / false——保守策略） | ✅ **MET**（schema 预留维度；实际 license 信息阶段 4 商业化前补） |

### 1.1 C8 API stretch goal 三态明示（Round 5 硬闸门）

| 状态 | 含义 | 1.5 实测 |
|---|---|---|
| **manual passed** | vellin / corvan / aelwin / 1 location 全 manual 入库 + 作者审阅接受率 ≥ 50% | ⚠️ **部分**（mini probe 5/5 端到端 PASS；剩余 14 + 1 张作者主动跳过；接受率未测） |
| **API implemented** | T-1.5.9 OpenAIImageProvider 落地 + smoke test 通过 | ✅ **落地**（commit `9826667` + 后续 4 fix；smoke skipped 因作者无 OPENAI_API_KEY，单元测试 12/12 + parity smoke unit 14/14 全过） |
| **API parity validated** | C4 dev/prod parity smoke test 跑了 + 3 对里 ≥ 2 对漂移评分 ≤ 1 | ❌ **未跑**（无 OPENAI_API_KEY；R1.5-4） |

### 整体结论

**有条件通过 / 部分通过**——

- **工程指标全部 MET**：工具链 / schema / manifest / ontology 写入 / image_validator / image_budget / image_cost_log / import_log / visual_experiment / visual_review_cli / visual_metrics / 12 维 AI 判官 prompt + OpenAIImageProvider + visual_parity_smoke 全部 10 + 1 任务 ABC 闭环、跨 LLM 评审审计轨迹完整 commit。
- **产品指标部分 MET**：mini probe 5 张端到端验证工具链（U-CL-3 PASS 5/5）；剩余 14 立绘 + 1 scene background 作者**主动跳过**全 batch 生图（手工 ChatGPT 生图速度太慢，工具链已实证 → 边际验证价值不抵生图成本）。
- **未测项目**：接受率（U-CL-2）/ AI 判官 vs 作者 kappa / dev-prod parity（C4）—— 全部进 §4 R1.5-* 遗留清单，**不阻塞 1.5 签字**（manual passed 工具链已实证为 sufficient evidence）。

**作者签字接受**——以"工具链端到端验证"作为 1.5 实质交付物，把"全 batch 真实生图 + 接受率统计"推到阶段 3（作者审阅工坊期）或阶段 4（商业化内容补齐期）。

---

## 2. mini probe 实验数据（唯一已跑批次）

**批次目录**：`generator/experiments/20260502T164726Z_s15_vellin_001/`（first run；后续 5 张续 batch 同 batch_name 但未生图）
**入库 commit**：`1185518` `feat(content): import 5 vellin character_sheet portraits via mini probe (T-1.5.6 U-CL-3 gate)`

### 2.1 数据汇总

| 指标 | 值 |
|---|---|
| total_pending_packages_generated | 5（mini probe 期内 visual_experiment 产出）|
| total_imported | 5（image_import 全过）|
| total_rejected | 0 |
| mechanical_check_pass_rate | **100%**（5/5）|
| acceptance_rate | **N/A**（未跑 visual_review_cli；作者 mini probe 期内**亲眼**确认 5/5 同一人，达到 U-CL-3 阈值 ≥ 4/5）|
| total_cost_usd | **$0.00**（manual 模式；ChatGPT Plus 订阅 sunk cost）|

### 2.2 5 张立绘

| asset_id | 表情 | 文件 | 入库时间 |
|---|---|---|---|
| `img_vellin_neutral_torso_up_01` | neutral | `content/visuals/vellin/img_vellin_neutral_torso_up_01.png` | 2026-05-02T16:34Z |
| `img_vellin_smiling_torso_up_02` | smiling（forced）| `content/visuals/vellin/img_vellin_smiling_torso_up_02.png` | 2026-05-02T16:34Z |
| `img_vellin_wary_torso_up_03` | wary | `content/visuals/vellin/img_vellin_wary_torso_up_03.png` | 2026-05-02T16:34Z |
| `img_vellin_tense_torso_up_04` | tense | `content/visuals/vellin/img_vellin_tense_torso_up_04.png` | 2026-05-02T16:34Z |
| `img_vellin_looking_distant_torso_up_05` | looking_distant | `content/visuals/vellin/img_vellin_looking_distant_torso_up_05.png` | 2026-05-02T16:34Z |

5 张统一规格：1254×1254 PNG RGBA（**注**：原 ChatGPT 输出为 RGB；已 Pillow 后处理转 RGBA 通过 image_validator——实际背景仍不透明，详见 R1.5-5）。

### 2.3 失败原因分布

无（5/5 入库；0 rejected）。

### 2.4 视觉 AI 判官 vs 作者本人评审对比

**未跑**——T-1.5.8 落地的视觉 12 维 AI 判官 prompt（`/generator/prompts/visual/REVIEW_PROMPT_AI_JUDGE_VISUAL.md`）尚未在 mini probe 5 张上实际跑过。Cohen's kappa 无法计算（推到 R1.5-3）。

---

## 3. 工作量速览

| 任务 | Commit | 一句话成果 |
|---|---|---|
| T-1.5.1 | `77a5f54` | ADR-014 + ROADMAP 1.5 实质 + SCHEMA_v0.2.md 占位 + visuals/_reference/ 目录 |
| T-1.5.1A | `4b4a8d9` | /generator/CLAUDE.md 历史化阶段 1 禁令 + pyproject 注册 generator.prompts.visual |
| T-1.5.2 | `3105648` | image_asset.schema.json + waystation.json 角色 visual_assets + SCHEMA_v0.2.md 完整 + schema 测试 |
| T-1.5.3 | `12b5942` | ImageProvider Protocol + ManualImportProvider + datamodel-code-generator 双 entry |
| T-1.5.4 | `f62d0cd` | image_validator 机械预检（9 维度 + Pillow + magic bytes 防伪造） |
| T-1.5.5 | `91dfd33` | image_cost_log + image_budget（check + log_charge 拆分；ADR-014 数字）|
| T-1.5.6 | `b278ba5` | generate_character_sheet + generate_scene_background + 双语 prompt 模板 + character_features 锚定 + U-CL-3 mini probe gate 实施 |
| T-1.5.7 | `b460c73` | image_import CLI + manifest.json 读写 + 结构化 import_log + 入库流程（manual + ontology 写入合法授权）|
| T-1.5.8 | `8c92e87` | visual_experiment + visual_review_cli + visual_metrics + 12 维 AI 判官 prompt 粗起 |
| T-1.5.9 | `9826667` | OpenAIImageProvider + visual_parity_smoke（fallback graceful；可推后） |
| **附**：mini probe 5 张入库 | `1185518` | 5 张 vellin 立绘端到端入库——manual pipeline 实证 |
| **附**：9 份 Codex 评审报告 backfill | `33611cd` | 跨 LLM 评审完整审计轨迹 |

每个任务**3 阶段（A 开发 / B GPT 评审 / C Claude 修复）全闭环**——10 任务 × 3 = 30 阶段全部 PASS；**Round 5 综合闸门 U-GPT-3 / U-GPT-6 / U-CL-2 / U-CL-3 / C8 全部纳入对应任务实施 + 修复 cycle**。

---

## 4. 遗留问题（R1.5-*）

| # | 项 | 性质 | 处理时机 | 来源 |
|---|---|---|---|---|
| **R1.5-1** | 14 character_sheet 立绘 + 1 scene background 全 batch 真实生图未跑（vellin 06-10 / corvan / aelwin / scene；prompt 包已生成在 _pending/ 等待，作者主动跳过手工 ChatGPT 生图） | 内容补齐 | **阶段 3 作者审阅工坊期**（一致环境下批量补；或阶段 4 商业化前内容填充期）| 作者主动选择 |
| **R1.5-2** | acceptance_rate（U-CL-2）未测——0 张资产经 visual_review_cli 走 review_log；mini probe 5/5 系作者亲检确认 5/5 同一人但未走结构化 review log | 评测覆盖 | **同 R1.5-1**（全 batch 生图后跑 visual_review_cli + visual_metrics）| Round 5 U-CL-2 |
| **R1.5-3** | 视觉 12 维 AI 判官（`REVIEW_PROMPT_AI_JUDGE_VISUAL.md`）vs 作者本人 Cohen's kappa 未算 —— 判官 prompt 是粗起一版，跨模型校准能力差异大 | 评测校准 | **阶段 2/3** —— 真实 batch 数据到位后跑判官 + 算 kappa；如 kappa < 0.5 则判官 prompt 回炉 | Round 5 U-CL-1 同款思路（视觉版）|
| **R1.5-4** | C4 dev/prod parity smoke test 未跑（作者无 OPENAI_API_KEY；OpenAIImageProvider 已实施但 smoke skipped）—— ADR-014 同源假设（manual ChatGPT vs API gpt-image-1）**未实证** | 假设验证 | **作者拿到 OPENAI_API_KEY 后**单独跑 `python -m generator.visual_parity_smoke --prompts <path> --n 3`；约 $0.51 一次性成本 | Round 5 C4 |
| **R1.5-5** | character_sheet 立绘 alpha 通道**形式合规但实际不透明**——ChatGPT GPT-Image 网页版默认输出 RGB；用 Pillow `convert('RGBA')` 后 alpha 全 255，实际背景仍是 soft wash 而非透明 | 资产质量 | **阶段 2/3 任一** —— 三选一：(a) prompt 调优强制 transparent RGBA（实测不稳）；(b) 集成 `rembg` 后处理（需新增依赖）；(c) 切 OpenAIImageProvider api 模式实测是否更可控 | mini probe 期实测发现 |
| **R1.5-6** | mini probe 5 张 ChatGPT 实际下载文件名为 `图1.png` ~ `图5.png`，作者人手 cp 后改名进 _pending；这一步缺工具支持（如 `image_import --from-downloads --rename-by-order`），未来 batch 跑作者会重复同样手工 | 工作流 ergonomic | **阶段 3 工坊化** | mini probe 期实操痛点 |

**已知遗留但已记 CLEANUP（不在 R1.5-* 重列）**：
- T-1.5.6 review #3.2 跨边界（已 commit `3583159`）
- T-1.5.7 review #4.5 三写半失败窗口（已 commit `73e4aab`，阶段 2 解决）
- R1（schema 合格率 85%）/ R2 (复合 condition few-shot) / R3 (选项过长) / R4 (location_ref 错配) / R5 (本体污染 D1) / R6 (AI 判官替代) / R7 (cost_log 高估) / R8 (机械预检器) —— **阶段 1 R 项**，1.5 范围外不复列

---

## 5. 阶段 2 启动前置条件

阶段 2 = 场景级 AI 生成 + 图校验。启动闸门按 [`/docs/ROADMAP.md` § 阶段 2 启动闸门](ROADMAP.md) + [Round 5 synthesis §6](reviews/master_plan/2026-04-30_synthesis.md) 实施：

**ADR-015 sequencing 已锁**——
- ✅ 1.5 manual 主线已交付（部分；本验收报告即签字）
- ⏳ **阶段 2 schema 实际 commit 现可启动**（1.5 已签字 → 串行卡口解锁）
- ⏳ **阶段 2 规划层（ADR / 范围 / 任务拆分）由 L1 / 阶段 2 规划师会话承担**——本会话不规划阶段 2

阶段 2 启动闸门清单（**留给阶段 2 规划师在 STAGE_2_TASKS.md 中纳入**）：

- **C1**：本体最小可生成契约（character / location / relation / state path 边界 schema）
- **C3**：阶段 1 R 项（R2 / R3 / R4 / R8）作为阶段 2 启动 cleanup gate
- **U-GPT-1**：ADR-009 第二层方法论拆 2A 拓扑 + 2B 抽样验证 / 有界符号执行
- **U-GPT-4**：阶段 2 baseline 协议（样本数 / 重试规则 / AI 判官权重 / 接受口径）
- **U-GPT-5**：角色槽位持久化形态决策（synthesis 推荐持久化层仍 concrete `character_refs`）

强建议（非硬闸门）：
- **U-CL-4**：Chapter / Act schema 前移到阶段 2 起手期
- **C5**：开源剥离边界清单从阶段 2 起维护

**HANDOFF_STAGE_1.5_TO_2.md** 由阶段 2 规划师在启动期产出，**不在本任务范围**。

---

## 6. 真实费用回顾

| 项 | 估算 | 实际 | 备注 |
|---|---|---|---|
| Manual 部分（mini probe 5 张 + visual_experiment 跑 4 batch 写 prompt 包）| $0 | **$0.00** | ChatGPT Plus 订阅摊薄；image_cost_log 5 行 manual 全 cost=$0 |
| API 部分（T-1.5.9 OpenAIImageProvider）| $20-$40 总盘子 | **$0.00**（smoke 全 skip）| 作者无 OPENAI_API_KEY；R1.5-4 |
| **1.5 总计** | $20-$40 | **$0.00** | |
| 单次硬卡 $1.00 触及次数 | — | 0 | manual 模式不烧 |
| 日预算 $5.00 触及次数 | — | 0 | 同上 |

**比预算大幅省**——manual 主线策略实证：ChatGPT Plus 订阅作 sunk cost 时，1.5 阶段实际 marginal $0/张。

---

## 7. 模块边界自检

```bash
$ grep -RE "from generator|import generator" engine/ state/ schema/ validator/
（空 — 运行时 + schema + state + validator 模块零依赖 /generator/）

$ grep -RE "import google\.genai|import openai" generator/ --include="*.py" | grep -v "providers/"
（空 — 业务代码无直接 SDK import；必须经 LLMProvider / ImageProvider 接口）

$ grep -RE "import openai|from openai|import google\.genai" engine/
（空 — 运行时绝不引入图像 / LLM SDK；ADR-002）
```

✅ ADR-002 / ADR-004 / ADR-006 / ADR-008 / ADR-011 / ADR-012 / ADR-013 / ADR-014 / ADR-015 在阶段 1.5 内全部坚守。

**额外验证**（1.5 特有）：
- ✅ `image_import` CLI 是阶段 1.5 唯一被授权写 `/state/ontology/waystation.json` 的代码路径（仅 `entities[type=character].visual_assets` 字段；T-1.5.7 边界硬闸门 + ontology 写入合法授权见 `/generator/CLAUDE.md` 阶段 1.5 例外段）
- ✅ /content/visuals/_reference/ 目录在 git，内容 .gitignore（合规预防；T-1.5.1 加固）
- ✅ /content/visuals/_pending/ 整目录 .gitignore（避免临时 prompt 包污染 git）
- ✅ /generator/image_cost_log.jsonl + /generator/import_log.jsonl 都在 .gitignore（runtime 写产物）

---

## 8. 跨 LLM 评审实绩（阶段 1.5 cycle 数据）

10 个任务 × 3 阶段（A 开发 / B Codex 评审 / C Claude 修复）全闭环：

| 任务 | B 阶段 finding 数 | C 阶段 fix commit 数 |
|---|---|---|
| T-1.5.1A | 4（1🔴 + 1🟡 + 1🟡 跨边界 + 1🟢） | 3 + 1 CLEANUP |
| T-1.5.2 | 3（2🟡 + 1🟢）| 3 |
| T-1.5.3 | 1（1🔴）| 1 |
| T-1.5.4 | 3（1🔴 + 1🟡 + 1🟢）| 3 |
| T-1.5.5 | 2（1🟡 + 1🟢）| 2 |
| T-1.5.6 | 7（1🔴 + 4🟡 + 1🟢 + 1 跨边界）| 6 + 1 CLEANUP |
| T-1.5.7 | 6（1🔴 + 4🟡 + 1🟢 + 1 跨边界）| 5 + 1 CLEANUP |
| T-1.5.8 | 4（2🔴 + 2🟡）| 4 |
| T-1.5.9 | 4（1🔴 + 3🟡）| 4 |
| **合计** | **34 finding**（7🔴 + 19🟡 + 5🟢 + 3 跨边界）| **31 fix + 3 CLEANUP** |

**100% finding 闭环率**（含 NICE 默认跳过 / 跨边界记 CLEANUP 的合规跳过）。**审计轨迹完整 commit `33611cd`**。

§通用 review prompt 模板在 1.5 期内**升级 2 次**（同样跨 LLM 评审驱动）：
- `a1c9cb5` → 加 grep self-check（防 T-1.5.1A 风格漏 placeholder）
- `de13110` → 4 条自检升级（防 T-1.5.5 / T-1.5.7 风格 prose-substitute）
- `f8479aa` → 两 commit 拆分约定 promote 为正式（解锁与 self-check Check 2 的鸡生蛋冲突）

---

## 9. 签字

**作者**：outsiderrr · **日期**：2026-05-02 · **签字**：[作者填写]

**接受条件**：
1. 以"工具链端到端验证（mini probe）"作为 1.5 实质交付物
2. R1.5-* 6 条遗留**不阻塞**阶段 2 启动；分别按各项处理时机推进
3. 阶段 2 schema commit 串行卡口解锁——可由阶段 2 规划师拍板启动
