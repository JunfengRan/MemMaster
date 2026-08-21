"""Run one new sample at a time on tied leaders until success rates split."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))

from experiments import load_questions, load_tiebreak_pool
from experiments.scripts.compare import ensure_sidecar
from experiments.scripts.run_harness import run_one, jsonl_rows
from experiments.scripts.score import _agg, apply_cost_outliers, recommend, score_row, score_dir

FINAL = ROOT / "experiments" / "runs" / "harness-best"
TIE_DIR = ROOT / "experiments" / "runs" / "tiebreak"


def success_key(stats: dict) -> tuple[int, int]:
    n = int(stats["n"])
    ok = int(round(float(stats["task_success"]) * n))
    return ok, n


def rate_of(key: tuple[int, int]) -> float:
    ok, n = key
    return ok / n if n else 0.0


def current_board(items_by_id: dict) -> dict[str, dict]:
    board: dict[str, list] = {}
    for path in sorted(FINAL.glob("E*.jsonl")):
        gid = path.stem
        if gid == "E0":
            continue
        scored = []
        for r in jsonl_rows(path):
            item = items_by_id.get(r["question_id"])
            if item:
                scored.append(score_row(r, item, flex=True))
        board[gid] = scored
    flat = [row for rows in board.values() for row in rows]
    apply_cost_outliers(flat)
    out = {}
    for gid, rows in board.items():
        out[gid] = _agg(rows)
        out[gid]["rows"] = rows
    return out


def tied_leaders(board: dict) -> list[str]:
    rates = {gid: success_key(s) for gid, s in board.items()}
    if not rates:
        return []
    best_rate = max(rate_of(k) for k in rates.values())
    cluster = [gid for gid, k in sorted(rates.items()) if abs(rate_of(k) - best_rate) < 1e-12]
    return cluster if len(cluster) > 1 else []


def ids_in(gid: str) -> set[str]:
    path = FINAL / f"{gid}.jsonl"
    if not path.exists():
        return set()
    return {r["question_id"] for r in jsonl_rows(path)}


def append_row(gid: str, row: dict) -> None:
    path = FINAL / f"{gid}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def persist(log: list, items_by_id: dict, chosen: dict) -> None:
    summary = score_dir(FINAL, flex=True)
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in summary.items()}
    exp2_path = ROOT / "experiments" / "runs" / "exp2-adjusted" / "metrics.json"
    if exp2_path.exists():
        exp2 = json.loads(exp2_path.read_text(encoding="utf-8"))
        if "E0" in public and "E0" in exp2.get("summary", {}):
            for key in ("avg_context_tokens", "avg_duration_ms", "avg_tool_calls"):
                public["E0"][key] = exp2["summary"]["E0"][key]
    rec = recommend(public)
    out = {
        "summary": public,
        "recommendation": rec,
        "protocol": "harness-plus-tiebreak-cost-outlier",
        "cost_rule": {
            "peers": "same question, E1-E9 (exclude Blank)",
            "tools": "z>=1.5 and calls >= median+2",
            "tokens": "z>=1.5 and tokens >= 1.6 * median",
            "duration": "z>=2.0 and ms >= 1.8 * median",
            "success": "required facts written AND not cost outlier",
        },
        "tiebreak_log": log,
        "chosen": chosen,
    }
    FINAL.mkdir(parents=True, exist_ok=True)
    (FINAL / "metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    TIE_DIR.mkdir(parents=True, exist_ok=True)
    (TIE_DIR / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ensure_sidecar()
    items = load_questions(False)
    pool = [p for p in load_tiebreak_pool() if not p.get("retired")]
    chosen = json.loads((FINAL / "chosen.json").read_text(encoding="utf-8")) if (FINAL / "chosen.json").exists() else {}
    TIE_DIR.mkdir(parents=True, exist_ok=True)
    items_by_id = {q["id"]: q for q in items}
    for probe in load_tiebreak_pool():
        items_by_id[probe["id"]] = probe
    log_path = TIE_DIR / "log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    if not isinstance(log, list):
        log = []

    for probe in pool:
        board = current_board(items_by_id)
        cluster = tied_leaders(board)
        if len(cluster) < 2:
            print("SPLIT", {g: success_key(board[g]) for g in board}, flush=True)
            break
        missing = [gid for gid in cluster if probe["id"] not in ids_in(gid)]
        if not missing:
            continue
        print(
            "TIE",
            cluster,
            {g: success_key(board[g]) for g in cluster},
            "probe",
            probe["id"],
            "missing",
            missing,
            flush=True,
        )
        for gid in missing:
            hid = (chosen.get(gid) or {}).get("harness") or "ha"
            tmp = TIE_DIR / probe["id"] / hid
            tmp.mkdir(parents=True, exist_ok=True)
            run_one(gid, hid, [probe], tmp / f"{gid}.jsonl")
            produced = tmp / f"{gid}.jsonl"
            rows = jsonl_rows(produced)
            if not rows:
                raise SystemExit(f"no result for {gid} {probe['id']}")
            append_row(gid, rows[-1])
            scored = score_row(rows[-1], probe, flex=True)
            log.append(
                {
                    "probe": probe["id"],
                    "group": gid,
                    "fact_success": scored["success"],
                    "answer": (rows[-1].get("answer") or "")[:240],
                }
            )
            print("TIE-RES", gid, probe["id"], "fact", scored["success"], flush=True)
            persist(log, items_by_id, chosen)

    board = current_board(items_by_id)
    persist(log, items_by_id, chosen)
    print("FINAL", {g: success_key(s) for g, s in board.items()}, flush=True)
    rec = json.loads((FINAL / "metrics.json").read_text(encoding="utf-8")).get("recommendation")
    print(json.dumps(rec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
