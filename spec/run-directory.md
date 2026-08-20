# Run Directory Convention

Adapted from JunfengRan/dev-env (MIT). Each SDD session creates an isolated run under `.runs/<workflowId>/<run-id>/`.

## Run ID

Format: `{YYYY-MM-DD}-{slug}-{shortHash}`

Prefer:

```bash
node tooling/sdd/cli.mjs init <run-id> --workflow delivery --slug memmaster
```

## Layout

```
.runs/<workflowId>/<run-id>/
├── run-meta.json
├── state.json
├── context-pack.json
├── snapshots/
├── observations.jsonl
├── replay-chain.json
└── artifacts/
```

Mutations go through `tooling/sdd/cli.mjs` (`apply` / `advance`). Do not hand-edit `state.json`.
