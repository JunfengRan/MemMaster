from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from memmaster.hashing import sha256_text
from memmaster.models import ACL, CanonicalDocument, SourceCursor
from memmaster.registry import SourceAdapter


class IMAdapter(SourceAdapter):
    source_id = "im"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def probe(self) -> dict:
        files = list(self.root.glob("*.ndjson"))
        return {"source_id": self.source_id, "files": len(files), "format": "ndjson-cursor"}

    def sync(self, cursor: SourceCursor | None = None) -> tuple[list[CanonicalDocument], SourceCursor]:
        docs: list[CanonicalDocument] = []
        last = cursor.watermark if cursor else ""
        for path in sorted(self.root.glob("*.ndjson")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                msg_id = item["id"]
                if last and msg_id <= last:
                    continue
                text = f"[{item['ts']}] {item['user']} ({item.get('alias', '')}): {item['text']}"
                docs.append(
                    CanonicalDocument(
                        doc_id=f"im:{msg_id}",
                        source_id="im",
                        external_id=msg_id,
                        uri=f"im://welink-xh7/{msg_id}",
                        title=f"IM {msg_id}",
                        text=text,
                        content_hash=sha256_text(text),
                        valid_time=datetime.fromisoformat(item["ts"]),
                        transaction_time=datetime.now(timezone.utc),
                        acl=ACL(groups=item.get("acl", ["delivery", "all"])),
                        metadata=item,
                    )
                )
                last = msg_id
        return docs, SourceCursor(source_id="im", watermark=last)
