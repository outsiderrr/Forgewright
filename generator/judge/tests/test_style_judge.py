"""judge 单测（MockProvider；0 API、隔离预算）。"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from generator.judge import GATE_DIM_IDS, TAXONOMY, judge_scene, render_judge_md, write_judge_artifacts
from generator.judge.taxonomy import SCORED_DIM_IDS
from generator.llm_provider import ProviderError
from generator.prompts.judge import STYLE_JUDGE_SYSTEM, build_judge_schema, build_judge_user_prompt


@pytest.fixture()
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


_GRAPH = {
    "graph_id": "judge_test_scene",
    "nodes": {
        "opening": {
            "narration": "灯罩发黄。「先听着。」",
            "options": [{"text": "我想打听点事。"}],
        },
        "b1": {"narration": "她压低声音。", "options": [{"text": "然后呢？"}]},
        "b2": {"narration": "楼下传来响动。", "options": [{"text": "我记下了。"}]},
        "end_a": {"narration": "你起身离开。", "options": []},
        "end_b": {"narration": "门在身后合上。", "options": []},
    },
}


class MockJudgeProvider:
    model_id = "mock-judge"

    def __init__(self, *, scores: dict[str, int] | None = None, fail_at: int | None = None):
        self.scores = scores or {d: 4 for d in SCORED_DIM_IDS}
        self.fail_at = fail_at
        self.calls = 0
        self.user_prompts: list[str] = []

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.001

    def generate_structured(self, *, system_prompt: str, user_prompt: str, json_schema: dict) -> Any:
        self.calls += 1
        self.user_prompts.append(user_prompt)
        if self.fail_at is not None and self.calls >= self.fail_at:
            raise ProviderError("boom")
        content = {
            "dim_scores": [
                {"dim": d, "score": s, "evidence": "「引句」"} for d, s in self.scores.items()
            ],
            "ap_violations": (
                [{"ap_id": "AP-4", "node_id": "b1", "quote": "假靶子句", "reason": "无人预期"}]
                if self.calls == 1
                else []
            ),
            "notes": [{"dim": "S13", "note": "灰色基线成立。"}] if self.calls == 1 else [],
        }
        return SimpleNamespace(
            content=content, raw_text="{}", input_tokens=100, output_tokens=150,
            model_id=self.model_id, finish_reason="stop",
        )


def test_judge_chunks_aggregates_and_gates(isolated_budget, tmp_path) -> None:
    provider = MockJudgeProvider()
    report = judge_scene(provider, _GRAPH, chunk_size=2)
    assert report.status == "success"
    assert provider.calls == 3  # 5 节点 / chunk_size 2 → 3 块
    assert report.dim_means["S1"] == 4.0
    assert report.gate_pass is True
    assert len(report.ap_violations) == 1 and report.ap_violations[0]["ap_id"] == "AP-4"
    assert report.notes and report.notes[0]["dim"] == "S13"
    paths = write_judge_artifacts(report, tmp_path / "out")
    assert paths["json"].exists() and paths["md"].exists()
    md = paths["md"].read_text(encoding="utf-8")
    assert "gate" in md and "AP-4" in md


def test_judge_gate_fails_below_threshold(isolated_budget) -> None:
    scores = {d: 4 for d in SCORED_DIM_IDS}
    scores["S11"] = 2  # gate 维度掉到 2 → gate 不过
    report = judge_scene(MockJudgeProvider(scores=scores), _GRAPH, chunk_size=5)
    assert report.gate_pass is False
    assert report.dim_mins["S11"] == 2


def test_judge_score_zero_means_not_applicable(isolated_budget) -> None:
    scores = {d: 4 for d in SCORED_DIM_IDS}
    scores["S7"] = 0  # 本块无 end 节点 → 不适用，不计入均分
    report = judge_scene(MockJudgeProvider(scores=scores), _GRAPH, chunk_size=5)
    assert "S7" not in report.dim_means
    assert report.gate_pass is True


def test_judge_provider_error_not_raised(isolated_budget) -> None:
    report = judge_scene(MockJudgeProvider(fail_at=2), _GRAPH, chunk_size=2)
    assert report.status == "provider_error"
    assert report.failure_reason and "boom" in report.failure_reason
    assert report.gate_pass is None
    assert len(report.chunk_results) == 1  # 第一块已完成的结果保留供排查


def test_judge_system_prompt_executes_approved_standards_only() -> None:
    # 铁律 + taxonomy 全 14 维 + 7 条 AP 在 system prompt 里
    assert "不得自创新标准" in STYLE_JUDGE_SYSTEM
    assert "拿不准 = 不报" in STYLE_JUDGE_SYSTEM
    for d in TAXONOMY:
        assert f"{d.id} {d.name}" in STYLE_JUDGE_SYSTEM
    for ap in ("AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-6", "AP-9"):
        assert f"### {ap}:" in STYLE_JUDGE_SYSTEM
    for ap in ("AP-7", "AP-8", "AP-10"):
        assert f"### {ap}:" not in STYLE_JUDGE_SYSTEM  # 程序化检测不归 judge


def test_judge_user_prompt_renders_nodes_and_schema_shape() -> None:
    u = build_judge_user_prompt(
        chunk_nodes=list(_GRAPH["nodes"].items())[:2],
        scene_id="sid",
        chunk_index=1,
        chunk_total=3,
    )
    assert "节点 opening" in u and "我想打听点事。" in u
    s = build_judge_schema()
    assert s["required"] == ["dim_scores", "ap_violations", "notes"]
    assert set(s["properties"]["dim_scores"]["items"]["properties"]["dim"]["enum"]) == set(
        SCORED_DIM_IDS
    )
    assert set(GATE_DIM_IDS) <= set(SCORED_DIM_IDS)
