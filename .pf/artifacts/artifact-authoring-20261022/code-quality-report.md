# Code quality and qualification

2026-10-22. Final candidate is the clean base + owned overrides in
qualification-inputs.json. Three changed Core modules and three new test modules
were checked. Tools: Python 3.14.3, Ruff 0.17.1, pytest 9.1.1, mypy 2.4.0.
The project interpreter and dependencies remain authoritative; shared QA supplies
tools only. No dependency installation or import-error suppression was used.

Registered launcher commands (resolved private roots are retained only locally):
- python <shared-python-qa>/qa.py --project-root <clean-source> lint --
  src/processforge_core/evidence/authoring.py src/processforge_core/evidence/validation.py
  src/processforge_core/work/state.py tests/artifact_authoring
- Same scoped files with format: six files already formatted, exit 0.
- Same scoped files with typecheck -- --follow-imports=silent and task-local cache:
  no issues in six files, exit 0. Existing fallback config; no missing-import ignore.
- test: 104 cases, exit 0; eight existing smoke scripts, all exit 0.

Formatting/import fixes were separate explicit operations limited to owned files.
The small existing validator was formatted; the large facade and adapters were
not touched. Primary review addressed typing, decoder line numbers, paired HTML,
limits visibility and parser complexity; see review-findings.md. Immutable capsule
denies subagents, so no independent-agent review is claimed.

Native checksum generator/check: PASS, 1,463 public entries over clean source,
delta limited to five owned public files. Baseline preservation: no unexpected
changes; the future token-card edit is verified as an exact appended input link,
with no change to status, execution mode, ownership or grants. Its native
task-doctor passed 12/12. Planning supplement is separate commit 61595a92.

No meaningful browser/dependency/security-package/ZIP gate is added for this
stdlib-only advisory parser and stored projection. No infrastructure/device
qualification is implied. Delivery awaits actual push and full dev SHA readback.
