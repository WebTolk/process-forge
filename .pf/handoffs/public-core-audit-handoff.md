# Public Core Audit Handoff

## Completed

- Split public release gate from local dogfooding tests.
- Moved internal smoke scripts to `.pf/dogfooding/tests/scripts/`.
- Added dogfooding manifest, README, and runner.
- Added `dev-test` and `dogfood-test` CLI aliases for the dogfooding runner.
- Moved checksum inventory contract to `checksums/processforge.sha256`.
- Updated release pack, archive inspection, schema validation, public cleanliness, and release checklist.

## Verification

- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS
- `python bin/pf.py release-test --root . --public --timeout-scale 1`: PASS
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, 439 files
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS
- `python .pf/dogfooding/run_dogfooding_tests.py --list`: PASS
- `python .pf/dogfooding/run_dogfooding_tests.py --suite supervisor-stress --timeout-scale 1`: PASS
- `python bin/pf.py dev-test --root . --list`: PASS
- `python bin/pf.py dev-test --root . --suite supervisor-stress --timeout-scale 1`: PASS
- Archive hygiene scan: PASS, 0 forbidden entries
- `git diff --check`: PASS
