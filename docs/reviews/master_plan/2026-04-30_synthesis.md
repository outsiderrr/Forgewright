# Master Plan Critique — Round 5 — 综合 (Claude × GPT-5.5)

**综合者**：Claude (cold-start session)
**综合日期**：2026-04-30
**两份原评审**：
- [`2026-04-30_claude_critique.md`](2026-04-30_claude_critique.md) — Claude (🔴4 🟡7 🟢3 = 14)
- [`2026-04-30_gpt55_critique.md`](2026-04-30_gpt55_critique.md) — GPT-5.5 via Codex (🔴3 🟡10 🟢3 = 16)

> 这是一份**只供作者拍板用**的综合 memo——把两份 critique 的共识、互补、分歧、行动清单聚合成单一可决策视图。**不替代两份原评审**——具体论据回各自文件查；不是新 ADR / 不是 ROADMAP 修改提案——是议题清单。

---

## 1. 综合判断

**前向路线图方向健康，但有两类问题需要在阶段 1.5 启动前后处理**：

(a) **8 条核心议题双方独立得出相同结论**——这些是路线图当前形态的真盲点（双方独立 critique 高 confidence 共识 = 不是单边偏见）。

(b) **两边各有独家洞察**，互补后清单更完整——尤其 GPT-5.5 抓到的 7 条 Claude 漏抓（验证了 cold-start 同模型评审仍有自我确认偏差，Round 5 跨模型组合的价值）。

**阶段 1.5 可启动**，但需补 4 条低成本启动闸门（详见 §5）。

---

## 2. 双方共识必修（C1–C8 — 高 confidence）

两边独立得出相同结论。Claude 严重度按其原评审；GPT 同。

| # | 议题 | Claude | GPT-5.5 | 综合严重度 |
|---|---|---|---|---|
| **C1** | **阶段 2 启动前需要"本体最小可生成契约"**（角色 / 地点 / 关系 / 状态路径事实卡）；否则 R4/R5 在多节点指数化放大 | §3.3 🔴 | §3.1 🔴 | **🔴** |
| **C2** | **ADR-009 第三层 playtest bots 必须在阶段 3 完成标志里**——否则阶段 4 才发现 50–100 场景里有 worst-bucket 路径 | §3.2 🔴 | §3.3 🔴 | **🔴** |
| **C3** | **R 项升级为阶段 2 启动 cleanup gate**（R2/R3/R4/R8 必先合入），不能只藏在 HANDOFF / 验收报告尾巴 | §4.4 🟡 | §4.5 🟡 | **🟡** |
| **C4** | **dev/prod prompt 同源是假设不是事实**——1.5 验收前至少跑 3 条 prompt 的对比 smoke test，未做就显式列遗留 | §4.3 🟡 | §4.3 🟡 | **🟡** |
| **C5** | **开源剥离边界 hook 从阶段 2/3 起维护清单**（fixture / 资产版权 / provider 假设），阶段 4 再执行 | §4.7 🟡 | §4.6 🟡 | **🟡** |
| **C6** | **阶段 3 一致性维护缺内容依赖索引**——本体变更如何反向 propagate 到生成产物没有设计 | §3.1（隐含）+ §9-1 | §4.9 🟡 | **🟡** |
| **C7** | **总时长偏乐观**——阶段 0/1 节奏不可外推，内容审阅 + 视觉返工 + 外部用户验证另算 | §3.4 🔴 | §4.7 🟡 | **🟡（修正）** |
| **C8** | **阶段 1.5 API stretch goal 验收口径要明示**（manual passed / API implemented / API parity validated 三态） | §4.3（包含） | §5.1 🟢 | **🟢** |

**严重度分歧只有 C7 一条**：Claude 🔴，GPT 🟡。综合后修正为 **🟡**——GPT 的拆估法（"工程 MVP 4.5–7 月" + "内容+开源 v0.1 另给 6–10 月"）比 Claude 原 §3.4 的"阶段 4 拆 4a/4b"更建设性，问题指向相同。

---

## 3. Claude 独家（5 条 — GPT 漏抓）

| # | 议题 | Claude 出处 | 严重度 |
|---|---|---|---|
| **U-CL-1** | 阶段 3 完成标志"一周 10 场景"是过程指标，无质量门槛（接受率 / 返工率） | §3.1 | 🔴 |
| **U-CL-2** | 阶段 1.5 完成标志多处不可测——manifest 完整性 100% 含义、接受率分母分子歧义 | §4.1 | 🟡 |
| **U-CL-3** | 角色一致性 C+B 兜底无硬指标——建议 vellin 5 张 mini probe 作为 T-1.5.6 启动 gate | §4.2 | 🟡 |
| **U-CL-4** | Chapter/Act schema 推到阶段 3 = 阶段 1/2 内容回填——建议前移到阶段 2 起手期 | §4.5 | 🟡 |
| **U-CL-5** | DEBATE §9.2 长对话一致性路线图无任何缓解措施 | §4.6 | 🟡 |

---

## 4. GPT-5.5 独家（7 条 — Claude 漏抓，承认偏见）

这些是 GPT 抓到 Claude 漏抓的事项——验证了 Round 5 跨 LLM 评审的实际增益。

| # | 议题 | GPT-5.5 出处 | 综合严重度 |
|---|---|---|---|
| **U-GPT-1** | **"证明任意合法状态组合可达结局"目前不可判定**——当前 schema 无状态变量定义域 / 初始状态集合 / effect 代数边界。建议把 ADR-009 第二层拆成 **2A 纯拓扑** + **2B 有界状态符号执行**；若只做抽样模拟要在完成标志里把"证明"改成"抽样验证" | §3.2 | **🔴** |
| **U-GPT-2** | 阶段 1.5 vs 阶段 2 sequencing 文档间冲突——`HANDOFF_STAGE_1_TO_2.md` 仍写"1.5 已推迟"，与 ADR-014 manual 模式消除阻塞冲突；执行会话会误读 | §4.1 | 🟡 |
| **U-GPT-3** | 背景图无一等引用位置 = manifest 孤儿资产风险——具体建议：`ImageAsset` 加 `target_ref` + `target_type` + `asset_role` 字段 | §4.2 | 🟡 |
| **U-GPT-4** | 阶段 2 70% 接受率缺 baseline 协议——样本数 / 重试规则 / AI 判官权重 / 机械失败口径都没定 | §4.4 | 🟡 |
| **U-GPT-5** | 角色槽位"抽象槽 vs 具体角色"持久化决策——这是 ROADMAP 唯一明确提到的阶段 2 重点，但落地决策点没拆开。**推荐**：持久化层仍 concrete `character_refs`，抽象槽作为 generator 中间产物 + `generation_trace` 记录 | §4.8 | 🟡 |
| **U-GPT-6** | 视觉资产 provenance / 版权元数据进 manifest——`source_mode` / `prompt_hash` / `reference_ids` / `reference_license_note` / `open_source_ok` / `commercial_ok`；阶段 4 商业化合规黑箱预防 | §4.10 | 🟡 |
| **U-GPT-7** | 阶段 3 审阅 UI 应有图视图作为第一公民——graph/mermaid 视图 + 路径列表 + validator panel + visual asset thumbnail | §5.2 | 🟢 |

---

## 5. 综合后阶段 1.5 启动 checklist

**4 项硬闸门 + 2 项软（可在 1.5 期内补）**

### 启动前（硬闸门）

- [ ] **C8** 验收三态口径写入 STAGE_1.5_TASKS.md：manual passed / API implemented / API parity validated（GPT §5.1）
- [ ] **U-CL-3** 角色一致性 mini probe：T-1.5.6 启动前跑 vellin 5 张让作者亲检"5 张里 ≥ 4 张是同一人"（Claude §4.2）
- [ ] **U-GPT-3** 背景资产挂载契约：T-1.5.2（image_asset.schema.json）必须含 `target_ref` + `target_type` + `asset_role` 字段（GPT §4.2）
- [ ] **U-GPT-2** 修文档冲突：`HANDOFF_STAGE_1_TO_2.md` 关于"1.5 已推迟"的过期叙述与 ADR-014 对齐（GPT §4.1）

### 1.5 期内（软）

- [ ] **C4** dev/prod parity smoke test：1.5 验收前至少 3 条 prompt 跑一次 manual vs API 对比，成本 ≈ $0.50（共识）
- [ ] **U-CL-2** 完成标志可测义补充：manifest 完整性定义 / 接受率分母分子（Claude §4.1）
- [ ] **U-GPT-6** 视觉资产 provenance 字段并入 ImageAsset schema 或 manifest（GPT §4.10）

---

## 6. 综合后阶段 2 启动 checklist

**5 项硬闸门 + 2 项强建议**

### 启动前（硬闸门）

- [ ] **C1** 本体最小可生成契约闸门：character / location / relation / state path 的事实边界 schema（共识 🔴）
- [ ] **C3** R 项 cleanup gate：R2/R3/R4/R8 prompt + 文本机械预检合入，作为 generate_scene 前置（共识）
- [ ] **U-GPT-1** ADR-009 第二层拆 2A/2B：把"证明结局可达"改写成 2A 拓扑校验 + 2B 抽样验证 / 有界符号执行（GPT §3.2 🔴）
- [ ] **U-GPT-4** 阶段 2 baseline 协议：先定 baseline 样本数 / 重试规则 / AI 判官权重 / 接受口径，再写代码（GPT §4.4）
- [ ] **U-GPT-5** 角色槽位持久化决策：抽象槽是否进 JSON？推荐持久化层仍 concrete（GPT §4.8）

### 强建议

- [ ] **U-CL-4** Chapter/Act schema 前移到阶段 2 起手期，与本体 Schema 打包做（Claude §4.5）
- [ ] **C5** 开源剥离边界清单从阶段 2 起维护（共识，但非硬闸门）

---

## 7. 综合后阶段 3 启动前置

不是阶段 3 的 checklist 完整版，只列两边都点出的"阶段 3 前必须先解决"：

- [ ] **C2** ADR-009 第三层 playtest bots 写入阶段 3 完成标志（共识 🔴）
- [ ] **C6** 内容依赖索引设计——`content_dependency_index` 作为生产期 sidecar，记录每个生成产物读过哪些 ontology ids / state paths / prompt hash / visual asset ids（共识，GPT §4.9 给了具体形态）
- [ ] **U-CL-1** 阶段 3 完成标志加质量门槛——X% 单次接受率 + Y 场景/周吞吐（Claude §3.1 🔴）
- [ ] **U-GPT-7** 阶段 3 审阅 UI 第一版含图视图（GPT §5.2 🟢）
- [ ] **U-CL-5** 长对话一致性缓解策略 ADR / 任务（Claude §4.6）

---

## 8. Top 3 综合最担心

按"如果不处理，project 最可能在哪里翻车"排序：

1. **阶段 2 在本体桩态启动 → 场景级污染 + 校验"通过"假象**
   - 双方共识 #1
   - GPT 表述更精准："图校验通过但事实层污染"
   - Claude §3.3 + GPT §3.1 合流

2. **ADR-009 第三层缺位 → 阶段 4 才发现 worst-bucket 路径**
   - 双方共识 #2
   - 影响 MVP 内容质量底线
   - Claude §3.2 + GPT §3.3 合流

3. **阶段 3 审阅 UI / 一致性维护 / 内容依赖索引一起被低估 → 阶段 3 时间黑洞 + 作者中段失去动力**
   - Claude §3.4（项目存活级风险） + GPT §4.9 + §5.2 合流
   - 这是综合后浮现的复合风险，单看任一份评审不会这么严重

---

## 9. 综合后开放决策清单（去重 → 9 项）

按建议处理顺序排：

1. **阶段 1.5 vs 阶段 2 sequencing 口径**（C8 + U-GPT-2 推荐："1.5 manual 主线先启动；2 的本体 / 角色槽位 schema 串行")
2. **阶段 2 是否必须先落地正式本体最小 Schema**？范围到角色/地点/关系/状态路径哪一级？（C1）
3. **角色槽位是否允许进入持久化 JSON**？还是只作为 generator 中间产物？（U-GPT-5）
4. **背景资产挂载到哪里**：location/scene 也加 `visual_assets`，还是 manifest 用 `target_ref` 解决？（U-GPT-3）
5. **"任意合法状态组合可达结局"的真实义**：严格证明 / 有界符号执行 / 抽样模拟？直接影响完成标志措辞（U-GPT-1）
6. **playtest bots 阶段位**：阶段 3 / 阶段 4 / 推到开源剥离后？（C2）
7. **Chapter/Act schema 时机**：阶段 2 起手期 / 保持阶段 3？（U-CL-4）
8. **开源剥离边界清单何时开始维护**：阶段 2/3 / 阶段 4？（C5）
9. **总时长拆估**：采纳 GPT "工程 4.5–7 月 + 内容/开源另 6–10 月"？（C7）

---

## 10. 阶段 1.5 启动建议（综合后）

**结论：直接启动，但带 4 条硬闸门 + 1 条 sequencing 决策**

- 采纳 GPT 的 sequencing 口径："**1.5 manual 主线先启动；阶段 2 的本体 / 角色槽位 schema 设计可并行起草，但 schema 实际 commit 等 1.5 验收后**"——遵守阶段 0/1.5 串行卡口先例
- 启动前补 §5 的 4 条硬闸门（成本：4 条都是文档 / 配置级，0 代码工作量）
- §5 软闸门可在 1.5 期内分批补
- §6 阶段 2 启动 checklist 不在 1.5 启动前要求完成——但建议作者读完决定哪些可在 1.5 期内并行起草

---

## 11. 元评审：跨 LLM 评审的实际增益

Round 5 是 Claude × GPT-5.5 第一次交手，可观察的增益：

- **共识 8 条**（§2）= 单方评审就能抓到的事项；跨模型只是冗余确认
- **互补 12 条**（§3 + §4）= 跨模型增益，单独一份评审会漏掉一半
  - Claude 漏抓 7 条（U-GPT-1 到 U-GPT-7），其中 U-GPT-1 是 🔴
  - GPT 漏抓 5 条（U-CL-1 到 U-CL-5），其中 U-CL-1 是 🔴
- **严重度分歧 1 条**（C7）= 综合后修正
- **0 条直接矛盾**（一边说 X 另一边说非 X）

**结论**：跨 LLM 评审在 Round 5 体现出了 ~50% 的事项增益（12 条互补 / 24 条总数），不是冗余开销。建议在阶段 2/3 关键决策点继续保留这一工作流。

---

## 版本

本文件版本：v0.1（首次综合）
日期：2026-04-30
关联 critique：[Claude](2026-04-30_claude_critique.md) + [GPT-5.5](2026-04-30_gpt55_critique.md)
