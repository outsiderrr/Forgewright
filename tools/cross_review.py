"""B 阶段自动化：经中转站 API 驱动跨模型（非 Claude 系）代码评审（governance v0.6 §13）。

用法（v1：只产报告文件；commit/push 由调用会话执行）：

    PYTHONPATH=. python -m tools.cross_review --pr 82 \\
        --task-prompt docs/prompts/stage_3/T-3P-0.md \\
        [--l2-context "重点看 E1-E8 边界与 loader 异常面"] [--dry-run]

环境（.env / 进程环境）：
    LLM_API_KEY     中转站 key（必填）
    LLM_BASE_URL    中转站 base url，OpenAI 兼容（必填）
    REVIEW_MODEL    评审模型 id（必填；**必须非 Claude 系**——cross-LLM 独立性硬要求）

流程：gh 拉 PR 元数据+diff → 打包上下文（REVIEW_PROMPT_CODE_GPT 模板 API 交付形态
+ 根/模块 CLAUDE.md + 任务规格 + diff，超限截断留告示）→ 调中转站 → 报告落
docs/reviews/<ISO_DATE>_pr<N>_review.md。评审调用经 generator.budget 记账（ADR-012）。

退出码：0=报告已写；1=API/报告格式失败（原始响应存 .raw.md）；2=用法/输入/环境错误。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

TEMPLATE_PATH = "docs/REVIEW_PROMPT_CODE_GPT.md"
DEFAULT_PER_FILE_CAP = 20_000  # 单文件 diff 字符上限（超出截断留告示）
DEFAULT_TOTAL_CAP = 120_000  # 打包 prompt 里 diff 总字符上限
_TIMEOUT_SEC = 600
# 实测（2026-07-08）：中转站 gpt-5.5 不带 max_tokens 会返回 content=None（token 烧在
# reasoning 上不透出）——必须显式给上限。评审报告 12k 足够。
_MAX_OUTPUT_TOKENS = 12_000
_RETRIES = 2  # 连接级失败（远端掐线等）重试次数

_API_PREAMBLE = """【API 交付形态说明（governance v0.6 §13）】
本次评审经中转站 API 进行：你没有仓库访问能力，全部上下文已打包在下文。
模板正文里"启动前必读（自己去读文件）/写报告文件/commit/push"等操作指令对你不适用
——那些是给交互式 Codex 会话的；对应材料已由工具打包附上。
你只输出一件东西：完整的评审报告 markdown 全文（严格按模板"报告产出→文件结构"
的格式，第一行就是「# Code Review — …」），不要输出报告以外的任何文字。
报告的落盘与 push 由调用方工具完成。评审者署名用「{model} via relay API」。
"""


class CrossReviewError(Exception):
    """用法/输入/环境错误（退出码 2 语义）。"""


def extract_template(template_md: str) -> str:
    """从 REVIEW_PROMPT_CODE_GPT.md 提取 ```text 代码块内的 stable 模板正文。"""
    m = re.search(r"```text\n(.*?)\n```", template_md, flags=re.DOTALL)
    if not m:
        raise CrossReviewError(f"{TEMPLATE_PATH} 里找不到 ```text 模板块")
    return m.group(1)


def truncate_diff(
    diff_text: str,
    *,
    per_file_cap: int = DEFAULT_PER_FILE_CAP,
    total_cap: int = DEFAULT_TOTAL_CAP,
) -> tuple[str, list[str]]:
    """按文件截断超大 diff（fixture/json 常见），再套全局上限。返回 (diff, 告示列表)。"""
    notices: list[str] = []
    parts = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    kept: list[str] = []
    for part in parts:
        if not part:
            continue
        if len(part) > per_file_cap:
            header = part.splitlines()[0] if part.splitlines() else "(unknown file)"
            kept.append(
                part[:per_file_cap]
                + f"\n…（本文件 diff 超 {per_file_cap} 字符，已截断——完整内容见 PR）\n"
            )
            notices.append(f"truncated per-file: {header}")
        else:
            kept.append(part)
    joined = "".join(kept)
    if len(joined) > total_cap:
        joined = (
            joined[:total_cap]
            + f"\n…（diff 总量超 {total_cap} 字符，已整体截断——完整内容见 PR）\n"
        )
        notices.append("truncated total diff")
    return joined, notices


def build_review_target(
    pr_meta: dict, task_prompt_paths: list[str], l2_context: str | None
) -> str:
    lines = [
        f"PR #{pr_meta['number']}：{pr_meta['title']}",
        f"分支 {pr_meta['headRefName']}（base = {pr_meta['baseRefName']}）",
    ]
    if task_prompt_paths:
        lines.append("任务规格（全文已打包在下方上下文）：" + " + ".join(task_prompt_paths))
    if l2_context:
        lines.append(
            "L2 视角补充上下文（不替 finding；仅作 review 关注方向）：" + l2_context
        )
    return "\n".join(lines)


def pack_prompt(
    *,
    template: str,
    review_target: str,
    model: str,
    context_files: dict[str, str],
    diff_text: str,
    pr_body: str = "",
) -> str:
    filled = template.replace("{{REVIEW_TARGET}}", review_target)
    blocks = [_API_PREAMBLE.format(model=model), filled]
    for path, content in context_files.items():
        blocks.append(f"\n===== 打包上下文：{path} =====\n{content}")
    if pr_body:
        blocks.append(f"\n===== PR 描述（A 阶段自述，含自报事项） =====\n{pr_body}")
    blocks.append(f"\n===== 被评审 diff =====\n{diff_text}")
    return "\n".join(blocks)


def validate_report(text: str) -> bool:
    return text.lstrip().startswith("# Code Review")


def call_relay(
    packed_prompt: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
    transport: Callable[[str, dict, dict], dict] | None = None,
) -> tuple[str, dict]:
    """调中转站 chat/completions。返回 (报告文本, usage dict)。transport 可注入供测试。"""
    if "claude" in model.lower():
        raise CrossReviewError(
            f"REVIEW_MODEL={model!r} 是 Claude 系——cross-LLM 独立性硬要求（governance §13.1），拒绝执行"
        )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": packed_prompt}],
        "temperature": 0.2,
        "max_tokens": _MAX_OUTPUT_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if transport is None:
        transport = _http_transport
    url = base_url.rstrip("/") + "/chat/completions"
    last_exc: Exception | None = None
    for attempt in range(1 + _RETRIES):
        try:
            resp = transport(url, payload, headers)
            break
        except (OSError, urllib.error.URLError) as e:  # 连接级失败可重试
            last_exc = e
            print(
                f"[cross_review] 连接失败（第 {attempt + 1} 次）: {e}", file=sys.stderr
            )
    else:
        raise RuntimeError(f"中转站连接连续失败 {1 + _RETRIES} 次: {last_exc}")
    try:
        choice = resp["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"中转站响应形态异常: {e}: {str(resp)[:500]}") from e
    if not content:
        raise RuntimeError(
            "中转站返回空 content"
            f"（finish_reason={choice.get('finish_reason')!r}, "
            f"usage={resp.get('usage')}）——检查 max_tokens / 模型行为"
        )
    return content, resp.get("usage", {}) or {}


def _http_transport(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as r:
        return json.loads(r.read().decode("utf-8"))


def _charge_budget(packed_chars: int, model: str):
    """ADR-012：评审调用经 budget 拦截记账。中转站评审模型无定价表 → 成本按 0 估、
    token 记实数（audit trail 目的）；费用异常由 cost_log 周对账兜底（governance §13.4）。"""
    try:
        from generator import budget
    except ImportError:
        return None, None
    record_id = budget.check_and_charge(
        0.0, model_id=model, input_tokens=packed_chars // 4, output_tokens=4000
    )
    return budget, record_id


def gather_pr(pr: int, repo_root: Path) -> tuple[dict, str]:
    """经 gh CLI 拉 PR 元数据 + diff。"""
    meta_raw = subprocess.run(
        ["gh", "pr", "view", str(pr), "--json", "number,title,body,headRefName,baseRefName,files"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    diff = subprocess.run(
        ["gh", "pr", "diff", str(pr)],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(meta_raw), diff


def collect_context_files(
    repo_root: Path, pr_meta: dict, task_prompt_paths: list[str]
) -> dict[str, str]:
    """根 CLAUDE.md + diff 触及模块的 CLAUDE.md + 任务规格文件。"""
    out: dict[str, str] = {}
    for rel in ["CLAUDE.md"]:
        p = repo_root / rel
        if p.exists():
            out[rel] = p.read_text(encoding="utf-8")
    top_dirs = {f["path"].split("/")[0] for f in pr_meta.get("files", []) if "/" in f["path"]}
    for d in sorted(top_dirs):
        p = repo_root / d / "CLAUDE.md"
        if p.exists():
            out[f"{d}/CLAUDE.md"] = p.read_text(encoding="utf-8")
    for rel in task_prompt_paths:
        p = repo_root / rel
        if not p.exists():
            raise CrossReviewError(f"任务规格文件不存在: {rel}")
        out[rel] = p.read_text(encoding="utf-8")
    return out


def run_review(
    *,
    repo_root: Path,
    pr_meta: dict,
    diff_text: str,
    task_prompt_paths: list[str],
    l2_context: str | None,
    out_path: Path,
    model: str,
    base_url: str,
    api_key: str,
    dry_run: bool = False,
    transport: Callable | None = None,
    per_file_cap: int = DEFAULT_PER_FILE_CAP,
    total_cap: int = DEFAULT_TOTAL_CAP,
) -> int:
    template = extract_template((repo_root / TEMPLATE_PATH).read_text(encoding="utf-8"))
    diff_trunc, notices = truncate_diff(
        diff_text, per_file_cap=per_file_cap, total_cap=total_cap
    )
    context_files = collect_context_files(repo_root, pr_meta, task_prompt_paths)
    packed = pack_prompt(
        template=template,
        review_target=build_review_target(pr_meta, task_prompt_paths, l2_context),
        model=model,
        context_files=context_files,
        diff_text=diff_trunc,
        pr_body=pr_meta.get("body", ""),
    )
    if notices:
        print("[cross_review] diff 截断告示: " + "; ".join(notices), file=sys.stderr)
    if dry_run:
        print(f"[cross_review] dry-run：打包 prompt {len(packed)} 字符；不调 API")
        return 0

    budget_mod, record_id = _charge_budget(len(packed), model)
    report, usage = call_relay(
        packed, base_url=base_url, api_key=api_key, model=model, transport=transport
    )
    if budget_mod is not None and record_id is not None:
        budget_mod.reconcile_after_call(
            record_id,
            actual_input_tokens=int(usage.get("prompt_tokens", len(packed) // 4)),
            actual_output_tokens=int(usage.get("completion_tokens", 0)),
            actual_cost_usd=0.0,
        )

    footer = (
        f"\n\n<!-- delivered via tools/cross_review.py (governance v0.6 §13); "
        f"model={model}; prompt_chars={len(packed)}; usage={json.dumps(usage)} -->\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not validate_report(report):
        raw = out_path.with_suffix(".raw.md")
        raw.write_text(report + footer, encoding="utf-8")
        print(f"[cross_review] 响应不符报告格式，原始输出已存 {raw}", file=sys.stderr)
        return 1
    out_path.write_text(report + footer, encoding="utf-8")
    print(f"[cross_review] 报告已写 {out_path}")
    print("[cross_review] 后续：由调用会话 commit + push 到 main（governance §10 第 7 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.cross_review",
        description="B 阶段自动化：中转站 API 跨模型评审（governance v0.6 §13）",
    )
    parser.add_argument("--pr", type=int, required=True, help="PR 编号")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--task-prompt", action="append", default=[], help="任务规格文件（可多次）"
    )
    parser.add_argument("--l2-context", default=None, help="L2 视角关注方向（一段文字）")
    parser.add_argument("--out", type=Path, default=None, help="报告输出路径")
    parser.add_argument("--dry-run", action="store_true", help="只打包不调 API")
    parser.add_argument("--per-file-cap", type=int, default=DEFAULT_PER_FILE_CAP)
    parser.add_argument("--total-cap", type=int, default=DEFAULT_TOTAL_CAP)
    args = parser.parse_args(argv)

    try:
        model = os.environ.get("REVIEW_MODEL", "")
        base_url = os.environ.get("LLM_BASE_URL", "")
        api_key = os.environ.get("LLM_API_KEY", "")
        if not args.dry_run and not (model and base_url and api_key):
            raise CrossReviewError(
                "缺环境变量：REVIEW_MODEL / LLM_BASE_URL / LLM_API_KEY（.env 未加载？）"
            )
        pr_meta, diff_text = gather_pr(args.pr, args.repo_root)
        out_path = args.out or (
            args.repo_root
            / "docs"
            / "reviews"
            / f"{_dt.date.today().isoformat()}_pr{args.pr}_review.md"
        )
        return run_review(
            repo_root=args.repo_root,
            pr_meta=pr_meta,
            diff_text=diff_text,
            task_prompt_paths=args.task_prompt,
            l2_context=args.l2_context,
            out_path=out_path,
            model=model or "dry-run",
            base_url=base_url,
            api_key=api_key,
            dry_run=args.dry_run,
            per_file_cap=args.per_file_cap,
            total_cap=args.total_cap,
        )
    except CrossReviewError as e:
        print(f"[cross_review] 输入/环境错误: {e}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print(f"[cross_review] gh 调用失败: {e.stderr}", file=sys.stderr)
        return 2
    except Exception as e:  # API/运行失败
        print(f"[cross_review] 运行失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
