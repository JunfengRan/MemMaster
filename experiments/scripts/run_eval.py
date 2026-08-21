from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "services" / "memory" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))

from memmaster import default_registry
from memmaster.engine import CORE_MEMORY, MemoryEngine
from memmaster.facts import extract_regex_facts, load_seed_facts
from memmaster.ingest import IngestPipeline
from memmaster.models import InterventionRequest, SearchRequest
from memmaster.store import Store

from experiments import ROOT, load_config, load_questions, load_tiebreak_pool
from experiments.scripts.opencode_run import memory_call_count, run_session

SOURCE_TOOLS = ["search_mail", "search_meeting", "search_im", "search_web"]


def build_index(db_path: Path, corpus: Path) -> Store:
    store = Store(db_path)
    pipeline = IngestPipeline(store)
    registry = default_registry(corpus)
    for adapter in registry.all():
        docs, cursor = adapter.sync()
        pipeline.ingest_documents(docs, cursor_source=adapter.source_id, watermark=cursor.watermark)
    load_seed_facts(ROOT / "datasets" / "tob-memory-v1" / "facts.seed.json", store)
    extract_regex_facts(store)
    return store


def answer_from_context(question: dict, context: str) -> tuple[str, bool]:
    hits_required = [ans for ans in question["answers"] if ans in context]
    if not hits_required:
        return "UNKNOWN", False
    return "；".join(hits_required), True


def run_group_oracle(cfg: dict, items: list[dict], engine: MemoryEngine, split: str) -> list[dict]:
    """Forced-retrieve ceiling. Not the official protocol."""
    results = []
    for item in items:
        memory_calls = 0
        context_parts: list[str] = []
        push_action = "no_intervention"
        if cfg.get("core_memory"):
            context_parts.append(CORE_MEMORY)
        if cfg.get("push"):
            iv = engine.intervene(
                InterventionRequest(session_id=f"{cfg['id']}-{item['id']}-{split}", recent_text=item["question"])
            )
            push_action = iv.action
            if iv.reminder:
                context_parts.append(iv.reminder)
                memory_calls += 1
        methods = cfg.get("methods") or []
        constraint_fail = False
        hits = []
        if methods:
            resp = engine.search(
                SearchRequest(
                    query=item["question"],
                    methods=methods,
                    top_k=cfg.get("max_chunks", 8),
                    max_tokens=cfg.get("max_inject_tokens", 3000),
                )
            )
            memory_calls += resp.calls_charged
            hits = resp.hits
            context_parts.extend(h.text for h in hits)
        context = "\n".join(context_parts)
        answer, _ = answer_from_context(item, context)
        results.append(
            {
                "group": cfg["id"],
                "question_id": item["id"],
                "source": item["source"],
                "type": item["type"],
                "question": item["question"],
                "answer": answer,
                "context": context[:4000],
                "retrieved_ids": [h.chunk_id for h in hits],
                "memory_calls": memory_calls,
                "tool_calls": memory_calls,
                "context_tokens": max(1, len(context) // 2),
                "duration_ms": 0,
                "push_action": push_action,
                "constraint_fail": constraint_fail,
                "backend": "oracle-ceiling",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
    return results


def sidecar_env(cfg: dict, harness_note: str = "") -> dict[str, str]:
    methods = ",".join(cfg.get("methods") or ["hybrid"])
    env = {
        "MEMMASTER_URL": os.environ.get("MEMMASTER_URL", "http://127.0.0.1:8787"),
        "MEMMASTER_METHODS": methods,
        "MEMMASTER_MAX_CALLS": str(cfg.get("max_memory_calls", 8)),
        "MEMMASTER_CORE": "1" if cfg.get("core_memory") else "0",
        "MEMMASTER_PUSH": "1" if cfg.get("push") else "0",
        "MEMMASTER_CORE_TEXT": CORE_MEMORY if cfg.get("core_memory") else "",
    }
    if harness_note:
        env["MEMMASTER_HARNESS_NOTE"] = harness_note
    return env


def wait_sidecar(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urlrequest.urlopen(url + "/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"sidecar not ready: {last}")


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={"content-type": "application/json"})
    with urlrequest.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_push(base: str, session_id: str, question: str) -> dict:
    try:
        return post_json(
            base.rstrip("/") + "/v1/interventions",
            {"session_id": session_id, "recent_text": question, "already_injected": []},
        )
    except Exception:
        return {"action": "no_intervention"}


def run_group_opencode(
    cfg: dict,
    items: list[dict],
    model: str,
    agent: str = "enterprise",
    harness_note: str = "",
) -> list[dict]:
    enable_tools = bool(cfg.get("tools"))
    env = sidecar_env(cfg, harness_note=harness_note)
    base = env["MEMMASTER_URL"]
    rows = []
    for item in items:
        started = datetime.now(timezone.utc)
        case_env = dict(env)
        push_action = "off"
        if cfg.get("push"):
            iv = fetch_push(base, f"{cfg['id']}-{item['id']}", item["question"])
            push_action = iv.get("action") or "no_intervention"
            if iv.get("reminder"):
                case_env["MEMMASTER_PUSH_TEXT"] = str(iv["reminder"])
        parsed = run_session(
            item["question"],
            model=model,
            enable_tools=enable_tools,
            env=case_env,
            title=f"{cfg['id']}-{item['id']}-{agent}",
            agent=agent,
        )
        tool_n = memory_call_count(parsed.get("tool_calls") or [])
        print(
            f"{cfg['id']} {item['id']} tools={tool_n} ctx={parsed.get('context_tokens')} "
            f"ms={parsed.get('duration_ms')} ok={parsed.get('ok')}",
            flush=True,
        )
        rows.append(
            {
                "group": cfg["id"],
                "question_id": item["id"],
                "source": item["source"],
                "type": item["type"],
                "question": item["question"],
                "answer": parsed.get("answer") or "",
                "context": parsed.get("all_text") or "",
                "retrieved_ids": [],
                "memory_calls": tool_n,
                "tool_calls": tool_n,
                "tool_events": parsed.get("tool_calls") or [],
                "context_tokens": parsed.get("context_tokens") or 0,
                "output_tokens": parsed.get("output_tokens") or 0,
                "cost_usd": parsed.get("cost_usd") or 0,
                "duration_ms": parsed.get("duration_ms") or 0,
                "session_id": parsed.get("session_id"),
                "push_action": push_action,
                "constraint_fail": False,
                "infra_failure": bool(parsed.get("infra_failure") or not parsed.get("ok")),
                "backend": "opencode",
                "model": model,
                "ts": started.isoformat(),
                "stderr_tail": parsed.get("stderr") or "",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", default=str(ROOT / "datasets" / "tob-memory-v1"))
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--db", default=str(ROOT / ".indexes" / "memmaster.sqlite"))
    parser.add_argument("--backend", choices=["opencode", "oracle"], default="opencode")
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--agent", default="enterprise")
    parser.add_argument("--harness-note", default="")
    parser.add_argument("--ids", default="")
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    items = load_questions(dev=args.dev)
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        pool = items + load_tiebreak_pool()
        items = [x for x in pool if x["id"] in wanted]
    if args.limit:
        items = items[: args.limit]
    if args.backend == "oracle":
        corpus = Path(args.dataset) / "corpus"
        store = build_index(Path(args.db), corpus)
        engine = MemoryEngine(store)
        rows = run_group_oracle(cfg, items, engine, "dev" if args.dev else "official")
    else:
        wait_sidecar(os.environ.get("MEMMASTER_URL", "http://127.0.0.1:8787"))
        rows = run_group_opencode(cfg, items, args.model, agent=args.agent, harness_note=args.harness_note)
    out_dir = Path(args.out) if args.out else ROOT / "experiments" / "runs" / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{cfg['id']}.jsonl"
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
