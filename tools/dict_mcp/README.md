# tools/dict_mcp/ — Forgewright D1 字典查询配置

> 本目录**仅放 Forgewright 项目特定的配置**。
> 通用的字典查询代码已剥离到独立开源 PyPI 包
> [`zh-dict-mcp`](https://github.com/outsiderrr/zh-dict-mcp)（由 Forgewright `pyproject.toml`
> 作为依赖引入）。

## 这里有什么

- `supplement_whitelist.yaml` —— Forgewright 项目级的 D1 字面直达**补丁白名单**。CC-CEDICT 漏收或释义不全的常用死比喻在此声明 pass。
- `d1_review_prompt.md` —— talkstyle-skill v0.1 D1 维度的 **review 端 prompt 模板**。供 generator pipeline / validator 集成时拼接到 LLM 提示词。

## 这里没有什么

字典查询代码、CC-CEDICT 原始数据、MCP server 实现——这些**全部在 [`zh-dict-mcp`](https://github.com/outsiderrr/zh-dict-mcp) 公开仓库**，不再 vendor 进本项目。

## 怎么用

### Python API（最直接）

```python
from pathlib import Path
from zh_dict_mcp import DictionaryLookup

WHITELIST = Path(__file__).parent / "supplement_whitelist.yaml"  # Forgewright 补丁
lookup = DictionaryLookup(whitelist_path=WHITELIST)

result = lookup.lookup("看见")
print(result.found, result.definitions, result.tags.is_neologism)
```

### MCP server (stdio) 启动（接 Claude Code / Desktop 等）

直接跑外部包的 entry point，可选传入本项目的补丁白名单：

```bash
uvx zh-dict-mcp --whitelist /abs/path/to/Forgewright/tools/dict_mcp/supplement_whitelist.yaml
```

或在 `.mcp.json` 配置：

```json
{
  "mcpServers": {
    "forgewright-d1-dict": {
      "command": "uvx",
      "args": [
        "zh-dict-mcp",
        "--whitelist",
        "/absolute/path/to/Forgewright/tools/dict_mcp/supplement_whitelist.yaml"
      ]
    }
  }
}
```

### D1 review prompt 集成

把 `d1_review_prompt.md` 内容作为 prompt fragment 拼进 generator / validator 的 review 流程。
具体接入位置见 generator pipeline 的现有 prompt 组织方式（参考 narration 层的
`generator/prompts/node/anti_pattern_blacklist.py` AP-1~AP-10 接入模式）。

## 升级 zh-dict-mcp

```bash
uv lock --upgrade-package zh-dict-mcp
uv sync
```

## 升级补丁白名单

直接编辑 `supplement_whitelist.yaml`，加新条目。重启 MCP server / 重导 `DictionaryLookup`
即生效（whitelist 不会热加载，要重新构造实例）。

## 评估测试集

39 case 验收测试集**已迁移到 zh-dict-mcp 公开仓库**
（[tests/test_lookup.py](https://github.com/outsiderrr/zh-dict-mcp/blob/master/tests/test_lookup.py)）。
Forgewright 不再维护自己的版本，避免重复。

如果将来本项目的补丁白名单累积到需要 acceptance test 验证它真的能修复
某些边界 case，可以在 Forgewright 这边新建测试，**单独**测白名单条目，
不重复测 CC-CEDICT 本身的覆盖。
