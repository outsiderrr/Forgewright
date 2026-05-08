"""T-3.7 测试套：dep_propagate 反向 propagate（ADR-023）。

测试矩阵（T-3.7 prompt §测试 mandate + 工具层稳健性兜底）：

# DP-1 核心反向查询
- 3 mock scene + sidecar fixture（character_id hit / state_path hit / 不命中）
- ontology id 命中（精确集合相交）
- state path 命中（精确 + 双向 prefix 子树匹配）
- visual asset id 命中
- clock id 命中
- 多类型混合命中（reasons 累加）
- 空输入 / 不存在的 content_root → 空列表
- 畸形 sidecar 不阻断后续 sidecar 扫描

# DP-3 / DP-4 渲染
- markdown report 含场景 id / sidecar 路径 / reason 类型 + value
- markdown 优先级分组（core > minor > context_only）
- JSON 输出 schema_version 锁 0.1.0；stale_scenes 数组形状稳定（review_ui 兼容）
- summary.total_stale + by_priority 正确

# CLI subprocess
- 端到端 `python -m tools.dep_propagate` 可调用；--json + --report 双写文件落盘
- --exit-code 在命中时返回 1（CI 友好）；不命中返回 0

# DP-2 git diff helper
- 真 git repo 上跑（在 tmp_path 内构造）；entity 字段变更 → 命中 changed_ontology_ids
- state_path_slug 变更 → 命中 changed_state_paths
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

from tools.dep_propagate import (
    REPORT_SCHEMA_VERSION,
    REASON_KIND_CLOCK,
    REASON_KIND_ONTOLOGY_ID,
    REASON_KIND_STATE_PATH,
    REASON_KIND_VISUAL_ASSET,
    ChangedOntology,
    StaleScene,
    diff_ontology,
    find_stale_scenes,
    main as cli_main,
    render_json_report,
    render_markdown_report,
)


# ---------------------------------------------------------------------------
# 共用 fixture 构造器
# ---------------------------------------------------------------------------

VALID_SHA256 = "sha256:" + "a" * 64
VALID_SHA256_2 = "sha256:" + "b" * 64


def _write_sidecar(scene_dir: Path, payload: dict) -> Path:
    """写出 sidecar；scene.json 也写一份占位（dep_propagate 当前实现未读它，但
    保持目录结构与生产一致便于以后扩展）。"""
    scene_dir.mkdir(parents=True, exist_ok=True)
    deps_path = scene_dir / "scene.deps.json"
    scene_path = scene_dir / "scene.json"
    deps_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    scene_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.1",
                "graph_id": payload["scene_id"],
                "entry_node_id": "n1",
                "scene_anchor": "scene_dummy",
                "character_refs": payload.get("ontology_ids_read", []),
                "nodes": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return deps_path


def _make_sidecar(
    scene_id: str,
    ontology_ids: Optional[list[str]] = None,
    state_paths_read: Optional[list[str]] = None,
    state_paths_written: Optional[list[str]] = None,
    visual_assets: Optional[list[str]] = None,
    clocks: Optional[list[str]] = None,
) -> dict:
    payload = {
        "schema_version": "0.3.0",
        "scene_id": scene_id,
        "generated_at": "2026-05-08T12:00:00Z",
        "ontology_ids_read": list(ontology_ids or []),
        "state_paths_read": list(state_paths_read or []),
        "state_paths_written": list(state_paths_written or []),
        "prompt_template_hash": VALID_SHA256,
    }
    if visual_assets:
        payload["visual_asset_ids_referenced"] = list(visual_assets)
    if clocks:
        payload["clock_ids_referenced"] = list(clocks)
    return payload


def _write_ontology(ontology_root: Path, entities: list[dict]) -> None:
    ontology_root.mkdir(parents=True, exist_ok=True)
    (ontology_root / "world.json").write_text(
        json.dumps({"entities": entities}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@pytest.fixture()
def three_scene_fixture(tmp_path: Path) -> dict:
    """T-3.7 prompt §测试 mandate：3 mock scenes。

    - scene_a: 引用 char_vellin + state_path `world.scene_count` → character_id hit
    - scene_b: 引用 state_path `flag.player_knows_letter` → state_path hit
    - scene_c: 引用 char_aelwin + visual_asset `img_aelwin_01` → 不命中本测试默认 input
    """
    content_root = tmp_path / "content"
    ontology_root = tmp_path / "state_ontology"

    _write_sidecar(
        content_root / "chapter_a" / "scene_a",
        _make_sidecar(
            scene_id="scene_a",
            ontology_ids=["char_vellin", "scene_waystation_of_iron_oath"],
            state_paths_read=["world.scene_count", "relationship.vellin.trust"],
            state_paths_written=["relationship.vellin.trust"],
        ),
    )
    _write_sidecar(
        content_root / "chapter_a" / "scene_b",
        _make_sidecar(
            scene_id="scene_b",
            ontology_ids=["scene_waystation_of_iron_oath"],
            state_paths_read=["flag.player_knows_letter"],
            state_paths_written=["flag.player_knows_letter"],
        ),
    )
    _write_sidecar(
        content_root / "chapter_b" / "scene_c",
        _make_sidecar(
            scene_id="scene_c",
            ontology_ids=["char_aelwin"],
            state_paths_read=["relationship.aelwin.trust"],
            state_paths_written=["relationship.aelwin.trust"],
            visual_assets=["img_aelwin_01"],
            clocks=["clk_pursuit"],
        ),
    )

    _write_ontology(
        ontology_root,
        [
            {
                "id": "char_vellin",
                "type": "character",
                "display_name": "Vellin",
                "state_path_slug": "vellin",
                "relations": [
                    {"target_character_ref": "char_corvan", "relation_type": "x", "narrative_weight": "core"},
                    {"target_character_ref": "char_aelwin", "relation_type": "y", "narrative_weight": "minor"},
                ],
            },
            {
                "id": "char_aelwin",
                "type": "character",
                "display_name": "Aelwin",
                "state_path_slug": "aelwin",
                "relations": [
                    {"target_character_ref": "char_vellin", "relation_type": "z", "narrative_weight": "minor"},
                ],
            },
            {
                "id": "scene_waystation_of_iron_oath",
                "type": "location",
                "display_name": "Waystation",
            },
        ],
    )

    return {
        "content_root": content_root,
        "ontology_root": ontology_root,
        "scene_a": content_root / "chapter_a" / "scene_a" / "scene.deps.json",
        "scene_b": content_root / "chapter_a" / "scene_b" / "scene.deps.json",
        "scene_c": content_root / "chapter_b" / "scene_c" / "scene.deps.json",
    }


# ---------------------------------------------------------------------------
# DP-1：核心反向查询
# ---------------------------------------------------------------------------

class TestFindStaleScenesCore:

    def test_changed_character_id_hits_only_referencing_scene(self, three_scene_fixture: dict) -> None:
        """T-3.7 mandate case 1：改 character_id（char_vellin）→ 命中 scene_a，不
        命中 scene_b / scene_c。"""
        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_a"]
        assert any(r.kind == REASON_KIND_ONTOLOGY_ID and r.value == "char_vellin" for r in stale[0].reasons)

    def test_changed_state_path_hits_referencing_scene(self, three_scene_fixture: dict) -> None:
        """T-3.7 mandate case 2：改 state_path（flag.player_knows_letter）→ 命中
        scene_b（在 read + write 都有），其余两个不命中。"""
        stale = find_stale_scenes(
            changed_state_paths=["flag.player_knows_letter"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_b"]
        assert any(r.kind == REASON_KIND_STATE_PATH and r.value == "flag.player_knows_letter" for r in stale[0].reasons)

    def test_no_match_returns_empty(self, three_scene_fixture: dict) -> None:
        """T-3.7 mandate case 3：改 character_id（char_inexistent）→ 0 命中。"""
        stale = find_stale_scenes(
            changed_ontology_ids=["char_inexistent"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert stale == []

    def test_state_path_subtree_match_hits_via_parent(self, three_scene_fixture: dict) -> None:
        """state path 双向 prefix 匹配：作者改了 `relationship.vellin`（父级），
        sidecar 引用 `relationship.vellin.trust`（子级）→ 命中（conservative
        over-approx）。"""
        stale = find_stale_scenes(
            changed_state_paths=["relationship.vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_a"]
        assert any(r.kind == REASON_KIND_STATE_PATH and r.value == "relationship.vellin.trust" for r in stale[0].reasons)

    def test_changed_state_path_with_wildcard_suffix_hits_subtree(
        self, three_scene_fixture: dict
    ) -> None:
        """C-phase regression（B-review §3.1 🔴）：CLI help 和 module docstring 暗示
        `faction.iron_oath.*` 是常见输入；归一化到字面 `faction.iron_oath` 之后
        通过双向 prefix 匹配命中 sidecar `relationship.vellin.trust`。

        本测试用 `relationship.vellin.*` 形态——验证修复后的 normalize 与既有
        `test_state_path_subtree_match_hits_via_parent`（去尾形态）行为等价。"""
        stale = find_stale_scenes(
            changed_state_paths=["relationship.vellin.*"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_a"]
        assert any(
            r.kind == REASON_KIND_STATE_PATH and r.value == "relationship.vellin.trust"
            for r in stale[0].reasons
        )

    def test_sidecar_with_invalid_field_type_skipped_does_not_block_others(
        self, three_scene_fixture: dict, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C-phase regression（B-review §4.2 🟡）：sidecar 字段类型错（如
        `ontology_ids_read` 是 null / object）不应抛 TypeError 中断扫描——
        guard 应 skip + warn，仍能扫到后续正常 sidecar 的命中。"""
        bad_path = (
            three_scene_fixture["content_root"]
            / "chapter_x"
            / "scene_typebad"
            / "scene.deps.json"
        )
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_payload = _make_sidecar(
            scene_id="scene_typebad",
            ontology_ids=["char_vellin"],
        )
        # 故意把 array 字段写成 null（schema 拒收，但生产期 generator bug 可能写出来）
        bad_payload["ontology_ids_read"] = None
        bad_path.write_text(json.dumps(bad_payload, ensure_ascii=False), encoding="utf-8")

        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        # 正常 sidecar（scene_a）仍能命中；坏 sidecar 被 skip
        assert [s.scene_id for s in stale] == ["scene_a"]
        captured = capsys.readouterr()
        assert "expected list" in captured.err
        assert "skipping sidecar" in captured.err

    def test_sidecar_with_non_string_array_item_skipped(
        self, three_scene_fixture: dict, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C-phase regression（B-review §4.2 🟡）：array 字段元素非 str（如混入 int）
        也走 skip + warn 路径——避免下游 `set(...)` 比较出意外。"""
        bad_path = (
            three_scene_fixture["content_root"]
            / "chapter_x"
            / "scene_itembad"
            / "scene.deps.json"
        )
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_payload = _make_sidecar(
            scene_id="scene_itembad",
            ontology_ids=["char_vellin"],
        )
        bad_payload["state_paths_read"] = ["world.scene_count", 42]  # type: ignore[list-item]
        bad_path.write_text(json.dumps(bad_payload, ensure_ascii=False), encoding="utf-8")

        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_a"]
        captured = capsys.readouterr()
        assert "non-string item" in captured.err

    def test_visual_asset_hit(self, three_scene_fixture: dict) -> None:
        stale = find_stale_scenes(
            changed_visual_assets=["img_aelwin_01"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_c"]
        assert any(r.kind == REASON_KIND_VISUAL_ASSET and r.value == "img_aelwin_01" for r in stale[0].reasons)

    def test_clock_hit(self, three_scene_fixture: dict) -> None:
        stale = find_stale_scenes(
            changed_clocks=["clk_pursuit"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_c"]
        assert any(r.kind == REASON_KIND_CLOCK and r.value == "clk_pursuit" for r in stale[0].reasons)

    def test_mixed_change_kinds_accumulate_reasons(self, three_scene_fixture: dict) -> None:
        """同一 scene 多个 reason 类型并存时，reasons 列表全部记录。"""
        stale = find_stale_scenes(
            changed_ontology_ids=["char_aelwin"],
            changed_visual_assets=["img_aelwin_01"],
            changed_clocks=["clk_pursuit"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_c"]
        kinds = {r.kind for r in stale[0].reasons}
        assert kinds == {REASON_KIND_ONTOLOGY_ID, REASON_KIND_VISUAL_ASSET, REASON_KIND_CLOCK}

    def test_empty_inputs_return_empty(self, three_scene_fixture: dict) -> None:
        """所有输入都空 → 空列表（"没有变更"语义）。"""
        stale = find_stale_scenes(
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert stale == []

    def test_missing_content_root_returns_empty(self, tmp_path: Path) -> None:
        """content_root 不存在 → 空列表（不抛错；CI / freshly-cloned repo 友好）。"""
        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=tmp_path / "does_not_exist",
            ontology_root=tmp_path / "also_missing",
        )
        assert stale == []

    def test_malformed_sidecar_does_not_block_others(
        self,
        three_scene_fixture: dict,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """畸形 JSON sidecar 跳过（stderr WARN），其余 sidecar 仍正常扫描。"""
        bad_path = three_scene_fixture["content_root"] / "chapter_x" / "scene_bad" / "scene.deps.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{not valid json,,,}", encoding="utf-8")

        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert [s.scene_id for s in stale] == ["scene_a"]
        captured = capsys.readouterr()
        assert "WARN failed to read sidecar" in captured.err

    def test_priority_sort_core_before_minor_before_context_only(self, tmp_path: Path) -> None:
        """priority 排序硬约：core > minor > context_only。

        构造三个场景分别命中 core / minor / context_only 等级 ontology 实体，
        验证返回顺序。"""
        content_root = tmp_path / "content"
        ontology_root = tmp_path / "ontology"

        _write_sidecar(
            content_root / "scene_low",
            _make_sidecar(scene_id="scene_low", ontology_ids=["char_no_relations"]),
        )
        _write_sidecar(
            content_root / "scene_mid",
            _make_sidecar(scene_id="scene_mid", ontology_ids=["char_minor_only"]),
        )
        _write_sidecar(
            content_root / "scene_high",
            _make_sidecar(scene_id="scene_high", ontology_ids=["char_core_one"]),
        )
        _write_ontology(
            ontology_root,
            [
                {"id": "char_no_relations", "type": "character", "display_name": "X", "relations": []},
                {
                    "id": "char_minor_only",
                    "type": "character",
                    "display_name": "Y",
                    "relations": [{"target_character_ref": "char_x", "relation_type": "r", "narrative_weight": "minor"}],
                },
                {
                    "id": "char_core_one",
                    "type": "character",
                    "display_name": "Z",
                    "relations": [
                        {"target_character_ref": "char_x", "relation_type": "r", "narrative_weight": "core"},
                        {"target_character_ref": "char_y", "relation_type": "r", "narrative_weight": "minor"},
                    ],
                },
            ],
        )
        stale = find_stale_scenes(
            changed_ontology_ids=["char_no_relations", "char_minor_only", "char_core_one"],
            content_root=content_root,
            ontology_root=ontology_root,
        )
        assert [s.scene_id for s in stale] == ["scene_high", "scene_mid", "scene_low"]
        assert [s.priority for s in stale] == ["core", "minor", "context_only"]

    def test_state_path_only_hit_falls_back_to_context_only(self, three_scene_fixture: dict) -> None:
        """state path 命中时，没有 ontology entity 可查 narrative_weight → 兜底
        context_only。"""
        stale = find_stale_scenes(
            changed_state_paths=["flag.player_knows_letter"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        assert stale[0].priority == "context_only"


# ---------------------------------------------------------------------------
# DP-3 / DP-4：渲染层
# ---------------------------------------------------------------------------

class TestReportRendering:

    def test_markdown_contains_scene_ids_and_reasons(self, three_scene_fixture: dict) -> None:
        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            changed_state_paths=["flag.player_knows_letter"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        md = render_markdown_report(
            stale,
            inputs={
                "since_commit": None,
                "changed_ontology_ids": ["char_vellin"],
                "changed_state_paths": ["flag.player_knows_letter"],
                "changed_visual_assets": [],
                "changed_clocks": [],
            },
            content_root=three_scene_fixture["content_root"],
        )
        assert "# Stale Scenes Report" in md
        assert "## Summary" in md
        assert "scene_a" in md
        assert "scene_b" in md
        assert "char_vellin" in md
        assert "flag.player_knows_letter" in md
        assert "ontology_id" in md
        assert "state_path" in md

    def test_markdown_groups_by_priority(self, tmp_path: Path) -> None:
        """priority 分组渲染（core 段在 minor 段之前）。"""
        content_root = tmp_path / "content"
        ontology_root = tmp_path / "ontology"
        _write_sidecar(
            content_root / "scene_high",
            _make_sidecar(scene_id="scene_high", ontology_ids=["char_core"]),
        )
        _write_sidecar(
            content_root / "scene_low",
            _make_sidecar(scene_id="scene_low", ontology_ids=["char_minor"]),
        )
        _write_ontology(
            ontology_root,
            [
                {
                    "id": "char_core",
                    "type": "character",
                    "display_name": "C",
                    "relations": [{"target_character_ref": "x", "relation_type": "r", "narrative_weight": "core"}],
                },
                {
                    "id": "char_minor",
                    "type": "character",
                    "display_name": "M",
                    "relations": [{"target_character_ref": "x", "relation_type": "r", "narrative_weight": "minor"}],
                },
            ],
        )
        stale = find_stale_scenes(
            changed_ontology_ids=["char_core", "char_minor"],
            content_root=content_root,
            ontology_root=ontology_root,
        )
        md = render_markdown_report(
            stale,
            inputs={"changed_ontology_ids": ["char_core", "char_minor"]},
            content_root=content_root,
        )
        assert md.index("Priority: core") < md.index("Priority: minor")
        assert md.index("scene_high") < md.index("scene_low")

    def test_markdown_no_stale_scenes_section_when_empty(self, tmp_path: Path) -> None:
        md = render_markdown_report(
            stale=[],
            inputs={"changed_ontology_ids": ["char_vellin"]},
            content_root=tmp_path,
        )
        assert "No stale scenes detected" in md
        assert "Stale scenes: **0**" in md

    def test_json_report_contract(self, three_scene_fixture: dict) -> None:
        """T-3.7 prompt §DP-4：JSON 输出与 review_ui 接口的形态承诺。"""
        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        payload = render_json_report(
            stale,
            inputs={
                "since_commit": None,
                "changed_ontology_ids": ["char_vellin"],
                "changed_state_paths": [],
                "changed_visual_assets": [],
                "changed_clocks": [],
            },
            content_root=three_scene_fixture["content_root"],
        )
        assert payload["schema_version"] == REPORT_SCHEMA_VERSION
        assert payload["tool"] == "tools.dep_propagate"
        assert payload["summary"]["total_stale"] == 1
        assert payload["summary"]["by_priority"]["core"] == 1
        assert payload["summary"]["by_priority"]["minor"] == 0
        assert payload["summary"]["by_priority"]["context_only"] == 0
        assert payload["inputs"]["changed_ontology_ids"] == ["char_vellin"]
        assert len(payload["stale_scenes"]) == 1
        scene = payload["stale_scenes"][0]
        assert scene["scene_id"] == "scene_a"
        assert scene["priority"] == "core"
        assert scene["scene_path"].endswith("scene.json")
        assert scene["deps_path"].endswith("scene.deps.json")
        assert {r["kind"] for r in scene["reasons"]} == {REASON_KIND_ONTOLOGY_ID}

    def test_json_serializable_round_trip(self, three_scene_fixture: dict) -> None:
        stale = find_stale_scenes(
            changed_ontology_ids=["char_vellin"],
            content_root=three_scene_fixture["content_root"],
            ontology_root=three_scene_fixture["ontology_root"],
        )
        payload = render_json_report(
            stale,
            inputs={"changed_ontology_ids": ["char_vellin"]},
            content_root=three_scene_fixture["content_root"],
        )
        text = json.dumps(payload, ensure_ascii=False)
        assert json.loads(text) == payload


# ---------------------------------------------------------------------------
# CLI subprocess
# ---------------------------------------------------------------------------

class TestCli:

    def test_cli_writes_markdown_and_json(self, three_scene_fixture: dict, tmp_path: Path) -> None:
        """端到端 in-process CLI：--report + --json 同时写盘，文件内容一致。"""
        report_path = tmp_path / "stale_report.md"
        json_path = tmp_path / "stale_report.json"
        rc = cli_main(
            [
                "--changed-ontology",
                "char_vellin",
                "--content-root",
                str(three_scene_fixture["content_root"]),
                "--ontology-root",
                str(three_scene_fixture["ontology_root"]),
                "--report",
                str(report_path),
                "--json",
                str(json_path),
            ]
        )
        assert rc == 0
        assert report_path.exists()
        assert json_path.exists()
        md = report_path.read_text(encoding="utf-8")
        assert "scene_a" in md
        assert "char_vellin" in md
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["summary"]["total_stale"] == 1
        assert payload["stale_scenes"][0]["scene_id"] == "scene_a"

    def test_cli_exit_code_flag_returns_one_when_stale(
        self,
        three_scene_fixture: dict,
        tmp_path: Path,
    ) -> None:
        report_path = tmp_path / "x.md"
        rc = cli_main(
            [
                "--changed-ontology",
                "char_vellin",
                "--content-root",
                str(three_scene_fixture["content_root"]),
                "--ontology-root",
                str(three_scene_fixture["ontology_root"]),
                "--report",
                str(report_path),
                "--exit-code",
            ]
        )
        assert rc == 1

    def test_cli_exit_code_flag_returns_zero_when_clean(
        self,
        three_scene_fixture: dict,
        tmp_path: Path,
    ) -> None:
        report_path = tmp_path / "y.md"
        rc = cli_main(
            [
                "--changed-ontology",
                "char_does_not_exist",
                "--content-root",
                str(three_scene_fixture["content_root"]),
                "--ontology-root",
                str(three_scene_fixture["ontology_root"]),
                "--report",
                str(report_path),
                "--exit-code",
            ]
        )
        assert rc == 0
        assert "No stale scenes detected" in report_path.read_text(encoding="utf-8")

    def test_cli_module_invocable_via_python_m(self, three_scene_fixture: dict, tmp_path: Path) -> None:
        """`python -m tools.dep_propagate` 真子进程跑通——验证 entry-point + 包注册。"""
        repo_root = Path(__file__).resolve().parents[2]
        report_path = tmp_path / "subproc.md"
        json_path = tmp_path / "subproc.json"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.dep_propagate",
                "--changed-ontology",
                "char_vellin",
                "--content-root",
                str(three_scene_fixture["content_root"]),
                "--ontology-root",
                str(three_scene_fixture["ontology_root"]),
                "--report",
                str(report_path),
                "--json",
                str(json_path),
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert report_path.exists()
        assert json_path.exists()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["stale_scenes"][0]["scene_id"] == "scene_a"


# ---------------------------------------------------------------------------
# DP-2：ontology git diff helper
# ---------------------------------------------------------------------------

def _git_init_repo(repo: Path) -> None:
    """初始化 tmp repo 并配置 user，避免 commit 报错。"""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)


def _git_commit_all(repo: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)
    rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return rev


class TestDiffOntology:

    def test_entity_field_change_marks_id(self, tmp_path: Path) -> None:
        """entity 任意字段变 → id 出现在 changed_ontology_ids（粗粒度；T-3.7 §DP-2 §6）。"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(
            ontology,
            [
                {"id": "char_vellin", "type": "character", "display_name": "Vellin", "state_path_slug": "vellin"},
                {"id": "char_aelwin", "type": "character", "display_name": "Aelwin", "state_path_slug": "aelwin"},
            ],
        )
        rev = _git_commit_all(repo, "init")

        _write_ontology(
            ontology,
            [
                {"id": "char_vellin", "type": "character", "display_name": "Vellin (updated)", "state_path_slug": "vellin"},
                {"id": "char_aelwin", "type": "character", "display_name": "Aelwin", "state_path_slug": "aelwin"},
            ],
        )

        diff = diff_ontology(ontology, since_commit=rev, repo_root=repo)
        assert isinstance(diff, ChangedOntology)
        assert "char_vellin" in diff.changed_ontology_ids
        assert "char_aelwin" not in diff.changed_ontology_ids

    def test_state_path_slug_change_emits_relationship_paths(self, tmp_path: Path) -> None:
        """state_path_slug 漂移 → 两侧 slug 全部回填 relationship.<slug>。"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V", "state_path_slug": "vellin"}],
        )
        rev = _git_commit_all(repo, "init")

        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V", "state_path_slug": "vellin_v2"}],
        )

        diff = diff_ontology(ontology, since_commit=rev, repo_root=repo)
        assert "char_vellin" in diff.changed_ontology_ids
        assert "relationship.vellin" in diff.changed_state_paths
        assert "relationship.vellin_v2" in diff.changed_state_paths

    def test_deleted_ontology_file_marks_old_entities_as_changed(
        self, tmp_path: Path
    ) -> None:
        """C-phase regression（B-review §4.1 🟡）：删除整个 ontology JSON 文件后
        `diff_ontology` 必须把旧 entity 标 changed——pre-commit hook
        `--since HEAD` 路径在作者删除/重命名 ontology 文件时不能假阴性。"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(
            ontology,
            [
                {
                    "id": "char_vellin",
                    "type": "character",
                    "display_name": "V",
                    "state_path_slug": "vellin",
                },
                {"id": "char_aelwin", "type": "character", "display_name": "A"},
            ],
        )
        rev = _git_commit_all(repo, "init")

        # 删除整个 world.json
        (ontology / "world.json").unlink()

        diff = diff_ontology(ontology, since_commit=rev, repo_root=repo)
        assert "char_vellin" in diff.changed_ontology_ids
        assert "char_aelwin" in diff.changed_ontology_ids
        assert "relationship.vellin" in diff.changed_state_paths

    def test_renamed_ontology_file_picks_up_old_path(self, tmp_path: Path) -> None:
        """C-phase regression（B-review §4.1 🟡）：重命名场景 = 旧 path 删除 + 新 path
        新增；diff_ontology 应同时看到两侧。本 case 验证旧 path 下的 entity id
        全部进入 changed_ontology_ids。"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V"}],
        )
        rev = _git_commit_all(repo, "init")

        # 重命名 world.json → world_v2.json（新 path 内容相同）
        (ontology / "world.json").rename(ontology / "world_v2.json")

        diff = diff_ontology(ontology, since_commit=rev, repo_root=repo)
        # entity id 出现于旧 path（删除）+ 新 path（新增）union
        assert "char_vellin" in diff.changed_ontology_ids

    def test_no_change_returns_empty(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V"}],
        )
        rev = _git_commit_all(repo, "init")

        diff = diff_ontology(ontology, since_commit=rev, repo_root=repo)
        assert diff.changed_ontology_ids == []
        assert diff.changed_state_paths == []

    def test_bad_revision_raises_runtime_error(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        _write_ontology(ontology, [{"id": "char_x", "type": "character", "display_name": "X"}])
        _git_commit_all(repo, "init")
        with pytest.raises(RuntimeError):
            diff_ontology(ontology, since_commit="not-a-real-revision", repo_root=repo)

    def test_cli_since_flag_invokes_diff_ontology(self, tmp_path: Path) -> None:
        """CLI `--since` 联通 diff_ontology + find_stale_scenes 的端到端通路。"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init_repo(repo)
        ontology = repo / "state" / "ontology"
        content_root = repo / "content"
        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V", "state_path_slug": "vellin"}],
        )
        _write_sidecar(
            content_root / "scene_a",
            _make_sidecar(scene_id="scene_a", ontology_ids=["char_vellin"]),
        )
        rev = _git_commit_all(repo, "init")

        _write_ontology(
            ontology,
            [{"id": "char_vellin", "type": "character", "display_name": "V2", "state_path_slug": "vellin"}],
        )

        report_path = tmp_path / "out.md"
        json_path = tmp_path / "out.json"
        rc = cli_main(
            [
                "--since",
                rev,
                "--content-root",
                str(content_root),
                "--ontology-root",
                str(ontology),
                "--report",
                str(report_path),
                "--json",
                str(json_path),
            ]
        )
        assert rc == 0
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["summary"]["total_stale"] == 1
        assert payload["stale_scenes"][0]["scene_id"] == "scene_a"
        assert "char_vellin" in payload["inputs"]["changed_ontology_ids"]


# ---------------------------------------------------------------------------
# StaleScene dataclass
# ---------------------------------------------------------------------------

class TestStaleSceneDataclass:

    def test_to_dict_uses_relative_paths(self, tmp_path: Path) -> None:
        scene = StaleScene(
            scene_id="x",
            scene_path=tmp_path / "content" / "x" / "scene.json",
            deps_path=tmp_path / "content" / "x" / "scene.deps.json",
            reasons=[],
        )
        out = scene.to_dict(content_root=tmp_path / "content")
        assert out["scene_path"] == "x/scene.json"
        assert out["deps_path"] == "x/scene.deps.json"
        assert out["scene_id"] == "x"
