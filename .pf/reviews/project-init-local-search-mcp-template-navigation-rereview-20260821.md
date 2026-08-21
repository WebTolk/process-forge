# Template Navigation Rereview

Result: `PASS_WITH_LIMITATION`

## Scope

Reviewed only the allowed files:

- `tools/processforge.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/smoke_project_init_local_search_mcp.py`

No product code changes. No subagents.

## Findings

No blocking findings found.

## Checks

### Registry-template path containment

`PASS`

Evidence:

- Template local-search snapshot entries persist only `path_ref: {registry: templates, id: ...}` and do not persist physical paths: `tools/processforge.py:9810-9823`.
- Runtime path resolution rejects non-private registry paths that escape the workplace root: `tools/processforge.py:9234-9242`.
- Runtime path resolution also rejects `relative_path` values escaping the declared registry root: `tools/processforge.py:9243-9247`.
- MCP injects `content_roots` only into a request-local snapshot copy, not the public snapshot: `tools/pf_runtime/mcp_server.py:114-123`.
- MCP adds `local_path` navigation only after resolving the candidate under the authorized root: `tools/pf_runtime/mcp_server.py:133-143`.

### Validator alias consistency

`PASS`

Evidence:

- CLI aliases `init-project`, `project-init`, and `project-onboard` share the same project initialization command path and compatible arguments, including `--answers`: `tools/processforge.py:24579-24625`.
- CLI maps `--answers` to internal `answers_path`: `tools/processforge.py:5838-5854`.
- MCP schema exposes `answers` for `pf.project_initialization.initialize`, while dispatcher allow-list accepts `answers` and rejects unsupported keys before calling initialization: `tools/pf_runtime/mcp_server.py:86-99`, `tools/pf_runtime/mcp_server.py:157-160`.
- Negative stdio fixture verifies that `answers_path` is rejected over MCP as `invalid_arguments`: `tools/smoke_project_init_local_search_mcp.py:85`, `tools/smoke_project_init_local_search_mcp.py:106-107`.

### New negative stdio fixture

`PASS` by static review.

Evidence:

- Fixture creates an outside file containing both `traversal-secret-token` and `registry-secret-token`: `tools/smoke_project_init_local_search_mcp.py:49`.
- Fixture injects a malicious template registry entry with `path: ../outside.md`: `tools/smoke_project_init_local_search_mcp.py:55-58`.
- Fixture injects a malicious `package: self` resource with `relative_path: ../outside.md`: `tools/smoke_project_init_local_search_mcp.py:72-75`.
- Fixture asserts public snapshot has no `content_roots`, `local_path`, or `resolved_path`, and does not contain the workplace absolute path: `tools/smoke_project_init_local_search_mcp.py:68-71`.
- Fixture asserts both traversal and registry-secret searches return no results: `tools/smoke_project_init_local_search_mcp.py:99-100`, `tools/smoke_project_init_local_search_mcp.py:111`.

## Verification Limitation

Attempted to run:

```powershell
python tools/smoke_project_init_local_search_mcp.py
```

The smoke did not execute under the current read-only sandbox because Python could not create a temporary directory under `D:\temp\...` (`PermissionError: [WinError 5]`). This is an environment permission blocker, not a confirmed product defect.