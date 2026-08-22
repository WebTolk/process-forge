# Beta Installation Contract Audit

## Result

`pass_with_conditions`

The required beta installation acceptance cases can be defined from the allowed sources. Confidence is limited because the capsule did not allow reading the process definition YAML files for `workplace-initialization`, `project-onboarding`, or `project-initialization`; this review is based on the CLI implementation, project manifest, and beta orchestration plan only.

## Sources Reviewed

- `tools/processforge.py`
- `.pf/process-forge.yaml`
- `.pf/artifacts/beta-release-qualification-20260822/orchestrator-plan.md`

## Contract Observations

- The active project manifest is file-only, linked install mode, with runner/backend optional.
- `workplace-init --apply` creates the workplace layer, required registries, runtime/log/artifact folders, runs `doctor-workplace`, and writes bootstrap report/review/handoff.
- `project-onboard --apply` creates project `.pf/`, local launcher, project artifacts, context snapshot outputs, event records, then runs `doctor-project`.
- `project-init-repair --apply` is intended as deterministic refresh-only repair: refresh context snapshot, rerun `doctor-project`, update onboarding doctor artifacts, and emit a context refresh event.
- `clean --release` removes only contained generated artifacts: `.pf/runtime`, cache dirs, `.pyc`, and `.pyo`; it skips `.git`, `.idea`, and `.serena`, and retries Windows read-only removals.

## Acceptance Cases

### BIC-01 Clean Archive Provenance

Commands:
```bash
python tools/processforge.py release-pack --root <clean-candidate-root> --output dist/processforge-beta.zip
python tools/processforge.py release-archive-test --archive dist/processforge-beta.zip --manifest dist/processforge-beta.manifest.json --root <clean-candidate-root> --extracted-test full --timeout-scale <scale>
```

Expected:
- `release-pack` preflight passes public cleanliness and checksum inventory.
- Archive manifest has deterministic build metadata, source commit/tree, archive SHA-256, entry count, sorted unique file list, and per-file hashes.
- Extracted `bin/pf.py --help`, `tools/processforge.py --help`, and extracted `release-test --public` pass.
- GO evidence records archive path, archive SHA-256, entry count, source commit, and manifest path.

### BIC-02 Clean Installation

Fixture:
- Fresh extracted beta distribution.
- Empty isolated workplace.
- Empty isolated project root.

Commands:
```bash
python <distribution>/bin/pf.py workplace-init --workplace <workplace> --profile software --apply
python <distribution>/bin/pf.py project-onboard --project-root <project> --workplace <workplace> --type generic --apply
python <distribution>/bin/pf.py doctor-workplace --root <workplace>
python <project>/.pf/runtime/bin/pf.py doctor-project --project-root <project>
python <project>/.pf/runtime/bin/pf.py doctor-context --project-root <project>
```

Expected:
- All commands exit `0`.
- Workplace contains `workplace.yaml`, required registries, `runtime/events/events.ndjson`, bootstrap report/review/handoff.
- Project contains `.pf/process-forge.yaml`, `.pf/process-forge.local.yaml`, `.pf/runtime/bin/pf.py`, first assignment, onboarding reports/reviews, handoff, and fresh context snapshot.
- `.gitignore` protects `.pf/process-forge.local.yaml`, `.pf/runtime/`, and `.pf/cache/`.
- Public manifests contain no secrets or private absolute paths.
- Event journal includes workplace initialization, workplace doctor, project onboarding, snapshot refresh, project doctor, and onboarding completion events.

### BIC-03 Repeat Installation

Commands:
```bash
python <distribution>/bin/pf.py workplace-init --workplace <workplace> --profile software --apply
python <distribution>/bin/pf.py project-onboard --project-root <project> --workplace <workplace> --type generic --apply
```

Expected:
- Repeat run exits `0`.
- Registry IDs are not duplicated.
- `.gitignore` entries are not duplicated.
- Global agent instruction bounded section is not duplicated.
- Static generated artifacts are unchanged or intentionally rewritten without creating `.candidate` files.
- Event journals may append new events; current snapshot may refresh and add one generation.
- Lifecycle reports must not accumulate duplicate repeated `## Doctor Status` sections.

Condition:
- Visible code appends project doctor status to the existing onboarding report during onboarding/repair. The beta gate should explicitly check this; duplicate report sections should be treated as a NO-GO installation idempotence defect unless product owners accept append-only report history.

### BIC-04 Repair Safety

Commands:
```bash
python <project>/.pf/runtime/bin/pf.py project-init-status --project-root <project> --json
python <project>/.pf/runtime/bin/pf.py project-init-repair --project-root <project> --repair-action refresh_context --reason beta-repair-dry-run
python <project>/.pf/runtime/bin/pf.py project-init-repair --project-root <project> --repair-action refresh_context --reason beta-repair-apply --apply
python <project>/.pf/runtime/bin/pf.py doctor-project --project-root <project>
python <project>/.pf/runtime/bin/pf.py doctor-context --project-root <project>
```

Expected:
- Dry run is non-mutating.
- Apply exits `0`, refreshes current snapshot, writes one snapshot generation, removes stale marker if present, writes context refresh report, and emits `context.snapshot.refreshed`.
- Repair does not alter semantic project artifacts such as assignments, process manifests, package declarations, or user-authored reports except for documented doctor/status refresh artifacts.
- Post-repair doctors pass.
- `restore_deterministic_artifacts` is either implemented with distinct behavior or rejected/documented; it must not silently behave as `refresh_context` while reporting a different requested action.

### BIC-05 Windows Cleanup

Fixture:
- Generated `.pf/runtime`.
- `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`.
- `.pyc` and `.pyo` files, including Windows read-only files.
- Control files under `.git`, `.idea`, `.serena`, and normal source/docs files.

Command:
```bash
python <distribution>/bin/pf.py clean --root <fixture-root> --release
```

Expected:
- Command exits `0`.
- Generated caches, `.pyc`, `.pyo`, and `.pf/runtime` are removed.
- Windows read-only generated files are removed after attribute retry.
- `.git`, `.idea`, `.serena`, source files, docs, manifests, archives, and files outside `<fixture-root>` are preserved.
- Second cleanup run exits `0` and reports no unexpected removals.
- If host temp root deletion fails after product cleanup because of OS locks, report it as an environment cleanup blocker, not a product cleanup failure, unless generated files remain inside the root.

## Conditions For Beta GO

- All five acceptance cases pass from a fresh extracted archive, not only from the development checkout.
- Exact archive SHA-256, manifest SHA-256 or path, source commit, fixture layout labels, command exits, and doctor results are captured in the beta validation report.
- Product defects are separated from environment blockers.
- Repeat-install duplicate report sections and `project-init-repair --repair-action restore_deterministic_artifacts` behavior are resolved or explicitly accepted before GO.