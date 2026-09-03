# Distribution consistency audit

Status: blocked before archive creation.

## Scope and evidence

Audit target: the live `dev` checkout on 2026-08-21, following `задания/process-forge-distribution-release-docs-sync-master-prompt.md`.

`RELEASE_DIRS` includes `src`; `RELEASE_REQUIRED_PATHS` explicitly requires `src/processforge_core`. A non-writing `release-pack --dry-run` resolved a release set of 840 files and included `bin/pf.py`, `checksums/processforge.sha256`, and the public documentation surface. The source layout therefore declares the Python Core to be part of the release contract.

## Checks performed

| Check | Result | Evidence |
| --- | --- | --- |
| `validate-process-forge-checksums.py --check` | FAIL | Inventory has stale hashes and misses current Core/Runtime/Event files. |
| `validate-public-cleanliness.py` | FAIL | Four false-positive findings; classified separately. |
| `release-check` | PASS for structural checks | Required paths, including `src/processforge_core`, are present; private runtime/archive prefixes are excluded. |
| `release-pack --dry-run` | PASS | 840 prospective entries; no archive written. |
| `release-pack` | BLOCKED | It requires a clean Git source checkout. |
| `release-archive-test --extracted-test quick` | NOT RUN | No archive exists because `release-pack` correctly blocked it. |
| `smoke_processforge_core_package_bootstrap.py` | PASS | Source checkout only. |
| `smoke_central_event_ingress.py` | PASS | Source checkout only. |
| `smoke_conversation_completeness.py` | PASS | Source checkout only. |
| `smoke_central_event_replay.py` | PASS | Source checkout only. |

## Blocking condition

The repository has a large pre-existing dirty set, including Central Event Ingress implementation files and prior `.pf` work. The task prompt requires a separate clean commit and push before this release-sync stage. `release-pack` enforces that same rule through `release_git_provenance()`.

No archive-level PASS may be claimed until the operator commits or otherwise hands off that baseline and the subsequent release/docs changes are again made from a clean Git state.

## Gate gap observed

`command_release_pack()` calls `release_checks()` and Git provenance, but it does not itself run checksum validation or public-cleanliness validation. Thus, on an otherwise clean checkout it can create an archive whose checksum inventory is stale and whose public-cleanliness gate fails. The corrective slice must add the narrow required gate(s), with regression coverage, after a write-scope handoff for `tools/processforge.py`.
