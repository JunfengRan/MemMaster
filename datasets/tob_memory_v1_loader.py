from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "tob-memory-v1"


def corpus_root() -> Path:
    return DATASET / "corpus"


def ensure_corpus() -> Path:
    script = DATASET / "build_corpus.py"
    spec = importlib.util.spec_from_file_location("build_corpus", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    mod.build()
    return corpus_root()
