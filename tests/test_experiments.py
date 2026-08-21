from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))
sys.path.insert(0, str(ROOT))

from datasets.tob_memory_v1_loader import corpus_root, ensure_corpus
from experiments import ROOT, load_config, load_questions
from experiments.scripts.run_eval import build_index, run_group_oracle
from experiments.scripts.score import rank_key, rank_groups
from memmaster.engine import MemoryEngine
from memmaster.models import SearchRequest


def test_oracle_ceiling_not_agent_protocol(tmp_path: Path):
    ensure_corpus()
    store = build_index(tmp_path / "db.sqlite", corpus_root())
    engine = MemoryEngine(store)
    items = load_questions(False)
    e0 = run_group_oracle(load_config(ROOT / "experiments" / "configs" / "E0.yaml"), items, engine, "t")
    e2 = run_group_oracle(load_config(ROOT / "experiments" / "configs" / "E2.yaml"), items, engine, "t")
    s0 = sum(1 for r in e0 if r["answer"] not in {"UNKNOWN", "FAIL_BUDGET"})
    s2 = sum(1 for r in e2 if r["answer"] not in {"UNKNOWN", "FAIL_BUDGET"})
    assert s0 < 8, s0
    assert s2 >= 12, (s2, [r["question_id"] for r in e2 if r["answer"] in {"UNKNOWN", "FAIL_BUDGET"}])
    assert all(r["backend"] == "oracle-ceiling" for r in e0 + e2)


def test_source_filter_isolates_corpus(tmp_path: Path):
    ensure_corpus()
    store = build_index(tmp_path / "db.sqlite", corpus_root())
    engine = MemoryEngine(store)
    mail = engine.search(SearchRequest(query="OceanStor", methods=["lexical"], source_id="mail"))
    web = engine.search(SearchRequest(query="OceanStor", methods=["lexical"], source_id="web"))
    assert mail.hits
    assert all(h.source_id == "mail" for h in mail.hits)
    assert all(h.source_id == "web" for h in web.hits)


def test_cost_outlier_needs_extra_calls_not_one_more():
    from experiments.scripts.score import apply_cost_outliers

    def row(gid, q, tools, tok, ms, ok=True):
        return {
            "group": gid,
            "question_id": q,
            "success": ok,
            "fact_success": ok,
            "memory_calls": tools,
            "context_tokens": tok,
            "duration_ms": ms,
            "constraint_fail": False,
            "infra_failure": False,
            "source": "mail",
            "type": "exact",
        }

    scored = [
        row("E0", "Q01", 0, 200, 1000, False),
        row("E2", "Q01", 2, 3000, 7000),
        row("E3", "Q01", 3, 3200, 7200),
        row("E4", "Q01", 2, 3100, 7100),
        row("E5", "Q01", 2, 3050, 7050),
        row("E6", "Q01", 2, 3000, 7000),
        row("E7", "Q01", 2, 2900, 6900),
        row("E8", "Q01", 8, 9000, 20000),
        row("E9", "Q01", 2, 3010, 7010),
    ]
    apply_cost_outliers(scored)
    by = {r["group"]: r for r in scored}
    assert by["E3"]["success"] is True
    assert by["E8"]["cost_fail"] is True
    assert by["E8"]["success"] is False
    assert by["E0"]["cost_fail"] is False


def test_lexicographic_rank_prefers_success_then_cheaper():
    summary = {
        "A": {"task_success": 0.8, "avg_context_tokens": 100, "avg_duration_ms": 10, "avg_tool_calls": 1},
        "B": {"task_success": 0.9, "avg_context_tokens": 500, "avg_duration_ms": 99, "avg_tool_calls": 4},
        "C": {"task_success": 0.9, "avg_context_tokens": 200, "avg_duration_ms": 50, "avg_tool_calls": 2},
        "D": {"task_success": 0.9, "avg_context_tokens": 200, "avg_duration_ms": 40, "avg_tool_calls": 3},
    }
    ranked = [gid for gid, _ in rank_groups(summary)]
    assert ranked == ["D", "C", "B", "A"]
    assert rank_key(summary["D"]) < rank_key(summary["C"])
