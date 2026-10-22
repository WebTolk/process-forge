# Test plan and cases

2026-10-22. Acceptance target: additive guidance, unchanged real evidence acceptance.

- Original matcher kind/status/identifier vocabulary, aliases and gate precedence.
- Latest failed record overrides older success; input/artifact cross-kind matching.
- Every generated positive/N/A example passes real normalization and matching;
  N/A missing reason/support fails, no new acceptance policy.
- Invalid/missing/outside/directory/absolute paths, stored missing/wrong hash,
  changed file and explicit resubmission. Caller hash continues to be recomputed.
- Pure advisory projection does not mutate inputs; unmatched evidence is retained
  without being promoted to a satisfied requirement.
- Terminal assignment in active Run, terminal Run, invalid capsule and blocked
  permissions have no actionable templates. Handoff requirement uses notes.
- Isolated project with explicit scoped creation: source CLI JSON and ordinary
  stdio MCP parity, invalid request leaves assignment bytes unchanged, wrong kind
  does not advance, corrected submission advances, live process drift cannot
  change pinned templates, exact selectors can inspect completed Work.
- Outcome-specific next-entry gates are conditional; required:false/blocking:true
  follows the existing transition rule and succeeds only after real submission.
- Existing current-state, missing-gate, linear, evidence-recording, pinned-process,
  invalid-request-recovery and file-freshness smoke regressions.

Registered shared Python launcher runs lint, format, mypy and pytest. Repeat final
source tests in a clean public HEAD snapshot with only scoped overrides, excluding
unrelated WIP. Checksum generator/check uses that same snapshot. No browser UI,
release ZIP, installed Core, connected-host update or infrastructure qualification.
