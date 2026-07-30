# Run Plan: Pre-release ProcessForge Remediation

Canonical implementation plan:
`.pf/artifacts/pre-release-remediation-plan-20260730.md`.

The run is open. No implementation has started.

Entry gate:

- read the audit and review;
- approve the schema-authority ADR;
- establish one-writer ownership for `tools/processforge.py`;
- record the exact pre-existing dirty baseline before edits.

Exit gate:

- all Critical and High audit findings are closed by tests and evidence;
- Medium findings are fixed or have explicit reviewed waivers;
- source and extracted archive gates pass from a clean traceable commit state;
- release review changes from `fail` to `pass` or `pass_with_conditions`.
