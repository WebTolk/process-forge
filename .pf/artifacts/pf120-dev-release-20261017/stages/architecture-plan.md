# architecture-plan

Status: ready; primary / release-engineer, 2026-10-17.

Execution architecture: exact clean detached LF worktree -> native source suite and release-pack -> consumer full archive suite -> immutable archive/hash plus native read-only plan/checkpoint -> guarded app-server stop -> one native apply -> guarded start -> installed manifest/byte/CLI/Runtime checks -> independent installed MCP suite -> actual connected-host provenance and calls. Use existing launchers and commands without product changes. Record per-command raw logs privately and safe hash/count receipts publicly; keep data roots/provenance explicit. Restore app-server service if update fails, inspect journals rather than replay apply. Complete review and native doctors, commit scoped release evidence and read back both remotes. Risks and pending checks are listed in ../plan.md.

Next: follow the pinned native process and ../plan.md; do not edit this evidence after transition.
