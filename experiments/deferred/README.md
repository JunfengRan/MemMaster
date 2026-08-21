# Deferred experiments

These configs are runnable later, not part of the locked 10.

## always-on push

```
python -m experiments run --config experiments/deferred/always_on_push.yaml
```

The first matrix used a forced `local-tool-agent` (always search, then string-extract). That protocol is invalid for agent evaluation. Official runs use OpenCode with four optional source tools and an unprompted question. Archive of the old jsonl: `experiments/runs/archive-local-tool-agent/` if present.

## full GraphRAG

Skipped: extra LLM indexing cost and community reports mismatch atomic QA.
