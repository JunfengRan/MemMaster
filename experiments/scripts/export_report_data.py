from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.scripts.score import score_dir, recommend


def main() -> None:
    run_dir = ROOT / "experiments" / "runs" / "official"
    summary = score_dir(run_dir)
    rec = recommend(summary)
    public = {gid: {k: v for k, v in s.items() if k != "rows"} for gid, s in summary.items()}
    out = ROOT / "artifacts" / "releases" / "report-data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": public, "recommendation": rec}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
