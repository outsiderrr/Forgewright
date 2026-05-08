"""Playtest bots framework (T-3.4 / ADR-022).

Develop-time only: simulates N=5 personas × M=20 paths per scene, scores
each path with an LLM-as-judge, ranks worst-10% paths and aggregates a
worst-10% scene list. The framework's three contracts:

  1. **calibration mandatory** — :func:`cli.run_calibration` exposes a
     1 scene × 1 persona × 5 paths smoke that records avg
     calls/path / cost/path / seconds/path before any full batch runs.
     ADR-022 / F9: never run 5×20 blind.
  2. **three-way budget guard** — every full batch enforces
     ``--max-cost-usd`` / ``--max-calls`` / ``--max-wall-clock-min``;
     any trip aborts the batch + flushes partial output (F9).
  3. **critical/major/minor severity taxonomy** — judge prompt names
     the three severities; ``critical`` is author-confirmed, never
     auto-passed by the LLM judge (F10).

Outputs land at ``/generator/experiments/playtest_NNN/`` with the
two-tier writeout (``worst_paths.jsonl`` + ``worst_scenes.{md,json}``;
F21) and a ``run_manifest.json`` that records model/temp/prompt-hash
/persona-hash/judge-rubric-version + calibration data for replay (F20).

Cost log: ``/generator/playtest_cost_log.jsonl`` (sibling-but-distinct
from ``cost_log.jsonl``; ADR-012 same shape).

Module boundary (T-3.4): adds nothing to /schema/, /state/, /engine/,
/validator/, /content/, /docs/, or main /generator/*.py business
files. Read-only on the world ontology.
"""

from generator.playtest.personas import Persona, load_persona, load_all_personas

__all__ = [
    "Persona",
    "load_persona",
    "load_all_personas",
]
