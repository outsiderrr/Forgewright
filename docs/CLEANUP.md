# CLEANUP — 跨边界 / 与 ADR 冲突的 finding 记录

> 本文件记录评审中发现但**当前修复任务边界外**、不应在该任务里直接修的 finding。
> 由作者按需另开 docs/edge 边界任务处理；不阻塞当前任务推进。

---

## 2026-05-01 — T-1.5.1A 评审 §4.1（跨边界）

- **来源**：`/docs/reviews/2026-05-01_T-1.5.1A_review.md` §4.1
- **类别**：[STYLE]
- **位置**：`/docs/reviews/_prompts/T-1.5.1A_codex_review.md:43`（及 `:45 / :49 / :87 / :135 / :184` 等出现处）
- **问题**：T-1.5.1A 主 commit (4b4a8d9) 捎带产出的 Codex 评审 prompt 文件残留 `[REVIEW_COMMIT]` / `[REVIEW_STATS]` placeholder 未替换为实际值（`4b4a8d9` / `3 files changed, 290 insertions(+), 2 deletions(-)`）。本次评审已手工补齐上下文，但若作者复用此文件，会得到 `git show [REVIEW_COMMIT]` 等不可执行目标，破坏 paste-ready 承诺。
- **为什么不在 T-1.5.1A 修复会话内修**：T-1.5.1A 修复任务边界严禁改 `/docs/`（只允许 `/generator/CLAUDE.md` + `/pyproject.toml`）。
- **建议处理路径**：作者另开一个 docs 边界任务（仅 `/docs/reviews/_prompts/T-1.5.1A_codex_review.md` 一文件）执行 placeholder 替换；同时检查 STAGE_1.5_TASKS.md `a1c9cb5` 引入的"placeholder 自检"对未来任务是否已能拦截同类问题。
- **优先级**：低（不阻塞 T-1.5.2~T-1.5.10 推进；只是同 commit 内交付的复用评审入口失效）。

---

## 2026-05-02 — T-1.5.6 评审 §3.2（跨边界）

- **来源**：`/docs/reviews/2026-05-02_T-1.5.6_review.md` §3.2
- **类别**：[ARCH]
- **位置**：`/docs/reviews/_prompts/T-1.5.6_codex_review.md:1`（位于 commit `b278ba5`）
- **问题**：T-1.5.6 实现 commit `b278ba5` 同时提交了 `docs/reviews/_prompts/T-1.5.6_codex_review.md` 这个 docs 文件，超出原任务模块边界。任务边界的"严禁修改 /docs/"未对评审 prompt 做例外授权（仅评审报告本身有例外），让该实现 commit 同时承担了"生成评审提示词"的 docs 改动。
- **为什么不在 T-1.5.6 修复会话内修**：本修复会话边界严禁改 `/docs/`（除评审报告新建/更新和本 CLEANUP 文件）。已 push 的 docs 文件不能在不被授权的情况下从历史里抹去。
- **建议处理路径**：作者另开一个 docs 边界任务，明确授权 `/docs/reviews/_prompts/`，决定是保留该评审 prompt（已被 Codex 实际使用并已落地评审报告，事后保留有价值）还是把它作为模板移到独立位置。同时检查 STAGE_1.5_TASKS.md 是否需要把"产出 codex review prompt"显式写进允许修改列表，避免后续 T-1.5.7+ 同款边界漂移。
- **优先级**：低（不阻塞合入；本 commit 携带的 docs prompt 已用于触发 T-1.5.6 Codex 评审，事实上是有价值的工件）。

---

## 2026-05-02 — T-1.5.7 评审 §4.5（跨边界）

- **来源**：`/docs/reviews/2026-05-02_T-1.5.7_review.md` §4.5
- **类别**：[ARCH]
- **位置**：`/generator/image_import.py` 成功路径 `_process_one()`（PNG move → save_manifest → _ontology_append_visual_asset 三步顺序写入；commit `b460c73` 起）
- **问题**：image_import CLI 的成功路径先 `shutil.move()` PNG，再 `save_manifest()` 写 manifest，最后 `_ontology_append_visual_asset()` 写本体。这三步分别是独立的原子写（temp + replace + fsync），但整体没有事务封装：manifest 写完后本体写入崩溃 → "PNG + manifest 已有，角色 visual_assets 没有"；PNG move 后 manifest 写入崩溃 → orphan PNG。
- **为什么不在 T-1.5.7 修复会话内修**：评审报告 §4.5 显式标 ⚠️ 跨边界——本轮不要硬修成事务系统（WAL / 两阶段提交 / SQLite 中间层），需要新模块或在 `/state/` 引入"状态写 API"统一收口，超出 T-1.5.7 修复任务边界。
- **建议处理路径**：阶段 2 正式状态写 API 落地时统一收口多文件写入；或单独开 docs/edge 任务实现 `reconcile_visual_assets.py`（扫描 manifest / ontology / `content/visuals/`，输出 orphan PNG 与 missing-embed 报告，作者人工审阅）。亦可考虑加 import-transaction marker（半成品状态写 `.in_progress` sentinel；启动时检测并提示 reconcile）。
- **优先级**：中低（不阻塞 1.5 验收，但若作者机器在生产 import 中崩溃，恢复需手动比对 manifest / ontology / 文件系统）。
