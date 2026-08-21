"""Two harness tunings per group (E1–E9), keep lexicographically better run."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))

from experiments import ROOT, load_catalog, load_config, load_questions, load_tiebreak_pool
from experiments.scripts.compare import ensure_sidecar
from experiments.scripts.score import rank_key, recommend, score_dir, score_row, _agg, SOURCES

HARNESSES = {
    "ha": {
        "agent": "enterprise-ha",
        "note": "",
        "label": "渠道启发式：按问题表面词选择邮件/会议/IM/网页，先检索再答",
    },
    "hb": {
        "agent": "enterprise-hb",
        "note": {
            "E1": "关键词尽量保留单号与产品型号原文。",
            "E2": "关键词同时覆盖专有名词与中文说法。",
            "E3": "第一跳没有单号或人名时换源，不要重复同一查询。",
            "E4": "若已有简短记忆提醒，仍要用检索核对数字。",
            "E5": "查询用实体名和单号。",
            "E6": "问当前/最新/修订时，检索词带上修订、更正、当前。",
            "E7": "术语表不能替代单号检索。",
            "E8": "查询用实体名，数字以原文为准。",
            "E9": "可用别名作检索词，如老陈、小刘、HCS、NCE。",
        },
        "label": "关键词改写：把问句压成专有名词再搜，空结果才换源",
    },
}

GROUPS = [f"E{i}" for i in range(1, 10)]


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + str(ROOT / "services" / "memory" / "src")
    env["MEMMASTER_URL"] = os.environ.get("MEMMASTER_URL", "http://127.0.0.1:8787")
    return env


def run_one(gid: str, hid: str, items: list[dict], out_path: Path) -> None:
    spec = HARNESSES[hid]
    note = spec["note"]
    if isinstance(note, dict):
        note = note.get(gid, "")
    ids = ",".join(q["id"] for q in items)
    cmd = [
        sys.executable,
        str(ROOT / "experiments" / "scripts" / "run_eval.py"),
        "--config",
        str(ROOT / "experiments" / "configs" / f"{gid}.yaml"),
        "--backend",
        "opencode",
        "--agent",
        spec["agent"],
        "--harness-note",
        str(note or ""),
        "--ids",
        ids,
        "--out",
        str(out_path.parent),
    ]
    print("RUN", gid, hid, ids, flush=True)
    subprocess.check_call(cmd, env=_env())
    src = out_path.parent / f"{gid}.jsonl"
    if src != out_path:
        out_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def jsonl_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def count_for(path: Path, n: int) -> bool:
    return len(jsonl_rows(path)) >= n


def pick_best(gid: str, items: list[dict]) -> tuple[str, Path, dict]:
    best_hid = None
    best_stats = None
    best_path = None
    qmap = {q["id"]: q for q in items}
    for hid in HARNESSES:
        path = ROOT / "experiments" / "runs" / "harness" / hid / f"{gid}.jsonl"
        rows = jsonl_rows(path)
        scored = [score_row(r, qmap[r["question_id"]], flex=True) for r in rows if r["question_id"] in qmap]
        stats = _agg(scored)
        if best_stats is None or rank_key(stats) < rank_key(best_stats):
            best_stats, best_hid, best_path = stats, hid, path
    return best_hid, best_path, best_stats


def main() -> None:
    ensure_sidecar()
    _run()


def _run() -> None:
    items = load_questions(False)
    n = len(items)
    for hid in HARNESSES:
        (ROOT / "experiments" / "runs" / "harness" / hid).mkdir(parents=True, exist_ok=True)
    for gid in GROUPS:
        for hid in HARNESSES:
            out = ROOT / "experiments" / "runs" / "harness" / hid / f"{gid}.jsonl"
            tmp_dir = ROOT / "experiments" / "runs" / "harness" / hid
            if count_for(out, n):
                print("skip", gid, hid)
                continue
            run_one(gid, hid, items, out)
            produced = tmp_dir / f"{gid}.jsonl"
            if produced != out:
                out.write_bytes(produced.read_bytes())

    final_dir = ROOT / "experiments" / "runs" / "harness-best"
    final_dir.mkdir(parents=True, exist_ok=True)
    chosen = {}
    for gid in GROUPS:
        hid, path, stats = pick_best(gid, items)
        chosen[gid] = {"harness": hid, "label": HARNESSES[hid]["label"], **{k: stats[k] for k in stats}}
        dest = final_dir / f"{gid}.jsonl"
        dest.write_bytes(path.read_bytes())
        print("BEST", gid, hid, stats["task_success"], flush=True)

    # E0: reuse adjusted exp2 (no harness)
    e0_src = ROOT / "experiments" / "runs" / "exp2-adjusted" / "E0.jsonl"
    if e0_src.exists():
        (final_dir / "E0.jsonl").write_bytes(e0_src.read_bytes())

    summary = score_dir(final_dir, flex=True)
    rec = recommend(summary)
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in summary.items()}
    payload = {
        "summary": public,
        "recommendation": rec,
        "protocol": "harness-best-of-two",
        "chosen": chosen,
    }
    (final_dir / "metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (final_dir / "chosen.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(final_dir / "metrics.json")
    print(json.dumps(rec.get("ranked"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
