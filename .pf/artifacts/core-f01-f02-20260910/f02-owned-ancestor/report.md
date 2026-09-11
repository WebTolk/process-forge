# F02 owned-ancestor correction

- Timestamp: 2026-09-10T05:22:23Z
- Status: implemented; primary verification pending

## Changes

- Allowed only exact removed, owned, regular non-symlink file ancestors.
- Preserved blockers for collisions, symlinks, unchanged-owned paths, and user paths.
- Added smoke coverage for clean, modified, forced, backup, and refusal cases.

## Checks

- PASS: AST syntax checks for both changed Python files.
- NOT RUN: smoke and full test suites, per assignment instruction.
- NOT RUN: standalone rollback; backup records were verified by smoke assertions.

Primary verification remains required.