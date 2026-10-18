# a01-search-report

Status: implemented; focused runtime smokes blocked by sandbox permissions.

Changed files:

- `src/processforge_core/local_resource_search.py`
  - Enforces file-root-only authorization.
  - Canonically confines directory sources to authorized roots.
  - Rejects discovered symlinks escaping the root.
  - Bumps derived index schema to version 5.
- `tools/smoke_search_file_root_containment.py`
  - Adds positive and negative containment coverage, including symlinks where supported.

Checks:

- Syntax compilation: PASS.
- `python tools/smoke_search_file_root_containment.py`: BLOCKED by `PermissionError` creating system temporary fixtures.
- `python tools/smoke_search_source_integrity.py`: BLOCKED by the same sandbox restriction.

Primary should rerun both smoke commands in an environment permitting disposable temporary directories.