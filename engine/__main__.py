"""`python -m engine <path-to-scene.json>` 入口。"""
from __future__ import annotations

import sys

from .player import play


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m engine <path-to-scene.json>", file=sys.stderr)
        return 1
    play(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
