"""promptpack IO envelope 共享 loader 单测（T-3P-0，critique F-3）.

P-A（T-3P-1）/ P-B（T-3P-2）只准经这两个 loader 读输入：
  - load_design_artifact：design.json 沿 engine.write_artifacts 现有 wrapper 形态；
  - load_scene_spec：spec 文件沿 specs/lucy.json 现有 {config, spec} wrapper；
    给了 design 时 cross-check config ↔ design.run_config 一致。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.promptpack.io import (
    PromptpackInputError,
    load_design_artifact,
    load_scene_spec,
)

_RUN_CONFIG = {
    "graph_id": "lucy_roadhouse_multipass",
    "scene_anchor": "scene_hibo_roadhouse",
    "speaker_ref": "char_lucy",
    "character_refs": ["char_lucy"],
    "npc_name": "露西",
}

_DESIGN = {
    "contract": {"player_goal": "拿到线索"},
    "topology": {
        "entry_node_id": "soft_line",
        "nodes": [
            {"node_id": "soft_line", "kind": "beats", "function": "", "reveals": ["线索甲"],
             "next": "end_soft"},
            {"node_id": "end_soft", "kind": "end", "function": "", "reveals": []},
        ],
    },
    "skeletons": {},
    "beats_plan": {
        "soft_line": [{"beat_id": "soft_line_b1", "reveals": ["线索甲"], "is_last": True}]
    },
    "run_config": _RUN_CONFIG,
}


def _write_design(
    tmp_path: Path,
    design: dict,
    *,
    status: str = "success",
    failure_reason: str | None = None,
) -> Path:
    p = tmp_path / "design.json"
    p.write_text(
        json.dumps(
            {
                "design": design,
                "call_metas": [],
                "warnings": [],
                "validation": {},
                "status": status,
                "failure_reason": failure_reason,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def _write_spec(tmp_path: Path, config: dict) -> Path:
    p = tmp_path / "spec.json"
    p.write_text(
        json.dumps({"config": config, "spec": {"background": "1920 公路酒馆"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return p


def test_load_design_artifact_returns_inner_design(tmp_path) -> None:
    path = _write_design(tmp_path, _DESIGN)
    design = load_design_artifact(path)
    assert design["run_config"] == _RUN_CONFIG
    assert design["beats_plan"]["soft_line"][0]["beat_id"] == "soft_line_b1"


def test_load_design_artifact_rejects_non_wrapper(tmp_path) -> None:
    p = tmp_path / "design.json"
    p.write_text(json.dumps(_DESIGN), encoding="utf-8")  # 裸 design，无 wrapper
    with pytest.raises(PromptpackInputError, match="wrapper"):
        load_design_artifact(p)


def test_load_design_artifact_rejects_legacy_design_with_guidance(tmp_path) -> None:
    """legacy design.json（缺 beats_plan/run_config）→ 报错引导先跑 structure-only。"""
    legacy = {k: v for k, v in _DESIGN.items() if k not in ("beats_plan", "run_config")}
    path = _write_design(tmp_path, legacy)
    with pytest.raises(PromptpackInputError, match="structure-only"):
        load_design_artifact(path)


def test_load_design_artifact_triages_failed_run_before_legacy(tmp_path) -> None:
    """失败运行产物（status != success）→ 透出 failure_reason，不误诊为 legacy。"""
    legacy = {k: v for k, v in _DESIGN.items() if k not in ("beats_plan", "run_config")}
    path = _write_design(
        tmp_path, legacy, status="provider_error", failure_reason="relay 502"
    )
    with pytest.raises(PromptpackInputError, match="失败运行") as ei:
        load_design_artifact(path)
    assert "relay 502" in str(ei.value)
    assert "legacy" not in str(ei.value)


def test_load_design_artifact_rejects_flat_list_beats_plan(tmp_path) -> None:
    """beats_plan 载体形态锁死为按链分组的 dict——flat list 在边界即拒收。"""
    design = dict(_DESIGN)
    design["beats_plan"] = [{"beat_id": "soft_line_b1", "reveals": [], "is_last": True}]
    with pytest.raises(PromptpackInputError, match="dict"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_malformed_beat_slot(tmp_path) -> None:
    design = dict(_DESIGN)
    design["beats_plan"] = {"soft_line": [{"beat_id": "soft_line_b1"}]}  # 缺 2 key
    with pytest.raises(PromptpackInputError, match="BeatSlot"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_run_config_missing_field(tmp_path) -> None:
    design = dict(_DESIGN)
    design["run_config"] = {k: v for k, v in _RUN_CONFIG.items() if k != "speaker_ref"}
    with pytest.raises(PromptpackInputError, match="speaker_ref"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_wrong_leaf_types(tmp_path) -> None:
    """三 key 齐但叶类型走形（reveals 是 str / is_last 是 str）也在边界拒收。"""
    design = dict(_DESIGN)
    design["beats_plan"] = {
        "soft_line": [{"beat_id": "soft_line_b1", "reveals": "线索甲", "is_last": "no"}]
    }
    with pytest.raises(PromptpackInputError, match="叶类型"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_beats_plan_topology_mismatch(tmp_path) -> None:
    """改了 topology 没重跑拆拍（线索并集对不上）→ 边界拒收，不流进 P-A/P-B。"""
    design = json.loads(json.dumps(_DESIGN))  # 深拷贝防污染共享常量
    design["topology"]["nodes"][0]["reveals"] = ["线索甲", "新加的线索乙"]
    path = _write_design(tmp_path, design)
    with pytest.raises(PromptpackInputError, match="不一致"):
        load_design_artifact(path)


def test_load_design_artifact_rejects_empty_beats_chain(tmp_path) -> None:
    """空拍链拒收：0-reveal 链约定必须有 1 个过场拍，空链会让 {pid}_b1 入口悬空。"""
    design = json.loads(json.dumps(_DESIGN))
    design["topology"]["nodes"][0]["reveals"] = []  # 0-reveal 链
    design["beats_plan"] = {"soft_line": []}  # 走形：空链而非 1 个过场拍
    with pytest.raises(PromptpackInputError, match="空链"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_directory_path(tmp_path) -> None:
    """传目录 → PromptpackInputError（退出码 2 契约），不裸 IsADirectoryError。"""
    with pytest.raises(PromptpackInputError, match="无法读取"):
        load_design_artifact(tmp_path)


def test_load_design_artifact_rejects_non_utf8_file(tmp_path) -> None:
    """非 UTF-8 文件 → PromptpackInputError，不裸 UnicodeDecodeError。"""
    p = tmp_path / "design.json"
    p.write_bytes("{}".encode("utf-16"))  # BOM + 双字节，UTF-8 解不开
    with pytest.raises(PromptpackInputError, match="UTF-8"):
        load_design_artifact(p)


# ---------------------------------------------------------------------------
# choice 骨架出边覆盖复算（C 阶段 finding 7：残留路由缺口在 loader 边界硬拦）
# ---------------------------------------------------------------------------

def _design_with_choice(option_routes: list[str]) -> dict:
    """带 choice 节点的最小 design：opening 两条出边 soft_line / press_line。"""
    return {
        "contract": {},
        "topology": {
            "entry_node_id": "opening",
            "nodes": [
                {"node_id": "opening", "kind": "choice", "function": "", "reveals": [],
                 "routes": [{"to": "soft_line", "stance": ""},
                            {"to": "press_line", "stance": ""}]},
                {"node_id": "soft_line", "kind": "beats", "function": "",
                 "reveals": ["线索甲"], "next": "end_soft"},
                {"node_id": "press_line", "kind": "beats", "function": "",
                 "reveals": ["线索乙"], "next": "end_soft"},
                {"node_id": "end_soft", "kind": "end", "function": "", "reveals": []},
            ],
        },
        "skeletons": {
            "opening": {
                "node_id": "opening",
                "options": [{"intent": "", "route_to": rt} for rt in option_routes],
            }
        },
        "beats_plan": {
            "soft_line": [{"beat_id": "soft_line_b1", "reveals": ["线索甲"], "is_last": True}],
            "press_line": [{"beat_id": "press_line_b1", "reveals": ["线索乙"], "is_last": True}],
        },
        "run_config": dict(_RUN_CONFIG),
    }


def test_load_design_artifact_accepts_full_route_coverage(tmp_path) -> None:
    """出边全覆盖（含多选项收敛到同一出边）→ 正常放行。"""
    design = _design_with_choice(["soft_line", "press_line", "soft_line"])
    loaded = load_design_artifact(_write_design(tmp_path, design))
    assert set(loaded["beats_plan"]) == {"soft_line", "press_line"}


def test_load_design_artifact_rejects_uncovered_out_edge(tmp_path) -> None:
    """出边未被任何选项覆盖（不可达链）→ 硬拦 + 引导重跑 structure-only / 人工修。"""
    design = _design_with_choice(["soft_line", "soft_line"])  # press_line 无人路由
    with pytest.raises(PromptpackInputError, match="press_line") as ei:
        load_design_artifact(_write_design(tmp_path, design))
    assert "不可达" in str(ei.value)
    assert "structure-only" in str(ei.value)


def test_load_design_artifact_rejects_illegal_route_to(tmp_path) -> None:
    """route_to 非法（不在出边内）→ 同径硬拦（语义对照 engine._route_violations）。"""
    design = _design_with_choice(["soft_line", "press_line", "nowhere"])
    with pytest.raises(PromptpackInputError, match="nowhere"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_design_artifact_rejects_missing_choice_skeleton(tmp_path) -> None:
    """topology 有 choice 但 skeletons 缺该骨架 → 出边必然未覆盖，硬拦。"""
    design = _design_with_choice(["soft_line", "press_line"])
    design["skeletons"] = {}
    with pytest.raises(PromptpackInputError, match="没有骨架"):
        load_design_artifact(_write_design(tmp_path, design))


def test_load_scene_spec_rejects_non_dict_spec(tmp_path) -> None:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"config": dict(_RUN_CONFIG), "spec": None}), encoding="utf-8")
    with pytest.raises(PromptpackInputError, match="spec"):
        load_scene_spec(p)


def test_load_scene_spec_returns_inner_spec(tmp_path) -> None:
    path = _write_spec(tmp_path, dict(_RUN_CONFIG))
    spec = load_scene_spec(path)
    assert spec == {"background": "1920 公路酒馆"}


def test_load_scene_spec_rejects_non_wrapper(tmp_path) -> None:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"background": "裸 spec"}), encoding="utf-8")
    with pytest.raises(PromptpackInputError, match="wrapper"):
        load_scene_spec(p)


def test_load_scene_spec_cross_check_passes_on_same_source(tmp_path) -> None:
    path = _write_spec(tmp_path, dict(_RUN_CONFIG))
    design = load_design_artifact(_write_design(tmp_path, _DESIGN))
    assert load_scene_spec(path, design=design) == {"background": "1920 公路酒馆"}


def test_load_scene_spec_cross_check_defaults_npc_name(tmp_path) -> None:
    """spec config 省略 npc_name（SceneRunConfig 默认 'NPC'）→ 与 run_config 同默认值比对。"""
    cfg = {k: v for k, v in _RUN_CONFIG.items() if k != "npc_name"}
    path = _write_spec(tmp_path, cfg)
    design = dict(_DESIGN)
    design["run_config"] = {**_RUN_CONFIG, "npc_name": "NPC"}
    assert load_scene_spec(path, design=design) == {"background": "1920 公路酒馆"}


def test_load_scene_spec_cross_check_mismatch_names_fields(tmp_path) -> None:
    cfg = {**_RUN_CONFIG, "graph_id": "someone_else", "speaker_ref": "char_vick"}
    path = _write_spec(tmp_path, cfg)
    design = load_design_artifact(_write_design(tmp_path, _DESIGN))
    with pytest.raises(PromptpackInputError, match="graph_id") as ei:
        load_scene_spec(path, design=design)
    assert "speaker_ref" in str(ei.value)


def test_load_scene_spec_rejects_non_dict_config(tmp_path) -> None:
    """坏文件走冻结的 PromptpackInputError（退出码 2 契约），不漏 AttributeError。"""
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"config": ["not", "a", "dict"], "spec": {}}), encoding="utf-8")
    with pytest.raises(PromptpackInputError, match="config"):
        load_scene_spec(p, design=dict(_DESIGN))


def test_load_scene_spec_rejects_design_with_malformed_run_config(tmp_path) -> None:
    """cross-check 前先验 run_config 形态：坏 design 不落进'拿错配对'的误导报错。"""
    path = _write_spec(tmp_path, dict(_RUN_CONFIG))
    design = dict(_DESIGN)
    design["run_config"] = None
    with pytest.raises(PromptpackInputError, match="run_config"):
        load_scene_spec(path, design=design)


def test_run_config_contract_matches_scene_run_config_dataclass() -> None:
    """冻结五字段/默认值 ↔ SceneRunConfig 漂移守卫：dataclass 变动时此测试先响。

    契约字面量是有意冻结（envelope 变更须过契约评审），不做 import 级派生；
    本测试提供响亮失败，防三处手写副本静默漂移。
    """
    from dataclasses import fields

    from generator.multipass.engine import SceneRunConfig
    from generator.promptpack import io as ppio

    fs = {f.name: f for f in fields(SceneRunConfig)}
    assert tuple(fs) == ppio.RUN_CONFIG_FIELDS
    assert fs["npc_name"].default == ppio._NPC_NAME_DEFAULT


class TestRunConfigLeafTypes:
    """B 阶段 F-002：run_config 冻结五字段的叶类型/额外字段硬校验。"""

    def _design_with_run_config(self, tmp_path, run_config):
        import copy
        design = copy.deepcopy(_DESIGN)
        design["run_config"] = run_config
        return _write_design(tmp_path, design)

    def _good(self):
        return {"graph_id": "g", "scene_anchor": "loc", "speaker_ref": "char_x",
                "character_refs": ["char_x"], "npc_name": "X"}

    def test_good_run_config_passes(self, tmp_path):
        from generator.promptpack.io import load_design_artifact
        load_design_artifact(self._design_with_run_config(tmp_path, self._good()))

    def test_non_string_leaves_rejected(self, tmp_path):
        import pytest
        from generator.promptpack.io import PromptpackInputError, load_design_artifact
        for field, bad in [("graph_id", 123), ("scene_anchor", None),
                           ("speaker_ref", ["char_x"]), ("npc_name", {"name": "露西"})]:
            rc = self._good(); rc[field] = bad
            with pytest.raises(PromptpackInputError, match=field):
                load_design_artifact(self._design_with_run_config(tmp_path, rc))

    def test_character_refs_string_rejected(self, tmp_path):
        import pytest
        from generator.promptpack.io import PromptpackInputError, load_design_artifact
        rc = self._good(); rc["character_refs"] = "char_x"
        with pytest.raises(PromptpackInputError, match="character_refs"):
            load_design_artifact(self._design_with_run_config(tmp_path, rc))

    def test_extra_key_rejected(self, tmp_path):
        import pytest
        from generator.promptpack.io import PromptpackInputError, load_design_artifact
        rc = self._good(); rc["extra_future_field"] = "unexpected"
        with pytest.raises(PromptpackInputError, match="extra_future_field"):
            load_design_artifact(self._design_with_run_config(tmp_path, rc))
