from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _ver(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.check_output([exe, *cmd[1:]], text=True, stderr=subprocess.STDOUT, timeout=20)
        return out.strip().splitlines()[0][:200]
    except Exception as exc:
        return f"error:{exc}"


def main() -> None:
    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "node": _ver(["node", "--version"]),
        "npm": _ver(["npm", "--version"]),
        "bun": _ver(["bun", "--version"]),
        "opencode": _ver(["opencode", "--version"]),
        "embedder": "hash-default; set MEMMASTER_EMBEDDER=bge-m3 to enable BGE-M3",
    }
    if not payload["python"] or not payload["node"]:
        payload["ok"] = False
    out = ROOT / "artifacts" / "gates" / "env-doctor.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(out)
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
