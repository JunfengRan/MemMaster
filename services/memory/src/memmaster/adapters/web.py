from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from memmaster.hashing import sha256_text
from memmaster.models import ACL, CanonicalDocument, SourceCursor
from memmaster.registry import SourceAdapter


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        text = data.strip()
        if text:
            self.parts.append(text)


class WebAdapter(SourceAdapter):
    source_id = "web"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def probe(self) -> dict:
        files = list(self.root.glob("*.html"))
        sitemap = (self.root / "sitemap.xml").exists()
        return {"source_id": self.source_id, "files": len(files), "format": "html+sitemap", "sitemap": sitemap}

    def sync(self, cursor: SourceCursor | None = None) -> tuple[list[CanonicalDocument], SourceCursor]:
        allowed = self._sitemap_paths()
        docs: list[CanonicalDocument] = []
        for path in sorted(self.root.glob("*.html")):
            if allowed and path.name not in allowed:
                continue
            raw = path.read_text(encoding="utf-8")
            parser = _TextExtractor()
            parser.feed(raw)
            text = "\n".join(parser.parts)
            date_m = re.search(r"data-updated=\"([^\"]+)\"", raw)
            valid = datetime.fromisoformat(date_m.group(1)) if date_m else datetime.now(timezone.utc)
            docs.append(
                CanonicalDocument(
                    doc_id=f"web:{path.stem}",
                    source_id="web",
                    external_id=path.stem,
                    uri=f"https://hcs.lumengrid.example/portal/{path.name}",
                    title=parser.title or path.stem,
                    text=text,
                    content_hash=sha256_text(text),
                    valid_time=valid,
                    transaction_time=datetime.now(timezone.utc),
                    acl=ACL(groups=["delivery", "all"]),
                    metadata={"file": path.name},
                )
            )
        return docs, SourceCursor(source_id="web", watermark=str(len(docs)))

    def _sitemap_paths(self) -> set[str]:
        sitemap = self.root / "sitemap.xml"
        if not sitemap.exists():
            return set()
        return set(re.findall(r"<loc>[^<]+/([^/<]+)</loc>", sitemap.read_text(encoding="utf-8")))
