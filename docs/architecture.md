# Architecture

```
mock mail/meeting/im/web
        │
 ConnectorRegistry (entry points)
        │
 CanonicalDocument + immutable snapshot
        │
 IngestPipeline (chunk, embed, FTS5, graph-lite, facts)
        │
 FastAPI /v1/search  /v1/interventions  /v1/memory/{id}
        │
 OpenCode plugin tools: `search_mail` / `search_meeting` / `search_im` / `search_web` plus optional push hook. The eval user message does not name a tool.
```

Ground truth is always the raw text snapshot. Derived facts, graph edges and core memory must cite `doc_id`/`chunk_id`/span and never overwrite snapshots.

Index update:

1. Adapter cursor fetch
2. Hash compare → create/update/delete/tombstone
3. Staging rebuild of chunks/vectors/edges
4. Consistency checks (counts, orphan edges)
5. Atomic manifest switch; rollback keeps previous manifest
