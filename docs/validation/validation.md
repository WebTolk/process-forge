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

Creates a deterministic SHA-256 inventory for public files and checks immutable context packages for recorded checksum fields.

## Public Cleanliness

```bash
python tools/validate-public-cleanliness.py
```

Checks public product files for private paths, secrets, temporary private notes, and private internal references.
