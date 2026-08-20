from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from memmaster.hashing import sha256_json
from memmaster.models import CanonicalDocument
from memmaster.chunker import split_chunks
from memmaster.embedder import Embedder, get_embedder
from memmaster.store import Store


ENTITY_PATTERNS = [
    r"OceanStor[\w\s\-]*",
    r"GaussDB[\w\-]*",
    r"Huawei Cloud Stack",
    r"HCS",
    r"iMaster NCE[^\s,，。]*",
    r"eSight",
    r"IdeaHub[^\s,，。]*",
    r"Kunpeng[^\s,，。]*",
    r"Ascend[^\s,，。]*",
    r"PO-[\w\-]+",
    r"CHG-\d+",
    r"XH-?7",
    r"星河-?7",
    r"LumenGrid",
]


class IngestPipeline:
    def __init__(self, store: Store, embedder: Embedder | None = None) -> None:
        self.store = store
        self.embedder = embedder or get_embedder()

    def ingest_documents(self, docs: list[CanonicalDocument], cursor_source: str | None = None, watermark: str = "") -> dict:
        staging = []
        for doc in docs:
            existing = self.store.conn.execute(
                "SELECT content_hash, version FROM documents WHERE doc_id=?",
                (doc.doc_id,),
            ).fetchone()
            if existing and existing["content_hash"] == doc.content_hash:
                continue
            if existing:
                doc.version = int(existing["version"]) + 1
            chunks = split_chunks(doc)
            vectors = self.embedder.encode([c.text for c in chunks]) if chunks else None
            rows = []
            for i, chunk in enumerate(chunks):
                vec = vectors[i].astype("float32").tobytes() if vectors is not None else None
                rows.append(
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        chunk.source_id,
                        chunk.version,
                        chunk.text,
                        chunk.start,
                        chunk.end,
                        chunk.valid_time.isoformat(),
                        chunk.transaction_time.isoformat(),
                        json.dumps({"groups": chunk.acl_groups}),
                        json.dumps(chunk.aliases, ensure_ascii=False),
                        json.dumps(chunk.tags, ensure_ascii=False),
                        vec,
                    )
                )
            self.store.upsert_document(doc)
            self.store.replace_chunks(doc.doc_id, rows)
            self._index_graph(doc, chunks)
            staging.append(doc.doc_id)
        if cursor_source:
            self.store.set_cursor(cursor_source, watermark)
        manifest = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "embedder": type(self.embedder).__name__,
            "dim": self.embedder.dim,
            "docs": self._count("documents"),
            "chunks": self._count("chunks"),
            "edges": self._count("edges"),
        }
        manifest["hash"] = sha256_json(manifest)
        self.store.set_manifest("active", manifest)
        self.store.commit()
        return manifest

    def delete_document(self, doc_id: str) -> None:
        self.store.tombstone_document(doc_id)
        self.store.conn.execute("DELETE FROM edges WHERE doc_id=?", (doc_id,))
        self.store.commit()

    def _index_graph(self, doc: CanonicalDocument, chunks) -> None:
        doc_node = f"doc:{doc.doc_id}"
        self.store.conn.execute(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
            (doc_node, "document", doc.title, doc.doc_id),
        )
        names = set()
        for pattern in ENTITY_PATTERNS:
            for match in re.findall(pattern, doc.text):
                names.add(match.strip())
        for name in names:
            nid = f"ent:{name}"
            self.store.conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
                (nid, "entity", name, None),
            )
            eid = f"{doc_node}->{nid}"
            self.store.conn.execute(
                "INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?,?,?)",
                (
                    eid,
                    doc_node,
                    nid,
                    "mentions",
                    doc.doc_id,
                    doc.valid_time.isoformat(),
                    None,
                ),
            )
        event_id = f"evt:{doc.source_id}:{doc.external_id}"
        self.store.conn.execute(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
            (event_id, "event", doc.title, doc.doc_id),
        )
        self.store.conn.execute(
            "INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?,?,?)",
            (
                f"{doc_node}->{event_id}",
                doc_node,
                event_id,
                "records",
                doc.doc_id,
                doc.valid_time.isoformat(),
                None,
            ),
        )

    def _count(self, table: str) -> int:
        return int(self.store.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE 1").fetchone()[0])

    def orphan_edges(self) -> int:
        row = self.store.conn.execute(
            """SELECT COUNT(*) FROM edges e
               WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id=e.src)
                  OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id=e.dst)"""
        ).fetchone()
        return int(row[0])
