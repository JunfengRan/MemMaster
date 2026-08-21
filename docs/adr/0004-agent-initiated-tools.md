# ADR 0004: Agent-initiated four-source tools

## Status

Accepted

## Context

The first official matrix used a `local-tool-agent` that always called a unified `memory_search` with the question text, then extracted answers by string match. Probe prompts also said “只能使用 memory_search”. That is not how an enterprise agent works, and it inflated task success.

## Decision

1. Each case is a fresh OpenCode session. The user message is **only the question**. No instruction names a tool.
2. E1–E9 expose four optional tools at once: `search_mail`, `search_meeting`, `search_im`, `search_web`. Each tool filters retrieval to that source. The agent must notice that it needs a tool and pick one.
3. E0 uses `--pure` (no memory plugin). Core memory / selective push remain context injection, not commanded tool use.
4. Sessions run in `experiments/eval-workspace` with read/glob/bash/web denied, so the agent cannot open repository ground truth.
5. Ranking is lexicographic over overall metrics, then the same key inside each source slice:
   - `task_success` descending
   - `avg_context_tokens` ascending
   - `avg_duration_ms` ascending
   - `avg_tool_calls` ascending

The old forced-retrieve runner remains as `--backend oracle` (retrieval ceiling only) and is not mixed into official ranking.

## Consequences

Official `python -m experiments compare` talks to a live sidecar and OpenCode. Unit tests keep the oracle ceiling and source-isolation checks. Previous `local-tool-agent` jsonl lives under `experiments/runs/archive-local-tool-agent/` if archived.
