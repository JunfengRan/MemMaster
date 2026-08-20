from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  external_id TEXT NOT NULL,
  uri TEXT NOT NULL,
  title TEXT NOT NULL,
  text TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version INTEGER NOT NULL,
  valid_time TEXT NOT NULL,
  transaction_time TEXT NOT NULL,
  acl_json TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  tombstone INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  text TEXT NOT NULL,
  start INTEGER NOT NULL,
  end INTEGER NOT NULL,
  valid_time TEXT NOT NULL,
  transaction_time TEXT NOT NULL,
  acl_json TEXT NOT NULL,
  aliases_json TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  tombstone INTEGER NOT NULL DEFAULT 0,
  vector BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  chunk_id UNINDEXED,
  text,
  aliases,
  tags,
  content=''
);
CREATE TABLE IF NOT EXISTS facts (
  fact_id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  chunk_id TEXT NOT NULL,
  span_start INTEGER NOT NULL,
  span_end INTEGER NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  superseded_by TEXT
);
CREATE TABLE IF NOT EXISTS nodes (
  node_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  ref_id TEXT
);
CREATE TABLE IF NOT EXISTS edges (
  edge_id TEXT PRIMARY KEY,
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL,
  doc_id TEXT,
  valid_from TEXT,
  valid_to TEXT
);
CREATE TABLE IF NOT EXISTS cursors (
  source_id TEXT PRIMARY KEY,
  watermark TEXT NOT NULL,
  extra_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manifests (
  name TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_document(self, doc) -> None:
        self.conn.execute(
            """INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)
               ON CONFLICT(doc_id) DO UPDATE SET
                 text=excluded.text, content_hash=excluded.content_hash,
                 version=excluded.version, valid_time=excluded.valid_time,
                 transaction_time=excluded.transaction_time, metadata_json=excluded.metadata_json,
                 tombstone=0""",
            (
                doc.doc_id,
                doc.source_id,
                doc.external_id,
                doc.uri,
                doc.title,
                doc.text,
                doc.content_hash,
                doc.version,
                doc.valid_time.isoformat(),
                doc.transaction_time.isoformat(),
                json.dumps(doc.acl.model_dump()),
                json.dumps(doc.metadata),
            ),
        )

    def tombstone_document(self, doc_id: str) -> None:
        self.conn.execute("UPDATE documents SET tombstone=1 WHERE doc_id=?", (doc_id,))
        self.conn.execute("UPDATE chunks SET tombstone=1 WHERE doc_id=?", (doc_id,))

    def replace_chunks(self, doc_id: str, rows: list[tuple]) -> None:
        old = self.conn.execute("SELECT chunk_id FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
        for (cid,) in old:
            self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (cid,))
            self.conn.execute("DELETE FROM chunks WHERE chunk_id=?", (cid,))
            self.conn.execute("DELETE FROM edges WHERE doc_id=?", (doc_id,))
        for row in rows:
            self.conn.execute(
                """INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?)""",
                row,
            )
            self.conn.execute(
                "INSERT INTO chunks_fts(chunk_id, text, aliases, tags) VALUES (?,?,?,?)",
                (row[0], row[4], row[10], row[11]),
            )

    def set_cursor(self, source_id: str, watermark: str, extra: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO cursors VALUES (?,?,?) ON CONFLICT(source_id) DO UPDATE SET watermark=excluded.watermark",
            (source_id, watermark, json.dumps(extra or {})),
        )

    def commit(self) -> None:
        self.conn.commit()

    def set_manifest(self, name: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT INTO manifests VALUES (?,?) ON CONFLICT(name) DO UPDATE SET payload_json=excluded.payload_json",
            (name, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        )

    def get_manifest(self, name: str) -> dict | None:
        row = self.conn.execute("SELECT payload_json FROM manifests WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else None
