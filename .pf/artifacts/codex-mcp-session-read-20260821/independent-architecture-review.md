# Independent architecture review

Reviewer: independent architecture reviewer, 2026-08-21.

Initial High findings were accepted and corrected before validation:

- a call argument could override a process-bound `--session`;
- raw replay did not restore conversation messages after raw-first persistence;
- hook installation could synchronously delay Codex and exceeded SessionEnd's limit.

Final disposition: approved for this slice after corrections. A configured MCP
session now rejects a different call argument; replay rebuilds prompt/Stop chat
through the sole existing writer; non-SessionEnd observers are async and every
handler is bounded to three seconds. Session read authorization is now a pure
Ledger lookup. Remaining design constraint: actual Codex hook trust/loading is
an explicit operator verification, not a claim made by the installer.
