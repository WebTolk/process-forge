# Implementation Report: evolve-20261002-28

Status: completed.

## Result

Fixed `release-archive-test --timeout-scale` so the finite positive scale is passed to the extracted archive's nested `release-test` command and also scales the outer extracted-test watchdog timeout.

Added shared finite-positive timeout-scale validation for `release-test`, `dev-test` / `dogfood-test`, and `release-archive-test`. Explicit `0`, negative values, `nan`, and `inf` are rejected before checks run; missing/`None` still defaults to `1.0`.

## Changed Files

- `tools/processforge.py`
- `tools/smoke_release_archive_timeout_scale.py`
- `docs/known-limitations.md`
- `docs/ru/known-limitations.md`
- `.pf/artifacts/evolve/evolve-20261002-28/*`
- `.pf/logs/evolve-20261002-28.md`

## Verification

- `python -B tools\smoke_release_archive_timeout_scale.py`
- `python -B -m py_compile tools\processforge.py tools\smoke_release_archive_timeout_scale.py`
- `python -B tools\processforge.py release-test --root . --list --timeout-scale 0`
- `python -B tools\processforge.py release-test --root . --list --timeout-scale nan`
- `python -B tools\processforge.py release-test --root . --list --timeout-scale 1`
- `python -B tools\processforge.py release-archive-test --help`
- `git diff --check -- tools/processforge.py tools/smoke_release_archive_timeout_scale.py docs/known-limitations.md docs/ru/known-limitations.md .pf/logs/evolve-20261002-28.md .pf/artifacts/evolve/evolve-20261002-28`

## Delivery And Evolution

No release package, installed Core update, Runtime/MCP restart, publication, commit, or push was performed. PF lifecycle completed through evolve. A general `evolve-run` was executed afterward and wrote `.pf/artifacts/evolve/evolution-report.md` and `.pf/artifacts/evolve/evolution-report.yaml`.
