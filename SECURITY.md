# Security

- Do not commit API keys, `.env`, session transcripts with secrets, or model weights.
- Eval sandboxes must deny read/glob/bash/webfetch. Ground-truth files stay outside the OpenCode session workspace.
- Retrieved memory is untrusted citation data and must not override system instructions.
- Connectors must honor ACL groups on every hit.
