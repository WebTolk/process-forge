# Public Core Audit Review

Review date: 2026-07-25.

## Result

PASS.

## Review Notes

- Public and dogfooding command ownership is explicit in `ReleaseCommand.layer` and `ReleaseCommand.public_gate`.
- Public archive hygiene is enforced both by `.processforge-releaseignore` and by `inspect_release_archive`.
- Dogfooding tests remain executable through `.pf/dogfooding/run_dogfooding_tests.py`.
- Dogfooding tests are also reachable through `python bin/pf.py dev-test --root .` and `python bin/pf.py dogfood-test --root .`.
- The old checksum location is no longer part of the release contract.

## Validation

- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python .pf/dogfooding/run_dogfooding_tests.py --list`: PASS
- `python .pf/dogfooding/run_dogfooding_tests.py --suite supervisor-stress --timeout-scale 1`: PASS
- `python bin/pf.py dev-test --root . --list`: PASS
- `python bin/pf.py dev-test --root . --suite supervisor-stress --timeout-scale 1`: PASS
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS
- `python bin/pf.py release-test --root . --public --timeout-scale 1`: PASS
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS
- Archive hygiene scan: PASS, 439 files, 0 forbidden entries
- `git diff --check`: PASS

## Residual Risks

- Historical `.pf` evidence files may still mention old `tools/smoke_*` paths; those are local audit history and are excluded from public archives.
- Dogfooding scripts are intentionally outside public release archives, so archive-extracted public tests cannot run dogfooding suites.
