from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_text(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def sha256_json(value: Any) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return sha256_text(blob)


def chunk_id(source_id: str, external_id: str, version: int, start: int, end: int, text: str) -> str:
    span_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{source_id}:{external_id}:v{version}:{start}-{end}:{span_hash}"
