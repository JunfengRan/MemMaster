# ADR 0003: Graph-lite instead of Microsoft GraphRAG

## Status

Accepted

## Context

GraphRAG community reports need extra LLM indexing and do not match atomic ToB QA. HippoRAG 2 PPR plus Graphiti bi-temporal metadata cover multihop and updates cheaper.

## Decision

Implement document–entity–term–event graph in SQLite with PPR. No community reports in v1.

## Consequences

Lower index LLM cost. Deferred GraphRAG config kept under `experiments/deferred/`.
