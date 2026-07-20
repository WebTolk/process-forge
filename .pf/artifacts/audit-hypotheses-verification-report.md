# Audit Hypotheses Verification Report

Date: 2026-07-20 22:26 +04:00
Agent: Codex

## Scope

This report verifies the external audit hypotheses H1-H5 against the real local
ProcessForge checkout. Fixes were applied only where the local diagnostic pass
confirmed a reproducible issue or a concrete static risk.

The checkout already contained the previous release-sync working tree changes.
This verification was performed on top of that state without reverting it.

## Hypothesis Results

| Hypothesis | Result | Summary |
| --- | --- | --- |
| H1 `smoke_update_framework_validation.py` may hang | Partial | No local hang, but the smoke had no subprocess timeout and left a trusted `http://localhost:8080` source before `entity-sources rebuild`. |
| H2 `release-archive-test` may hang | Not confirmed | Local archive test passed and printed the nested `release-test` RUN step. |
| H3 release archive may be stale | Not confirmed | Canonical archive and manifest matched current release surface after rebuild. |
| H4 source/dev zip may contain runtime/cache garbage | Confirmed | `.pf/runtime` and `tools/__pycache__` appeared after test commands; `clean --release` removed them. |
| H5 platform-agnostic boundary may be broken | Not confirmed | Boundary grep outside allowed docs/examples/policy surfaces returned no matches. |

## Diagnostic Pass

| Command | Result | Exit | Duration | Last visible step | Hypothesis |
| --- | --- | ---: | ---: | --- | --- |
| `python tools/smoke_update_framework_validation.py` | pass | 0 | 5.415s | `PASS: update framework validation regression smoke checks passed.` | H1 |
| `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip` | pass | 0 | 92.813s | `RESULT: PASS` | H2 |
| archive/source inspection | pass | 0 | n/a | zip and manifest matched `384` files | H3 |
| runtime/cache inventory | partial | 0 | n/a | found `.pf/runtime` and `tools/__pycache__` | H4 |
| platform boundary grep | pass | 1 | n/a | no matches | H5 |

Static H1 findings:

- `tools/smoke_update_framework_validation.py` used `subprocess.run()` without
  a timeout.
- The smoke wrote trusted `http://localhost:8080/catalog.json` and validated it.
- The next negative scenario invoked `pf update entity-sources rebuild` while
  that registry value was still present.

## Fixes Applied

H1:

- Added `PF_TIMEOUT_SECONDS = 30` and passed it to the smoke's subprocess
  helper.
- Added `RUN: pf ...` output before each helper invocation, so a future timeout
  is localized to a visible command.
- Reset the temporary update source registry back to the safe HTTPS fixture
  before the negative `entity-sources rebuild` override validation.

H4:

- No additional code change was needed in this task. The current
  `python bin/pf.py clean --root . --release` behavior removed `.pf/runtime`
  and Python caches before packing.

No fixes were applied for H2, H3, or H5 because the local checks did not confirm
those hypotheses.

## Retest Results

| Command | Result | Duration | Last visible step |
| --- | --- | ---: | --- |
| `python -m py_compile tools/smoke_update_framework_validation.py` | pass | n/a | no output |
| `python tools/smoke_update_framework_validation.py` | pass | 5.071s | `PASS: update framework validation regression smoke checks passed.` |
| `python tools/smoke_update_framework_readonly.py` | pass | 3.185s | `PASS: update framework read-only smoke checks passed.` |
| `python tools/smoke_multiagent_assignment_contract.py` | pass | 0.884s | `PASS: multiagent assignment contract smoke` |
| `python tools/smoke_manifest_driven_platforms.py` | pass | 3.929s | `RESULT: PASS` |
| `python tools/smoke_platform_inheritance.py` | pass | 9.669s | `RESULT: PASS` |
| `python tools/validate-process-forge-schemas.py --root .` | pass | 0.678s | schema validation passed |
| `python tools/validate-public-cleanliness.py --root .` | pass | 0.374s | public cleanliness passed |
| `python tools/validate-process-forge-checksums.py --root . --check` | pass | 0.152s | checksum inventory matches |
| `python bin/pf.py release-test --root .` | pass | 92.243s | `RESULT: PASS` |
| `python bin/pf.py release-pack --root . --output dist/processforge-v1.0.0.zip` | pass | 0.813s | `FILES: 384` |
| `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip` | pass | 94.086s | `RESULT: PASS` |
| `git diff --check` | pass | n/a | whitespace warnings only |

## Release Archive State

Final archive inspection:

- source release-surface file count: `384`
- archive file count: `384`
- manifest file count: `384`
- manifest version: `1.0.0`
- zip and manifest match 1:1: yes
- missing expected files: none
- forbidden entries: none
- stale archive entries: none

Required update CLI entries were present in archived `tools/processforge.py`:

- `update bootstrap-source`
- `update sources-list`
- `update entity-sources`
- `update manifest`

Required update framework files and smoke files were present, including:

- `schemas/entity-update-sites.schema.json`
- `schemas/installed-subjects.schema.json`
- `schemas/installed-update-sites.schema.json`
- `schemas/normalized-update-manifest.schema.json`
- `schemas/update-candidates.schema.json`
- `schemas/update-notifications.schema.json`
- `schemas/update-site-overrides.schema.json`
- `schemas/update-source-registry.schema.json`
- `templates/registries/installed-subjects.yaml`
- `templates/registries/update-site-overrides.yaml`
- `templates/registries/update-sources.yaml`
- `templates/runtime/update/installed-update-sites.json`
- `tools/smoke_multiagent_assignment_contract.py`
- `tools/smoke_update_framework_readonly.py`
- `tools/smoke_update_framework_validation.py`

## Platform Boundary

The platform/domain marker grep over release-facing core surfaces outside
`docs/**`, `examples/**`, and explicit policy surfaces returned no matches.
`python tools/validate-public-cleanliness.py --root .` also passed.

## Remaining Limitations

- POSIX was not executed in this Windows workspace.
- `release-test` and `release-archive-test` may recreate private `.pf/runtime`
  event/cache directories after they run. The final release archive excludes
  them, and `clean --release` removes them before packing.
- `git diff --check` passed, but Git printed line-ending normalization warnings
  for existing Windows checkout behavior.
