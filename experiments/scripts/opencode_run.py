"""Create a fresh OpenCode session per case. Fallback is documented in metrics backend field."""
from __future__ import annotations

import argparse
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments import load_questions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    items = load_questions(False)[: args.limit]
    out_dir = ROOT / "experiments" / "runs" / "opencode-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        prompt = (
            "你是企业助手。只能使用 memory_search 工具查阅本地记忆，禁止猜测。"
            f"问题：{item['question']}\n请给出简洁答案并引用检索片段。"
        )
        cmd = [
            "opencode",
            "run",
            "-m",
            args.model,
            "--pure",
            prompt,
        ]
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
            rows.append(
                {
                    "question_id": item["id"],
                    "ok": proc.returncode == 0,
                    "stdout": (proc.stdout or "")[-4000:],
                    "stderr": (proc.stderr or "")[-2000:],
                }
            )
        except Exception as exc:
            rows.append({"question_id": item["id"], "ok": False, "error": str(exc)})
    path = out_dir / "probe.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
