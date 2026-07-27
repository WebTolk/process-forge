# Software Lifecycle Process Alignment Report

Timestamp: 2026-07-27T17:56:26+04:00
Agent/role: Codex primary agent
Task: processforge_software_lifecycle_process_alignment_master_prompt.md
Status: completed

## Previous Mismatch

`software-feature-development` described work "from intake through release and evolution", but the actual process only had `intake`, `architecture`, `implementation`, and `assurance` stages. Release and evolution were promised in prose without stages, gates, or artifacts.

## New Lifecycle

The process now covers:

1. orchestration
2. intake-scope
3. investigation
4. domain-modeling
5. architecture-plan
6. implementation
7. code-assurance
8. release-delivery
9. evolve

Lifecycle modes were added under `metadata.lifecycle_modes`: `full`, `feature`, `bug_fix`, `debug_loop`, and `implementation_only`.

## Legacy Mapping

| Legacy `.webtolk` contract | ProcessForge contract |
| --- | --- |
| `.webtolk` orchestration | PF `orchestration` |
| `.webtolk` intake | PF `intake-scope` |
| `.webtolk` investigation | PF `investigation` |
| `.webtolk` domain | PF `domain-modeling` |
| `.webtolk` architecture | PF `architecture-plan` |
| `.webtolk` implementation | PF `implementation` |
| `.webtolk` assurance | PF `code-assurance` |
| `.webtolk` release | PF `release-delivery` |
| `.webtolk` evolve | PF `evolve` |
| `.webtolk` updated-cursor | PF `instruction-update-proposal` |
| `.webtolk` delivery/build runner | PF delivery/build profile, not process |

## Delivery Boundary

Delivery/build/package/install is modeled as `execution_profile.delivery_profile`, not as a PF process id. The public core process does not hardcode Joomla or platform-specific delivery commands.

## Optional Policy

Conditional artifacts and stages must record `status: not_applicable`, a reason, and evidence. `release-delivery`, `evolve`, and `browser-verification-report` cannot be silently skipped.

## Schema Changes

No process-definition JSON Schema change was required. The existing schema already permits compatible metadata and conditional policy fields.

## Validation

- `python -m py_compile ...`: PASS
- six new software lifecycle smokes: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python bin\pf.py process-doctor --project-root . --process software-feature-development --contract-only`: PASS
- `python bin\pf.py builtin-process-catalog-doctor --root . --public`: PASS
- broad smokes from the assignment: PASS
- `release-test --only smoke_software_lifecycle_process_contract --public --fail-fast`: PASS
- `release-test --only smoke_delivery_profile_not_process --public --fail-fast`: PASS
- `python bin\pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS
- `python bin\pf.py release-test --root . --public --timeout-scale 1`: PASS
- `python bin\pf.py release-pack --root . --output dist\processforge.zip`: PASS, 630 files
- `python bin\pf.py release-archive-test --archive dist\processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS
- `git diff --check`: PASS

## Remaining Limitations

- No platform-specific delivery profile example was added to public core; the neutral software-project example shows only a generic project-local profile.
- Working tree includes earlier uncommitted updater and project-context lock-model slices; this report covers only the software lifecycle alignment slice.

