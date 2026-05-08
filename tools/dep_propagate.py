"""T-3.7 一致性维护：基于 ContentDependencyIndex sidecar 反向 propagate（ADR-023 / F5）。

# 设计要点

ROADMAP §阶段 3 完成标志要求"本体变更时定向反向 propagate（标记需重审的已生成内容）"，
ADR-023 决策 sidecar 形态 = `<scene>.deps.json`（与 scene.json 同目录）；写入语义是
**context assembly over-approx trace**——不是 scene 反查。本工具的角色是**消费侧**：

1. 扫描 `content_root` 下所有 `*.deps.json` sidecar（schema 见
   `/schema/content_dependency_index.schema.json`）。
2. 对每个 sidecar 检查其声明的 ontology / state / visual / clock 依赖是否与
   "本次声明发生变更" 的输入集合相交。
3. 命中即标 stale；输出 markdown + JSON report 供作者重审。

写入侧（T-3.5 batch_scheduler）已经做了 conservative over-approx，反向查询保持
**精确集合相交**——叠加 over-approx 会造成误报次数级膨胀（T-3.7 范围里宁愿做"快但
准"，over-approx 责任由 trace 写入侧承担）。唯一例外是 state path 的父子关系命中
（见 `_state_path_intersect`）：作者经常只改某 namespace 的子树（如
`faction.iron_oath.*`），这种 prefix 匹配是常见使用方式，按字面相交就漏报了。

# 模块边界（CLAUDE.md 规则 2 / T-3.7 prompt §模块边界）

- 本模块**只读** sidecar / scene.json / ontology JSON。
- 不调用 LLM、不修改 stale 场景内容（见 T-3.7 §不要做的事）。
- 不导入 `/generator` / `/validator`（解耦工具层）。
- 本体加载用本模块自带轻量 loader（不依赖 `state.ontology._load_all`，因为后者全局
  缓存 + 路径硬编码 `/state/ontology/`，对测试 / 多 world 不友好）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_CONTENT_ROOT = Path("content")
DEFAULT_ONTOLOGY_ROOT = Path("state/ontology")

#: stale report 自身 schema 版本（与 sidecar schema 解耦；report 仅供 review_ui /
#: CLI 消费，不是入库 artifact）。版本变更时同步 review_ui 接入侧。
REPORT_SCHEMA_VERSION = "0.1.0"

#: 优先级数值映射（小 = 高）。来源 ADR-016 character.relations[].narrative_weight
#: 取值 = "core" / "minor"；"context_only" 是本工具兜底（ontology 实体无 relations
#: 时 fallback 项；state path / visual / clock reason 也回到 context_only）。
_PRIORITY_RANK = {"core": 0, "minor": 1, "context_only": 2}

#: 反向命中时填到 StaleReason.kind 的值（review_ui 集成侧按 kind 分组渲染）。
REASON_KIND_ONTOLOGY_ID = "ontology_id"
REASON_KIND_STATE_PATH = "state_path"
REASON_KIND_VISUAL_ASSET = "visual_asset"
REASON_KIND_CLOCK = "clock"


# ---------------------------------------------------------------------------
# dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StaleReason:
    """命中详情：哪类依赖（kind）的哪个 id（value）触发了 stale 标记。"""

    kind: str
    value: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "value": self.value}


@dataclass
class StaleScene:
    """T-3.7 prompt §DP-1 §2 指定 dataclass：scene_id / scene_path / deps_path /
    reasons；本工具额外加 priority 字段（DP-3 §8 排序键）。"""

    scene_id: str
    scene_path: Path
    deps_path: Path
    reasons: list[StaleReason] = field(default_factory=list)
    priority: str = "context_only"

    def to_dict(self, content_root: Optional[Path] = None) -> dict:
        """JSON 输出（DP-4）。content_root 给定时 path 输出相对路径，便于跨机器复用。"""

        def _format_path(p: Path) -> str:
            if content_root is None:
                return str(p)
            try:
                return str(p.resolve().relative_to(content_root.resolve()))
            except ValueError:
                return str(p)

        return {
            "scene_id": self.scene_id,
            "scene_path": _format_path(self.scene_path),
            "deps_path": _format_path(self.deps_path),
            "priority": self.priority,
            "reasons": [r.to_dict() for r in self.reasons],
        }


@dataclass
class ChangedOntology:
    """DP-2 helper 返回值：粗粒度 ontology diff 结果。"""

    changed_ontology_ids: list[str] = field(default_factory=list)
    changed_state_paths: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DP-1 核心：反向查询
# ---------------------------------------------------------------------------

def _normalize_changed_path(path: str) -> str:
    """C-phase fix（B-review §3.1 🔴）：把"namespace 通配"形态归一到字面 prefix。

    CLI help / docstring 一直把 `faction.iron_oath.*` 作为常见输入示意（"改了某个
    namespace 子树"），但字面 `.*` 只是约定俗成的 ASCII 标记——后续 prefix 匹配是
    `ch + "."` 字面拼接，输入 `faction.iron_oath.*` 时算出来的前缀变成
    `faction.iron_oath.*.`，永远不会命中真实路径 `faction.iron_oath.reputation`。

    做法：归一化到去尾 `.*` 的"父 path"形态——后续 `ref.startswith(ch + ".")`
    分支会自然命中所有子路径。也兼容 `*` 单独项（兜底为空字符串，等价于"任意
    state path 都命中"，但这种用法极不寻常；不需要在反向 propagate 工具内特殊
    处理通配符 catch-all——作者真要"全标 stale"会直接传 broader inputs）。
    """
    if path.endswith(".*"):
        return path[:-2]
    return path


def _state_path_intersect(changed: Iterable[str], referenced: Iterable[str]) -> list[str]:
    """state path 命中检查（双向 prefix 匹配 + namespace 通配归一）。

    返回 sidecar 中被命中的 path 集合（用作 reason 渲染——给作者看的是 sidecar
    侧的具体路径，便于 grep 定位）。

    匹配规则：path A 命中 path B（任一方向） ⇔
    - A == B（精确相等）
    - A 是 B 的祖先（B 以 A + "." 开头）：作者改了 `faction.iron_oath`，
      sidecar 引用 `faction.iron_oath.reputation` → 命中
    - B 是 A 的祖先（A 以 B + "." 开头）：作者改了 `faction.iron_oath.reputation`，
      sidecar 引用 `faction.iron_oath`（schema 实际拒收裸 namespace；保留方向
      性是为给 sidecar schema 演进留口子）→ 命中

    输入端 `.*` 尾缀（如 `faction.iron_oath.*`，CLI help 暗示的常见用法）由
    `_normalize_changed_path` 归一到 `faction.iron_oath` 后再走前缀匹配——B
    阶段评审 §3.1 修订（避免静默 false negative，违背 ADR-023/F5
    "宁可误报 stale 也不漏依赖"目标）。
    """
    changed_set = {_normalize_changed_path(c) for c in changed}
    hits: list[str] = []
    for ref in referenced:
        for ch in changed_set:
            if ref == ch or ref.startswith(ch + ".") or ch.startswith(ref + "."):
                hits.append(ref)
                break
    return hits


def _load_sidecar(deps_path: Path) -> Optional[dict]:
    """读 sidecar；JSON 解析失败返回 None（DP-1 实现层稳健性——畸形 sidecar 不阻断
    其他正常 sidecar 的扫描；记录 stderr 警告便于作者排查）。"""
    try:
        return json.loads(deps_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[dep_propagate] WARN failed to read sidecar {deps_path}: {exc}", file=sys.stderr)
        return None


def _list_field(sidecar: dict, deps_path: Path, key: str) -> Optional[list[str]]:
    """C-phase fix（B-review §4.2 🟡）：sidecar 字段类型 guard。

    sidecar schema（content_dependency_index.schema.json）声明字段必须是
    `array of string`、optional 字段走 missing-only（schema 拒收 null），但本工具
    的设计哲学是"宁可宽松也不阻断"——遇到不合规 sidecar（例如 generator bug 把
    optional 字段写成 null，或人工编辑 sidecar 时把 array 写成 object）时，**单个
    sidecar skip + 全局扫描继续**，不能让一颗坏 sidecar 拖垮整批 stale report。

    返回值语义：
    - key 缺失（合法 missing-only）→ 空 list（"该 sidecar 没有此类引用"）
    - key 存在但不是 list / list 元素不是 str → 返回 None（标记 sidecar 整体 skip）
    """
    if key not in sidecar:
        return []
    value = sidecar[key]
    if not isinstance(value, list):
        print(
            f"[dep_propagate] WARN sidecar {deps_path}: field {key!r} expected list, got "
            f"{type(value).__name__}; skipping sidecar",
            file=sys.stderr,
        )
        return None
    if not all(isinstance(item, str) for item in value):
        print(
            f"[dep_propagate] WARN sidecar {deps_path}: field {key!r} contains non-string item; "
            f"skipping sidecar",
            file=sys.stderr,
        )
        return None
    return list(value)


def _resolve_scene_path(deps_path: Path) -> Path:
    """`<scene>.deps.json` → `<scene>.json`（ADR-023 / STAGE_3_TASKS §2.4 文件名约定）。"""
    name = deps_path.name
    if name.endswith(".deps.json"):
        scene_name = name[: -len(".deps.json")] + ".json"
    else:
        scene_name = name + ".scene.json"
    return deps_path.parent / scene_name


def find_stale_scenes(
    changed_ontology_ids: Optional[list[str]] = None,
    changed_state_paths: Optional[list[str]] = None,
    changed_visual_assets: Optional[list[str]] = None,
    changed_clocks: Optional[list[str]] = None,
    content_root: Path = DEFAULT_CONTENT_ROOT,
    ontology_root: Path = DEFAULT_ONTOLOGY_ROOT,
) -> list[StaleScene]:
    """反向 propagate（ADR-023 / F5）：扫描 content_root 下所有 `<scene>.deps.json`
    sidecar，返回依赖与"changed"输入集相交的场景列表。

    Conservative over-approx 由**写入侧**（T-3.5 trace 累加器）承担；本函数对 trace
    做精确集合相交（state path 双向 prefix 匹配是唯一例外，见 `_state_path_intersect`）。

    参数全部 None / 空 list → 返回空列表（"没有任何变更"语义）。
    """

    changed_ontology_ids = list(changed_ontology_ids or [])
    changed_state_paths = list(changed_state_paths or [])
    changed_visual_assets = list(changed_visual_assets or [])
    changed_clocks = list(changed_clocks or [])

    if not any([changed_ontology_ids, changed_state_paths, changed_visual_assets, changed_clocks]):
        return []

    if not content_root.exists():
        return []

    ontology_index = _load_ontology_entities(ontology_root)
    changed_ontology_set = set(changed_ontology_ids)
    changed_visual_set = set(changed_visual_assets)
    changed_clock_set = set(changed_clocks)

    results: list[StaleScene] = []

    for deps_path in sorted(content_root.rglob("*.deps.json")):
        sidecar = _load_sidecar(deps_path)
        if sidecar is None:
            continue
        if not isinstance(sidecar, dict):
            print(
                f"[dep_propagate] WARN sidecar {deps_path}: expected JSON object, got "
                f"{type(sidecar).__name__}; skipping sidecar",
                file=sys.stderr,
            )
            continue

        ontology_ids_read = _list_field(sidecar, deps_path, "ontology_ids_read")
        state_paths_read = _list_field(sidecar, deps_path, "state_paths_read")
        state_paths_written = _list_field(sidecar, deps_path, "state_paths_written")
        visual_asset_ids = _list_field(sidecar, deps_path, "visual_asset_ids_referenced")
        clock_ids = _list_field(sidecar, deps_path, "clock_ids_referenced")
        if any(
            field is None
            for field in (
                ontology_ids_read,
                state_paths_read,
                state_paths_written,
                visual_asset_ids,
                clock_ids,
            )
        ):
            continue

        reasons: list[StaleReason] = []

        ontology_hits = changed_ontology_set & set(ontology_ids_read or [])
        for hit in sorted(ontology_hits):
            reasons.append(StaleReason(REASON_KIND_ONTOLOGY_ID, hit))

        sidecar_state_paths = list(state_paths_read or []) + list(state_paths_written or [])
        state_hits = _state_path_intersect(changed_state_paths, sidecar_state_paths)
        for hit in sorted(set(state_hits)):
            reasons.append(StaleReason(REASON_KIND_STATE_PATH, hit))

        visual_hits = changed_visual_set & set(visual_asset_ids or [])
        for hit in sorted(visual_hits):
            reasons.append(StaleReason(REASON_KIND_VISUAL_ASSET, hit))

        clock_hits = changed_clock_set & set(clock_ids or [])
        for hit in sorted(clock_hits):
            reasons.append(StaleReason(REASON_KIND_CLOCK, hit))

        if not reasons:
            continue

        scene_id_raw = sidecar.get("scene_id", deps_path.stem.replace(".deps", ""))
        scene_id = str(scene_id_raw) if not isinstance(scene_id_raw, str) else scene_id_raw
        scene_path = _resolve_scene_path(deps_path)
        priority = _derive_priority(ontology_hits, ontology_index)

        results.append(
            StaleScene(
                scene_id=scene_id,
                scene_path=scene_path,
                deps_path=deps_path,
                reasons=reasons,
                priority=priority,
            )
        )

    results.sort(key=lambda s: (_PRIORITY_RANK.get(s.priority, 99), s.scene_id))
    return results


def _derive_priority(
    ontology_hits: Iterable[str],
    ontology_index: dict[str, dict],
) -> str:
    """从命中的 ontology entity 的 `relations[].narrative_weight` 取最大值。

    ADR-016 character schema 中只有 `relations[].narrative_weight`（取值 core /
    minor），character / location 实体本身没有顶层 weight 字段。state path /
    visual / clock 命中无关 narrative_weight，priority 兜底 `context_only`
    （T-3.7 prompt §DP-3 §8 排序对齐）。
    """
    best = "context_only"
    for entity_id in ontology_hits:
        entity = ontology_index.get(entity_id)
        if entity is None:
            continue
        for relation in entity.get("relations", []) or []:
            weight = relation.get("narrative_weight")
            if not weight:
                continue
            if _PRIORITY_RANK.get(weight, 99) < _PRIORITY_RANK.get(best, 99):
                best = weight
    return best


def _load_ontology_entities(ontology_root: Path) -> dict[str, dict]:
    """轻量 ontology loader：扫描 `ontology_root/*.json`，返回 `{id: entity}`。

    与 `state.ontology._load_all` 同源算法（同样的 entities 数组遍历），但去掉全局
    cache + 支持任意 ontology_root 参数（用于测试 / 多 world / forgewright-framework
    剥离时复用）。重复 id 取第一个（与 `state.ontology` 抛错语义不同：propagate 工具
    宁可宽松也不阻断；duplicate 由作者通过 ontology validator 治理）。"""
    if not ontology_root.exists() or not ontology_root.is_dir():
        return {}
    index: dict[str, dict] = {}
    for json_file in sorted(ontology_root.glob("*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entity in payload.get("entities", []) or []:
            entity_id = entity.get("id")
            if not entity_id or entity_id in index:
                continue
            index[entity_id] = entity
    return index


# ---------------------------------------------------------------------------
# DP-2 helper：本体 git diff 检测（粗粒度）
# ---------------------------------------------------------------------------

def diff_ontology(
    ontology_path: Path,
    since_commit: str,
    repo_root: Optional[Path] = None,
) -> ChangedOntology:
    """从 since_commit 到工作树（含未提交改动）做粗粒度 ontology entity diff。

    实现：取**工作树文件 ∪ since_commit 文件**两侧 union（C-phase fix B-review §4.1
    🟡）——只看工作树会漏掉删除/重命名，pre-commit hook `--since HEAD` 路径要求
    "ontology 删除也算变更"。每个文件分别 `git show <since_commit>:<rel_path>`
    加载 OLD payload + 工作树读 NEW payload；按 `id` 比较 entity 字典，凡有任意
    字段不一致（含 OLD 存在 NEW 不存在 = 删除）即标 changed。粒度"实体级"——
    命中 ontology_ids，state_paths 仅在 `state_path_slug` 漂移时粗粒度回填
    （当前 character entity 的 slug 漂移可能导致 `relationship.<slug>.*` 路径全部
    失效，回填两侧 slug）。

    生产期 propagate 报告的设计哲学："偏宽松好于偏紧"——T-3.7 prompt §DP-2 §6
    明示。

    参数：
    - ontology_path：ontology 目录或单文件（目录 → 扫描下属所有 .json + since
      tree 同目录下的 .json union）。
    - since_commit：git revision（commit / branch / HEAD~N 等）。
    - repo_root：git repo 根目录（默认推断为 ontology_path 上溯到含 `.git/` 目录的
      最近祖先）。

    failure modes：since_commit 不存在 / git 不可用 → 抛 `RuntimeError`；OLD
    payload 解析失败 → 视作"全 entity 都是新增/变更"返回当前全集（写入侧已
    over-approx 不漏依赖）。
    """
    repo_root = repo_root or _find_git_root(ontology_path)
    files = _ontology_files_to_diff(ontology_path, repo_root, since_commit)

    changed_ids: set[str] = set()
    changed_paths: set[str] = set()

    for f in files:
        old_text = _git_show(repo_root, since_commit, f)

        new_payload: Optional[dict] = None
        if f.exists():
            try:
                new_payload = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                new_payload = None

        if new_payload is None and old_text is None:
            continue

        if new_payload is None:
            try:
                old_payload = json.loads(old_text or "")
            except json.JSONDecodeError:
                continue
            for entity in old_payload.get("entities", []) or []:
                if eid := entity.get("id"):
                    changed_ids.add(eid)
                if slug := entity.get("state_path_slug"):
                    changed_paths.add(f"relationship.{slug}")
            continue

        if old_text is None:
            for entity in new_payload.get("entities", []) or []:
                if eid := entity.get("id"):
                    changed_ids.add(eid)
                if slug := entity.get("state_path_slug"):
                    changed_paths.add(f"relationship.{slug}")
            continue

        try:
            old_payload = json.loads(old_text)
        except json.JSONDecodeError:
            for entity in new_payload.get("entities", []) or []:
                if eid := entity.get("id"):
                    changed_ids.add(eid)
            continue

        old_entities = {e.get("id"): e for e in (old_payload.get("entities", []) or []) if e.get("id")}
        new_entities = {e.get("id"): e for e in (new_payload.get("entities", []) or []) if e.get("id")}

        for entity_id in set(old_entities) | set(new_entities):
            old_entity = old_entities.get(entity_id)
            new_entity = new_entities.get(entity_id)
            if old_entity != new_entity:
                changed_ids.add(entity_id)
                old_slug = (old_entity or {}).get("state_path_slug")
                new_slug = (new_entity or {}).get("state_path_slug")
                if old_slug:
                    changed_paths.add(f"relationship.{old_slug}")
                if new_slug and new_slug != old_slug:
                    changed_paths.add(f"relationship.{new_slug}")

    return ChangedOntology(
        changed_ontology_ids=sorted(changed_ids),
        changed_state_paths=sorted(changed_paths),
    )


def _ontology_files_to_diff(
    ontology_path: Path,
    repo_root: Path,
    since_commit: str,
) -> list[Path]:
    """C-phase fix（B-review §4.1 🟡）：取"工作树 .json" ∪ "since_commit 树下同目录
    .json"，包含被删除/重命名的旧文件。

    单文件输入只看该文件本身（即使工作树已删除，也用 commit 树里同名 path 重建
    abs path——`git show <rev>:<path>` 仍可读）。

    目录输入扫两侧：
    - 工作树 `<dir>/*.json`（rglob 用 glob，不递归——保持与原行为一致）
    - `git ls-tree <since_commit> -- <rel_dir>/` 列出该目录下 .json 文件
    """
    if ontology_path.is_file():
        return [ontology_path]

    candidates: set[Path] = set()
    if ontology_path.is_dir():
        candidates.update(ontology_path.glob("*.json"))

    try:
        rel_dir = ontology_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel_dir = None

    if rel_dir is not None:
        env = {"LC_ALL": "C", "LANG": "C", "PATH": _safe_path_env()}
        try:
            proc = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "ls-tree",
                    "--name-only",
                    since_commit,
                    f"{rel_dir.as_posix()}/",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("git executable not found; install git or pass --changed-* manually") from exc

        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line.endswith(".json"):
                    continue
                candidates.add((repo_root / line).resolve())
        else:
            stderr = proc.stderr or ""
            if not (
                "Not a valid object name" in stderr
                or "fatal: bad revision" in stderr
                or "unknown revision" in stderr
                or "exists on disk" in stderr
                or "does not exist" in stderr
            ):
                pass  # 目录不存在于 since_commit 时 ls-tree 返回空 + 0；非零 + 未识别字符串保守忽略

    return sorted(candidates)


def _find_git_root(start: Path) -> Path:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def _git_show(repo_root: Path, revision: str, file_path: Path) -> Optional[str]:
    """`git show <rev>:<rel>`；revision 不含此文件返回 None（新增文件场景）。

    强制 `LC_ALL=C` 让 git stderr 走英文，避免不同 locale（如 zh_CN 翻译"致命错误"）
    破坏 stderr 的字面匹配。失败语义：
    - bad revision / 仓库结构问题（exit 128 + "invalid object" / "unknown revision"）
      → RuntimeError（让上层 CLI 报错退出码 2 给作者排查）
    - 路径在该 revision 下不存在 / 文件未追踪（exit 128 + "does not exist in" /
      "exists on disk, but not in"）→ 返回 None（视作"新文件"，diff 侧视当前全集为
      新增）
    - 其他非零退出 → 保守 RuntimeError（与"无声 swallow"相比，作者可见性更高）
    """
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    env = {"LC_ALL": "C", "LANG": "C", "PATH": _safe_path_env()}
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{revision}:{rel.as_posix()}"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found; install git or pass --changed-* manually") from exc

    if proc.returncode == 0:
        return proc.stdout

    stderr = proc.stderr or ""
    if "does not exist in" in stderr or "exists on disk, but not in" in stderr:
        return None
    raise RuntimeError(
        f"git show {revision}:{rel} failed (exit {proc.returncode}): "
        f"{stderr.strip() or 'unknown error'}"
    )


def _safe_path_env() -> str:
    """保留系统 PATH（git 可能装在 /usr/bin / /opt/homebrew/bin 等位置）；构造
    minimal env 避免父进程意外环境变量污染 git CLI 输出格式。"""
    import os

    return os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin")


# ---------------------------------------------------------------------------
# DP-3 / DP-4：CLI 入口 + markdown / JSON writers
# ---------------------------------------------------------------------------

def render_markdown_report(
    stale: list[StaleScene],
    inputs: dict,
    content_root: Path,
) -> str:
    """T-3.7 prompt §DP-3 §8：markdown report 含 stale scenes 列表 + 每场景 reasons +
    suggested 重审优先级（按 narrative_weight 排序）。

    输出语义：作者扫一眼就知道"改了什么 → 哪些场景需重审 → 先看哪几个"。优先级分组
    用 H2 / 场景用 H3，每场景 reason 用 bullet，命中类型用前缀 emoji（视觉优先级，
    review_ui 集成时复用同样的颜色映射 - core 红 / minor 黄 / context_only 灰）。
    """
    lines: list[str] = []
    lines.append("# Stale Scenes Report")
    lines.append("")
    lines.append(f"_Generated_: {_iso_now()}")
    lines.append(f"_Tool_: `tools.dep_propagate` (T-3.7 / ADR-023 reverse propagate)")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- `since_commit`: `{inputs.get('since_commit') or '—'}`")
    lines.append(
        f"- `changed_ontology_ids` ({len(inputs.get('changed_ontology_ids') or []):d}): "
        f"`{', '.join(inputs.get('changed_ontology_ids') or []) or '—'}`"
    )
    lines.append(
        f"- `changed_state_paths` ({len(inputs.get('changed_state_paths') or []):d}): "
        f"`{', '.join(inputs.get('changed_state_paths') or []) or '—'}`"
    )
    lines.append(
        f"- `changed_visual_assets` ({len(inputs.get('changed_visual_assets') or []):d}): "
        f"`{', '.join(inputs.get('changed_visual_assets') or []) or '—'}`"
    )
    lines.append(
        f"- `changed_clocks` ({len(inputs.get('changed_clocks') or []):d}): "
        f"`{', '.join(inputs.get('changed_clocks') or []) or '—'}`"
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Stale scenes: **{len(stale)}**")
    counts = {p: 0 for p in _PRIORITY_RANK}
    for s in stale:
        counts[s.priority] = counts.get(s.priority, 0) + 1
    lines.append(
        f"- By priority: core = {counts.get('core', 0)}, "
        f"minor = {counts.get('minor', 0)}, "
        f"context_only = {counts.get('context_only', 0)}"
    )
    lines.append("")

    if not stale:
        lines.append("No stale scenes detected. ✅")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Stale Scenes")
    lines.append("")
    lines.append("> Sorted by priority (core > minor > context_only). Re-review high-priority first.")
    lines.append("")

    last_priority: Optional[str] = None
    for idx, scene in enumerate(stale, start=1):
        if scene.priority != last_priority:
            lines.append(f"### Priority: {scene.priority}")
            lines.append("")
            last_priority = scene.priority

        scene_path = _format_path_relative(scene.scene_path, content_root)
        deps_path = _format_path_relative(scene.deps_path, content_root)
        lines.append(f"#### {idx}. `{scene.scene_id}`")
        lines.append("")
        lines.append(f"- Scene: `{scene_path}`")
        lines.append(f"- Sidecar: `{deps_path}`")
        lines.append(f"- Reasons:")
        for reason in scene.reasons:
            lines.append(f"  - {_REASON_PREFIX.get(reason.kind, '·')} `{reason.kind}` → `{reason.value}`")
        lines.append("")

    return "\n".join(lines)


_REASON_PREFIX = {
    REASON_KIND_ONTOLOGY_ID: "🧬",
    REASON_KIND_STATE_PATH: "🔧",
    REASON_KIND_VISUAL_ASSET: "🖼",
    REASON_KIND_CLOCK: "⏱",
}


def render_json_report(
    stale: list[StaleScene],
    inputs: dict,
    content_root: Path,
) -> dict:
    """T-3.7 prompt §DP-4：与 review_ui 兼容的 JSON 输出形态。

    schema 形态稳定承诺：T-3.6b stale 面板将订阅本字段集（schema_version =
    REPORT_SCHEMA_VERSION，目前 0.1.0）。增字段不破坏；删字段或改语义须同步 bump
    REPORT_SCHEMA_VERSION + review_ui 切换 minimum-supported。
    """
    counts = {p: 0 for p in _PRIORITY_RANK}
    for s in stale:
        counts[s.priority] = counts.get(s.priority, 0) + 1

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": _iso_now(),
        "tool": "tools.dep_propagate",
        "inputs": {
            "since_commit": inputs.get("since_commit"),
            "changed_ontology_ids": list(inputs.get("changed_ontology_ids") or []),
            "changed_state_paths": list(inputs.get("changed_state_paths") or []),
            "changed_visual_assets": list(inputs.get("changed_visual_assets") or []),
            "changed_clocks": list(inputs.get("changed_clocks") or []),
            "content_root": str(content_root),
        },
        "summary": {
            "total_stale": len(stale),
            "by_priority": counts,
        },
        "stale_scenes": [s.to_dict(content_root=content_root) for s in stale],
    }


def _format_path_relative(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(p)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [piece.strip() for piece in value.split(",") if piece.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.dep_propagate",
        description=(
            "Reverse-propagate ontology / state / visual / clock changes to scene "
            "dep_index sidecars and emit a stale-review report (T-3.7 / ADR-023)."
        ),
    )
    parser.add_argument(
        "--since",
        metavar="COMMIT",
        help="Run git diff_ontology against this revision; merges with --changed-ontology.",
    )
    parser.add_argument(
        "--changed-ontology",
        metavar="IDS",
        help="Comma-separated ontology entity ids that changed (e.g. char_vellin,loc_x).",
    )
    parser.add_argument(
        "--changed-state-paths",
        metavar="PATHS",
        help="Comma-separated ADR-016 state paths (e.g. world.scene_count,faction.iron_oath.*).",
    )
    parser.add_argument(
        "--changed-visual-assets",
        metavar="IDS",
        help="Comma-separated ImageAsset.asset_id values that changed.",
    )
    parser.add_argument(
        "--changed-clocks",
        metavar="IDS",
        help="Comma-separated clock ids that changed.",
    )
    parser.add_argument(
        "--content-root",
        type=Path,
        default=DEFAULT_CONTENT_ROOT,
        help=f"Root containing scene/*.deps.json sidecars (default {DEFAULT_CONTENT_ROOT}).",
    )
    parser.add_argument(
        "--ontology-root",
        type=Path,
        default=DEFAULT_ONTOLOGY_ROOT,
        help=f"Ontology directory used for priority derivation (default {DEFAULT_ONTOLOGY_ROOT}).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        metavar="PATH",
        help="Write markdown report to PATH (otherwise printed to stdout).",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        type=Path,
        metavar="PATH",
        help="Write JSON report to PATH (review_ui-compatible).",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with code 1 if any stale scene is found (CI-friendly).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    explicit_ontology = _split_csv(args.changed_ontology)
    explicit_state_paths = _split_csv(args.changed_state_paths)
    changed_visual_assets = _split_csv(args.changed_visual_assets)
    changed_clocks = _split_csv(args.changed_clocks)

    diff_ontology_ids: list[str] = []
    diff_state_paths: list[str] = []
    if args.since:
        try:
            diff = diff_ontology(args.ontology_root, args.since)
        except RuntimeError as exc:
            print(f"[dep_propagate] ERROR --since failed: {exc}", file=sys.stderr)
            return 2
        diff_ontology_ids = diff.changed_ontology_ids
        diff_state_paths = diff.changed_state_paths

    changed_ontology_ids = sorted(set(explicit_ontology) | set(diff_ontology_ids))
    changed_state_paths = sorted(set(explicit_state_paths) | set(diff_state_paths))

    stale = find_stale_scenes(
        changed_ontology_ids=changed_ontology_ids,
        changed_state_paths=changed_state_paths,
        changed_visual_assets=changed_visual_assets,
        changed_clocks=changed_clocks,
        content_root=args.content_root,
        ontology_root=args.ontology_root,
    )

    inputs_meta = {
        "since_commit": args.since,
        "changed_ontology_ids": changed_ontology_ids,
        "changed_state_paths": changed_state_paths,
        "changed_visual_assets": changed_visual_assets,
        "changed_clocks": changed_clocks,
    }

    markdown = render_markdown_report(stale, inputs_meta, args.content_root)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
        if not markdown.endswith("\n"):
            sys.stdout.write("\n")

    if args.json_out:
        payload = render_json_report(stale, inputs_meta, args.content_root)
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.exit_code and stale:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
