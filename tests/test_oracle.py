from experiments.scripts.oracle import oracle_check


def test_oracle_gate():
    from datasets.tob_memory_v1_loader import ensure_corpus

    ensure_corpus()
    report = oracle_check()
    assert report["ok"], report["failures"]
