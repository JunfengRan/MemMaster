from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))
from memmaster.facts import extract_regex_facts
from memmaster.store import Store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(Path(__file__).resolve().parents[2] / ".indexes" / "memmaster.sqlite"))
    args = parser.parse_args()
    store = Store(Path(args.db))
    n = extract_regex_facts(store)
    print("extracted", n)


if __name__ == "__main__":
    main()
