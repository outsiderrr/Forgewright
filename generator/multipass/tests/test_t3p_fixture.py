"""T-3P 共用 fixture golden 测试（T-3P-0 内容 E）.

augmented lucy design.json = legacy design（2026-06-11_convfix 真实产物）
+ beats_plan（确定性拆拍器产出）+ run_config（手工抄 specs/lucy.json config 段）。
T-3P-1/2/3 的 golden 测试全部引用这一份，保证字节级一致——本测试钉死：
  - fixture 经 load_design_artifact 可读（wrapper 形态合规）；
  - beats_plan 与拆拍器对 fixture 自身 topology 的输出完全一致（可再生）；
  - run_config 与 specs/lucy.json 的 config 段逐字段一致（同源同形）；
  - legacy design 内容原样保留（未被合成过程改动）。
"""
from __future__ import annotations

import json
from pathlib import Path

from generator.multipass.beat_split import build_beats_plan
from generator.promptpack.io import load_design_artifact

_EXP = Path(__file__).resolve().parents[2] / "experiments" / "multipass_structure"
FIXTURE = _EXP / "2026-06-29_t3p_fixture" / "lucy" / "design.json"
LEGACY = _EXP / "2026-06-11_convfix" / "lucy" / "design.json"
SPEC = _EXP / "specs" / "lucy.json"


def test_fixture_loadable_via_shared_loader() -> None:
    design = load_design_artifact(FIXTURE)
    assert "beats_plan" in design and "run_config" in design


def test_fixture_beats_plan_reproducible_from_own_topology() -> None:
    design = load_design_artifact(FIXTURE)
    assert design["beats_plan"] == build_beats_plan(design["topology"])
    # lucy 有 5 条 beats 链（dict 按链分组的实证依据）
    assert len(design["beats_plan"]) == 5


def test_fixture_run_config_matches_spec_config() -> None:
    design = load_design_artifact(FIXTURE)
    spec_config = json.loads(SPEC.read_text(encoding="utf-8"))["config"]
    assert design["run_config"] == spec_config


def test_fixture_preserves_legacy_design_content() -> None:
    design = load_design_artifact(FIXTURE)
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))["design"]
    for key in legacy:  # contract / topology / skeletons / proses / beats / ends ...
        assert design[key] == legacy[key], f"legacy design[{key!r}] 被合成过程改动"
    # 超集只准超出恰好两 key（README 契约的反向钉死：不许夹带第三个新 key）
    assert set(design) == set(legacy) | {"beats_plan", "run_config"}
