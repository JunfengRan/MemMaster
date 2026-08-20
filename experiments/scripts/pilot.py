from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.scripts.compare import main as compare_main


def main() -> None:
    sys.argv = ["pilot.py", "--dev"]
    compare_main()


if __name__ == "__main__":
    main()
