"""N3 分拍样例：把多 pass 跑出的信息密集 N3 节点 pace 成 2-3 个单选项节拍.

作者反馈（2026-06-08）落地探索：演示"N3 一锅端 → 2-3 拍单选项节点"。
schema 不动（node.schema.json 已支持单选项：type=dialogue ⇒ options minItems=1）；
只在生成层 pace。LLM 走 PoloAIProvider + budget（ADR-011/012）。

运行：PYTHONPATH=. python generator/scripts/pace_n3_sample.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from generator import budget
from generator.llm_provider import ProviderError
from generator.prompts.node.multipass.beat_pacing import (
    BEAT_PACING_SYSTEM,
    build_beat_pacing_schema,
    build_beat_pacing_user_prompt,
)

GENERATOR_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = GENERATOR_ROOT / "experiments" / "multipass_structure" / "2026-06-08_lucy_multipass"
OUT_DIR = GENERATOR_ROOT / "experiments" / "multipass_structure" / "2026-06-08_n3_paced_sample"


def _render(old_n3: dict, beats: list[dict], reveals: list[str]) -> str:
    old_dlg = "\n".join(f"> {l}" for l in old_n3.get("dialogue", []))
    blocks = []
    for i, b in enumerate(beats, 1):
        dlg = "\n".join(f"> {l}" for l in b.get("dialogue", []))
        opt = b.get("continue_option", {}).get("text", "")
        blocks.append(
            f"""#### 节拍 {i}（单选项节点）
{b.get('narration','')}

**露西：**
{dlg or '（无）'}

**玩家（唯一选项）→** `[ {opt} ]`"""
        )
    beats_block = "\n\n".join(blocks)
    return f"""# N3 分拍样例：一锅端 → 单选项节拍

> 同一组线索（{len(reveals)} 条），左边原本一个节点全倒，右边拆成 {len(beats)} 个**单选项节拍**一拍一拍喂。
> schema 未改（node type=dialogue 允许单选项）；纯生成层 pace。

## ❌ 原 N3（一个节点，露西一口气 {len(old_n3.get('dialogue',[]))} 句说完）

**露西：**
{old_dlg}

（然后底下一次性给 5 个选项）

---

## ✅ 分拍版（{len(beats)} 个单选项节点，露西说一点→玩家接一句→再说一点）

{beats_block}
"""


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=str(GENERATOR_ROOT.parent / ".env"))
    except Exception:
        pass
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("POLOAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL") or "https://poloai.top/v1"
    model = os.environ.get("LLM_MODEL") or "gpt-5.5"
    json_mode = os.environ.get("LLM_JSON_MODE") or "prompt_only"
    if not api_key:
        print("❌ 缺 LLM_API_KEY（.env 或环境变量）", file=sys.stderr)
        return 2

    from generator.providers.poloai import PoloAIProvider

    provider = PoloAIProvider(api_key=api_key, model_id=model, base_url=base_url, json_mode=json_mode)

    result = json.loads((RUN_DIR / "result.json").read_text(encoding="utf-8"))
    contract = result["scene_contract"]
    n3_skeleton = result["skeleton_nodes"]["N3"]
    old_n3_prose = result["prose"]["N3"]
    reveals = n3_skeleton.get("reveals", [])
    situation = n3_skeleton.get("situation", "")

    system = BEAT_PACING_SYSTEM
    user = build_beat_pacing_user_prompt(
        scene_contract=contract, node_situation=situation, reveals=reveals
    )
    schema = build_beat_pacing_schema()

    n = (len(system) + len(user)) // 4
    rid = budget.check_and_charge(
        provider.estimate_cost(n, 1200), model_id=model, input_tokens=n, output_tokens=1200
    )
    t0 = time.time()
    try:
        resp = provider.generate_structured(system_prompt=system, user_prompt=user, json_schema=schema)
    except ProviderError as e:
        budget.refund_estimated(rid, reason="pace fail")
        print(f"❌ provider_error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    actual = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    budget.reconcile_after_call(
        rid, actual_input_tokens=resp.input_tokens, actual_output_tokens=resp.output_tokens, actual_cost_usd=actual
    )
    beats = resp.content.get("beats", [])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "beats.json").write_text(json.dumps(resp.content, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "sample.md").write_text(_render(old_n3_prose, beats, reveals), encoding="utf-8")

    print("=" * 60)
    print(f"OK · beats={len(beats)} · cost=${actual:.4f} · {time.time()-t0:.1f}s")
    for i, b in enumerate(beats, 1):
        print(
            f"  节拍{i}: narration {len(b.get('narration',''))}字, "
            f"露西 {len(b.get('dialogue',[]))}句, →[{b.get('continue_option',{}).get('text','')}]"
        )
    print(f"sample: {OUT_DIR / 'sample.md'}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
