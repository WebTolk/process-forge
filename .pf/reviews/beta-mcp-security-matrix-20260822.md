# Beta MCP Security Matrix

## Scope

Assignment: `beta-mcp-security-matrix-20260822`

Read-only review of the current MCP/search/init/session contracts. No code changes attempted.

Sources reviewed:

- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/session_read.py`
- `src/processforge_core/local_resource_search.py`
- `src/processforge_core/project_initialization.py`
- `.pf/artifacts/beta-release-qualification-20260822/orchestrator-plan.md`

The orchestration plan requires MCP stdio, real Codex, search/resolve, initialization/repair, security, and path/session/write boundary gates before beta GO (`orchestrator-plan.md:18-31`). It also states that a real Codex MCP call blocked by approval policy `never` must be recorded as an environment blocker, not replaced by stdio evidence (`orchestrator-plan.md:37-40`).

## Contract Summary

- MCP exposes these tools: `pf.project_state`, `pf.project_initialization.status`, `pf.project_initialization.initialize`, `pf.project_initialization.repair`, `pf.work_state`, `pf.resolve`, `pf.search`, `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity` (`mcp_server.py:16-28`).
- Session mismatch is rejected before any tool-specific routing when both configured and requested sessions differ (`mcp_server.py:54-58`).
- Non-session tools require a supplied session, bind it to the Ledger project, and reject conflicting `project_root` (`mcp_server.py:66-74`).
- `pf.project_initialization.initialize` and `.repair` are write-capable MCP tools, but require `apply: true` and reject unexpected arguments (`mcp_server.py:81-101`).
- `pf.search` requires fresh or fresh-with-updates context, resolves `path_ref` roots only into a request-local snapshot copy, and returns local navigation only after containment checks (`mcp_server.py:109-145`).
- Session read models authorize through Ledger presence and reject missing, unknown, unrouted, invalid, or mismatched sessions/projects (`session_read.py:43-69`).
- Session context returns bounded active agents, blockers, stage obligations, freshness, and recent activity (`session_read.py:107-178`).
- Session chat enforces bounded pagination, unambiguous cursors, valid role filters, and cursor validity (`session_read.py:181-221`).
- Session activity is authorized by caller session but intentionally returns current-project activity, not only the caller session's own events (`session_read.py:224-238`).
- Local search indexes only snapshot-supplied resource records and supported text files up to 1 MB (`local_resource_search.py:74-141`).
- Local search treats user query as a literal FTS phrase and returns provenance with snapshot checksum (`local_resource_search.py:172-205`).
- Initialization status is non-mutating and public-safe, including `public_safety: no_private_paths` (`project_initialization.py:33-68`).

## Executable Test Matrix

| ID | Area | Case | Setup | Action | Expected Evidence |
|---|---|---|---|---|---|
| MCP-001 | stdio protocol | Initialize handshake | Installed beta MCP server, isolated workplace manifest | Send JSON-RPC `initialize` | Response has `protocolVersion: 2024-11-05`, `serverInfo.name: processforge`, and `capabilities.tools` (`mcp_server.py:181-182`) |
| MCP-002 | stdio protocol | Tool discovery | Same | Send `tools/list` | Response lists all 11 PF tools with input schemas (`mcp_server.py:16-28`, `mcp_server.py:183-185`) |
| MCP-003 | stdio protocol | Unknown method | Same | Send method not implemented by server | JSON-RPC error `-32601`, message `method not found` (`mcp_server.py:193`) |
| MCP-004 | stdio protocol | Malformed JSON | Same | Send invalid JSON line | JSON-RPC error `-32700`, message `invalid request` (`mcp_server.py:204-212`) |
| MCP-005 | error shape | Tool exception redaction | Same | Call a tool with known bad input | Tool result has `isError: true` and text JSON contains only stable `error.code`, no traceback/path diagnostic (`mcp_server.py:168-172`, `mcp_server.py:186-192`) |
| SESS-001 | session auth | Missing session | Start MCP without `--session`; omit `session_id` | Call `pf.project_state` | Error code `missing_session` (`mcp_server.py:66-67`) |
| SESS-002 | session auth | Configured/requested mismatch | Start with session A | Call any tool with `arguments.session_id` B | Error code `session_mismatch` before project access (`mcp_server.py:54-58`) |
| SESS-003 | session auth | Unknown session | Use non-existent session id | Call `pf.session_context` | Error code `unknown_session` (`session_read.py:46-52`) |
| SESS-004 | session auth | Session not routed | Ledger presence exists without `project_root` | Call `pf.session_context` | Error code `session_not_routed` (`session_read.py:53-55`) |
| SESS-005 | session auth | Invalid stored project | Ledger presence points to invalid project or mismatched project id | Call `pf.session_context` | Error code `session_project_invalid` (`session_read.py:56-61`) |
| SESS-006 | session auth | Cross-project read blocked | Session bound to project A | Call `pf.session_context` or `pf.project_state` with project B | Error code `session_project_mismatch` (`session_read.py:62-68`, `mcp_server.py:70-74`) |
| CTX-001 | session context | Positive current context | Active Ledger-bound session in fresh project | Call `pf.session_context` | Payload kind `pf.session_context`; includes session, project, work, stage obligations, blockers, active agents, context freshness, recent activity (`session_read.py:137-178`) |
| CTX-002 | session context | Bounds | Project has more than 20 agents/activity events and more than 10 blockers | Call `pf.session_context` | `active_agents` max 20, `recent_activity` max 20, `blockers` max 10 (`session_read.py:115-177`) |
| CHAT-001 | transcript read | Positive chat page | Ledger-bound session with chat messages | Call `pf.session_chat` with `limit: 2` | Payload kind `pf.session_chat`; includes exported messages with content and page metadata (`session_read.py:181-221`) |
| CHAT-002 | transcript read | Invalid limit | Same | Call `pf.session_chat` with `limit: 0`, `101`, `true`, or non-integer | Error code `invalid_limit` (`session_read.py:29-40`, `session_read.py:193`) |
| CHAT-003 | transcript read | Ambiguous cursor | Same | Call `pf.session_chat` with different `before` and `cursor` | Error code `ambiguous_cursor` (`session_read.py:194-195`) |
| CHAT-004 | transcript read | Invalid cursor | Same | Call `pf.session_chat` with unknown cursor id | Error code `invalid_cursor` (`session_read.py:208-212`) |
| CHAT-005 | transcript read | Role filter | Same | Call `pf.session_chat` with `roles: ["user"]` | Returned messages all have user role (`session_read.py:197-206`) |
| CHAT-006 | transcript read | Invalid roles | Same | Call with non-list roles or role outside `user`, `assistant`, `system` | Error code `invalid_roles` (`session_read.py:198-203`) |
| ACT-001 | activity read | Positive activity | Ledger-bound session with current project journal | Call `pf.session_activity` | Payload kind `pf.session_activity`; newest-first bounded current-project activity (`session_read.py:224-238`) |
| ACT-002 | activity read | Peer activity visible | Same project has events from another active session | Call `pf.session_activity` from authorized session | Peer project events are visible because model is current-project scoped (`session_read.py:229-231`) |
| INIT-001 | status | Initialized project complete | Initialized project, fresh snapshot, deterministic artifacts present | Call `pf.project_initialization.status` | State `complete`; `public_safety: no_private_paths`; resources summary present (`project_initialization.py:33-68`) |
| INIT-002 | status | Missing/incomplete project | Missing `.pf` or missing snapshot | Call status | State `incomplete`; repair plan includes `initialize` (`project_initialization.py:42-64`) |
| INIT-003 | status | Repairable project | Stale/broken context or missing deterministic artifact | Call status | State `repairable`; repair plan includes `refresh_context`, and `restore_deterministic_artifacts` when artifacts are missing (`project_initialization.py:47-68`) |
| INIT-004 | write guard | Initialize without apply | Bound session | Call `pf.project_initialization.initialize` without `apply: true` | Error code `apply_required`; no files created/changed (`mcp_server.py:81-85`) |
| INIT-005 | write guard | Repair without apply | Bound session | Call `pf.project_initialization.repair` without `apply: true` | Error code `apply_required`; no files changed (`mcp_server.py:81-85`) |
| INIT-006 | argument allowlist | Extra init arg rejected | Bound session | Call initialize with `apply: true` plus unexpected argument | Error code `invalid_arguments` (`mcp_server.py:86-91`) |
| INIT-007 | argument allowlist | Extra repair arg rejected | Bound session | Call repair with `apply: true` plus unexpected argument | Error code `invalid_arguments` (`mcp_server.py:86-91`) |
| INIT-008 | apply positive | Initialize through MCP | Fresh greenfield project bound through session, valid workplace manifest | Call initialize with `apply: true` and allowed args | Response `action: initialize`, `applied: true`; deterministic `.pf` state exists (`project_initialization.py:116-140`) |
| INIT-009 | apply safety | Missing workplace manifest | Apply init with missing workplace manifest and no `allow_missing_workplace` | Call initialize | Error code `workplace_manifest_required` (`project_initialization.py:121-122`) |
| REPAIR-001 | repair positive | Refresh context | Initialized project with repairable snapshot | Call repair with `apply: true`, `repair_action: refresh_context` | Response `action: repair`, `applied: true`; subsequent status no longer stale/broken if repair succeeds (`project_initialization.py:143-169`) |
| REPAIR-002 | repair positive | Restore deterministic artifacts | Initialized project missing deterministic artifact | Call repair with `apply: true`, `repair_action: restore_deterministic_artifacts` | Missing artifact restored through deterministic project file builder (`project_initialization.py:158-168`) |
| REPAIR-003 | repair negative | Unsupported action | Direct service or schema-bypassing MCP call with unsupported action | Call repair | Error code `unsupported_repair_action` (`project_initialization.py:151-153`) |
| SEARCH-001 | search positive | Fresh snapshot search | Fresh project context with authorized local search resources | Call `pf.search` with known literal query | Payload kind `pf.search`; results include `resource_id`, `canonical_path`, `path_ref`, `provenance.snapshot_checksum`, `page` (`local_resource_search.py:172-205`) |
| SEARCH-002 | freshness gate | Stale/broken snapshot | Make project context stale/broken | Call `pf.search` | Error code `snapshot_not_fresh` (`mcp_server.py:109-111`) |
| SEARCH-003 | input validation | Empty query | Fresh context | Call `pf.search` with empty/missing query | Error code `invalid_query` (`local_resource_search.py:172-174`) |
| SEARCH-004 | input validation | Invalid limit | Fresh context | Call with `limit: 0`, `101`, `true`, or non-integer | Error code `invalid_limit` (`local_resource_search.py:42-53`) |
| SEARCH-005 | input validation | Invalid offset | Fresh context | Call with negative, boolean, or non-integer `limitstart`/`offset` | Error code `invalid_offset` (`local_resource_search.py:56-71`) |
| SEARCH-006 | input validation | Ambiguous offset | Fresh context | Call with different `limitstart` and `offset` | Error code `ambiguous_offset` (`local_resource_search.py:56-60`) |
| SEARCH-007 | FTS literal safety | Operator-like query | Fresh context | Search for punctuation/operator string such as `foo-bar "baz"` | Query is treated as one quoted literal phrase; no FTS operator execution or syntax leakage (`local_resource_search.py:194-202`) |
| SEARCH-008 | indexing boundary | Snapshot-only corpus | Snapshot has one authorized root and an adjacent unauthorized file | Search terms unique to each | Authorized term can match; unauthorized term returns no result (`local_resource_search.py:74-114`) |
| SEARCH-009 | path boundary | Skip URL/private placeholders | Snapshot resource paths include `<placeholder>` or `scheme://...` | Build/search index | Such paths are skipped and never indexed (`local_resource_search.py:98-101`) |
| SEARCH-010 | file boundary | File type and size limits | Authorized root contains supported text, unsupported binary suffix, and text file >1 MB | Search terms unique to each | Only supported <=1 MB text file is indexed (`local_resource_search.py:18-21`, `local_resource_search.py:117-127`) |
| SEARCH-011 | index lifecycle | Missing index | Delete test fixture search index | Call `pf.search` | Index is rebuilt and `search_status` is `current` or `empty` (`local_resource_search.py:148-180`) |
| SEARCH-012 | index lifecycle | Stale checksum | Existing index has old snapshot checksum | Call `pf.search` after snapshot checksum changes | Index is rebuilt and response `search_status: stale` (`local_resource_search.py:181-190`) |
| SEARCH-013 | path disclosure | Public snapshot remains clean | Resource has `path_ref` resolved by MCP wrapper | Call `pf.search`; inspect snapshot before/after | Physical `content_roots` are request-local only and not persisted (`mcp_server.py:114-123`) |
| SEARCH-014 | navigation containment | Local path only inside authorized root | Search result canonical path is valid under root | Call `pf.search` | Optional `local_path` appears only when candidate is a file under root; navigation is `private_runtime_authorized` (`mcp_server.py:128-144`) |
| RESOLVE-001 | resolve positive | Resolve project/resource | Bound session | Call `pf.resolve` with and without resource id | Payload resolves through Ledger-bound session (`mcp_server.py:102-105`) |
| WORK-001 | work state | Positive current work | Bound session with active work | Call `pf.work_state` | Payload is returned for session-bound project only (`mcp_server.py:102-103`) |
| WORKPLACE-001 | workplace state | Positive workplace read | Valid workplace | Call `pf.workplace_state` | Derived workplace ledger state returned (`mcp_server.py:146-147`) |
| CODEX-001 | real Codex | Real MCP session context | Installed beta configured in Codex with actual MCP server and valid session | From real Codex, call `pf.session_context` | Durable evidence shows real Codex tool call and valid `pf.session_context` payload; not a hand-run stdio substitute (`orchestrator-plan.md:29-31`) |
| CODEX-002 | real Codex | Real MCP search after context | Same real Codex session | Call `pf.session_context`, then `pf.search` | Evidence proves both calls occurred in order in the same Codex session (`orchestrator-plan.md:29-31`) |
| CODEX-003 | real Codex | Approval-policy blocker | Environment uses approval policy `never` and real MCP call is blocked | Attempt real Codex MCP call | Record as environment blocker with exact policy/command evidence; do not count stdio-only result as this gate (`orchestrator-plan.md:37-40`) |

## Minimum Beta Evidence Bundle

For each matrix run, collect:

- Candidate commit/tag and archive SHA-256.
- Installed distribution, workplace, and project fixture identifiers, with exact paths kept in private evidence only.
- Raw MCP stdio request/response logs for MCP/search/session/init/repair cases.
- Real Codex MCP evidence for `CODEX-001` and `CODEX-002`, or a blocker record for `CODEX-003`.
- Before/after file inventory for write-guard cases proving no mutation when `apply` is missing or invalid.
- Snapshot before/after evidence for search path-ref resolution proving physical roots are not persisted.
- Search index evidence showing missing-index rebuild and stale-checksum rebuild.
- Final classification per case: PASS, FAIL product defect, or BLOCKED environment.

## GO / NO-GO Rules

Beta is GO for this slice only if:

- All positive stdio MCP, session, initialization, repair, resolve/work/workplace, and search cases pass.
- All negative session, write-boundary, argument, freshness, cursor, pagination, offset, query, and path-boundary cases return the expected stable error code or safe empty result.
- Real Codex evidence includes `pf.session_context` followed by `pf.search`, unless blocked by approval policy `never`, in which case the gate is BLOCKED environment rather than PASS.
- No public report/artifact includes private workspace paths copied from runtime access files.
- Any failure that leaks private paths, bypasses Ledger session binding, writes without exact `apply: true`, searches stale snapshots, or indexes outside snapshot-authorized roots is a NO-GO product defect.