# Validation

ProcessForge ships with lightweight local validators.

## Schema and Structure

```bash
python tools/validate-process-forge-schemas.py
```

Checks required files, JSON schema syntax, seed process fields, manifest references, and basic yaml-like file structure.

## Checksums

```bash
python tools/validate-process-forge-checksums.py
```

Checks the current public files against the existing deterministic SHA-256 inventory.

Run with `--check` (default when `--write` is not set) to validate existing inventory
files. Run with `--write` to generate/update `checksums/processforge.sha256`.

This command checks only public file inventories. It does not validate context capsules.

Context and capsule checks use explicit doctor commands:

```bash
python bin/pf.py project-context-check --project-root <project-root> --json
python bin/pf.py capsule-doctor --project-root <project-root> --capsule <capsule-path>
```

`project-context-check` validates project context snapshot freshness.
`capsule-doctor` validates the assignment capsule and its context checksum contract.

## Public Cleanliness

```bash
python tools/validate-public-cleanliness.py
```

Checks public product files for private paths, secrets, temporary private notes, and private internal references.
