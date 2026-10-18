# Native Python core audit

Date: 2026-09-10
Repository: `D:\Dev\process-forge`
Audited commit: `901d0551773fe7a5b382b89ebe95b212b0747e83`
Scope: `src/processforge_core/core_update.py` and `src/processforge_core/local_resource_search.py`

## Verdict

Two reproducible correctness/security findings remain in the bounded scope. No product files were changed. All fixtures use system temporary directories; durable evidence is limited to this directory.

## F-CORE-01: missing migration source passes plan and leaves update state applying

Location: `src/processforge_core/core_update.py:272-276`, `:321`, `:583-612`.

Trigger: an archive contains a valid `processforge.workplace_migration` document with a `copy_if_missing` operation whose `source` is a safe relative path that is absent from the ZIP. The archive manifest may still validate because `validate_archive_payload()` checks only manifest-listed files; migration source paths are not checked during `workplace_migration_plan()`.

Expected: `build_plan()` rejects the archive with a structured `CoreUpdateError` before update state is created, or apply records a structured failed update.

Actual: `build_plan()` returns `status=planned` and migration `status=planned`. `apply_update()` reaches `archive.read(operation["source"])` and raises raw `KeyError`. Because `apply_update()` only records failure for `OSError` and re-raises `CoreUpdateError`, `runtime/core-update/in-progress.json` remains `status=applying` with no structured error.

Reproducer:

```powershell
python .pf/artifacts/codebase-audit-20260910/native-core/audit_core_update_missing_migration_source.py
```

Captured output (`migration-source-output.txt`):

```text
PLAN_STATUS planned
MIGRATION_STATUS planned
APPLY_EXCEPTION KeyError KeyError("There is no item named 'templates/missing.yaml' in the archive")
IN_PROGRESS_EXISTS True
IN_PROGRESS_STATUS applying
```

Complexity: low. During migration planning, require each `copy_if_missing.source` to be present in the archive and validate it as an archive member (ideally also require it to be manifest-owned). Add a regression asserting a structured `CoreUpdateError`, no `applying` residue, and no Workplace mutation.

## F-SEARCH-02: single-file resource roots allow `..` sibling indexing

Location: `src/processforge_core/local_resource_search.py:352-359`.

Trigger: an authorized resource has a single file as its `content_roots` entry and a full-text source path such as `../secret.txt`. `_iter_source_files()` checks a file root against `root.parent`, so the sibling resolves as in-bounds; the directory-root branch correctly checks against `root`.

Expected: every source path remains within the authorized file root; a source path escaping the file root yields no files (or a structured invalid-source result).

Actual: the sibling is discovered, indexed, and returned to a query despite not being the authorized file.

Reproducer:

```powershell
python .pf/artifacts/codebase-audit-20260910/native-core/audit_search_file_root_escape.py
```

Captured output (`file-root-escape-output.txt`):

```text
DISCOVERED [('...\\project\\secret.txt', 'secret.txt')]
INDEXED {'status': 'fresh', 'indexed': 1, 'resources': 1, ...}
SEARCH_TOTAL 1
RESULT_PATHS ['secret.txt']
```

Complexity: low. For a file root, allow only `base == root`; reject any source path that resolves outside that exact file. Add a regression with an authorized file and sibling text containing a unique marker, asserting zero indexed rows and zero search results for the sibling marker.

## Validation

- `python tools/smoke_core_update_manifest.py` — PASS; symlink fixtures skipped by Windows `WinError 1314`.
- `python tools/smoke_search_source_integrity.py` — PASS, including existing explicit-file filtering and pagination coverage.
- Both audit probes compile with `python -m py_compile` — PASS.

The supplied existing smoke passes do not cover either finding. The audit is analysis-only; remediation and governance transitions remain with the primary task owner.
