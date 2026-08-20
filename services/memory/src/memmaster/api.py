from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from memmaster.engine import MemoryEngine
from memmaster.ingest import IngestPipeline
from memmaster.models import InterventionRequest, SearchRequest
from memmaster.store import Store
from memmaster import default_registry

APP_STATE: dict = {}


class SyncBody(BaseModel):
    corpus_root: str
    db_path: str = ".indexes/memmaster.sqlite"


def get_engine() -> MemoryEngine:
    engine = APP_STATE.get("engine")
    if engine is None:
        raise HTTPException(503, "memory engine not initialized; POST /v1/sync first")
    return engine


def create_app() -> FastAPI:
    app = FastAPI(title="MemMaster", version="0.1.0")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/v1/sync")
    def sync(body: SyncBody):
        store = Store(Path(body.db_path))
        pipeline = IngestPipeline(store)
        registry = default_registry(Path(body.corpus_root))
        ingested = {}
        for adapter in registry.all():
            docs, cursor = adapter.sync()
            manifest = pipeline.ingest_documents(docs, cursor_source=adapter.source_id, watermark=cursor.watermark)
            ingested[adapter.source_id] = {"docs": len(docs), "probe": adapter.probe()}
        APP_STATE["engine"] = MemoryEngine(store)
        APP_STATE["store"] = store
        return {"ok": True, "ingested": ingested, "manifest": store.get_manifest("active")}

    @app.post("/v1/search")
    def search(req: SearchRequest):
        return get_engine().search(req)

    @app.get("/v1/memory/{chunk_id}")
    def get_chunk(chunk_id: str):
        store: Store = APP_STATE.get("store")
        if store is None:
            raise HTTPException(503, "not ready")
        row = store.conn.execute(
            """SELECT c.*, d.uri, d.title FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
               WHERE c.chunk_id=? AND c.tombstone=0""",
            (chunk_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "chunk not found")
        return dict(row)

    @app.post("/v1/interventions")
    def interventions(req: InterventionRequest):
        return get_engine().intervene(req)

    return app


app = create_app()
