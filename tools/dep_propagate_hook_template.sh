#!/usr/bin/env bash
# T-3.7 / ADR-023 dep_propagate pre-commit hook（**模板**——T-3.7 prompt §DP-5
# 明示不强制安装；作者按需 `cp tools/dep_propagate_hook_template.sh
# .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` 启用）。
#
# 触发条件：本次 commit 暂存区含 `state/ontology/*.json` 改动 → 跑 dep_propagate
# 反向 propagate 报告（since HEAD）；输出仅警告，不阻断 commit（CLAUDE.md 规则 7
# 精神：决策权在作者；hook 自动 abort 容易误伤）。
#
# 退出码：始终 0；报告写到 `docs/reviews/_dep_propagate_<timestamp>.md`，作者
# 自行决定是否 amend / 追加修复 commit。
set -euo pipefail

ontology_changed=$(git diff --cached --name-only -- 'state/ontology/*.json' || true)
if [ -z "$ontology_changed" ]; then
  exit 0
fi

ts=$(date -u +"%Y%m%dT%H%M%SZ")
report_dir="docs/reviews"
mkdir -p "$report_dir"
report_path="${report_dir}/_dep_propagate_${ts}.md"

echo "[dep_propagate hook] ontology files staged for commit:"
echo "$ontology_changed" | sed 's/^/  - /'
echo "[dep_propagate hook] running reverse propagate against HEAD..."

if ! python3 -m tools.dep_propagate --since HEAD --report "$report_path"; then
  echo "[dep_propagate hook] WARN dep_propagate exited non-zero; report may be incomplete."
fi

if [ -f "$report_path" ]; then
  echo "[dep_propagate hook] report written to: ${report_path}"
  echo "[dep_propagate hook] review the report before pushing; commit not blocked."
fi
