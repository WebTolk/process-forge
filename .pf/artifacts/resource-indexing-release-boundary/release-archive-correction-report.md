# Release Archive Correction Report

## Status

Pre-commit release archive build is blocked as designed because `release-pack` requires a clean Git source tree.

Observed:

```text
FAIL: release-pack requires clean git source before publishing
```

## Confirmed Current Gates

- `python tools/processforge.py release-check --root .` PASS.
- `python tools/validate-public-cleanliness.py --root .` PASS.
- `python tools/validate-process-forge-checksums.py --root . --check` PASS after checksum refresh.
- Sidecar manifest contract code already checks sorted unique file paths, physical ZIP member matching, per-file hashes, archive hash/size, and current-root freshness when `--root` is supplied.

## Required Next Step

Commit the source/report changes, then run:

```text
python tools/processforge.py release-pack --root . --output dist/processforge-1.0.2-resource-indexing-20260822.zip
python tools/processforge.py release-archive-test --archive dist/processforge-1.0.2-resource-indexing-20260822.zip --root . --extracted-test quick
python tools/processforge.py release-archive-test --archive dist/processforge-1.0.2-resource-indexing-20260822.zip --root . --extracted-test full
```
