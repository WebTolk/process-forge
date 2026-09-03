# Core Manifest Design

## Contract

File name: `processforge-core.manifest.json`

The manifest is installed at the ProcessForge core root and is also embedded into release archives.

Required fields:

- `schema_version: 1`
- `kind: processforge.core_manifest`
- `version`
- `generated_at`
- `source`
- `files[]`
  - `relative_path`
  - `size`
  - `sha256`

## Ownership Semantics

The manifest defines PF-owned payload files. The manifest control file itself is not listed as an owned payload file to avoid self-hash recursion.

Derived/local state is excluded:

- `runtime/`
- workplace data
- project `.pf`
- caches
- SQLite indexes
- update journals and backups

## Path Rules

Accepted paths are normalized relative paths under core root.

Rejected:

- absolute paths
- drive-qualified paths
- UNC paths
- backslashes
- empty segments
- `.`
- `..`
- paths resolving outside core root
- `processforge-core.manifest.json` as a payload file

## Release Integration

`release-pack` now generates `processforge-core.manifest.json` and writes it into the archive. The manifest timestamp uses release provenance `generated_at`, not wall-clock time, to preserve deterministic release archives.
