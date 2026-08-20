from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from memmaster.hashing import sha256_text
from memmaster.store import Store


def load_seed_facts(path: Path, store: Store) -> int:
    if not path.exists():
        return 0
    facts = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for fact in facts:
        chunk_id = fact.get("chunk_id")
        if not chunk_id or chunk_id == "pending":
            row = store.conn.execute(
                "SELECT chunk_id FROM chunks WHERE doc_id=? AND tombstone=0 LIMIT 1",
                (fact["doc_id"],),
            ).fetchone()
            chunk_id = row["chunk_id"] if row else fact["doc_id"]
        store.conn.execute(
            """INSERT OR REPLACE INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact["fact_id"],
                fact["subject"],
                fact["predicate"],
                fact["object"],
                fact["doc_id"],
                chunk_id,
                fact.get("span", [0, 0])[0],
                fact.get("span", [0, 0])[1],
                fact["valid_from"],
                fact.get("valid_to"),
                fact.get("superseded_by"),
            ),
        )
        count += 1
    store.commit()
    return count


def extract_regex_facts(store: Store) -> int:
    patterns = [
        (r"PO-[\w\-]+", "purchase_order"),
        (r"CHG-\d+", "change_ticket"),
        (r"RTO\s*[:=为是]\s*([0-9]+分钟|[0-9]+ min)", "rto"),
        (r"V100R024C\d+", "nce_version"),
        (r"租户ID[：:]\s*(\S+)", "tenant_id"),
    ]
    count = 0
    rows = store.conn.execute(
        "SELECT chunk_id, doc_id, text, valid_time FROM chunks WHERE tombstone=0"
    ).fetchall()
    for row in rows:
        for pattern, pred in patterns:
            for match in re.finditer(pattern, row["text"]):
                value = match.group(0)
                fid = sha256_text(f"{row['chunk_id']}:{pred}:{value}")[7:23]
                store.conn.execute(
                    """INSERT OR REPLACE INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        fid,
                        row["doc_id"],
                        pred,
                        value,
                        row["doc_id"],
                        row["chunk_id"],
                        match.start(),
                        match.end(),
                        row["valid_time"],
                        None,
                        None,
                    ),
                )
                count += 1
    store.commit()
    return count


def search_facts(store: Store, query: str, as_of: datetime | None = None) -> list[dict]:
    rows = store.conn.execute(
        """SELECT * FROM facts WHERE subject LIKE ? OR object LIKE ? OR predicate LIKE ?""",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()
    out = []
    for row in rows:
        if as_of and row["valid_to"]:
            if datetime.fromisoformat(row["valid_to"]) <= as_of:
                continue
        out.append(dict(row))
    return out
