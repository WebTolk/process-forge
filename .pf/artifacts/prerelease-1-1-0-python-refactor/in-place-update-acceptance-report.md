# In-Place Update Acceptance Report

Date: 2026-08-23
Status: pending final RC archive

## Planned Checks

- Plan update from previous installed version to 1.1.0 archive.
- Apply update.
- Verify new manifest/version.
- Verify Runtime/MCP/search health after update.
- Verify obsolete PF-owned files are removed.
- Verify unknown local files are preserved.
- Verify locally modified core files are not overwritten silently.
- Verify incomplete update detection and repair reporting.

## Current Evidence

Source-level update smokes passed before final archive packaging:

- `smoke_core_update_manifest`: PASS.
- `smoke_update_stage_verify_apply_file_provider`: PASS.

Full in-place update acceptance must be rerun against the final committed
1.1.0 archive.
