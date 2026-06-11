"""结构层正式生成 CLI —— 多 pass + 分拍 + 动态拓扑（generator/multipass 引擎）.

用法（需 .env 配 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL；json_mode 默认 prompt_only）：

  # 全量生成（1 个候选）
  PYTHONPATH=. python generator/scripts/run_multipass_scene.py \
      --spec generator/experiments/multipass_structure/specs/lucy.json

  # 只 smoke 契约 + 拓扑规划两个调用（验证新 call 类型过中转站；~$0.05）
  PYTHONPATH=. python generator/scripts/run_multipass_scene.py --spec ... --topology-only

  # 多候选（复核用：同 spec 重跑 N 次，各自独立产物目录）
  PYTHONPATH=. python generator/scripts/run_multipass_scene.py --spec ... --candidates 2

spec 文件形态（JSON）：
  {"config": {"graph_id", "scene_anchor", "speaker_ref", "character_refs", "npc_name"},
   "spec":   {"background", "design_goal", "character_state",
              "required_clues", "optional_clues", "forbidden_events"}}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from generator.budget import BudgetExceeded
from generator.llm_provider import ProviderError
from generator.multipass import SceneRunConfig, run_multipass_scene
from generator.multipass.calls import structured_call
from generator.multipass.engine import write_artifacts
from generator.multipass.topology import validate_topology
from generator.prompts.node.multipass import (
    PASS1_SKELETON_SYSTEM,
    TOPOLOGY_SYSTEM,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_topology_schema,
    build_topology_user_prompt,
)

GENERATOR_ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = GENERATOR_ROOT / "experiments" / "multipass_structure"


def _make_provider():
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=str(GENERATOR_ROOT.parent / ".env"))
    except Exception:
        pass
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("POLOAI_API_KEY")
    if not api_key:
        print("❌ 缺 LLM_API_KEY（.env 或环境变量）", file=sys.stderr)
        return None
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("POLOAI_BASE_URL") or "https://poloai.top/v1"
    model_id = os.environ.get("LLM_MODEL") or os.environ.get("POLOAI_MODEL_ID") or "gpt-5.5"
    json_mode = os.environ.get("LLM_JSON_MODE") or "prompt_only"  # 中转站现实：大请求 json_schema/json_object 会 502
    from generator.providers.poloai import PoloAIProvider

    provider = PoloAIProvider(api_key=api_key, model_id=model_id, base_url=base_url, json_mode=json_mode)
    print(f"provider: {base_url} {model_id} json_mode={json_mode}")
    return provider


def _topology_only(provider, spec: dict) -> int:
    """smoke：契约 + 拓扑规划两个小调用，打印 plan + 确定性校验结果。"""
    contract, m1 = structured_call(
        provider,
        system_prompt=PASS1_SKELETON_SYSTEM,
        user_prompt=build_pass1_contract_user_prompt(spec),
        json_schema=build_pass1_contract_schema(),
        est_output_tokens=600,
        label="smoke_contract",
    )
    plan, m2 = structured_call(
        provider,
        system_prompt=TOPOLOGY_SYSTEM,
        user_prompt=build_topology_user_prompt(scene_spec=spec, scene_contract=contract),
        json_schema=build_topology_schema(),
        est_output_tokens=800,
        label="smoke_topology",
    )
    errors = validate_topology(plan)
    cost = m1["actual_cost_usd"] + m2["actual_cost_usd"]
    print("=" * 60)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print("-" * 60)
    print(f"确定性校验：{'✅ 合法' if not errors else errors}")
    print(f"2 次调用 · ${cost:.4f} · 契约 {m1['elapsed_sec']:.1f}s / 拓扑 {m2['elapsed_sec']:.1f}s")
    print("=" * 60)
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="多 pass + 分拍 + 动态拓扑场景生成")
    parser.add_argument("--spec", type=Path, required=True, help="spec JSON（含 config + spec 两段）")
    parser.add_argument("--candidates", type=int, default=1, help="候选数（同 spec 重跑 N 次）")
    parser.add_argument("--topology-only", action="store_true", help="只 smoke 契约+拓扑两个调用")
    parser.add_argument("--out-root", type=Path, default=None, help="产物根目录")
    args = parser.parse_args(argv)

    payload = json.loads(args.spec.read_text(encoding="utf-8"))
    spec = payload["spec"]
    cfg = payload["config"]
    config = SceneRunConfig(
        graph_id=cfg["graph_id"],
        scene_anchor=cfg["scene_anchor"],
        speaker_ref=cfg["speaker_ref"],
        character_refs=cfg["character_refs"],
        npc_name=cfg.get("npc_name", "NPC"),
    )

    provider = _make_provider()
    if provider is None:
        return 2

    try:
        if args.topology_only:
            return _topology_only(provider, spec)

        out_root = args.out_root or (OUT_ROOT / f"{date.today().isoformat()}_{config.graph_id}")
        exit_code = 0
        for cand in range(1, args.candidates + 1):
            t0 = time.time()
            result = run_multipass_scene(provider, spec, config)
            out_dir = out_root / f"candidate_{cand}" if args.candidates > 1 else out_root
            paths = write_artifacts(result, out_dir)
            m = result.metrics
            print("=" * 60)
            print(
                f"candidate {cand}: {result.status}"
                + (f"（{result.failure_reason}）" if result.failure_reason else "")
            )
            if result.status == "success":
                print(
                    f"节点 {m.get('node_count')} 个 · 调用 {m['total_calls']} 次 · "
                    f"${m['total_cost_usd']:.4f} · {time.time() - t0:.1f}s · "
                    f"硬校验 {'✅' if m.get('hard_pass') else '❌'} · AP flag {m.get('ap_flag_count', 0)} · "
                    f"拓扑 {'回退' if result.topology_fallback else '动态'}"
                )
            else:
                exit_code = 1
            for w in result.warnings:
                print(f"  ⚠️ {w}")
            print(f"  scene: {paths.get('scene_md', paths['design'])}")
        return exit_code
    except BudgetExceeded as e:
        print(f"❌ budget_exceeded: {e}", file=sys.stderr)
        return 1
    except ProviderError as e:
        print(f"❌ provider_error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
