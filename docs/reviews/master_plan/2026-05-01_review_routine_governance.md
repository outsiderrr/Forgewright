# Review / Routine 治理备忘

> 2026-05-01 L1 规划讨论结论。后续 L2 规划师与执行会话起手前必读。
>
> **本备忘不修改 L1 文档**（CLAUDE.md / DECISIONS.md / DEBATE_NOTES.md / ROADMAP.md / SCHEMA_v0*.md / HANDOFF_*.md / STAGE_*_ACCEPTANCE.md），只是把讨论共识落盘，作为下游会话的工作前提。如未来要把任何条目升格为 ADR / ROADMAP 修订，需作者明示授权 + 走专门执行会话。

**日期**：2026-05-01 · **版本**：v0.1 · **产出方**：L1 规划讨论会话（master plan 续接）
**触发问题**：作者询问能否用 Claude Code 桌面端 routines（定时任务）自动驱动 L1 → L2 → L3 整条链路

---

## 1. 核心结论

**routines 不接 L1→L2→L3 主链；只跑维护层 + 部分纯执行类 L3。** 决策点（L1/L2/B 类 L3）必须人在环路。

四个理由（详见对话记录，此处略）：

1. L2 不是 L1 的机械展开——每次都伴随新 ADR / 架构决策（ADR-014 / ADR-015 即此类）
2. L3 内部有 schema commit 串行卡口（CLAUDE.md 规则 2 + ADR-015）
3. L3 commit 经常反向触发 L2/L1 修订（阶段 1 R1–R8 即此类）
4. 作者是单点 reviewer + 不会编程，审阅带宽稀缺，错向自动跑代价大

---

## 2. L3 任务分类制度（**软建议**——能标就标，不强制）

> v0.2 修订（2026-05-01 作者拍板）：从"硬性必须"降级为软建议。理由见 §9 修订记录。

建议每个 L3 任务条目标注类型；**未标注的 L3 默认按 `[B-author-gate]` 处理**——即每个 commit 让作者看一眼再放下一个，保持安全默认。三种类型描述如下：

### `[A-execute]` 类：纯执行，可 routine 串行自动跑

- 写代码 / 写测试 / 写 docstring / 重构 / 修 bug
- 不动 `/schema/*` / `/docs/DECISIONS.md` / `/docs/ROADMAP.md` / `/docs/CLAUDE.md` / 其他 L1 文档
- 阶段 1 例：T-1.2 / T-1.3 / T-1.4 / T-1.5 / T-1.7

### `[B-author-gate]` 类：架构级，必须硬停等作者拍板

- 动 schema 文件 / 新增或修订 ADR / 修订 SCHEMA_v0*.md / 验收报告
- 触发 CLAUDE.md 规则 9/10 例外条款，需作者明示授权
- 阶段 1 例：T-1.0（动 SCHEMA_v0.md）/ T-1.1（ADR-011/012/013 立项）/ T-1.8（验收）
- 阶段 1.5 已知例：T-1.5.1（ADR-014，已 commit `77a5f54`）/ T-1.5.2（image_asset schema + visual_assets 字段）/ T-1.5.10（验收）

### 隐藏第三类：反向回退 / 修复任务

- 不在原 L3 清单里，由前置 L3 跑出问题反向冒出
- 阶段 1 例：commit `10017b7` / `54e0920` / `db06af5`（baseline 迭代修 bug）
- routine 跑到 validate-all 失败时**硬停叫人**，不机械跑下一个

---

## 3. Review tier 分层（**review 颗粒度匹配决策颗粒度**）

| 层级 | 评审对象 | 评审者 | 触发 | 频率估计 |
|---|---|---|---|---|
| **L1** | 路线图 / 跨阶段 sequencing / 整体架构 | cross-LLM（Claude × GPT-5.5） | 作者主动起会话 | 项目周期共 1–3 次（Round 5 已 1 次） |
| **L2** | `STAGE_X_TASKS.md` 草稿 | cross-LLM 手动跑 | L2 规划师草稿合入前必经 | 每阶段 1 次（5–6 次） |
| **B 类 L3** | schema / ADR / 验收报告 commit | cross-LLM 手动跑（升级到 L2 标准） | B 类 L3 commit 后 | 每阶段 1–3 次 |
| **A 类 L3** | 代码 commit | 本地 `/review` skill + validate-all | commit-time 自动 | 每阶段 5–10 次 |

**关键约束**：A 类 L3 **不上 cross-LLM**——会产生大量噪声 review，消耗作者审阅带宽，反而违反"快速决策"原则。

---

## 4. Routines 启用清单（settings.json hook 由 update-config skill 后续落地）

### 当下启用（3 项）

| ID | Routine | 频率 | 说明 |
|---|---|---|---|
| **5a** | `make validate-all` 日跑 | 每天 1 次（凌晨） | schema 校验 + 单元测试 + lint；早抓 silent breakage |
| **5b** | `cost_log` 对账 | 每周 1 次 | 阶段 1 R7 已知 cost_log 高估（验收 §6：估 $2.14 vs 真实 $0.7–1.2）；周对账校准 |
| **5c** | `anthropic-skills:consolidate-memory` 跑 | 每周 1 次 | 现有 skill 直接调用；防 memory 文件腐烂 |

### 推到阶段 2/3 再启用

- 长跑 baseline 实验过夜跑（阶段 2 baseline_005+ 才需要；按需手动启动，不严格 routine）
- dependency drift scan（synthesis §6 `content_dependency_index` 雏形；阶段 3+ 才有意义）
- GitHub PR 状态扫描（阶段 4 开源剥离后）

### 不启用

- 事件触发 git hook / GitHub Action 跑 GPT critique——L2 + B 类 L3 合计每阶段 2–4 次触发，频率太低，搭基础设施不划算

---

## 5. L2 规划师工作约束（明日起）

### 产 `STAGE_X_TASKS.md` 时建议做

1. **鼓励**每个 L3 任务条目标 `[A-execute]` 或 `[B-author-gate]`——但**未标注不阻塞 L3 启动**；未标走 [B-author-gate] 安全默认（作者每个 commit 看一眼）。v0.2 修订
2. 草稿落地后**手动**起 cross-LLM critique 会话（GPT-5.5 / Codex），跑 stable critique prompt（Round 5 `master_plan_battle_*` 系列已验证可复用），结果落 `/docs/reviews/stage_X/2026-XX-XX_gpt_critique.md`
3. critique 消化后形成最终版本 TASKS.md，作者明示授权后才进入 L3 执行
4. B 类 L3 commit 后**手动**起 cross-LLM critique，结果落 `/docs/reviews/stage_X/`

### 不要做

- 不要尝试搭 git hook / GitHub Action 自动化 critique——按当前频率手动跑性价比更高
- 不要让 routine 跨 B 类 L3 跑下一个 [A-execute]——B 类必须硬停
- 不要把 L1 文档当 [A-execute] 改——任何 L1 文档 commit 都是 [B-author-gate]，需作者明示授权

---

## 6. 待办（按时机）

| 时机 | 事项 | 责任方 |
|---|---|---|
| 立刻 | 起草 routines 5a/5c 的 settings.json hook 配置 prompt（用 update-config skill） | 作者起执行会话 |
| 阶段 1.5 启动 | 起草 STAGE_1.5_TASKS.md 时按 §2 标 [A-execute] / [B-author-gate]；草稿落地后跑 6-A 手动 critique | 阶段 1.5 L2 规划师 |
| R7 想真修时 | 实现 cost_log 反向对账脚本（5b 启用前置） | 阶段 2 起手期某个 [A-execute] L3 |
| 阶段 2 启动 | 同 §2 / §5 流程 | 阶段 2 L2 规划师 |

---

## 7. 决策表（作者已 ✓ 的拍板项）

- ✓ **1**：L1→L2→L3 主链不接 routines，保持人在环路
- ✓ **2**：L2 review = cross-LLM 强制 gate
- ✓ **3a**：L3 review 深度 = 本地 `/review` + validate-all
- ✓ **3b**（v0.2 软化）：分类是软建议——能分时 [A-execute] 可 routine 串行 / [B-author-gate] 硬停；**未分类默认 [B-author-gate]**（作者每个 commit 看一眼）
- ✓ **4**：B 类 L3（动 schema / ADR / provider 接口）升级到 L2 review 标准
- ✓ **5a / 5b / 5c**：启用 validate-all 日跑 + cost_log 周对账（推到 R7 想真修时）+ memory consolidate 周跑
- ✓ **5d/e/f 推迟**：长跑实验 / drift scan / PR 扫描推到阶段 2/3
- ✓ **6-A**：L2 critique 走手动模式（不引入事件触发自动化）

---

## 8. 与现有 L1 文档的兼容性

本备忘不与任何 L1 文档冲突：

- **CLAUDE.md 规则 2 + 9 + 10**：B 类 L3 显式继承"作者明示授权"逻辑
- **ADR-015**：1.5 schema commit 串行 + 阶段 2 schema commit 等 1.5 验收 = 自然映射到本备忘 [B-author-gate] 类
- **ROADMAP §阶段 2 启动闸门 / §阶段 3 完成标志强化项**：占位指针待 L2 规划师落地，本备忘明确"L2 规划师必须先跑 cross-LLM critique 才能进 L3"
- **HANDOFF_STAGE_1_TO_1.5.md / HANDOFF_STAGE_1_TO_2.md**：未来交接档应在"工作模式"段补一行指向本备忘

如未来需要把本备忘任何条目升格为 ADR-016+ / ROADMAP 修订，由作者明示授权 + 专门执行会话执行（参考 ADR-011/012/013/014/015 合入先例：commit `1d2030f` / `77a5f54` / `9851419`）。

---

## 9. 修订记录

- **2026-05-01 v0.2**：作者拍板把 §2 任务分类制度从"硬性必须"降级为"软建议"。触发：阶段 1.5 已在执行中（T-1.5.1 commit `77a5f54` 已完成 / T-1.5.1a 已完成 / 后续 L2 规划层在路上），实际推进观察到 L3 大半涉及 schema / image / ADR / provider 接口，B 类居多，强制分类边际收益低。修订点：§2 引言语气 + §5 第 1 条 + §7 3b。**默认行为不变**：未分类的 L3 走 `[B-author-gate]`（作者每个 commit 看一眼），保持安全。其余条款（§3 review tier / §4 routines 启用清单 / §6 待办 / §8 与 L1 兼容性）未变。
- **2026-05-01 v0.1**：初版。L1 规划讨论"能否用桌面端 routines 自动驱动 L1→L2→L3"问题落盘，含核心结论 / 任务分类制度（硬性版）/ review tier 分层 / routines 启用清单 / L2 规划师约束。

## 版本

本文件版本：v0.2
最后更新：2026-05-01（v0.2 同日修订）
