"""tools/cross_review.py 单测（无网络；transport 注入）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.cross_review import (
    CrossReviewError,
    build_review_target,
    call_relay,
    extract_template,
    pack_prompt,
    run_review,
    truncate_diff,
    validate_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_META = {
    "number": 99,
    "title": "feat: 测试用 PR",
    "body": "PR 自述正文",
    "headRefName": "claude/test-branch",
    "baseRefName": "main",
    "files": [{"path": "generator/foo.py"}, {"path": "engine/player.py"}],
}


def test_extract_template_pulls_text_block():
    md = "前言\n```text\n模板正文 {{REVIEW_TARGET}}\n多行\n```\n后记"
    assert extract_template(md) == "模板正文 {{REVIEW_TARGET}}\n多行"


def test_extract_template_missing_block_raises():
    with pytest.raises(CrossReviewError):
        extract_template("没有代码块")


def test_extract_template_works_on_real_template():
    real = (REPO_ROOT / "docs" / "REVIEW_PROMPT_CODE_GPT.md").read_text(encoding="utf-8")
    body = extract_template(real)
    assert "{{REVIEW_TARGET}}" in body
    assert "评审维度" in body


def test_truncate_diff_small_passthrough():
    diff = "diff --git a/x b/x\n+small\n"
    out, notices = truncate_diff(diff)
    assert out == diff
    assert notices == []


def test_truncate_diff_per_file_cap():
    big = "diff --git a/big.json b/big.json\n" + "+x\n" * 20_000
    small = "diff --git a/s.py b/s.py\n+ok\n"
    out, notices = truncate_diff(big + small, per_file_cap=1000, total_cap=10**9)
    assert "已截断" in out
    assert "+ok" in out  # 小文件不受影响
    assert any("big.json" in n for n in notices)


def test_truncate_diff_total_cap():
    diff = "diff --git a/a b/a\n" + "+y\n" * 5000
    out, notices = truncate_diff(diff, per_file_cap=10**9, total_cap=500)
    assert len(out) < 700
    assert "truncated total diff" in notices


def test_build_review_target_and_pack_prompt():
    target = build_review_target(_META, ["docs/prompts/stage_3/T-3P-0.md"], "看边界")
    assert "PR #99" in target and "L2 视角补充上下文" in target
    packed = pack_prompt(
        template="头 {{REVIEW_TARGET}} 尾",
        review_target=target,
        model="gpt-test",
        context_files={"CLAUDE.md": "根规则"},
        diff_text="diff --git ...",
        pr_body="自述",
    )
    assert "{{REVIEW_TARGET}}" not in packed  # 槽位已填
    assert "API 交付形态说明" in packed
    assert "打包上下文：CLAUDE.md" in packed
    assert "被评审 diff" in packed and "自述" in packed


def test_call_relay_rejects_claude_family():
    with pytest.raises(CrossReviewError):
        call_relay("p", base_url="http://x", api_key="k", model="claude-fable-5")


def test_call_relay_parses_transport_response():
    def fake_transport(url, payload, headers):
        assert url.endswith("/chat/completions")
        assert payload["model"] == "gpt-test"
        assert headers["Authorization"] == "Bearer k"
        return {
            "choices": [{"message": {"content": "# Code Review — ok"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    content, usage = call_relay(
        "p", base_url="http://x/v1", api_key="k", model="gpt-test", transport=fake_transport
    )
    assert content.startswith("# Code Review")
    assert usage["completion_tokens"] == 5


def test_validate_report():
    assert validate_report("\n# Code Review — X\n...")
    assert not validate_report("好的，我来评审……")


def _run(tmp_path, transport, report_name="r.md", **kw):
    out = tmp_path / report_name
    rc = run_review(
        repo_root=REPO_ROOT,
        pr_meta=_META,
        diff_text="diff --git a/generator/foo.py b/generator/foo.py\n+code\n",
        task_prompt_paths=[],
        l2_context=None,
        out_path=out,
        model="gpt-test",
        base_url="http://relay/v1",
        api_key="k",
        transport=transport,
        **kw,
    )
    return rc, out


def test_run_review_writes_report(tmp_path, monkeypatch):
    # budget 记账走真实 cost_log 会污染仓库日志 → 指到临时文件
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost.jsonl"))

    def transport(url, payload, headers):
        # 打包 prompt 里应含根 CLAUDE.md 与两个模块 CLAUDE.md 的上下文标头
        content = payload["messages"][0]["content"]
        assert "打包上下文：CLAUDE.md" in content
        assert "打包上下文：generator/CLAUDE.md" in content
        return {"choices": [{"message": {"content": "# Code Review — PR #99\n正文"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    rc, out = _run(tmp_path, transport)
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Code Review")
    assert "delivered via tools/cross_review.py" in text


def test_run_review_invalid_report_saves_raw(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost.jsonl"))

    def transport(url, payload, headers):
        return {"choices": [{"message": {"content": "抱歉，我不能……"}}], "usage": {}}

    rc, out = _run(tmp_path, transport)
    assert rc == 1
    assert not out.exists()
    assert out.with_suffix(".raw.md").exists()


def test_run_review_dry_run_no_transport(tmp_path):
    rc, out = _run(tmp_path, transport=None, dry_run=True)
    assert rc == 0
    assert not out.exists()
