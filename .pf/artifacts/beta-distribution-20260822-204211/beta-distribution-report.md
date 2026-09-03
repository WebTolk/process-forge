# Beta Distribution Report

Date: 2026-08-22

## Output

- Archive: $archive
- Manifest: $manifest
- Archive size: 1264774 bytes
- Manifest size: 157681 bytes
- Archive file count: 863
- Contains processforge-core.manifest.json: yes

## Validation

- elease-check --root .: pass
- elease-pack --root . --output dist\processforge-1.0.2-beta-20260822-204211.zip: pass
- Required archive entries: pass
- Forbidden private/repository runtime entries: pass

## Logs

- Release check log: $releaseCheckLog
- Release pack log: $packLog

## Notes

This is a beta-named distribution archive. It does not modify VERSION.
