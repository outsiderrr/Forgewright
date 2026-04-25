"""Local pytest config for /generator/tests/.

Registers the `smoke` marker and skips smoke-marked tests by default.
Run them explicitly with `pytest -m smoke` (they hit real APIs and cost money).
"""

from __future__ import annotations

import pytest
from dotenv import load_dotenv

# Load repo-root .env so smoke tests can pick up GEMINI_API_KEY without the
# operator having to `export` it manually. Existing unit tests use monkeypatch
# to override env, so this is harmless to them.
load_dotenv()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "smoke: real-API smoke test (costs money); skipped unless `pytest -m smoke`",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    markexpr = config.getoption("-m", default="") or ""
    if "smoke" in markexpr:
        return
    skip_smoke = pytest.mark.skip(
        reason="smoke test (real API); run with `pytest -m smoke`"
    )
    for item in items:
        if "smoke" in item.keywords:
            item.add_marker(skip_smoke)
