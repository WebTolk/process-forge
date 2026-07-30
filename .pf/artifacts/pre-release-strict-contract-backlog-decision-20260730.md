# Strict-contract backlog decision for ProcessForge 1.0.0

- Date: 2026-07-30
- Run: `pre-release-remediation-20260730`
- Status: accepted for the 1.0.0 release shield
- Scope: narrow release closeout after sanitation; no `packs` model rewrite

## Decision

For the 1.0.0 public release, the strict-contract backlog is split into a
small release-blocking set and an explicit post-1.0 backlog.

The release-blocking set is limited to contracts that directly affect archive
integrity, release reproducibility, and safe recovery from partially applied
authoring transactions. Broader architectural cleanup remains valid, but is
not allowed to expand this closeout slice.

## Closed now for 1.0.0

1. Permanent crash-recovery smoke instead of waiver.
   - Contract: a persisted incomplete authoring journal can be recovered after
     a simulated crash between publish and rollback.
   - Contract: corrupted backups are not falsely marked as `rolled_back`; they
     end in `recovery_required`.
   - Evidence gate: `tools/smoke_authoring_crash_recovery.py`, included in
     `release-test --public`.

2. Release-manifest v1 provenance contract.
   - Contract: `dist/processforge.manifest.json` is schema-versioned as
     `schema_version: 1` for the first public release.
   - Contract: `release-pack` captures clean Git `HEAD`, `HEAD^{tree}`,
     deterministic `source_date_epoch`, final ZIP size/SHA-256, entry count,
     per-file size/SHA-256, and official pack manifest provenance.
   - Contract: `release-archive-test` validates the sidecar as a consumer:
     shape, archive filename/size/hash, file list, entry count, member
     safety, and per-file size/hash.
   - Evidence gates:
     `schemas/release-manifest.schema.json` and
     `tools/smoke_release_manifest_provenance_contract.py`.

3. Clean-source release shield.
   - Required sequence: clean commit, full `release-test --public`, final
     `release-pack`, full `release-archive-test`, checksum verification, and
     `git diff --check`.
   - Live logs must stay outside `.pf/runtime`, because `release-test` starts
     by cleaning release-generated runtime state.

4. First-public versioning.
   - Public contracts introduced for 1.0.0 use `schema_version: 1`.
   - Historical `.pf` reports that mention v2 are process history, not current
     release authority.

## Deferred as post-1.0

These items remain useful product work, but are not part of this final release
closeout slice:

1. Full MCP auth model.
   - Keep the current structural checks for 1.0.0.
   - Design executable provider-specific auth verification after release.

2. Provider/runtime contract implementation.
   - Keep existing update/provider validation.
   - Add deeper provider runtime execution contracts after release.

3. Lifecycle/process invariant hardening beyond the current public smokes.
   - Keep current schema and smoke coverage for 1.0.0.
   - Split stricter lifecycle invariants into separately reviewable tasks.

4. Distribution-as-installed-tool boundary.
   - Current extracted-archive full test still uses the repository's project
     `.pf` files as part of its self-test surface.
   - A cleaner distribution root with `packaging/distribution-AGENTS.md` and
     no project `.pf` files is accepted as a follow-up slice, because doing it
     properly requires changing extracted release-test assumptions rather than
     merely removing files from the ZIP.

5. Legacy/flat alias cleanup that is not currently public-contract-breaking.
   - Do not add compatibility shims.
   - Do not broaden this closeout into a global rewrite.

## Release rule

If any item from the post-1.0 list is promoted before publication, it must be
opened as a separate narrow task with its own assignment, implementation,
review, and release shield. It must not be bundled implicitly into this
closeout.
