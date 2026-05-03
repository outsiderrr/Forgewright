"""Scene-level few-shot for skeleton-first scene generation (T-2.5).

`load_iron_oath_scene_few_shot()` returns one demonstration pair: the
scene_setting + character cards a caller would feed for the《铁誓驿站》场景，
and the **whole** DialogueGraph JSON we want the model to mirror back.

Why a single demo to start with: scene-level generation costs an order of
magnitude more tokens per call than node-level. One canonical demo seeds
the structure (5 nodes / 2 ending / 节奏 / state path slug usage / `core`
关系编织 / dramatic_triggers prescriptive 写法）without inflating prompt
length. Add more demos only if baseline shows over-fitting to this scene.

The expected DialogueGraph is loaded from
`/content/test_scene_v0/scene.json` (gold standard), not synthesised — that
keeps prompt hash deterministic and ensures the demo is **exactly** what
validator.schema_check accepts as v0.1.1 dialogue_graph.

The few `Option.text` strings whose originals exceed the 25-字 cap added
in T-2.0 are short-circuited via `_FEW_SHOT_TEXT_OVERRIDES` (mirrors
node-level `prompts.few_shot._FEW_SHOT_TEXT_OVERRIDES`); originals stay
untouched on disk.

The character card snippets in the input context include the v0.3 ontology
fields the scene system prompt needs to teach LLM to consume:
`state_path_slug`, `character_features`, `dramatic_triggers`, and
`relations[].narrative_weight`. They are **synthesised** here (not loaded
from /state/ontology/waystation.json) to keep this module read-only with
respect to /state/ — see `/generator/CLAUDE.md` 跨模块约束.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

_SCENE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "content"
    / "test_scene_v0"
    / "scene.json"
)


# Mirrors generator.prompts.few_shot._FEW_SHOT_TEXT_OVERRIDES.
# Keep in sync with that module so node-level and scene-level demos display
# identical text — different demos saying different things for the same
# scene would teach the model nothing useful.
_FEW_SHOT_TEXT_OVERRIDES: dict[tuple[str, str], str] = {
    ("arrival_waystation", "opt_read_the_room"): "[观察入微] 我看出那是军驿函件。",
    ("vellin_confession", "opt_report_to_oath"): "我欠铁誓一份军饷。明早告诉 Corvan。",
    ("patrol_arrives", "opt_lie_for_vellin"): "Corvan，我没看见什么信。以兰岭起誓。",
    ("patrol_arrives", "opt_invoke_old_bond"): "[诉诸旧情] 看在兰岭那年的份上。",
}


# Synthesised character cards for the demo's input context. Mirror the
# fields scene/system.py instructs LLM to consume: id / state_path_slug /
# character_features / dramatic_triggers / relations[narrative_weight].
# Hand-written so /state/ontology/* stays read-only (see /generator/CLAUDE.md).
_DEMO_CHARACTER_CARDS: list[dict] = [
    {
        "id": "char_vellin",
        "display_name": "Vellin",
        "state_path_slug": "vellin",
        "description": "铁誓驿站现任老板娘；前边境兵；左眉骨上有一道新伤。",
        "character_features": [
            "stoic mercenary",
            "驿站老板娘",
            "守口如瓶但内心动摇",
            "对玩家心存旧日恩情",
        ],
        "dramatic_triggers": [
            {
                "trait": "stoic mercenary",
                "when": "被质问过去",
                "how": "沉默几秒后岔开话题",
                "priority": 1,
            },
            {
                "trait": "守口如瓶但内心动摇",
                "when": "看到旧友受到铁誓威胁",
                "how": "压低声音、加快收手中物件的动作",
                "priority": 2,
                "cooldown_scenes": 2,
            },
        ],
        "relations": [
            {
                "target_character_ref": "char_corvan",
                "relation_type": "former_brother_in_arms_now_adversary",
                "narrative_weight": "core",
            },
            {
                "target_character_ref": "char_aelwin",
                "relation_type": "complicit_protector",
                "narrative_weight": "core",
            },
        ],
    },
    {
        "id": "char_corvan",
        "display_name": "Corvan",
        "state_path_slug": "corvan",
        "description": "铁誓卫队巡逻官；与玩家有过五年前兰岭追私盐队的并肩经历。",
        "character_features": [
            "铁誓巡逻官",
            "前兰岭战友；玩家旧相识",
            "秩序至上但旧情有重量",
            "习惯性按剑柄；语带威压",
        ],
        "dramatic_triggers": [
            {
                "trait": "秩序至上但旧情有重量",
                "when": "被旧战友诉诸过往恩情",
                "how": "停顿一拍后给出冷硬但留余地的回应",
                "priority": 1,
            }
        ],
        "relations": [
            {
                "target_character_ref": "char_vellin",
                "relation_type": "former_brother_in_arms_now_adversary",
                "narrative_weight": "core",
            },
            {
                "target_character_ref": "char_aelwin",
                "relation_type": "iron_oath_target",
                "narrative_weight": "minor",
            },
        ],
    },
    {
        "id": "char_aelwin",
        "display_name": "Aelwin",
        "state_path_slug": "aelwin",
        "description": "铁誓卫队的逃兵；本场仅作 anchor，不出场。",
        "character_features": [
            "逃兵",
            "前陶窑山口少年兵；玩家旧战友",
            "藏匿于东边牧人废屋",
        ],
        "dramatic_triggers": [],
        "relations": [
            {
                "target_character_ref": "char_vellin",
                "relation_type": "trusted_smuggler",
                "narrative_weight": "context_only",
            }
        ],
    },
]


_DEMO_LOCATION_CANDIDATES: list[dict] = [
    {
        "location_id": "scene_waystation_of_iron_oath",
        "display_name": "铁誓驿站",
        "location_type": "scene",
        "parent_location_ref": None,
        "description": "铁誓路上的三层石塔驿站；塔顶旗帜褪成铜绿；现由 Vellin 经营。",
    }
]


_DEMO_TARGET_BEATS: list[str] = [
    "抵达驿站，建立张力",
    "秘密摊开，玩家二选一",
    "巡逻官登场，外部压力",
    "ending：共谋余韵",
    "ending：告发代价",
]


_DEMO_ACTIVE_CLOCKS: list[dict] = []  # 阶段 0/1.5 桩态：本体未注册时钟


_DEMO_SYSTEM_TIME: dict = {"scene_count": 0, "long_rest_count": 0}


@dataclass(frozen=True)
class SceneFewShotPair:
    """One whole-scene demonstration: scene_setting + character cards as
    prose input, plus the canonical DialogueGraph JSON output."""

    scene_setting_summary: str
    expected_graph: dict


def _scene_setting_summary() -> str:
    """Render the scene_setting + ontology snippets as a markdown fragment.

    Layout mirrors the order scene/system.py and (later) T-2.6
    `assemble_scene_context_block` will use, so a single demo trains the
    model on the exact section ordering it'll see at runtime.
    """
    parts: list[str] = []
    parts.append("## 场景锚点 (`scene_anchor`)")
    parts.append("- `scene_waystation_of_iron_oath`")
    parts.append("")
    parts.append("## 候选地点 (`location_candidates`)")
    parts.append(
        "下列是本体已定义的候选地点；任何 `location_ref` **必须**取自其中"
        " `location_id`。"
    )
    parts.append(
        f"- 主地点（推荐默认 `location_ref`）：`{_DEMO_LOCATION_CANDIDATES[0]['location_id']}`"
    )
    for cand in _DEMO_LOCATION_CANDIDATES:
        parts.append("```json")
        parts.append(json.dumps(cand, ensure_ascii=False, indent=2))
        parts.append("```")
    parts.append("")
    parts.append("## 节拍序列 (`target_beats`)")
    for idx, beat in enumerate(_DEMO_TARGET_BEATS, start=1):
        parts.append(f"{idx}. {beat}")
    parts.append("")
    parts.append("## 出场角色卡 (`participating_npcs`)")
    parts.append(
        "字段含 `id` / `state_path_slug` / `character_features` /"
        " `dramatic_triggers` / `relations[narrative_weight]`。**所有"
        " `relationship.<slug>.*` 路径里的 `<slug>` 必须取自 `state_path_slug`"
        "**（不是 `id`）。`relations[].narrative_weight=="
        "context_only` 的关系**不要**写进对白；`core` 必须显性体现，"
        "`minor` 可选体现。"
    )
    for card in _DEMO_CHARACTER_CARDS:
        parts.append("```json")
        parts.append(json.dumps(card, ensure_ascii=False, indent=2))
        parts.append("```")
    parts.append("")
    parts.append("## 阵营时钟当前值 (`active_clocks`)")
    parts.append("- （阶段 0/1.5 本体桩未注册时钟；空数组）")
    parts.append("")
    parts.append("## 系统时间 (`system_time`)")
    parts.append(f"- `world.scene_count`: {_DEMO_SYSTEM_TIME['scene_count']}")
    parts.append(f"- `world.long_rest_count`: {_DEMO_SYSTEM_TIME['long_rest_count']}")
    parts.append("")
    parts.append("## 本次生成要求")
    parts.append("- 一次产出整棵 DialogueGraph（5 个节点：3 个 dialogue + 2 个 end）。")
    parts.append("- entry node 落在节拍 1，ending 落在节拍 4–5。")
    parts.append(
        "- `relationship.<slug>.trust` 中的 `<slug>` 用 `vellin` / `corvan`，"
        "**严禁**写 `char_vellin`。"
    )
    return "\n".join(parts)


def _load_expected_graph() -> dict:
    """Return a deep-copied DialogueGraph with R3 text overrides applied.

    Deep-copy + override mirrors `prompts.few_shot.load_iron_oath_few_shot`
    — we never mutate /content/.
    """
    graph = json.loads(_SCENE_PATH.read_text(encoding="utf-8"))
    for node_id, node in graph["nodes"].items():
        for opt in node.get("options") or []:
            override = _FEW_SHOT_TEXT_OVERRIDES.get((node_id, opt["option_id"]))
            if override is not None:
                opt["text"] = override
    return graph


def load_iron_oath_scene_few_shot() -> SceneFewShotPair:
    """Return the single canonical scene-level demonstration.

    Adding more demos = appending to a future `load_*_scene_few_shot()` and
    composing them at render time. Don't bake multi-demo logic in until
    baseline shows it's needed.
    """
    return SceneFewShotPair(
        scene_setting_summary=_scene_setting_summary(),
        expected_graph=copy.deepcopy(_load_expected_graph()),
    )


def render_scene_few_shot_block(pair: SceneFewShotPair) -> str:
    """Render one scene few-shot pair as a markdown prompt fragment.

    Pulled out so the strategy module can cache the rendered block across
    skeleton + fill calls (the few-shot is identical across both phases;
    only the per-call requirement tail differs)."""
    parts: list[str] = ["## Few-shot 示范（整场场景）"]
    parts.append("### 输入 scene_setting + 角色卡")
    parts.append(pair.scene_setting_summary)
    parts.append("")
    parts.append("### 期望输出 DialogueGraph JSON")
    parts.append("```json")
    parts.append(json.dumps(pair.expected_graph, ensure_ascii=False, indent=2))
    parts.append("```")
    return "\n".join(parts)
