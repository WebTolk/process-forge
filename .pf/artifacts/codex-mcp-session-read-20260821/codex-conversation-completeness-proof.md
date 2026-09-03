# Codex conversation completeness proof

`python tools/smoke_conversation_completeness.py` passed on 2026-08-21.

The smoke creates a ledger-bound Codex session and proves `UserPromptSubmit` records one user transcript entry; repeated `Stop` delivery has the identical chat id and records one main assistant final message; `SubagentStop` records a subagent final message; and transcript content is absent from the project event journal.
