from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from memmaster.hashing import sha256_text
from memmaster.models import ACL, CanonicalDocument, SourceCursor
from memmaster.registry import SourceAdapter


class MeetingAdapter(SourceAdapter):
    source_id = "meeting"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def probe(self) -> dict:
        files = list(self.root.glob("*.md")) + list(self.root.glob("*.json"))
        return {"source_id": self.source_id, "files": len(files), "format": "markdown+json"}

    def sync(self, cursor: SourceCursor | None = None) -> tuple[list[CanonicalDocument], SourceCursor]:
        docs: list[CanonicalDocument] = []
        for path in sorted(self.root.iterdir()):
            if path.suffix == ".md":
                docs.append(self._from_md(path))
            elif path.suffix == ".json":
                docs.append(self._from_json(path))
        return docs, SourceCursor(source_id="meeting", watermark=str(len(docs)))

    def _from_md(self, path: Path) -> CanonicalDocument:
        raw = path.read_text(encoding="utf-8")
        meta: dict = {}
        body = raw
        if raw.startswith("---"):
            _, fm, body = raw.split("---", 2)
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
        valid = datetime.fromisoformat(meta.get("date", "2026-01-01T00:00:00+08:00"))
        return CanonicalDocument(
            doc_id=f"meeting:{path.stem}",
            source_id="meeting",
            external_id=path.stem,
            uri=f"meeting://xh7/{path.name}",
            title=meta.get("title", path.stem),
            text=body.strip(),
            content_hash=sha256_text(body.strip()),
            valid_time=valid,
            transaction_time=datetime.now(timezone.utc),
            acl=ACL(groups=["delivery", "all"]),
            metadata=meta,
        )

    def _from_json(self, path: Path) -> CanonicalDocument:
        data = json.loads(path.read_text(encoding="utf-8"))
        text = data["text"]
        valid = datetime.fromisoformat(data["date"])
        return CanonicalDocument(
            doc_id=f"meeting:{path.stem}",
            source_id="meeting",
            external_id=path.stem,
            uri=f"meeting://xh7/{path.name}",
            title=data.get("title", path.stem),
            text=text,
            content_hash=sha256_text(text),
            valid_time=valid,
            transaction_time=datetime.now(timezone.utc),
            acl=ACL(groups=["delivery", "all"]),
            metadata={k: v for k, v in data.items() if k != "text"},
        )
