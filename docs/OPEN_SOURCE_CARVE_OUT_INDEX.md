# 开源剥离边界清单（OPEN_SOURCE_CARVE_OUT_INDEX）v0.2

> Sidecar，跟踪从 `forgewright`（私有 + 全过程仓库）剥离 `forgewright-framework`（开源工具核心）时需要拆出 / 替换 / 文档化的内容。
> 阶段 2 起手时建立首版（C5 强建议；STAGE_2_TASKS §2.1 D6），阶段 3 维护增量（T-3.11；synthesis §6/§7 C5），阶段 4 执行剥离。

## §1 用途

- 跟踪从 forgewright 仓库剥离开源框架时需要**拆出 / 替换 / 文档化**的内容。
- 阶段 2 起维护，阶段 4 执行剥离。
- 不替代 ROADMAP §4（剥离动作本身），仅作为"已知私有依赖"的连续清单 hook，避免阶段 4 才发现遗漏。

## §2 三类边界

### A. fixture / 角色 / 场景内容（作者本人项目；不能进开源框架默认）

- `/content/test_scene_v0/scene.json`（《铁誓驿站》gold scene）
- `/state/ontology/waystation.json`（vellin / corvan / aelwin 角色实体 + 关系）
- `/generator/prompts/few_shot.py` 引用的内容（节点级 few-shot 含《铁誓驿站》台词 / 角色名）
- `/generator/prompts/scene/few_shot.py` 引用的内容（**v1.0 新增；D6 修订** — 场景级 few-shot 同上）
- `/generator/prompts/scene/system.py` 含《铁誓驿站》场景默认 prompt 时（**v1.0 新增；D6 修订** — 标记并由 T-2.5 落地后回填）
- `/generator/fixtures/scene/`（如 T-2.12 加 scene fixture，**v1.0 新增**）

### B. 资产版权（视觉资产）

- `/content/visuals/`（mini probe 5 张 vellin 立绘 + 后续 batch 资产；版权属作者，不进开源默认）
- `/content/visuals/_reference/`（作者私有风格参考；已 `.gitignore`）
- `/generator/image_cost_log.jsonl` + `import_log.jsonl`（runtime 产物，非框架内容；剥离时不带）

### C. provider 假设（默认 SDK / API key）

- `GeminiProvider` 默认 `model_id`（`gemini-3.1-pro-preview`）—— 开源默认应给可替换 provider 接口或抽象基类，不锁定 Google
- `OpenAIImageProvider`（`gpt-image-1`）—— 同上
- `.env` / `.env.example`（API key）—— 已 `.gitignore`；开源仓只留示例 stub，不带具体 key 或 endpoint

## §3 v0.2 增量（阶段 3 引入的私有依赖）

> T-3.11 落地（C5 在阶段 3 期间维护边界 hook 的延续工作）。本节按 v0.1 §2 三类边界（A/B/C）扩展 + 加 D/E/F 三个新类。所有条目继承 §5（原 v0.1 §3）维护规则；本版本仅记录"已知"，剥离动作在阶段 4 执行。
>
> **执行说明**：以下条目对应阶段 3 任务 T-3.0 ~ T-3.10 期间引入的模块；执行时这些模块大多尚未落地（T-3.11 在 Wave 0 起手），属于前瞻 hook，避免阶段 4 才发现。阶段 3 末期（T-3.10 实测后）需回填具体路径 + 实测产出至 §4 follow-up 段。

### v0.2-A：fixture / 角色 / 场景内容增量

1. `/generator/playtest/personas/*.json`（5 个 persona JSON：`cautious` / `aggressive` / `completionist` / `speedrunner` / `role_player`；T-3.4 落地）—— 通用 RPG persona 范式，**建议保留入开源默认**；如 `augmented_description` 字段含《铁誓驿站》上下文（角色名 / 关系 / 地点），剥离时清理至通用样例。
2. `/generator/playtest_cost_log.jsonl` + `/tools/review_ui/state/review_log.jsonl`（runtime 产物；T-3.4 / T-3.6a 落地）—— 运行期日志，**剥离时不带**；与 v0.1 §B `image_cost_log.jsonl` / `import_log.jsonl` 同类。

### v0.2-B：资产版权增量

3. `/content/visuals/` 阶段 3 实测期补充资产（如 R1.5-1 遗留的 14 立绘 + 1 background；T-3.10 实测期触发）—— 沿用 v0.1 §B 规则（版权属作者，不进开源默认）；阶段 3 末期视实测产出补具体路径至 §4 follow-up。

### v0.2-C：provider 假设增量

4. `/generator/batch_scheduler.py`（T-3.5 落地）—— 默认 `N=3` 并发 + `RPM=60` + ontology 锁基于 `fcntl` POSIX file lock 假设。**POSIX file lock 在 Windows 不可用**；v0.2 标记需提供跨平台 fallback（如 `portalocker` 库），剥离时由 framework 仓库实现。
5. `/tools/review_ui/server.py`（T-3.6a 落地；F2 + F17 修订要点）：
   - **FastAPI + uvicorn 依赖**：引入 Python Web 生态依赖（`pip install fastapi uvicorn` 一行；门槛低但破纯 stdlib 假设）；剥离时 framework 仓库需在 README 文档化最小依赖集 + 可选 Web UI 模块。
   - **mermaid.js CDN URL 假设**：v0.2 应已含 vendor bundle fallback（T-3.6a 范围）；CDN URL 可能不可用 / 大版本变化，**剥离时 framework 仓库默认走 vendor，不依赖 CDN**。
6. `/generator/version_recorder.py`（T-3.8a 落地）—— `git subprocess` 假设：调用本地 `git` 命令读 commit hash / dirty 状态。**非 git 用户**（如直接 zip 下载 framework 用户）无法用；v0.2 标记需提供 fallback path（如 hash from file mtime + content；剥离时 framework 实现）。

### v0.2-D：用户配置默认值（新类别）

7. **环境变量默认值**（T-3.5 / T-3.6a 落地）：
   - `FORGEWRIGHT_BATCH_CONCURRENT_N`（默认 3；基于 PoloAI 速率限制）
   - `FORGEWRIGHT_PROVIDER_RPM`（默认 60；同上）
   - `FORGEWRIGHT_REVIEW_UI_PORT`（默认 `8765`；本地 localhost 审阅 UI 端口，可由开源用户按端口冲突情况覆盖；STAGE_3_TASKS §2.4 / §3.4 锁定）

   全部默认基于作者环境，**开源用户需在 README 文档化所有 env vars**（类型 / 默认值 / 调整指引）；剥离时 framework 仓库附 `.env.example`。
8. `prompt_template_hash` 算法（SHA256 of concat 文件；T-3.5 / T-3.2 dep_index 调用）—— 算法假设稳定，剥离时 v0.2 维持原样；如未来需改算法，需在 ADR-023（dep_index）补迁移说明。

### v0.2-E：阶段 1.5 R1.5-* 遗留对开源剥离的影响

9. **R1.5-1**（剩余 14 立绘 + 1 background 全 batch 跳过；阶段 1.5 遗留）—— 阶段 4 剥离时如开源 framework 不带任何视觉资产例子，需提供 placeholder 资产（占位图 + 文档说明 + 生成示例 prompt），保证开源用户能跑通视觉资产 import / 校验 / dep_index 引用全链。
10. **R1.5-3**（视觉判官 vs 作者 kappa 未算；阶段 1.5 遗留）—— 不影响开源剥离；标记为**作者评测专属，不入框架默认评测路径**；剥离时 framework 仓库的视觉判官 baseline 协议建议给通用样例（不带《铁誓驿站》上下文）。

### v0.2-F：阶段 3 cross-LLM critique workflow（新类别）

11. `/docs/REVIEW_PROMPT_L2_STAGE_TASKS.md`（阶段 3 新建模板；含 7 个占位符）—— 跨 LLM 评审 L2 阶段任务清单的标准 prompt 模板，**建议入开源框架默认**（可复用阶段 4+ 任务清单 critique）；剥离时去除项目专属占位符填充例子，保留 prompt 骨架。
12. `/docs/reviews/master_plan/*` 系列文档（阶段 3 各轮 critique / response / synthesis）—— 治理审计轨迹；**阶段 4 剥离时建议保留**作为 "how this project handled cross-LLM review" 的开源案例参考（非 framework 默认必须，但作为 governance 范例有教育价值）。

---

## §4 阶段 3 末期 follow-up 段（T-3.10 实测期回填）

> 占位段。阶段 3 T-3.10 实测期（≥ 1 周 / ≥ 10 场景）跑批后，由作者或 T-3.11 后续 follow-up 任务回填实测产出引入的具体边界条目（如：实测期补的视觉资产路径、实测期发现的新 provider 假设、实测期触发的 R3.X follow-up 引入的依赖等）。
>
> 回填格式同 v0.1 §3（改 §5）维护规则：`- <路径>（<一句话来由 / 任务编号 / 修订标记>）`。
>
> v0.3（如阶段 3 末期需要再加增量）由 T-3.12 阶段 3 验收报告 / R3.X follow-up 触发。

（待回填）

---

## §5 阶段 2 / 3 维护规则（原 §3）

- 每个新增的 schema fixture / 资产引用 / provider 假设落新一行到 §2（v0.1 baseline）/ §3（v0.2 增量）对应类。
- L3 任务执行会话发现新边界时追加（`[A-execute]` 兼容 routine）。
- 追加格式：`- <路径>（<一句话来由 / 任务编号 / 修订标记>）`。
- 不在此处做剥离动作本身（阶段 4 才执行）；本清单仅记录"已知"。
- **v0.2 起新增**：阶段 3 任务（T-3.0 ~ T-3.12）引入的私有依赖落 §3 v0.2 增量段；阶段 3 末期实测期产出落 §4 follow-up 段。

## §6 版本历史

### v0.1 状态：起步清单

即 §2。本版本由 T-2.10 起步，吸收 STAGE_2_TASKS v1.0 D6（critique 4.6）对 scene prompt 子包 + scene fixtures 的修订标注。

### v0.2 状态：阶段 3 增量

即 §3（v0.2-A ~ v0.2-F 六类）+ §4（阶段 3 末期 follow-up 占位）。本版本由 T-3.11 落地，吸收 synthesis §6/§7 C5（阶段 2/3 期间维护边界 hook）+ STAGE_3_TASKS v1.0 F2 / F17（FastAPI deps + mermaid CDN 风险）+ HANDOFF_STAGE_2_TO_3 阶段 1.5 R1.5-* 遗留分析。

---

**版本**：v0.2
**起步任务**：T-2.10（v0.1，C5 强建议落地）→ T-3.11（v0.2，C5 阶段 3 维护增量）
**最后更新**：2026-05-08
