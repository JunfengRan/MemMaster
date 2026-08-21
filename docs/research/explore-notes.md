# Method catalog evidence

Accessed 2026-08-20. Claims below are tied to public papers/repos. Vendor self-reported scores are labeled separately.

## Systems reviewed

| System | Ground truth | Incremental | Retrieval | Local | License signal |
|---|---|---|---|---|---|
| Mem0 | Default extracted facts, not verbatim | add/update/delete; add is accumulative | vector (+ optional graph) | OSS self-host | Apache-2.0 |
| MemOS | MemCube + provenance/version | lifecycle migrate/merge | vector + graph | OSS, evolving | Apache-2.0 |
| GraphRAG | TextUnit maps to Document | `graphrag update` | local + community global | yes, LLM-heavy | MIT |
| HippoRAG 2 | passages + source_id | limited incremental tests | PPR over phrase/passage | yes | research code |
| LightRAG | full docs + chunks | incremental merge | dual-level graph+vector | yes | MIT |
| RAGFlow | strongest parsers | KG not always delete-consistent | keyword+vector | Docker-heavy | Apache-2.0 |
| Letta/MemGPT | messages + archival | agent-written blocks | semantic archival | runtime coupled | Apache-2.0 |
| Graphiti/Zep | episodes kept as nodes | real-time bi-temporal | BM25+vector+graph | Neo4j etc. | Apache-2.0 |
| A-MEM | derived notes | link + rewrite history | vector + links | prototype | MIT |
| MemoryOS (BAI-LAB) | chat hierarchy | FIFO/hotness | semantic layers | dialogue-centric | research |

## Dataset construction lessons

LoCoMo (ACL 2024) grounds dialogues on personas and temporal event graphs, then writes atomic QA. LongMemEval compiles timestamped histories around each question with evidence sessions and abstention cases. MemMaster copies: event timeline first, then questions, then distractors, then oracle span checks.

## Push vs pull

Proactive Memory Agent (arXiv:2607.08716) runs a memory agent beside an unmodified action agent, injecting a short reminder or remaining silent. Ablations: selective > always-on > generic retrieval. OpenCode mapping: optional `search_mail` / `search_meeting` / `search_im` / `search_web` tools plus silent-or-remind injection. The eval prompt must not name a tool.

## Decision

Do not vendor-lock Mem0/MemOS/GraphRAG as the store. Keep immutable text as ground truth. Compose lexical, dense, graph-lite, extractive facts, time filters, core memory, dual channel, fact keys, and selective push as switches.
