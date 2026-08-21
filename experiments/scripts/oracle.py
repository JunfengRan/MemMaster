from __future__ import annotations

import json
from pathlib import Path

from memmaster import default_registry
from memmaster.ingest import IngestPipeline
from memmaster.store import Store

from experiments import ROOT, load_questions


def oracle_check() -> dict:
    corpus = ROOT / "datasets" / "tob-memory-v1" / "corpus"
    registry = default_registry(corpus)
    docs = []
    for adapter in registry.all():
        got, _ = adapter.sync()
        docs.extend(got)
    by_id = {d.doc_id: d.text for d in docs}
    items = load_questions(False)
    failures = []
    per = {"mail": 0, "meeting": 0, "im": 0, "web": 0}
    for item in items:
        per[item["source"]] += 1
        blob = []
        for doc_id in item["evidence_docs"]:
            if doc_id not in by_id:
                # try prefix match
                matches = [t for i, t in by_id.items() if i == doc_id or i.endswith(doc_id.split(":", 1)[-1]) or doc_id in i]
                if not matches:
                    failures.append({"id": item["id"], "reason": f"missing {doc_id}"})
                    continue
                blob.extend(matches)
            else:
                blob.append(by_id[doc_id])
        text = "\n".join(blob)
        if not all(a in text for a in item["answers"]):
            failures.append({"id": item["id"], "reason": "answers not in evidence"})
    ok = not failures and min(per.values()) >= 5 and len(items) >= 20
    return {"ok": ok, "questionCount": len(items), "perSource": per, "oraclePass": ok, "failures": failures}


if __name__ == "__main__":
    print(json.dumps(oracle_check(), ensure_ascii=False, indent=2))
