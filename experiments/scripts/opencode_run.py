"""Run one OpenCode session per case. User message is the question only."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "experiments" / "eval-workspace"
SOURCE_TOOLS = ("search_mail", "search_meeting", "search_im", "search_web")
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
EVAL_CONFIG_DIR = ROOT / ".indexes" / "opencode-eval-home"


def opencode_bin() -> str:
    explicit = os.environ.get("OPENCODE_BIN")
    if explicit:
        return explicit
    home = Path.home()
    for c in (
        home / "AppData" / "Roaming" / "npm" / "node_modules" / "opencode-ai" / "bin" / "opencode.exe",
        home / "AppData" / "Roaming" / "npm" / "opencode.cmd",
    ):
        if c.exists():
            return str(c)
    return "opencode"


def isolated_config_env() -> dict[str, str]:
    """Use a config dir without global Daytona/Feishu plugins. Never commit this dir."""
    EVAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    src = Path.home() / ".config" / "opencode" / "opencode.json"
    cfg: dict[str, Any] = {}
    if src.exists():
        cfg = json.loads(src.read_text(encoding="utf-8-sig"))
    cfg["plugin"] = []
    cfg.pop("agent", None)
    (EVAL_CONFIG_DIR / "opencode.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"OPENCODE_CONFIG_DIR": str(EVAL_CONFIG_DIR)}


def parse_events(stdout: str) -> dict[str, Any]:
    session_id = None
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    context_tokens = 0
    output_tokens = 0
    cost = 0.0
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = ev.get("sessionID") or session_id
        kind = ev.get("type")
        part = ev.get("part") or {}
        if kind == "text":
            t = part.get("text") or ""
            if t:
                texts.append(t)
        elif kind == "tool_use":
            state = part.get("state") or {}
            name = part.get("tool") or part.get("name") or state.get("command") or ""
            args = state.get("input") or state.get("args") or {}
            tool_calls.append({"tool": name, "args": args, "status": state.get("status")})
        elif kind == "step_finish":
            tok = part.get("tokens") or {}
            cache = tok.get("cache") or {}
            inp = int(tok.get("input") or 0)
            cached = int(cache.get("read") or 0)
            context_tokens = max(context_tokens, inp + cached)
            output_tokens += int(tok.get("output") or 0)
            cost += float(part.get("cost") or 0)
    return {
        "session_id": session_id,
        "answer": texts[-1] if texts else "",
        "all_text": "\n".join(texts),
        "tool_calls": tool_calls,
        "context_tokens": context_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }


def run_session(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
    enable_tools: bool = True,
    env: dict[str, str] | None = None,
    timeout: int = 180,
    title: str = "memmaster",
    agent: str = "enterprise",
) -> dict[str, Any]:
    cmd = [
        opencode_bin(),
        "run",
        "--format",
        "json",
        "--auto",
        "--agent",
        agent,
        "-m",
        model,
        "--dir",
        str(SANDBOX),
        "--title",
        title,
        question,
    ]
    if not enable_tools:
        cmd.insert(2, "--pure")
    merged = os.environ.copy()
    merged.update(isolated_config_env())
    if env:
        merged.update(env)
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=merged,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        parsed = parse_events(proc.stdout or "")
        parsed.update(
            {
                "ok": proc.returncode == 0,
                "duration_ms": duration_ms,
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "")[-2000:],
                "backend": "opencode",
                "prompt": question,
            }
        )
        if not parsed.get("answer") and proc.stdout:
            parsed["answer"] = (proc.stdout or "")[-1500:]
        return parsed
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "infra_failure": True,
            "answer": "",
            "tool_calls": [],
            "context_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "backend": "opencode",
            "error": "timeout",
            "prompt": question,
        }


def memory_call_count(tool_calls: list[dict[str, Any]]) -> int:
    n = 0
    for call in tool_calls:
        name = str(call.get("tool") or "")
        if name in SOURCE_TOOLS or name.startswith("search_"):
            n += 1
    return n
