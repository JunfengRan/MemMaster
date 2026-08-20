# ADR 0001: Local sidecar + OpenCode plugin

## Status

Accepted

## Context

OpenCode plugins are JS/TS modules. Heavy embedding and SQLite/FTS belong in Python. Huawei ToB mock sources must stay hot-pluggable.

## Decision

TypeScript plugin in `apps/opencode-plugin` talks HTTP to `services/memory` FastAPI. Connectors register via `memmaster.sources` entry points. Raw text snapshots are the only ground truth.

## Consequences

Two processes. Versioned `/v1` API. Plugin never reads dataset files from disk during eval.
