## 2026-08-22 14:01 - codex-main

Task: Verify live Codex event capture through chat and MCP.
Files changed: `.pf/artifacts/mcp-core-codex-capture-verification-20260822/live-capture-verification.md`; this log.
Artifacts changed: live capture verification report.
Templates used: none.
Tools used: fresh `codex exec` host with trusted hooks; private raw/ledger inspection; installed beta.2 stdio MCP session reads; `events-validate`; focused source-path inspection.
Decisions: Do not change Python Core during an assurance task. Classify the transcript loss as a confirmed ordering defect and the missing `Stop` as an observed Codex exec event-surface limit until separately remediated or documented.
Risks: Existing synthetic smoke does not reproduce asynchronous native hook scheduling and therefore cannot establish the live chat-capture guarantee.
Next steps: Create an implementation task only after accepting a remediation design for session-start ordering; add a real-host regression that requires raw, transcript and MCP chat evidence.
Handoff: Raw ingress and session MCP work; full message capture does not.
