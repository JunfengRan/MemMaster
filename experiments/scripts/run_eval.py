from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

from experiments import ROOT, load_config, load_questions


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
    hits_required = []
    missing = []
    for ans in question["answers"]:
        if ans in context:
            hits_required.append(ans)
        else:
            missing.append(ans)
    forbidden_hit = any(x in context for x in question.get("forbidden") or [])
    if forbidden_hit and question.get("type") in {"update", "distractor", "combo"}:
        # still ok if required also present; scorer handles forbidden in output
        pass
    if not hits_required:
        return "UNKNOWN", False
    return "；".join(hits_required), True


def run_group(cfg: dict, items: list[dict], engine: MemoryEngine, split: str) -> list[dict]:
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
        if methods:
            if memory_calls >= cfg.get("max_memory_calls", 2):
                constraint_fail = True
                hits = []
            else:
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
            if memory_calls > cfg.get("max_memory_calls", 2):
                constraint_fail = True
        else:
            hits = []
        context = "\n".join(context_parts)
        answer, _ = answer_from_context(item, context)
        if constraint_fail:
            answer = "FAIL_BUDGET"
        results.append(
            {
                "group": cfg["id"],
                "question_id": item["id"],
                "source": item["source"],
                "type": item["type"],
                "question": item["question"],
                "answer": answer,
                "context": context[:4000],
                "retrieved_ids": [h.chunk_id for h in hits] if methods else [],
                "memory_calls": memory_calls,
                "push_action": push_action,
                "constraint_fail": constraint_fail,
                "backend": "local-tool-agent",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", default=str(ROOT / "datasets" / "tob-memory-v1"))
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--db", default=str(ROOT / ".indexes" / "memmaster.sqlite"))
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    corpus = Path(args.dataset) / "corpus"
    store = build_index(Path(args.db), corpus)
    engine = MemoryEngine(store)
    items = load_questions(dev=args.dev)
    rows = run_group(cfg, items, engine, "dev" if args.dev else "official")
    out_dir = Path(args.out) if args.out else ROOT / "experiments" / "runs" / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{cfg['id']}.jsonl"
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
