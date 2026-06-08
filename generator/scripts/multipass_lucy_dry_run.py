"""多 pass design-first 引擎原型——露西切片端到端跑测（Phase 1 结构层）.

把 design-first 生成从"一个大 prompt"改造成 **2 遍**（StoryWriter plan-compose-write）：

    Pass 1（骨架）：场景 spec → Scene Contract + 4 节点 Interaction Skeleton
                    （结构规则only；0 文风/AP）
    Pass 2（正文）：逐节点把骨架 + 历史压缩摘要当输入 → narration + dialogue + 第一人称选项
                    （瘦身文风：AP-1~6+9；去 AP-7/8/10）

对照 baseline = docs/experiments/design_first_node/2026-06-02_lucy_candidate_api_gpt55.md
（同一露西场景，单 monolithic prompt 产出）。

CLAUDE.md 合规：
    - LLM 调用走 PoloAIProvider 接口（ADR-011），不直接 import SDK。
    - 每次文本 LLM 调用前经 budget.check_and_charge()（ADR-012）；失败 refund。
    - 只在 /generator；产物写 generator/experiments/multipass_structure/，不碰 /docs。

运行（需先在 .env 配 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL，或对应 POLOAI_* / 环境变量）：
    python generator/scripts/multipass_lucy_dry_run.py            # 真跑（花预算）
    python generator/scripts/multipass_lucy_dry_run.py --dry      # 只装配 prompt，不调 API、不花预算
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from generator import budget
from generator.budget import BudgetExceeded
from generator.llm_provider import ProviderError
from generator.prompts.node.multipass import (
    PASS1_SKELETON_SYSTEM,
    PASS2_PROSE_SYSTEM,
    build_pass1_contract_schema,
    build_pass1_contract_user_prompt,
    build_pass1_node_schema,
    build_pass1_node_user_prompt,
    build_pass1_schema,
    build_pass1_user_prompt,
    build_pass2_schema,
    build_pass2_user_prompt,
)

GENERATOR_ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = GENERATOR_ROOT / "experiments" / "multipass_structure"

# 4 节点树形：N3 / N4 是 N2 的并行分支——N4 不应看见 N3 已揭露的线索（保护线索分层）。
NODE_ORDER = ["N1", "N2", "N3", "N4"]
ANCESTORS: dict[str, list[str]] = {
    "N1": [],
    "N2": ["N1"],
    "N3": ["N1", "N2"],
    "N4": ["N1", "N2"],
}


# ---------- 露西场景 spec（DOC §6 原样内联）----------

LUCY_SCENE_SPEC: dict[str, Any] = {
    "background": (
        "1920 年代禁酒令，美国公路酒馆，克苏鲁调查风。玩家调查查尔斯·莱特教授之死，"
        "来到希博公路酒馆找露西。露西曾和莱特有关系，知道莱特藏东西的小屋线索，但她害怕被牵连。"
        "酒馆里有一个角落男人可能在监视她。楼下是地下酒吧。氛围应是调查、压迫、现实危险和一点"
        "物理异常，不要直接写'邪恶存在'。"
    ),
    "design_goal": (
        "重点不是写漂亮小说，而是设计 playable scene（可玩场景）。每个 choice 都要从当前节点的"
        "信息、风险、NPC 心理和玩家目标里自然长出来。特别关注：玩家为什么此刻可以软问 / 给钱 / "
        "观察角落男人 / 威胁施压？每种做法有什么收益和代价？露西为什么会因不同选择改变 "
        "trust/fear/cooperability/affinity？"
    ),
    "character_state": (
        "露西：想保住自己、不想被莱特的死牵连；知道旧测绘小屋的大致路线；"
        "害怕角落男人听见'小屋''钥匙''教授'等词；对玩家没有初始信任，但希望有人把莱特留下的东西带走。\n"
        "角落男人：坐在靠窗角落；桌上没有酒，只有报纸；可能在监视露西，不一定立刻动手。"
    ),
    "required_clues": [
        "莱特在希博公路北侧有一间旧测绘小屋。",
        "小屋不在主路旁，要从酒馆后方的土路绕过去。",
        "路标是第七码碑和一根断了半截的电线杆。",
        "莱特把一只小铁盒留在小屋里。",
        "露西不知道铁盒里是什么，或者她声称不知道。",
    ],
    "optional_clues": [
        "小屋钥匙可能藏在雨桶底下。",
        "莱特死前来过酒馆，手上有黑色粉末。",
        "楼下有人问过莱特的行踪。",
        "角落男人不是本地酒客，他盯的是露西，不是玩家。",
        "地下酒吧后门通向旧货运坡道。",
        "莱特说过：'屋子外面只有二十步宽，里面量出来却多了四步。'",
    ],
    "forbidden_events": [
        "不揭示完整真相。",
        "不让露西解释神话体系或命名超自然来源。",
        "不让玩家在这里直接找到铁盒。",
        "不让露西死亡、被绑走或永久失联。",
        "不写成完整小说路径。",
        "不产生五个结局。",
        "不生成完整 DialogueGraph JSON。",
        "不把'信任高就全说、信任低就失败'做成单一门槛。",
    ],
}


# ---------- provider 配置（兼容 t_3y_1 的 LLM_* 习惯）----------


def _resolve_provider_config(model_id_override: str | None, json_mode_override: str | None) -> dict[str, Any]:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("POLOAI_API_KEY")
    base_url = (
        os.environ.get("LLM_BASE_URL")
        or os.environ.get("POLOAI_BASE_URL")
        or "https://poloai.top/v1"
    )
    model_id = (
        model_id_override
        or os.environ.get("LLM_MODEL")
        or os.environ.get("POLOAI_MODEL_ID")
        or "gpt-5.5-pro"
    )
    json_mode = (
        json_mode_override
        or os.environ.get("LLM_JSON_MODE")
        or os.environ.get("POLOAI_JSON_MODE")
        or "json_object"  # gpt-5.5-pro via relay：json_object 兼容性较好（见 t_3y_1）
    )
    return {"api_key": api_key, "base_url": base_url, "model_id": model_id, "json_mode": json_mode}


# ---------- 单次 LLM 调用（budget + provider + reconcile/refund）----------


def _one_call(
    provider: Any,
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    est_output_tokens: int,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """跑一次结构化调用；返回 (content, meta)。失败 refund 后抛 ProviderError。"""
    est_input_tokens = (len(system_prompt) + len(user_prompt)) // 4
    est_cost = provider.estimate_cost(est_input_tokens, est_output_tokens)
    record_id = budget.check_and_charge(
        est_cost,
        model_id=provider.model_id,
        input_tokens=est_input_tokens,
        output_tokens=est_output_tokens,
    )
    t0 = time.time()
    try:
        resp = provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
        )
    except ProviderError:
        budget.refund_estimated(record_id, reason=f"provider_error in {label}")
        raise
    elapsed = time.time() - t0
    actual_cost = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=resp.input_tokens,
        actual_output_tokens=resp.output_tokens,
        actual_cost_usd=actual_cost,
    )
    meta = {
        "label": label,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "actual_cost_usd": actual_cost,
        "elapsed_sec": elapsed,
        "finish_reason": resp.finish_reason,
    }
    return resp.content, meta


# ---------- 主流程：2-pass ----------


def run_multipass(provider: Any, spec: dict[str, Any]) -> dict[str, Any]:
    """跑完整 2-pass；返回结果 dict（含 skeleton / 4 节点正文 / metrics）。"""
    call_metas: list[dict[str, Any]] = []

    # --- Pass 1a：场景契约（小输出，过中转站超时）---
    scene_contract, c_meta = _one_call(
        provider,
        system_prompt=PASS1_SKELETON_SYSTEM,
        user_prompt=build_pass1_contract_user_prompt(spec),
        json_schema=build_pass1_contract_schema(),
        est_output_tokens=600,
        label="pass1_contract",
    )
    call_metas.append(c_meta)

    # --- Pass 1b：逐节点骨架（每次中等大小；喂前序节点 → 功能分化 + 线索分层）---
    node_by_id: dict[str, Any] = {}
    prior_nodes: list[dict[str, Any]] = []
    for nid in NODE_ORDER:
        node, n_meta = _one_call(
            provider,
            system_prompt=PASS1_SKELETON_SYSTEM,
            user_prompt=build_pass1_node_user_prompt(
                scene_spec=spec,
                scene_contract=scene_contract,
                node_id=nid,
                prior_nodes=prior_nodes,
            ),
            json_schema=build_pass1_node_schema(),
            est_output_tokens=800,
            label=f"pass1_skeleton_{nid}",
        )
        call_metas.append(n_meta)
        node.setdefault("node_id", nid)
        node_by_id[nid] = node
        prior_nodes.append(node)

    # --- Pass 2：逐节点正文（历史压缩）---
    prose_by_id: dict[str, Any] = {}
    for nid in NODE_ORDER:
        node_skeleton = node_by_id.get(nid)
        if node_skeleton is None:
            continue  # Pass 1 漏了某节点——容错跳过，metrics 会反映出来
        revealed: list[str] = []
        used_intents: list[str] = []
        for anc in ANCESTORS[nid]:
            anc_node = node_by_id.get(anc)
            if not anc_node:
                continue
            revealed.extend(anc_node.get("reveals", []))
            used_intents.extend(o.get("intent", "") for o in anc_node.get("options", []))
        p2_content, p2_meta = _one_call(
            provider,
            system_prompt=PASS2_PROSE_SYSTEM,
            user_prompt=build_pass2_user_prompt(
                scene_contract=scene_contract,
                node_skeleton=node_skeleton,
                revealed_clues=revealed,
                used_option_intents=used_intents,
            ),
            json_schema=build_pass2_schema(),
            est_output_tokens=1500,
            label=f"pass2_{nid}",
        )
        call_metas.append(p2_meta)
        prose_by_id[nid] = p2_content

    metrics = _compute_metrics(node_by_id, prose_by_id, call_metas)
    return {
        "status": "success",
        "scene_contract": scene_contract,
        "skeleton_nodes": node_by_id,
        "prose": prose_by_id,
        "call_metas": call_metas,
        "metrics": metrics,
        "raw_pass1": {"scene_contract": scene_contract, "nodes": list(node_by_id.values())},
    }


def _compute_metrics(
    node_by_id: dict[str, Any],
    prose_by_id: dict[str, Any],
    call_metas: list[dict[str, Any]],
) -> dict[str, Any]:
    """客观结构类 metrics——直接对账 baseline 弱点。"""
    narration_lens = {
        nid: len(prose_by_id.get(nid, {}).get("narration", "")) for nid in NODE_ORDER if nid in prose_by_id
    }
    option_counts = {
        nid: len(prose_by_id.get(nid, {}).get("options", [])) for nid in NODE_ORDER if nid in prose_by_id
    }
    # 节点功能分化信号：N1↔N2 option intent 重叠（越低越好；baseline 几乎全重叠）
    n1_intents = {o.get("intent", "") for o in node_by_id.get("N1", {}).get("options", [])}
    n2_intents = {o.get("intent", "") for o in node_by_id.get("N2", {}).get("options", [])}
    overlap = sorted(n1_intents & n2_intents) if (n1_intents and n2_intents) else []
    total_cost = sum(m["actual_cost_usd"] for m in call_metas)
    return {
        "narration_lengths": narration_lens,
        "narration_len_avg": (sum(narration_lens.values()) / len(narration_lens)) if narration_lens else 0,
        "option_counts": option_counts,
        "n1_n2_intent_overlap": overlap,
        "n1_n2_overlap_count": len(overlap),
        "total_calls": len(call_metas),
        "total_cost_usd": total_cost,
        "functions": {nid: node_by_id.get(nid, {}).get("function", "") for nid in NODE_ORDER if nid in node_by_id},
    }


# ---------- 落档 ----------


def _render_report(result: dict[str, Any], *, model_id: str) -> str:
    sc = result["scene_contract"]
    skel = result["skeleton_nodes"]
    prose = result["prose"]
    m = result["metrics"]
    today = date.today().isoformat()

    def _node_block(nid: str) -> str:
        s = skel.get(nid, {})
        p = prose.get(nid, {})
        opts = "\n".join(
            f"{i + 1}. {o.get('text','')}　*(intent: {o.get('intent','')})*"
            for i, o in enumerate(p.get("options", []))
        )
        dlg = "\n".join(f"> {line}" for line in p.get("dialogue", []))
        return f"""### {nid} — {s.get('function','')}
**当前局面**：{s.get('situation','')}
**choice pressure**：{s.get('choice_pressure','')}
**reveals**：{('、'.join(s.get('reveals', []))) or '（无）'}　**hides**：{('、'.join(s.get('hides', []))) or '（无）'}

**narration（{len(p.get('narration',''))} 字）**
{p.get('narration','')}

**dialogue**
{dlg or '（无）'}

**player options**
{opts or '（无）'}
"""

    nodes_md = "\n\n".join(_node_block(nid) for nid in NODE_ORDER if nid in prose)
    metrics_md = (
        f"- narration 长度：{json.dumps(m['narration_lengths'], ensure_ascii=False)}（均值 {m['narration_len_avg']:.0f} 字）\n"
        f"- 每节点选项数：{json.dumps(m['option_counts'], ensure_ascii=False)}\n"
        f"- N1↔N2 选项 intent 重叠：{m['n1_n2_overlap_count']} 个 {m['n1_n2_intent_overlap']}（越低=节点功能越分化）\n"
        f"- 节点功能：{json.dumps(m['functions'], ensure_ascii=False)}\n"
        f"- 总调用 {m['total_calls']} 次；总成本 ${m['total_cost_usd']:.4f}"
    )
    return f"""# 多 pass design-first 露西复测（Phase 1 结构层）

> **日期**：{today}　**模型**：`{model_id}`　**状态**：✅
> **对照 baseline**：docs/experiments/design_first_node/2026-06-02_lucy_candidate_api_gpt55.md

## 0. 结构类客观 metrics
{metrics_md}

## 1. Scene Contract（Pass 1）
- 玩家目标：{sc.get('player_goal','')}
- 露西目标：{sc.get('npc_goal','')}
- 露西恐惧：{sc.get('npc_fear','')}
- 必须线索：{('、'.join(sc.get('required_clues', []))) or '（无）'}
- 可选线索：{('、'.join(sc.get('optional_clues', []))) or '（无）'}
- 失败可续路径：{sc.get('failsafe_path','')}
- 禁止事项：{('、'.join(sc.get('forbidden', []))) or '（无）'}

## 2. 节点（Pass 1 骨架 + Pass 2 正文）
{nodes_md}

## 3. 调用 metas
```json
{json.dumps(result['call_metas'], ensure_ascii=False, indent=2)}
```

## 4. 原始 Pass 1 输出
```json
{json.dumps(result['raw_pass1'], ensure_ascii=False, indent=2)}
```
"""


def _emit(result: dict[str, Any], out_dir: Path, *, model_id: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "result.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = out_dir / "report.md"
    report_path.write_text(_render_report(result, model_id=model_id), encoding="utf-8")
    return report_path, json_path


# ---------- --dry：只装配 prompt，不调 API ----------


def _dry_run() -> int:
    spec = LUCY_SCENE_SPEC
    p1_user = build_pass1_user_prompt(spec)
    stub_node = {
        "node_id": "N2",
        "function": "hub：把接近方式升格成软问 vs 施压",
        "speaker_ref": "露西",
        "situation": "（示例 stub）",
        "options": [{"intent": "软问路线"}, {"intent": "高压施压"}, {"intent": "点破角落男人"}],
    }
    p2_user = build_pass2_user_prompt(
        scene_contract={"player_goal": "取得小屋线索", "npc_name": "露西"},
        node_skeleton=stub_node,
        revealed_clues=["莱特来过酒馆"],
        used_option_intents=["定向开场"],
    )
    print("=" * 70)
    print("[--dry] 只装配 prompt，不调 API、不花预算")
    print("=" * 70)
    print(f"Pass1 system: {len(PASS1_SKELETON_SYSTEM)} 字 | Pass1 user: {len(p1_user)} 字 | schema keys: {list(build_pass1_schema()['properties'])}")
    print(f"Pass2 system: {len(PASS2_PROSE_SYSTEM)} 字 | Pass2 user(stub): {len(p2_user)} 字 | schema keys: {list(build_pass2_schema()['properties'])}")
    print("-" * 70)
    print("Pass1 user 预览（前 600 字）：\n" + p1_user[:600])
    print("-" * 70)
    print("Pass2 system 预览（前 800 字）：\n" + PASS2_PROSE_SYSTEM[:800])
    print("-" * 70)
    print("Pass2 user(stub) 预览（前 600 字）：\n" + p2_user[:600])
    return 0


# ---------- CLI ----------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="多 pass design-first 露西复测原型")
    parser.add_argument("--dry", action="store_true", help="只装配 prompt，不调 API、不花预算")
    parser.add_argument("--model-id", default=None, help="覆盖模型 ID（默认 LLM_MODEL 或 gpt-5.5-pro）")
    parser.add_argument("--json-mode", default=None, help="json_schema | json_object | prompt_only")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_ROOT / f"{date.today().isoformat()}_lucy_multipass",
        help="产物输出目录（默认 generator/experiments/multipass_structure/<date>_lucy_multipass）",
    )
    args = parser.parse_args(argv)

    if args.dry:
        return _dry_run()

    # 真跑：装 .env + 配 provider
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass  # dotenv 可选；环境变量已设也行

    cfg = _resolve_provider_config(args.model_id, args.json_mode)
    if not cfg["api_key"]:
        print("❌ 缺 API key：请在 .env 或环境变量设 LLM_API_KEY（或 POLOAI_API_KEY）。", file=sys.stderr)
        print("   同时建议设 LLM_BASE_URL + LLM_MODEL 以匹配 baseline 用的中转站/模型。", file=sys.stderr)
        return 2

    from generator.providers.poloai import PoloAIProvider

    provider = PoloAIProvider(
        api_key=cfg["api_key"],
        model_id=cfg["model_id"],
        base_url=cfg["base_url"],
        json_mode=cfg["json_mode"],
    )
    print(f"provider: base_url={cfg['base_url']} model={cfg['model_id']} json_mode={cfg['json_mode']}")

    t0 = time.time()
    try:
        result = run_multipass(provider, LUCY_SCENE_SPEC)
    except BudgetExceeded as e:
        print(f"❌ budget_exceeded: {e}", file=sys.stderr)
        return 1
    except ProviderError as e:
        print(f"❌ provider_error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    result["metrics"]["elapsed_sec_total"] = time.time() - t0

    report_path, json_path = _emit(result, args.out_dir, model_id=cfg["model_id"])
    m = result["metrics"]
    print("=" * 70)
    print("STATUS: success")
    print(f"narration 长度: {m['narration_lengths']}（均值 {m['narration_len_avg']:.0f} 字）")
    print(f"N1↔N2 intent 重叠: {m['n1_n2_overlap_count']} {m['n1_n2_intent_overlap']}")
    print(f"节点功能: {m['functions']}")
    print(f"总调用: {m['total_calls']} 次 | 总成本: ${m['total_cost_usd']:.4f} | 总耗时: {m['elapsed_sec_total']:.1f}s")
    print(f"report: {report_path}")
    print(f"json:   {json_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
