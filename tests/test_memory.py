from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "memory" / "src"))
sys.path.insert(0, str(ROOT))

from memmaster import default_registry
from memmaster.engine import MemoryEngine
from memmaster.ingest import IngestPipeline
from memmaster.models import SearchRequest
from memmaster.store import Store
from experiments.scripts.oracle import oracle_check


def test_oracle_and_sources(tmp_path):
    from datasets.tob_memory_v1_loader import ensure_corpus

    ensure_corpus()
    report = oracle_check()
    assert report["ok"], report
    assert report["questionCount"] >= 20
    assert report["perSource"]["mail"] >= 5
    assert report["perSource"]["meeting"] >= 5
    assert report["perSource"]["im"] >= 5
    assert report["perSource"]["web"] >= 5


def test_ingest_hybrid_and_delete(tmp_path):
    from datasets.tob_memory_v1_loader import ensure_corpus, corpus_root

    ensure_corpus()
    store = Store(tmp_path / "db.sqlite")
    pipeline = IngestPipeline(store)
    registry = default_registry(corpus_root())
    for adapter in registry.all():
        docs, cursor = adapter.sync()
        assert adapter.probe()["files"] > 0
        pipeline.ingest_documents(docs, cursor_source=adapter.source_id, watermark=cursor.watermark)
    assert pipeline.orphan_edges() == 0
    engine = MemoryEngine(store)
    hit = engine.search(SearchRequest(query="PO-XH7-20260318-044", methods=["lexical"]))
    assert hit.hits
    doc_id = hit.hits[0].doc_id
    pipeline.delete_document(doc_id)
    hit2 = engine.search(SearchRequest(query="PO-XH7-20260318-044", methods=["lexical"]))
    assert all(h.doc_id != doc_id for h in hit2.hits)


def test_update_increments_version(tmp_path):
    from memmaster.adapters.mail import MailAdapter
    from datasets.tob_memory_v1_loader import ensure_corpus, corpus_root

    ensure_corpus()
    store = Store(tmp_path / "db.sqlite")
    pipeline = IngestPipeline(store)
    adapter = MailAdapter(corpus_root() / "mail")
    docs, _ = adapter.sync()
    pipeline.ingest_documents(docs)
    doc = docs[0]
    doc.text += "\n附录：版本2标记。"
    from memmaster.hashing import sha256_text

    doc.content_hash = sha256_text(doc.text)
    pipeline.ingest_documents([doc])
    row = store.conn.execute("SELECT version FROM documents WHERE doc_id=?", (doc.doc_id,)).fetchone()
    assert row["version"] == 2
