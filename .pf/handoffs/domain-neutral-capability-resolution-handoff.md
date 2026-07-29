# Handoff: implementation -> next

Objective:
Complete domain-neutral capability resolution and zero user capability builtin
satisfaction.

Current status:
Implemented and validated.

Input artifacts:
- `задания/processforge_domain_neutral_capability_resolution_master_prompt.md`

Files changed:
- `tools/processforge.py`
- `schemas/specialization.schema.json`
- specialization/project override smokes and helpers
- capability/specialization/snapshot/workplace docs
- `checksums/processforge.sha256`
- `dist/processforge.zip`
- `dist/processforge.manifest.json`

Files not to touch:
- Unrelated dirty files from previous specialization slices unless continuing
  those assignments.

Known issues:
- None blocking.

Required checks:
- Public release-test: passed.
- Release archive full extracted test: passed.
- `git diff --check`: passed with CRLF warnings only.

Next recommended action:
Review the combined dirty working tree and commit the validated slices if ready.
