from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceId = Literal["mail", "meeting", "im", "web"]


class ACL(BaseModel):
    groups: list[str] = Field(default_factory=lambda: ["all"])


class CanonicalDocument(BaseModel):
    doc_id: str
    source_id: SourceId
    external_id: str
    uri: str
    title: str
    text: str
    content_hash: str
    version: int = 1
    valid_time: datetime
    transaction_time: datetime
    acl: ACL = Field(default_factory=ACL)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceCursor(BaseModel):
    source_id: SourceId
    watermark: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_id: SourceId
    version: int
    text: str
    start: int
    end: int
    valid_time: datetime
    transaction_time: datetime
    acl_groups: list[str]
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tombstone: bool = False


class Fact(BaseModel):
    fact_id: str
    subject: str
    predicate: str
    object: str
    doc_id: str
    chunk_id: str
    span: tuple[int, int]
    valid_from: datetime
    valid_to: datetime | None = None
    superseded_by: str | None = None


class Hit(BaseModel):
    chunk_id: str
    doc_id: str
    source_id: SourceId
    text: str
    score: float
    uri: str
    title: str
    channel: str = "raw"


class SearchRequest(BaseModel):
    query: str
    methods: list[str] = Field(default_factory=lambda: ["hybrid"])
    top_k: int = 8
    max_tokens: int = 3000
    as_of: datetime | None = None
    acl_groups: list[str] = Field(default_factory=lambda: ["all"])
    session_id: str | None = None
    source_id: SourceId | None = None


class SearchResponse(BaseModel):
    hits: list[Hit]
    tokens: int
    calls_charged: int = 1


class InterventionRequest(BaseModel):
    session_id: str
    recent_text: str
    already_injected: list[str] = Field(default_factory=list)


class InterventionResponse(BaseModel):
    action: Literal["remind", "no_intervention"]
    reminder: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    tokens: int = 0
