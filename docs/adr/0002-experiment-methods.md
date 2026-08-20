# ADR 0002: Experiment methods

## Status

Accepted

## Context

Need ablation of pull/push and methods adapted from Mem0, MemOS, Graphiti, HippoRAG 2, LongMemEval, MemGPT, A-MEM. Hard cap 10 groups. E0–E4 must remain.

## Decision

Locked by default:

| ID | Methods | Attribution baseline |
|---|---|---|
| E0 | none | blank |
| E1 | lexical | vs E0 |
| E2 | hybrid RRF | vs E1 |
| E3 | hybrid + PPR graph-lite | vs E2 |
| E4 | E3 + selective push | vs E3 |
| E5 | extractive facts + pull | vs E2 |
| E6 | time-aware hybrid | vs E2 |
| E7 | core memory + hybrid | vs E2 |
| E8 | dual channel | vs E2/E5 |
| E9 | fact-augmented keys | vs E2 |

Defer: full GraphRAG, always-on push, HippoRAG OpenIE. Budget overflow demotes E9 then E8 then E7, never E0–E4.

## Consequences

All configs live under `experiments/`. Runner is `--config` driven. Derived facts must cite source spans.
