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
