from __future__ import annotations

import email
from datetime import datetime, timezone
from email.policy import default
from pathlib import Path

from memmaster.hashing import sha256_text
from memmaster.models import ACL, CanonicalDocument, SourceCursor
from memmaster.registry import SourceAdapter


class MailAdapter(SourceAdapter):
    source_id = "mail"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def probe(self) -> dict:
        files = sorted(self.root.glob("*.eml"))
        return {"source_id": self.source_id, "files": len(files), "format": "rfc822"}

    def sync(self, cursor: SourceCursor | None = None) -> tuple[list[CanonicalDocument], SourceCursor]:
        docs: list[CanonicalDocument] = []
        for path in sorted(self.root.glob("*.eml")):
            raw = path.read_bytes()
            msg = email.message_from_bytes(raw, policy=default)
            body = msg.get_body(preferencelist=("plain", "html"))
            text = body.get_content() if body else raw.decode("utf-8", errors="replace")
            date_hdr = msg.get("Date")
            valid = _parse_date(date_hdr) if date_hdr else datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            message_id = (msg.get("Message-ID") or path.stem).strip("<>")
            docs.append(
                CanonicalDocument(
                    doc_id=f"mail:{path.stem}",
                    source_id="mail",
                    external_id=path.stem,
                    uri=f"mail://xh7/{path.name}",
                    title=msg.get("Subject") or path.stem,
                    text=_headers_and_body(msg, text),
                    content_hash=sha256_text(text),
                    valid_time=valid,
                    transaction_time=datetime.now(timezone.utc),
                    acl=ACL(groups=["delivery", "all"]),
                    metadata={"from": msg.get("From"), "message_id": message_id},
                )
            )
        return docs, SourceCursor(source_id="mail", watermark=str(len(docs)))


def _headers_and_body(msg, text: str) -> str:
    return (
        f"From: {msg.get('From')}\nTo: {msg.get('To')}\nCc: {msg.get('Cc')}\n"
        f"Subject: {msg.get('Subject')}\nDate: {msg.get('Date')}\n\n{text.strip()}\n"
    )


def _parse_date(value: str) -> datetime:
    from email.utils import parsedate_to_datetime

    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
