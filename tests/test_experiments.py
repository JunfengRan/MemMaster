from pathlib import Path

from datasets.tob_memory_v1_loader import corpus_root, ensure_corpus
from experiments import ROOT, load_config, load_questions
from experiments.scripts.run_eval import build_index, run_group
from memmaster.engine import MemoryEngine


def test_blank_vs_hybrid(tmp_path: Path):
    ensure_corpus()
    store = build_index(tmp_path / "db.sqlite", corpus_root())
    engine = MemoryEngine(store)
    items = load_questions(False)
    e0 = run_group(load_config(ROOT / "experiments" / "configs" / "E0.yaml"), items, engine, "t")
    e2 = run_group(load_config(ROOT / "experiments" / "configs" / "E2.yaml"), items, engine, "t")
    s0 = sum(1 for r in e0 if r["answer"] not in {"UNKNOWN", "FAIL_BUDGET"})
    s2 = sum(1 for r in e2 if r["answer"] not in {"UNKNOWN", "FAIL_BUDGET"})
    assert s0 < 8, s0
    assert s2 >= 12, (s2, [r["question_id"] for r in e2 if r["answer"] in {"UNKNOWN", "FAIL_BUDGET"}])
