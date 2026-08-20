from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))

from datasets.tob_memory_v1_loader import corpus_root, ensure_corpus
from memmaster import default_registry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="")
    args = parser.parse_args()
    ensure_corpus()
    registry = default_registry(corpus_root())
    ids = [args.source] if args.source else registry.ids()
    for sid in ids:
        adapter = registry.get(sid)
        docs, cursor = adapter.sync()
        print(sid, adapter.probe(), "docs", len(docs), "cursor", cursor.watermark)


if __name__ == "__main__":
    main()
