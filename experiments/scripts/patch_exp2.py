"""Freeze experiment-2 (untuned harness) after dataset repair.

New items default to failure. Context / duration / tool-call averages stay
the original experiment-2 values (not diluted by dummy rows).
"""
from __future__ import annotations

import json
from pathlib import Path

from experiments import ROOT, load_questions
from experiments.scripts.score import score_row, _agg, recommend, SOURCES

SRC = ROOT / "experiments" / "runs" / "official"
DST = ROOT / "experiments" / "runs" / "exp2-adjusted"
OLD_METRICS = json.loads((SRC / "metrics.json").read_text(encoding="utf-8"))


def main() -> None:
    items = {q["id"]: q for q in load_questions(False)}
    new_ids = [qid for qid, q in items.items() if q.get("added_after_exp1")]
    DST.mkdir(parents=True, exist_ok=True)
    by_group = {}
    for path in sorted(SRC.glob("E*.jsonl")):
        rows_out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["question_id"] not in items:
                continue  # dropped Q06
            item = items[row["question_id"]]
            scored = score_row(row, item, flex=False)
            row["success"] = scored["success"]
            rows_out.append(row)
        gid = path.stem
        for qid in new_ids:
            item = items[qid]
            rows_out.append(
                {
                    "group": gid,
                    "question_id": qid,
                    "source": item["source"],
                    "type": item["type"],
                    "question": item["question"],
                    "answer": "",
                    "success": False,
                    "memory_calls": 0,
                    "tool_calls": 0,
                    "context_tokens": 0,
                    "duration_ms": 0,
                    "constraint_fail": False,
                    "infra_failure": False,
                    "backend": "exp2-default-fail",
                    "note": "题面在第二次实验之后加入，按协议记失败，不计入三项代价均值",
                }
            )
        (DST / path.name).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out) + "\n",
            encoding="utf-8",
        )
        scored_rows = []
        for row in rows_out:
            item = items[row["question_id"]]
            scored_rows.append(score_row(row, item, flex=False))
        overall = _agg(scored_rows)
        old = OLD_METRICS["summary"][gid]
        overall["avg_context_tokens"] = old["avg_context_tokens"]
        overall["avg_duration_ms"] = old["avg_duration_ms"]
        overall["avg_tool_calls"] = old["avg_tool_calls"]
        overall["by_source"] = {}
        for src in SOURCES:
            overall["by_source"][src] = _agg([r for r in scored_rows if r["source"] == src])
            # restore cost metrics from old source slice when present
            old_src = (old.get("by_source") or {}).get(src) or {}
            if isinstance(old_src, dict) and "avg_context_tokens" in old_src:
                overall["by_source"][src]["avg_context_tokens"] = old_src["avg_context_tokens"]
                overall["by_source"][src]["avg_duration_ms"] = old_src["avg_duration_ms"]
                overall["by_source"][src]["avg_tool_calls"] = old_src["avg_tool_calls"]
        overall["rows"] = scored_rows
        by_group[gid] = overall
    rec = recommend(by_group)
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in by_group.items()}
    out = {
        "summary": public,
        "recommendation": rec,
        "protocol": "exp2-untuned-adjusted",
        "note": "Q06 因第一版天花全失败已删除；Q21/Q22 为替换/新增，第二次实验记失败。三项代价指标沿用原 20 题均值。",
        "dropped": ["Q06"],
        "added_as_fail": new_ids,
    }
    (DST / "metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(DST / "metrics.json")
    print("n", {g: public[g]["n"] for g in public})
    print("success", {g: round(public[g]["task_success"], 4) for g in public})


if __name__ == "__main__":
    main()
