"""T-3Y-1 mini prototype 端到端 dry-run（end-to-end dry run）— goal 3 实证.

完整流水线：
    读 A1 dry-run §3.7.3 露西节点骨架（node_3_info_offer）+ scene_inn_meet_lucy 场景
    → Forward Planner 三步（intent / state_summary / reconcile）
    → render_node_prompt 拼接 {system, user}
    → PoloAIProvider 调真实 LLM（gpt-5.5-pro via https://poloai.top）
    → 解析输出 JSON
    → anti_pattern_detector 程序化检测 AP-7/8/10
    → node_rubric_scorer 评分 information_density + baimiao_compliance
    → 写 JSON + markdown 实测报告

CLAUDE.md 合规：
    - LLM 调用走 PoloAIProvider 接口（ADR-011）
    - 任何文本 LLM API 调用前经 budget.check_and_charge()（ADR-012）
    - 结构化输出走 provider 原生能力（ADR-013）

运行：
    .venv/bin/python generator/scripts/t_3y_1_dry_run.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from generator import budget
from generator.budget import BudgetExceeded
from generator.forward_planner.intent import compute_intent
from generator.forward_planner.reconcile import reconcile
from generator.forward_planner.state_summary import compute_player_known_info
from generator.llm_provider import ProviderError
from generator.node_text_gen.render import render_node_prompt
from generator.providers.poloai import PoloAIProvider
from validator.anti_pattern_detector import detect_anti_patterns
from validator.node_rubric_scorer import score_node


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------- A1 dry-run §3.7.3 节点骨架 + 场景上下文（mini prototype 内联） ----------
# 不读 /content/test_scene_v0/scene.json（那是铁誓驿站 gold scene；与本节点无关）
# T-3Y-1 mini prototype 用内联结构；后续 production 可改读文件


def build_inn_lucy_graph() -> dict[str, Any]:
    """构造酒馆见露西场景 + node_3_info_offer 骨架.

    参考：/docs/reviews/master_plan/2026-05-13_A1_dry_run_crimson_letters.md §3.7.3
    场景：scene_inn_meet_lucy（act_2_investigation；克苏鲁版极乐迪斯科 spiritual successor）
    节点：node_3_info_offer（4 options；信息密度最高节点）
    """
    return {
        "schema_version": "0.1.1",
        "graph_id": "scene_inn_meet_lucy",
        "entry_node_id": "node_3_info_offer",
        "scene_anchor": "scene_inn",
        "character_refs": ["char_lucy"],
        # ADR-034 D4 scene_metaparams
        "scene_metaparams": {
            "culprit_id": "culprit_vick",
            "difficulty_level": "normal",
            "apparition_level": 1,
        },
        # ADR-034 D5 scene_reveals（ordered flag set）
        "scene_reveals": [
            {
                "reveal_id": "R1_wright_double_life",
                "trigger_node_ids": ["node_3_info_offer"],
                "completion_node_id": "node_3_info_offer",
                "required_stages": [1, 2],
            }
        ],
        # ADR-034 D6 scene_seeds（coverage_strategy enum）
        "scene_seeds": [
            {
                "seed_id": "S2_vick_dangerous",
                "planted_in_node_ids": ["node_3_info_offer"],
                "coverage_strategy": "mandatory_all_paths",
            },
            {
                "seed_id": "S4_country_cottage_cache",
                "planted_in_node_ids": ["node_3_info_offer"],
                "coverage_strategy": "conditional_reward",
                "condition": {
                    "op": "gte",
                    "path": "relationship.lucy.trust",
                    "value": 2,
                },
            },
        ],
        # ADR-016 v0.4 player_known_info
        "player_known_info": [
            {"knowledge_path": "knowledge.wright_dead", "stage": 1},
            {"knowledge_path": "knowledge.lucy_known_to_player"},
            {"knowledge_path": "knowledge.gangster_watching_lucy"},
        ],
        "nodes": {
            "node_3_info_offer": {
                "node_id": "node_3_info_offer",
                "type": "dialogue",
                "narration": "",  # LLM 待填
                "speaker_ref": "char_lucy",
                "location_ref": "scene_inn",
                "on_enter_effects": [
                    {"op": "set", "path": "flag.lucy_opened_up", "value": True}
                ],
                "options": [
                    {
                        "option_id": "opt_continue_press",
                        "text": "",  # LLM 待填
                        "target_node_id": "node_5_end_ally",
                        "condition": None,
                        "effects": [
                            {"op": "set", "path": "flag.lucy_knows_wright_lower_life", "value": True},
                            {"op": "set", "path": "flag.player_got_vick_card", "value": True},
                        ],
                        "unavailable_behavior": "hide",
                    },
                    {
                        "option_id": "opt_warn_about_vick",
                        "text": "",
                        "target_node_id": "node_5_end_ally",
                        "condition": None,
                        "effects": [
                            {"op": "set", "path": "flag.player_got_vick_card", "value": True},
                            {"op": "set", "path": "flag.lucy_alerted", "value": True},
                            {"op": "inc", "path": "relationship.lucy.trust", "value": 1},
                        ],
                        "unavailable_behavior": "hide",
                    },
                    {
                        "option_id": "opt_press_for_cache",
                        "text": "",
                        "target_node_id": "node_5_end_ally",
                        "condition": {
                            "op": "gte",
                            "path": "relationship.lucy.trust",
                            "value": 2,
                        },
                        "effects": [
                            {"op": "set", "path": "flag.cache_known", "value": True},
                            {"op": "set", "path": "flag.player_got_vick_card", "value": True},
                        ],
                        "unavailable_behavior": "disable_with_hint",
                    },
                    {
                        "option_id": "opt_betray_lucy_to_eyes",
                        "text": "",
                        "target_node_id": "node_6_end_cold",
                        "condition": None,
                        "effects": [
                            {"op": "set", "path": "flag.lucy_betrayed_to_gangs", "value": True},
                            {"op": "set", "path": "flag.player_got_vick_card", "value": False},
                            {"op": "dec", "path": "relationship.lucy.trust", "value": 999},
                        ],
                        "unavailable_behavior": "hide",
                    },
                ],
                # T-3Y-1 节点级新字段
                "background_seeds": ["S2_vick_dangerous", "S4_country_cottage_cache"],
                "foreground_goal": "R1_wright_double_life.stage_2",
            }
        },
    }


def build_player_state() -> dict[str, Any]:
    """构造玩家当前 state——已走访莱特办公室 + 知道露西关联.

    模拟玩家进入 node_3 时已知信息（对应 player_known_info 全部 set）.
    """
    return {
        "knowledge.wright_dead": True,
        "knowledge.lucy_known_to_player": True,
        "knowledge.gangster_watching_lucy": True,
    }


def build_all_known_info_summary() -> str:
    """全局背景摘要（不入 schema；prompt assembly 阶段拼接）."""
    return (
        "玩家是私家侦探，受雇调查教授莱特之死。"
        "已走访莱特办公室，发现破镜 + 烧过文件 + 散落的赌债借条。"
        "露西是莱特的情人 + 希博公路酒馆侍应；玩家刚被引荐到酒馆。"
        "酒馆角落桌有两个穿西装的男人在监视露西方向——大西洋城打手风格。"
        "倒计时：通路征兆显现等级 1（远处的幻听 / 转角的影子）。"
    )


def build_npc_state() -> dict[str, Any]:
    """NPC 当前 state（露西在 node_3 入口的状态机快照）."""
    return {
        "name": "Lucy",
        "current_persona": "wary_but_warming",  # 警惕但开始开口
        "relationship_with_player": {
            "trust": 1,
            "fear": 2,
            "affinity": 1,
        },
        "current_emotion": "受惊但努力镇定",
        "knows_about_culprit": "vick",
        "secret_layer_1": "wright 赌债 / 大西洋城打手",
        "secret_layer_2_locked": "vick 名片 + 弗林德斯监视细节（需 trust ≥ 2 解锁）",
    }


# ---------- 输出 JSON Schema（提供给 PoloAIProvider）----------


def build_response_schema() -> dict[str, Any]:
    """构造 LLM 输出契约的 JSON Schema.

    只约束 narration + options[].text 两字段；其他字段 LLM echo 原值即可.
    """
    return {
        "type": "object",
        "required": ["narration", "options"],
        "properties": {
            "narration": {
                "type": "string",
                "description": "节点旁白；150-400 汉字；遵守 3 分类角色守则旁白契约",
            },
            "options": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "required": ["option_id", "text"],
                    "properties": {
                        "option_id": {
                            "type": "string",
                            "description": "保持骨架中的 option_id 不变",
                        },
                        "text": {
                            "type": "string",
                            "description": "≤ 25 汉字；第一人称玩家语言；可保留 [skill] 前缀",
                        },
                    },
                },
            },
        },
    }


# ---------- 主流水线 ----------


def run_pipeline(
    *,
    out_report_path: Path,
    out_json_path: Path,
    model_id: str = "gpt-5.5-pro",
) -> dict[str, Any]:
    """跑一次完整 dry-run；返回结果 dict.

    失败也会落档报告（含失败原因 + 中间产物）；成功返回完整结果.
    """
    t_start = time.time()
    trace: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_id": model_id,
        "steps": [],
    }

    def _trace(step: str, **kwargs: Any) -> None:
        trace["steps"].append({"step": step, **kwargs})

    # ---------- step 1: 装载 .env + 校验 API key ----------
    load_dotenv()
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://poloai.top/v1")
    if not api_key:
        return _emit_failure_report(
            trace, out_report_path, out_json_path,
            failure_reason="missing_api_key",
            detail="LLM_API_KEY 未在 .env 或环境变量中找到；无法调用 LLM provider",
            elapsed_sec=time.time() - t_start,
        )
    _trace("env_loaded", base_url=base_url, model_id=model_id)

    # ---------- step 2: 构造场景 + 节点骨架 + 玩家 state ----------
    graph = build_inn_lucy_graph()
    node_id = "node_3_info_offer"
    current_state = build_player_state()
    summary = build_all_known_info_summary()
    npc_state = build_npc_state()
    _trace(
        "scene_loaded",
        graph_id=graph["graph_id"],
        node_id=node_id,
        scene_seeds=len(graph["scene_seeds"]),
        scene_reveals=len(graph["scene_reveals"]),
    )

    # ---------- step 3: Forward Planner 三步 ----------
    intent = compute_intent(graph, node_id)
    pki = compute_player_known_info(graph, current_state)
    rec = reconcile(intent, pki)
    _trace(
        "forward_planner",
        foreground_goal=intent.get("foreground_goal"),
        background_seeds=intent.get("background_seeds"),
        relevant_known_count=len(pki),
        reconcile_verdict=rec.get("verdict"),
    )
    if rec.get("verdict") != "pass":
        return _emit_failure_report(
            trace, out_report_path, out_json_path,
            failure_reason="reconcile_failed",
            detail=f"Forward Planner reconcile verdict = {rec.get('verdict')} ({rec.get('reason')})",
            elapsed_sec=time.time() - t_start,
        )

    # ---------- step 4: render prompt ----------
    skeleton = graph["nodes"][node_id]
    prompt = render_node_prompt(
        node_skeleton=skeleton,
        player_known_info=pki,
        foreground_goal=intent["foreground_goal"],
        background_seeds=intent["background_seeds"],
        speaker_ref=skeleton.get("speaker_ref"),
        npc_state=npc_state,
        all_known_info_summary=summary,
    )
    sys_chars = len(prompt["system"])
    user_chars = len(prompt["user"])
    _trace("prompt_rendered", system_chars=sys_chars, user_chars=user_chars)

    # ---------- step 5: budget 预算检查 + 实例化 provider ----------
    est_input_tokens = (sys_chars + user_chars) // 4
    est_output_tokens = 1500
    provider = PoloAIProvider(
        api_key=api_key,
        model_id=model_id,
        base_url=base_url,
        json_mode="json_object",  # gpt-5.5-pro via poloai relay；json_object 较 schema 兼容性好
    )
    est_cost = provider.estimate_cost(est_input_tokens, est_output_tokens)
    try:
        record_id = budget.check_and_charge(
            estimated_cost_usd=est_cost,
            model_id=model_id,
            input_tokens=est_input_tokens,
            output_tokens=est_output_tokens,
        )
        _trace(
            "budget_charged",
            record_id=record_id,
            estimated_cost_usd=est_cost,
            est_input_tokens=est_input_tokens,
            est_output_tokens=est_output_tokens,
        )
    except BudgetExceeded as e:
        return _emit_failure_report(
            trace, out_report_path, out_json_path,
            failure_reason="budget_exceeded",
            detail=str(e),
            elapsed_sec=time.time() - t_start,
        )

    # ---------- step 6: 真调 LLM ----------
    response_schema = build_response_schema()
    t_llm_start = time.time()
    try:
        resp = provider.generate_structured(
            system_prompt=prompt["system"],
            user_prompt=prompt["user"],
            json_schema=response_schema,
        )
    except ProviderError as e:
        # Refund + 落档失败报告
        try:
            from generator import cost_log
            cost_log.mark_refunded(record_id, reason=f"provider_error: {e}")
        except Exception:
            pass
        return _emit_failure_report(
            trace, out_report_path, out_json_path,
            failure_reason="provider_error",
            detail=f"{type(e).__name__}: {e}",
            elapsed_sec=time.time() - t_start,
            extra={"prompt_system_preview": prompt["system"][:500], "prompt_user_preview": prompt["user"][:1000]},
        )
    elapsed_llm = time.time() - t_llm_start

    # 实际 token 对账
    actual_cost = provider.estimate_cost(resp.input_tokens, resp.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=resp.input_tokens,
        actual_output_tokens=resp.output_tokens,
        actual_cost_usd=actual_cost,
    )
    _trace(
        "llm_call_complete",
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        actual_cost_usd=actual_cost,
        elapsed_sec_llm=elapsed_llm,
        finish_reason=resp.finish_reason,
    )

    # ---------- step 7: merge LLM 输出回节点 ----------
    completed_node = json.loads(json.dumps(skeleton))  # deep copy
    llm_narration = resp.content.get("narration", "")
    completed_node["narration"] = llm_narration
    llm_options_by_id = {
        opt.get("option_id"): opt.get("text", "")
        for opt in resp.content.get("options", [])
    }
    for opt in completed_node["options"]:
        opt["text"] = llm_options_by_id.get(opt["option_id"], opt["text"])

    # ---------- step 8: anti-pattern + rubric ----------
    ap_flags = detect_anti_patterns(completed_node)
    rubric_results = score_node(completed_node)
    _trace(
        "evaluation_complete",
        anti_pattern_flags=len(ap_flags),
        rubric_information_density=rubric_results["information_density"].score,
        rubric_baimiao_compliance=rubric_results["baimiao_compliance"].score,
    )

    elapsed_total = time.time() - t_start

    result: dict[str, Any] = {
        "status": "success",
        "completed_node": completed_node,
        "anti_pattern_flags": [asdict(f) for f in ap_flags],
        "rubric": {
            dim: {"score": s.score, "trace": s.trace}
            for dim, s in rubric_results.items()
        },
        "raw_llm_output": resp.content,
        "metadata": {
            "model_id": resp.model_id,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "actual_cost_usd": actual_cost,
            "elapsed_sec_total": elapsed_total,
            "elapsed_sec_llm": elapsed_llm,
            "finish_reason": resp.finish_reason,
            "started_at": trace["started_at"],
        },
        "trace": trace,
    }

    # ---------- step 9: 落档 JSON + markdown ----------
    _emit_success_report(
        result=result,
        out_report_path=out_report_path,
        out_json_path=out_json_path,
        graph=graph,
        intent=intent,
        pki=pki,
        npc_state=npc_state,
        prompt=prompt,
    )

    return result


# ---------- 报告落档 ----------


def _emit_failure_report(
    trace: dict[str, Any],
    out_report_path: Path,
    out_json_path: Path,
    *,
    failure_reason: str,
    detail: str,
    elapsed_sec: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """失败也落档——含中间产物 trace + 失败原因."""
    result = {
        "status": "failed",
        "failure_reason": failure_reason,
        "detail": detail,
        "elapsed_sec_total": elapsed_sec,
        "trace": trace,
        "extra": extra or {},
    }
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = _render_failure_markdown(result)
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(md, encoding="utf-8")
    return result


def _emit_success_report(
    *,
    result: dict[str, Any],
    out_report_path: Path,
    out_json_path: Path,
    graph: dict[str, Any],
    intent: dict[str, Any],
    pki: list[dict[str, Any]],
    npc_state: dict[str, Any],
    prompt: dict[str, str],
) -> None:
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = _render_success_markdown(
        result=result, graph=graph, intent=intent, pki=pki,
        npc_state=npc_state, prompt=prompt,
    )
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(md, encoding="utf-8")


def _render_success_markdown(
    *,
    result: dict[str, Any],
    graph: dict[str, Any],
    intent: dict[str, Any],
    pki: list[dict[str, Any]],
    npc_state: dict[str, Any],
    prompt: dict[str, str],
) -> str:
    node = result["completed_node"]
    meta = result["metadata"]
    rubric = result["rubric"]
    ap = result["anti_pattern_flags"]
    today = date.today().isoformat()

    options_md = "\n".join(
        f"- **{opt['option_id']}**: {opt['text']}"
        + (f" *(检定条件 condition: `{json.dumps(opt['condition'], ensure_ascii=False)}`)*"
           if opt.get("condition") else "")
        for opt in node["options"]
    )
    pki_md = "\n".join(
        f"  - `{item['knowledge_path']}`"
        + (f" (阶段 stage {item['stage']})" if item.get("stage") else "")
        for item in pki
    )
    ap_md = (
        "无 anti-pattern 触发（程序化检测 AP-7/8/10 全 clean）"
        if not ap
        else "\n".join(
            f"- **{f['ap_id']}** @ `{f['location']}`：{f['reason']}\n  - 触发片段：「{f['excerpt']}」"
            for f in ap
        )
    )

    return f"""# T-3Y-1 mini prototype 实测报告（dry-run report）

> **日期**：{today}
> **状态**：✅ 成功
> **任务**：T-3Y-1 节点级文本生成 mini prototype 端到端 dry-run
> **节点**：`{node['node_id']}`（A1 dry-run §3.7.3 露西对话节点）
> **场景**：`{graph['graph_id']}`（克苏鲁版极乐迪斯科 spiritual successor / 酒馆见露西）

---

## 1. 生成结果（generated narration + options）

### Narration（旁白；{len(node['narration'])} 字）

{node['narration']}

### Options（选项；{len(node['options'])} 个）

{options_md}

---

## 2. 评估元数据（evaluation metadata）

### 2.1 Rubric scorer 评分（0-10 分）

| 维度（dimension） | 分数（score） | 计算痕迹（trace） |
|---|---|---|
| **信息密度（information_density）** | **{rubric['information_density']['score']:.2f}** | `{json.dumps(rubric['information_density']['trace'], ensure_ascii=False)}` |
| **白描合规度（baimiao_compliance）** | **{rubric['baimiao_compliance']['score']:.2f}** | `{json.dumps(rubric['baimiao_compliance']['trace'], ensure_ascii=False)}` |

### 2.2 Anti-pattern detector flags（程序化检测）

{ap_md}

**未程序化（LLM-as-judge 待办）**：AP-1 对仗式 / AP-2 修辞失底 / AP-3 物理方向 /
AP-4 假靶子否定 / AP-5 总结代细节 / AP-6 锚定未说明标准 / AP-9 读不懂的省略 ——
本报告本节点这 7 条未自动检测；留待作者人工 [A]/[R]/[S] 段判定。

---

## 3. 实测 metrics（实测 token + 耗时 + 成本）

| 指标（metric） | 值 |
|---|---|
| **模型（model）** | `{meta['model_id']}` |
| **input_tokens** | {meta['input_tokens']} |
| **output_tokens** | {meta['output_tokens']} |
| **实际成本（actual_cost_usd）** | ${meta['actual_cost_usd']:.4f} |
| **LLM 调用耗时（elapsed_sec_llm）** | {meta['elapsed_sec_llm']:.2f} s |
| **总耗时（elapsed_sec_total）** | {meta['elapsed_sec_total']:.2f} s |
| **finish_reason** | `{meta['finish_reason']}` |
| **开始时间（started_at）** | {meta['started_at']} |

---

## 4. Forward Planner 输入（编剧意图 + 玩家状态）

### 4.1 模块 A intent（剧本意图层）

- **foreground_goal**: `{intent.get('foreground_goal')}`
- **background_seeds**: `{json.dumps(intent.get('background_seeds', []), ensure_ascii=False)}`

### 4.2 模块 B state_summary（状态摘要层）

**relevant_known_info（结构化短列表）**：

{pki_md}

**all_known_info_summary（全局背景；不入 schema）**：

> {prompt['user'].split('all_known_info_summary')[1].split('**')[2].strip() if 'all_known_info_summary' in prompt['user'] else '(见 prompt user message)'}

### 4.3 模块 C reconcile

- **verdict**: `pass`

---

## 5. NPC 状态机快照（npc_state）

```json
{json.dumps(npc_state, ensure_ascii=False, indent=2)}
```

---

## 6. 待人工审稿 [A]/[R]/[S] 段（accept / revise / scrap）

> 作者按以下三档标注，作为 T-3Y-1 实证完成的最后一步：
>
> - **[A] Accept**：narration 或 option 文本可直接采用
> - **[R] Revise**：需要小修订
> - **[S] Scrap**：需要重生成

| 段落 | 内容片段 | 你的标注 |
|---|---|---|
| Narration | （见上文 §1） | [_] |
| opt_continue_press | `{node['options'][0]['text']}` | [_] |
| opt_warn_about_vick | `{node['options'][1]['text']}` | [_] |
| opt_press_for_cache | `{node['options'][2]['text']}` | [_] |
| opt_betray_lucy_to_eyes | `{node['options'][3]['text']}` | [_] |

整体接受率（gross_pass_rate）= [A] / ([A] + [R] + [S]) = _____

---

## 7. 工程层附录

### 7.1 调用链 trace

```json
{json.dumps(result['trace'], ensure_ascii=False, indent=2)}
```

### 7.2 prompt 全文（system + user）

<details>
<summary>system prompt（点开展开）</summary>

```text
{prompt['system']}
```

</details>

<details>
<summary>user message（点开展开）</summary>

```text
{prompt['user']}
```

</details>

### 7.3 raw LLM 输出

```json
{json.dumps(result['raw_llm_output'], ensure_ascii=False, indent=2)}
```

---

## 8. 落档信息

- **产出方**：T-3Y-1 工程会话（claude/eloquent-mclean-8f0bd9 worktree）
- **依赖**：ADR-016 v0.4（knowledge.* 命名空间）+ ADR-034 D4-D11（场景级字段）+ ADR-029（技能体系）+ ADR-002/004（运行时无 LLM；生产期分离）
- **commit 范围**：goal 1（schema + Forward Planner stubs + state_path_validator）+ goal 2（prompt 模板 + node_text_gen + anti_pattern_detector + rubric scorer）+ goal 3（本 dry-run）
"""


def _render_failure_markdown(result: dict[str, Any]) -> str:
    today = date.today().isoformat()
    return f"""# T-3Y-1 mini prototype 实测报告（dry-run report）

> **日期**：{today}
> **状态**：❌ 失败
> **失败原因（failure_reason）**：`{result['failure_reason']}`
> **耗时（elapsed_sec_total）**：{result['elapsed_sec_total']:.2f} s

---

## 失败 detail

```
{result['detail']}
```

---

## 中间产物 trace（已完成的 step）

```json
{json.dumps(result['trace'], ensure_ascii=False, indent=2)}
```

---

## 附加上下文（如有）

```json
{json.dumps(result.get('extra', {}), ensure_ascii=False, indent=2)}
```

---

## 后续动作建议

- **missing_api_key**：检查 `.env` 中 `LLM_API_KEY`；本地建文件参考 README
- **reconcile_failed**：Forward Planner 输出缺 foreground_goal 或 relevant_known_info；
  补全场景 schema 字段或调整玩家初始 state
- **budget_exceeded**：超过 per-call 预算（默认 $0.50）；检查 `PER_CALL_BUDGET_USD` 环境变量
- **provider_error**：检查 API key / model 名 / 网络；relay 可能返回 4xx (auth / model_not_found)
"""


# ---------- CLI 入口 ----------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-3Y-1 mini prototype 端到端 dry-run")
    parser.add_argument(
        "--model-id",
        default=os.environ.get("LLM_MODEL", "gpt-5.5-pro"),
        help="LLM 模型 ID（默认从 LLM_MODEL env 拉，否则 gpt-5.5-pro）",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=REPO_ROOT / "docs" / "reviews" / "master_plan" / f"{date.today().isoformat()}_T-3Y-1_dry_run_report.md",
        help="markdown 实测报告输出路径",
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=REPO_ROOT / "docs" / "reviews" / "master_plan" / f"{date.today().isoformat()}_T-3Y-1_dry_run_output.json",
        help="完整 JSON 结果输出路径",
    )
    args = parser.parse_args(argv)

    result = run_pipeline(
        out_report_path=args.report_path,
        out_json_path=args.json_path,
        model_id=args.model_id,
    )

    print("=" * 60)
    print(f"STATUS: {result['status']}")
    print(f"Report: {args.report_path}")
    print(f"JSON:   {args.json_path}")
    print("=" * 60)
    if result["status"] == "success":
        meta = result["metadata"]
        rubric = result["rubric"]
        node = result["completed_node"]
        print(f"narration 字数: {len(node['narration'])}")
        print(f"options 数: {len(node['options'])}")
        print(f"input_tokens: {meta['input_tokens']}")
        print(f"output_tokens: {meta['output_tokens']}")
        print(f"actual_cost_usd: ${meta['actual_cost_usd']:.4f}")
        print(f"elapsed_sec_llm: {meta['elapsed_sec_llm']:.2f}s")
        print(f"elapsed_sec_total: {meta['elapsed_sec_total']:.2f}s")
        print(f"rubric.information_density: {rubric['information_density']['score']:.2f} / 10")
        print(f"rubric.baimiao_compliance: {rubric['baimiao_compliance']['score']:.2f} / 10")
        print(f"anti_pattern_flags: {len(result['anti_pattern_flags'])}")
        for f in result["anti_pattern_flags"]:
            print(f"  - {f['ap_id']} @ {f['location']}: {f['excerpt']}")
        return 0
    else:
        print(f"failure_reason: {result['failure_reason']}")
        print(f"detail: {result['detail']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
