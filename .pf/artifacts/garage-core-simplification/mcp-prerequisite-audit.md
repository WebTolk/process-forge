# MCP Prerequisite Audit

Generated: 2026-08-24 14:45 +04

| Tool | Current prerequisites | Really needed prerequisites | Garage availability | Forge/session enhancements |
| --- | --- | --- | --- | --- |
| `pf.context` | Missing | Valid PF project, current snapshot, workplace for path refs | Required new preferred entry | Add session telemetry when provided |
| `pf.project_state` | Ledger session due MCP gate | Valid PF project, current snapshot | Should be sessionless | Session can assert project consistency |
| `pf.work_state` | Ledger session due MCP gate | Valid PF project for read-only work summary | Should be partially sessionless | Ownership/current session details require Ledger |
| `pf.search` | Ledger session due MCP gate | Valid PF project, fresh/safely refreshed snapshot, authorized resources, search index | Should be sessionless | Session can assert project consistency and add telemetry |
| `pf.resolve` | Ledger session due MCP gate | Valid PF project, current snapshot, authorized resource id/path ref | Should be sessionless | Session can assert project consistency and add audit trail |
| `pf.workplace_state` | Ledger session due MCP gate | Workplace root | Diagnostic/operator, not ordinary Garage | Session not required, but should avoid project/session leakage |
| `pf.project_initialization.status` | Ledger session due MCP gate | Valid PF project; workplace optional for resource checks | Diagnostic/operator; can be sessionless read | Session can assert consistency |
| `pf.project_initialization.initialize` | Ledger session and `apply: true` | Write authority for target project | Not Garage read path | Keep stricter session/apply requirements |
| `pf.project_initialization.repair` | Ledger session and `apply: true` | Write authority for target project | Not Garage read path | Keep stricter session/apply requirements |
| `pf.session_context` | Ledger session | Ledger session | Not global Garage; session-only | Existing behavior remains |
| `pf.session_chat` | Ledger session | Ledger session | Not Garage | Existing behavior remains |
| `pf.session_activity` | Ledger session | Ledger session | Not Garage | Existing behavior remains |

## Decision

Move the session gate from "all non-session tools" to "only tools that expose
session/private/ownership data or perform writes". Read-only Garage tools must
resolve by `project_root` and fail closed if the project or snapshot is invalid.
