"""T-0.9 三层校验器测试。

覆盖：
  - content/test_scene_v0/scene.json → PASS
  - scene_broken_schema.json → FAIL at [schema]
  - scene_broken_dangling.json → FAIL at [graph]（悬空）
  - scene_broken_unreachable.json → FAIL at [graph]（不可达）
  - 本目录 fixtures/*.json 覆盖一致性层三类错误 + 图论层两类补充错误
  - CLI exit code / 不短路行为 / ValidationReport 结构
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from validator import ValidationReport, validate
from validator.cli import main as cli_main

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "test_scene_v0"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

SCENE = CONTENT_DIR / "scene.json"
SCENE_BROKEN_SCHEMA = CONTENT_DIR / "scene_broken_schema.json"
SCENE_BROKEN_DANGLING = CONTENT_DIR / "scene_broken_dangling.json"
SCENE_BROKEN_UNREACHABLE = CONTENT_DIR / "scene_broken_unreachable.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 四个内容样本
# ---------------------------------------------------------------------------

def test_scene_passes_all_three_layers():
    report = validate(_load(SCENE))
    assert isinstance(report, ValidationReport)
    assert report.passed, f"expected PASS, got errors={report.errors}"
    assert report.errors == []
    assert report.issues_by_level["schema"] == []
    assert report.issues_by_level["graph"] == []
    assert report.issues_by_level["cons"] == []


def test_broken_schema_fails_at_schema_layer():
    report = validate(_load(SCENE_BROKEN_SCHEMA))
    assert not report.passed
    assert len(report.issues_by_level["schema"]) >= 1
    # graph_id 违反正则，应在 schema 层被抓
    assert any(
        "graph_id" in issue.location or "graph_id" in issue.message
        for issue in report.issues_by_level["schema"]
    )


def test_broken_dangling_fails_at_graph_layer_with_specific_locator():
    report = validate(_load(SCENE_BROKEN_DANGLING))
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    graph_errors = report.issues_by_level["graph"]
    assert len(graph_errors) >= 1
    # 错误消息必须能定位到 N3 节点的 opt_reveal_to_corvan 选项 + end_iron_gallows 目标
    joined = "\n".join(
        f"{issue.location} {issue.message}" for issue in graph_errors
    )
    assert "patrol_arrives" in joined
    assert "opt_reveal_to_corvan" in joined
    assert "end_iron_gallows" in joined


def test_broken_unreachable_fails_at_graph_layer_with_orphan_id():
    report = validate(_load(SCENE_BROKEN_UNREACHABLE))
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    graph_errors = report.issues_by_level["graph"]
    assert any(
        issue.location == "orphan_warning_from_vellin"
        for issue in graph_errors
    )


# ---------------------------------------------------------------------------
# 一致性层三类错误（手工 fixtures）
# ---------------------------------------------------------------------------

def test_speaker_ref_outside_character_refs_fails_at_cons():
    report = validate(_load(FIXTURES_DIR / "speaker_ref_outside_character_refs.json"))
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    assert report.issues_by_level["graph"] == []
    cons = report.issues_by_level["cons"]
    assert any(
        "speaker_ref" in issue.message and "char_corvan" in issue.message
        for issue in cons
    )


def test_dialogue_speaker_ref_outside_character_refs_fails_at_cons():
    """ADR-040：dialogue[].speaker_ref 也走 ⊆ character_refs 闭合（同 node.speaker_ref）。"""
    report = validate(
        _load(FIXTURES_DIR / "dialogue_speaker_ref_outside_character_refs.json")
    )
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    assert report.issues_by_level["graph"] == []
    cons = report.issues_by_level["cons"]
    # 坏的那条（char_corvan ∉ character_refs）触发，location 指到 dialogue
    assert any(
        "speaker_ref" in issue.message
        and "char_corvan" in issue.message
        and "dialogue" in issue.location
        for issue in cons
    )
    # 合法的 char_vellin 不应触发任何 cons 问题
    assert not any("char_vellin" in issue.message for issue in cons)


def test_duplicate_option_id_fails_at_cons():
    report = validate(_load(FIXTURES_DIR / "duplicate_option_id.json"))
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    assert report.issues_by_level["graph"] == []
    cons = report.issues_by_level["cons"]
    assert any(
        "duplicate option_id" in issue.message and "opt_dup" in issue.message
        for issue in cons
    )


def test_character_ref_not_in_ontology_fails_at_cons():
    report = validate(_load(FIXTURES_DIR / "character_ref_not_in_ontology.json"))
    assert not report.passed
    assert report.issues_by_level["schema"] == []
    assert report.issues_by_level["graph"] == []
    cons = report.issues_by_level["cons"]
    assert any(
        "char_unknown_specter" in issue.message and "ontology" in issue.message
        for issue in cons
    )


# ---------------------------------------------------------------------------
# 图论层补充错误
# ---------------------------------------------------------------------------

def test_no_end_node_fails_at_graph_layer():
    report = validate(_load(FIXTURES_DIR / "no_end_node.json"))
    assert not report.passed
    assert any(
        'no terminal node' in issue.message
        for issue in report.issues_by_level["graph"]
    )


def test_entry_node_missing_fails_at_graph_layer():
    report = validate(_load(FIXTURES_DIR / "entry_node_missing.json"))
    assert not report.passed
    # entry 不存在于 nodes 是 graph 层错误
    assert any(
        'entry_node_id' in issue.message and issue.location == "root"
        for issue in report.issues_by_level["graph"]
    )


# ---------------------------------------------------------------------------
# 行为 / 结构断言
# ---------------------------------------------------------------------------

def test_layers_do_not_short_circuit():
    """Schema 层失败时，后续图论 / 一致性层仍必须运行。"""
    # 制造一个：schema 失败（graph_id 非法）+ 一致性失败（speaker_ref 超出 char_refs）
    payload = _load(FIXTURES_DIR / "speaker_ref_outside_character_refs.json")
    payload["graph_id"] = "Bad.Id#123"  # 违反 D7 正则
    report = validate(payload)
    assert not report.passed
    assert len(report.issues_by_level["schema"]) >= 1
    # 尽管 schema 失败，cons 层也跑了并抓到 speaker_ref 问题
    assert any(
        "speaker_ref" in issue.message for issue in report.issues_by_level["cons"]
    )


def test_validate_returns_issues_by_level_keys():
    report = validate(_load(SCENE))
    assert set(report.issues_by_level.keys()) == {"schema", "graph", "cons"}


# ---------------------------------------------------------------------------
# CLI 契约
# ---------------------------------------------------------------------------

def test_cli_exits_zero_on_pass():
    out = io.StringIO()
    rc = cli_main(["validator", str(SCENE)], stdout=out)
    assert rc == 0
    assert "PASS" in out.getvalue()


def test_cli_exits_one_on_fail_and_tags_all_layers():
    out = io.StringIO()
    rc = cli_main(["validator", str(SCENE_BROKEN_DANGLING)], stdout=out)
    assert rc == 1
    output = out.getvalue()
    assert "[graph]" in output
    assert "FAIL" in output


def test_cli_usage_on_bad_args():
    out = io.StringIO()
    rc = cli_main(["validator"], stdout=out)
    assert rc == 1
    assert "Usage" in out.getvalue()
