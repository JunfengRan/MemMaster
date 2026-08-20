from __future__ import annotations

from memmaster.hashing import chunk_id
from memmaster.models import CanonicalDocument, Chunk


def split_chunks(doc: CanonicalDocument, size: int = 512, overlap: int = 64) -> list[Chunk]:
    text = doc.text
    if len(text) <= size:
        spans = [(0, len(text))]
    else:
        spans = []
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            spans.append((start, end))
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    chunks = []
    for start, end in spans:
        piece = text[start:end]
        cid = chunk_id(doc.source_id, doc.external_id, doc.version, start, end, piece)
        chunks.append(
            Chunk(
                chunk_id=cid,
                doc_id=doc.doc_id,
                source_id=doc.source_id,
                version=doc.version,
                text=piece,
                start=start,
                end=end,
                valid_time=doc.valid_time,
                transaction_time=doc.transaction_time,
                acl_groups=list(doc.acl.groups),
            )
        )
    return chunks
