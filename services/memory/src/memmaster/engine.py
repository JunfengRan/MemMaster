from __future__ import annotations

from datetime import datetime

from memmaster.models import Hit, InterventionRequest, InterventionResponse, SearchRequest, SearchResponse
from memmaster.retrieve import Retriever, estimate_tokens, rrf
from memmaster.facts import search_facts
from memmaster.store import Store

CORE_MEMORY = (
    "星河-7/XH-7 是 LumenGrid 客户侧华为 ToB 合成项目。"
    "关键产品：OceanStor Dorado、GaussDB、Huawei Cloud Stack、iMaster NCE、eSight、IdeaHub、Kunpeng、Ascend。"
    "PM 陈启明（老陈），存储 刘芳（小刘），数据库 王磊，网络 赵宇。"
)


class MemoryEngine:
    def __init__(self, store: Store, retriever: Retriever | None = None) -> None:
        self.store = store
        self.retriever = retriever or Retriever(store)
        self._push_cooldown: dict[str, int] = {}

    def search(self, req: SearchRequest) -> SearchResponse:
        methods = req.methods or ["hybrid"]
        hits: list[Hit] = []
        if "blank" in methods:
            return SearchResponse(hits=[], tokens=0, calls_charged=0)
        lexical = []
        hybrid = []
        if any(m in methods for m in ("lexical", "hybrid", "graph", "time", "facts", "dual", "keys", "core")):
            lexical = self.retriever.lexical(req.query, k=20, as_of=req.as_of, acl=req.acl_groups)
        if any(m in methods for m in ("hybrid", "graph", "time", "dual", "keys", "core", "dense")):
            hybrid = self.retriever.hybrid(req.query, k=12, as_of=req.as_of, acl=req.acl_groups)
        if "lexical" in methods and "hybrid" not in methods:
            hits = lexical[: req.top_k]
        elif "hybrid" in methods or "dense" in methods:
            hits = hybrid[: req.top_k]
        if "graph" in methods:
            hits = self.retriever.ppr(hits or hybrid or lexical, k=req.top_k)
        if "time" in methods:
            hits = self._time_filter(req.query, hits or hybrid, req.as_of)
        if "facts" in methods:
            hits = self._facts_then_source(req.query, req.as_of, req.top_k)
        if "dual" in methods:
            fact_hits = self._facts_then_source(req.query, req.as_of, req.top_k)
            hits = rrf([hybrid or lexical, fact_hits], k=req.top_k)
        if "keys" in methods:
            hits = self._keyed(req.query, hits or hybrid, req.top_k)
        hits = self._budget(hits, req.max_tokens, req.top_k)
        tokens = sum(estimate_tokens(h.text) for h in hits)
        return SearchResponse(hits=hits, tokens=tokens, calls_charged=1)

    def core_prefix(self) -> str:
        return CORE_MEMORY

    def intervene(self, req: InterventionRequest) -> InterventionResponse:
        calls = self._push_cooldown.get(req.session_id, 0)
        if calls >= 1:
            return InterventionResponse(action="no_intervention")
        result = self.search(
            SearchRequest(query=req.recent_text, methods=["hybrid", "graph"], top_k=3, max_tokens=600)
        )
        if not result.hits:
            return InterventionResponse(action="no_intervention")
        top = result.hits[0]
        if top.chunk_id in req.already_injected or top.score < 0.02:
            return InterventionResponse(action="no_intervention")
        snippet = top.text.replace("\n", " ")[:280]
        reminder = f"[记忆提醒] {top.title}: {snippet}"
        self._push_cooldown[req.session_id] = calls + 1
        return InterventionResponse(
            action="remind",
            reminder=reminder,
            chunk_ids=[top.chunk_id],
            tokens=estimate_tokens(reminder),
        )

    def _facts_then_source(self, query: str, as_of: datetime | None, k: int) -> list[Hit]:
        facts = search_facts(self.store, query, as_of=as_of)
        hits: list[Hit] = []
        seen = set()
        for fact in facts:
            if fact["chunk_id"] in seen:
                continue
            row = self.store.conn.execute(
                """SELECT c.chunk_id, c.doc_id, c.source_id, c.text, d.uri, d.title
                   FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
                   WHERE c.chunk_id=? AND c.tombstone=0""",
                (fact["chunk_id"],),
            ).fetchone()
            if not row:
                continue
            seen.add(row["chunk_id"])
            hits.append(
                Hit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    source_id=row["source_id"],
                    text=f"{fact['subject']} {fact['predicate']} {fact['object']}\n{row['text']}",
                    score=0.9,
                    uri=row["uri"],
                    title=row["title"],
                    channel="fact",
                )
            )
            if len(hits) >= k:
                break
        if len(hits) < k:
            extra = self.retriever.hybrid(query, k=k, as_of=as_of)
            hits = rrf([hits, extra], k=k)
        return hits

    def _keyed(self, query: str, base: list[Hit], k: int) -> list[Hit]:
        aliases = {
            "老陈": "陈启明",
            "小刘": "刘芳",
            "星河": "XH-7",
            "星河-7": "XH-7",
            "HCS": "Huawei Cloud Stack",
            "NCE": "iMaster NCE",
        }
        expanded = query
        for alias, canon in aliases.items():
            if alias in query:
                expanded = f"{query} {canon}"
        keyed = self.retriever.lexical(expanded, k=20)
        return rrf([base, keyed], k=k)

    def _time_filter(self, query: str, hits: list[Hit], as_of: datetime | None) -> list[Hit]:
        latest: dict[str, Hit] = {}
        for hit in hits:
            key = hit.doc_id.split(":")[0] + ":" + " ".join(hit.title)
            prev = latest.get(hit.doc_id)
            if prev is None or hit.score >= prev.score:
                latest[hit.doc_id] = hit
        ordered = sorted(latest.values(), key=lambda h: h.score, reverse=True)
        if any(tok in query for tok in ("最新", "当前", "现在", "修订后", "更新后")):
            return ordered
        return hits

    def _budget(self, hits: list[Hit], max_tokens: int, top_k: int) -> list[Hit]:
        out = []
        used = 0
        for hit in hits:
            cost = estimate_tokens(hit.text)
            if len(out) >= min(top_k, 8):
                break
            if used + cost > max_tokens:
                break
            out.append(hit)
            used += cost
        return out
