"""多 pass 分拍场景生成（作者 2026-06-08 拍板"采纳为默认"的 v1 实现）—— 露西全场.

结构层产**分拍节点图**：
  - choice 节点（多选项决策点）：开场（怎么接近）+ 枢纽（软问 vs 施压、路由）。
  - 单选项 beat 链（信息密集自动分拍）：软路径（完整线索）+ 硬路径（残缺线索）。
schema 不动（node.schema.json: type=dialogue 已允许单选项）。

⚠️ v1 拓扑是**半固定脚手架**（开场 → 枢纽 → 两分支 → end），用全部已验证的 call 类型规避
中转站超时；"完全动态拓扑（LLM 自己决定节点数/结构）"留作后续 refinement。

调用 ≈ 7 次（全是已验证 call 类型）：
  contract → 开场(skel+prose) → 枢纽(skel+prose) → 软分支(beat-pace) → 硬分支(beat-pace)

运行：PYTHONPATH=. python generator/scripts/multipass_paced_lucy.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from generator.llm_provider import ProviderError
from generator.prompts.node.multipass import (
    PASS1_SKELETON_SYSTEM,
    PASS2_PROSE_SYSTEM,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass1_node_schema,
    build_pass1_node_user_prompt,
    build_pass2_schema,
    build_pass2_user_prompt,
)
from generator.prompts.node.multipass.beat_pacing import (
    BEAT_PACING_SYSTEM,
    build_beat_pacing_schema,
    build_beat_pacing_user_prompt,
)
from generator.scripts.multipass_lucy_dry_run import (
    LUCY_SCENE_SPEC,
    _one_call,
    _resolve_provider_config,
)

GENERATOR_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = GENERATOR_ROOT / "experiments" / "multipass_structure" / "2026-06-08_lucy_paced_scene"

# 硬路径的残缺线索（failsafe 碎片；不含绕行方式/钥匙/异常）
DEGRADED_REVEALS = [
    "目标在希博公路北侧",
    "路标编号与“第七”有关",
    "旁边有一根断了半截的电线杆，可作野外搜索参照",
    "莱特在那留过一只小铁盒（露西坚称不知内容）",
]


def run_paced_scene(provider, spec: dict) -> dict:
    metas: list[dict] = []

    # Pass 1a：契约
    contract, m = _one_call(
        provider,
        system_prompt=PASS1_SKELETON_SYSTEM,
        user_prompt=build_pass1_contract_user_prompt(spec),
        json_schema=build_pass1_contract_schema(),
        est_output_tokens=600,
        label="contract",
    )
    metas.append(m)

    # choice 节点：开场(N1) + 枢纽(N2)，各 skel + prose
    choice: dict[str, dict] = {}
    prior: list[dict] = []
    for nid in ("N1", "N2"):
        skel, m = _one_call(
            provider,
            system_prompt=PASS1_SKELETON_SYSTEM,
            user_prompt=build_pass1_node_user_prompt(
                scene_spec=spec, scene_contract=contract, node_id=nid, prior_nodes=prior
            ),
            json_schema=build_pass1_node_schema(),
            est_output_tokens=800,
            label=f"skel_{nid}",
        )
        metas.append(m)
        skel.setdefault("node_id", nid)
        revealed = [r for p in prior for r in p.get("reveals", [])]
        prose, m = _one_call(
            provider,
            system_prompt=PASS2_PROSE_SYSTEM,
            user_prompt=build_pass2_user_prompt(
                scene_contract=contract,
                node_skeleton=skel,
                revealed_clues=revealed,
                used_option_intents=[],
            ),
            json_schema=build_pass2_schema(),
            est_output_tokens=1500,
            label=f"prose_{nid}",
        )
        metas.append(m)
        choice[nid] = {"skeleton": skel, "prose": prose}
        prior.append(skel)

    # 软分支：全线索分拍
    full_reveals = list(contract.get("required_clues", [])) + list(contract.get("optional_clues", []))
    soft, m = _one_call(
        provider,
        system_prompt=BEAT_PACING_SYSTEM,
        user_prompt=build_beat_pacing_user_prompt(
            scene_contract=contract,
            node_situation="玩家走了低压软问路线，露西在有限信任下交底；仍在公共区域、角落男人在看。",
            reveals=full_reveals,
        ),
        json_schema=build_beat_pacing_schema(),
        est_output_tokens=1200,
        label="soft_beats",
    )
    metas.append(m)

    # 硬分支：残缺线索分拍
    hard, m = _one_call(
        provider,
        system_prompt=BEAT_PACING_SYSTEM,
        user_prompt=build_beat_pacing_user_prompt(
            scene_contract=contract,
            node_situation="玩家施压、露西被逼到防御，只想尽快切断关系；只给能行动的残缺碎片，不给绕行方式/钥匙/异常。",
            reveals=DEGRADED_REVEALS,
        ),
        json_schema=build_beat_pacing_schema(),
        est_output_tokens=1000,
        label="hard_beats",
    )
    metas.append(m)

    return {
        "contract": contract,
        "choice": choice,
        "soft_beats": soft.get("beats", []),
        "hard_beats": hard.get("beats", []),
        "metas": metas,
    }


def _choice_block(title: str, node: dict) -> str:
    p = node["prose"]
    s = node["skeleton"]
    dlg = "\n".join(f"> {l}" for l in p.get("dialogue", []))
    opts = "\n".join(f"{i + 1}. {o.get('text','')}" for i, o in enumerate(p.get("options", [])))
    return f"""## ◆ {title}（选择节点 · {len(p.get('options', []))} 选项）
{p.get('narration','')}

**露西：**
{dlg or '（无）'}

**玩家可选：**
{opts}
"""


def _beats_block(title: str, beats: list[dict]) -> str:
    out = [f"## ─ {title}（{len(beats)} 个单选项节拍）"]
    for i, b in enumerate(beats, 1):
        dlg = "\n".join(f"> {l}" for l in b.get("dialogue", []))
        opt = b.get("continue_option", {}).get("text", "")
        out.append(
            f"""**〔节拍 {i}〕** {b.get('narration','')}
{dlg}
　→ `[ {opt} ]`"""
        )
    return "\n\n".join(out)


def _render(result: dict) -> str:
    total_cost = sum(m["actual_cost_usd"] for m in result["metas"])
    return f"""# 多 pass 分拍 · 露西全场（v1 采纳版）

> 作者 2026-06-08 "采纳为默认"。choice 节点（多选项）+ 单选项 beat 链；**schema 未改**。
> ⚠️ v1 拓扑半固定（开场 → 枢纽 → 两分支 → end）；完全动态拓扑是后续 refinement。
> 调用 {len(result['metas'])} 次 · 总成本 ${total_cost:.4f}

{_choice_block("开场", result['choice']['N1'])}
{_choice_block("枢纽：软问 vs 施压", result['choice']['N2'])}
{_beats_block("软路径（低压 · 完整线索）", result['soft_beats'])}

{_beats_block("硬路径（高压 · 残缺线索）", result['hard_beats'])}

## ◆ end（终止节点，无选项）
（玩家带着线索离开酒馆，进入后续野外调查；本场景结束。）
"""


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=str(GENERATOR_ROOT.parent / ".env"))
    except Exception:
        pass
    cfg = _resolve_provider_config(None, os.environ.get("LLM_JSON_MODE") or "prompt_only")
    if not cfg["api_key"]:
        print("❌ 缺 LLM_API_KEY", file=sys.stderr)
        return 2
    from generator.providers.poloai import PoloAIProvider

    provider = PoloAIProvider(
        api_key=cfg["api_key"], model_id=cfg["model_id"], base_url=cfg["base_url"], json_mode=cfg["json_mode"]
    )
    print(f"provider: {cfg['base_url']} {cfg['model_id']} {cfg['json_mode']}")
    t0 = time.time()
    try:
        result = run_paced_scene(provider, LUCY_SCENE_SPEC)
    except ProviderError as e:
        print(f"❌ provider_error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "scene.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "scene.md").write_text(_render(result), encoding="utf-8")
    total_cost = sum(m["actual_cost_usd"] for m in result["metas"])
    print("=" * 60)
    print(
        f"OK · 调用 {len(result['metas'])} 次 · ${total_cost:.4f} · {time.time()-t0:.1f}s · "
        f"软 {len(result['soft_beats'])} 拍 / 硬 {len(result['hard_beats'])} 拍"
    )
    print(f"scene: {OUT_DIR / 'scene.md'}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
