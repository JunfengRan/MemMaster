from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

from experiments import ROOT, load_catalog

SIDECAR_PORT = 8787


def sidecar_cmd() -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "memmaster.api:app",
        "--app-dir",
        str(ROOT / "services" / "memory" / "src"),
        "--host",
        "127.0.0.1",
        "--port",
        str(SIDECAR_PORT),
        "--log-level",
        "warning",
    ]


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={"content-type": "application/json"})
    with urlrequest.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_sidecar() -> subprocess.Popen | None:
    health = f"http://127.0.0.1:{SIDECAR_PORT}/health"
    try:
        with urlrequest.urlopen(health, timeout=2):
            post_json(
                f"http://127.0.0.1:{SIDECAR_PORT}/v1/sync",
                {
                    "corpus_root": str(ROOT / "datasets" / "tob-memory-v1" / "corpus"),
                    "db_path": str(ROOT / ".indexes" / "memmaster.sqlite"),
                },
            )
            return None
    except Exception:
        pass
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "services" / "memory" / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(sidecar_cmd(), cwd=str(ROOT), env=env)
    deadline = time.time() + 40
    last = None
    while time.time() < deadline:
        try:
            with urlrequest.urlopen(health, timeout=2):
                post_json(
                    f"http://127.0.0.1:{SIDECAR_PORT}/v1/sync",
                    {
                        "corpus_root": str(ROOT / "datasets" / "tob-memory-v1" / "corpus"),
                        "db_path": str(ROOT / ".indexes" / "memmaster.sqlite"),
                    },
                )
                return proc
        except Exception as exc:
            last = exc
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError(f"failed to start sidecar: {last}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--groups", default="")
    parser.add_argument("--backend", default="opencode", choices=["opencode", "oracle"])
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    args = parser.parse_args()
    catalog = load_catalog()
    wanted = [g.strip() for g in args.groups.split(",") if g.strip()]
    groups = [g["id"] for g in catalog["groups"] if g["status"] == "locked"]
    if wanted:
        groups = [g for g in groups if g in wanted]
    out_dir = ROOT / "experiments" / "runs" / ("pilot" if args.dev else "official")
    out_dir.mkdir(parents=True, exist_ok=True)
    sidecar = None
    try:
        if args.backend == "opencode":
            sidecar = ensure_sidecar()
        py_path = str(ROOT) + os.pathsep + str(ROOT / "services" / "memory" / "src")
        for gid in groups:
            cfg = ROOT / "experiments" / "configs" / f"{gid}.yaml"
            cmd = [
                sys.executable,
                str(ROOT / "experiments" / "scripts" / "run_eval.py"),
                "--config",
                str(cfg),
                "--out",
                str(out_dir),
                "--backend",
                args.backend,
                "--model",
                args.model,
            ]
            if args.dev:
                cmd.append("--dev")
            print("running", gid, args.backend)
            env = dict(os.environ)
            env["PYTHONPATH"] = py_path
            env["MEMMASTER_URL"] = f"http://127.0.0.1:{SIDECAR_PORT}"
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
    finally:
        if sidecar is not None:
            sidecar.terminate()


if __name__ == "__main__":
    main()
