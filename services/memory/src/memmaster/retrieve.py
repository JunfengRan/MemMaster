from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime

import numpy as np

from memmaster.embedder import Embedder, get_embedder
from memmaster.models import Hit
from memmaster.store import Store

STOP = set("的了在是和与及或为对从到将把被有没有这那一不也就都还要会能可".split())


def tokenize(query: str) -> list[str]:
    parts = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9]+", query)
    return [p for p in parts if p not in STOP and len(p.strip()) > 0]


class Retriever:
    def __init__(self, store: Store, embedder: Embedder | None = None) -> None:
        self.store = store
        self.embedder = embedder or get_embedder()

    def lexical(
        self,
        query: str,
        k: int = 20,
        as_of: datetime | None = None,
        acl: list[str] | None = None,
        source_id: str | None = None,
    ) -> list[Hit]:
        tokens = tokenize(query)
        if not tokens:
            return []
        quoted = [f'"{t}"' for t in tokens[:12] if t]
        fts_query = " OR ".join(quoted)
        src_sql, src_params = _source_clause(source_id)
        rows = []
        try:
            rows = self.store.conn.execute(
                f"""SELECT c.chunk_id, c.doc_id, c.source_id, c.text, c.valid_time, c.acl_json,
                          d.uri, d.title, bm25(chunks_fts) AS rank
                   FROM chunks_fts
                   JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                   JOIN documents d ON d.doc_id = c.doc_id
                   WHERE chunks_fts MATCH ? AND c.tombstone=0 AND d.tombstone=0{src_sql}
                   ORDER BY rank LIMIT ?""",
                (fts_query, *src_params, k),
            ).fetchall()
        except Exception:
            rows = []
        if not rows:
            like = f"%{tokens[0]}%"
            rows = self.store.conn.execute(
                f"""SELECT c.chunk_id, c.doc_id, c.source_id, c.text, c.valid_time, c.acl_json,
                          d.uri, d.title, 0 AS rank
                   FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
                   WHERE c.tombstone=0 AND d.tombstone=0 AND (c.text LIKE ? OR c.text LIKE ?){src_sql}
                   LIMIT ?""",
                (like, f"%{query[:24]}%", *src_params, k),
            ).fetchall()
        hits = []
        for row in rows:
            if not _acl_ok(row["acl_json"], acl):
                continue
            if not _time_ok(row["valid_time"], as_of):
                continue
            hits.append(
                Hit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    source_id=row["source_id"],
                    text=row["text"],
                    score=float(-row["rank"]) if row["rank"] is not None else 0.0,
                    uri=row["uri"],
                    title=row["title"],
                    channel="lexical",
                )
            )
        return hits

    def dense(
        self,
        query: str,
        k: int = 20,
        as_of: datetime | None = None,
        acl: list[str] | None = None,
        source_id: str | None = None,
    ) -> list[Hit]:
        q = self.embedder.encode([query])[0]
        src_sql, src_params = _source_clause(source_id)
        rows = self.store.conn.execute(
            f"""SELECT c.chunk_id, c.doc_id, c.source_id, c.text, c.valid_time, c.acl_json, c.vector,
                      d.uri, d.title
               FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
               WHERE c.tombstone=0 AND d.tombstone=0 AND c.vector IS NOT NULL{src_sql}""",
            src_params,
        ).fetchall()
        scored: list[Hit] = []
        for row in rows:
            if row["vector"] is None:
                continue
            if not _acl_ok(row["acl_json"], acl) or not _time_ok(row["valid_time"], as_of):
                continue
            vec = np.frombuffer(row["vector"], dtype=np.float32)
            if vec.size == 0:
                continue
            score = float(np.dot(q, vec) / (np.linalg.norm(q) * np.linalg.norm(vec) + 1e-9))
            scored.append(
                Hit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    source_id=row["source_id"],
                    text=row["text"],
                    score=score,
                    uri=row["uri"],
                    title=row["title"],
                    channel="dense",
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def hybrid(
        self,
        query: str,
        k: int = 8,
        as_of: datetime | None = None,
        acl: list[str] | None = None,
        source_id: str | None = None,
    ) -> list[Hit]:
        lex = self.lexical(query, k=20, as_of=as_of, acl=acl, source_id=source_id)
        den = self.dense(query, k=20, as_of=as_of, acl=acl, source_id=source_id)
        return rrf([lex, den], k=k)

    def graph_expand(self, seeds: list[Hit], k: int = 8) -> list[Hit]:
        if not seeds:
            return []
        names = set()
        for hit in seeds[:5]:
            names.update(tokenize(hit.text)[:8])
        extra: list[Hit] = []
        for name in list(names)[:12]:
            rows = self.store.conn.execute(
                """SELECT e.dst, n.ref_id FROM edges e
                   JOIN nodes n ON n.node_id = e.dst
                   JOIN nodes s ON s.node_id = e.src
                   WHERE s.name LIKE ? OR n.name LIKE ? LIMIT 8""",
                (f"%{name}%", f"%{name}%"),
            ).fetchall()
            for row in rows:
                ref = row["ref_id"]
                if not ref:
                    continue
                chunk = self.store.conn.execute(
                    """SELECT c.chunk_id, c.doc_id, c.source_id, c.text, d.uri, d.title
                       FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
                       WHERE (c.chunk_id=? OR c.doc_id=?) AND c.tombstone=0 LIMIT 1""",
                    (ref, ref),
                ).fetchone()
                if not chunk:
                    continue
                extra.append(
                    Hit(
                        chunk_id=chunk["chunk_id"],
                        doc_id=chunk["doc_id"],
                        source_id=chunk["source_id"],
                        text=chunk["text"],
                        score=0.15,
                        uri=chunk["uri"],
                        title=chunk["title"],
                        channel="graph",
                    )
                )
        return rrf([seeds, extra], k=k)

    def ppr(self, seeds: list[Hit], k: int = 8) -> list[Hit]:
        nodes = [r["node_id"] for r in self.store.conn.execute("SELECT node_id FROM nodes").fetchall()]
        if not nodes:
            return seeds[:k]
        index = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        adj = np.zeros((n, n), dtype=np.float32)
        for row in self.store.conn.execute("SELECT src, dst FROM edges"):
            if row["src"] in index and row["dst"] in index:
                adj[index[row["src"]], index[row["dst"]]] = 1
                adj[index[row["dst"]], index[row["src"]]] = 1
        deg = adj.sum(axis=1, keepdims=True)
        deg[deg == 0] = 1
        trans = adj / deg
        personal = np.zeros(n, dtype=np.float32)
        for hit in seeds:
            nid = f"doc:{hit.doc_id}"
            if nid in index:
                personal[index[nid]] = 1.0
        if personal.sum() == 0:
            return seeds[:k]
        personal /= personal.sum()
        rank = personal.copy()
        damping = 0.85
        for _ in range(12):
            rank = damping * trans.T @ rank + (1 - damping) * personal
        order = np.argsort(-rank)
        expanded = list(seeds)
        seen = {h.chunk_id for h in expanded}
        for idx in order[:20]:
            node = nodes[int(idx)]
            row = self.store.conn.execute("SELECT ref_id, kind FROM nodes WHERE node_id=?", (node,)).fetchone()
            if not row or row["kind"] != "document":
                continue
            chunks = self.store.conn.execute(
                """SELECT c.chunk_id, c.doc_id, c.source_id, c.text, d.uri, d.title
                   FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
                   WHERE c.doc_id=? AND c.tombstone=0 LIMIT 1""",
                (row["ref_id"],),
            ).fetchall()
            for chunk in chunks:
                if chunk["chunk_id"] in seen:
                    continue
                seen.add(chunk["chunk_id"])
                expanded.append(
                    Hit(
                        chunk_id=chunk["chunk_id"],
                        doc_id=chunk["doc_id"],
                        source_id=chunk["source_id"],
                        text=chunk["text"],
                        score=float(rank[idx]),
                        uri=chunk["uri"],
                        title=chunk["title"],
                        channel="ppr",
                    )
                )
        return expanded[:k]


def rrf(lists: list[list[Hit]], k: int, k_rrf: int = 60) -> list[Hit]:
    scores: dict[str, float] = defaultdict(float)
    best: dict[str, Hit] = {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.chunk_id] += 1.0 / (k_rrf + rank)
            if hit.chunk_id not in best or hit.score > best[hit.chunk_id].score:
                best[hit.chunk_id] = hit
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    out = []
    for cid, score in ordered[:k]:
        hit = best[cid].model_copy(update={"score": score})
        out.append(hit)
    return out


def _source_clause(source_id: str | None) -> tuple[str, tuple]:
    if not source_id:
        return "", ()
    return " AND c.source_id=?", (source_id,)


def _acl_ok(acl_json: str, groups: list[str] | None) -> bool:
    if not groups:
        return True
    data = json.loads(acl_json)
    owned = set(data.get("groups", []))
    return "all" in groups or bool(owned.intersection(groups) or "all" in owned)


def _time_ok(valid_time: str, as_of: datetime | None) -> bool:
    if as_of is None:
        return True
    try:
        vt = datetime.fromisoformat(valid_time)
    except ValueError:
        return True
    as_cmp = as_of if as_of.tzinfo else as_of.replace(tzinfo=vt.tzinfo)
    vt_cmp = vt if vt.tzinfo else vt.replace(tzinfo=as_cmp.tzinfo)
    return vt_cmp <= as_cmp


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 2.5))
