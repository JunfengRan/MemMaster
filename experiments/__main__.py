from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "services" / "memory" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--dataset", default=str(ROOT / "datasets" / "tob-memory-v1"))
    run.add_argument("--dev", action="store_true")
    run.add_argument("--backend", default="opencode", choices=["opencode", "oracle"])
    compare = sub.add_parser("compare")
    compare.add_argument("--dev", action="store_true")
    compare.add_argument("--groups", default="")
    compare.add_argument("--backend", default="opencode", choices=["opencode", "oracle"])
    args = parser.parse_args()
    if args.cmd == "run":
        from experiments.scripts import run_eval

        sys.argv = [
            "run_eval",
            "--config",
            args.config,
            "--dataset",
            args.dataset,
            "--backend",
            args.backend,
        ]
        if args.dev:
            sys.argv.append("--dev")
        run_eval.main()
    elif args.cmd == "compare":
        from experiments.scripts import compare

        sys.argv = ["compare", "--backend", args.backend]
        if args.dev:
            sys.argv.append("--dev")
        if args.groups:
            sys.argv.extend(["--groups", args.groups])
        compare.main()


if __name__ == "__main__":
    main()
