"""引擎端到端单测（MockProvider；0 API、隔离预算）。

验证目标（DESIGN §1/§5/§6 的可测承诺）：
  - 端到端产出**通过真 validator**（schema + mechanical 0 issue）的 dialogue_graph；
  - 全部调用都是小调用（est 护栏内）；beats reveals >4 自动分块；
  - 拓扑不合法 → 重试 → 回退脚手架（如实标 fallback）；
  - 骨架路由违规 → 带错误反馈重试一次；
  - 失败语义：ProviderError 不上抛，落 failure_reason。
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from generator.llm_provider import ProviderError
from generator.multipass.calls import CallTooLargeError, structured_call
from generator.multipass.engine import (
    MultipassSceneResult,
    SceneRunConfig,
    run_multipass_scene,
    write_artifacts,
)
from generator.multipass.render import render_scene_md

_SPEC = {
    "background": "1920 年代公路酒馆，调查氛围。",
    "design_goal": "playable scene 设计。",
    "character_state": "露西：害怕被牵连。角落男人：在看报纸。",
    "required_clues": ["线索甲", "线索乙", "线索丙", "线索丁", "线索戊"],
    "optional_clues": ["可选线索一"],
    "forbidden_events": ["不揭示完整真相"],
}

_CONFIG = SceneRunConfig(
    graph_id="test_lucy_multipass",
    scene_anchor="scene_hibo_roadhouse",
    speaker_ref="char_lucy",
    character_refs=["char_lucy"],
    npc_name="露西",
)

# 动态拓扑 canned plan：opening(choice 2 路) → 软 beats(5 条线索 → 2 次分拍调用) /
# 硬 beats(2 条) → 各自 end。
_PLAN = {
    "entry_node_id": "opening",
    "nodes": [
        {
            "node_id": "opening",
            "kind": "choice",
            "function": "开场：建立空间与风险",
            "reveals": [],
            "routes": [
                {"to": "soft_line", "stance": "低压软问"},
                {"to": "press_line", "stance": "高压施压"},
            ],
        },
        {"node_id": "soft_line", "kind": "beats", "function": "软分支：交底",
         "reveals": ["线索甲", "线索乙", "线索丙", "线索丁", "线索戊"], "next": "end_good"},
        {"node_id": "press_line", "kind": "beats", "function": "硬分支：残缺碎片",
         "reveals": ["线索甲的残缺记号", "线索乙的残缺记号"], "next": "end_bad"},
        {"node_id": "end_good", "kind": "end", "function": "带完整线索离开", "reveals": []},
        {"node_id": "end_bad", "kind": "end", "function": "带残缺碎片离开", "reveals": []},
    ],
}

_NARRATION_260 = "吧台的灯罩发黄，木头缝里渗着潮气。" * 13  # ~260 字白描占位


class MockProvider:
    """按输出 schema 特征分发 canned 内容的 LLMProvider 替身。"""

    model_id = "mock-model"

    def __init__(self, *, topology_content: dict | None = None, bad_route_first: bool = False):
        self.topology_content = topology_content if topology_content is not None else _PLAN
        self.bad_route_first = bad_route_first
        self.calls: list[str] = []
        self._skeleton_attempts: dict[str, int] = {}

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.001

    def generate_structured(self, *, system_prompt: str, user_prompt: str, json_schema: dict) -> Any:
        props = json_schema.get("properties", {})
        required = json_schema.get("required", [])
        if "entry_node_id" in props:
            kind, content = "topology", self.topology_content
        elif "failsafe_path" in props:
            kind, content = "contract", {
                "player_goal": "拿到线索",
                "npc_goal": "保住自己",
                "npc_fear": "被牵连",
                "required_clues": _SPEC["required_clues"],
                "optional_clues": _SPEC["optional_clues"],
                "failsafe_path": "残缺碎片仍可行动",
                "forbidden": ["不揭示完整真相"],
            }
        elif "choice_pressure" in props:
            kind = "skeleton"
            content = self._skeleton(json_schema, user_prompt)
        elif "beats" in props:
            kind, content = "beats", {
                "beats": [
                    {
                        "narration": "她压低声音，手指在台面上点了两下。",
                        "dialogue": ["「先听着，别记在纸上。」"],
                        "continue_option": {"text": "然后呢？"},
                    },
                    {
                        "narration": "楼下传来椅子腿刮地的声音。",
                        "dialogue": ["「剩下的，你自己看。」"],
                        "continue_option": {"text": "我记下了。"},
                    },
                ]
            }
        elif required == ["narration", "dialogue"]:
            kind, content = "end", {"narration": "你把杯子推回去，起身离开。门外的风比来时硬。", "dialogue": []}
        elif required == ["narration", "dialogue", "options"]:
            kind, content = "prose", {
                "narration": _NARRATION_260,
                "dialogue": ["要喝什么就坐吧，外头冷。", "「教授的朋友可真多。」", "“弯引号句要被归一。”"],
                "options": [
                    {"intent": "INTENT_A", "text": "我想找个人，打听点事。"},
                    {"intent": "INTENT_B", "text": "[观察] 先看看角落那个人。"},
                    {"intent": "INTENT_C", "text": "我直说了：莱特的事。"},
                ],
            }
        else:  # pragma: no cover - 未知 schema 即测试配置错误
            raise AssertionError(f"未知 schema: {list(props)}")
        self.calls.append(kind)
        return SimpleNamespace(
            content=content,
            raw_text="{}",
            input_tokens=100,
            output_tokens=200,
            model_id=self.model_id,
            finish_reason="stop",
        )

    def _skeleton(self, json_schema: dict, user_prompt: str) -> dict:
        allowed = json_schema["properties"]["options"]["items"]["properties"]["route_to"]["enum"]
        node_id = "opening"
        self._skeleton_attempts[node_id] = self._skeleton_attempts.get(node_id, 0) + 1
        if self.bad_route_first and self._skeleton_attempts[node_id] == 1:
            routes = ["nowhere"] * 3  # 全部非法 → 触发路由重试
        else:
            # 覆盖所有出边：逐个轮转
            routes = [allowed[i % len(allowed)] for i in range(3)]
        return {
            "node_id": node_id,
            "function": "开场：建立空间与风险",
            "situation": "酒馆里只有零星酒客。",
            "choice_pressure": "角落男人在看。",
            "reveals": [],
            "hides": ["深层线索"],
            "options": [
                {
                    "intent": f"INTENT_{i}",
                    "payoff": "信息",
                    "cost": "暴露",
                    "relationship_delta": "trust +1",
                    "route_to": routes[i],
                }
                for i in range(3)
            ],
        }


@pytest.fixture()
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def test_end_to_end_dynamic_topology(isolated_budget, tmp_path) -> None:
    provider = MockProvider()
    result = run_multipass_scene(provider, _SPEC, _CONFIG)

    assert result.status == "success"
    assert result.topology_fallback is False
    graph = result.graph
    assert graph is not None

    # 真 validator：schema 0 issue + mechanical 0 issue
    assert result.validation["schema_issues"] == [], result.validation["schema_issues"]
    assert result.validation["mechanical_issues"] == {}, result.validation["mechanical_issues"]
    assert result.validation["hard_pass"] is True

    # 调用构成：1 契约 + 1 拓扑 + 1 骨架 + 1 正文 + 3 分拍（5 条线索→2 次 + 2 条→1 次）+ 2 end
    assert provider.calls.count("contract") == 1
    assert provider.calls.count("topology") == 1
    assert provider.calls.count("skeleton") == 1
    assert provider.calls.count("prose") == 1
    assert provider.calls.count("beats") == 3
    assert provider.calls.count("end") == 2

    # 分拍链接线：soft_line 2 次调用 × 2 拍 = 4 拍；b1→b2→b3→b4→end_good
    nodes = graph["nodes"]
    assert graph["entry_node_id"] == "opening"
    for i in range(1, 4):
        opt = nodes[f"soft_line_b{i}"]["options"][0]
        assert opt["target_node_id"] == f"soft_line_b{i + 1}"
    assert nodes["soft_line_b4"]["options"][0]["target_node_id"] == "end_good"
    assert nodes["end_good"]["type"] == "end" and nodes["end_good"]["options"] == []

    # choice 接线：选项 route 轮转覆盖两条出边（target = beats 链第 1 拍）
    targets = {o["target_node_id"] for o in nodes["opening"]["options"]}
    assert targets == {"soft_line_b1", "press_line_b1"}

    # NPC 对白归一化进 narration（裸句加「」；已带「」不重复包；弯引号整句换「」）
    assert "「要喝什么就坐吧，外头冷。」" in nodes["opening"]["narration"]
    assert "「「" not in nodes["opening"]["narration"]
    assert "「弯引号句要被归一。」" in nodes["opening"]["narration"]
    assert "“" not in nodes["opening"]["narration"]

    # 落盘四件产物
    paths = write_artifacts(result, tmp_path / "out")
    assert paths["scene"].exists() and paths["scene_md"].exists()
    md = paths["scene_md"].read_text(encoding="utf-8")
    assert "选择节点" in md and "单选项节拍" in md and "✅ 通过" in md


def test_topology_invalid_falls_back(isolated_budget) -> None:
    bad_plan = {"entry_node_id": "opening", "nodes": [
        {"node_id": "opening", "kind": "choice", "function": "开场", "reveals": [],
         "routes": [{"to": "nowhere", "stance": "断头路"}]},
    ]}
    provider = MockProvider(topology_content=bad_plan)
    result = run_multipass_scene(provider, _SPEC, _CONFIG)

    assert result.status == "success"
    assert result.topology_fallback is True
    assert provider.calls.count("topology") == 3  # 1 + 2 重试
    assert any("回退" in w for w in result.warnings)
    # 回退脚手架照样组装出硬通过的图
    assert result.validation["hard_pass"] is True
    assert result.graph["entry_node_id"] == "opening"
    assert "hub" in result.graph["nodes"]


def test_skeleton_route_violation_retries_once(isolated_budget) -> None:
    provider = MockProvider(bad_route_first=True)
    result = run_multipass_scene(provider, _SPEC, _CONFIG)
    assert result.status == "success"
    assert provider.calls.count("skeleton") == 2  # 首次违规 + 重试
    assert any("路由违规" in w for w in result.warnings)
    # 重试后接线干净：无 route 回退 warning 之外的丢弃
    targets = {o["target_node_id"] for o in result.graph["nodes"]["opening"]["options"]}
    assert targets == {"soft_line_b1", "press_line_b1"}


def test_provider_error_not_raised(isolated_budget) -> None:
    class ExplodingProvider(MockProvider):
        def generate_structured(self, **kwargs):  # type: ignore[override]
            raise ProviderError("relay 502")

    result = run_multipass_scene(ExplodingProvider(), _SPEC, _CONFIG)
    assert result.status == "provider_error"
    assert result.graph is None
    assert "502" in (result.failure_reason or "")


def test_structured_call_size_guard(isolated_budget) -> None:
    """est_output_tokens 超护栏的调用根本不发出（不触 budget、不触 provider）。"""
    provider = MockProvider()
    with pytest.raises(CallTooLargeError):
        structured_call(
            provider,
            system_prompt="s",
            user_prompt="u",
            json_schema={},
            est_output_tokens=4096,
            label="too_big",
        )
    assert provider.calls == []  # provider 未被触碰


def test_scene_anchor_injected_into_beats_and_end(isolated_budget) -> None:
    """复核根因④修复：分拍/收束调用注入场景锚定事实（character_state）+ 禁新增人物规则."""

    class CapturingProvider(MockProvider):
        def __init__(self):
            super().__init__()
            self.user_prompts: dict[str, list[str]] = {}

        def generate_structured(self, *, system_prompt, user_prompt, json_schema):  # type: ignore[override]
            resp = super().generate_structured(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema
            )
            self.user_prompts.setdefault(self.calls[-1], []).append(user_prompt)
            return resp

    provider = CapturingProvider()
    run_multipass_scene(provider, _SPEC, _CONFIG)
    for kind in ("beats", "end"):
        for u in provider.user_prompts[kind]:
            assert "场景锚定事实" in u
            assert _SPEC["character_state"] in u


def test_beat_layer_author_feedback_rules() -> None:
    """2026-06-10 作者审阅反馈回归锁：A 电报体 / B 承接 / D 复述+疑问句 规则在分拍 prompt 内."""
    from generator.prompts.node.multipass.beat_pacing import BEAT_PACING_SYSTEM

    assert "别电报体" in BEAT_PACING_SYSTEM            # A：自然口语
    assert "承接" in BEAT_PACING_SYSTEM                # B：下一拍必须承接玩家上一句
    assert "变成问题再问一遍" in BEAT_PACING_SYSTEM     # D：不复述已答内容
    assert "不用疑问句" in BEAT_PACING_SYSTEM           # D：确认类不用疑问句


def test_mid_scene_prose_and_beats_no_reentry(isolated_budget) -> None:
    """C 项修复：非入口节点的正文/分拍调用带"非开场"信号；跨 chunk 传上一拍玩家接话."""

    class CapturingProvider(MockProvider):
        def __init__(self):
            super().__init__()
            self.user_prompts: dict[str, list[str]] = {}

        def generate_structured(self, *, system_prompt, user_prompt, json_schema):  # type: ignore[override]
            resp = super().generate_structured(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema
            )
            self.user_prompts.setdefault(self.calls[-1], []).append(user_prompt)
            return resp

    provider = CapturingProvider()
    run_multipass_scene(provider, _SPEC, _CONFIG)
    # 入口 choice（opening）= 场景开场 → 不带"非开场"提示
    assert "不是场景开场" not in provider.user_prompts["prose"][0]
    # 非入口 beats 链 → 带"非开场"提示
    for u in provider.user_prompts["beats"]:
        assert "不是场景开场" in u
    # soft_line 5 条线索分 2 块：第 2 块带"上一拍玩家刚说"承接提示（mock 末拍 continue = 我记下了。）
    second_chunks = [u for u in provider.user_prompts["beats"] if "上一拍玩家刚说" in u]
    assert second_chunks and "我记下了。" in second_chunks[0]


def test_prompts_carry_anchor_and_second_person_rules() -> None:
    """机械修复回归锁：称'你'规则 + 禁新增人物/转场规则在 prompt 内."""
    from generator.prompts.node.multipass import PASS2_PROSE_SYSTEM
    from generator.prompts.node.multipass.beat_pacing import BEAT_PACING_SYSTEM
    from generator.prompts.node.multipass.pass2_prose import build_end_prose_user_prompt

    assert "一律写\"你\"" in PASS2_PROSE_SYSTEM or "一律写“你”" in PASS2_PROSE_SYSTEM
    assert "不替玩家总结选择结构" in PASS2_PROSE_SYSTEM
    assert "不得新增任何人物" in BEAT_PACING_SYSTEM
    end_u = build_end_prose_user_prompt(
        scene_contract={}, node_function="F", path_summary="P", scene_anchor_facts="ANCHOR_MARK"
    )
    assert "ANCHOR_MARK" in end_u and "不得新增人物" in end_u


class _CapturingProvider(MockProvider):
    """记录每类调用 user prompt 的 MockProvider（入口上下文注入断言用）。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_prompts: dict[str, list[str]] = {}

    def generate_structured(self, *, system_prompt, user_prompt, json_schema):  # type: ignore[override]
        resp = super().generate_structured(
            system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema
        )
        self.user_prompts.setdefault(self.calls[-1], []).append(user_prompt)
        return resp


def test_entry_context_injected_at_junctions(isolated_budget) -> None:
    """收敛路由根因①⑥ + junction 承接（DESIGN_2026-06-11）：
    - 收敛入口（soft_line ← 选项 0/2）：链首拍带"对所有入口都成立"+ 两句选项台词；
    - 单入口（press_line ← 选项 1）：链首拍带"先承接这句话"+ 玩家原句；
    - end 节点：带链尾玩家末句（「我记下了。」）；
    - 入口节点（opening）：不带入口上下文。
    """
    provider = _CapturingProvider()
    run_multipass_scene(provider, _SPEC, _CONFIG)

    beats_prompts = provider.user_prompts["beats"]
    # MockProvider 骨架路由轮转：选项 0/2 → soft_line（收敛 2 入口），选项 1 → press_line（单入口）
    conv = [u for u in beats_prompts if "对所有入口都成立" in u]
    assert conv, "soft_line 链首拍应带收敛入口清单"
    assert "我想找个人，打听点事。" in conv[0] and "我直说了：莱特的事。" in conv[0]
    assert "低压软问" in conv[0]  # 该入边 stance 作为共同姿态注入
    single = [u for u in beats_prompts if "先承接这句话" in u and "[观察] 先看看角落那个人。" in u]
    assert single, "press_line 链首拍应带单入口玩家原句"
    # 链首注入只发生在第 1 chunk（第 2 chunk 走既有跨 chunk 传话，不重复注入入口）
    assert all("入口上下文" not in u for u in beats_prompts if "本链第 2/2 段" in u)

    # end 节点承接链尾玩家末句
    for u in provider.user_prompts["end"]:
        assert "玩家刚说/刚做：「我记下了。」" in u

    # 入口 choice（opening）骨架/正文均不带入口上下文
    assert all("入口上下文" not in u for u in provider.user_prompts["skeleton"])
    assert all("入口上下文" not in u for u in provider.user_prompts["prose"])


def test_metrics_route_convergence_and_cross_branch_similarity(isolated_budget) -> None:
    """D-2 可观测项：出边收敛度 + 平行分支对白行相似度（mock 两链对白相同 → 1.0）。"""
    result = run_multipass_scene(MockProvider(), _SPEC, _CONFIG)
    m = result.metrics
    assert m["route_convergence"] == {"opening": {"soft_line": 2, "press_line": 1}}
    sim = m["cross_branch_line_similarity"]
    assert sim["max_ratio"] == 1.0  # mock 给两条平行链同一套对白 → 信号被抓到
    assert sim["max_pair"] == "press_line↔soft_line"
    assert sim["high_similarity_lines"]


def test_render_smoke(isolated_budget) -> None:
    result = run_multipass_scene(MockProvider(), _SPEC, _CONFIG)
    md = render_scene_md(result)
    assert "opening" in md and "soft_line" in md and "end_good" in md
    assert "场景契约" in md
    assert "$" in md  # 成本行


def test_result_is_dataclass_with_metrics(isolated_budget) -> None:
    result = run_multipass_scene(MockProvider(), _SPEC, _CONFIG)
    assert isinstance(result, MultipassSceneResult)
    m = result.metrics
    assert m["total_calls"] == len(result.call_metas) == 9
    assert m["node_count"] == len(result.graph["nodes"])
    assert m["hard_pass"] is True
    assert m["topology_fallback"] is False
