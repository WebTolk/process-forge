# Core Update Operational Audit

Run: `operational-hardening-search-update-20260822`

## Findings

- `core-update plan` is read-only and validates archive manifest/payload checksums.
- `core-update apply` requires `--confirm`.
- Unknown files remain outside the PF-owned manifest boundary and are preserved.
- Locally modified PF-owned files block update unless explicitly forced.
- The installed manifest is written after payload file operations.
- File operation failures are converted to `file_operation_failed`.

## Gap Closed

The previous incomplete update journal did not record enough operational detail. The journal now records versions, archive, counts, completed operations, pending operations, backed-up files, backup directory, and failure code/message.

## Remaining Runtime Integration Gap

Runtime/MCP stop/start is not implemented in this slice. The current safe behavior is to surface file-operation blockers and incomplete state honestly.
