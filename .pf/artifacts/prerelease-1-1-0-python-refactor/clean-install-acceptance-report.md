# Clean Install Acceptance Report

Date: 2026-08-23
Status: PASS

## Archive Under Test

- Archive: `dist/processforge.zip`.
- Manifest: `dist/processforge.manifest.json`.
- Version: `1.1.0`.
- Files: `869`.
- Size: `1280633` bytes.
- SHA256:
  `fd4c9948de1270a2b836c19796b6882ab994ec61dde854a44403f949661f43dc`.
- Manifest source commit:
  `49695f7f0a156f21382a91c5da44dffab5164d7c`.

## Installed-RC Checks

- PASS: extracted `bin/pf.py --help`.
- PASS: extracted `tools/processforge.py release-check`.
- PASS: `workplace-init --apply`.
- PASS: `doctor-workplace --root`.
- PASS: `project-onboard --type generic --apply`.
- PASS: `project-context-refresh --apply`.
- PASS: `project-context-check --json` returned `status=fresh`,
  `resource_readiness.status=fresh`, `execution_readiness.status=ready`.
- PASS: `search-index refresh`.
- PASS: archive-local `tools/smoke_project_init_local_search_mcp.py`.

## Supporting Gates

- PASS: full public `release-test` from clean source.
- PASS: quick extracted archive test.
- PASS: full extracted archive test.
- PASS: source-level `smoke_project_init_acceptance`.
- PASS: source-level `smoke_long_lived_runtime`.
