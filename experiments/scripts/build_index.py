from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))

from datasets.tob_memory_v1_loader import corpus_root, ensure_corpus
from experiments.scripts.run_eval import build_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT / ".indexes" / "memmaster.sqlite"))
    args = parser.parse_args()
    ensure_corpus()
    build_index(Path(args.db), corpus_root())
    print(args.db)


if __name__ == "__main__":
    main()
