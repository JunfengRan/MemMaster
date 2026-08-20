from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT_REPO = Path(__file__).resolve().parents[2]
if str(ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(ROOT_REPO))

from experiments import ROOT, load_questions


def score_row(row: dict, item: dict) -> dict:
    answer = row.get("answer") or ""
    required = item["answers"]
    forbidden = item.get("forbidden") or []
    required_hits = [a for a in required if a in answer]
    forbidden_hits = [a for a in forbidden if a in answer]
    constraint_fail = bool(row.get("constraint_fail")) or answer == "FAIL_BUDGET"
    success = (not constraint_fail) and len(required_hits) == len(required) and not forbidden_hits
    retrieved = " ".join(row.get("retrieved_ids") or []) + " " + (row.get("context") or "")
    evidence_ok = all(any(part in retrieved or part.split(":")[-1] in retrieved for part in [d.split(":")[-1]]) for d in item.get("evidence_docs") or [])
    citation = (not item.get("must_cite")) or bool(row.get("retrieved_ids") or row.get("group") == "E0")
    if row.get("group") == "E0":
        citation = True
        evidence_ok = False
    return {
        "question_id": item["id"],
        "group": row.get("group"),
        "success": success,
        "required_hits": required_hits,
        "forbidden_hits": forbidden_hits,
        "constraint_fail": constraint_fail,
        "evidence_in_context": evidence_ok,
        "citation_ok": citation and (row.get("group") == "E0" or bool(row.get("retrieved_ids") or "记忆提醒" in (row.get("context") or "") or CORE_HINT(row))),
        "memory_calls": row.get("memory_calls", 0),
        "source": item["source"],
        "type": item["type"],
    }


def CORE_HINT(row: dict) -> bool:
    return "星河-7" in (row.get("context") or "")


def score_dir(run_dir: Path) -> dict:
    items = {q["id"]: q for q in load_questions(dev=False)}
    by_group: dict[str, list] = defaultdict(list)
    for path in sorted(run_dir.glob("E*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            item = items[row["question_id"]]
            by_group[row["group"]].append(score_row(row, item))
    summary = {}
    for gid, rows in by_group.items():
        n = len(rows)
        summary[gid] = {
            "n": n,
            "task_success": sum(r["success"] for r in rows) / n if n else 0,
            "constraint_fail": sum(r["constraint_fail"] for r in rows),
            "evidence_in_context": sum(r["evidence_in_context"] for r in rows) / n if n else 0,
            "by_source": _break(rows, "source"),
            "by_type": _break(rows, "type"),
            "rows": rows,
        }
    return summary


def _break(rows, key):
    buckets = defaultdict(list)
    for r in rows:
        buckets[r[key]].append(r)
    return {k: sum(x["success"] for x in v) / len(v) for k, v in buckets.items()}


def recommend(summary: dict) -> dict:
    ranked = sorted(
        (
            (gid, s)
            for gid, s in summary.items()
            if s["constraint_fail"] == 0
        ),
        key=lambda kv: (-kv[1]["task_success"], kv[0]),
    )
    if not ranked:
        return {"winner": None, "reason": "all groups failed constraints"}
    best_id, best = ranked[0]
    return {
        "winner": best_id,
        "task_success": best["task_success"],
        "ranked": [(g, s["task_success"]) for g, s in ranked],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=str(ROOT / "experiments" / "runs" / "latest"))
    args = parser.parse_args()
    summary = score_dir(Path(args.run_dir))
    rec = recommend(summary)
    public = {
        gid: {k: v for k, v in s.items() if k != "rows"}
        for gid, s in summary.items()
    }
    out = {"summary": public, "recommendation": rec, "detail": summary}
    path = Path(args.run_dir) / "metrics.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(rec)
