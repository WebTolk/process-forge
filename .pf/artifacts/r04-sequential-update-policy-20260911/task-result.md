# R04 task result

Completed user-directed policy change.

- All tracked historical `dist/` archives and manifests are removed.
- Core update applies Core payload and manifest before Workplace migration.
- A failed post-Core Workplace migration retains the new Core version and is
  marked `manual_repair_required`.
- Documentation states Core → Workplace → project-work order and prohibits
  independent parallel applies.

Validation PASS: `smoke_core_update_manifest.py`,
`smoke_core_update_migration_sources.py`, schema validation, checksum rewrite,
and `git diff --check`. Windows symlink subfixtures are skipped because the
current OS account lacks symlink privilege.