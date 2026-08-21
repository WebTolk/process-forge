# Documentation Update Report

## Updated public truth

English and Russian concept pages now describe the Python Core raw-first event path, central ingress, durable replay, conversation completeness, agent/session relations, Runtime MCP boundary, and chat relay.

## Limitations made explicit

- Raw event storage uses hourly shards, per-event indexes, and locks; it is not a substitute for an externally managed high-volume event store.
- Payloads are capped at 1 MiB.
- Codex hook registration is not bundled as a repository hook configuration; documented runtime ingress remains explicit and opt-in.

## Verification

- `smoke_windows_utf8_docs` passed in the public release suite.
- `validate-public-cleanliness.py --root .` passed after documentation updates.
