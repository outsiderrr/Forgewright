"""`run_multipass_scene.py --structure-only` CLI wiring 测试（T-3P-0，critique F-2）.

真 LLM smoke 由 A 阶段报告记录命令；本测试用 MockProvider 验证 flag 接线：
一条命令只落 design.json + metrics.json（含 beats_plan/run_config 两 key），
不落 scene.json / scene.md。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from generator.multipass.tests.test_engine import MockProvider, _SPEC

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_multipass_scene.py"


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("run_multipass_scene_cli", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_topology_only_and_structure_only_mutually_exclusive(tmp_path) -> None:
    """两个局部模式组合时 argparse 直接拒收（不再静默忽略 --structure-only）。"""
    mod = _load_cli_module()
    with pytest.raises(SystemExit) as ei:
        mod.main(["--spec", str(tmp_path / "x.json"), "--topology-only", "--structure-only"])
    assert ei.value.code == 2  # argparse 用法错误退出码


def test_structure_only_flag_writes_design_and_metrics_only(
    isolated_budget, tmp_path, monkeypatch, capsys
) -> None:
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        json.dumps(
            {
                "config": {
                    "graph_id": "cli_smoke",
                    "scene_anchor": "scene_hibo_roadhouse",
                    "speaker_ref": "char_lucy",
                    "character_refs": ["char_lucy"],
                    "npc_name": "露西",
                },
                "spec": _SPEC,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_root = tmp_path / "out"

    mod = _load_cli_module()
    monkeypatch.setattr(mod, "_make_provider", lambda: MockProvider())
    rc = mod.main(
        ["--spec", str(spec_file), "--structure-only", "--out-root", str(out_root)]
    )

    assert rc == 0
    assert sorted(p.name for p in out_root.iterdir()) == ["design.json", "metrics.json"]
    payload = json.loads((out_root / "design.json").read_text(encoding="utf-8"))
    assert "beats_plan" in payload["design"] and "run_config" in payload["design"]
    assert payload["design"]["run_config"]["graph_id"] == "cli_smoke"
    # 产物行标签如实：structure-only 指向的是 design.json，不冒充 scene
    out = capsys.readouterr().out
    assert "design:" in out and "scene:" not in out
