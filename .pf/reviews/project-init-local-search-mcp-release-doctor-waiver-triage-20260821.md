# Release doctor capability-waiver triage

## Result

The failing public release-suite smoke was caused by an assertion at the wrong
command boundary, not by the waiver implementation.

`project-init --apply` intentionally emits a concise YAML summary. It contains
`status: blocked` and `doctor.status: fail`, but not the full doctor diagnostic.
The exact message `capability registry declarations are missing` is emitted by
the direct `doctor-project` command.

## Evidence

- A direct `doctor-project` before waivers exits non-zero and prints the missing
  registry declaration diagnostic.
- `tools/processforge.py` classifies unresolved required capabilities as FAIL;
  after active, non-expired runtime-access waivers it emits WARN instead.
- The repaired smoke asserts the concise init result first, the exact direct
  doctor diagnostic before waivers, and successful doctor execution after the
  waiver artifact is written.

## Disposition

The smoke contract was repaired in
`tools/smoke_doctor_project_capability_waiver.py` and passed in a writable local
environment. The independent follow-up review accepted the narrowed contract in
`.pf/reviews/project-init-local-search-mcp-doctor-waiver-smoke-review-20260821.md`.
