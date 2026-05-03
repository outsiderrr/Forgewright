"""Scene-level prompt assets (T-2.5).

Made into a regular Python package so setuptools picks it up in the wheel
(packages list in pyproject.toml) — see critique 4.6. Submodules
(`system`, `few_shot`) are imported explicitly by callers; this `__init__`
intentionally exposes nothing so the subpackage stays a thin namespace.
"""
