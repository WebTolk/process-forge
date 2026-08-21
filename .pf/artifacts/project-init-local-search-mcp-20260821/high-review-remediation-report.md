# Remediation of high MCP search review

## Reviewed findings

- Fixed the confirmed HIGH finding: `resolve_workspace_path_ref()` now resolves
  a candidate only after it proves that the candidate is contained by its
  declared package or registry base. Absolute and parent-traversal
  `relative_path` values return `unresolved` with `invalid_path_ref`.
- Extended the isolated stdio fixture to call `pf.search` through the actual
  MCP server, assert its canonical result and absence of the temporary
  physical path, and prove that a malicious `../outside.md` snapshot entry
  cannot expose the sibling token.
- Strengthened the pre-existing session mismatch assertion to require
  `isError: true` as well as `session_project_mismatch`.

## Verification

1. `python -m py_compile tools\\processforge.py tools\\smoke_project_init_local_search_mcp.py`
2. `python tools\\smoke_project_init_local_search_mcp.py` — PASS.
3. Direct isolated resolver assertion for `package:self` plus `../escape` —
   PASS (`unresolved`, `invalid_path_ref`).
4. `git diff --check` — PASS; only existing CRLF conversion warnings.

## Residual scope

The review addressed the static MCP search boundary and stdio coverage. The
larger shared initialize/repair writer refactor remains a separate delivery
slice and is not claimed by this remediation.
