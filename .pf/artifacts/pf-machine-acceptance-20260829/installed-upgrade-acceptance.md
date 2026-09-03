# Installed Upgrade Acceptance

## Candidate

- Version: `1.2.1`.
- Candidate commit: `6f72af1` (isolated local clone).
- Archive: `processforge-1.2.1.zip`.
- Entries: `894`.
- SHA-256: `9722d7e87b52bec52926cfaa801c49ced588867fd78fd66c62f08acdf36040e1`.
- Archive manifest, `PROCESSFORGE_VERSION` и `RELEASE_ARCHIVE_VERSION`: `1.2.1`.

## Gates

- Manifest, physical entries, file sizes/hashes and current candidate tree parity: PASS.
- Full `release-test` from extracted final archive: PASS, 1105.41 s.
- Standard target-side `core-update plan`: 0 blockers, 4 changed, 889 unchanged, no local modifications.
- Standard target-side `core-update apply --confirm`: applied; backup `core-update-20260829T105134Z`.
- Installed Runtime after update: ready, PID `13068`, core/installed version `1.2.1`.
- Installed governance and MCP smokes: PASS.

Earlier isolated 1.1.0 -> 1.2.1 -> 1.1.0 matrix proved confirm-required apply, exact rollback parity, local-modification blocking, forced rollback and corrupt-archive rejection. The 1.1.0 updater itself is not used as a readiness criterion; the tested updater is the target 1.2.1 implementation.
