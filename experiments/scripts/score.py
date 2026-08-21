from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

ROOT_REPO = Path(__file__).resolve().parents[2]
if str(ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(ROOT_REPO))

import re
from experiments import ROOT, load_questions, load_tiebreak_pool

SOURCES = ("mail", "meeting", "im", "web")

# 按题在参赛组上估正态分布。n≈8–9 时 1 次额外调用就会把 z 抬很高，
# 所以相对 z 之外必须带绝对余量，避免把「多数人 2 次、有人 3 次」判失败。
COST_MIN_PEERS = 3
TOOLS_Z = 1.5
TOOLS_EXTRA = 2
TOKEN_Z = 1.5
TOKEN_RATIO = 1.6
DURATION_Z = 2.0
DURATION_RATIO = 1.8


def _has_fact(answer: str, fact: str) -> bool:
    if fact in answer:
        return True
    compact = lambda s: re.sub(r"\s+", "", s)
    return compact(fact).lower() in compact(answer).lower()


def score_row(row: dict, item: dict, flex: bool = False) -> dict:
    answer = row.get("answer") or ""
    if flex:
        answer = re.sub(r"[*`_]+", "", answer)
    required = item["answers"]
    forbidden = item.get("forbidden") or []
    check = _has_fact if flex else (lambda a, f: f in a)
    required_hits = [a for a in required if check(answer, a)]
    forbidden_hits = [a for a in forbidden if check(answer, a)]
    constraint_fail = bool(row.get("constraint_fail")) or answer == "FAIL_BUDGET"
    infra = bool(row.get("infra_failure"))
    has_all = len(required_hits) == len(required)
    # 任务完成率：写出全部必答事实即可。forbidden 是约束/干扰旁路，不进主排序。
    success = (not constraint_fail) and (not infra) and has_all
    return {
        "question_id": item["id"],
        "group": row.get("group"),
        "success": success,
        "required_hits": required_hits,
        "forbidden_hits": forbidden_hits,
        "constraint_fail": constraint_fail,
        "infra_failure": infra,
        "memory_calls": int(row.get("tool_calls") or row.get("memory_calls") or 0),
        "context_tokens": int(row.get("context_tokens") or 0),
        "duration_ms": int(row.get("duration_ms") or 0),
        "source": item["source"],
        "type": item["type"],
        "cost_fail": False,
        "cost_reasons": [],
        "fact_success": success,
    }


def _pop_std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def cost_outlier_reasons(row: dict, peers: list[dict]) -> list[str]:
    """Flag expensive outliers vs the same question's peer distribution."""
    if row.get("group") == "E0":
        return []
    if len(peers) < COST_MIN_PEERS:
        return []
    reasons = []

    def pack(key: str) -> tuple[float, float, float]:
        xs = [float(p.get(key) or 0) for p in peers]
        m = mean(xs)
        s = _pop_std(xs)
        med = float(median(xs))
        val = float(row.get(key) or 0)
        z = (val - m) / s if s > 1e-6 else 0.0
        return z, med, val

    z_t, med_t, val_t = pack("memory_calls")
    z_k, med_k, val_k = pack("context_tokens")
    z_m, med_m, val_m = pack("duration_ms")
    if z_t >= TOOLS_Z and val_t >= med_t + TOOLS_EXTRA:
        reasons.append(f"tools {val_t:.0f} z={z_t:.2f} med={med_t:.0f}")
    if z_k >= TOKEN_Z and med_k > 0 and val_k >= TOKEN_RATIO * med_k:
        reasons.append(f"tokens {val_k:.0f} z={z_k:.2f} med={med_k:.0f}")
    if z_m >= DURATION_Z and med_m > 0 and val_m >= DURATION_RATIO * med_m:
        reasons.append(f"duration {val_m:.0f} z={z_m:.2f} med={med_m:.0f}")
    return reasons


def apply_cost_outliers(scored: list[dict]) -> list[dict]:
    by_q: dict[str, list[dict]] = defaultdict(list)
    for row in scored:
        by_q[row["question_id"]].append(row)
    for peers in by_q.values():
        comparable = [p for p in peers if p.get("group") != "E0"]
        for row in peers:
            reasons = cost_outlier_reasons(row, comparable)
            row["cost_fail"] = bool(reasons)
            row["cost_reasons"] = reasons
            fact = bool(row.get("fact_success", row.get("success")))
            row["fact_success"] = fact
            row["success"] = fact and not row["cost_fail"]
    return scored


def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {
            "n": 0,
            "task_success": 0.0,
            "avg_context_tokens": 0.0,
            "avg_duration_ms": 0.0,
            "avg_tool_calls": 0.0,
            "constraint_fail": 0,
            "cost_fail": 0,
            "infra_failure": 0,
            "fact_success": 0.0,
        }
    return {
        "n": n,
        "task_success": sum(r["success"] for r in rows) / n,
        "avg_context_tokens": mean(r["context_tokens"] for r in rows),
        "avg_duration_ms": mean(r["duration_ms"] for r in rows),
        "avg_tool_calls": mean(r["memory_calls"] for r in rows),
        "constraint_fail": sum(r["constraint_fail"] for r in rows),
        "cost_fail": sum(1 for r in rows if r.get("cost_fail")),
        "infra_failure": sum(r["infra_failure"] for r in rows),
        "fact_success": sum(1 for r in rows if r.get("fact_success", r.get("success"))) / n,
    }


def rank_key(stats: dict) -> tuple:
    """Completion rate desc, then context/time/tool-calls asc."""
    return (
        -float(stats.get("task_success") or 0),
        float(stats.get("avg_context_tokens") or 0),
        float(stats.get("avg_duration_ms") or 0),
        float(stats.get("avg_tool_calls") or 0),
    )


def rank_groups(summary: dict) -> list[tuple[str, dict]]:
    return sorted(summary.items(), key=lambda kv: rank_key(kv[1]))


def score_dir(run_dir: Path, flex: bool = False) -> dict:
    items = {q["id"]: q for q in load_questions(dev=False)}
    for extra in load_tiebreak_pool():
        items[extra["id"]] = extra
    all_scored: list[dict] = []
    for path in sorted(run_dir.glob("E*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            item = items.get(row["question_id"])
            if item is None:
                continue
            all_scored.append(score_row(row, item, flex=flex))
    apply_cost_outliers(all_scored)
    by_group: dict[str, list] = defaultdict(list)
    for scored in all_scored:
        by_group[scored["group"]].append(scored)
    summary = {}
    for gid, rows in by_group.items():
        overall = _agg(rows)
        overall["by_source"] = {}
        for src in SOURCES:
            overall["by_source"][src] = _agg([r for r in rows if r["source"] == src])
        overall["by_type"] = {}
        types = sorted({r["type"] for r in rows})
        for typ in types:
            overall["by_type"][typ] = _agg([r for r in rows if r["type"] == typ])
        overall["rows"] = rows
        summary[gid] = overall
    return summary


def recommend(summary: dict) -> dict:
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in summary.items()}
    ranked = rank_groups(public)
    by_source = {}
    for src in SOURCES:
        src_stats = {gid: s["by_source"][src] for gid, s in public.items() if src in s.get("by_source", {})}
        by_source[src] = [(gid, stats) for gid, stats in rank_groups(src_stats)]
    if not ranked:
        return {"winner": None, "reason": "no groups", "ranked": [], "by_source": by_source}
    best_id, best = ranked[0]
    return {
        "winner": best_id,
        "task_success": best["task_success"],
        "avg_context_tokens": best["avg_context_tokens"],
        "avg_duration_ms": best["avg_duration_ms"],
        "avg_tool_calls": best["avg_tool_calls"],
        "key": "task_success desc, avg_context_tokens, avg_duration_ms, avg_tool_calls",
        "ranked": [
            {
                "group": gid,
                "n": s.get("n") or 0,
                "task_success": s["task_success"],
                "fact_success": s.get("fact_success"),
                "cost_fail": s.get("cost_fail") or 0,
                "avg_context_tokens": s["avg_context_tokens"],
                "avg_duration_ms": s["avg_duration_ms"],
                "avg_tool_calls": s["avg_tool_calls"],
            }
            for gid, s in ranked
        ],
        "by_source": {
            src: [
                {
                    "group": gid,
                    "task_success": s["task_success"],
                    "avg_context_tokens": s["avg_context_tokens"],
                    "avg_duration_ms": s["avg_duration_ms"],
                    "avg_tool_calls": s["avg_tool_calls"],
                }
                for gid, s in rows
            ]
            for src, rows in by_source.items()
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=str(ROOT / "experiments" / "runs" / "latest"))
    parser.add_argument("--flex", action="store_true")
    args = parser.parse_args()
    summary = score_dir(Path(args.run_dir), flex=args.flex)
    rec = recommend(summary)
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in summary.items()}
    out = {"summary": public, "recommendation": rec, "protocol": "agent-initiated-four-tools"}
    path = Path(args.run_dir) / "metrics.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
