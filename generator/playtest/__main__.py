"""``python -m generator.playtest`` entry point (T-3.4 / ADR-022)."""
import sys

from generator.playtest.cli import main

if __name__ == "__main__":
    sys.exit(main())
