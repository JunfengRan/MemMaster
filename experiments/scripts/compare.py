from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from experiments import ROOT, load_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--groups", default="")
    args = parser.parse_args()
    catalog = load_catalog()
    wanted = [g.strip() for g in args.groups.split(",") if g.strip()]
    groups = [g["id"] for g in catalog["groups"] if g["status"] == "locked"]
    if wanted:
        groups = [g for g in groups if g in wanted]
    out_dir = ROOT / "experiments" / "runs" / ("pilot" if args.dev else "official")
    out_dir.mkdir(parents=True, exist_ok=True)
    db = ROOT / ".indexes" / "memmaster.sqlite"
    for gid in groups:
        cfg = ROOT / "experiments" / "configs" / f"{gid}.yaml"
        cmd = [
            sys.executable,
            str(ROOT / "experiments" / "scripts" / "run_eval.py"),
            "--config",
            str(cfg),
            "--out",
            str(out_dir),
            "--db",
            str(db),
        ]
        if args.dev:
            cmd.append("--dev")
        print("running", gid)
        env = dict(**{**__import__("os").environ, "PYTHONPATH": str(ROOT) + __import__("os").pathsep + str(ROOT / "services" / "memory" / "src")})
        subprocess.check_call(cmd, env=env)
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "experiments" / "scripts" / "score.py"),
            "--run-dir",
            str(out_dir),
        ]
    )
    print(out_dir)


if __name__ == "__main__":
    main()
