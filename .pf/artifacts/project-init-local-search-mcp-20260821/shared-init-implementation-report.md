# Shared initialization and repair implementation

## Delivered

- Expanded `processforge_core.project_initialization` from a read-model guard
  into the application service for deterministic initialization and repair.
- Converted CLI `project-onboard` / `init-project` / `project-init` into a
  thin request adapter over that service.
- Added `project-init-repair`, whose default is a non-mutating plan and whose
  only supported applied action is `refresh_context` plus doctor validation.
- Added Ledger-bound MCP tools
  `pf.project_initialization.initialize` and
  `pf.project_initialization.repair`. Both call the same service and reject
  every request without the exact JSON boolean `apply: true`.

## Safety boundary

- MCP replaces any supplied project root with the Ledger-bound project after
  the existing mismatch check.
- Repair rejects a project without `.pf` and never performs onboarding.
- Existing writers retain their brownfield non-overwrite behavior unless
  `force` is explicitly supplied.
- MCP results return project id, relative artifact records, snapshot facts and
  doctor state; they do not return physical workspace paths or doctor output.

## Verification

1. `python -m py_compile src\\processforge_core\\project_initialization.py tools\\processforge.py tools\\pf_runtime\\mcp_server.py tools\\smoke_project_init_local_search_mcp.py`
2. `python tools\\smoke_project_init_local_search_mcp.py` — PASS.
   The fixture now proves `pf.project_initialization.repair` rejects an absent
   apply acknowledgement and succeeds with `apply: true` plus doctor PASS.
3. `git diff --check` — PASS (only existing CRLF conversion warnings).

## Review remediation

The first independent code review found two real issues. They are fixed and
covered by the stdio smoke:

- MCP initialization now copies only an explicit per-tool allowlist. An
  injected `answers_path` is rejected as `invalid_arguments`, so the MCP
  service cannot read an arbitrary server-local answers file.
- Public onboarding reports no longer embed raw doctor output. They retain the
  result and direct an operator to run doctor locally; the smoke proves that a
  project’s absolute temporary root is absent from that public report.
